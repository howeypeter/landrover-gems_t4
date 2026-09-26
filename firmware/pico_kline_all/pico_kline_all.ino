/*
 * pico_kline_all — ONE Raspberry Pi Pico K-line adapter firmware for USB + BLE
 * + (optional) WiFi. Serves the gems_t4 host protocol (../HOST_PROTOCOL.md) over
 * whichever transport a client shows up on, so there's a single sketch to flash.
 *
 *   gems_t4 kline live            (USB auto-detect, or --port COMx)
 *   gems_t4 kline live --ble      (Bluetooth LE, no pairing/no COM port)
 *   gems_t4 kline live --connect gems-pico.local   (WiFi/TCP, if enabled)
 *
 * The K-line timing/logic (5-baud slow init + W4 handshake, fast init, echo
 * cancel, inter-byte framing) is copied VERBATIM from pico_kline 2.0.0 and is
 * IDENTICAL across all transports. Only the host byte-pipe is abstracted (see
 * the "transport layer" section) behind an "active transport" the loop selects
 * per incoming frame. Superset: also answers the pentest CMD_RAW_INIT (0x05).
 *
 * ---- BUILD ---------------------------------------------------------------
 * Toggle the transports below. USB-CDC is ALWAYS on.
 *   - Plain Pico / Pico 2 (no radio): set ENABLE_BLE 0 and ENABLE_WIFI 0.
 *       arduino-cli compile --fqbn rp2040:rp2040:rpipico   (or rpipico2)
 *   - Pico W / Pico 2 W with BLE and/or WiFi: build with the COMBINED stack:
 *       --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble
 *       (IDE: Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth")
 *   - WiFi credentials are set at RUNTIME (no file, no reflash to change): plug in
 *     USB and run   gems_t4 kline set-wifi "SSID" "password"   — stored in LittleFS,
 *     survives reflash, changeable the same way anytime. WiFi is idle until set.
 *
 * ⚠️ UNVERIFIED ON HARDWARE — concurrent BLE+WiFi on the CYW43 has to survive the
 * delay()-heavy 5-baud init (~2 s of blocking), during which the radio's async
 * context isn't pumped; a client may drop mid-init and reconnect. If BLE+WiFi
 * together prove unstable, run USB+BLE (ENABLE_WIFI 0) or USB+WiFi (ENABLE_BLE 0)
 * — the point of the toggles. Validate on a real Pico 2 W before relying on it.
 */

// ======================= TRANSPORT TOGGLES ================================
// USB-CDC is ALWAYS on and takes PRECEDENCE. BLE and WiFi are compile toggles
// (both need a Pico W / 2 W radio + the combined BT-stack build). WiFi creds are
// stored at RUNTIME in LittleFS via `set-wifi` (no file, no reflash); WiFi stays
// idle until creds exist. Transport precedence when frames arrive: USB > WiFi > BLE.
#define ENABLE_BLE   1     // Bluetooth LE (Pico W / 2 W; needs the BT stack build)
#define ENABLE_WIFI  1     // WiFi/TCP (Pico W / 2 W; set 0 on a non-radio board).
                           // Credentials live in LittleFS, set at RUNTIME with the
                           // `gems_t4 kline set-wifi` command - no wifi_secrets.h and
                           // NO reflash to change the password. WiFi stays idle until
                           // creds are stored (that's the "enable if creds exist" rule).
// ==========================================================================

#include <Arduino.h>
#if ENABLE_BLE
  #include <BLE.h>          // arduino-pico BLE (BTstack); provides BLEServiceUART
#endif
#if ENABLE_WIFI
  #include <WiFi.h>
  #include <LEAmDNS.h>
  #include <LittleFS.h>     // persistent WiFi creds (set at runtime; survive reflash)
#endif
#include "kline_transport.h"  // enum ActiveT (in a header so auto-prototypes see it)

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
static const uint8_t CMD_RAW_XFER = 0x08;   // raw send/recv, NO echo cancel (RE tool)
static const uint8_t CMD_SET_WIFI = 0x06, CMD_WIFI_STATUS = 0x07;
static const uint8_t ST_OK = 0x00, ST_TIMEOUT = 0x01, ST_BUS_ERROR = 0x02, ST_BAD_REQUEST = 0x03;
static const uint16_t RESP_TIMEOUT_MS = 1000;
static const size_t   MAX_PAYLOAD = 255;

// "pentest" substring kept so pentest_scan.py's firmware gate passes.
static const char FW_VERSION[] = "gems_t4-pico-all-pentest 3.4.0";

// ---- BLE / WiFi objects ----------------------------------------------------
#if ENABLE_BLE
static BLEServiceUART uart(256, 20);              // NUS; small txbuff => notify-safe
static const char BLE_NAME[] = "gems-pico";
static const size_t  BLE_TX_CHUNK = 16;           // <= txbuff and <= min ATT MTU payload
static const uint8_t BLE_TX_GAP_MS = 6;
#endif
#if ENABLE_WIFI
static const uint16_t TCP_PORT = 9141;
static const char     MDNS_NAME[] = "gems-pico";
static const char     WIFI_CRED_PATH[] = "/wifi.txt";   // LittleFS: line1 SSID, line2 pass
static WiFiServer server(TCP_PORT);
static WiFiClient client;
static char g_ssid[33] = {0};
static char g_pass[64] = {0};
static bool g_server_up = false;
#endif

// ---- crc8 (XOR) ------------------------------------------------------------
static uint8_t crc8(const uint8_t *buf, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; i++) c ^= buf[i];
  return c;
}

// ======================= TRANSPORT LAYER ==================================
// The loop sets g_active to whichever transport a frame arrived on; sendPico and
// readHost then operate on that transport. Handling is synchronous (one frame at
// a time), so a single active-transport selector is safe.
static ActiveT g_active = T_USB;   // enum ActiveT is declared in kline_transport.h

#if ENABLE_BLE
// BLE notifications don't fragment (they truncate to the ATT MTU), so send in
// MTU-safe chunks, pacing so each notify transmits (delay pumps the CYW43 ctx).
static void bleWrite(const uint8_t *buf, size_t len) {
  if (!uart) return;
  for (size_t off = 0; off < len; off += BLE_TX_CHUNK) {
    size_t n = (len - off < BLE_TX_CHUNK) ? (len - off) : BLE_TX_CHUNK;
    for (size_t i = 0; i < n; i++) uart.write(buf[off + i]);
    uart.flush();
    delay(BLE_TX_GAP_MS);
  }
}
#endif

static bool hostAvailable(ActiveT t) {
  switch (t) {
    case T_USB:  return Serial.available() > 0;
#if ENABLE_BLE
    case T_BLE:  return uart && uart.available();
#endif
#if ENABLE_WIFI
    case T_WIFI: return client && client.connected() && client.available();
#endif
    default:     return false;
  }
}

static int hostReadByte(ActiveT t) {              // returns byte, or -1
  switch (t) {
    case T_USB:  return Serial.read();
#if ENABLE_BLE
    case T_BLE:  return uart.read();
#endif
#if ENABLE_WIFI
    case T_WIFI: return client.read();
#endif
    default:     return -1;
  }
}

static void hostWrite(ActiveT t, const uint8_t *buf, size_t n) {
  switch (t) {
    case T_USB:  Serial.write(buf, n); Serial.flush(); break;
#if ENABLE_BLE
    case T_BLE:  bleWrite(buf, n); break;
#endif
#if ENABLE_WIFI
    case T_WIFI: if (client && client.connected()) { client.write(buf, n); client.flush(); } break;
#endif
    default: break;
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
  hostWrite(g_active, frame, n);
}

// Block until n bytes read from the active transport, or timeout; returns count.
static size_t readHost(uint8_t *buf, size_t n, uint32_t timeout_ms) {
  uint32_t start = millis();
  size_t got = 0;
  while (got < n && (millis() - start) < timeout_ms) {
    if (hostAvailable(g_active)) buf[got++] = (uint8_t)hostReadByte(g_active);
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
  while (!Serial1.available()) {
    if (millis() - start > RESP_TIMEOUT_MS) return -1;
  }
  uint32_t lastByte = millis();
  size_t n = 0;
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

static bool slowInit(uint8_t address, uint32_t baud, uint8_t *keybytes, uint8_t *kb_len) {
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

  // Session UART baud: GEMS = 10400; the Lucas 10AS alarm unit = 9600. The full
  // W4 handshake (below) must run at the module's baud, so it's a parameter now.
  Serial1.begin(baud);
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

static bool fastInit(uint8_t address, uint32_t baud, uint8_t *keybytes, uint8_t *kb_len) {
  Serial1.end();
  pinMode(KLINE_TX_PIN, OUTPUT);
  digitalWrite(KLINE_TX_PIN, HIGH); delay(300);
  digitalWrite(KLINE_TX_PIN, LOW);  delay(25);
  digitalWrite(KLINE_TX_PIN, HIGH); delay(25);
  Serial1.begin(baud);

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
  // Optional baud in payload[2..3] (big-endian). Backward-compatible: a 2-byte
  // payload (old host) defaults to KLINE_BAUD (10400, GEMS). Pass 9600 for the
  // 10AS. This is a FULL-handshake init (unlike CMD_RAW_INIT), so the addressed
  // module enters a real diagnostic session and will answer SEND_RECV.
  uint32_t baud = (len >= 4) ? (((uint32_t)payload[2] << 8) | payload[3]) : KLINE_BAUD;
  uint8_t kb[2], kb_len = 0;
  bool ok = (mode == 1) ? fastInit(address, baud, kb, &kb_len)
                        : slowInit(address, baud, kb, &kb_len);
  if (ok) sendPico(ST_OK, kb, kb_len);
  else    sendPico(ST_TIMEOUT, nullptr, 0);
}

static void handleSendRecv(const uint8_t *payload, uint8_t len) {
  if (!klineWrite(payload, len)) { sendPico(ST_BUS_ERROR, nullptr, 0); return; }
  delay(P2);
  static uint8_t resp[MAX_PAYLOAD];
  int n = klineReadFrame(resp, sizeof(resp));
  if (n < 0)  sendPico(ST_TIMEOUT, nullptr, 0);
  else        sendPico(ST_OK, resp, (uint8_t)n);
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
  if (mode == 0) {
    digitalWrite(KLINE_TX_PIN, LOW); delay(200);
    for (int i = 0; i < 8; i++) { digitalWrite(KLINE_TX_PIN, (addr >> i) & 1); delay(200); }
    digitalWrite(KLINE_TX_PIN, HIGH); delay(200);
  } else if (mode == 1) {
    digitalWrite(KLINE_TX_PIN, LOW); delay(25);
    digitalWrite(KLINE_TX_PIN, HIGH); delay(25);
  }
  Serial1.begin(baud);
  for (uint8_t i = 0; i < framelen; i++) {
    if (!klineWriteByte(frame[i])) break;
  }
  uint8_t buf[64];
  int n = klineReadRaw(buf, sizeof(buf), 500);
  sendPico(ST_OK, buf, (uint8_t)n);
}

// Raw send/recv at the CURRENT session baud, with NO echo cancellation: flush
// stale RX, transmit the frame, then collect EVERYTHING received over a fixed
// window (echo bytes first, then any ECU response) and hand it all back. The
// host separates echo (the first N = frame length) from the real response. This
// is the reverse-engineering tool for modules whose framing/echo timing we don't
// model yet (e.g. the Lucas 10AS at 9600, where the normal echo-cancelling
// SEND_RECV path returns only mangled echo). Read-only w.r.t. the sketch.
static void handleRawXfer(const uint8_t *payload, uint8_t len) {
  while (Serial1.available()) Serial1.read();          // drop stale RX
  for (uint8_t i = 0; i < len; i++) Serial1.write(payload[i]);
  Serial1.flush();                                     // wait for TX to drain
  static uint8_t buf[200];
  size_t n = 0;
  uint32_t start = millis();
  while (n < sizeof(buf) && (millis() - start) < 400) {  // fixed 400 ms capture
    if (Serial1.available()) buf[n++] = Serial1.read();
  }
  sendPico(ST_OK, buf, (uint8_t)n);
}

// Parse and dispatch ONE host frame from the ACTIVE transport (0xA5 framed).
static void serviceHostFrame() {
  if (hostReadByte(g_active) != HOST_START) return;   // resync on stray byte

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
    case CMD_RAW_XFER:   handleRawXfer(payload, len); break;
#if ENABLE_WIFI
    case CMD_SET_WIFI:    handleSetWifi(payload, len); break;
    case CMD_WIFI_STATUS: handleWifiStatus(); break;
#endif
    default:             sendPico(ST_BAD_REQUEST, nullptr, 0); break;
  }
}

#if ENABLE_WIFI
// Load creds from LittleFS (/wifi.txt: line 1 = SSID, line 2 = password).
static bool loadCreds() {
  g_ssid[0] = g_pass[0] = 0;
  File f = LittleFS.open(WIFI_CRED_PATH, "r");
  if (!f) return false;
  String s = f.readStringUntil('\n'); s.trim();
  String p = f.readStringUntil('\n'); p.trim();
  f.close();
  if (s.length() == 0) return false;
  s.toCharArray(g_ssid, sizeof(g_ssid));
  p.toCharArray(g_pass, sizeof(g_pass));
  return true;
}

static bool saveCreds(const char *ssid, const char *pass) {
  File f = LittleFS.open(WIFI_CRED_PATH, "w");
  if (!f) return false;
  f.print(ssid); f.print('\n');
  f.print(pass); f.print('\n');
  f.close();
  return true;
}

// Connect using stored creds. No creds => WiFi stays idle (that's the
// "enable WiFi only if creds exist" rule, now runtime instead of compile-time).
static void connectWiFi() {
  if (!loadCreds()) { Serial.println("WiFi: no creds stored (use `set-wifi`)."); return; }
  WiFi.setHostname(MDNS_NAME);
  WiFi.begin(g_ssid, g_pass);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) delay(300);
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK on \""); Serial.print(g_ssid);
    Serial.print("\", --connect "); Serial.println(WiFi.localIP());
    if (MDNS.begin(MDNS_NAME)) MDNS.addService("gems", "tcp", TCP_PORT);
    if (!g_server_up) { server.begin(); g_server_up = true; }
  } else {
    Serial.println("WiFi FAILED - check SSID/password (set-wifi), 2.4GHz band, signal.");
  }
}

// CMD_SET_WIFI payload: [ssidLen][ssid bytes...][password bytes...].
// Persists to LittleFS and reconnects - no reflash needed to change the password.
static void handleSetWifi(const uint8_t *payload, uint8_t len) {
  if (len < 1) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }
  uint8_t sl = payload[0];
  if ((uint16_t)1 + sl > len || sl >= sizeof(g_ssid)) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }
  char ssid[33] = {0}, pass[64] = {0};
  memcpy(ssid, payload + 1, sl);
  uint8_t pl = (uint8_t)(len - 1 - sl);
  if (pl >= sizeof(pass)) pl = sizeof(pass) - 1;
  memcpy(pass, payload + 1 + sl, pl);
  if (!saveCreds(ssid, pass)) { sendPico(ST_BUS_ERROR, nullptr, 0); return; }
  // ACK the SAVE immediately: connectWiFi() blocks up to 20 s, which exceeds the
  // host's ~6 s frame timeout and made set-wifi falsely report "no response"
  // even though the creds saved and the join succeeded. ST_OK means "saved";
  // the actual join happens next and is reported by `wifi-status`.
  sendPico(ST_OK, nullptr, 0);
  connectWiFi();
}

static void handleWifiStatus() {
  char buf[96];
  // MAC is always reported so a client can set a DHCP reservation without
  // digging through the router. SSID is LAST because it can contain spaces;
  // the MAC (fixed 17 chars, no spaces) sits before it so parsing stays
  // unambiguous. Formats:
  //   connected <ip> <mac> <ssid>
  //   offline <mac> (creds set: <ssid>)
  //   no-creds <mac>
  uint8_t mac[6] = {0};
  WiFi.macAddress(mac);
  char macs[18];
  snprintf(macs, sizeof(macs), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  if (WiFi.status() == WL_CONNECTED) {
    IPAddress ip = WiFi.localIP();
    snprintf(buf, sizeof(buf), "connected %u.%u.%u.%u %s %s",
             ip[0], ip[1], ip[2], ip[3], macs, g_ssid);
  } else if (g_ssid[0]) {
    snprintf(buf, sizeof(buf), "offline %s (creds set: %s)", macs, g_ssid);
  } else {
    snprintf(buf, sizeof(buf), "no-creds %s", macs);
  }
  sendPico(ST_OK, (const uint8_t *)buf, (uint8_t)strlen(buf));
}
#endif

void setup() {
  Serial.begin(115200);              // USB-CDC host transport (always on)
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial1.setTX(KLINE_TX_PIN);
  Serial1.setRX(KLINE_RX_PIN);
  Serial1.begin(KLINE_BAUD);

#if ENABLE_BLE
  BLE.begin(BLE_NAME);
  BLE.server()->addService(&uart);
  BLE.startAdvertising(false);       // advertise the FULL name (we scan by name)
  uart.setAutoflush(30);
  Serial.println("BLE NUS up as \"gems-pico\" (--ble)");
#endif
#if ENABLE_WIFI
  LittleFS.begin();
  connectWiFi();                    // uses creds from LittleFS; none -> WiFi idle
#endif
  Serial.println("pico_kline_all ready: USB always"
#if ENABLE_BLE
                 " + BLE"
#endif
#if ENABLE_WIFI
                 " + WiFi"
#endif
                 );
}

void loop() {
#if ENABLE_WIFI
  // Keep WiFi up. SINGLE client, LAST-connection-wins: always check for a NEW
  // connection and let it TAKE OVER, dropping any previous/stale one. This fixes
  // the old first-wins lockout, where once a client was connected a second
  // tester's socket was accepted by the TCP stack but never serviced (silent
  // hangs / intermittent failures), and a half-closed connection held the slot
  // forever. A healthy lone client is untouched - accept() only yields a client
  // when a genuinely new connection arrives - so a fresh `kline`/portal connect
  // cleanly takes over from a dead one instead of fighting it.
  if (WiFi.status() == WL_CONNECTED) {
    MDNS.update();
    WiFiClient incoming = server.accept();
    if (incoming) {
      if (client) client.stop();        // drop the previous / stale tester
      client = incoming;
      client.setNoDelay(true);
    }
  }
#endif

  // LED: SOLID when a wireless client is connected; a slow HEARTBEAT blink
  // (~100 ms every 1 s) when idle so you can see the firmware is alive - USB has
  // no "connected" state, so this is your "it booted and is running" signal.
  // Only write on change (the Pico W LED is driven via the CYW43 - don't spam it).
  bool linked = false;
#if ENABLE_BLE
  linked = linked || (bool)uart;
#endif
#if ENABLE_WIFI
  linked = linked || (client && client.connected());
#endif
  bool want = linked ? true : ((millis() % 1000) < 100);
  static bool led_on = false;
  if (want != led_on) { led_on = want; digitalWrite(LED_BUILTIN, want ? HIGH : LOW); }

  // Service one frame from whichever transport has bytes waiting.
  // PRECEDENCE: USB > WiFi > BLE.
  if (Serial.available() > 0) {
    g_active = T_USB;  serviceHostFrame();
  }
#if ENABLE_WIFI
  else if (client && client.connected() && client.available()) {
    g_active = T_WIFI; serviceHostFrame();
  }
#endif
#if ENABLE_BLE
  else if (uart && uart.available()) {
    g_active = T_BLE;  serviceHostFrame();
  }
#endif
}
