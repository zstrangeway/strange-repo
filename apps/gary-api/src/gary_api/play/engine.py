"""The turn engine: tool dispatch, combat resolution, and SSE streaming."""

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from gary_api import db, dice, logs, narration, scenes, systems, world
from gary_api.auth import Refusal
from gary_api.models import (
    Adversary,
    Campaign,
    Character,
    Roll,
    Scene,
    Turn,
    WorldEvent,
)
from gary_api.play.campaigns import _party

logger = logs.get_logger(__name__)


# What gary is asked for when a campaign has a party and nothing has been
# said. Not a player's message — there is no player message, and that is the
# only thing unusual about an opening — but it arrives by the same route,
# because everything else about it is an ordinary turn.
OPENING = (
    "Open the campaign. Nothing has happened yet and nobody has said "
    "anything.\n\n"
    "Put the party in the situation, not in front of it. In two or three "
    "short paragraphs: say plainly why they are here and who wants this "
    "dealt with — you were told, so tell them — then show them the thing "
    "that is wrong, happening now, close enough to touch.\n\n"
    "End on pressure: something that has just changed, or is about to, and "
    "that they will have to answer. Give them a way in they can take this "
    "minute, not a landscape to admire. Do not end by asking what they do; "
    "they know, and they will tell you."
)


def _frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _named(party: list[Character], name: str) -> Character:
    wanted = (name or "").strip().lower()
    for character in party:
        if character.name.lower() == wanted:
            return character
    raise world.WorldError(f"nobody here is called {name!r}")


def _text_of(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise world.WorldError(f"an adversary needs a {key}")
    return value.strip()


def _count_of(payload: dict, key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise world.WorldError(f"an adversary's {key} must be a whole number")
    return value


async def _either_side(database, campaign, party, name: str):
    """That name, whichever side it is on, and which column holds it."""
    try:
        return "character_id", _named(party, name)
    except world.WorldError:
        pass

    wanted = (name or "").strip().lower()
    for adversary in await database.scalars(
        select(Adversary).where(Adversary.campaign_id == campaign.id)
    ):
        if adversary.name.lower() == wanted:
            return "adversary_id", adversary
    raise world.WorldError(f"nobody here is called {name!r}")


def _in_fight(state: world.World, name: str):
    """Whoever that is, on either side, by the name a person would use."""
    wanted = (name or "").strip().lower()
    for candidate in [*state.party, *state.enemies]:
        if candidate.name.lower() == wanted:
            return candidate
    raise world.WorldError(f"nobody in this fight is called {name!r}")


async def _fighting(
    database, campaign, party, foes, call, arguments, rolled, moved, turn_id
):
    """The four things that can happen to a fight.

    Together rather than spread through the chain in ``_run``, because every
    one of them needs the same two things first — the world as it stands, and
    whether there is a fight at all — and because they are one feature.

    What gary decides here: who is fighting, and what somebody tries. What it
    does not: who goes first, whether a blow lands, or what it costs.
    """
    ruleset = systems.ruleset(campaign.system_slug)
    state = await world.of(database, campaign.id)
    fight = state.fight
    rows = {str(one.id): one for one in [*party, *foes]}

    if call.name == "begin_combat":
        if fight is not None:
            raise world.WorldError("a fight is already happening")
        # No check that anybody is here to fight it: the turn endpoint refuses
        # a campaign with no party before a byte is streamed, so a fight
        # cannot be started in one. A guard here would be a branch nothing
        # could reach.

        wanted = arguments.get("adversaries") or []
        if not isinstance(wanted, list) or not wanted:
            raise world.WorldError("a fight needs something to fight")

        made = []
        for one in wanted:
            if not isinstance(one, dict):
                raise world.WorldError("each adversary needs a name and a shape")
            adversary = Adversary(
                campaign_id=campaign.id,
                name=_text_of(one, "name")[:80],
                max_hp=_count_of(one, "hit_points"),
                armour_class=_count_of(one, "armour_class"),
                attack_bonus=int(one.get("attack_bonus") or 0),
                damage=str(one.get("damage") or ruleset.unarmed_damage)[:32],
            )
            database.add(adversary)
            made.append(adversary)
        await database.flush()

        # Everybody rolls and the engine sorts them. This is the whole point:
        # gary decided the order before, with modifiers it invented.
        frames, order = [], []
        for character in party:
            score = (character.abilities or {}).get(ruleset.initiative_ability, 10)
            thrown = ruleset.initiative(ruleset.modifier(score))
            frames.append(
                _frame(
                    "roll",
                    rolled(thrown, character, ability=ruleset.initiative_ability),
                )
            )
            order.append((thrown.total, str(character.id), character.name))
        for adversary in made:
            thrown = ruleset.initiative(adversary.attack_bonus)
            frames.append(_frame("roll", rolled(thrown, foe=adversary)))
            order.append((thrown.total, str(adversary.id), adversary.name))

        # Highest first, ties broken by name so that folding the log twice
        # lands the same way twice.
        order.sort(key=lambda one: (-one[0], one[2]))
        result, changed = await moved(
            world.FOUGHT,
            {"order": [one[1] for one in order]},
            "a fight began. The order is "
            + ", ".join(f"{name} ({total})" for total, _, name in order),
        )
        return result, [*frames, *changed]

    if fight is None:
        raise world.WorldError("there is no fight happening")

    up = state.anyone(fight.whose)

    if call.name == "end_combat":
        return await moved(world.PEACE, {}, "the fight is over")

    if call.name == "end_turn":
        if isinstance(up, world.Member) and up.played_by == "player":
            # The reason combat was asked for. Gary reaching the player's turn
            # has to stop there and ask, not narrate through it.
            #
            # Once they have taken it, though, somebody has to move the order
            # on — and it is gary, because the player says what they do rather
            # than operating the machinery. So the bar is that they acted, not
            # that gary may never do this: a fight where nothing could end the
            # player's turn would stop on it forever.
            raise world.WorldError(
                f"it is {up.name}'s turn, and {up.name} is the player's to "
                "take — ask them what they do"
            )
        return await moved(
            world.TURNED, {}, f"{up.name if up else 'that'}'s turn is over"
        )

    # An attack, then. Whoever is up swings at somebody.
    attacker = _in_fight(state, arguments.get("attacker", ""))
    if up is None or attacker.id != up.id:
        raise world.WorldError(
            f"it is not {attacker.name}'s turn — it is "
            f"{up.name if up else 'nobody'}'s"
        )
    target = _in_fight(state, arguments.get("target", ""))
    if target.id == attacker.id:
        raise world.WorldError(f"{attacker.name} cannot attack themselves")
    if target.down:
        raise world.WorldError(f"{target.name} is already down")

    swinging = rows.get(attacker.id)
    hitting = isinstance(attacker, world.Foe)
    bonus = (
        attacker.attack_bonus
        if hitting
        else ruleset.attack_bonus(swinging.abilities)
    )
    guard = (
        target.armour_class
        if isinstance(target, world.Foe)
        else ruleset.default_armour_class
    )
    swing = ruleset.resolve(
        dc=guard, modifier=bonus, reason=f"attack on {target.name}"
    )

    mine = {"foe": swinging} if hitting else {"who": swinging}
    frames = [_frame("roll", rolled(swing.roll, graded=swing, **mine))]

    landed = swing.degree in (
        systems.Degree.SUCCESS,
        systems.Degree.CRITICAL_SUCCESS,
    )

    said = f"{attacker.name} missed {target.name}"
    if landed:
        hurt = dice.roll(
            attacker.damage if hitting else ruleset.unarmed_damage,
            f"{attacker.name} hits {target.name}",
        )
        frames.append(_frame("roll", rolled(hurt, **mine)))
        whose = "adversary_id" if isinstance(target, world.Foe) else "character_id"
        _, changed = await moved(
            world.DAMAGED,
            {whose: target.id, "amount": hurt.total},
            "",
        )
        frames.extend(changed)
        # What they are now at, not only what came off. Every result here used
        # to report a delta and leave gary to do the arithmetic against a
        # world snapshot taken before the turn began — so a wrong write was
        # invisible until the next turn, and a real model narrated a monster
        # at 20 while the world had it at 18. Saying the standing number means
        # gary can never be more than one result behind the truth.
        left = max(0, target.hp - hurt.total)
        said = (
            f"{attacker.name} hit {target.name} for {hurt.total} — "
            f"{target.name} is now on {left} of {target.max_hp}"
        )

    # Swinging is what taking a turn *is* here — a turn holds one action and
    # nothing else is modelled — so the order moves on by itself. Which is
    # also how the player's turn ever ends: gary may not end it for them, and
    # a fight that could not move past them would stop there forever.
    _, over = await moved(world.TURNED, {}, "")
    return narration.Result(
        call, f"{said} ({swing.roll.total} against {guard}). Their turn is over."
    ), [*frames, *over]


async def _run(
    database,
    campaign: Campaign,
    party: list[Character],
    call,
    turn_id: uuid.UUID | None,
    scene_id: uuid.UUID,
) -> tuple[narration.Result, list[str]]:
    """Do what the narrator asked, or refuse it, and say what came of it.

    Everything a narrator can change goes through here, which is the whole
    arrangement: the model proposes, the engines decide, and what goes back to
    the model is what actually happened rather than what it suggested.
    """
    arguments = call.arguments or {}

    async def moved(kind: str, payload: dict, summary: str):
        await world.record(database, campaign.id, kind, payload, turn_id, scene_id)
        return narration.Result(call, summary), [
            _frame("world", {"kind": kind, **payload})
        ]

    def rolled(made, who=None, graded=None, ability=None, foe=None) -> dict:
        """Write one roll down and describe it, whoever it belonged to.

        One place, so what is stored and what is streamed cannot drift: the
        frame said who made a check long before the row had anywhere to keep
        it, and a reload lost the name every time.

        ``who`` is a character row and ``foe`` an adversary row; at most one.
        Rows rather than the world's projection of them, because what goes in
        the column is an id the database will check.
        """
        reason = graded.reason if graded else made.reason
        named = foe or who
        database.add(
            Roll(
                turn_id=turn_id,
                character_id=who.id if who else None,
                adversary_id=foe.id if foe else None,
                notation=made.notation,
                dice=list(made.dice),
                modifier=made.modifier,
                ability=ability,
                total=made.total,
                reason=reason,
                dc=graded.dc if graded else None,
                degree=graded.degree.value if graded else None,
            )
        )
        described = {
            "notation": made.notation,
            "dice": list(made.dice),
            "modifier": made.modifier,
            "total": made.total,
            "reason": reason,
            # Named rather than identified: everything downstream of this is
            # something a person reads.
            "character": named.name if named else None,
            "ability": ability,
            # So a card can tell a monster's roll from a party member's
            # without having to know every name at the table.
            "side": "adversary" if foe else "party",
        }
        if graded:
            described["dc"] = graded.dc
            described["degree"] = graded.degree.value
        return described

    try:
        if call.name == "roll":
            # Whose it is, when it is anybody's. A roll about how sound the
            # timbers are belongs to nobody, and saying otherwise would be
            # inventing a fact to fill a field.
            named = (arguments.get("character") or "").strip()
            who = _named(party, named) if named else None
            notation = arguments.get("notation", "")

            ability = (arguments.get("ability") or "").strip().lower() or None
            modifier = 0
            if who is not None:
                # Plain dice for a person's roll. This is the hole everything
                # in `check` was built to close, left open: gary ran a whole
                # encounter through it, giving four characters initiative
                # modifiers of +1, +2, +3 and +4 that came from nowhere, off
                # sheets of straight tens. A rule that binds only the tool
                # gary can route around is not a rule.
                if dice.modifier_in(notation):
                    raise world.WorldError(
                        f"{notation!r} carries a modifier, and a roll for "
                        f"{who.name} takes plain dice — name an ability and "
                        "the sheet decides what it is worth"
                    )
                ruleset = systems.ruleset(campaign.system_slug)
                if ability:
                    if ability not in ruleset.abilities:
                        raise world.WorldError(
                            f"{ability!r} is not an ability in this system"
                        )
                    modifier = ruleset.modifier(
                        (who.abilities or {}).get(ability, 10)
                    )
                    notation = f"{notation}{modifier:+d}" if modifier else notation

            made = dice.roll(notation, arguments.get("reason", ""))
            payload = rolled(made, who, ability=ability)
            await database.flush()
            return narration.Result(
                call,
                f"{made.notation} came up {made.total}"
                + (f" for {who.name}" if who else ""),
            ), [_frame("roll", payload)]

        if call.name == "check":
            # The rules grade it, not gary and not this module. A system with
            # four degrees returns four here without anything else changing.
            ruleset = systems.ruleset(campaign.system_slug)

            # Everyone facing the same thing, in one call. Resolved before
            # anything is rolled, because a check is all or nothing: half of
            # it applied says two of them crossed and the fiction says they
            # went together.
            names = arguments.get("characters") or []
            if isinstance(names, str):
                names = [names]
            if not names:
                raise world.WorldError("a check needs somebody to make it")
            facing = [_named(party, str(name)) for name in names]

            dc = arguments.get("dc")
            if isinstance(dc, bool) or not isinstance(dc, int):
                raise world.WorldError(f"{dc!r} is not a difficulty class")

            # An ability, not a modifier. What a score is worth is a rule the
            # ruleset owns, and the score itself is on a sheet the narrator
            # does not — which is why gary is never asked for the number.
            ability = (arguments.get("ability") or "").strip().lower() or None
            if ability and ability not in ruleset.abilities:
                raise world.WorldError(
                    f"{ability!r} is not an ability in this system"
                )

            reason = arguments.get("reason", "")
            said, frames = [], []
            for character in facing:
                modifier = (
                    ruleset.modifier((character.abilities or {}).get(ability, 10))
                    if ability
                    else 0
                )
                outcome = ruleset.resolve(dc=dc, modifier=modifier, reason=reason)
                frames.append(
                    _frame("roll", rolled(outcome.roll, character, outcome, ability))
                )
                said.append(
                    f"{character.name}'s {outcome.reason or 'check'} was a "
                    f"{outcome.degree.value} "
                    f"({outcome.roll.total} against {outcome.dc})"
                )

            await database.flush()
            # One summary covering all of them, because one call asked. A
            # model told only about the last of four would narrate the other
            # three from memory.
            return narration.Result(call, "; ".join(said)), frames

        if call.name in ("begin_combat", "attack", "end_turn", "end_combat"):
            foes = list(
                await database.scalars(
                    select(Adversary).where(Adversary.campaign_id == campaign.id)
                )
            )
            return await _fighting(
                database,
                campaign,
                party,
                foes,
                call,
                arguments,
                rolled,
                moved,
                turn_id,
            )

        if call.name == "move_party":
            place = arguments.get("place", "")
            return await moved(world.MOVED, {"place": place}, f"the party is at {place}")

        if call.name == "remember":
            key, value = arguments.get("key", ""), arguments.get("value", "")
            return await moved(
                world.REMEMBERED, {"key": key, "value": value}, f"{key} is {value}"
            )

        if call.name in ("damage", "heal"):
            # Either side. A monster takes hit points off the same way a
            # character does, and a tool that only reached the party would
            # send gary back to narrating a wound nothing recorded.
            whose, character = await _either_side(
                database, campaign, party, arguments.get("character", "")
            )
            amount = arguments.get("amount")
            kind = world.DAMAGED if call.name == "damage" else world.HEALED
            verb = "took" if call.name == "damage" else "recovered"
            # Folded for the same reason the attack result is: a delta alone
            # leaves gary keeping its own books, and its books and the world's
            # then disagree without either side noticing. The row holds the
            # sheet as it was created, so the standing number has to come from
            # the log.
            # Not guarded: _either_side found this either in the party or in
            # the campaign's adversaries, and world.of folds every one of
            # both, so whoever it found is in the world it just built. A
            # fallback here would be a branch nothing can reach.
            standing = (await world.of(database, campaign.id)).anyone(
                str(character.id)
            )
            moves = -1 if call.name == "damage" else 1
            now = min(
                standing.max_hp, max(0, standing.hp + moves * int(amount or 0))
            )
            return await moved(
                kind,
                {whose: str(character.id), "amount": amount},
                f"{character.name} {verb} {amount} — {character.name} is now "
                f"on {now} of {standing.max_hp}",
            )

        if call.name in ("add_condition", "remove_condition"):
            character = _named(party, arguments.get("character", ""))
            condition = arguments.get("condition", "")
            kind = (
                world.AFFLICTED
                if call.name == "add_condition"
                else world.RELIEVED
            )
            became = "is" if call.name == "add_condition" else "is no longer"
            return await moved(
                kind,
                {"character_id": str(character.id), "condition": condition},
                f"{character.name} {became} {condition}",
            )

        if call.name == "award_experience":
            ruleset = systems.ruleset(campaign.system_slug)

            # All of them or none, for the check's reason: a party survives a
            # thing together, and half an award applied says two of them were
            # there for something all four came through.
            names = arguments.get("awarded") or []
            if isinstance(names, str):
                names = [names]
            if not names:
                raise world.WorldError("an award needs somebody to give it to")
            earning = [_named(party, str(name)) for name in names]

            amount = arguments.get("experience")
            if isinstance(amount, bool) or not isinstance(amount, int):
                raise world.WorldError(f"{amount!r} is not an amount of experience")
            reason = arguments.get("reason", "")

            # Folded once, before anything is written. Where somebody stands
            # is the sheet plus what the log did to it, never the row — the
            # row is where they started and nothing ever writes it again.
            folded = {
                one.id: one for one in (await world.of(database, campaign.id)).party
            }
            said, frames = [], []
            for character in earning:
                # A lookup rather than a search: `_named` already found them
                # in the party and the fold is built from that same party, so
                # a miss here is impossible and a branch guarding it would be
                # one nothing could ever take.
                standing = folded[str(character.id)]

                # The bound, before anything is written. Damage is bounded by
                # a fight and experience by nothing, so without this a model
                # having a strange turn could hand out ten thousand and jump
                # four levels in a sentence.
                most = ruleset.most_per_award(standing.level)
                if amount > most:
                    raise world.WorldError(
                        f"{amount} is more experience than this system allows "
                        f"in one award at level {standing.level}; the most is "
                        f"{most}"
                    )

                await world.record(
                    database,
                    campaign.id,
                    world.EARNED,
                    {
                        "character_id": str(character.id),
                        "amount": amount,
                        "reason": reason,
                    },
                    turn_id,
                    scene_id,
                )
                frames.append(
                    _frame(
                        "world",
                        {
                            "kind": world.EARNED,
                            "character": character.name,
                            "amount": amount,
                            "reason": reason,
                        },
                    )
                )
                total = standing.experience + amount
                said.append(
                    f"{character.name} gained {amount} experience"
                    f"{f' for {reason}' if reason else ''} and is on {total}"
                )

                # Gary proposed the award; everything below is the engine's
                # answer to it, which is why it is a second event rather than
                # a field on the first one.
                for reached in range(
                    standing.level + 1, ruleset.level_at(total) + 1
                ):
                    gained = ruleset.gains(
                        character.character_class, character.abilities or {}
                    )
                    await world.record(
                        database,
                        campaign.id,
                        world.LEVELLED,
                        {
                            "character_id": str(character.id),
                            "level": reached,
                            "hit_points": gained,
                        },
                        turn_id,
                        scene_id,
                    )
                    frames.append(
                        _frame(
                            "world",
                            {
                                "kind": world.LEVELLED,
                                "character": character.name,
                                "level": reached,
                                "hit_points": gained,
                            },
                        )
                    )
                    said.append(
                        f"{character.name} reached level {reached} "
                        f"and gained {gained} hit points"
                    )

            await database.flush()
            return narration.Result(call, "; ".join(said)), frames

        if call.name == "pass_time":
            minutes = arguments.get("minutes")
            return await moved(
                world.ELAPSED, {"minutes": minutes}, f"{minutes} minutes passed"
            )

        if call.name == "scene":
            # Noted, not acted on. A boundary inside a turn would leave that
            # turn's narration half in each scene, and the close pass would
            # run inside a stream that is still open. The turn that ends a
            # scene is the last turn of it.
            title = arguments.get("title", "")
            return narration.Result(
                call, f"the scene will change to {title!r} when this turn ends"
            ), []

        raise world.WorldError(f"gary has no {call.name!r} to call")

    except (dice.DiceError, world.WorldError, systems.SystemError) as error:
        # Refused, not fatal. The narrator is told what went wrong and carries
        # on, and the player sees it — a tool that quietly did nothing would
        # leave the prose describing something that never happened.
        return narration.Result(call, str(error), failed=True), [
            _frame("error", {"detail": str(error), "code": "refused_tool"})
        ]


def _gary_for(campaign: Campaign) -> narration.Narrator:
    """The narrator this campaign runs on, or a refusal saying why not.

    A deployment with no key is what a fresh app is until its secrets are set.
    Refused before a byte is sent, because this is one of the few things that
    can still be said with a status — after the stream opens it cannot — and
    because letting it escape reads as gary crashing rather than as gary not
    being configured.
    """
    try:
        return narration.narrator(campaign.model or narration.models.default())
    except narration.NarrationError as error:
        logger.error("gm.unconfigured", reason=str(error))
        raise Refusal(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "gm_unavailable",
            "gary cannot reach a model on this deployment",
        ) from error


async def _left_a_mark(database, turn_id: uuid.UUID) -> bool:
    """Did this turn change anything that outlives it?

    Asked of the database rather than tracked in a variable, because what
    matters is what was actually written — a tool the engines refused looks
    exactly like a tool that ran, right up until you go looking for the row.
    """
    rolled = await database.scalar(
        select(func.count()).select_from(Roll).where(Roll.turn_id == turn_id)
    )
    changed = await database.scalar(
        select(func.count())
        .select_from(WorldEvent)
        .where(WorldEvent.turn_id == turn_id)
    )
    return bool(rolled or changed)


async def _stream(campaign_id, scene_id, message, gary):
    """The turn, as it happens.

    Opens its own session: this outlives the request handler, and the
    request-scoped one is closed the moment that returns.
    """
    factory = async_sessionmaker(db.engine, expire_on_commit=False)

    async with factory() as database:
        campaign = await database.get(Campaign, campaign_id)
        party = await _party(database, campaign_id)
        # This scene's turns, not the campaign's. Prose stops being memory at
        # a scene boundary; what crosses one is the world and the recaps.
        scene = await database.get(Scene, scene_id)
        turns = await scenes.turns_in(database, scene_id)

        ruleset = systems.ruleset(campaign.system_slug)
        module = systems.module(campaign.system_slug, campaign.module_slug)
        state = await world.of(database, campaign_id)

        prompt = narration.Prompt(
            briefing=ruleset.briefing(),
            model=campaign.model or narration.models.default(),
            system_slug=campaign.system_slug,
            module_slug=campaign.module_slug,
            module_title=module.title,
            module_premise=module.premise,
            module_hook=module.hook,
            world=world.render(state),
            message=message,
            transcript=[(turn.role, turn.content) for turn in turns],
            scene_title=scene.title,
            recaps=await scenes.recaps(database, campaign_id),
        )

        gm_turn = Turn(
            campaign_id=campaign_id,
            scene_id=scene_id,
            role="gm",
            content="",
            complete=False,
        )
        database.add(gm_turn)
        await database.flush()

        yield _frame("turn", {"turn_id": str(gm_turn.id), "role": "gm"})

        spoken: list[str] = []
        finished = False
        wanted_scene: str | None = None
        generator = gary.narrate(prompt)
        sending: list[narration.Result] | None = None

        try:
            while True:
                try:
                    event = await generator.asend(sending)
                except StopAsyncIteration:
                    finished = True
                    break

                sending = None

                if isinstance(event, narration.Said):
                    if event.text:
                        spoken.append(event.text)
                        yield _frame("narration", {"text": event.text})
                elif isinstance(event, narration.Calls):
                    results = []
                    for call in event.calls:
                        result, frames = await _run(
                            database, campaign, party, call, gm_turn.id, scene_id
                        )
                        if call.name == "scene":
                            # Acted on once the stream is done, not here.
                            wanted_scene = call.arguments.get("title", "")
                        results.append(result)
                        for frame in frames:
                            yield frame
                    sending = results
                else:
                    # Refused. Not an error: gary declined, and that is an
                    # answer. An else rather than a third isinstance because
                    # the three are the whole union — a fourth arm would be a
                    # branch nothing can reach.
                    #
                    # Whether the turn survives is decided in one place, below,
                    # on whether it did anything. A decline that changed
                    # nothing leaves nothing behind; a decline that came after
                    # the dice were already thrown is not nothing.
                    yield _frame(
                        "refusal", {"detail": event.detail, "code": "gm_refused"}
                    )
                    return

        except narration.NarrationError as error:
            logger.error("gm.unreachable", campaign_id=str(campaign_id))
            yield _frame(
                "error", {"detail": str(error), "code": "gm_unavailable"}
            )
            return

        finally:
            # Reached on a normal end, on a refusal, on an unreachable model
            # and on the client walking away alike — which is why the decision
            # about what to keep is only made here.
            #
            # A turn cut off is kept and marked rather than dropped: the next
            # turn is told the transcript, and a hole in it is a story that
            # never happened.
            await generator.aclose()
            if spoken:
                gm_turn.content = "".join(spoken).strip()
                gm_turn.complete = finished
                await database.commit()
            elif await _left_a_mark(database, gm_turn.id):
                # Silence is not nothing. Gary can spend a whole turn calling
                # tools and never reach a word of prose — and deleting that
                # turn takes its rolls with it, because they cascade, while
                # leaving the damage it dealt behind, because world events do
                # not. What that produces is a transcript in which nothing
                # happened beside a party that is bleeding, and no way to ever
                # find out why.
                gm_turn.content = ""
                gm_turn.complete = False
                await database.commit()
            else:
                await database.delete(gm_turn)
                await database.commit()

        # Now the turn is over, and only now. Closing a scene runs a whole
        # second pass through a model, and doing that mid-stream would stall
        # the narration the player is reading.
        if wanted_scene is not None:
            opened = await scenes.begin(
                database, campaign, party, _run, wanted_scene
            )
            await database.commit()
            yield _frame(
                "scene",
                {"scene_id": str(opened.id), "title": opened.title,
                 "number": opened.number},
            )

        yield _frame("done", {"turn_id": str(gm_turn.id), "role": "gm"})
