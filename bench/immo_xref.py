"""Content-based cross-reference of ecu2's block against disco1's FULL page-0x18.

The two ECUs have different PROM ids => possibly different EEPROM layouts, so a
record-by-record diff is invalid. Instead: for each ecu2 record, find where (if
anywhere) that exact 16 bytes appears in disco1's full 152-record page. Records
that match somewhere = shared/constant (calibration); records unique to ecu2 =
ECU-identity candidates (the immobiliser/security data we're hunting).

  python immo_xref.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# disco1 full page from the da9 sweep log
recs1: dict[int, str] = {}
for line in (Path.home() / "da9_sweep.log").read_text(errors="replace").splitlines():
    m = re.search(r"3C 18 ([0-9A-Fa-f]{2}) -> ([0-9A-Fa-f]{32})", line)
    if m:
        recs1[int(m.group(1), 16)] = m.group(2).upper()

ecu2 = json.loads((Path.home() / "immo_ref_ecu2.json").read_text())["block"]

# reverse index of disco1 content -> [records]
by_content: dict[str, list[int]] = {}
for rr, hx in recs1.items():
    by_content.setdefault(hx, []).append(rr)

print(f"disco1 page: {len(recs1)} records   ecu2 block: {len(ecu2)} records\n")
print("ecu2 rec | content                          | found in disco1 at")
print("-" * 74)
for rr_hex in sorted(ecu2):
    hx = ecu2[rr_hex].upper()
    hits = by_content.get(hx, [])
    where = ", ".join(f"{h:02X}" for h in hits) if hits else "*** UNIQUE (not in disco1) ***"
    asc = "".join(chr(int(hx[i:i+2], 16)) if 32 <= int(hx[i:i+2], 16) < 127 else "." for i in range(0, 32, 2))
    print(f"   {rr_hex}    | {hx} |{asc}| {where}")

# and the reverse: which disco1 immo-block records (A4,A7 / A5,A8) appear in ecu2?
print("\ndisco1 immo-block records -> present in ecu2's A3-A9?")
ecu2_contents = set(v.upper() for v in ecu2.values())
for rr in (0xA4, 0xA5, 0xA7, 0xA8):
    hx = recs1.get(rr, "").upper()
    print(f"   disco1 {rr:02X} {hx}  -> {'YES' if hx in ecu2_contents else 'no'}")
