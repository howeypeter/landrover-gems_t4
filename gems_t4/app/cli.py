"""gems_t4 command-line interface — the dev/hacking bench.

Everything runs against the in-memory virtual ECU with ``--fake`` (the default),
so the whole tool works with no car and no adapter. A ``--port COMx`` selects the
Pico adapter instead.

Run as ``python -m gems_t4 <command>`` (or the installed ``gems_t4`` command).

Examples::

    python -m gems_t4 scenarios
    python -m gems_t4 live --scenario coolant_sensor
    python -m gems_t4 dtc read --scenario misfire_cyl3
    python -m gems_t4 dtc clear --scenario misfire_cyl3
    python -m gems_t4 actuator fuel_pump --state on
"""
from __future__ import annotations

import argparse
import os
import sys

from gems_t4 import __version__
from gems_t4.app import render
from gems_t4.app.backend import Backend
from gems_t4.gems import actuators, programming
from gems_t4.gems.scenarios import SCENARIOS, get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import WirelessWriteRefused
from gems_t4.transport.tcp import parse_endpoint
from gems_t4.transport.virtual import VirtualTransport


def _backend_from_args(args: argparse.Namespace) -> Backend:
    """Build a **connected** :class:`Backend` for the KWP-stylized commands.

    Single seam shared with the GUI: the Backend owns transport construction
    (virtual ECU by default, a USB Pico with ``--port``, or a TCP endpoint with
    ``--connect``). These commands (live/dtc/actuator/coding/immo) speak the
    KWP-stylized stack — the *real*-GEMS K-line profile is the separate ``kline``
    command — so we force ``real_ecu=False`` on remote connections. Caller must
    ``backend.disconnect()`` when done.
    """
    port = getattr(args, "port", None)
    connect = getattr(args, "connect", None)
    if port and connect:
        raise SystemExit("choose --port (USB) or --connect (network), not both")
    backend = Backend(
        getattr(args, "scenario", "healthy"),
        immobilised=getattr(args, "immobilised", False),
        latency=getattr(args, "latency", 0.0),
    )
    if port:
        backend.apply_connection("usb", com_port=port, real_ecu=False)
    elif connect:
        host, tcp_port = parse_endpoint(connect)
        backend.apply_connection(
            "network", host=host, tcp_port=tcp_port,
            allow_writes=getattr(args, "allow_writes", False), real_ecu=False,
        )
    else:
        backend.connect()
        for _ in range(5):  # warm the sim (warm-up curve / idle hunt) like before
            backend.tick(0.1)
    return backend


def _source_label(args: argparse.Namespace) -> str:
    """Where the data comes from, for table titles."""
    if getattr(args, "port", None):
        return f"USB {args.port}"
    if getattr(args, "connect", None):
        return args.connect
    return f"scenario '{args.scenario}'"


def _prompt_yes_no(prompt: str) -> bool:
    """Interactive ``[y/N]`` confirmation. Only 'y'/'yes' confirms.

    EOF (a non-interactive/empty stdin) is treated as "no" so a scripted run
    never blocks or silently proceeds. Tolerates the UTF-8 BOM PowerShell
    prepends when piping (``echo y | ...``), seen as U+FEFF (utf-8 stdin) or
    ``\\xef\\xbb\\xbf`` (cp1252).
    """
    try:
        reply = input(prompt)
    except EOFError:
        return False
    reply = reply.lstrip("﻿\xef\xbb\xbf").strip().lower()
    return reply in ("y", "yes")


def _cmd_scenarios(args: argparse.Namespace) -> int:
    render.console.print("[bold]Available fault scenarios:[/]")
    for name in SCENARIOS:
        render.console.print(f"  - {name}")
    return 0


def _cmd_live(args: argparse.Namespace) -> int:
    render.communicating()
    backend = _backend_from_args(args)
    try:
        ids = [int(x, 0) for x in args.ids] if args.ids else None
        measures = backend.read_live(ids)
    finally:
        backend.disconnect()
    render.print_live(measures, title=f"Live data - {_source_label(args)}")
    return 0


def _cmd_dtc(args: argparse.Namespace) -> int:
    # Clearing fault codes is destructive; confirm before touching the ECU
    # (unless --yes). The confirmation is asked up front so a declined clear
    # never opens a session.
    if args.dtc_action == "clear" and not args.yes and not _prompt_yes_no(
        "Clear all stored fault codes? [y/N] "
    ):
        render.console.print("Clear cancelled.")
        return 1
    render.communicating()
    backend = _backend_from_args(args)
    try:
        if args.dtc_action == "clear":
            backend.clear_dtcs()
            render.console.print("[green]Fault codes cleared.[/]")
            return 0
        dtcs = backend.read_dtcs()
    finally:
        backend.disconnect()
    render.print_dtcs(dtcs, title=f"Fault codes - {_source_label(args)}")
    return 0


def _cmd_gui(args: argparse.Namespace) -> int:
    if getattr(args, "instant", False):
        # Disable "the waiting" (the ECU-communication overlay's minimum
        # display time) for impatient users - see gems_t4/app/gui/wait.py.
        os.environ["GEMS_T4_INSTANT"] = "1"
    if sum(bool(getattr(args, x, None)) for x in ("port", "connect", "ble")) > 1:
        render.console.print(
            "[red]choose ONE of --port (USB), --connect (network), or --ble[/]"
        )
        return 2
    try:
        from gems_t4.app.gui.app import run
    except ImportError:
        render.console.print(
            "[red]PySide6 is not installed.[/] Install the GUI extra: "
            "pip install -e \".[gui]\""
        )
        return 2
    return run(
        scenario=args.scenario,
        port=args.port,
        connect=args.connect,
        ble=getattr(args, "ble", None),
        allow_writes=args.allow_writes,
    )


def _cmd_serve(args: argparse.Namespace) -> int:
    """Serve the host protocol over TCP — virtual ECU or USB-Pico bridge."""
    from gems_t4.app.server import TcpFrameServer, run_serial_bridge

    try:
        listen_host, listen_port = parse_endpoint(args.listen)
    except ValueError as exc:
        render.console.print(f"[red]{exc}[/]")
        return 2

    log = lambda msg: render.console.print(f"[dim]{msg}[/]")  # noqa: E731

    if args.port:
        render.console.print(
            f"[bold]Bridging USB Pico on {args.port}[/] at "
            f"{listen_host}:{listen_port} - Ctrl+C to stop."
        )
        try:
            run_serial_bridge(
                args.port, host=listen_host, port=listen_port, log=log
            )
        except KeyboardInterrupt:
            render.console.print("Stopped.")
        return 0

    ecu = VirtualEcu(
        get_scenario(args.scenario), immobilised=args.immobilised
    )
    server = TcpFrameServer(
        VirtualTransport(ecu, latency=args.latency),
        host=listen_host,
        port=listen_port,
        on_exchange=ecu.tick,
        log=log,
    )
    host, port = server.address
    render.console.print(
        f"[bold]Serving virtual GEMS ECU[/] (scenario '{args.scenario}') at "
        f"{host}:{port} - Ctrl+C to stop."
    )
    if listen_host == "127.0.0.1":
        render.console.print(
            "[dim]Localhost only. Use --listen 0.0.0.0:9141 to allow other "
            "machines on your network.[/]"
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        render.console.print("Stopped.")
    finally:
        server.stop()
    return 0


def _cmd_actuator(args: argparse.Namespace) -> int:
    state = actuators.STATE_ON if args.state == "on" else actuators.STATE_OFF
    try:
        act = actuators.by_name(args.name)
    except KeyError as exc:
        render.console.print(f"[red]{exc}[/]")
        return 2
    render.communicating()
    backend = _backend_from_args(args)
    try:
        outcome = backend.run_actuator(act.actuator_id, state)
    finally:
        backend.disconnect()
    render.print_actuator(outcome)
    return 0 if outcome.ok else 1


def _cmd_coding(args: argparse.Namespace) -> int:
    from rich.table import Table

    render.communicating()
    backend = _backend_from_args(args)
    try:
        if args.coding_action == "write":
            if not args.field or args.value is None:
                render.console.print("[red]coding write needs --field and --value[/]")
                return 2
            try:
                value = backend.encode_coding_text(args.field, args.value)
                backup = backend.backup_coding(args.field)

                def _confirm() -> bool:
                    if args.yes:
                        return True
                    field = programming.CODING_FIELDS[args.field]
                    old = programming.decode_field(args.field, backup.data)
                    return _prompt_yes_no(
                        f"Write {field.name}: '{old}' -> '{args.value}'? [y/N] "
                    )

                result = backend.write_coding(
                    args.field, value, backup=backup, confirm=_confirm
                )
            except (KeyError, ValueError, programming.ProgrammingRefused) as exc:
                render.console.print(f"[red]{exc}[/]")
                return 1
            style = "green" if result.ok else "bold red"
            render.console.print(f"[{style}]{result.message}[/]")
            return 0 if result.ok else 1

        # read
        table = Table(title="GEMS coding block", header_style="bold cyan")
        table.add_column("Field"); table.add_column("Value"); table.add_column("Writable")
        for f in backend.coding_fields():
            table.add_row(f.name, backend.read_coding_text(f.key),
                          "yes" if f.writable else "no")
        render.console.print(table)
        return 0
    finally:
        backend.disconnect()


def _cmd_immo(args: argparse.Namespace) -> int:
    render.communicating()
    backend = _backend_from_args(args)
    try:
        if args.immo_action == "learn":
            result = backend.security_learn(
                on_progress=lambda s: render.console.print(f"  [dim]{s}[/]")
            )
            style = "green" if result.ok else "bold red"
            render.console.print(f"[{style}]{result.message}[/]")
            return 0 if result.ok else 1
        status = backend.immobiliser_status()
        colour = "green" if status.mobilised else "bold red"
        render.console.print(f"Immobiliser: [{colour}]{status.summary}[/]")
        return 0
    finally:
        backend.disconnect()


def _kline_connection_spec(args: argparse.Namespace) -> tuple[str, dict]:
    """Map --port/--connect/--ble to a ``Backend.apply_connection`` (kind, kwargs).

    Single source of truth for how the real-ECU CLI reaches the adapter — the
    ``Backend`` then builds the transport, and the GUI uses that same seam. No
    transport is constructed here (that lives only in ``Backend``).
    """
    port = getattr(args, "port", None)
    connect = getattr(args, "connect", None)
    ble = getattr(args, "ble", None)
    if sum(bool(x) for x in (port, connect, ble)) > 1:
        raise SystemExit(
            "choose ONE of --port (USB), --connect (network), or --ble (Bluetooth LE)"
        )
    if port:
        return "usb", {"com_port": port}
    if connect:
        host, tcp_port = parse_endpoint(connect)
        return "network", {"host": host, "tcp_port": tcp_port,
                           "allow_writes": getattr(args, "allow_writes", False)}
    if ble:
        return "ble", {"device": ble}
    raise SystemExit(
        "kline talks to a REAL ECU: pass --port COMx (bench/on-car adapter), "
        "--connect HOST[:PORT] (WiFi), or --ble [NAME] (Bluetooth LE). "
        "It does not use the virtual ECU."
    )


def _kline_live_table(rows, source: str):
    from rich.table import Table

    table = Table(title=f"K-line live data - {source}")
    table.add_column("PID", style="dim")
    table.add_column("Parameter")
    table.add_column("Value", justify="right")
    table.add_column("Unit", style="dim")
    for row in rows:
        pid = row.raw if isinstance(row.raw, int) else 0
        table.add_row(f"0x{pid:02X}", row.name, str(row.value), row.unit)
    return table


def _run_kline_secure(args: argparse.Namespace, backend, kind: str, kwargs: dict) -> int:
    """`kline secure`: the proprietary 0xDA SecurityAccess channel (bench, K+L).

    Unlocks with the recovered $27 key, then (by default) reads coding. Optional
    ``--dump ADDR:LEN`` does a single 0x3C read (LEN 1..3F; 0x3C addressing is not
    linear on this ECU, so it's one record, not a range); ``--reset-adaptive`` /
    ``--immobiliser-synch`` run the two known writes (with confirmation). Needs
    the ECU's L-line tied to the K node — this is a bench capability, not on-car.
    """
    from gems_t4.protocol.gems_secure import GemsSecureError
    from gems_t4.protocol.kline import connect_help
    from gems_t4.transport.base import TransportError

    try:
        # Register the transport WITHOUT the OBD 0x33 connect; the secure session
        # does its own 5-baud init at 0xDA.
        backend.set_connection(kind, real_ecu=True, **kwargs)
        session = backend.secure_session()
    except (TransportError, OSError, ValueError) as exc:
        render.console.print(f"[bold red]{exc}[/]")
        return 1

    render.communicating()
    try:
        session.connect()
    except (TransportError, OSError) as exc:
        render.console.print("[bold red]Could not open the 0xDA channel.[/]")
        render.console.print(connect_help(exc, kind=kind))
        return 1

    try:
        if not session.unlock():
            render.console.print(
                "[bold red]$27 unlock FAILED[/] (no 6702AA). Check the L-line is "
                "tied to the K node and the ECU is powered; power-cycle if it may "
                "be in $27 lockout."
            )
            return 1
        seed = session.last_seed or 0
        render.console.print(f"[green]Unlocked ($27) — seed {seed:04X}.[/]")

        did_action = False
        if getattr(args, "reset_adaptive", False):
            did_action = True
            if args.yes or _prompt_yes_no("Reset ECU adaptive values? [y/N] "):
                session.reset_adaptive_values()
                render.console.print("[green]Reset-adaptive-values sent.[/]")
            else:
                render.console.print("Reset cancelled.")
        if getattr(args, "immobiliser_synch", False):
            did_action = True
            render.console.print(
                "[yellow]Immobiliser synch (Security-Learn) mutates BeCM<->ECM "
                "pairing.[/]"
            )
            if args.yes or _prompt_yes_no("Send immobiliser synch? [y/N] "):
                session.immobiliser_synch()
                render.console.print("[green]Immobiliser-synch sent.[/]")
            else:
                render.console.print("Immobiliser synch cancelled.")
        if getattr(args, "dump", None):
            did_action = True
            try:
                addr_s, len_s = args.dump.split(":", 1)
                addr, length = int(addr_s, 16), int(len_s, 16)
            except ValueError:
                render.console.print("[red]--dump wants ADDR:LEN in hex, e.g. 1800:10[/]")
                return 2
            if not 1 <= length <= 0x3F:
                render.console.print(
                    "[red]LEN must be 1..3F (a single 0x3C read). 0x3C addressing "
                    "is NOT linear on this ECU, so a multi-read 'dump' is meaningless "
                    "— read one record at a time.[/]"
                )
                return 2
            data = session.read_at(addr, length)
            if data:
                render.console.print(
                    f"[bold]0x3C read @0x{addr:04X} ({len(data)} B):[/] {data.hex().upper()}"
                )
            else:
                render.console.print(
                    "[yellow]No data (0x3C returned negative/silent/short).[/]"
                )

        if getattr(args, "immo", False):
            did_action = True
            block = session.read_immobiliser_block()
            render.console.print("[bold]Immobiliser/security block (page 0x18, A4-A8):[/]")
            for rec in sorted(block):
                render.console.print(f"  {rec:02X}  {block[rec].hex().upper()}")
            a4, a7 = block.get(0xA4), block.get(0xA7)
            if a4 is not None and a7 is not None:
                match = "identical (copies agree)" if a4 == a7 else "DIFFER (copies disagree!)"
                render.console.print(f"  copies A4/A7: [cyan]{match}[/]")
            render.console.print(
                "[dim]byte meanings not yet decoded — this is the raw block.[/]"
            )

        if not did_action:
            # default: read coding
            from rich.table import Table
            t = Table(title="GEMS coding (0xDA, authorized)", header_style="bold cyan")
            t.add_column("Field"); t.add_column("Value")
            prom = session.read_prom_id()
            cfg = session.read_config()
            vin = session.read_vin_last6()
            t.add_row("PROM ID", prom or "—")
            if cfg:
                t.add_row("Displacement", cfg.displacement + " L")
                t.add_row("Transmission", cfg.transmission)
                t.add_row("Config byte", f"0x{cfg.raw:02X}")
            t.add_row("VIN (last 6)", vin or "unavailable on this ECU")
            render.console.print(t)
        return 0
    except GemsSecureError as exc:
        render.console.print(f"[bold red]secure channel error:[/] {exc}")
        return 1
    finally:
        session.close()


def _cmd_kline(args: argparse.Namespace) -> int:
    """Talk to a REAL ECU over ISO 9141-2 / OBD-II (bench or on-car).

    This is the confirmed, hardware-tested protocol (5-baud init at 0x33), as
    opposed to the KWP-stylized virtual ECU used by the other commands.
    """
    from gems_t4.app.backend import Backend
    from gems_t4.gems.types import DtcState
    from gems_t4.protocol.kline import connect_help
    from gems_t4.transport.base import TransportError

    kind, kwargs = _kline_connection_spec(args)
    backend = Backend()
    if args.kline_action == "secure":
        return _run_kline_secure(args, backend, kind, kwargs)
    render.communicating()
    try:
        # kline is the REAL-ECU command: force the K-line profile over any
        # transport (USB, a WiFi Pico via --connect, or BLE).
        source = backend.apply_connection(kind, real_ecu=True, **kwargs)
    except (TransportError, OSError) as exc:
        render.console.print("[bold red]Could not connect to the ECU.[/]")
        render.console.print(connect_help(exc, kind=kind))
        return 1
    try:
        if args.kline_action == "dtc":
            dtcs = backend.read_dtcs()
            stored = [d for d in dtcs if d.state == DtcState.STORED]
            pending = [d for d in dtcs if d.state == DtcState.PENDING]
            if stored:
                render.console.print(f"[bold]Stored (confirmed) codes - {source}:[/]")
                for d in stored:
                    render.console.print(f"  [red]{d.code}[/]")
            else:
                render.console.print(f"No stored (confirmed) codes - {source}.")
            if pending:
                render.console.print(f"[bold]Pending codes - {source}:[/]")
                for d in pending:
                    render.console.print(f"  [yellow]{d.code}[/]")
            else:
                render.console.print("No pending codes.")
            return 0

        if args.kline_action == "vin":
            vin = backend.read_vin()
            if vin:
                render.console.print(f"[bold]VIN - {source}:[/] {vin}")
                if len(vin) != 17:
                    render.console.print(
                        f"[yellow](got {len(vin)} chars, not the usual 17)[/]"
                    )
            else:
                render.console.print(
                    f"No VIN from {source}. The GEMS engine ECU may not support "
                    "OBD-II Service 09 (early ISO 9141-2). The full VIN, if held "
                    "electronically at all, lives in the body/security module "
                    "(P38 BeCM / Discovery 1 Lucas 10AS), not the engine ECU."
                )
            return 0

        if args.kline_action == "clear":
            if not getattr(args, "yes", False) and not _prompt_yes_no(
                "Clear fault codes and reset readiness monitors? [y/N] "
            ):
                render.console.print("Clear cancelled.")
                return 1
            before = [d.code for d in backend.read_dtcs()]
            ok = backend.clear_dtcs()
            state = "accepted" if ok else "sent (no positive echo)"
            render.console.print(f"[green]Clear command {state} - {source}.[/]")
            render.console.print(f"Codes before clear: {', '.join(before) or 'none'}.")
            # The GEMS ECU reboots after a Mode 04 clear: it drops the session
            # and goes unresponsive for a minute or two, then recovers on its
            # own (cycling the ignition can force it). Drop the session so the
            # next read re-inits, and tell the operator what to do next.
            backend.disconnect()
            render.console.print(
                "[yellow]The GEMS ECU goes quiet for a minute or two after a "
                "clear (it reboots its diagnostics) — wait for it to come back "
                "(or cycle the ignition), then run 'kline dtc' to confirm.[/]"
            )
            return 0

        if args.kline_action == "monitor":
            import time

            from rich.live import Live

            render.console.print(
                f"[dim]K-line live monitor - {source}. Ctrl+C to stop.[/]"
            )
            try:
                with Live(_kline_live_table(backend.read_live(), source),
                          console=render.console, refresh_per_second=4) as live:
                    while True:
                        live.update(_kline_live_table(backend.read_live(), source))
                        time.sleep(0.2)
            except KeyboardInterrupt:
                render.console.print("stopped.")
            return 0

        # live (one-shot)
        table = _kline_live_table(backend.read_live(), source)
        render.console.print(table)
        if table.row_count == 0:
            render.console.print("[yellow]No live PIDs returned by the ECU.[/]")
        return 0
    finally:
        backend.disconnect()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gems_t4",
        description="T4-style diagnostic tool for the Lucas/SAGEM GEMS V8 ECU.",
    )
    parser.add_argument("--version", action="version", version=f"gems_t4 {__version__}")

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--fake", action="store_true", default=True,
                        help="use the virtual ECU (default)")
        sp.add_argument("--port", help="serial port of the Pico adapter (e.g. COM3)")
        sp.add_argument("--connect", metavar="HOST[:PORT]",
                        help="TCP endpoint (gems_t4 serve bridge or WiFi Pico); "
                             "default port 9141")
        sp.add_argument("--allow-writes", action="store_true",
                        help="permit coding/actuator/Security-Learn writes over "
                             "--connect (default: network is read-only)")
        sp.add_argument("--scenario", default="healthy",
                        choices=sorted(SCENARIOS), help="fault scenario for --fake")
        sp.add_argument("--latency", type=float, default=0.0,
                        help="modeled per-exchange latency in seconds")

    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("scenarios", help="list fault scenarios")
    sp.set_defaults(func=_cmd_scenarios)

    sp = sub.add_parser("live", help="read live data")
    add_common(sp)
    sp.add_argument("--ids", nargs="*", help="specific local ids (e.g. 0x01 0x02)")
    sp.set_defaults(func=_cmd_live)

    sp = sub.add_parser("dtc", help="read or clear fault codes")
    add_common(sp)
    sp.add_argument("dtc_action", choices=["read", "clear"], help="read or clear")
    sp.add_argument("--yes", "-y", action="store_true",
                    help="skip the confirmation prompt when clearing")
    sp.set_defaults(func=_cmd_dtc)

    sp = sub.add_parser("actuator", help="run an actuator test")
    add_common(sp)
    sp.add_argument("name", help="actuator token (mil, o2_heater, fuel_pump, ...)")
    sp.add_argument("--state", choices=["on", "off"], default="on")
    sp.set_defaults(func=_cmd_actuator)

    sp = sub.add_parser("coding", help="read or write ECU coding fields (gated)")
    add_common(sp)
    sp.add_argument("coding_action", choices=["read", "write"])
    sp.add_argument("--field", help="coding field key (e.g. vin_last6)")
    sp.add_argument("--value", help="new value (ASCII for vin/part, else hex)")
    sp.add_argument("--yes", "-y", action="store_true",
                    help="skip the interactive write confirmation prompt")
    sp.set_defaults(func=_cmd_coding)

    sp = sub.add_parser("immo", help="immobiliser status / Security-Learn re-sync")
    add_common(sp)
    sp.add_argument("immo_action", choices=["status", "learn"])
    sp.add_argument("--immobilised", action="store_true",
                    help="start the virtual ECU desynced (ENGINE IMMOBILISED)")
    sp.set_defaults(func=_cmd_immo)

    sp = sub.add_parser("gui", help="launch the PySide6 Win98 kiosk GUI")
    sp.add_argument("--scenario", default="healthy",
                    choices=sorted(SCENARIOS), help="initial fault scenario")
    sp.add_argument("--instant", action="store_true",
                    help="skip the 'Communicating with ECU' waits "
                         "(sets GEMS_T4_INSTANT=1)")
    sp.add_argument("--port", help="start connected to the USB Pico adapter "
                                   "(e.g. COM3)")
    sp.add_argument("--connect", metavar="HOST[:PORT]",
                    help="start connected to a TCP endpoint (default port 9141)")
    sp.add_argument("--ble", nargs="?", const="gems-pico", metavar="NAME|ADDR",
                    help="start connected to a Bluetooth LE adapter (NUS); optional "
                         "device name/address (default: gems-pico)")
    sp.add_argument("--allow-writes", action="store_true",
                    help="permit write functions over --connect")
    sp.set_defaults(func=_cmd_gui)

    sp = sub.add_parser(
        "serve",
        help="serve the ECU over TCP (virtual ECU, or bridge a USB Pico)",
    )
    sp.add_argument("--listen", metavar="HOST[:PORT]", default="127.0.0.1:9141",
                    help="listen address (default 127.0.0.1:9141; use "
                         "0.0.0.0:9141 to allow the LAN)")
    sp.add_argument("--scenario", default="healthy",
                    choices=sorted(SCENARIOS),
                    help="fault scenario for the virtual ECU")
    sp.add_argument("--immobilised", action="store_true",
                    help="start the virtual ECU desynced (ENGINE IMMOBILISED)")
    sp.add_argument("--latency", type=float, default=0.0,
                    help="modeled per-exchange latency in seconds")
    sp.add_argument("--port",
                    help="bridge the USB Pico adapter on this serial port "
                         "instead of serving the virtual ECU")
    sp.set_defaults(func=_cmd_serve)

    sp = sub.add_parser(
        "kline",
        help="talk to a REAL ECU over the K-line (ISO 9141-2 / OBD-II; bench or car)",
    )
    sp.add_argument("kline_action",
                    choices=["live", "dtc", "monitor", "clear", "vin", "secure"],
                    help="one-shot live data; fault codes (stored + pending); a "
                         "continuous live monitor; clear codes (Mode 04); read "
                         "the VIN (Mode 09 - may be unsupported on GEMS); or "
                         "'secure' = the proprietary 0xDA $27 channel (bench, "
                         "L-line tied): unlock + read coding")
    sp.add_argument("--yes", "-y", action="store_true",
                    help="skip confirmation prompts (clear; secure writes)")
    # `secure`-only options:
    sp.add_argument("--dump", metavar="ADDR:LEN",
                    help="secure: one 0x3C read, hex ADDR:LEN, LEN 1..3F (e.g. 1800:10)")
    sp.add_argument("--immo", action="store_true",
                    help="secure: read the immobiliser/security block (page 0x18 A4-A8)")
    sp.add_argument("--reset-adaptive", action="store_true",
                    help="secure: send the reset-adaptive-values write")
    sp.add_argument("--immobiliser-synch", action="store_true",
                    help="secure: send the immobiliser-synch (Security-Learn) write")
    sp.add_argument("--port", help="serial port of the Pico adapter (e.g. COM4)")
    sp.add_argument("--connect", metavar="HOST[:PORT]",
                    help="TCP endpoint (serve bridge or WiFi Pico); default port 9141")
    sp.add_argument("--ble", nargs="?", const="gems-pico", metavar="NAME|ADDR",
                    help="Bluetooth LE adapter (NUS); optional device name or "
                         "address (default: gems-pico). No pairing / no COM port.")
    sp.add_argument("--allow-writes", action="store_true",
                    help="permit writes over --connect (default: read-only)")
    sp.set_defaults(func=_cmd_kline)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except WirelessWriteRefused as exc:
        render.console.print(f"[bold red]REFUSED:[/] {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
