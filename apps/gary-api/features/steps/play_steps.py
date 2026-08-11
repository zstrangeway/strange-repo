import uuid

import parse
from behave import given, register_type, then, when

from environment import with_session
from gary_api import world

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


register_type(Class=a_class, Names=some_names, Slugs=some_slugs)

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


@given('I started "{name}" on "{system}" running "{module}"')
@when('I start "{name}" on "{system}" running "{module}"')
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
