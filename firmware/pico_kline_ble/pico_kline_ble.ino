/*
 * pico_kline_ble — Raspberry Pi Pico 2 W (or Pico W) BLE K-line adapter.
 *
 * Serves the gems_t4 host protocol (../HOST_PROTOCOL.md) over **Bluetooth LOW
 * ENERGY** using a Nordic UART Service (NUS), instead of Bluetooth Classic SPP.
 *
 * WHY BLE (vs the Classic-SPP pico_kline_bt): BLE GATT needs **no bonding** — the
 * laptop's Python client (bleak) just connects to the service. That means **no
 * Windows pairing dialog, no virtual COM port, no incoming/outgoing port mess**,
 * which is exactly the Classic-SPP pain this replaces. The laptop also keeps its
 * own WiFi (point-to-point), like the Classic-BT build.
 *
 *   gems_t4 kline dtc --ble gems-pico      (BleTransport, no COM port)
 *
 * NUS UUIDs (what the bleak client talks to):
 *   service 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
 *   RX (host->Pico, Write)   6E400002-...   <- client writes host frames here
 *   TX (Pico->host, Notify)  6E400003-...   <- client subscribes for replies
 *
 * SUPERSET: answers every production host command PLUS the pentest CMD_RAW_INIT
 * (0x05), so gems_t4 AND the pentest/debug scripts work over BLE. PING reports
 * "gems_t4-pico-ble-pentest 2.1.0" (the "pentest" substring is required by
 * pentest_scan.py's firmware gate).
 *
 * BOARD: Pico 2 W / Pico W. BUILD: enable Bluetooth:
 *   arduino-cli ... --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble
 *   (IDE: Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth")
 *
 * ⚠️ UNVERIFIED ON HARDWARE / needs an on-device tuning pass. BLE notifications
 * do NOT fragment — they truncate to the negotiated ATT MTU. The core doesn't
 * raise the MTU, so this sketch sends replies in small (<=16 B) chunks with a
 * short delay between them (delay() pumps the CYW43 async context so each notify
 * actually transmits before the next). The Python side reassembles the byte
 * stream. If replies look truncated/garbled on real hardware, tune BLE_TX_CHUNK
 * / the inter-chunk delay, or raise the ATT MTU. Real GEMS frames are small
 * (DTC/live/raw-init << 100 B), so this is comfortable in practice.
 *
 * SECURITY: no bonding + no link encryption by default — anything in BLE range
 * that speaks NUS can drive the K-line. The laptop treats BLE like the Classic
 * BT link (not the TCP "wireless" gate), so writes are allowed. Use on a bench
 * you control; the firmware is a dumb timed pipe.
 */

#include <Arduino.h>
#include <BLE.h>             // arduino-pico BLE (BTstack); provides BLEServiceUART

// NUS UART service; rxbuff generous, txbuff kept small so each notify fits any
// ATT MTU (a notify is capped at MTU-3 and NOT fragmented).
static BLEServiceUART uart(256, 20);
static const char BLE_NAME[] = "gems-pico";
static const size_t BLE_TX_CHUNK = 16;      // <= txbuff and <= min MTU payload (20)
static const uint8_t BLE_TX_GAP_MS = 6;     // let the stack transmit each chunk

// ---- pins / config (identical to the USB firmware) -------------------------
static const uint32_t KLINE_BAUD = 10400;
static const uint8_t  KLINE_TX_PIN = 0;
static const uint8_t  KLINE_RX_PIN = 1;

static uint16_t P1 = 20, P2 = 50, P3 = 55, P4 = 10;

// ---- host protocol constants (must match HOST_PROTOCOL.md) -----------------
static const uint8_t HOST_START = 0xA5;
static const uint8_t PICO_START = 0x5A;
static const uint8_t CMD_PING = 0x01, CMD_INIT = 0x02, CMD_SEND_RECV = 0x03, CMD_SET_TIMING = 0x04;
static const uint8_t CMD_RAW_INIT = 0x05;
static const uint8_t ST_OK = 0x00, ST_TIMEOUT = 0x01, ST_BUS_ERROR = 0x02, ST_BAD_REQUEST = 0x03;

static const uint16_t RESP_TIMEOUT_MS = 1000;
static const size_t   MAX_PAYLOAD = 255;

//   ble 2.1.0 = pico_kline 2.0.0 K-line logic + pentest CMD_RAW_INIT, over BLE NUS.
//   Keep the "pentest" substring: pentest_scan.py gates on it.
static const char FW_VERSION[] = "gems_t4-pico-ble-pentest 2.1.0";

// ---- crc8 (XOR) ------------------------------------------------------------
static uint8_t crc8(const uint8_t *buf, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; i++) c ^= buf[i];
  return c;
}

// ---- host frame I/O over the BLE UART --------------------------------------
// Send raw bytes in MTU-safe chunks, pacing so each notify transmits.
static void bleWrite(const uint8_t *buf, size_t len) {
  if (!uart) return;                       // no connected client
  for (size_t off = 0; off < len; off += BLE_TX_CHUNK) {
    size_t n = (len - off < BLE_TX_CHUNK) ? (len - off) : BLE_TX_CHUNK;
    for (size_t i = 0; i < n; i++) uart.write(buf[off + i]);
    uart.flush();                          // one notification for this chunk
    delay(BLE_TX_GAP_MS);                  // delay() pumps the CYW43/BTstack context
  }
}

static void sendPico(uint8_t status, const uint8_t *payload, uint8_t len) {
  uint8_t frame[3 + MAX_PAYLOAD + 1];
  size_t n = 0;
  frame[n++] = PICO_START;
  frame[n++] = status;
  frame[n++] = len;
  for (uint8_t i = 0; i < len; i++) frame[n++] = payload[i];
  uint8_t hdr[2] = { status, len };
  frame[n++] = crc8(hdr, 2) ^ crc8(payload, len);
  bleWrite(frame, n);
}

// Block until n bytes are read from the BLE client, or timeout; returns count.
static size_t readHost(uint8_t *buf, size_t n, uint32_t timeout_ms) {
  uint32_t start = millis();
  size_t got = 0;
  while (got < n && (millis() - start) < timeout_ms) {
    if (uart.available()) buf[got++] = uart.read();
  }
  return got;
}

// ==========================================================================
//  K-line helpers + init + handlers — copied VERBATIM from pico_kline 2.0.0.
//  Keep in lockstep with ../pico_kline/pico_kline.ino if that changes.
// ==========================================================================
static bool klineWriteByte(uint8_t b) {
  Serial1.write(b);
  uint32_t start = millis();
  while (!Serial1.available()) {
    if (millis() - start > P4 + 5) return false;
  }
  Serial1.read();
  return true;
}

static bool klineWrite(const uint8_t *frame, size_t n) {
  for (size_t i = 0; i < n; i++) {
    if (!klineWriteByte(frame[i])) return false;
    delay(P4);
  }
  return true;
}

static int klineReadFrame(uint8_t *out, size_t maxlen) {
  uint32_t start = millis();
  size_t n = 0;
  while (!Serial1.available()) {
    if (millis() - start > RESP_TIMEOUT_MS) return -1;
  }
  uint32_t lastByte = millis();
  while (n < maxlen) {
    if (Serial1.available()) {
      out[n++] = Serial1.read();
      lastByte = millis();
    } else if (millis() - lastByte > P1 + 2) {
      break;
    } else if (millis() - start > RESP_TIMEOUT_MS) {
      break;
    }
  }
  return (int)n;
}

static bool klineReadByte(uint8_t *b, uint32_t timeout_ms) {
  uint32_t start = millis();
  while (!Serial1.available()) {
    if (millis() - start > timeout_ms) return false;
  }
  *b = Serial1.read();
  return true;
}

static bool slowInit(uint8_t address, uint8_t *keybytes, uint8_t *kb_len) {
  Serial1.end();
  pinMode(KLINE_TX_PIN, OUTPUT);
  digitalWrite(KLINE_TX_PIN, HIGH);
  delay(300);
  digitalWrite(KLINE_TX_PIN, LOW); delay(200);
  for (int i = 0; i < 8; i++) {
    digitalWrite(KLINE_TX_PIN, (address >> i) & 1);
    delay(200);
  }
  digitalWrite(KLINE_TX_PIN, HIGH); delay(200);

  Serial1.begin(KLINE_BAUD);
  uint8_t sync, kb1, kb2;
  if (!klineReadByte(&sync, 500) || sync != 0x55) return false;
  if (!klineReadByte(&kb1, 50)) return false;
  if (!klineReadByte(&kb2, 50)) return false;

  uint32_t kb2_at = millis();
  while (millis() - kb2_at < 30) { /* W4 window */ }
  Serial1.write((uint8_t)(kb2 ^ 0xFF));
  uint8_t echo, inv_addr;
  klineReadByte(&echo, 50);
  klineReadByte(&inv_addr, 100);

  keybytes[0] = kb1;
  keybytes[1] = kb2;
  *kb_len = 2;
  return true;
}

static bool fastInit(uint8_t address, uint8_t *keybytes, uint8_t *kb_len) {
  Serial1.end();
  pinMode(KLINE_TX_PIN, OUTPUT);
  digitalWrite(KLINE_TX_PIN, HIGH); delay(300);
  digitalWrite(KLINE_TX_PIN, LOW);  delay(25);
  digitalWrite(KLINE_TX_PIN, HIGH); delay(25);
  Serial1.begin(KLINE_BAUD);

  uint8_t sc[5] = { 0x81, address, 0xF7, 0x81, 0 };
  sc[4] = (uint8_t)(sc[0] + sc[1] + sc[2] + sc[3]);
  for (int i = 0; i < 5; i++) {
    if (!klineWriteByte(sc[i])) return false;
  }

  uint8_t buf[16];
  int n = klineReadFrame(buf, sizeof(buf));
  for (int i = 0; i + 2 < n; i++) {
    if (buf[i] == 0xC1) {
      keybytes[0] = buf[i + 1];
      keybytes[1] = buf[i + 2];
      *kb_len = 2;
      return true;
    }
  }
  return false;
}

static void handleInit(const uint8_t *payload, uint8_t len) {
  if (len < 2) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }
  uint8_t address = payload[0], mode = payload[1];
  uint8_t kb[2], kb_len = 0;
  bool ok = (mode == 1) ? fastInit(address, kb, &kb_len)
                        : slowInit(address, kb, &kb_len);
  if (ok) sendPico(ST_OK, kb, kb_len);
  else    sendPico(ST_TIMEOUT, nullptr, 0);
}

static void handleSendRecv(const uint8_t *payload, uint8_t len) {
  if (!klineWrite(payload, len)) { sendPico(ST_BUS_ERROR, nullptr, 0); return; }
  delay(P2);
  static uint8_t resp[MAX_PAYLOAD];
  int n = klineReadFrame(resp, sizeof(resp));
  if (n < 0)      sendPico(ST_TIMEOUT, nullptr, 0);
  else            sendPico(ST_OK, resp, (uint8_t)n);
  delay(P3);
}

static void handleSetTiming(const uint8_t *payload, uint8_t len) {
  if (len < 8) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }
  P1 = (payload[0] << 8) | payload[1];
  P2 = (payload[2] << 8) | payload[3];
  P3 = (payload[4] << 8) | payload[5];
  P4 = (payload[6] << 8) | payload[7];
  sendPico(ST_OK, nullptr, 0);
}

// Read raw K-line bytes: wait up to firstTimeout for the first byte, then read
// until an inter-byte gap. Returns whatever arrives, UNFILTERED (0 = silent).
static int klineReadRaw(uint8_t *out, size_t maxlen, uint32_t firstTimeout) {
  uint32_t start = millis();
  while (!Serial1.available()) {
    if (millis() - start > firstTimeout) return 0;
  }
  size_t n = 0;
  uint32_t last = millis();
  while (n < maxlen) {
    if (Serial1.available()) { out[n++] = Serial1.read(); last = millis(); }
    else if (millis() - last > P1 + 5) break;
    else if (millis() - start > firstTimeout + 800) break;
  }
  return (int)n;
}

// Pentest primitive (CMD_RAW_INIT): arbitrary init at an arbitrary UART baud,
// RAW response returned (unfiltered). payload:
//   [mode][baudHi][baudLo][addr][optional frame bytes...]
//   mode 0 = 5-baud slow init of <addr>; 1 = fast wake pulse; 2 = none (listen).
static void handleRawInit(const uint8_t *payload, uint8_t len) {
  if (len < 4) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }
  uint8_t mode = payload[0];
  uint32_t baud = ((uint32_t)payload[1] << 8) | payload[2];
  uint8_t addr = payload[3];
  const uint8_t *frame = payload + 4;
  uint8_t framelen = (uint8_t)(len - 4);

  Serial1.end();
  pinMode(KLINE_TX_PIN, OUTPUT);
  digitalWrite(KLINE_TX_PIN, HIGH);
  delay(300);
  if (mode == 0) {                        // 5-baud address, LSB first
    digitalWrite(KLINE_TX_PIN, LOW); delay(200);
    for (int i = 0; i < 8; i++) { digitalWrite(KLINE_TX_PIN, (addr >> i) & 1); delay(200); }
    digitalWrite(KLINE_TX_PIN, HIGH); delay(200);
  } else if (mode == 1) {                 // fast wake pulse
    digitalWrite(KLINE_TX_PIN, LOW); delay(25);
    digitalWrite(KLINE_TX_PIN, HIGH); delay(25);
  }
  Serial1.begin(baud);
  for (uint8_t i = 0; i < framelen; i++) {
    if (!klineWriteByte(frame[i])) break; // best-effort send + echo cancel
  }
  uint8_t buf[64];
  int n = klineReadRaw(buf, sizeof(buf), 500);
  sendPico(ST_OK, buf, (uint8_t)n);
}

// Parse and dispatch ONE host frame from the BLE client (0xA5 framed).
static void serviceHostFrame() {
  if (uart.read() != HOST_START) return;   // resync on stray byte

  uint8_t hdr[2];
  if (readHost(hdr, 2, 100) != 2) return;
  uint8_t cmd = hdr[0], len = hdr[1];

  static uint8_t payload[MAX_PAYLOAD];
  if (len && readHost(payload, len, 200) != len) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }

  uint8_t rxcrc;
  if (readHost(&rxcrc, 1, 100) != 1) return;
  uint8_t want = crc8(hdr, 2) ^ crc8(payload, len);
  if (rxcrc != want) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }

  switch (cmd) {
    case CMD_PING:       sendPico(ST_OK, (const uint8_t *)FW_VERSION, (uint8_t)(sizeof(FW_VERSION) - 1)); break;
    case CMD_INIT:       handleInit(payload, len); break;
    case CMD_SEND_RECV:  handleSendRecv(payload, len); break;
    case CMD_SET_TIMING: handleSetTiming(payload, len); break;
    case CMD_RAW_INIT:   handleRawInit(payload, len); break;
    default:             sendPico(ST_BAD_REQUEST, nullptr, 0); break;
  }
}

void setup() {
  Serial.begin(115200);              // USB debug only (optional)
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial1.setTX(KLINE_TX_PIN);
  Serial1.setRX(KLINE_RX_PIN);
  Serial1.begin(KLINE_BAUD);

  BLE.begin(BLE_NAME);               // advertise as "gems-pico"
  BLE.server()->addService(&uart);
  BLE.startAdvertising();
  uart.setAutoflush(30);             // safety-net flush for any straggler bytes

  Serial.print("BLE NUS up as \"");
  Serial.print(BLE_NAME);
  Serial.println("\" - connect with: gems_t4 kline dtc --ble gems-pico");
}

void loop() {
  // Solid LED = a BLE client is connected.
  digitalWrite(LED_BUILTIN, uart ? HIGH : LOW);

  // Service one host frame if bytes are waiting.
  if (uart && uart.available()) {
    serviceHostFrame();
  }
}
