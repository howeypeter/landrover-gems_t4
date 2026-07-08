# Pico ↔ Host Protocol (USB-CDC)

The Pico smart adapter owns all K-line timing; the PC (Python
`gems_t4.transport.pico.PicoAdapterTransport`) drives it with this simple binary
protocol over USB-CDC serial. Both sides implement exactly this.

## Framing

```
Host -> Pico:  0xA5  <cmd>     <len>  <payload[len]>  <crc8>
Pico -> Host:  0x5A  <status>  <len>  <payload[len]>  <crc8>
```

- `0xA5` / `0x5A` are the start bytes (host / pico).
- `len` is a single byte: payload length, 0..255.
- `crc8` = XOR of every byte from the `cmd`/`status` byte through the last
  payload byte (i.e. `crc8 = cmd ^ len ^ payload[0] ^ … ^ payload[len-1]`).
- Multi-byte integers are big-endian.

## Commands (host → pico)

| cmd  | name        | payload                              | ok response payload |
|------|-------------|--------------------------------------|---------------------|
| 0x01 | PING        | —                                    | version string, e.g. `PICO v1` |
| 0x02 | INIT        | `[address][mode]` mode 0=slow,1=fast | keybytes (e.g. `08 08`) |
| 0x03 | SEND_RECV   | one complete KWP frame               | the KWP response frame |
| 0x04 | SET_TIMING  | `P1 P2 P3 P4` as 4× uint16 ms        | — |

## Status (pico → host)

| status | meaning     |
|--------|-------------|
| 0x00   | OK          |
| 0x01   | TIMEOUT (no K-line response within P2/response window) |
| 0x02   | BUS_ERROR (framing/echo/checksum problem on the wire) |
| 0x03   | BAD_REQUEST (unknown cmd or malformed host frame) |

## Worked example — SEND_RECV a TesterPresent

Host sends KWP frame `80 10 F1 01 3E C0` (TesterPresent — the trailing `C0`
is the KWP checksum: the 8-bit sum of all preceding bytes,
`80+10+F1+01+3E = 0x1C0` → `C0`):

```
A5 03 06 80 10 F1 01 3E C0 <crc8>
   |  |  \__________________/
   |  |   payload (the KWP frame, 6 bytes)
   |  len = 6
   cmd = SEND_RECV
crc8 = 03 ^ 06 ^ 80 ^ 10 ^ F1 ^ 01 ^ 3E ^ C0
```

Pico puts those bytes on the K-line (cancelling the half-duplex echo), collects
the ECU's reply framed by the P1 inter-byte timeout, and returns e.g.:

```
5A 00 06 80 F1 10 01 7E 00 <crc8>   (status OK, the 6-byte KWP response frame;
                                     80+F1+10+01+7E = 0x200 → KWP checksum 00)
```

## Notes

- The Pico is a *timed byte pipe*: it never interprets KWP service/GEMS
  semantics. All framing/decoding of the KWP frame is done in Python.
- On the K-line, every transmitted byte is echoed back (single-wire half duplex);
  the firmware reads and discards each echo before listening for the reply.
- A `SEND_RECV` whose K-line reply does not begin within the response window
  returns `TIMEOUT`; the Python side maps that to `TransportTimeout`.
