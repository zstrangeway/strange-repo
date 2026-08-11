"""Where a stretch of play begins and ends, and what survives the seam.

A scene is the unit of gary's memory. What the narrator is told each turn is
this scene's turns plus the recaps of the ones before it — never every word
since the campaign began. Without that, a campaign costs more per turn the
longer it runs, without limit, and the thing that eventually breaks is not the
bill but the model's grip on a context it cannot hold.

So a boundary is where **prose stops being memory**. Across one, what carries
is the world as the log has it and a few sentences a scene. Which makes
closing a scene the last moment at which something gary narrated but never
recorded can still be recorded — and that is what the close pass is for.

Reconciling is not a licence to assert. The close pass proposes into the same
engines, through the same ``run`` the router uses for a turn, and is refused
by the same refusals. It is offered fewer tools, not looser ones: no dice and
no checks, because a die thrown after the fact decides something nobody was
there for.

**The bound is this module's, not the model's.** Gary may ask for a break and
the player may say so, but a scene past ``SCENE_TURNS`` or ``SCENE_CHARS``
breaks whether either of them thinks it should. A bound a model can decline to
apply is not a bound, and what a turn costs is not a narrative judgement.
"""

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gary_api import logs, narration, world
from gary_api.models import Campaign, Character, Scene, Turn

logger = logs.get_logger(__name__)

# How long a scene may run before it is broken regardless. Turns first,
# because it is the legible one; characters as well, because turns are a poor
# proxy for what a turn costs when the turns are long.
TURNS = 20
CHARS = 24_000


def bounds() -> tuple[int, int]:
    """The bound, read at the moment it is applied.

    From the environment rather than captured at import so a spec can set it
    per scenario, which is the only way to exercise a 20-turn threshold
    without writing 20 turns.
    """

    def whole(name: str, fallback: int) -> int:
        raw = os.environ.get(name, "")
        return int(raw) if raw.isdigit() and int(raw) > 0 else fallback

    return whole("SCENE_TURNS", TURNS), whole("SCENE_CHARS", CHARS)


async def all_of(database: AsyncSession, campaign_id: uuid.UUID) -> list[Scene]:
    """Every scene, oldest first."""
    return list(
        await database.scalars(
            select(Scene)
            .where(Scene.campaign_id == campaign_id)
            .order_by(Scene.number)
        )
    )


async def current(database: AsyncSession, campaign_id: uuid.UUID) -> Scene:
    """The scene being played, opening the first one if there is none.

    Opened lazily rather than when the campaign is created, so a campaign that
    predates scenes reads exactly like one that does not.
    """
    found = await database.scalar(
        select(Scene)
        .where(Scene.campaign_id == campaign_id, Scene.closed_at.is_(None))
        .order_by(Scene.number.desc())
    )
    if found is not None:
        return found

    return await _open(database, campaign_id, "")


async def _open(
    database: AsyncSession, campaign_id: uuid.UUID, title: str
) -> Scene:
    highest = await database.scalar(
        select(func.coalesce(func.max(Scene.number), 0)).where(
            Scene.campaign_id == campaign_id
        )
    )
    scene = Scene(
        campaign_id=campaign_id,
        number=(highest or 0) + 1,
        title=(title or "").strip()[:160],
    )
    database.add(scene)
    await database.flush()

    # In the log as well as in its own table, so "when did the story turn a
    # corner" is answerable in order beside everything else that happened.
    await world.record(
        database,
        campaign_id,
        world.SCENED,
        {"title": scene.title},
        scene_id=scene.id,
    )
    return scene


async def recaps(
    database: AsyncSession, campaign_id: uuid.UUID
) -> list[tuple[str, str]]:
    """What gary is told about the scenes it can no longer remember.

    A scene closed without a recap contributes nothing rather than an empty
    line: gary being unable to say what happened is not the same as nothing
    having happened, and a blank would read as the latter.
    """
    return [
        (scene.title, scene.recap)
        for scene in await all_of(database, campaign_id)
        if scene.closed_at is not None and scene.recap
    ]


async def turns_in(
    database: AsyncSession, scene_id: uuid.UUID
) -> list[Turn]:
    return list(
        await database.scalars(
            select(Turn)
            .where(Turn.scene_id == scene_id)
            .order_by(Turn.created_at, Turn.id)
        )
    )


async def outgrown(database: AsyncSession, scene: Scene) -> bool:
    """Whether this scene has run past what may be sent every turn."""
    turns = await turns_in(database, scene.id)
    limit_turns, limit_chars = bounds()

    if len(turns) >= limit_turns:
        return True
    return sum(len(turn.content or "") for turn in turns) >= limit_chars


async def close(
    database: AsyncSession,
    campaign: Campaign,
    scene: Scene,
    party: list[Character],
    run,
) -> Scene:
    """End a scene: record what it left unrecorded, then sum it up.

    ``run`` is the router's tool runner, handed in rather than reached for.
    That is what keeps this from being a second, quieter path into the world:
    there is one implementation of what a tool does, and reconciling uses it.

    The scene closes whichever way the close pass goes. Gary being unreachable
    costs a recap; refusing to close would cost the bound, and the bound is
    the whole point.
    """
    said = await turns_in(database, scene.id)

    if not said:
        # Nothing happened in it, so there is nothing to reconcile and nothing
        # to sum up. Asking anyway would spend a call to be told so.
        scene.closed_at = datetime.now(timezone.utc)
        await database.flush()
        return scene

    prompt = narration.Prompt(
        briefing="",
        # Not the campaign's model. Recapping is summarising, not running a
        # game, and this is the one call nobody is reading a sentence at a
        # time.
        model=narration.models.scene_model(),
        system_slug=campaign.system_slug,
        module_slug=campaign.module_slug,
        module_title="",
        module_premise="",
        # Empty like the two above: closing_prompt() shows the scene and the
        # world and asks for a summary. Why the party came is not part of
        # summarising what they did.
        module_hook="",
        world=world.render(await world.of(database, campaign.id)),
        scene_title=scene.title,
        transcript=[(turn.role, turn.content) for turn in said],
    )

    recap = ""
    generator = narration.narrator(prompt.model).close(prompt)
    sending: list[narration.Result] | None = None

    try:
        while True:
            try:
                event = await generator.asend(sending)
            except StopAsyncIteration:
                break

            sending = None

            if isinstance(event, narration.Calls):
                results = []
                for call in event.calls:
                    if call.name not in narration.CLOSING_TOOLS:
                        # Refused rather than run. The close pass is offered a
                        # subset and a model reaching outside it is asking for
                        # something this moment cannot answer.
                        results.append(
                            narration.Result(
                                call,
                                f"{call.name} cannot be called while closing a scene",
                                failed=True,
                            )
                        )
                        continue
                    result, _ = await run(
                        database, campaign, party, call, None, scene.id
                    )
                    results.append(result)
                sending = results
            else:
                # A Recap, and nothing else: close() yields those two.
                recap = event.text

    except narration.NarrationError as error:
        # Logged rather than raised. A campaign missing a paragraph is worse
        # than one with it; a campaign whose context never stops growing is
        # worse than both.
        logger.error(
            "scene.unrecapped", campaign_id=str(campaign.id), reason=str(error)
        )
    finally:
        await generator.aclose()

    scene.recap = recap.strip() or None
    scene.closed_at = datetime.now(timezone.utc)
    await database.flush()
    return scene


async def begin(
    database: AsyncSession,
    campaign: Campaign,
    party: list[Character],
    run,
    title: str = "",
) -> Scene:
    """Close the scene being played and open the next one."""
    await close(database, campaign, await current(database, campaign.id), party, run)
    return await _open(database, campaign.id, title)
