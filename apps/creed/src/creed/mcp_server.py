"""creed as an MCP server, over stdio.

The same capabilities the CLI calls, exposed as tools. Not a second
implementation of anything — every function here opens the database, calls the
module that does the work, and turns what comes back into text a model can
read.

Three rules this file exists to keep:

* **stdout is the protocol.** One stray print in a startup path and the
  client's first parse fails, which reaches a person as a server that will not
  connect and no explanation anywhere. Logging is pinned to stderr in main,
  and the sync's running commentary goes through the logger rather than print.
* **A refusal is a result, not an exception.** An error crossing the transport
  takes the session's turn with it, so every tool turns a refusal into
  ``ToolError``, which the SDK hands back as something the model can read and
  act on.
* **Every answer carries its date.** A model cannot see the sync log, so
  without the timestamp in the text it has no way to say how current the
  answer is.
"""

import logging
import os
import sys

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import answers, army, datasheets, db, detachments, render, rules, sync, validate
from .attack import UnreadableProfileError, resolve
from .fetch import ExportUnreachableError

logger = logging.getLogger("creed.mcp")

server = MCPServer(
    name="creed",
    instructions=(
        "Warhammer 40,000 rules and stats, read from Wahapedia's data export "
        "for 11th edition. Look up datasheets, stratagems, detachments and "
        "enhancements; build and check an army list; and work out the "
        "arithmetic of an attack from the real profiles. Every answer says "
        "which sync it came from. Points depend on how many of a datasheet "
        "an army already holds, so a unit has no single price. check_list "
        "reports what it checked and never says a list is legal."
    ),
)


def _refuse(message: str) -> str:
    """Hand a refusal back as something the model reads, not as a crash.

    It has to be ``ToolError`` specifically. Any other exception is reported
    to the client as "Error executing tool <name>" with the reason logged
    server-side, where nobody driving the tool will ever see it.
    """
    logger.info("refused: %s", message)
    raise ToolError(message)


def _provenance(connection):
    try:
        return answers.provenance(connection)
    except answers.NotSyncedError as error:
        _refuse(str(error))


def _resolve(connection, reference: str, faction: str | None = None):
    """A datasheet by id, then exact name, then search — or the choices."""
    sheet = datasheets.get(connection, reference)
    if sheet is not None:
        return sheet
    sheets = datasheets.by_name(connection, reference, faction=faction)
    if len(sheets) == 1:
        return sheets[0]
    if len(sheets) > 1:
        choices = "\n".join(f"- {s.name} ({s.faction}) `{s.id}`" for s in sheets)
        _refuse(
            f"{len(sheets)} datasheets are called {reference!r}. Call again "
            f"with an id or a faction:\n{choices}"
        )
    found = datasheets.search(connection, reference, faction=faction)
    if len(found.matches) == 1:
        return datasheets.get(connection, found.matches[0].id)
    if found.matches:
        choices = "\n".join(f"- {m.name} ({m.faction}) `{m.id}`" for m in found.matches)
        _refuse(f"Nothing is called exactly {reference!r}. Did you mean:\n{choices}")
    _refuse(f"Nothing matched {reference!r}.")


@server.tool(
    description=(
        "Find Warhammer 40,000 datasheets by part of a name. Returns each "
        "match with its faction and id. Several factions have a datasheet "
        "with the same name, so this never picks one for you."
    )
)
def search_datasheets(query: str, faction: str | None = None) -> str:
    logger.info("tool.call search_datasheets")
    with db.session() as connection:
        provenance = _provenance(connection)
        if not (query or "").strip():
            _refuse("search_datasheets needs something to search for.")
        return render.search_results(
            datasheets.search(connection, query, faction=faction), provenance
        )


@server.tool(
    description=(
        "One datasheet in full: every model's statline, weapon profiles, "
        "abilities, keywords, unit composition, points, damaged profile and "
        "who can lead it. Takes an id from search_datasheets, or an exact name."
    )
)
def get_datasheet(datasheet: str, faction: str | None = None) -> str:
    logger.info("tool.call get_datasheet")
    with db.session() as connection:
        provenance = _provenance(connection)
        return render.datasheet(_resolve(connection, datasheet, faction), provenance)


@server.tool(description="Every faction in the export, with the id other tools take.")
def list_factions() -> str:
    logger.info("tool.call list_factions")
    with db.session() as connection:
        provenance = _provenance(connection)
        lines = [
            f"- **{faction['name']}** `{faction['id']}`"
            for faction in datasheets.factions(connection)
        ]
        return "\n".join(lines) + "\n\n" + render.provenance_block(provenance)


@server.tool(
    description=(
        "Find stratagems by what matters in play: whose turn, which phase, "
        "which detachment, and how much CP you have. Stratagems usable in any "
        "phase or either turn always match."
    )
)
def find_stratagems(
    name: str | None = None,
    phase: str | None = None,
    turn: str | None = None,
    detachment: str | None = None,
    faction: str | None = None,
    max_cp: int | None = None,
) -> str:
    logger.info("tool.call find_stratagems")
    with db.session() as connection:
        provenance = _provenance(connection)
        if phase:
            known = rules.phases(connection)
            if not any(phase.lower() in one.lower() for one in known):
                _refuse(
                    f"{phase!r} is not a phase in the export. It has: "
                    + ", ".join(known)
                )
        found = rules.stratagems(
            connection,
            name=name,
            phase=phase,
            turn=turn,
            detachment=detachment,
            faction=faction,
            max_cp=max_cp,
        )
        return render.stratagems(found, provenance)


@server.tool(
    description=(
        "What a detachment gives an army: its ability, stratagems, "
        "enhancements, Detachment Points and Force Disposition. Detachment "
        "Points differ by chapter for some detachments, and the answer says "
        "so. Pass a faction instead to list that faction's detachments."
    )
)
def get_detachment(name: str | None = None, faction: str | None = None) -> str:
    logger.info("tool.call get_detachment")
    with db.session() as connection:
        provenance = _provenance(connection)
        if name:
            found = detachments.by_name(connection, name)
            if not found:
                _refuse(f"No detachment matched {name!r}.")
            one = found[0]
            return render.detachment(
                one, detachments.contents(connection, one.id), provenance
            )
        if not faction:
            _refuse("get_detachment needs a detachment name or a faction.")
        found = detachments.for_faction(connection, faction)
        if not found:
            _refuse(f"No detachments for {faction!r}.")
        lines = [
            f"- **{one.name}** — {one.dp if one.dp is not None else '?'} DP"
            + (f", {one.force_disposition}" if one.force_disposition else "")
            + f" `{one.id}`"
            for one in found
        ]
        return "\n".join(lines) + "\n\n" + render.provenance_block(provenance)


@server.tool(description="Start an army list for a faction at a points limit.")
def start_list(name: str, faction: str, points: int = 2000) -> str:
    logger.info("tool.call start_list")
    with db.session() as connection:
        _provenance(connection)
        try:
            list_id = army.create(connection, name, faction, points)
        except army.ListError as error:
            _refuse(str(error))
        return (
            f"Started {name!r} for {faction} at {points} points. list_id is {list_id}."
        )


@server.tool(
    description=(
        "Add a unit to a list. Its price comes from how many of that "
        "datasheet the list already holds: 11th edition charges more for "
        "later copies of the same unit."
    )
)
def add_unit(list_id: int, datasheet: str, models: int | None = None) -> str:
    logger.info("tool.call add_unit")
    with db.session() as connection:
        _provenance(connection)
        sheet = _resolve(connection, datasheet)
        try:
            unit_id = army.add_unit(connection, list_id, sheet.id, models)
            priced = army.price(connection, list_id)
        except army.ListError as error:
            _refuse(str(error))
        added = next(unit for unit in priced.units if unit.id == unit_id)
        tier = (
            f" as your {added.tier} of this datasheet"
            if added.tier and added.tier != "any"
            else ""
        )
        note = (
            f"That list is now {priced.over_by} points over its limit."
            if priced.over_by
            else f"Total {priced.total} / {priced.points_limit}."
        )
        return (
            f"Added {added.name} ({added.models} models) at {added.unit_cost}pts"
            f"{tier}. unit_id is {unit_id}.\n{note}"
        )


@server.tool(
    description=(
        "Remove a unit from a list. The units left may get cheaper, because "
        "their position in the list decides their price."
    )
)
def remove_unit(list_id: int, unit_id: int) -> str:
    logger.info("tool.call remove_unit")
    with db.session() as connection:
        _provenance(connection)
        try:
            army.remove_unit(connection, unit_id)
            priced = army.price(connection, list_id)
        except army.ListError as error:
            _refuse(str(error))
        return (
            f"Removed. Total {priced.total} / {priced.points_limit}.\n"
            "Units left may have changed price, because position decides cost."
        )


@server.tool(description="Choose a list's detachment.")
def set_detachment(list_id: int, detachment: str) -> str:
    logger.info("tool.call set_detachment")
    with db.session() as connection:
        _provenance(connection)
        try:
            army.set_detachment(connection, list_id, detachment)
        except army.ListError as error:
            _refuse(str(error))
        return f"Detachment set to {detachment!r}."


@server.tool(
    description=(
        "A list with every unit, its price, the total and what remains. Omit "
        "list_id to see every list."
    )
)
def show_list(list_id: int | None = None) -> str:
    logger.info("tool.call show_list")
    with db.session() as connection:
        provenance = _provenance(connection)
        if list_id is None:
            lists = army.all_lists(connection)
            if not lists:
                return "No lists yet. Start one with start_list."
            return "\n".join(
                f"- **{one['name']}** ({one['faction_id']}, "
                f"{one['points_limit']}pts) `{one['id']}`"
                for one in lists
            )
        try:
            priced = army.price(connection, list_id)
        except army.ListError as error:
            _refuse(str(error))
        return render.army_list(priced, provenance)


@server.tool(
    description=(
        "Check a list against what the export encodes: points, faction, "
        "leader attachments, enhancements, and datasheets that cannot be "
        "taken at all. It reports what it checked, shows the eligibility "
        "wording it cannot decide, and names the core rules that are not in "
        "the export. It never says a list is legal."
    )
)
def check_list(list_id: int) -> str:
    logger.info("tool.call check_list")
    with db.session() as connection:
        provenance = _provenance(connection)
        try:
            report = validate.check(connection, list_id)
        except army.ListError as error:
            _refuse(str(error))
        return render.report(report, provenance)


@server.tool(
    description=(
        "The arithmetic of one unit attacking another, from the real "
        "profiles: rolls needed, expected hits, wounds, damage and models "
        "killed. Takes two datasheets rather than typed statlines, so the "
        "numbers come from the export. Names any weapon ability it did not "
        "apply, including ones that only apply against some targets."
    )
)
def work_out_attack(
    attacker: str, target: str, weapon: str | None = None, models: int = 1
) -> str:
    logger.info("tool.call work_out_attack")
    with db.session() as connection:
        provenance = _provenance(connection)
        attacking = _resolve(connection, attacker)
        defending = _resolve(connection, target)
        if not defending.models:
            _refuse(f"{defending.name} has no model profile in the export.")
        weapons = [
            one
            for one in attacking.wargear
            if weapon is None or weapon.lower() in one["name"].lower()
        ]
        if not weapons:
            _refuse(
                f"{attacking.name} has no weapon matching {weapon!r}. It has: "
                + ", ".join(one["name"] for one in attacking.wargear)
            )
        blocks = []
        for one in weapons:
            try:
                result = resolve(
                    one,
                    defending.models[0],
                    attacker=attacking.name,
                    target=defending.name,
                    models=models,
                    target_keywords=tuple(
                        defending.keywords + defending.faction_keywords
                    ),
                )
            except UnreadableProfileError as error:
                blocks.append(
                    f"# {one['name']}\ncreed could not read this profile: {error}"
                )
                continue
            blocks.append(render.attack_result(result, provenance))
        return "\n\n".join(blocks)


@server.tool(
    description=(
        "When the Wahapedia export creed holds was last updated, when creed "
        "last checked, and how many rows it has. Use this to say how current "
        "an answer is."
    )
)
def data_freshness() -> str:
    logger.info("tool.call data_freshness")
    state = sync.status()
    if not state["synced"]:
        _refuse(
            "creed has no data yet. Run `creed sync`, or restart the server "
            "with network access."
        )
    with db.session() as connection:
        provenance = _provenance(connection)
    return (
        f"Export last updated: {state['last_update']}\n"
        f"creed last checked: {state['last_checked']}\n"
        f"Rows held: {state['rows']} across {len(state['tables'])} tables\n\n"
        f"{render.provenance_block(provenance)}"
    )


def _sync_on_start() -> None:
    """Bring the data up to date before serving, and never on stdout.

    Skippable with CREED_SYNC_ON_START=0, which is how the specs start a
    server that does not reach the network.
    """
    if os.environ.get("CREED_SYNC_ON_START", "1") == "0":
        logger.info("startup sync skipped")
        return
    try:
        result = sync.sync(on_progress=lambda line: logger.info("%s", line))
    except ExportUnreachableError as error:
        logger.warning("could not reach the export (%s); serving what is here", error)
        return
    if result.failed:
        logger.warning("sync failed (%s); serving what was already here", result.failed)
    elif result.already_current:
        logger.info("already current at %s", result.last_update)
    else:
        logger.info("synced to %s: %s rows", result.last_update, result.rows)


def main() -> int:
    """Run the server on stdio.

    Logging is configured before anything else can emit a record, and pinned
    to stderr: the default handler writes to stdout, which is the transport.
    """
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        # Without this, basicConfig does nothing at all when an imported
        # module has already configured the root logger, and creed's lines go
        # out in somebody else's format.
        force=True,
    )
    # httpx logs every request at INFO. Twenty-one of those on each sync bury
    # the lines creed writes about what it actually did.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _sync_on_start()
    server.run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
