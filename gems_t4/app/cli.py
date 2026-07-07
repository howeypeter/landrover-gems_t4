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
import sys

from gems_t4 import __version__
from gems_t4.app import render
from gems_t4.gems import actuators, dtc, immobiliser, livedata, programming
from gems_t4.gems.scenarios import SCENARIOS, get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.transport.pico import PicoAdapterTransport
from gems_t4.transport.virtual import VirtualTransport


def _build_client(args: argparse.Namespace) -> tuple[KwpClient, VirtualEcu | None]:
    """Build a client over the virtual ECU (default) or the Pico adapter."""
    if getattr(args, "port", None):
        transport = PicoAdapterTransport(args.port)
        return KwpClient(transport), None
    ecu = VirtualEcu(
        get_scenario(args.scenario), immobilised=getattr(args, "immobilised", False)
    )
    # A few ticks so the warm-up curve / idle hunt have advanced a little.
    for _ in range(5):
        ecu.tick(0.1)
    transport = VirtualTransport(ecu, latency=args.latency)
    return KwpClient(transport), ecu


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
    render.print_live(measures, title=f"Live data - scenario '{args.scenario}'")
    return 0


def _cmd_dtc(args: argparse.Namespace) -> int:
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
    render.print_dtcs(dtcs, title=f"Fault codes - scenario '{args.scenario}'")
    return 0


def _cmd_gui(args: argparse.Namespace) -> int:
    try:
        from gems_t4.app.gui.app import run
    except ImportError:
        render.console.print(
            "[red]PySide6 is not installed.[/] Install the GUI extra: "
            "pip install -e \".[gui]\""
        )
        return 2
    return run(scenario=args.scenario)


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
                result = programming.write_coding(
                    client, args.field, value, backup=backup, confirm=lambda: True
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
    sp.set_defaults(func=_cmd_gui)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
