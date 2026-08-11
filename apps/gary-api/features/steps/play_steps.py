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
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}/characters",
        json={"name": name, "character_class": character_class},
        headers=_headers(context),
    )
    if context.response.status_code == 201:
        context.characters[name] = _body(context)


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
