"""One real turn against a real model, by hand.

Nothing in any of the three test tiers calls a model — they all run the
double, the same trade already made for Google and Facebook. So the specs
prove what gary does with a narration and prove nothing about whether a given
model can hold up its end. This is the only thing that does.

What it is looking for is not prose quality. It is whether the model goes
*through* the engines: asks for the roll rather than inventing a number,
asks for the check rather than announcing a degree, records a change to the
world rather than asserting one. A model that narrates around the tools
produces a game that reads fine and is not being adjudicated by anything,
which is the failure this whole architecture exists to prevent — and the
failure a spec suite running a double can never see.

    pnpm --filter gary-api smoke
    pnpm --filter gary-api smoke -- deepseek/deepseek-v3.2

No database, and no writes anywhere: the world lives in memory for the length
of the turn. It costs a fraction of a cent and reports what it cost.
"""

import asyncio
import os
import sys

import httpx

from gary_api import dice, narration, systems, world
from gary_api import play as play_module
from gary_api.narration import models

# Chosen to make a well-behaved model reach for two different tools: a check
# against the rules, and a change to the world. A model that answers this with
# prose alone has told us something.
SAYS = (
    "I search the far wall for a hidden catch, and if I find one I open it "
    "and step through."
)

DIFFICULTY = 15


def spend() -> float | None:
    """What this key has spent so far, in dollars."""
    try:
        response = httpx.get(
            "https://openrouter.ai/api/v1/key",
            headers={"authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
            timeout=15,
        )
        response.raise_for_status()
        return float(response.json()["data"]["usage"])
    except Exception:
        return None


def a_world(opening: bool = False) -> world.World:
    """The world as gary would have it — mid-scene, or at the very start.

    An opening gets the second. A campaign that has not begun has one event
    in its log, the module's own starting place, and nothing else; opening
    against a world that is already 25 minutes into a fight would report on a
    prompt gary never sends.
    """
    if opening:
        return world.World(
            place=systems.rulesets()[0].modules[0].opening,
            party=[
                world.Member(
                    id="00000000-0000-0000-0000-000000000001",
                    name="Bramble",
                    character_class="rogue",
                    level=1,
                    max_hp=8,
                    hp=8,
                )
            ],
        )

    return world.World(
        place="a stone chamber below the belfry, ankle-deep in water",
        minutes=25,
        facts={"bell-rings": "3"},
        party=[
            world.Member(
                id="00000000-0000-0000-0000-000000000001",
                name="Bramble",
                character_class="rogue",
                level=1,
                max_hp=8,
                hp=6,
            )
        ],
    )


def run_tool(call, ruleset, state, log):
    """Answer a tool the way the router would, without a database."""
    arguments = call.arguments or {}
    log.append((call.name, arguments))

    try:
        if call.name == "roll":
            made = dice.roll(arguments.get("notation", ""), arguments.get("reason", ""))
            return f"{made.notation} came up {made.total}", made
        if call.name == "check":
            outcome = ruleset.resolve(
                dc=int(arguments.get("dc", DIFFICULTY)),
                modifier=int(arguments.get("modifier") or 0),
                reason=arguments.get("reason", "check"),
            )
            return (
                f"{arguments.get('character', 'they')} rolled "
                f"{outcome.roll.total} against {outcome.dc}: "
                f"{outcome.degree.value}"
            ), outcome
        if call.name == "move_party":
            state.place = arguments.get("place", state.place)
            return f"the party is at {state.place}", None
        if call.name == "remember":
            state.facts[arguments.get("key", "?")] = arguments.get("value", "")
            return f"noted {arguments.get('key')}", None
        if call.name == "pass_time":
            state.minutes += int(arguments.get("minutes") or 0)
            return f"{arguments.get('minutes')} minutes passed", None
        if call.name in ("damage", "heal"):
            return f"{arguments.get('character')} is noted as {call.name}d", None
        if call.name in ("add_condition", "remove_condition"):
            return f"condition {call.name.split('_')[0]}ed", None
        if call.name == "award_experience":
            # Priced by the real ruleset, so a smoke run shows whether the
            # model respects the bound rather than only whether it can spell
            # the tool. Nothing is stored — this whole harness holds the world
            # in memory — so the level is worked out from the award alone.
            wanted = arguments.get("awarded") or []
            amount = int(arguments.get("experience") or 0)
            most = ruleset.most_per_award(1)
            if amount > most:
                return (
                    f"refused: {amount} is more than the {most} this system "
                    f"allows in one award"
                ), None
            reached = ruleset.level_at(amount)
            return (
                f"{', '.join(str(one) for one in wanted) or 'nobody'} gained "
                f"{amount} experience and is level {reached}"
            ), None
        if call.name == "begin_combat":
            # Named back, so a smoke run shows whether the model authored a
            # monster or asked for a fight with nothing in it.
            wanted = arguments.get("adversaries") or []
            names = ", ".join(str(one.get("name")) for one in wanted if isinstance(one, dict))
            return f"a fight began against {names or 'nothing'}", None
        if call.name == "attack":
            return (
                f"{arguments.get('attacker')} swung at {arguments.get('target')}",
                None,
            )
        if call.name == "end_turn":
            return "that turn is over", None
        if call.name == "end_combat":
            return "the fight is over", None
        if call.name == "scene":
            # Noted, exactly as the router notes it. One turn is not a scene,
            # so there is nothing here to close — but a tool the model is
            # offered and this cannot answer would report a failure the real
            # router does not have.
            return (
                f"the scene will change to {arguments.get('title')!r} "
                "when this turn ends"
            ), None
    except Exception as error:
        return f"refused: {error}", None

    return f"gary has no {call.name!r}", None


async def play(model: str, opening: bool = False) -> int:
    # Whatever is registered first, rather than a system named here — this
    # file is outside the systems package and tests/test_pluggable.py fails
    # the build if anything out here learns a system's name. It caught this
    # exact line.
    ruleset = systems.rulesets()[0]
    module = ruleset.modules[0]
    state = a_world(opening)

    prompt = narration.Prompt(
        briefing=ruleset.briefing(),
        model=model,
        system_slug=ruleset.slug,
        module_slug=module.slug,
        module_title=module.title,
        module_premise=module.premise,
        module_hook=module.hook,
        world=world.render(state),
        # The opening answers gary-api's instruction rather than a player, so
        # it is the one thing here where the transcript is genuinely empty.
        message=play_module.OPENING if opening else SAYS,
        transcript=[] if opening else [("player", SAYS)],
    )

    gary = narration.narrator(model)
    called: list[tuple[str, dict]] = []
    graded = []
    said: list[str] = []

    print(f"model    {model}")
    print(f"system   {ruleset.name}")
    print(f"module   {module.title}")
    if opening:
        print("player   (nobody has said anything — this is the opening)")
    else:
        print(f'player   "{SAYS}"')
    print()
    print("narration " + "-" * 60)

    generator = gary.narrate(prompt)
    sending = None
    try:
        while True:
            try:
                event = await generator.asend(sending)
            except StopAsyncIteration:
                break
            sending = None

            if isinstance(event, narration.Said):
                said.append(event.text)
                sys.stdout.write(event.text)
                sys.stdout.flush()
            elif isinstance(event, narration.Calls):
                results = []
                for call in event.calls:
                    summary, detail = run_tool(call, ruleset, state, called)
                    if detail is not None and hasattr(detail, "degree"):
                        graded.append(detail)
                    results.append(narration.Result(call, summary))
                sending = results
            else:
                # Refused — the only event left, so an else rather than a
                # third isinstance that nothing could fall past.
                print(f"\n\nrefused: {event.detail}")
    except narration.NarrationError as error:
        print(f"\n\nUNREACHABLE: {error}")
        return 1
    finally:
        await generator.aclose()

    print("\n" + "-" * 70)
    print()

    if called:
        print("tools it called")
        for name, arguments in called:
            print(f"  {name:<18}{arguments}")
    else:
        print("tools it called: NONE")

    print()
    print("did it go through the engines?")
    asked_for_a_number = any(name in ("roll", "check") for name, _ in called)
    print(
        f"  asked for a roll or check   {'yes' if asked_for_a_number else 'NO'}"
        f"{'' if asked_for_a_number else '   <- it decided the outcome itself'}"
    )
    if graded:
        allowed = [degree.value for degree in ruleset.degrees]
        for outcome in graded:
            fine = outcome.degree.value in allowed
            print(
                f"  degree from the rules       {outcome.degree.value} "
                f"({'valid' if fine else 'NOT ONE THIS SYSTEM GRADES'})"
            )
    changed = [name for name, _ in called if name not in ("roll", "check")]
    print(f"  recorded a world change     {', '.join(changed) if changed else 'no'}")

    prose = "".join(said)
    print(f"\nwrote {len(prose.split())} words in {len(said)} pieces")
    return 0


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        print(
            "OPENROUTER_API_KEY is not set, so there is nothing to smoke-test.\n"
            "This is the one check that talks to a real model; without a key it\n"
            "would pass by doing nothing, which is worse than not running it.",
            file=sys.stderr,
        )
        return 2

    if os.environ.get("GM_FAKE") == "1":
        print(
            "GM_FAKE=1, which would test the double against itself.",
            file=sys.stderr,
        )
        return 2

    wanted = [one for one in sys.argv[1:] if one != "--opening"]
    opening = "--opening" in sys.argv[1:]
    model = wanted[0] if wanted else models.default()

    before = spend()
    code = asyncio.run(play(model, opening))
    after = spend()

    if before is not None and after is not None:
        print(f"cost  ${after - before:.5f}   (key total ${after:.4f})")
    else:
        print("cost  unknown — could not read the key's usage")

    return code
