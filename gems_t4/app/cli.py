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
from gems_t4.gems import actuators, dtc, immobiliser, livedata, programming
from gems_t4.gems.scenarios import SCENARIOS, get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient, WirelessWriteRefused
from gems_t4.transport.pico import PicoAdapterTransport
from gems_t4.transport.tcp import TcpTransport, parse_endpoint
from gems_t4.transport.virtual import VirtualTransport


def _build_client(args: argparse.Namespace) -> tuple[KwpClient, VirtualEcu | None]:
    """Build a client over the virtual ECU (default), the USB Pico adapter
    (``--port``), or a TCP endpoint (``--connect``)."""
    if getattr(args, "port", None) and getattr(args, "connect", None):
        raise SystemExit("choose --port (USB) or --connect (network), not both")
    if getattr(args, "port", None):
        transport = PicoAdapterTransport(args.port)
        return KwpClient(transport), None
    if getattr(args, "connect", None):
        host, tcp_port = parse_endpoint(args.connect)
        transport = TcpTransport(
            host, tcp_port, allow_writes=getattr(args, "allow_writes", False)
        )
        return KwpClient(transport), None
    ecu = VirtualEcu(
        get_scenario(args.scenario), immobilised=getattr(args, "immobilised", False)
    )
    # A few ticks so the warm-up curve / idle hunt have advanced a little.
    for _ in range(5):
        ecu.tick(0.1)
    transport = VirtualTransport(ecu, latency=args.latency)
    return KwpClient(transport), ecu


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
    client, _ = _build_client(args)
    render.communicating()
    client.connect()
    try:
        client.start_session()
        ids = None
        if args.ids:
            ids = [int(x, 0) for x in args.ids]
        measures = livedata.read_all(client, ids)
    finally:
        client.close()
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
    client, _ = _build_client(args)
    render.communicating()
    client.connect()
    try:
        client.start_session()
        if args.dtc_action == "clear":
            dtc.clear_dtcs(client)
            render.console.print("[green]Fault codes cleared.[/]")
            return 0
        dtcs = dtc.read_dtcs(client)
    finally:
        client.close()
    render.print_dtcs(dtcs, title=f"Fault codes - {_source_label(args)}")
    return 0


def _cmd_gui(args: argparse.Namespace) -> int:
    if getattr(args, "instant", False):
        # Disable "the waiting" (the ECU-communication overlay's minimum
        # display time) for impatient users - see gems_t4/app/gui/wait.py.
        os.environ["GEMS_T4_INSTANT"] = "1"
    if args.port and args.connect:
        render.console.print("[red]choose --port (USB) or --connect, not both[/]")
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
    client, _ = _build_client(args)
    state = actuators.STATE_ON if args.state == "on" else actuators.STATE_OFF
    try:
        act = actuators.by_name(args.name)
    except KeyError as exc:
        render.console.print(f"[red]{exc}[/]")
        return 2
    render.communicating()
    client.connect()
    try:
        client.start_session()
        outcome = actuators.run(client, act.actuator_id, state)
    finally:
        client.close()
    render.print_actuator(outcome)
    return 0 if outcome.ok else 1


def _cmd_coding(args: argparse.Namespace) -> int:
    from rich.table import Table

    client, _ = _build_client(args)
    render.communicating()
    client.connect()
    try:
        client.start_session()
        if args.coding_action == "write":
            if not args.field or args.value is None:
                render.console.print("[red]coding write needs --field and --value[/]")
                return 2
            try:
                value = programming.encode_field(args.field, args.value)
                backup = programming.backup(client, args.field)

                def _confirm() -> bool:
                    if args.yes:
                        return True
                    field = programming.CODING_FIELDS[args.field]
                    old = programming.decode_field(args.field, backup.data)
                    return _prompt_yes_no(
                        f"Write {field.name}: '{old}' -> '{args.value}'? [y/N] "
                    )

                result = programming.write_coding(
                    client, args.field, value, backup=backup, confirm=_confirm
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
        for f in programming.CODING_FIELDS.values():
            val = programming.decode_field(f.key, programming.read_coding(client, f.key))
            table.add_row(f.name, val, "yes" if f.writable else "no")
        render.console.print(table)
        return 0
    finally:
        client.close()


def _cmd_immo(args: argparse.Namespace) -> int:
    client, _ = _build_client(args)
    render.communicating()
    client.connect()
    try:
        client.start_session()
        if args.immo_action == "learn":
            result = immobiliser.security_learn(
                client, on_progress=lambda s: render.console.print(f"  [dim]{s}[/]")
            )
            style = "green" if result.ok else "bold red"
            render.console.print(f"[{style}]{result.message}[/]")
            return 0 if result.ok else 1
        status = immobiliser.read_status(client)
        colour = "green" if status.mobilised else "bold red"
        render.console.print(f"Immobiliser: [{colour}]{status.summary}[/]")
        return 0
    finally:
        client.close()


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
