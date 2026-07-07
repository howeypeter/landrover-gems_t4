---
name: gems-p38-focus
description: User owns a GEMS-era P38 Range Rover — the project's representative vehicle and research focus (was Discovery 2 Td5)
metadata:
  type: project
---

On 2026-07-06 the user said they have a **Land Rover with GEMS engine
management** and that this is what they want to research. Later the same day they
described it as a **"Discovery 2 petrol with GEMS"** — but research shows that
combination cannot exist: **GEMS was P38 (1995–early99) + Discovery SERIES I V8i
(1996–early99) + Defender 90 NAS (97); the Discovery 2 petrol V8 was always Bosch
Motronic "Thor," never GEMS.** So the actual vehicle is a **P38 or a Discovery 1**
(or a Thor Disco 2 mislabelled). **UNRESOLVED — confirm with the user.** Docs and
CLAUDE.md currently centre on the P38 as the representative GEMS platform. See
[[research-gems-hardware]] for the full correction.

Docs and CLAUDE.md were rewritten around the P38: BeCM-centric body
electronics, EAS air suspension, message centre, "ENGINE IMMOBILISED" sync
fault as a canon failure mode. Discovery 2 Td5 demoted to an era variation.

**Done**: Consolidated two old Discovery 2 diagrams into a single
`p38-gems-network.svg` showing both the diagnostic K-line star and point-to-point
wiring (BeCM-centric). Old `d2-*` diagrams deleted on 2026-07-06.

**Validated on 2026-07-06**: Diagram reviewed by three independent agents:
- **Rendering agent**: Confirmed SVG renders correctly; identified and fixed two arrow alignment issues (ABS speed signal, EAS fault routing)
- **Component accuracy agent**: All 8 ECUs present, correctly named, functions accurately described, BeCM hub status correct
- **Connection topology agent**: K-line star verified, all major inter-module connections accurate (torque reduction, immobiliser, message centre, outstations, EAS faults)

Final status: Visually excellent, functionally accurate, ready for use.

**Isolation clarity added on 2026-07-06**: Diagram rewritten to visually distinguish:
- **Integrated real-time coordination network** (grouped in box): GEMS, EAT, ABS, EAS, BeCM hub, Instruments, door outstations with their point-to-point wires
- **Isolated systems** (outside box, dashed borders): SRS (K-line diagnostics only, safety-critical), HEVAC (K-line + simple analogue 12V signals)
- Makes clear that SRS doesn't coordinate with other systems and HEVAC has minimal integration

**Still pending**: Deeper GEMS research (fault code tables, live-data parameter
list, actuator test set — RAVE manual is the authoritative source). Note Revill's
$61/$7f byte-level detail is MEMS3, not GEMS — emulator protocol is a stylization
for now.

Related: [[testbook-t4-emulator]], [[workflow-directives]]
