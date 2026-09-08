/*
 * pico_kline_wireless — Raspberry Pi Pico 2 W (or Pico W) K-line adapter that
 * serves the gems_t4 host protocol (../HOST_PROTOCOL.md) over BOTH WiFi/TCP AND
 * Bluetooth Classic SPP, at the same time. Use whichever suits the moment:
 *
 *   WiFi (both ends on one network / hotspot):
 *     gems_t4 kline live --connect gems-pico.local
 *     gems_t4 kline dtc  --connect 192.168.1.50
 *   Bluetooth (point-to-point; your laptop keeps its own WiFi):
 *     (pair "gems-pico" in Windows -> it makes a virtual COM port)
 *     gems_t4 kline live --port COM7
 *     python ~/pentest_scan.py   (edit PORT/host in the script)
 *
 * ONE firmware, BOTH radios. The CYW43 does WiFi + Bluetooth concurrently, and
 * the "IPv4 + Bluetooth" build (ipbtstack=ipv4btcble) turns both on. Only ONE
 * tester talks at a time (there is one K-line): whichever transport connects
 * first owns the session until it disconnects, then the other can take over.
 *
 * SUPERSET: answers every production host command (PING/INIT/SEND_RECV/
 * SET_TIMING) PLUS the pentest primitive CMD_RAW_INIT (0x05), so gems_t4 AND the
 * pentest/debug scripts all work over either transport. PING reports
 * "gems_t4-pico-wireless-pentest 2.1.0" (the "pentest" substring is REQUIRED —
 * pentest_scan.py refuses any firmware whose ping lacks it).
 *
 * The K-line timing/logic is IDENTICAL to the USB firmware — only the host
 * transport differs. Wiring (Pico <-> L9637D <-> ECU) unchanged — see ../README.md.
 *
 * BOARD: Pico 2 W / Pico W. BUILD: enable Bluetooth (which also keeps WiFi):
 *   Arduino IDE: Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth".
 *   arduino-cli: fqbn ...:rpipico2w:ipbtstack=ipv4btcble  (see ../README.md).
 *
 * SECURITY: the read-only "wireless" write gate lives on the LAPTOP, and it only
 * fires for the TCP transport (is_wireless=True). A Bluetooth SPP link reaches
 * the laptop as a *wired-looking* COM port, so writes are ALLOWED by default
 * over Bluetooth (like USB). Keep TCP on a trusted LAN; pair only trusted
 * laptops. The firmware is a dumb timed pipe either way.
 *
 * COEXISTENCE CAVEAT: the 5-baud slow init spends ~2-3 s in delay() while the
 * CYW43 services WiFi *and* BT in the background; running both radios raises
 * contention there. If a session drops mid-init, retry. If you ever see
 * flaky inits, fall back to the single-radio sketches (../pico_kline_wifi or
 * ../pico_kline_bt), which are otherwise identical.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiMulti.h>       // try several known networks, join the strongest
#include <LEAmDNS.h>         // advertise gems-pico.local
#include <SerialBT.h>        // Bluetooth Classic SPP (Serial-compatible)
#include <BluetoothLock.h>   // async_context lock required before any BTStack call
#include "wifi_secrets.h"    // <-- create from wifi_secrets.h.example

// ---- network / bluetooth config -------------------------------------------
static const uint16_t TCP_PORT = 9141;           // must match TcpTransport DEFAULT_PORT
static const char     MDNS_NAME[] = "gems-pico";  // -> gems-pico.local (WiFi)
static const char     BT_NAME[]   = "gems-pico";  // name shown when pairing (BT)
// Optional STATIC IP (leave commented for DHCP). Match your LAN.
// static IPAddress STATIC_IP(192, 168, 1, 50);
// static IPAddress STATIC_GW(192, 168, 1, 1);
// static IPAddress STATIC_MASK(255, 255, 255, 0);
// static IPAddress STATIC_DNS(192, 168, 1, 1);

WiFiServer server(TCP_PORT);
WiFiClient wifiClient;                            // active TCP tester (if any)
WiFiMulti  multi;                                 // known-network list

// Active host transport: whichever connected first. Host I/O goes through the
// Stream* so the same frame code serves TCP and Bluetooth.
enum HostKind { HOST_NONE, HOST_WIFI, HOST_BT };
static HostKind hostKind = HOST_NONE;
static Stream  *host = nullptr;

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

//   wireless 2.1.0 = pico_kline 2.0.0 K-line logic + pentest CMD_RAW_INIT, over
//   WiFi/TCP and Bluetooth SPP concurrently. Keep the "pentest" substring:
//   pentest_scan.py gates on `"pentest" in ping()` (startup + mid-sweep recovery).
static const char FW_VERSION[] = "gems_t4-pico-wireless-pentest 2.1.0";

// ---- crc8 (XOR) ------------------------------------------------------------
static uint8_t crc8(const uint8_t *buf, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; i++) c ^= buf[i];
  return c;
}

// ---- host frame I/O over the active transport (Stream*) --------------------
static void sendPico(uint8_t status, const uint8_t *payload, uint8_t len) {
  if (!host) return;
  uint8_t hdr[2] = { status, len };
  uint8_t c = crc8(hdr, 2) ^ crc8(payload, len);
  host->write(PICO_START);
  host->write(hdr, 2);
  if (len) host->write(payload, len);
  host->write(c);
  host->flush();
}

// Block until n bytes are read from the active host, or timeout; returns count.
static size_t readHost(uint8_t *buf, size_t n, uint32_t timeout_ms) {
  uint32_t start = millis();
  size_t got = 0;
  while (got < n && (millis() - start) < timeout_ms) {
    if (host && host->available()) buf[got++] = host->read();
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

// Parse and dispatch ONE host frame from the active transport (0xA5 framed).
static void serviceHostFrame() {
  if (host->read() != HOST_START) return;   // resync on stray byte

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

// ---- WiFi bring-up ---------------------------------------------------------
static void addKnownNetworks() {
#ifdef WIFI_NETWORKS
  #define X(ssid, pass) multi.addAP(ssid, pass);
  WIFI_NETWORKS
  #undef X
#else
  multi.addAP(WIFI_SSID, WIFI_PASS);
#endif
}

// Bounded connect attempt (used at boot). Non-fatal if it fails — Bluetooth
// still works, and loop() will retry WiFi in the background.
static void connectWiFi() {
  Serial.println("WiFi: connecting to the strongest known network ...");
#ifdef STATIC_IP
  WiFi.config(STATIC_IP, STATIC_DNS, STATIC_GW, STATIC_MASK);
#endif
  WiFi.setHostname(MDNS_NAME);
  uint32_t start = millis();
  while (multi.run() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK on \"");
    Serial.print(WiFi.SSID());
    Serial.print("\".  --connect ");
    Serial.print(WiFi.localIP());
    Serial.print("  (or ");
    Serial.print(MDNS_NAME);
    Serial.println(".local)");
    if (MDNS.begin(MDNS_NAME)) MDNS.addService("gems", "tcp", TCP_PORT);
  } else {
    Serial.println("WiFi not connected (Bluetooth still available). Will retry in background.");
  }
}

void setup() {
  Serial.begin(115200);              // USB debug only (optional)
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial1.setTX(KLINE_TX_PIN);
  Serial1.setRX(KLINE_RX_PIN);
  Serial1.begin(KLINE_BAUD);

  // --- WiFi ---
  addKnownNetworks();
  connectWiFi();
  server.begin();

  // --- Bluetooth SPP, headless "Just Works" pairing ---
  SerialBT.setName(BT_NAME);
  SerialBT.begin();
  {
    // NO_INPUT_NO_OUTPUT + auto-accept => Windows pairs with no PIN/passkey.
    // (Stock SerialBT advertises DISPLAY_YES_NO and never confirms the code.)
    BluetoothLock l;
    gap_ssp_set_io_capability(SSP_IO_CAPABILITY_NO_INPUT_NO_OUTPUT);
    gap_ssp_set_auto_accept(1);
  }
  Serial.print("Bluetooth SPP up as \"");
  Serial.print(BT_NAME);
  Serial.println("\" (pair it -> virtual COM port). WiFi + Bluetooth both live.");
}

// Throttled, connection-aware WiFi reconnect. Skipped while a tester is
// connected (over either radio) so a WiFi scan never interrupts a live session
// or starves Bluetooth when WiFi is simply unavailable.
static void maybeReconnectWiFi() {
  static uint32_t lastTry = 0;
  if (host) return;                             // never reconnect mid-session
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - lastTry < 15000) return;       // at most every 15 s
  lastTry = millis();
  multi.run();                                  // one attempt (brief scan)
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi reconnected on \"");
    Serial.print(WiFi.SSID());
    Serial.print("\" ");
    Serial.println(WiFi.localIP());
    if (MDNS.begin(MDNS_NAME)) MDNS.addService("gems", "tcp", TCP_PORT);
  }
}

void loop() {
  // Drop the active host if its transport went away.
  if (hostKind == HOST_WIFI && !wifiClient.connected()) {
    wifiClient.stop(); hostKind = HOST_NONE; host = nullptr;
  } else if (hostKind == HOST_BT && SerialBT.availableForWrite() == 0) {
    hostKind = HOST_NONE; host = nullptr;
  }

  // No active tester: adopt whichever transport has one waiting (BT first,
  // then a new TCP client). One tester at a time — one K-line.
  if (hostKind == HOST_NONE) {
    if (SerialBT.availableForWrite() > 0) {      // a paired client opened the SPP port
      host = &SerialBT; hostKind = HOST_BT;
      Serial.println("tester connected over Bluetooth");
    } else {
      WiFiClient incoming = server.accept();
      if (incoming) {
        wifiClient = incoming;
        wifiClient.setNoDelay(true);
        host = &wifiClient; hostKind = HOST_WIFI;
        Serial.print("tester connected over WiFi: ");
        Serial.println(wifiClient.remoteIP());
      }
    }
  }

  if (WiFi.status() == WL_CONNECTED) MDNS.update();
  maybeReconnectWiFi();

  // Solid LED = a tester is connected (either radio).
  digitalWrite(LED_BUILTIN, host ? HIGH : LOW);

  // Service one host frame if bytes are waiting.
  if (host && host->available()) {
    serviceHostFrame();
  }
}
