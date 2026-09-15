"""Align disco1 vs ecu2 full page-0x18 dumps and classify records.

1. Find the global record-shift k that best aligns the two pages (disco1[r] vs
   ecu2[r+k]) — tells us if ecu2's layout is just offset from disco1's.
2. At the best shift, over records present in BOTH:
     - IDENTICAL  -> shared constant / calibration (same across ECUs)
     - DIFFER     -> ECU-specific = VIN/immobiliser/adaptive IDENTITY candidates
3. List records UNIQUE to each page (no counterpart).

  python immo_align.py
"""
from __future__ import annotations

import re
from pathlib import Path


def load(path: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        m = re.search(r"3C 18 ([0-9A-Fa-f]{2}) -> ([0-9A-Fa-f]{32})", line)
        if m:
            out[int(m.group(1), 16)] = m.group(2).upper()
    return out


d1 = load(Path.home() / "da9_sweep.log")
e2 = load(Path.home() / "ecu2_sweep.log")
print(f"disco1: {len(d1)} records   ecu2: {len(e2)} records\n")

# --- 1. best global shift --------------------------------------------------
print("shift  matched-records (disco1[r] == ecu2[r+k])")
best_k, best_n = 0, -1
for k in range(-4, 5):
    n = sum(1 for r, hx in d1.items() if e2.get(r + k) == hx)
    print(f"  {k:+d}     {n}")
    if n > best_n:
        best_k, best_n = k, n
print(f"\nbest shift = {best_k:+d}  ({best_n} identical records)\n")

# --- also: total byte-identical records anywhere (order-free) --------------
shared = set(d1.values()) & set(e2.values())
print(f"records byte-identical SOMEWHERE in both pages: {len(shared)} "
      f"(of {len(d1)}/{len(e2)})\n")

# --- 2. at best shift, classify the overlap --------------------------------
k = best_k
both = sorted(r for r in d1 if (r + k) in e2)
identical = [r for r in both if d1[r] == e2[r + k]]
differ = [r for r in both if d1[r] != e2[r + k]]
print(f"=== overlap at shift {k:+d}: {len(both)} record-pairs "
      f"({len(identical)} identical, {len(differ)} differ) ===\n")

print("DIFFERING record-pairs (ECU-specific = identity/adaptive candidates):")
print("  d1 rec / e2 rec : disco1 bytes            ecu2 bytes            (diff offsets)")
for r in differ:
    a, b = bytes.fromhex(d1[r]), bytes.fromhex(e2[r + k])
    offs = [i for i in range(16) if a[i] != b[i]]
    # skip records that are wildly different (unrelated) vs a few-byte identity delta
    tag = "  <- few-byte delta" if len(offs) <= 4 else ""
    print(f"  {r:02X} / {r+k:02X} : {d1[r]}  {e2[r+k]}  off={offs}{tag}")
