/*
 * pico_kline — Raspberry Pi Pico / Pico 2 K-line smart adapter for gems_t4.
 *
 * Builds unchanged for either board: only the portable Arduino API is used
 * (Serial, Serial1, pinMode, digitalWrite, delay, millis), which the
 * arduino-pico core implements identically on RP2040 (Pico) and RP2350
 * (Pico 2). Only the --fqbn build target differs between them — see
 * ../README.md "Build & flash".
 *
 * Do NOT use a Pico W / Pico 2 W with this sketch yet. The wireless (WiFi,
 * read-only) mode's LAPTOP side already exists (gems_t4 TcpTransport + serve
 * speak this same host protocol over TCP), but the Pico WiFi firmware is not
 * yet implemented — see "Pico 2 W wireless (WiFi) mode" under Tech stack →
 * Hardware in the project's CLAUDE.md.
 *
 * The Pico owns all ISO 9141 / KWP2000 K-line timing; the PC drives it with the
 * simple USB-CDC host protocol in ../HOST_PROTOCOL.md. This sketch is a timed
 * byte pipe: it performs the init handshake, transmits a KWP frame on the
 * K-line (cancelling the half-duplex self-echo), collects the response framed by
 * an inter-byte timeout, and hands the raw bytes back to the host. It never
 * interprets KWP/GEMS meaning — that lives in Python.
 *
 * Hardware: Pico or Pico 2 + MikroElektronika "ISO 9141 Click" (ST L9637D)
 * transceiver.
 *   - Serial1 TX (GP0) -> Click TX (UART -> K-line)
 *   - Serial1 RX (GP1) <- Click RX (K-line -> UART)
 *   - Click VBAT <- OBD pin 16 (+12V, FUSED); GND <- OBD pins 4/5
 *   - K-line     -> OBD pin 7
 * See ../README.md for the full wiring table and safety notes.
 */

#include <Arduino.h>

// ---- pins / config ---------------------------------------------------------
static const uint32_t KLINE_BAUD = 10400;   // ISO 9141 / KWP2000 line rate
static const uint8_t  KLINE_TX_PIN = 0;     // Serial1 TX (GP0)
static const uint8_t  KLINE_RX_PIN = 1;     // Serial1 RX (GP1)

// KWP2000 timing (milliseconds), overridable via SET_TIMING.
static uint16_t P1 = 20;    // max inter-byte time within an ECU response
static uint16_t P2 = 50;    // request-end -> response-start window (wait budget)
static uint16_t P3 = 55;    // response-end -> next-request minimum gap
static uint16_t P4 = 10;    // inter-byte time within a tester request

// ---- host protocol constants (must match HOST_PROTOCOL.md) -----------------
static const uint8_t HOST_START = 0xA5;
static const uint8_t PICO_START = 0x5A;
static const uint8_t CMD_PING = 0x01, CMD_INIT = 0x02, CMD_SEND_RECV = 0x03, CMD_SET_TIMING = 0x04;
static const uint8_t ST_OK = 0x00, ST_TIMEOUT = 0x01, ST_BUS_ERROR = 0x02, ST_BAD_REQUEST = 0x03;

static const uint16_t RESP_TIMEOUT_MS = 1000;  // overall budget for a K-line reply
static const size_t   MAX_PAYLOAD = 255;

// ---- crc8 (XOR) ------------------------------------------------------------
static uint8_t crc8(const uint8_t *buf, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; i++) c ^= buf[i];
  return c;
}

// ---- host frame I/O --------------------------------------------------------
static void sendPico(uint8_t status, const uint8_t *payload, uint8_t len) {
  uint8_t hdr[2] = { status, len };
  uint8_t c = crc8(hdr, 2) ^ crc8(payload, len);
  Serial.write(PICO_START);
  Serial.write(hdr, 2);
  if (len) Serial.write(payload, len);
  Serial.write(c);
}

// Block until n bytes are read from USB, or timeout; returns bytes read.
static size_t readHost(uint8_t *buf, size_t n, uint32_t timeout_ms) {
  uint32_t start = millis();
  size_t got = 0;
  while (got < n && (millis() - start) < timeout_ms) {
    if (Serial.available()) buf[got++] = Serial.read();
  }
  return got;
}

// ---- K-line helpers --------------------------------------------------------

// Write one byte to the K-line and consume its echo (single-wire half duplex).
static bool klineWriteByte(uint8_t b) {
  Serial1.write(b);
  uint32_t start = millis();
  while (!Serial1.available()) {
    if (millis() - start > P4 + 5) return false;  // echo never arrived
  }
  Serial1.read();  // discard the echo
  return true;
}

// Transmit a whole frame on the K-line, cancelling each echo.
static bool klineWrite(const uint8_t *frame, size_t n) {
  for (size_t i = 0; i < n; i++) {
    if (!klineWriteByte(frame[i])) return false;
    delay(P4);
  }
  return true;
}

// Read a response frame: wait up to RESP_TIMEOUT_MS for the first byte, then
// keep reading until an inter-byte gap of > P1 (frame complete).
static int klineReadFrame(uint8_t *out, size_t maxlen) {
  uint32_t start = millis();
  size_t n = 0;
  // wait for first byte
  while (!Serial1.available()) {
    if (millis() - start > RESP_TIMEOUT_MS) return -1;  // timeout
  }
  uint32_t lastByte = millis();
  while (n < maxlen) {
    if (Serial1.available()) {
      out[n++] = Serial1.read();
      lastByte = millis();
    } else if (millis() - lastByte > P1 + 2) {
      break;  // inter-byte gap => end of frame
    } else if (millis() - start > RESP_TIMEOUT_MS) {
      break;
    }
  }
  return (int)n;
}

// 5-baud slow init: bit-bang the address at 200 ms/bit on the TX line, then
// return to UART mode and read the 0x55 sync + keybytes.
static bool slowInit(uint8_t address, uint8_t *keybytes, uint8_t *kb_len) {
  Serial1.end();
  pinMode(KLINE_TX_PIN, OUTPUT);
  digitalWrite(KLINE_TX_PIN, HIGH);
  delay(300);
  // start bit (low), 8 data bits LSB-first, stop bit (high) — 200 ms each
  digitalWrite(KLINE_TX_PIN, LOW); delay(200);
  for (int i = 0; i < 8; i++) {
    digitalWrite(KLINE_TX_PIN, (address >> i) & 1);
    delay(200);
  }
  digitalWrite(KLINE_TX_PIN, HIGH); delay(200);

  Serial1.begin(KLINE_BAUD);
  uint8_t buf[8];
  int n = klineReadFrame(buf, sizeof(buf));
  if (n < 3 || buf[0] != 0x55) return false;  // expect 0x55 sync then keybytes
  keybytes[0] = buf[1];
  keybytes[1] = buf[2];
  *kb_len = 2;
  return true;
}

// Fast init: 25 ms low / 25 ms high wake pulse, then the link is live.
static bool fastInit(uint8_t *keybytes, uint8_t *kb_len) {
  Serial1.end();
  pinMode(KLINE_TX_PIN, OUTPUT);
  digitalWrite(KLINE_TX_PIN, HIGH); delay(300);
  digitalWrite(KLINE_TX_PIN, LOW);  delay(25);
  digitalWrite(KLINE_TX_PIN, HIGH); delay(25);
  Serial1.begin(KLINE_BAUD);
  keybytes[0] = 0x08; keybytes[1] = 0x08;  // conventional ISO 9141-2 keybytes
  *kb_len = 2;
  return true;
}

// ---- command handlers ------------------------------------------------------
static void handleInit(const uint8_t *payload, uint8_t len) {
  if (len < 2) { sendPico(ST_BAD_REQUEST, nullptr, 0); return; }
  uint8_t address = payload[0], mode = payload[1];
  uint8_t kb[2], kb_len = 0;
  bool ok = (mode == 1) ? fastInit(kb, &kb_len) : slowInit(address, kb, &kb_len);
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

// ---- main loop -------------------------------------------------------------
void setup() {
  Serial.begin(115200);          // USB-CDC to the host
  Serial1.setTX(KLINE_TX_PIN);
  Serial1.setRX(KLINE_RX_PIN);
  Serial1.begin(KLINE_BAUD);
}

void loop() {
  // Wait for a host frame: 0xA5 <cmd> <len> <payload> <crc8>
  if (!Serial.available()) return;
  if (Serial.read() != HOST_START) return;  // resync

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
    case CMD_PING:       { const char *v = "PICO v1"; sendPico(ST_OK, (const uint8_t *)v, 7); break; }
    case CMD_INIT:       handleInit(payload, len); break;
    case CMD_SEND_RECV:  handleSendRecv(payload, len); break;
    case CMD_SET_TIMING: handleSetTiming(payload, len); break;
    default:             sendPico(ST_BAD_REQUEST, nullptr, 0); break;
  }
}
