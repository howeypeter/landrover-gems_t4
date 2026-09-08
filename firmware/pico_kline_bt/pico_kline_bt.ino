/*
 * pico_kline_bt — Raspberry Pi Pico 2 W (or Pico W) BLUETOOTH K-line adapter.
 *
 * Same K-line smart adapter as ../pico_kline/pico_kline.ino, but it serves the
 * gems_t4 host protocol (../HOST_PROTOCOL.md) over a **Bluetooth Classic SPP**
 * (Serial Port Profile) link instead of USB-CDC or WiFi.
 *
 * WHY BLUETOOTH: a paired SPP device shows up on Windows as a *virtual COM
 * port*, so it drops straight into the EXISTING serial transport — no new
 * Python. And it's point-to-point, so your LAPTOP STAYS ON ITS NORMAL WIFI
 * (unlike the WiFi/hotspot mode, where both ends must share one network).
 *
 *     (pair the Pico in Windows Bluetooth settings -> it creates COMx)
 *     gems_t4 kline live --port COM7
 *     gems_t4 kline dtc  --port COM7
 *     gems_t4 gui        --port COM7      (USB COM-port mode)
 *     python ~/pentest_scan.py COM7      (or any debug/probe script)
 *
 * SUPERSET FIRMWARE: because the BT link is just a virtual COM port, ANY tool
 * that opens that serial port works over it. So this sketch answers EVERY host
 * command the production sketch does (PING/INIT/SEND_RECV/SET_TIMING) PLUS the
 * pentest primitive CMD_RAW_INIT (0x05, copied from ../pico_kline_pentest) — so
 * gems_t4 AND pentest_scan.py / da*_probe.py / any ad-hoc debug script all run
 * over the one Bluetooth connection, no re-flashing to switch tasks. (PING
 * reports "gems_t4-pico-bt-pentest 2.1.0" — the "pentest" substring is required
 * because pentest_scan.py refuses any firmware whose ping lacks it.)
 *
 * The K-line timing/logic (5-baud init + W4 handshake, fast init, echo cancel,
 * inter-byte framing) is IDENTICAL to the USB firmware — only the host transport
 * changed (Serial -> SerialBT). The wiring (Pico <-> L9637D <-> ECU) is
 * unchanged — see ../README.md.
 *
 * BOARD: **Pico 2 W** (RP2350 + CYW43) or Pico W (RP2040 + CYW43). A non-W board
 * has no radio. Build target (arduino-pico): "Raspberry Pi Pico 2 W".
 * ENABLE BLUETOOTH: this sketch does NOT link unless the Bluetooth stack is
 * turned on. Arduino IDE: Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth".
 * arduino-cli: add ":ipbtstack=ipv4btcble" to the fqbn (see ../README.md).
 *
 * SECURITY NOTE — DIFFERENT FROM WIFI: a paired BT SPP link is point-to-point
 * and reaches the laptop as a *wired-looking* COM port, so the Python side
 * treats it as a trusted (non-wireless) transport and **ALLOWS writes by
 * default** (coding / immobiliser / actuators), exactly like plugging in USB.
 * The read-only "wireless" gate does NOT apply here. Only pair laptops you
 * trust, and start sessions read-only until you mean to write.
 */

#include <Arduino.h>
#include <SerialBT.h>        // arduino-pico Bluetooth Classic SPP (Serial-compatible)
#include <BluetoothLock.h>   // async_context lock required before any BTStack call

// ---- Bluetooth device name (what you'll see when pairing) ------------------
static const char BT_NAME[] = "gems-pico";

// ---- pins / config (identical to the USB firmware) -------------------------
static const uint32_t KLINE_BAUD = 10400;
static const uint8_t  KLINE_TX_PIN = 0;
static const uint8_t  KLINE_RX_PIN = 1;

static uint16_t P1 = 20, P2 = 50, P3 = 55, P4 = 10;

// ---- host protocol constants (must match HOST_PROTOCOL.md) -----------------
static const uint8_t HOST_START = 0xA5;
static const uint8_t PICO_START = 0x5A;
static const uint8_t CMD_PING = 0x01, CMD_INIT = 0x02, CMD_SEND_RECV = 0x03, CMD_SET_TIMING = 0x04;
static const uint8_t CMD_RAW_INIT = 0x05;   // pentest primitive (see ../pico_kline_pentest)
static const uint8_t ST_OK = 0x00, ST_TIMEOUT = 0x01, ST_BUS_ERROR = 0x02, ST_BAD_REQUEST = 0x03;

static const uint16_t RESP_TIMEOUT_MS = 1000;
static const size_t   MAX_PAYLOAD = 255;

//   bt 2.1.0  = pico_kline 2.0.0 K-line logic + pentest CMD_RAW_INIT, over BT SPP.
//   This is a SUPERSET firmware: it answers every host command the production
//   sketch does PLUS the raw-init sweep primitive, so gems_t4 AND the pentest/
//   debug scripts all work over the one Bluetooth COM port.
//   NOTE: the version string DELIBERATELY contains "pentest" — pentest_scan.py
//   gates on `"pentest" in ping()` (both at startup and in mid-sweep recovery)
//   and would otherwise refuse to run against this firmware. Keep the substring.
static const char FW_VERSION[] = "gems_t4-pico-bt-pentest 2.1.0";

// ---- crc8 (XOR) ------------------------------------------------------------
static uint8_t crc8(const uint8_t *buf, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; i++) c ^= buf[i];
  return c;
}

// ---- host frame I/O over SerialBT (was Serial in the USB firmware) ---------
static void sendPico(uint8_t status, const uint8_t *payload, uint8_t len) {
  uint8_t hdr[2] = { status, len };
  uint8_t c = crc8(hdr, 2) ^ crc8(payload, len);
  if (!SerialBT) return;                 // no paired client
  SerialBT.write(PICO_START);
  SerialBT.write(hdr, 2);
  if (len) SerialBT.write(payload, len);
  SerialBT.write(c);
  SerialBT.flush();
}

// Block until n bytes are read from the BT client, or timeout; returns count.
static size_t readHost(uint8_t *buf, size_t n, uint32_t timeout_ms) {
  uint32_t start = millis();
  size_t got = 0;
  while (got < n && (millis() - start) < timeout_ms) {
    if (SerialBT && SerialBT.available()) buf[got++] = SerialBT.read();
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
// After init, Serial1 opens at <baud>; any <frame> bytes are sent (echo
// cancelled); then raw bytes are read and returned (empty payload = silent).
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

// Parse and dispatch ONE host frame from the BT client (0xA5 framed).
static void serviceHostFrame() {
  if (SerialBT.read() != HOST_START) return;   // resync on stray byte

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

  SerialBT.setName(BT_NAME);          // shows up as "gems-pico" when pairing
  SerialBT.begin();

  // --- Headless pairing ("Just Works") ------------------------------------
  // The Pico has no screen or keypad, but stock SerialBT advertises
  // DISPLAY_YES_NO, which makes Windows do numeric-comparison pairing (show a
  // 6-digit code to confirm) — and SerialBT never sends that confirmation, so
  // pairing fails with "that PIN didn't work". Re-advertise as NO_INPUT_NO_OUTPUT
  // and auto-accept so both sides negotiate "Just Works": no PIN, no passkey
  // prompt. BTStack APIs must be called while holding the async_context lock.
  {
    BluetoothLock l;
    gap_ssp_set_io_capability(SSP_IO_CAPABILITY_NO_INPUT_NO_OUTPUT);
    gap_ssp_set_auto_accept(1);
  }

  Serial.print("Bluetooth SPP up as \"");
  Serial.print(BT_NAME);
  Serial.println("\" - pair it in Windows, then use: gems_t4 kline live --port COMx");
}

void loop() {
  // Solid LED = a tester is paired/connected over Bluetooth.
  digitalWrite(LED_BUILTIN, SerialBT ? HIGH : LOW);

  // Service one host frame if bytes are waiting.
  if (SerialBT && SerialBT.available()) {
    serviceHostFrame();
  }
}
