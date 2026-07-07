# Memory Index

- [Workflow directives](workflow-directives.md) — Always update CLAUDE.md and memory; memory stays local to this directory only
- [Tech stack decision](tech-stack-decision.md) — FINAL: Python + PySide6, Windows desktop only, wired serial, no BLE/iPhone/Android
- [Implementation status](implementation-status.md) — gems_t4 Phases 1-5 built: 93 passing tests, CLI + PySide6 GUI; INTERFACES.md / GUI_INTERFACES.md are the frozen contracts
- [Phase 5 programming](phase5-programming.md) — Security-Learn immobiliser re-sync, gated coding, read-only map lookalike; where each piece lives
- [Repo & git state](repo-git-state.md) — branch v0.0.1, NOTHING committed yet (only README.md stub); .gitignore/.gitattributes added; README.md(landing)+README.html(styled); UTF-16 gotcha
- [Pico board support](pico-board-support.md) — firmware supports Pico + Pico 2 (wired, no code diff); Pico 2 W wireless read-only mode designed but deferred, tracked in CLAUDE.md
- [GEMS P38 focus](gems-p38-focus.md) — User's vehicle is a GEMS-era P38 Range Rover (4.0/4.6 V8, 1995–98); now the representative vehicle, D2 demoted to era variation

## Research (2026-07-06 six-agent GEMS programming sweep)

- [Research SYNTHESIS](research/SYNTHESIS.md) — START HERE: two headlines (Disco2≠GEMS; GEMS not port-reflashable) + recommended build path
- [GEMS hardware](research/gems-hardware.md) — dual-CPU + two UV-EPROMs; what "programming" means; the Disco2/GEMS correction
- [GEMS data catalog](research/gems-data-catalog.md) — DTCs, ~35 live params, actuator tests, adaptations, coding, immobiliser
- [K-line protocols](research/kline-protocols.md) — ISO9141/KWP2000/Rover-native, init, services, seed-key, programming
- [Open-source tools](research/opensource-tools.md) — libcomm14cux, memsfcr, Revill MEMS3, Nanocom/Faultmate; GEMS has no open lib
- [Hardware interfaces](research/hardware-interfaces.md) — L9637D transceiver, KKL cable, J2534; build a smart MCU front-end
- [Python architecture](research/python-architecture.md) — layered transport/protocol/gems/app; udsoncan-shaped seam; virtual ECU
- [LandRoverV1 project home](landrover-v1-project-home.md) — ALWAYS save project files to C:\Users\howey\OneDrive\Documents\Claude\Projects\LandRoverV1
- [TestBook T4 emulator](testbook-t4-emulator.md) — current project: simulate the Rover T4 dealer tool UI + emulated ECU; spec of record is LandRoverV1\CLAUDE.md
- [T4 research sources](t4-research-sources.md) — Revill's MEMS3 page, the saved thread PDF in Downloads, and the 402-paywall gotcha

(On 2026-07-06 the user asked that memories from earlier chats be ignored; the old Pathfinder/CANable entries were removed from this index. Their files remain in this directory if ever needed.)
