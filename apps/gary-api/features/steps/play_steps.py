import json
import os
import uuid

import parse
from behave import given, register_type, then, when

from environment import sql, with_session
from gary_api import dice, narration, systems, world
from gary_api.narration import fake
from gary_api.narration.fake import DIRECTIVE

# behave's placeholders are greedy, so `the {character_class}` would swallow
# `rogue in "add-1e"` whole and two perfectly distinct steps would collide.
# Naming the shapes is what keeps the Gherkin reading the way it should
# instead of being reworded around the parser.


@parse.with_pattern(r'[A-Za-z][A-Za-z-]*|""')
def a_class(text):
    return text.strip('"')


@parse.with_pattern(r'"[^"]*"(?:\s*,\s*"[^"]*")*')
def some_names(text):
    return [part.strip().strip('"') for part in text.split(",")]


@parse.with_pattern(r"[a-z0-9][a-z0-9-]*(?:\s*,\s*[a-z0-9][a-z0-9-]*)*")
def some_slugs(text):
    return [part.strip() for part in text.split(",")]


@parse.with_pattern(r'[^"]*')
def inside_quotes(text):
    """Anything that is not a quote.

    Without this a trailing placeholder swallows its own closing quote and
    everything after it, so `running "{module}"` also matches
    `running "x" with "y"` and two distinct steps collide.
    """
    return text


register_type(
    Class=a_class, Names=some_names, Slugs=some_slugs, Q=inside_quotes
)

# A campaign id that is a real uuid and belongs to nobody, for the scenarios
# about reaching something that is not there.
NOWHERE = "00000000-0000-0000-0000-00000000dead"


def _headers(context):
    if getattr(context, "token", None):
        return {"authorization": f"Bearer {context.token}"}
    return {}


def _body(context):
    return context.response.json()


def _campaign_id(context):
    assert getattr(context, "campaign", None), "no campaign in this scenario"
    return context.campaign["id"]


def _character_id(context, name):
    found = context.characters.get(name)
    assert found, f"no character called {name} in this scenario"
    return found["id"]


def _record(context, kind, payload):
    campaign_id = uuid.UUID(_campaign_id(context))
    with_session(lambda s: world.record(s, campaign_id, kind, payload))


# ---------------------------------------------------------------- catalogue


@then("the systems offered should be {expected:Slugs}")
def step_systems_offered(context, expected):
    actual = [system["slug"] for system in _body(context)]
    assert actual == expected, f"expected {expected}, got {actual}"


@then("every system should carry a name and a blurb")
def step_systems_described(context):
    for system in _body(context):
        assert system["name"].strip(), f"{system['slug']} has no name"
        assert system["blurb"].strip(), f"{system['slug']} has no blurb"


@then("every system should have at least one module")
def step_systems_playable(context):
    for system in _body(context):
        assert system["modules"], f"{system['slug']} has nothing to play"


@then('"{slug}" should be among its modules')
def step_module_listed(context, slug):
    actual = [module["slug"] for module in _body(context)["modules"]]
    assert slug in actual, f"expected {slug} among {actual}"


@then("every module should carry a title and a premise")
def step_modules_described(context):
    for module in _body(context)["modules"]:
        assert module["title"].strip(), f"{module['slug']} has no title"
        assert module["premise"].strip(), f"{module['slug']} has no premise"


# ---------------------------------------------------------------- campaigns


@given('I started "{name}" on "{system}" running "{module:Q}"')
@when('I start "{name}" on "{system}" running "{module:Q}"')
def step_start_campaign(context, name, system, module):
    context.response = context.client.post(
        "/campaigns",
        json={"name": name, "system": system, "module": module},
        headers=_headers(context),
    )
    if context.response.status_code == 201:
        context.campaign = _body(context)
        context.characters = {}


@when("I read that campaign")
def step_read_campaign(context):
    context.response = context.client.get(
        f"/campaigns/{_campaign_id(context)}", headers=_headers(context)
    )


@then("the campaign should have no turns yet")
def step_no_turns(context):
    assert _body(context)["turns"] == 0, _body(context)["turns"]


@then("my campaigns should be {expected:Names}")
def step_my_campaigns(context, expected):
    actual = [campaign["name"] for campaign in _body(context)]
    assert actual == expected, f"expected {expected}, got {actual}"


@then("I should have no campaigns")
def step_no_campaigns(context):
    assert _body(context) == [], _body(context)


@given("another account has a campaign")
def step_other_campaign(context):
    mine = getattr(context, "token", None)
    context.execute_steps(
        '''
        Given I am signed in at google as "stranger@example.com" named "A Stranger"
        And I started "Not yours" on "dnd-5e" running "the-drowned-belfry"
        '''
    )
    context.other_campaign = context.campaign
    context.campaign = None
    # Back to whoever the scenario was signed in as, including nobody.
    context.token = mine


@when("I read their campaign")
def step_read_their_campaign(context):
    context.response = context.client.get(
        f"/campaigns/{context.other_campaign['id']}", headers=_headers(context)
    )


# --------------------------------------------------------------- characters


@given('I add "{name}" the {character_class:Class}')
@when('I add "{name}" the {character_class:Class}')
def step_add_character(context, name, character_class):
    """Add somebody without saying who plays them.

    The first one is yours and the rest are companions, which is what every
    scenario using this phrasing means: it wants a party that can play, not a
    statement about control. Scenarios that are *about* control say "as mine"
    or "as a companion" and get exactly what they say.
    """
    taken = any(
        one["played_by"] == "player" for one in _party(context)
    )
    _add(context, name, character_class, not taken)


@when('I add "{name}" the {character_class:Class} in "{system}"')
def step_add_character_in_system(context, name, character_class, system):
    context.execute_steps(
        f'Given I started "A test" on "{system}" running '
        f'"{_first_module(system)}"'
    )
    context.execute_steps(f'When I add "{name}" the {character_class}')


@when('I add "{name}" the {character_class:Class} to their campaign')
def step_add_to_their_campaign(context, name, character_class):
    context.response = context.client.post(
        f"/campaigns/{context.other_campaign['id']}/characters",
        json={"name": name, "character_class": character_class},
        headers=_headers(context),
    )


def _first_module(system):
    from gary_api import systems

    return systems.ruleset(system).modules[0].slug


@when("I read the party")
def step_read_party(context):
    context.response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/characters", headers=_headers(context)
    )


@when("I read their party")
def step_read_their_party(context):
    context.response = context.client.get(
        f"/campaigns/{context.other_campaign['id']}/characters",
        headers=_headers(context),
    )


@then("the party should be {expected:Names}")
def step_party_is(context, expected):
    actual = [character["name"] for character in _body(context)]
    assert actual == expected, f"expected {expected}, got {actual}"


@then("the party should be empty")
def step_party_empty(context):
    assert _body(context) == [], _body(context)


@then("the character should be level {level:d}")
def step_character_level(context, level):
    # Its own step rather than the generic field one, which compares strings
    # and would read 1 as "1".
    assert _body(context)["level"] == level, _body(context)


# ------------------------------------------------------------------- world


@when("I read the world")
def step_read_world(context):
    context.response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/world", headers=_headers(context)
    )


@when("I read their world")
def step_read_their_world(context):
    context.response = context.client.get(
        f"/campaigns/{context.other_campaign['id']}/world", headers=_headers(context)
    )


@when("I read what has happened")
def step_read_history(context):
    context.response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/history", headers=_headers(context)
    )


@then("the party should be somewhere")
def step_somewhere(context):
    assert _body(context)["place"].strip(), "the world started nowhere"


@then("no time should have passed")
def step_no_time(context):
    assert _body(context)["minutes"] == 0, _body(context)["minutes"]


@then("nothing should be remembered yet")
def step_nothing_remembered(context):
    assert _body(context)["facts"] == {}, _body(context)["facts"]


@given('the party moves to "{place}"')
@when('the party moves to "{place}"')
def step_move(context, place):
    _record(context, world.MOVED, {"place": place})


@then('the party should be at "{place}"')
def step_party_at(context, place):
    assert _body(context)["place"] == place, _body(context)["place"]


@given('gary remembers "{key}" as "{value}"')
@when('gary remembers "{key}" as "{value}"')
def step_remember(context, key, value):
    _record(context, world.REMEMBERED, {"key": key, "value": value})


@then('"{key}" should be remembered as "{value}"')
def step_remembered(context, key, value):
    facts = _body(context)["facts"]
    assert facts.get(key) == value, facts


@then("{count:d} fact should be remembered")
@then("{count:d} facts should be remembered")
def step_fact_count(context, count):
    facts = _body(context)["facts"]
    assert len(facts) == count, facts


@given("{minutes:d} minutes pass")
@when("{minutes:d} minutes pass")
def step_time_passes(context, minutes):
    _record(context, world.ELAPSED, {"minutes": minutes})


@then("{minutes:d} minutes should have passed")
def step_time_passed(context, minutes):
    assert _body(context)["minutes"] == minutes, _body(context)["minutes"]


@given('"{who}" takes {amount:d} damage')
@when('"{who}" takes {amount:d} damage')
def step_damage(context, who, amount):
    _record(
        context,
        world.DAMAGED,
        {"character_id": _character_id(context, who), "amount": amount},
    )


@given('"{who}" heals {amount:d}')
@when('"{who}" heals {amount:d}')
def step_heal(context, who, amount):
    _record(
        context,
        world.HEALED,
        {"character_id": _character_id(context, who), "amount": amount},
    )


def _member(context, who):
    for member in _body(context)["party"]:
        if member["name"] == who:
            return member
    raise AssertionError(f"{who} is not in the party: {_body(context)['party']}")


@then('"{who}" should be {amount:d} hit points down')
def step_hp_down(context, who, amount):
    member = _member(context, who)
    lost = member["max_hp"] - member["hp"]
    assert lost == amount, f"expected {amount} lost, got {lost}"


@then('"{who}" should be at full hit points')
def step_hp_full(context, who):
    member = _member(context, who)
    assert member["hp"] == member["max_hp"], member


@then('"{who}" should be on {amount:d} hit points')
def step_hp_exactly(context, who, amount):
    assert _member(context, who)["hp"] == amount, _member(context, who)


@then('"{who}" should be down')
def step_is_down(context, who):
    assert _member(context, who)["down"], _member(context, who)


@given('"{who}" becomes "{condition}"')
@when('"{who}" becomes "{condition}"')
def step_afflict(context, who, condition):
    _record(
        context,
        world.AFFLICTED,
        {"character_id": _character_id(context, who), "condition": condition},
    )


@when('"{who}" stops being "{condition}"')
def step_relieve(context, who, condition):
    _record(
        context,
        world.RELIEVED,
        {"character_id": _character_id(context, who), "condition": condition},
    )


@then('"{who}" should be "{condition}"')
def step_has_condition(context, who, condition):
    assert condition in _member(context, who)["conditions"], _member(context, who)


@then('"{who}" should not be "{condition}"')
def step_lacks_condition(context, who, condition):
    assert condition not in _member(context, who)["conditions"], _member(context, who)


@then('"{who}" should have {count:d} condition')
@then('"{who}" should have {count:d} conditions')
def step_condition_count(context, who, count):
    actual = _member(context, who)["conditions"]
    assert len(actual) == count, actual


@then("{count:d} things should have happened")
def step_history_count(context, count):
    # The move that opened the campaign is not one of the things a scenario
    # arranged, so it is discounted here rather than counted in every spec.
    events = [event for event in _body(context) if event["seq"] > 1]
    assert len(events) == count, [event["kind"] for event in _body(context)]


@then("they should be in the order they happened")
def step_history_ordered(context):
    sequence = [event["seq"] for event in _body(context)]
    assert sequence == sorted(sequence), sequence
    assert len(set(sequence)) == len(sequence), f"repeated sequence numbers: {sequence}"


# ----------------------------------------------------------------- playing


def _say(context, message, campaign_id, stop_after=None):
    """Take a turn and collect the stream.

    Frames are collected as they arrive rather than read at the end, because
    what several of these scenarios are about is that they arrive at all
    rather than in one lump at the close.
    """
    context.events = []
    if not hasattr(context, "all_rolls"):
        context.all_rolls = []

    with context.client.stream(
        "POST",
        f"/campaigns/{campaign_id}/turns",
        json={"message": message},
        headers=_headers(context),
    ) as response:
        context.response = response
        if response.status_code != 200:
            # Read it while the connection is open, so the shared steps that
            # assert on the body still have one to read.
            response.read()
            return

        name = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                name = line[len("event: ") :].strip()
            elif line.startswith("data: "):
                context.events.append((name, json.loads(line[len("data: ") :])))
                if stop_after is not None and len(context.events) >= stop_after:
                    # Walk away mid-turn, as a closed tab does.
                    break

    context.all_rolls += [
        data["total"] for kind, data in context.events if kind == "roll"
    ]


def _of(context, kind):
    return [data for name, data in context.events if name == kind]


@given('I said "{message}"')
@when('I say "{message}"')
def step_say(context, message):
    _say(context, message, _campaign_id(context))


@when('I say "{message}" in that campaign')
def step_say_in_that(context, message):
    _say(context, message, _campaign_id(context))


@when('I say "{message}" in their campaign')
def step_say_in_theirs(context, message):
    _say(context, message, context.other_campaign["id"])


@when('I say "{message}" in a campaign that does not exist')
def step_say_nowhere(context, message):
    _say(context, message, NOWHERE)


@when('gary is interrupted halfway through "{message}"')
def step_interrupted(context, message):
    """Read a few frames, then walk away — as a closed tab does.

    Through the endpoint rather than the client, because the test client's
    transport has no backpressure: a reader that stops reading does not stop
    the writer, so the turn would run forever instead of being cut off. What
    is exercised here is the real endpoint and the real generator; closing it
    early is exactly what Starlette does when a socket goes away.
    """
    from gary_api import play
    from gary_api.models import Campaign, User

    campaign_id = uuid.UUID(_campaign_id(context))

    async def work(session):
        campaign = await session.get(Campaign, campaign_id)
        user = await session.get(User, campaign.user_id)
        response = await play.take_turn(
            campaign_id, play.NewTurn(message=message), session, user
        )

        frames = response.body_iterator
        seen = 0
        async for _ in frames:
            seen += 1
            if seen >= 3:
                break
        await frames.aclose()

    with_session(work)


@then("the turn should stream to completion")
def step_streamed(context):
    assert context.response.status_code == 200, context.response.status_code
    assert _of(context, "done"), [name for name, _ in context.events]


@then('the narration should mention "{word}"')
def step_narration_mentions(context, word):
    said = "".join(data["text"] for data in _of(context, "narration"))
    assert word.lower() in said.lower(), said


@then("the narration should arrive in more than one piece")
def step_narration_in_pieces(context):
    pieces = _of(context, "narration")
    assert len(pieces) > 1, f"arrived in {len(pieces)} piece(s)"


@then("the transcript should hold {count:d} turn")
@then("the transcript should hold {count:d} turns")
def step_transcript_length(context, count):
    rows = sql(
        "SELECT role, content, complete FROM turns WHERE campaign_id = :id"
        " ORDER BY created_at, id",
        id=_campaign_id(context),
    )
    assert len(rows) == count, [(row[0], row[1][:30]) for row in rows]


@then("gary's turn should be marked incomplete")
def step_incomplete(context):
    rows = sql(
        "SELECT complete FROM turns WHERE campaign_id = :id AND role = 'gm'",
        id=_campaign_id(context),
    )
    assert rows, "gary took no turn at all"
    assert not rows[-1][0], "gary's turn was marked finished"


@then('a roll of "{notation}" should have been made for "{reason}"')
def step_roll_made(context, notation, reason):
    rolls = _of(context, "roll")
    assert any(
        roll["notation"] == notation and roll["reason"] == reason for roll in rolls
    ), rolls


@then("the roll should be recorded against gary's turn")
def step_roll_recorded(context):
    rows = sql(
        "SELECT r.notation FROM rolls r JOIN turns t ON t.id = r.turn_id"
        " WHERE t.campaign_id = :id AND t.role = 'gm'",
        id=_campaign_id(context),
    )
    assert rows, "no roll was written down"


@then("the move should be recorded against gary's turn")
def step_move_recorded(context):
    rows = sql(
        "SELECT e.kind FROM world_events e JOIN turns t ON t.id = e.turn_id"
        " WHERE t.campaign_id = :id AND t.role = 'gm'",
        id=_campaign_id(context),
    )
    assert rows, "the world changed but nothing says which turn did it"


@then("narration should arrive after the roll")
def step_narration_after_roll(context):
    order = [name for name, _ in context.events]
    assert "roll" in order, order
    assert "narration" in order[order.index("roll") :], order


@then("the roll total should be between {low:d} and {high:d}")
def step_roll_within(context, low, high):
    rolls = _of(context, "roll")
    assert rolls, "nothing was rolled"
    for roll in rolls:
        assert low <= roll["total"] <= high, roll


@then("no roll should have been recorded")
def step_no_roll(context):
    rows = sql(
        "SELECT r.id FROM rolls r JOIN turns t ON t.id = r.turn_id"
        " WHERE t.campaign_id = :id",
        id=_campaign_id(context),
    )
    assert not rows, f"{len(rows)} roll(s) were written down"


@given("the dice are seeded with {value:d}")
@when("the dice are seeded with {value:d} again")
def step_seed(context, value):
    dice.seed(value)


@then("both rolls should have the same total")
def step_same_total(context):
    totals = context.all_rolls
    assert len(totals) == 2, totals
    assert totals[0] == totals[1], totals


@then("the stream should carry an error")
def step_stream_error(context):
    assert _of(context, "error"), [name for name, _ in context.events]


@then("the stream should carry a refusal")
def step_stream_refusal(context):
    assert _of(context, "refusal"), [name for name, _ in context.events]


@then("the refusal should say why in words")
def step_refusal_words(context):
    said = _of(context, "refusal")[0]["detail"]
    assert len(said.split()) > 3, said


@then("gary should have been sent {count:d} prior turn")
@then("gary should have been sent {count:d} prior turns")
def step_prompt_transcript(context, count):
    assert fake.LAST is not None, "gary was never asked"
    assert len(fake.LAST.transcript) == count, fake.LAST.transcript


@then("the party should have been among what gary was sent")
def step_prompt_party(context):
    assert fake.LAST is not None, "gary was never asked"
    for name in context.characters:
        assert name in fake.LAST.world, fake.LAST.world


@then('gary should have been told the module is "{slug}"')
def step_prompt_module(context, slug):
    assert fake.LAST.module_slug == slug, fake.LAST.module_slug


@then('gary should have been told the system is "{slug}"')
def step_prompt_system(context, slug):
    assert fake.LAST.system_slug == slug, fake.LAST.system_slug


@then("the check should have been recorded against {dc:d}")
def step_check_recorded(context, dc):
    rows = sql(
        "SELECT r.dc, r.degree FROM rolls r JOIN turns t ON t.id = r.turn_id"
        " WHERE t.campaign_id = :id AND r.dc IS NOT NULL",
        id=_campaign_id(context),
    )
    assert rows, "no check was written down"
    assert rows[-1][0] == dc, rows[-1]


@then("the degree should be one this system grades")
def step_degree_valid(context):
    from gary_api import systems

    allowed = [d.value for d in systems.ruleset(fake.LAST.system_slug).degrees]
    graded = [roll["degree"] for roll in _of(context, "roll") if roll.get("degree")]
    assert graded, "nothing was graded"
    for degree in graded:
        assert degree in allowed, f"{degree} is not one of {allowed}"


@then("this system should grade {count:d} ways")
def step_degree_count(context, count):
    from gary_api import systems

    allowed = systems.ruleset(fake.LAST.system_slug).degrees
    assert len(allowed) == count, [degree.value for degree in allowed]


def _world(context):
    response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/world", headers=_headers(context)
    )
    assert response.status_code == 200, response.status_code
    return response.json()


@then('the world should say the party is at "{place}"')
def step_world_place(context, place):
    assert _world(context)["place"] == place, _world(context)["place"]


@then('the world should remember "{key}" as "{value}"')
def step_world_fact(context, key, value):
    facts = _world(context)["facts"]
    assert facts.get(key) == value, facts


@then('the world should have "{who}" {amount:d} hit points down')
def step_world_damage(context, who, amount):
    member = next(m for m in _world(context)["party"] if m["name"] == who)
    assert member["max_hp"] - member["hp"] == amount, member


@then('the world should have "{who}" at full hit points')
def step_world_full(context, who):
    member = next(m for m in _world(context)["party"] if m["name"] == who)
    assert member["hp"] == member["max_hp"], member


@then('the world should have "{who}" "{condition}"')
def step_world_condition(context, who, condition):
    member = next(m for m in _world(context)["party"] if m["name"] == who)
    assert condition in member["conditions"], member


@then("the world should say {minutes:d} minutes have passed")
def step_world_minutes(context, minutes):
    assert _world(context)["minutes"] == minutes, _world(context)["minutes"]


# ------------------------------------------------------------------ models


@then("every model should carry a name and a price")
def step_models_described(context):
    for model in _body(context):
        assert model["name"].strip(), model
        assert model["prompt_cost"] >= 0, model
        assert model["completion_cost"] >= 0, model


@then("every model offered should be able to call tools")
def step_models_tool_capable(context):
    # The list is filtered before it is offered, so this asserts the filter
    # rather than the models: anything reachable here is something gary can
    # actually be run on.
    offered = {model["id"] for model in _body(context)}
    from gary_api.narration import models as catalogue

    assert offered, "no models offered at all"
    assert offered <= {model.id for model in catalogue.available()}


@then("some models should be suggested")
def step_models_suggested(context):
    suggested = [model for model in _body(context) if model["suggested"]]
    assert suggested, "nothing suggested, so the list starts nowhere"
    assert len(suggested) < len(_body(context)), (
        "everything is suggested, which suggests nothing"
    )


@given('I started "{name}" on "{system}" running "{module}" with "{model}"')
@when('I start "{name}" on "{system}" running "{module}" with "{model}"')
def step_start_campaign_on_model(context, name, system, module, model):
    context.response = context.client.post(
        "/campaigns",
        json={"name": name, "system": system, "module": module, "model": model},
        headers=_headers(context),
    )
    if context.response.status_code == 201:
        context.campaign = _body(context)
        context.characters = {}


@when('I move that campaign to "{model}"')
def step_move_model(context, model):
    context.response = context.client.patch(
        f"/campaigns/{_campaign_id(context)}",
        json={"model": model},
        headers=_headers(context),
    )


@when("I move that campaign to the default model")
def step_move_to_default(context):
    context.response = context.client.patch(
        f"/campaigns/{_campaign_id(context)}",
        json={"model": None},
        headers=_headers(context),
    )


@when('I move their campaign to "{model}"')
def step_move_their_model(context, model):
    context.response = context.client.patch(
        f"/campaigns/{context.other_campaign['id']}",
        json={"model": model},
        headers=_headers(context),
    )


@then('the campaign should run on "{model}"')
def step_campaign_model(context, model):
    body = _body(context)
    assert body["model"] == model, body
    assert body["model_chosen"], body


@then("the campaign should run on the default model")
def step_campaign_default_model(context):
    from gary_api.narration import models as catalogue

    body = _body(context)
    assert body["model"] == catalogue.default(), body
    assert not body["model_chosen"], body


@then('gary should have been asked for "{model}"')
def step_prompt_model(context, model):
    assert fake.LAST is not None, "gary was never asked"
    assert fake.LAST.model == model, fake.LAST.model


@when("I read the transcript")
def step_read_transcript(context):
    context.response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/turns", headers=_headers(context)
    )


@when("I read their transcript")
def step_read_their_transcript(context):
    context.response = context.client.get(
        f"/campaigns/{context.other_campaign['id']}/turns",
        headers=_headers(context),
    )


@then("the transcript should read back {count:d} turns")
def step_transcript_read_back(context, count):
    assert len(_body(context)) == count, [t["role"] for t in _body(context)]


@then("the first turn should be mine")
def step_first_turn_mine(context):
    assert _body(context)[0]["role"] == "player", _body(context)[0]


@then('gary\'s turn should carry a roll of "{notation}"')
def step_turn_carries_roll(context, notation):
    gm = [turn for turn in _body(context) if turn["role"] == "gm"]
    assert gm, "gary took no turn"
    rolls = [roll["notation"] for turn in gm for roll in turn["rolls"]]
    assert notation in rolls, rolls


# ------------------------------------------------------------------ scenes


def _scenes(context, campaign_id=None):
    """The scenes as gary-api reports them, freshly asked for."""
    response = context.client.get(
        f"/campaigns/{campaign_id or _campaign_id(context)}/scenes",
        headers=_headers(context),
    )
    context.response = response
    return response.json() if response.status_code == 200 else []


@when("I read the scenes")
def step_read_scenes(context):
    context.scenes = _scenes(context)


@when("I read their scenes")
def step_read_their_scenes(context):
    _scenes(context, context.other_campaign["id"])


def _begin(context, title="", campaign_id=None):
    context.response = context.client.post(
        f"/campaigns/{campaign_id or _campaign_id(context)}/scenes",
        json={"title": title},
        headers=_headers(context),
    )


@given("a new scene begins")
@when("a new scene begins")
def step_new_scene(context):
    _begin(context)


@given('I begin a scene called "{title}"')
@when('I begin a scene called "{title}"')
def step_begin_named(context, title):
    _begin(context, title)


@when("I begin a scene in that campaign")
def step_begin_in_that(context):
    _begin(context)


@then("there should be {count:d} scene")
@then("there should be {count:d} scenes")
def step_scene_count(context, count):
    found = _scenes(context)
    assert len(found) == count, f"expected {count} scenes, got {len(found)}"


@then("the scene should be open")
def step_scene_open(context):
    found = _scenes(context)
    assert found and found[0]["open"], f"no open scene in {found}"


@then('the open scene should be called "{title}"')
def step_open_scene_named(context, title):
    found = [scene for scene in _scenes(context) if scene["open"]]
    assert found, "no scene is open"
    assert found[0]["title"] == title, f"open scene is {found[0]['title']!r}"


@then("the first scene should be closed")
def step_first_closed(context):
    found = _scenes(context)
    assert found and not found[0]["open"], f"first scene still open: {found}"


@then("the first scene should have a recap")
def step_first_recapped(context):
    found = _scenes(context)
    assert found[0]["recap"], f"no recap on {found[0]}"


@then("the first scene should say its recap is missing")
def step_first_unrecapped(context):
    found = _scenes(context)
    assert not found[0]["open"], "the scene did not close"
    # Null rather than empty: gary being unable to say what happened is not
    # the same as nothing having happened, and a blank would read as the
    # latter.
    assert found[0]["recap"] is None, f"expected no recap, got {found[0]['recap']!r}"


@then("the recap of the first scene should have been among what gary was sent")
def step_recap_sent(context):
    assert fake.LAST, "gary was not asked anything"
    assert fake.LAST.recaps, "gary was sent no recaps"


@then("the stream should carry a scene change")
def step_stream_scene(context):
    assert _of(context, "scene"), f"no scene frame in {context.events}"


@then("gary's turn should belong to the first scene")
def step_turn_in_first_scene(context):
    turns = context.client.get(
        f"/campaigns/{_campaign_id(context)}/turns", headers=_headers(context)
    ).json()
    scenes_seen = _scenes(context)
    first = scenes_seen[0]["id"]
    gm = [turn for turn in turns if turn["role"] == "gm"]
    assert gm, "gary said nothing"
    assert gm[-1]["scene_id"] == first, "gary's turn landed in the wrong scene"


@then("the turns should carry the scene they happened in")
def step_turns_carry_scene(context):
    turns = context.client.get(
        f"/campaigns/{_campaign_id(context)}/turns", headers=_headers(context)
    ).json()
    assert turns and all(turn.get("scene_id") for turn in turns)


@then("the transcript should read back {count:d} scenes")
def step_transcript_scenes(context, count):
    turns = context.client.get(
        f"/campaigns/{_campaign_id(context)}/turns", headers=_headers(context)
    ).json()
    seen = {turn["scene_id"] for turn in turns}
    assert len(seen) == count, f"turns spanned {len(seen)} scenes, expected {count}"


@given("a scene is broken after {count:d} turns")
def step_bound_turns(context, count):
    os.environ["SCENE_TURNS"] = str(count)


@given("a scene is broken after {count:d} characters")
def step_bound_chars(context, count):
    os.environ["SCENE_CHARS"] = str(count)
    # Otherwise the turn bound fires first and the scenario would pass without
    # the size bound existing at all.
    os.environ["SCENE_TURNS"] = "999"


@given('gary will remember "{key}" as "{value}" when the scene closes')
def step_close_remembers(context, key, value):
    fake.ON_CLOSE = [f"remember {key}={value}"]


@given('gary will hurt "{name}" when the scene closes')
def step_close_hurts(context, name):
    fake.ON_CLOSE = [f"damage {name} 4"]


@given("this deployment has no model key")
def step_no_key(context):
    # As a Fly app is before anybody sets its secrets. environment.py puts
    # both back before the next scenario.
    os.environ.pop("GM_FAKE", None)
    os.environ.pop("OPENROUTER_API_KEY", None)
    narration.narrator.cache_clear()


@given("gary will roll dice when the scene closes")
def step_close_rolls(context):
    fake.ON_CLOSE = ["roll 1d20+3 Perception"]


@given("gary is unreachable when the scene closes")
def step_close_fails(context):
    fake.ON_CLOSE = ["fail"]


@then('the history should hold that change against the first scene')
def step_history_against_scene(context):
    first = _scenes(context)[0]["id"]
    events = context.client.get(
        f"/campaigns/{_campaign_id(context)}/history", headers=_headers(context)
    ).json()
    against = [event for event in events if event.get("scene_id") == first]
    assert any(
        event["kind"] == world.REMEMBERED for event in against
    ), f"nothing remembered against the first scene: {events}"


@then("the recap should have been asked of the scene model")
def step_recap_model(context):
    assert fake.LAST_CLOSE, "no scene was closed"
    assert fake.LAST_CLOSE.model == narration.models.scene_model()


@then("the scene model should not be the campaign's model")
def step_recap_model_differs(context):
    assert narration.models.scene_model() != narration.models.default()


@then("gary should not have been asked to close anything")
def step_nothing_closed(context):
    assert fake.LAST_CLOSE is None, "a close pass ran on an empty scene"


# ----------------------------------------------------------------- opening


def _begin_campaign(context, campaign_id=None):
    """Ask gary to open the scene, collecting the stream as a turn does."""
    context.events = []
    with context.client.stream(
        "POST",
        f"/campaigns/{campaign_id or _campaign_id(context)}/opening",
        headers=_headers(context),
    ) as response:
        context.response = response
        if response.status_code != 200:
            response.read()
            return

        name = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                name = line[len("event: ") :].strip()
            elif line.startswith("data: "):
                context.events.append((name, json.loads(line[len("data: ") :])))


@given("gary has begun")
@when("I ask gary to begin")
def step_begin(context):
    _begin_campaign(context)


@when('I ask gary to begin with "{directives}"')
def step_begin_with(context, directives):
    # An opening answers gary-api's instruction, not a player's message, so
    # there is nothing for a scenario to write its directives into. Arranged
    # rather than read, and cleared per scenario.
    fake.ON_OPEN = [one.strip() for one in DIRECTIVE.findall(directives)]
    _begin_campaign(context)


@when("I ask gary to begin theirs")
def step_begin_theirs(context):
    _begin_campaign(context, context.other_campaign["id"])


@then("the opening should be gary's")
def step_opening_is_garys(context):
    turns = context.client.get(
        f"/campaigns/{_campaign_id(context)}/turns", headers=_headers(context)
    ).json()
    assert turns, "nothing was said at all"
    assert turns[0]["role"] == "gm", f"the first turn was {turns[0]['role']}"
    assert turns[0]["content"].strip(), "gary opened with nothing"


@then("the opening should belong to the open scene")
def step_opening_in_open_scene(context):
    turns = context.client.get(
        f"/campaigns/{_campaign_id(context)}/turns", headers=_headers(context)
    ).json()
    open_scene = [scene for scene in _scenes(context) if scene["open"]][0]
    assert turns[0]["scene_id"] == open_scene["id"]


@then("the campaign should still be waiting to begin")
def step_still_waiting(context):
    found = context.client.get(
        f"/campaigns/{_campaign_id(context)}", headers=_headers(context)
    ).json()
    assert not found["begun"], "the campaign counts as begun after a failure"


@then("the campaign should carry the module's premise")
def step_campaign_premise(context):
    premise = _body(context).get("premise") or ""
    assert len(premise.split()) > 5, f"no premise worth reading: {premise!r}"


@then("the campaign should say where it begins")
def step_campaign_place(context):
    assert (_body(context).get("place") or "").strip(), "nowhere to begin"


@then("the campaign should say it has not begun")
def step_campaign_not_begun(context):
    assert _body(context)["begun"] is False


@then("gary should have been told what brought the party here")
def step_told_the_hook(context):
    assert fake.LAST, "gary was not asked anything"
    # The module's own words, not a paraphrase: if the hook did not reach the
    # prompt then "why am I here" has nowhere to be answered from.
    module = systems.module(
        context.campaign["system"], context.campaign["module"]
    )
    assert module.hook in fake.LAST.module_hook, (
        "gary was told nothing about why the party is here"
    )


@then("every module should carry a hook")
def step_modules_hooked(context):
    for system in _body(context):
        for module in system["modules"]:
            hook = module.get("hook") or ""
            assert len(hook.split()) > 10, (
                f"{module['slug']} says nothing about why anybody would go"
            )


@then("no hook should merely repeat its premise")
def step_hook_is_not_the_premise(context):
    for system in _body(context):
        for module in system["modules"]:
            assert module["hook"].strip() != module["premise"].strip(), (
                f"{module['slug']}'s hook is its premise again"
            )


# ------------------------------------------------------------------ party


def _add(context, name, character_class, mine):
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}/characters",
        json={"name": name, "character_class": character_class, "mine": mine},
        headers=_headers(context),
    )
    if context.response.status_code == 201:
        context.characters[name] = _body(context)


@given('I add "{name}" the {character_class:Class} as mine')
@when('I add "{name}" the {character_class:Class} as mine')
def step_add_mine(context, name, character_class):
    _add(context, name, character_class, True)


@given('I add "{name}" the {character_class:Class} as a companion')
@when('I add "{name}" the {character_class:Class} as a companion')
def step_add_companion(context, name, character_class):
    _add(context, name, character_class, False)


def _party(context, campaign_id=None):
    response = context.client.get(
        f"/campaigns/{campaign_id or _campaign_id(context)}/characters",
        headers=_headers(context),
    )
    return response.json() if response.status_code == 200 else []


@when('I take over "{name}"')
def step_take_over(context, name):
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}"
        f"/characters/{_character_id(context, name)}/player",
        headers=_headers(context),
    )


@when("I take over somebody who does not exist")
def step_take_over_nobody(context):
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}/characters/{NOWHERE}/player",
        headers=_headers(context),
    )


@when("I take over one of their characters")
def step_take_over_theirs(context):
    context.response = context.client.post(
        f"/campaigns/{context.other_campaign['id']}"
        f"/characters/{NOWHERE}/player",
        headers=_headers(context),
    )


@then('the party should say "{name}" is mine')
def step_party_says_mine(context, name):
    found = [one for one in _party(context) if one["name"] == name]
    assert found, f"nobody called {name} at this table"
    assert found[0]["played_by"] == "player", f"{name} is gary's"


@then('the party should say "{name}" is gary\'s')
def step_party_says_garys(context, name):
    found = [one for one in _party(context) if one["name"] == name]
    assert found, f"nobody called {name} at this table"
    assert found[0]["played_by"] == "gary", f"{name} is mine"


@then("exactly {count:d} character should be mine")
def step_exactly_mine(context, count):
    played = [
        one for one in _party(context) if one["played_by"] == "player"
    ]
    assert len(played) == count, f"{len(played)} characters are mine"


@then('gary should have been told "{name}" is the player\'s')
def step_told_players(context, name):
    assert fake.LAST, "gary was not asked anything"
    for line in fake.LAST.world.splitlines():
        if name in line:
            assert "PLAYER" in line, f"gary was not told {name} is yours: {line}"
            return
    raise AssertionError(f"gary was told nothing about {name}")


@then('gary should have been told "{name}" is gary\'s to play')
def step_told_garys(context, name):
    assert fake.LAST, "gary was not asked anything"
    for line in fake.LAST.world.splitlines():
        if name in line:
            assert "yours to play" in line, f"gary was not offered {name}: {line}"
            return
    raise AssertionError(f"gary was told nothing about {name}")


@then('the world should say "{name}" is mine')
def step_world_says_mine(context, name):
    found = [one for one in _body(context)["party"] if one["name"] == name]
    assert found and found[0]["played_by"] == "player"


@then('the world should say "{name}" is gary\'s')
def step_world_says_garys(context, name):
    found = [one for one in _body(context)["party"] if one["name"] == name]
    assert found and found[0]["played_by"] == "gary"


# ------------------------------------------------------------------- rolls
#
# Whose a roll was, and what it was against. A number in the middle of a
# story means nothing on its own, and gary was working around that by writing
# the name into the reason — "John falling damage" — which is a mechanical
# fact in a free-text field where nothing can check it.


def _with_ability(context, name, character_class, ability, score, mine):
    """Somebody with a score worth a modifier, so a check can prove it used one."""
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}/characters",
        json={
            "name": name,
            "character_class": character_class,
            "abilities": {ability: score},
            "mine": mine,
        },
        headers=_headers(context),
    )
    assert context.response.status_code == 201, context.response.text
    context.characters[name] = _body(context)


@given('"{name}" the {character_class:Class} has {ability} {score:d}')
def step_character_with_ability(context, name, character_class, ability, score):
    _with_ability(context, name, character_class, ability, score, False)


@given('"{name}" the {character_class:Class} has {ability} {score:d}, and is mine')
def step_my_character_with_ability(context, name, character_class, ability, score):
    _with_ability(context, name, character_class, ability, score, True)


@then('the roll should have been made for "{who}"')
def step_roll_for(context, who):
    rolls = _of(context, "roll")
    assert rolls, "nothing was rolled"
    assert any(roll.get("character") == who for roll in rolls), rolls


@then("the roll should have been made for nobody")
def step_roll_for_nobody(context):
    rolls = _of(context, "roll")
    assert rolls, "nothing was rolled"
    for roll in rolls:
        assert roll.get("character") is None, roll


@then('the roll should still say it was for "{who}"')
def step_roll_still_for(context, who):
    """After a reload, which is the half that was missing.

    The stream carried a name and the table did not, so the moment a page was
    refreshed the roll was back to a bare number.
    """
    rolls = [roll for turn in _body(context) for roll in turn["rolls"]]
    assert rolls, "the transcript carried no rolls"
    assert any(roll.get("character") == who for roll in rolls), rolls


@then("there should be {count:d} rolls")
def step_roll_count(context, count):
    rolls = _of(context, "roll")
    assert len(rolls) == count, [roll.get("character") for roll in rolls]


@then("there should be no rolls")
def step_no_rolls_at_all(context):
    assert not _of(context, "roll"), _of(context, "roll")
    rows = sql(
        "SELECT r.id FROM rolls r JOIN turns t ON t.id = r.turn_id"
        " WHERE t.campaign_id = :id",
        id=_campaign_id(context),
    )
    assert not rows, "a refused check still wrote rolls down"


@then("gary should have been told both results")
def step_told_both(context):
    """One call, one answer, covering everybody in it.

    A model told only about the last of four would narrate the other three
    from memory, which is the whole failure this design exists to prevent.
    """
    summary = fake.LAST_RESULTS
    assert summary, "gary was told nothing"
    said = " ".join(result.summary for result in summary)
    for who in ("Bramble", "John"):
        assert who in said, said


@then("the roll should be refused")
def step_roll_refused(context):
    refusals = [
        data
        for name, data in context.events
        if name == "error" and data.get("code") == "refused_tool"
    ]
    assert refusals, [name for name, _ in context.events]
    context.refusal = refusals[-1]


@then('the refusal should name "{what}"')
def step_refusal_names(context, what):
    assert what in context.refusal["detail"], context.refusal


@then("the check should have used a modifier of {modifier:d}")
def step_check_modifier(context, modifier):
    rolls = _of(context, "roll")
    assert rolls, "nothing was rolled"
    assert all(roll["modifier"] == modifier for roll in rolls), rolls


@then('the roll should read "{notation}"')
def step_roll_reads(context, notation):
    rolls = _of(context, "roll")
    assert any(roll["notation"] == notation for roll in rolls), rolls


@then('"{who}" should have rolled "{notation}"')
def step_who_rolled(context, who, notation):
    rolls = [roll for roll in _of(context, "roll") if roll.get("character") == who]
    assert rolls, f"{who} rolled nothing"
    assert all(roll["notation"] == notation for roll in rolls), rolls


# ------------------------------------------------------------------ combat


def _fight(context):
    """The fight as the world has it, read back through the API."""
    context.response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/world", headers=_headers(context)
    )
    assert context.response.status_code == 200, context.response.text
    return _body(context)


def _refusals(context):
    return [
        data
        for name, data in context.events
        if name == "error" and data.get("code") == "refused_tool"
    ]


@then("the tool should be refused")
def step_tool_refused(context):
    refusals = _refusals(context)
    assert refusals, [name for name, _ in context.events]
    context.refusal = refusals[-1]


@then("the refusal should say {what}")
def step_refusal_says(context, what):
    # Matched on a few words rather than the whole sentence: what a refusal
    # means is what it tells gary, and pinning the wording would make every
    # rewording a failing spec.
    wanted = {
        "a fight is already happening": "already happening",
        "there is no fight": "no fight",
        "whose turn it is": "it is not",
        "it is mine to take": "to take",
        "this system cannot do fights yet": "by side",
        "the sheet decides the modifier": "sheet",
        "nobody is called that": "nobody in this fight",
        "you cannot hit yourself": "cannot attack themselves",
        "there is nobody to fight it": "nobody here to fight",
        "they are already down": "already down",
        "the award is larger than this system allows": "more experience than",
        "first edition prices a level per class": "per class",
    }[what]
    assert wanted in context.refusal["detail"], context.refusal


@then("everybody in the fight should have rolled initiative")
def step_everybody_rolled(context):
    rolled = [
        roll for roll in _of(context, "roll") if roll["reason"] == "initiative"
    ]
    fight = _fight(context)["fight"]
    assert fight, "no fight was started"
    assert len(rolled) == len(fight["order"]), (rolled, fight["order"])


@then("the order should run from highest to lowest")
def step_order_sorted(context):
    totals = {
        roll["character"]: roll["total"]
        for roll in _of(context, "roll")
        if roll["reason"] == "initiative"
    }
    order = [one["name"] for one in _fight(context)["fight"]["order"]]
    got = [totals[name] for name in order]
    assert got == sorted(got, reverse=True), list(zip(order, got))


@then("it should be round {number:d}")
def step_round_is(context, number):
    assert _fight(context)["fight"]["round"] == number, _fight(context)["fight"]


@then('the world should have "{name}" in the fight')
def step_world_has_foe(context, name):
    names = [one["name"] for one in _fight(context)["enemies"]]
    assert name in names, names


@then('"{name}" should have hit points')
def step_foe_has_hp(context, name):
    foe = next(one for one in _fight(context)["enemies"] if one["name"] == name)
    assert foe["max_hp"] > 0 and foe["hp"] == foe["max_hp"], foe


@then('"{name}" should not be in the party')
def step_foe_not_party(context, name):
    names = [one["name"] for one in _fight(context)["party"]]
    assert name not in names, names


@then('"{who}" should have rolled initiative with a modifier of {modifier:d}')
def step_initiative_modifier(context, who, modifier):
    rolled = [
        roll
        for roll in _of(context, "roll")
        if roll["reason"] == "initiative" and roll["character"] == who
    ]
    assert rolled, f"{who} rolled no initiative"
    assert rolled[0]["modifier"] == modifier, rolled[0]


def _whose(context):
    fight = _fight(context)["fight"]
    return fight["order"][fight["at"]]["name"]


def _somebody_else(context, besides):
    """Anyone else in the fight who is still standing.

    Still standing, because the engine refuses a swing at somebody already
    down — which is right, and which a step that picked blindly would trip
    over as soon as anybody fell.
    """
    world_now = _fight(context)
    upright = {
        one["name"]
        for one in [*world_now["party"], *world_now["enemies"]]
        if not one["down"]
    }
    return next(
        one["name"]
        for one in world_now["fight"]["order"]
        if one["name"] != besides and one["name"] in upright
    )


@when("gary has somebody act out of turn")
def step_out_of_turn(context):
    order = [one["name"] for one in _fight(context)["fight"]["order"]]
    at = _whose(context)
    other = next(name for name in order if name != at)
    target = next(name for name in order if name != other)
    context.execute_steps(
        f'When I say "out of turn [[attack {other} {target}]]"'
    )


@when("the one whose turn it is attacks")
def step_whoever_attacks(context):
    at = _whose(context)
    target = next(
        one["name"]
        for one in _fight(context)["fight"]["order"]
        if one["name"] != at
    )
    context.execute_steps(f'When I say "it swings [[attack {at} {target}]]"')


@then("the attack should have been rolled against the target's armour class")
def step_attack_rolled(context):
    swings = [roll for roll in _of(context, "roll") if roll.get("dc")]
    assert swings, _of(context, "roll")
    assert swings[-1]["degree"], swings[-1]


@then("gary should have been told what happened")
def step_told_outcome(context):
    said = " ".join(result.summary for result in fake.LAST_RESULTS or [])
    assert "hit" in said or "missed" in said, said


@then("the damage should match whether it hit")
def step_damage_matches(context):
    swings = [roll for roll in _of(context, "roll") if roll.get("degree")]
    assert swings, "nothing was rolled to hit"
    hit = swings[-1]["degree"] in ("success", "critical-success")
    # Damage specifically. Every attack ends a turn, and that is a world
    # change too — counting any of them would make this assertion always true.
    hurt = [
        data
        for name, data in context.events
        if name == "world" and data.get("kind") == "damaged"
    ]
    assert bool(hurt) == hit, (swings[-1], hurt)


@then("the history should say which turn did it")
def step_history_turn(context):
    rows = sql(
        "SELECT e.kind FROM world_events e JOIN turns t ON t.id = e.turn_id"
        " WHERE t.campaign_id = :id",
        id=_campaign_id(context),
    )
    assert rows, "the fight changed the world and nothing says which turn did"


def _take_turn(context):
    """Whoever is up acts, then the turn ends.

    The player's character has to actually act before gary may end their turn
    — that is the whole rule — so a step that only ends turns would deadlock
    on them, exactly as a fight would.
    """
    at = _whose(context)
    mine = {one["name"] for one in _fight(context)["party"] if one["played_by"] == "player"}
    if at in mine:
        # Gary may not end the player's turn, so the only way past it is for
        # them to take it — which is the rule this whole feature is about.
        # Swinging is taking it: one action is all a turn holds.
        context.execute_steps(
            f'When I say "it swings [[attack {at} {_somebody_else(context, at)}]]"'
        )
        return
    # Everybody else can simply pass, which keeps a step that only wants the
    # order to move from also deciding who hits whom.
    context.execute_steps('When I say "and on [[endturn]]"')


@when("the one whose turn it is ends it")
def step_end_turn(context):
    context.was = _whose(context)
    _take_turn(context)


@then("it should be the next one's turn")
def step_next_turn(context):
    assert _whose(context) != context.was, context.was


@when("everybody has had a turn")
def step_full_round(context):
    for _ in _fight(context)["fight"]["order"]:
        _take_turn(context)


@given('the order has reached "{who}"')
def step_order_reaches(context, who):
    for _ in range(8):
        if _whose(context) == who:
            return
        _take_turn(context)
    raise AssertionError(f"the order never reached {who}")


@then("gary should have been told to stop and ask me")
def step_told_to_stop(context):
    assert fake.LAST is not None
    assert "Stop and ask them" in fake.LAST.world, fake.LAST.world


@then("the attack should have been made")
def step_attack_made(context):
    assert [roll for roll in _of(context, "roll") if roll.get("degree")], (
        _of(context, "roll")
    )


@then("the fight should be over")
def step_fight_over(context):
    assert _fight(context)["fight"] is None, _fight(context)["fight"]


@then("gary should have been told the order")
def step_told_order(context):
    assert "Order:" in fake.LAST.world, fake.LAST.world


@then("gary should have been told whose turn it is")
def step_told_whose(context):
    assert "it is their turn" in fake.LAST.world, fake.LAST.world


@then("gary should have been told the round")
def step_told_round(context):
    assert "Round " in fake.LAST.world, fake.LAST.world


@then("gary should have been told what was fought")
def step_told_fought(context):
    assert "Previously fought" in fake.LAST.world, fake.LAST.world


@given('"{name}" has been knocked down')
def step_knock_down(context, name):
    """Enough damage to put it out, however much that is.

    Written as damage rather than as a state, because there is no state — a
    thing is down when the log has taken its hit points off it, and a step
    that set a flag would be testing something the world does not have.
    """
    foe = next(one for one in _fight(context)["enemies"] if one["name"] == name)
    context.execute_steps(
        f'When I say "it reels [[damage {name} {foe["max_hp"]}]]"'
    )


@then('"{name}" should be {amount:d} hit points down on the other side')
def step_foe_hurt(context, name, amount):
    foe = next(one for one in _fight(context)["enemies"] if one["name"] == name)
    assert foe["max_hp"] - foe["hp"] == amount, foe


# --------------------------------------------------------------- creation


@when('I read the system "{slug}"')
def step_read_system(context, slug):
    context.response = context.client.get(f"/catalogue/{slug}")
    assert context.response.status_code == 200, context.response.text


def _offers(context):
    return {method["slug"] for method in _body(context)["methods"]}


OFFERED = {
    "the standard array": "standard-array",
    "point buy": "point-buy",
    "rolling 4d6 and dropping the lowest": "roll-4d6-drop-lowest",
    "rolling 3d6 in order": "roll-3d6-in-order",
    "typing them in": "manual",
}


@parse.with_pattern(r"|".join(OFFERED))
def parse_offered(text):
    return text


register_type(Offered=parse_offered)


@then("it should offer the {what}")
@then("it should offer {what:Offered}")
def step_offers(context, what):
    assert OFFERED[what] in _offers(context), _offers(context)


@then("it should not offer {what:Offered}")
def step_does_not_offer(context, what):
    assert OFFERED[what] not in _offers(context), _offers(context)


@then("every system should offer typing them in")
def step_all_offer_manual(context):
    """Not a method so much as the absence of one, so nothing may lack it.

    A system with no way in at all would be registered, listed, and then
    discovered to be unplayable at the first party page.
    """
    context.response = context.client.get("/catalogue")
    for system in _body(context):
        context.execute_steps(f'When I read the system "{system["slug"]}"')
        assert "manual" in _offers(context), system["slug"]


@then("gary should generate nothing for it")
def step_generates_nothing(context):
    generating = [
        method for method in _body(context)["methods"] if method["generates"]
    ]
    assert not generating, generating


@then("it should say why")
def step_says_why(context):
    assert _body(context)["cannot_generate"].strip(), _body(context)


@given('I have a campaign on "{system}"')
def step_campaign_on(context, system):
    context.execute_steps(
        f'Given I started "A test" on "{system}" running '
        f'"{_first_module(system)}"'
    )


def _roll_scores(context, method):
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}/scores",
        json={"method": method},
        headers=_headers(context),
    )
    if context.response.status_code == 200:
        context.scores = context.scores + [_body(context)] if hasattr(
            context, "scores"
        ) else [_body(context)]


@when('I roll scores with "{method}"')
def step_roll_scores(context, method):
    context.scores = []
    _roll_scores(context, method)


@when('I roll scores with "{method}" again')
def step_roll_scores_again(context, method):
    _roll_scores(context, method)


@then("I should get {count:d} scores")
def step_score_count(context, count):
    assert len(_body(context)["scores"]) == count, _body(context)


@then("each should be between {low:d} and {high:d}")
def step_scores_within(context, low, high):
    for one in _body(context)["scores"]:
        assert low <= one["score"] <= high, one


@then("the roll should be recorded as dice, not as a number")
def step_scores_show_dice(context):
    """Four dice and the one thrown away, not just the total.

    "15" and "6, 5, 4 and a discarded 1" are different things to read while
    you are deciding where to put it.
    """
    for one in _body(context)["scores"]:
        assert len(one["dice"]) == 4, one
        assert one["dropped"] == min(one["dice"]), one
        assert one["score"] == sum(one["dice"]) - one["dropped"], one


@then("the scores should already be assigned to abilities")
def step_scores_assigned(context):
    assigned = _body(context)["assigned"]
    assert assigned, "nothing was placed"
    from gary_api import systems

    ruleset = systems.ruleset(context.campaign["system"])
    assert set(assigned) == set(ruleset.abilities), assigned


@then("the refusal should name the method")
def step_refusal_names_method(context):
    assert "roll-3d6-in-order" in _body(context)["detail"], _body(context)


@then("the two sets should differ")
def step_sets_differ(context):
    """Seeded, so this is not luck: two draws from one seeded generator are
    different draws, and a client that cached the first would show the same
    six numbers twice."""
    first, second = (
        [one["score"] for one in got["scores"]] for got in context.scores
    )
    assert first != second, first


def _add_with(context, name, character_class, abilities, mine=False):
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}/characters",
        json={
            "name": name,
            "character_class": character_class,
            "abilities": abilities,
            "mine": mine,
        },
        headers=_headers(context),
    )
    if context.response.status_code == 201:
        context.characters[name] = _body(context)


@when('I add "{name}" the {character_class:Class} with {sheet} as mine')
def step_add_with_mine(context, name, character_class, sheet):
    step_add_with(context, name, character_class, sheet, mine=True)


@when('I add "{name}" the {character_class:Class} with {sheet}')
def step_add_with(context, name, character_class, sheet, mine=False):
    """One step for however many scores a scenario cares to state.

    "with dex 16" and "with dex 16 and con 14" are the same sentence with more
    of it, and two step definitions competing over which owns the tail is a
    match that goes wrong quietly.
    """
    words = sheet.replace(" and ", " ").split()
    pairs = dict(zip(words[::2], words[1::2], strict=True))
    _add_with(
        context,
        name,
        character_class,
        {
            ability: int(score) if score.lstrip("-").isdigit() else score
            for ability, score in pairs.items()
        },
        mine,
    )


@then('"{name}" should have {ability} {score:d}')
def step_character_score(context, name, ability, score):
    assert context.characters[name]["abilities"][ability] == score, (
        context.characters[name]["abilities"]
    )


@then('a check on "{name}" should use a modifier of {modifier:d}')
def step_their_check_modifier(context, name, modifier):
    """The point of the whole feature, asserted end to end: a score typed at
    creation reaches a check made in play."""
    context.execute_steps(
        f'When I say "they duck [[check {name} dex 12 dodging]]"'
    )
    context.execute_steps(f"Then the check should have used a modifier of {modifier}")


@then('"{name}" should have {count:d} hit point')
@then('"{name}" should have {count:d} hit points')
def step_character_hp(context, name, count):
    assert context.characters[name]["max_hp"] == count, context.characters[name]


@then('"{first}" should have more hit points than "{second}"')
def step_more_hp(context, first, second):
    assert (
        context.characters[first]["max_hp"] > context.characters[second]["max_hp"]
    ), (context.characters[first]["max_hp"], context.characters[second]["max_hp"])


@then('the body should mention "{what}"')
def step_body_mentions(context, what):
    assert what in context.response.text, context.response.text


@then("{what:Offered} should spend the budget")
def step_spends(context, what):
    """Which method spends the budget is the system's to say.

    ``generates`` and ``arrange`` are the same two answers for point buy and
    for typing them in, so a client reading only those cannot tell one from
    the other and would have to recognise a slug — which is a copy of the
    rules living somewhere they are not maintained.
    """
    spending = {
        method["slug"] for method in _body(context)["methods"] if method["spends"]
    }
    assert OFFERED[what] in spending, spending


@then("{what:Offered} should not spend the budget")
def step_does_not_spend(context, what):
    spending = {
        method["slug"] for method in _body(context)["methods"] if method["spends"]
    }
    assert OFFERED[what] not in spending, spending


@then("nothing it offers should spend the budget")
def step_nothing_spends(context):
    spending = [
        method["slug"] for method in _body(context)["methods"] if method["spends"]
    ]
    assert not spending, spending


@then("it should say what every score it allows is worth")
def step_says_worth(context):
    """Every score between the system's lowest and highest, and no holes.

    A table with gaps would be a client having to work the missing ones out,
    which is the arithmetic this exists to keep out of clients.
    """
    body = _body(context)
    low, high = body["scores"]
    worth = body["modifiers"]
    for score in range(low, high + 1):
        assert str(score) in worth, f"{score} is not priced: {sorted(worth)}"


@then("a {score:d} should be worth {worth:d}")
def step_score_worth(context, score, worth):
    said = _body(context)["modifiers"][str(score)]
    assert said == worth, f"a {score} is worth {said}, not {worth}"


@then("every score should be worth {worth:d}")
def step_every_score_worth(context, worth):
    said = _body(context)["modifiers"]
    wrong = {score: each for score, each in said.items() if each != worth}
    assert not wrong, wrong
