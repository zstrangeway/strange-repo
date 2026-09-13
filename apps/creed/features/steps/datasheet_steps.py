"""Steps for looking up datasheets, stratagems and detachments."""

from behave import then, when

from creed import datasheets, db, detachments, rules
from creed.markup import to_markdown


def _search(context, query, faction=None):
    with db.session() as connection:
        context.found = datasheets.search(connection, query, faction=faction)
    return context.found


@when('I look up "Testudo Captain"')
def step_look_up_captain(context):
    with db.session() as connection:
        context.sheets = datasheets.by_name(connection, "Testudo Captain")


@when('I search datasheets for "testudo captain"')
@when('I search datasheets for "captain"')
def step_search_captain(context):
    _search(context, "captain")


@when('I search datasheets for "walker"')
def step_search_walker(context):
    _search(context, "walker")


@when("I search datasheets for a name more than one faction uses")
def step_search_shared(context):
    with db.session() as connection:
        context.sheets = datasheets.by_name(connection, "Testudo Guard")
    _search(context, "Testudo Guard")


@when('I search datasheets for "walker" in the Test Guard')
def step_search_in_faction(context):
    _search(context, "walker", faction="Test Guard")


@when('I search datasheets for "Emperor\'s Own Breakfast Cereal"')
def step_search_nothing(context):
    _search(context, "Emperor's Own Breakfast Cereal")


@when("I look up a datasheet with more than one model profile")
def step_multi_profile(context):
    with db.session() as connection:
        context.sheet = datasheets.by_name(connection, "Testudo Guard", "Test Guard")[0]


@when("I look up a datasheet with a weapon that has keywords")
@when("I look up a datasheet whose ability text is marked up")
@when("I look up a datasheet that comes in more than one size")
@when("I look up a datasheet priced by how many you have taken")
@when("I look up a datasheet with priced wargear options")
def step_load_d1(context):
    with db.session() as connection:
        context.sheet = datasheets.by_name(connection, "Testudo Guard", "Test Guard")[0]


@when("I look up a vehicle with a damaged profile")
def step_load_vehicle(context):
    with db.session() as connection:
        context.sheet = datasheets.by_name(connection, "Testudo Walker")[0]


@when("I look up a character that can lead")
def step_load_leader(context):
    with db.session() as connection:
        context.sheet = datasheets.by_name(connection, "Testudo Captain")[0]


@when("I look up an ability that emphasises a keyword")
@when("I look up an ability whose text contains a list")
def step_load_ability(context):
    with db.session() as connection:
        context.abilities = rules.abilities(connection, "Testudo Resolve")


@when("I ask creed for the factions")
def step_ask_factions(context):
    with db.session() as connection:
        context.factions = datasheets.factions(connection)


@when("I ask for the Test Guard datasheets")
def step_faction_sheets(context):
    with db.session() as connection:
        context.matches = datasheets.in_faction(connection, "Test Guard")


@then("I should get one datasheet")
def step_one_sheet(context):
    assert len(context.sheets) == 1, [s.faction for s in context.sheets]


@then("it should be the Test Guard one")
def step_is_tg(context):
    assert context.sheets[0].faction == "Test Guard", context.sheets[0].faction


@then('the results should include "Testudo Walker"')
def step_includes_walker(context):
    names = [match.name for match in context.found.matches]
    assert "Testudo Walker" in names, names


@then('the results should include "Testudo Captain"')
def step_includes_captain(context):
    names = [match.name for match in context.found.matches]
    assert "Testudo Captain" in names, names


@then("the results should name each faction that has it")
def step_names_factions(context):
    factions = {match.faction for match in context.found.matches}
    assert factions == {"Test Guard", "Test Xenos"}, factions


@then("creed should not pick one on my behalf")
def step_no_pick(context):
    assert len(context.sheets) > 1, "creed narrowed a shared name to one"


@then("every result should be a Test Guard datasheet")
def step_all_tg(context):
    results = getattr(context, "matches", None) or context.found.matches
    factions = {match.faction for match in results}
    assert factions == {"Test Guard"}, factions


@then("creed should say nothing matched")
def step_nothing_matched(context):
    assert context.found.matches == [], context.found.matches


@then("creed should not invent a datasheet")
def step_no_invention(context):
    assert context.found.total == 0, context.found.total


@then("the answer should include its statline")
def step_has_statline(context):
    assert context.sheet.models and context.sheet.models[0]["T"]


@then("the answer should include its weapon profiles")
def step_has_weapons(context):
    assert context.sheet.wargear


@then("the answer should include its abilities")
def step_has_abilities(context):
    assert context.sheet.abilities


@then("the answer should include its keywords")
def step_has_keywords(context):
    assert context.sheet.keywords


@then("the answer should include its unit composition")
def step_has_composition(context):
    assert context.sheet.composition


@then("the answer should include its points cost")
def step_has_points(context):
    assert context.sheet.points.sizes


@then("the answer should give each model's statline separately")
def step_each_statline(context):
    assert len(context.sheet.models) > 1, context.sheet.models


@then("each statline should be named")
def step_statlines_named(context):
    assert all(model["name"] for model in context.sheet.models)


@then("each weapon should carry its range, attacks, skill, strength, AP and damage")
def step_weapon_fields(context):
    for weapon in context.sheet.wargear:
        for field in ("range", "A", "BS_WS", "S", "AP", "D"):
            assert weapon[field] is not None, (weapon["name"], field)


@then("each weapon should carry its own abilities")
def step_weapon_abilities(context):
    assert any(weapon["profile"] for weapon in context.sheet.wargear)


@then("the answer should give a cost for each size")
def step_cost_per_size(context):
    assert context.sheet.points.sizes == [5, 10], context.sheet.points.sizes


@then("each cost should say how many models it buys")
def step_cost_models(context):
    for tier in context.sheet.points.tiers:
        assert all(option.models for option in tier.options)


@then("the answer should give each tier")
def step_each_tier(context):
    assert len(context.sheet.points.tiers) == 2, context.sheet.points.tiers


@then("each tier should say which of your units it applies to")
def step_tier_labels(context):
    labels = [tier.label for tier in context.sheet.points.tiers]
    assert labels == ["1-2", "3+"], labels


@then("creed should not quote one price as though it were the price")
def step_not_one_price(context):
    assert context.sheet.points.escalates
    assert context.sheet.points.cost_for(5, 1) != context.sheet.points.cost_for(5, 3)


@then("the answer should list each option with its cost")
def step_wargear_listed(context):
    assert context.sheet.points.wargear
    assert context.sheet.points.wargear[0].cost == 5


@then("those costs should be kept apart from the unit's own cost")
def step_wargear_separate(context):
    unit_costs = {
        option.description
        for tier in context.sheet.points.tiers
        for option in tier.options
    }
    wargear = {option.description for option in context.sheet.points.wargear}
    assert not (unit_costs & wargear), unit_costs & wargear


@then("the answer should say which units it can lead")
def step_can_lead(context):
    assert [led["name"] for led in context.sheet.leads] == ["Testudo Guard"]


@then("the answer should include what it confers on the unit it leads")
def step_confers(context):
    assert context.sheet.abilities or context.sheet.leads


@then("the answer should say at what wounds it becomes damaged")
def step_damaged_at(context):
    assert context.sheet.damaged["wounds"] == "4", context.sheet.damaged


@then("the answer should say what changes")
def step_damaged_effect(context):
    assert "Objective Control" in context.sheet.damaged["effect"]


@then("the ability text should have no HTML tags in it")
def step_no_html(context):
    for ability in context.sheet.abilities:
        assert "<" not in ability["description"], ability["description"]


@then("the line breaks in the original should still be line breaks")
def step_line_breaks(context):
    joined = "\n".join(a["description"] for a in context.sheet.abilities)
    assert "\n" in joined, joined


@then("that keyword should still be emphasised in the markdown")
def step_keyword_emphasis(context):
    text = context.abilities[0]["description"]
    assert "**TESTUDO**" in text, text


@then("each item should still be its own item")
def step_list_items(context):
    text = context.abilities[0]["description"]
    assert text.count("* ") >= 2, text


@then("the answer should render it as a markdown table")
def step_markdown_table(context):
    assert "|" in to_markdown(context.table_html)


@then("no cell's text should have run into the next")
def step_cells_separate(context):
    rendered = to_markdown(context.table_html)
    assert "onetwo" not in rendered, rendered


@when("I look up an ability whose text contains a table")
def step_table_ability(context):
    context.table_html = (
        "<table><tbody><tr><td>one</td><td>two</td></tr></tbody></table>"
    )


@then("I should get every faction in the export")
def step_all_factions(context):
    assert {f["name"] for f in context.factions} == {"Test Guard", "Test Xenos"}


@then("each should carry the id the other tools take")
def step_faction_ids(context):
    assert all(faction["id"] for faction in context.factions)


@then("each should carry enough to look it up in full")
def step_match_ids(context):
    assert all(match.id for match in context.matches)


@when('I look up the stratagem "BRACE"')
def step_one_stratagem(context):
    with db.session() as connection:
        context.stratagems = rules.stratagems(connection, name="BRACE")


@when("I ask for stratagems in the Shooting phase")
def step_shooting(context):
    with db.session() as connection:
        context.stratagems = rules.stratagems(connection, phase="Shooting phase")


@when("I ask for stratagems in my own turn")
def step_my_turn(context):
    with db.session() as connection:
        context.stratagems = rules.stratagems(connection, turn="Your turn")


@when("I ask for stratagems in a named detachment")
def step_in_detachment(context):
    with db.session() as connection:
        context.stratagems = rules.stratagems(connection, detachment="DT1")


@when("I ask for stratagems costing at most 1 CP")
def step_cheap(context):
    with db.session() as connection:
        context.stratagems = rules.stratagems(connection, max_cp=1)


@when("I ask for my own turn, Shooting phase, at most 1 CP")
def step_combined(context):
    with db.session() as connection:
        context.stratagems = rules.stratagems(
            connection, turn="Your turn", phase="Shooting phase", max_cp=1
        )


@when('I ask which stratagems apply to "Testudo Guard"')
def step_datasheet_stratagems(context):
    with db.session() as connection:
        sheet = datasheets.by_name(connection, "Testudo Guard", "Test Guard")[0]
        context.stratagems = rules.stratagems_for_datasheet(connection, sheet.id)


@when("I look up a stratagem that is not in the export")
def step_no_stratagem(context):
    with db.session() as connection:
        context.stratagems = rules.stratagems(connection, name="BREAKFAST")


@when('I ask for stratagems in the "Breakfast phase"')
def step_bad_phase(context):
    with db.session() as connection:
        context.phases = rules.phases(connection)
        context.bad_phase = not any(
            "breakfast" in phase.lower() for phase in context.phases
        )


@then("I should get that stratagem")
def step_got_stratagem(context):
    assert [s.name for s in context.stratagems] == ["BRACE"], context.stratagems


@then("it should carry its CP cost")
def step_cp(context):
    assert context.stratagems[0].cp == 1


@then("it should carry when it can be used and what it does")
def step_when_what(context):
    stratagem = context.stratagems[0]
    assert stratagem.phase and stratagem.description


@then("every result should be usable in the Shooting phase")
def step_all_shooting(context):
    for stratagem in context.stratagems:
        assert not stratagem.phase or "Shooting" in stratagem.phase, stratagem.phase


@then("no result should be an opponent's-turn-only stratagem")
def step_no_opponent(context):
    for stratagem in context.stratagems:
        assert "Opponent" not in stratagem.turn, stratagem.turn


@then("every result should belong to that detachment or to the core rules")
def step_detachment_or_core(context):
    for stratagem in context.stratagems:
        assert stratagem.detachment_id in ("DT1", ""), stratagem.detachment_id


@then("no result should cost more than 1 CP")
def step_cheap_only(context):
    for stratagem in context.stratagems:
        assert stratagem.cp is None or stratagem.cp <= 1, stratagem.cp


@then("every result should satisfy all three")
def step_all_three(context):
    for stratagem in context.stratagems:
        assert not stratagem.turn or "Your" in stratagem.turn
        assert not stratagem.phase or "Shooting" in stratagem.phase
        assert stratagem.cp is None or stratagem.cp <= 1


@then("the results should be the ones the export ties to that datasheet")
def step_tied(context):
    assert {s.name for s in context.stratagems} == {"BRACE", "COMMAND RE-ROLL"}, [
        s.name for s in context.stratagems
    ]


@then("creed should say it found nothing")
def step_found_nothing(context):
    # Two features use this wording — one about a stratagem nobody has, one
    # about a detachment nobody has — so it asserts on whatever the scenario
    # actually looked up rather than on one of them.
    for name in ("stratagems", "detachments", "abilities", "enhancements"):
        found = getattr(context, name, None)
        if found is not None:
            assert found == [], (name, found)
            return
    raise AssertionError("the scenario looked nothing up")


@then("creed should not describe a stratagem it does not have")
def step_no_fabrication(context):
    assert context.stratagems == []


@then("creed should say which phases there are")
def step_lists_phases(context):
    assert context.phases, "no phases offered"


@then("creed should not return an empty list as though it were an answer")
def step_not_empty_answer(context):
    assert context.bad_phase, "a nonsense phase was accepted"


@when('I look up the ability "Testudo Resolve"')
def step_ability(context):
    with db.session() as connection:
        context.abilities = rules.abilities(connection, "Testudo Resolve")


@then("I should get its rules text")
def step_ability_text(context):
    assert context.abilities[0]["description"]


@then("it should say which faction it belongs to")
def step_ability_faction(context):
    assert context.abilities[0]["faction_id"] == "TG"


@when("I ask for the enhancements in a named detachment")
def step_enhancements(context):
    with db.session() as connection:
        context.enhancements = rules.enhancements(connection, detachment="DT1")


@then("every result should belong to that detachment")
def step_enh_detachment(context):
    for enhancement in context.enhancements:
        assert enhancement["detachment_id"] == "DT1"


@then("each should carry its points cost")
def step_enh_cost(context):
    assert all(e["cost"] is not None for e in context.enhancements)


@then("each should say which models can take it")
def step_enh_eligibility(context):
    assert all(e["eligibility"] for e in context.enhancements)


@when("I ask what a named detachment does")
def step_detachment_contents(context):
    with db.session() as connection:
        context.contents = detachments.contents(connection, "DT1")


@then("I should get its detachment ability")
def step_det_ability(context):
    assert context.contents["detachment"].ability["name"] == "Hold The Line"


@then("I should get the stratagems it brings")
def step_det_stratagems(context):
    assert context.contents["stratagems"]


@then("I should get the enhancements it brings")
def step_det_enhancements(context):
    assert context.contents["enhancements"]


@when('I look up "Testudo Guard"')
def step_look_up_guard(context):
    with db.session() as connection:
        context.sheets = datasheets.by_name(
            connection, "Testudo Guard", faction="Test Guard"
        )
        context.sheet = context.sheets[0]


@when('I search datasheets for "testudo guard"')
def step_search_guard_lowercase(context):
    _search(context, "testudo guard")


@then('the results should include "Testudo Guard"')
def step_includes_guard(context):
    names = [match.name for match in context.found.matches]
    assert "Testudo Guard" in names, names


@when('I search datasheets for "captain" in the Test Guard')
def step_search_captain_in_faction(context):
    _search(context, "captain", faction="Test Guard")
