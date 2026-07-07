"""GEMS layer: the Lucas/SAGEM GEMS meaning on top of raw KWP services.

DTC tables, $61 live-data records, actuator tests with refusal interlocks, the
programming/coding surface, the virtual ECU state machine, and the four fault
scenarios (healthy / coolant-sensor / cylinder-3 misfire / lambda-heater OC).

NOTE ON FIDELITY: the exact GEMS K-line command bytes are not public. This layer
implements a *coherent, faithful-in-shape* dialect (KWP2000 $61/$7F records,
single-byte-style actuator commands) — a stylization, not a byte-exact clone.
See memory/research/kline-protocols.md and gems-data-catalog.md.
"""
