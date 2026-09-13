"""creed on the command line.

The same capabilities the MCP server exposes, driven by a person. Syncing in
particular needs to be runnable by hand: it is the first thing to suspect when
an answer looks out of date, and a tool somebody cannot check is a tool they
stop believing.

Every command that changes something says what it changed, and a command that
finds nothing says so rather than printing an empty list.
"""

import argparse
import sys

from . import answers, army, datasheets, db, detachments, render, rules, sync, validate
from .attack import UnreadableProfileError, resolve
from .fetch import ExportUnreachableError


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _sync(args) -> int:
    try:
        result = sync.sync(force=args.force, on_progress=lambda line: print(line))
    except ExportUnreachableError as error:
        return _fail(f"could not reach the export: {error}")
    if result.failed:
        return _fail(
            f"sync failed, and the previous data is untouched: {result.failed}"
        )
    if result.already_current:
        print(f"Already current. The export was last updated {result.last_update}.")
        return 0
    print(
        f"Synced to {result.last_update}: {result.rows} rows across "
        f"{len(result.tables)} tables "
        f"({len(result.downloaded)} downloaded, {len(result.not_modified)} unchanged)."
    )
    return 0


def _status(args) -> int:
    state = sync.status()
    if not state["synced"]:
        return _fail("creed has no data yet. Run `creed sync`.")
    print(f"Export last updated : {state['last_update']}")
    print(f"creed last checked  : {state['last_checked']}")
    print(f"Rows held           : {state['rows']}")
    print(f"Tables              : {len(state['tables'])}")
    return 0


def _with_data(handler):
    """Run a read command, turning "no data yet" into one clear message."""

    def run(args) -> int:
        with db.session() as connection:
            try:
                provenance = answers.provenance(connection)
            except answers.NotSyncedError as error:
                return _fail(str(error))
            return handler(args, connection, provenance)

    return run


@_with_data
def _search(args, connection, provenance) -> int:
    result = datasheets.search(connection, args.query, faction=args.faction)
    print(render.search_results(result, provenance))
    return 0 if result.matches else 1


@_with_data
def _show(args, connection, provenance) -> int:
    sheets = datasheets.by_name(connection, args.name, faction=args.faction)
    if not sheets:
        result = datasheets.search(connection, args.name, faction=args.faction)
        if not result.matches:
            print(render.search_results(result, provenance))
            return 1
        sheets = [datasheets.get(connection, result.matches[0].id)]
    if len(sheets) > 1:
        print(
            f"{len(sheets)} datasheets are called {args.name!r}. "
            "Name the faction to choose one:"
        )
        for sheet in sheets:
            print(f"- {sheet.name} ({sheet.faction})")
        return 1
    print(render.datasheet(sheets[0], provenance))
    return 0


@_with_data
def _factions(args, connection, provenance) -> int:
    for faction in datasheets.factions(connection):
        print(f"{faction['id']:<6} {faction['name']}")
    print()
    print(render.provenance_block(provenance))
    return 0


@_with_data
def _stratagems(args, connection, provenance) -> int:
    if args.phase:
        known = rules.phases(connection)
        if not any(args.phase.lower() in phase.lower() for phase in known):
            return _fail(
                f"{args.phase!r} is not a phase in the export. It has: "
                + ", ".join(known)
            )
    found = rules.stratagems(
        connection,
        name=args.name,
        phase=args.phase,
        turn=args.turn,
        detachment=args.detachment,
        faction=args.faction,
        max_cp=args.max_cp,
    )
    print(render.stratagems(found, provenance))
    return 0 if found else 1


@_with_data
def _detachments(args, connection, provenance) -> int:
    if args.name:
        found = detachments.by_name(connection, args.name)
        if not found:
            return _fail(f"no detachment matched {args.name!r}")
        one = found[0]
        print(
            render.detachment(one, detachments.contents(connection, one.id), provenance)
        )
        return 0
    found = detachments.for_faction(connection, args.faction)
    if not found:
        return _fail(f"no detachments for {args.faction!r}")
    for one in found:
        points = "?" if one.dp is None else one.dp
        print(f"{one.name:<34} {points} DP   {one.force_disposition}")
    print()
    print(render.provenance_block(provenance))
    return 0


def _list_new(args) -> int:
    with db.session() as connection:
        try:
            answers.provenance(connection)
            list_id = army.create(connection, args.name, args.faction, args.points)
        except (answers.NotSyncedError, army.ListError) as error:
            return _fail(str(error))
    print(f"Started {args.name!r}: {args.faction}, {args.points} points. id {list_id}")
    return 0


def _list_add(args) -> int:
    with db.session() as connection:
        try:
            provenance = answers.provenance(connection)
            sheets = datasheets.by_name(connection, args.unit)
            if not sheets:
                found = datasheets.search(connection, args.unit)
                if not found.matches:
                    return _fail(f"no datasheet matched {args.unit!r}")
                sheets = [datasheets.get(connection, found.matches[0].id)]
            unit_id = army.add_unit(connection, args.list, sheets[0].id, args.models)
            priced = army.price(connection, args.list)
        except (answers.NotSyncedError, army.ListError) as error:
            return _fail(str(error))
    added = next(unit for unit in priced.units if unit.id == unit_id)
    print(f"Added {added.name} ({added.models} models) at {added.unit_cost}pts.")
    if priced.over_by:
        print(f"That list is now {priced.over_by} points over its limit.")
    else:
        print(f"Total {priced.total} / {priced.points_limit}.")
    _ = provenance
    return 0


def _list_remove(args) -> int:
    with db.session() as connection:
        try:
            army.remove_unit(connection, args.unit)
            priced = army.price(connection, args.list)
        except army.ListError as error:
            return _fail(str(error))
    print(f"Removed. Total {priced.total} / {priced.points_limit}.")
    return 0


def _list_detachment(args) -> int:
    with db.session() as connection:
        try:
            army.set_detachment(connection, args.list, args.detachment)
        except army.ListError as error:
            return _fail(str(error))
    print(f"Detachment set to {args.detachment}.")
    return 0


@_with_data
def _list_show(args, connection, provenance) -> int:
    if args.list is None:
        lists = army.all_lists(connection)
        if not lists:
            print("No lists yet.")
            return 1
        for one in lists:
            print(
                f"{one['id']:<4} {one['name']:<28} "
                f"{one['faction_id']:<8} {one['points_limit']}pts"
            )
        return 0
    try:
        priced = army.price(connection, args.list)
    except army.ListError as error:
        return _fail(str(error))
    print(render.army_list(priced, provenance))
    return 0


@_with_data
def _list_check(args, connection, provenance) -> int:
    try:
        report = validate.check(connection, args.list)
    except army.ListError as error:
        return _fail(str(error))
    print(render.report(report, provenance))
    return 0 if report.passed else 1


@_with_data
def _attack(args, connection, provenance) -> int:
    attackers = datasheets.by_name(connection, args.attacker)
    targets = datasheets.by_name(connection, args.target)
    if not attackers:
        return _fail(f"no datasheet called {args.attacker!r}")
    if not targets:
        return _fail(f"no datasheet called {args.target!r}")
    attacker, target = attackers[0], targets[0]
    if not target.models:
        return _fail(f"{target.name} has no model profile in the export")
    weapons = [
        weapon
        for weapon in attacker.wargear
        if args.weapon is None or args.weapon.lower() in weapon["name"].lower()
    ]
    if not weapons:
        return _fail(
            f"{attacker.name} has no weapon matching {args.weapon!r}. It has: "
            + ", ".join(weapon["name"] for weapon in attacker.wargear)
        )
    for weapon in weapons:
        try:
            result = resolve(
                weapon,
                target.models[0],
                attacker=attacker.name,
                target=target.name,
                models=args.models,
                target_keywords=tuple(target.keywords + target.faction_keywords),
            )
        except UnreadableProfileError as error:
            print(f"# {weapon['name']}\ncreed could not read this profile: {error}\n")
            continue
        print(render.attack_result(result, provenance))
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creed", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="pull the current export")
    sync_parser.add_argument(
        "--force", action="store_true", help="sync even if current"
    )
    sync_parser.set_defaults(handler=_sync)

    status_parser = subparsers.add_parser("status", help="how fresh the data is")
    status_parser.set_defaults(handler=_status)

    search_parser = subparsers.add_parser("search", help="find datasheets by name")
    search_parser.add_argument("query")
    search_parser.add_argument("--faction")
    search_parser.set_defaults(handler=_search)

    show_parser = subparsers.add_parser("show", help="one datasheet, whole")
    show_parser.add_argument("name")
    show_parser.add_argument("--faction")
    show_parser.set_defaults(handler=_show)

    factions_parser = subparsers.add_parser("factions", help="list the factions")
    factions_parser.set_defaults(handler=_factions)

    strat_parser = subparsers.add_parser("stratagems", help="find stratagems")
    strat_parser.add_argument("--name")
    strat_parser.add_argument("--phase")
    strat_parser.add_argument("--turn", choices=["Your turn", "Opponent's turn"])
    strat_parser.add_argument("--detachment")
    strat_parser.add_argument("--faction")
    strat_parser.add_argument("--max-cp", type=int, dest="max_cp")
    strat_parser.set_defaults(handler=_stratagems)

    det_parser = subparsers.add_parser(
        "detachments", help="detachments and what they give"
    )
    det_parser.add_argument("--faction", default="")
    det_parser.add_argument("--name")
    det_parser.set_defaults(handler=_detachments)

    attack_parser = subparsers.add_parser("attack", help="work out an attack")
    attack_parser.add_argument("attacker")
    attack_parser.add_argument("target")
    attack_parser.add_argument("--weapon")
    attack_parser.add_argument("--models", type=int, default=1)
    attack_parser.set_defaults(handler=_attack)

    list_parser = subparsers.add_parser("list", help="build and check an army list")
    list_subparsers = list_parser.add_subparsers(dest="list_command", required=True)

    new_parser = list_subparsers.add_parser("new")
    new_parser.add_argument("name")
    new_parser.add_argument("faction")
    new_parser.add_argument("--points", type=int, default=2000)
    new_parser.set_defaults(handler=_list_new)

    add_parser = list_subparsers.add_parser("add")
    add_parser.add_argument("list", type=int)
    add_parser.add_argument("unit")
    add_parser.add_argument("--models", type=int)
    add_parser.set_defaults(handler=_list_add)

    remove_parser = list_subparsers.add_parser("remove")
    remove_parser.add_argument("list", type=int)
    remove_parser.add_argument("unit", type=int)
    remove_parser.set_defaults(handler=_list_remove)

    detachment_parser = list_subparsers.add_parser("detachment")
    detachment_parser.add_argument("list", type=int)
    detachment_parser.add_argument("detachment")
    detachment_parser.set_defaults(handler=_list_detachment)

    show_list_parser = list_subparsers.add_parser("show")
    show_list_parser.add_argument("list", type=int, nargs="?")
    show_list_parser.set_defaults(handler=_list_show)

    check_parser = list_subparsers.add_parser("check")
    check_parser.add_argument("list", type=int)
    check_parser.set_defaults(handler=_list_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
