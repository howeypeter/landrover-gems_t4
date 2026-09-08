/*
 * pico_kline_wifi — Raspberry Pi Pico 2 W (or Pico W) WiFi K-line adapter.
 *
 * Same K-line smart adapter as ../pico_kline/pico_kline.ino, but it serves the
 * gems_t4 host protocol (../HOST_PROTOCOL.md) over a **TCP socket** instead of
 * USB-CDC — so the laptop talks to it wirelessly:
 *
 *     gems_t4 kline live --connect gems-pico.local
 *     gems_t4 kline dtc  --connect 192.168.1.50
 *     gems_t4 gui        --connect 192.168.1.50   (Network mode)
 *
 * The K-line timing/logic (5-baud init + W4 handshake, fast init, echo cancel,
 * inter-byte framing) is IDENTICAL to the USB firmware — only the host transport
 * changed (Serial -> WiFiClient). The Python side is unchanged: TcpTransport
 * already speaks these 0xA5/0x5A frames.
 *
 * BOARD: **Pico 2 W** (RP2350 + CYW43) or Pico W (RP2040 + CYW43). A non-W board
 * has no WiFi radio and will not run this — use ../pico_kline for USB.
 * Build target (arduino-pico): Tools ▸ Board ▸ "Raspberry Pi Pico 2 W".
 *
 * WIFI CREDENTIALS: copy `wifi_secrets.h.example` to `wifi_secrets.h` and put
 * your SSID/password there. `wifi_secrets.h` is git-ignored so it never gets
 * committed. The rest of the wiring (Pico ↔ L9637D ↔ ECU) is unchanged — see
 * ../README.md.
 *
 * SECURITY: this is a dumb timed K-line pipe on your LAN. The write-refusal
 * ("read-only unless --allow-writes") lives on the LAPTOP (KwpClient +
 * TcpTransport.is_wireless), NOT here — so only run it on a trusted network.
 * Anything that can reach TCP :9141 can drive the K-line.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiMulti.h>        // try several known networks, join the strongest
#include <LEAmDNS.h>          // arduino-pico bundled mDNS (advertise gems-pico.local)
#include "wifi_secrets.h"    // <-- create this from wifi_secrets.h.example

// ---- network config --------------------------------------------------------
static const uint16_t TCP_PORT = 9141;          // must match TcpTransport DEFAULT_PORT
static const char     MDNS_NAME[] = "gems-pico"; // -> gems-pico.local
// Optional STATIC IP (leave commented for DHCP). Match your LAN.
// static IPAddress STATIC_IP(192, 168, 1, 50);
// static IPAddress STATIC_GW(192, 168, 1, 1);
// static IPAddress STATIC_MASK(255, 255, 255, 0);
// static IPAddress STATIC_DNS(192, 168, 1, 1);

WiFiServer server(TCP_PORT);
WiFiClient client;                              // the one active tester connection
WiFiMulti  multi;                               // holds the known-network list

// ---- pins / config (identical to the USB firmware) -------------------------
static const uint32_t KLINE_BAUD = 10400;
static const uint8_t  KLINE_TX_PIN = 0;
static const uint8_t  KLINE_RX_PIN = 1;

static uint16_t P1 = 20, P2 = 50, P3 = 55, P4 = 10;

// ---- host protocol constants (must match HOST_PROTOCOL.md) -----------------
static const uint8_t HOST_START = 0xA5;
static const uint8_t PICO_START = 0x5A;
static const uint8_t CMD_PING = 0x01, CMD_INIT = 0x02, CMD_SEND_RECV = 0x03, CMD_SET_TIMING = 0x04;
static const uint8_t ST_OK = 0x00, ST_TIMEOUT = 0x01, ST_BUS_ERROR = 0x02, ST_BAD_REQUEST = 0x03;

static const uint16_t RESP_TIMEOUT_MS = 1000;
static const size_t   MAX_PAYLOAD = 255;

//   wifi 2.0.0  = pico_kline 2.0.0 K-line logic, served over TCP/WiFi
static const char FW_VERSION[] = "gems_t4-pico-wifi 2.0.0";

// ---- crc8 (XOR) ------------------------------------------------------------
static uint8_t crc8(const uint8_t *buf, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; i++) c ^= buf[i];
  return c;
}

// ---- host frame I/O over the TCP client (was Serial in the USB firmware) ---
static void sendPico(uint8_t status, const uint8_t *payload, uint8_t len) {
  uint8_t hdr[2] = { status, len };
  uint8_t c = crc8(hdr, 2) ^ crc8(payload, len);
  if (!client || !client.connected()) return;
  client.write(PICO_START);
  client.write(hdr, 2);
  if (len) client.write(payload, len);
  client.write(c);
  client.flush();
}

// Block until n bytes are read from the client, or timeout; returns bytes read.
static size_t readHost(uint8_t *buf, size_t n, uint32_t timeout_ms) {
  uint32_t start = millis();
  size_t got = 0;
  while (got < n && (millis() - start) < timeout_ms) {
    if (client && client.available()) buf[got++] = client.read();
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

// Parse and dispatch ONE host frame from the connected client (0xA5 framed).
static void serviceHostFrame() {
  if (client.read() != HOST_START) return;   // resync on stray byte

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
    default:             sendPico(ST_BAD_REQUEST, nullptr, 0); break;
  }
}

// ---- WiFi bring-up ---------------------------------------------------------
// Register every known network (call once). WiFiMulti then joins whichever is
// in range with the strongest signal. Two source formats are supported in
// wifi_secrets.h:
//   * WIFI_NETWORKS  — an X-macro list of one or more SSID/password pairs, OR
//   * WIFI_SSID / WIFI_PASS — the original single-network pair (fallback).
static void addKnownNetworks() {
#ifdef WIFI_NETWORKS
  #define X(ssid, pass) multi.addAP(ssid, pass);
  WIFI_NETWORKS
  #undef X
#else
  multi.addAP(WIFI_SSID, WIFI_PASS);
#endif
}

static void connectWiFi() {
  Serial.println("WiFi: connecting to the strongest known network ...");
#ifdef STATIC_IP
  WiFi.config(STATIC_IP, STATIC_DNS, STATIC_GW, STATIC_MASK);
#endif
  WiFi.setHostname(MDNS_NAME);        // router shows/serves "gems-pico"
  uint32_t start = millis();
  while (multi.run() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK on \"");
    Serial.print(WiFi.SSID());        // which known network it actually joined
    Serial.print("\".  Connect the laptop with:  gems_t4 kline live --connect ");
    Serial.println(WiFi.localIP());
    Serial.print("   (or --connect ");
    Serial.print(MDNS_NAME);
    Serial.println(".local  if mDNS resolves on your PC)");
    if (MDNS.begin(MDNS_NAME)) MDNS.addService("gems", "tcp", TCP_PORT);
  } else {
    Serial.println("WiFi FAILED - check wifi_secrets.h (SSID/password), 2.4GHz band, and signal.");
  }
}

void setup() {
  Serial.begin(115200);              // USB debug only (optional; prints the IP)
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial1.setTX(KLINE_TX_PIN);
  Serial1.setRX(KLINE_RX_PIN);
  Serial1.begin(KLINE_BAUD);
  addKnownNetworks();                 // register all SSIDs once, before connecting
  connectWiFi();
  server.begin();
}

void loop() {
  // Keep WiFi up; solid LED = connected.
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_BUILTIN, LOW);
    connectWiFi();
    return;
  }
  digitalWrite(LED_BUILTIN, HIGH);
  MDNS.update();

  // Accept one tester at a time (one tester per K-line).
  if (!client || !client.connected()) {
    WiFiClient incoming = server.accept();
    if (incoming) {
      if (client) client.stop();
      client = incoming;
      client.setNoDelay(true);       // K-line frames are tiny; don't batch
      Serial.print("client connected: ");
      Serial.println(client.remoteIP());
    }
  }

  // Service one host frame if bytes are waiting.
  if (client && client.connected() && client.available()) {
    serviceHostFrame();
  }
}
