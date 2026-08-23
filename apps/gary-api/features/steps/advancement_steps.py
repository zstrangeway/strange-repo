"""Advancement: experience gary awards, and levels the engine grants.

Where somebody currently stands is read off `GET /campaigns/{id}/world`, never
off the character row — the row is the sheet as created and the log is
everything since, so asserting against the row would pass while the thing
these scenarios are about did not happen.

The helpers below are local copies of one-liners in play_steps rather than
imports of them. behave loads every module in this directory itself, and a
module that also imports a sibling can get it loaded twice under two names,
which registers every step in it twice and fails the run.
"""

from behave import given, then

from gary_api import systems
from gary_api.narration import fake


def _headers(context):
    if getattr(context, "token", None):
        return {"authorization": f"Bearer {context.token}"}
    return {}


def _body(context):
    return context.response.json()


def _campaign_id(context):
    return context.campaign["id"]


def _character_id(context, name):
    return context.characters[name]["id"]


def _frames(context, kind):
    return [data for name, data in context.events if name == kind]


def _world(context):
    response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/world", headers=_headers(context)
    )
    assert response.status_code == 200, response.status_code
    return response.json()


def _standing(context, who):
    """Somebody as the world currently has them."""
    for member in _world(context)["party"]:
        if member["name"] == who:
            return member
    raise AssertionError(f"{who} is not in the party")


def _events(context, kind):
    """Everything of one kind in the history, oldest first."""
    response = context.client.get(
        f"/campaigns/{_campaign_id(context)}/history", headers=_headers(context)
    )
    assert response.status_code == 200, response.status_code
    return [one for one in response.json() if one["kind"] == kind]


def _awards(context):
    return [
        one
        for one in _frames(context, "world")
        if one["kind"] == "experience-gained"
    ]


# ---------------------------------------------------------- what a system says


@then("level {level:d} should cost {cost:d} experience")
def step_level_costs(context, level, cost):
    slug = _body(context)["slug"]
    actual = systems.ruleset(slug).experience_for(level)
    assert actual == cost, f"{slug} prices level {level} at {actual}"


@then("it should advance no further than level {top:d}")
def step_stops_at(context, top):
    ruleset = systems.ruleset(_body(context)["slug"])
    assert ruleset.max_level == top, ruleset.max_level


@then("it should say it cannot price a level")
def step_cannot_price(context):
    ruleset = systems.ruleset(_body(context)["slug"])
    try:
        ruleset.experience_for(2)
    except systems.SystemError:
        return
    raise AssertionError(f"{ruleset.slug} priced a level after all")


# ------------------------------------------------------------------- the sheet


@given('I add "{name}" the {character_class} at level {level:d}')
def step_add_at_level(context, name, character_class, level):
    context.response = context.client.post(
        f"/campaigns/{_campaign_id(context)}/characters",
        json={"name": name, "character_class": character_class, "level": level},
        headers=_headers(context),
    )
    assert context.response.status_code == 201, context.response.text
    context.characters[name] = _body(context)


# ------------------------------------------------------------ where they stand


@then('"{who}" should be level {level:d}')
@then('"{who}" should still be level {level:d}')
def step_is_level(context, who, level):
    standing = _standing(context, who)
    assert standing["level"] == level, standing


@then('"{who}" should have {amount:d} experience')
def step_has_experience(context, who, amount):
    standing = _standing(context, who)
    assert standing["experience"] == amount, standing


@then('"{who}" should have no experience')
def step_has_no_experience(context, who):
    standing = _standing(context, who)
    assert standing["experience"] == 0, standing


@then('"{who}" should have more maximum hit points than they started with')
def step_tougher(context, who):
    sheet = context.characters[who]["max_hp"]
    standing = _standing(context, who)
    assert standing["max_hp"] > sheet, f"{standing['max_hp']} against {sheet}"


@then('"{who}" should still be {short:d} below their maximum')
def step_still_short(context, who, short):
    standing = _standing(context, who)
    actual = standing["max_hp"] - standing["hp"]
    assert actual == short, f"{actual} below, not {short}"


# ----------------------------------------------------------------- the history


@then('the history should hold an award of {amount:d} to "{who}"')
def step_history_award(context, amount, who):
    awards = _events(context, "experience-gained")
    wanted = _character_id(context, who)
    assert any(
        one["payload"]["character_id"] == wanted
        and one["payload"]["amount"] == amount
        for one in awards
    ), awards


@then("it should say what it was for")
def step_award_reason(context):
    awards = _events(context, "experience-gained")
    assert awards, "nothing was awarded"
    assert all(one["payload"]["reason"] for one in awards), awards


@then('the award should say it was for "{reason}"')
def step_award_reason_is(context, reason):
    earned = _awards(context)
    assert earned, "no award reached the stream"
    assert any(one["reason"] == reason for one in earned), earned


@then('the history should hold a level for "{who}"')
def step_history_level(context, who):
    levels = _events(context, "level-gained")
    wanted = _character_id(context, who)
    assert any(one["payload"]["character_id"] == wanted for one in levels), levels


@then("the level should not be something gary asked for")
def step_level_is_the_engines(context):
    """The guarantee, checked where it can be: gary has no tool for this.

    A level is written by the engine in answer to an award, so no tool the
    narrator is ever offered names one. Guarded again in
    tests/test_pluggable.py, which fails the build if that stops being true.
    """
    from gary_api import narration

    for name, fields in narration.TOOLS.items():
        assert "level" not in name, name
        assert "level" not in fields, (name, fields)


@then("the level should record what was gained")
def step_level_records_gain(context):
    levels = _events(context, "level-gained")
    assert levels, "nobody levelled"
    assert all(one["payload"]["hit_points"] >= 1 for one in levels), levels


@then("it should have taken one award to do it")
def step_one_award(context):
    """One call, several rows: each of them gets their own event."""
    names = {one["character"] for one in _awards(context)}
    assert len(names) > 1, _awards(context)


@then("what \"{who}\" gained should come off a {character_class}'s hit die")
def step_gain_fits_die(context, who, character_class):
    ruleset = systems.ruleset(context.campaign["system"])
    die = ruleset.hit_dice[character_class]
    wanted = _character_id(context, who)
    levels = [
        one
        for one in _events(context, "level-gained")
        if one["payload"]["character_id"] == wanted
    ]
    assert levels, f"{who} did not level"
    for one in levels:
        # A hit die plus a constitution modifier, floored at one. The die is
        # the engine's and the modifier comes off the sheet, so the band is
        # what a class can possibly gain rather than a fixed number.
        gained = one["payload"]["hit_points"]
        assert 1 <= gained <= die + 5, f"{gained} does not come off a d{die}"


# ------------------------------------------------------------ what gary is told


@then('gary should have been told "{who}" is level {level:d}')
def step_gary_told_level(context, who, level):
    assert fake.LAST, "gary was not asked anything"
    assert f"{who}, level {level}" in fake.LAST.world, fake.LAST.world


@then('gary should have been told how much experience "{who}" has')
def step_gary_told_experience(context, who):
    assert fake.LAST, "gary was not asked anything"
    standing = _standing(context, who)
    wanted = f"{standing['experience']} experience"
    assert wanted in fake.LAST.world, fake.LAST.world


@then('"{who}" should have no next level to reach')
def step_no_next_level(context, who):
    standing = _standing(context, who)
    assert standing["next_level"] is None, standing


def _changes(context):
    """Everything every turn in the transcript says it changed."""
    return [
        change for turn in _body(context) for change in turn["changes"]
    ]


@then('the turn should carry an award to "{who}"')
def step_turn_carries_award(context, who):
    changes = _changes(context)
    assert any(
        one["kind"] == "experience-gained" and one["character"] == who
        for one in changes
    ), changes


@then('the turn should carry a level for "{who}"')
def step_turn_carries_level(context, who):
    changes = _changes(context)
    assert any(
        one["kind"] == "level-gained" and one["character"] == who
        for one in changes
    ), changes
