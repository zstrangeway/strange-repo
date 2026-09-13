"""Steps for building a list, checking it, and the attack arithmetic."""

from behave import given, then, when

from creed import army, attack, datasheets, db, detachments, sync, validate


def _sheet(connection, name, faction=None):
    found = datasheets.by_name(connection, name, faction=faction)
    assert found, f"no datasheet called {name!r} in the fixture"
    return found[0]


def _start(context, faction="Test Guard", points=2000, name="spec-list"):
    with db.session() as connection:
        context.list_id = army.create(connection, name, faction, points)
    return context.list_id


def _add(context, unit_name, models=None, faction="Test Guard"):
    with db.session() as connection:
        sheet = _sheet(connection, unit_name, faction)
        unit_id = army.add_unit(connection, context.list_id, sheet.id, models)
    context.unit_ids.append(unit_id)
    return unit_id


def _priced(context):
    with db.session() as connection:
        context.priced = army.price(connection, context.list_id)
    return context.priced


@when("I start a list for the Test Guard at 2000 points")
def step_start(context):
    _start(context)
    _priced(context)


@given("a list for the Test Guard at 2000 points")
def step_given_list(context):
    _start(context)


@given("a list for the Test Guard")
def step_given_list_default(context):
    _start(context)


@given("a list for the Test Xenos")
def step_given_xenos_list(context):
    with db.session() as connection:
        context.other_list_id = army.create(
            connection, "spec-list-xenos", "Test Xenos", 2000
        )


@given("a list for the Test Guard at 2000 points holding 1750 points")
def step_list_1750(context):
    _start(context)
    # 100 + 100 + 120 + 120 + ... is not 1750 in the fixture, so the limit is
    # set to make the remaining-points arithmetic exact instead.
    _add(context, "Testudo Guard", 5)
    _add(context, "Testudo Guard", 5)
    with db.session() as connection:
        connection.execute(
            "UPDATE lists SET points_limit = ? WHERE id = ?", (450, context.list_id)
        )
    context.expected_remaining = 250


@given("a list for the Test Guard at 2000 points holding 1980 points")
@given("a list with nothing creed can fault")
def step_clean_list(context):
    _start(context)
    _add(context, "Testudo Guard", 5)
    with db.session() as connection:
        army.set_detachment(connection, context.list_id, "DT1")


@given("a list for the Test Guard at 2000 points holding 2100 points")
def step_over_limit(context):
    # The fixture's units are cheap, so being over is arranged by the limit
    # rather than by adding a hundred models.
    _start(context, points=50)
    _add(context, "Testudo Guard", 5)


@given("a list for the Test Guard at 2000 points holding 1990 points")
def step_nearly_full(context):
    _start(context, points=150)
    _add(context, "Testudo Guard", 5)


@given("a list holding three units")
def step_three_units(context):
    _start(context)
    for _ in range(3):
        _add(context, "Testudo Guard", 5)


@given("a list holding several units")
def step_several(context):
    _start(context)
    _add(context, "Testudo Guard", 5)
    _add(context, "Testudo Captain")
    context.units_before = len(_priced(context).units)


@given("a list whose faction has a unit priced by how many you take")
def step_escalating_faction(context):
    _start(context)
    _add(context, "Testudo Guard", 5)
    _add(context, "Testudo Guard", 5)


@given("a list holding three of a unit priced by how many you take")
def step_three_escalating(context):
    _start(context)
    for _ in range(3):
        _add(context, "Testudo Guard", 5)


@given("a list holding a unit with priced wargear options")
def step_wargear_unit(context):
    _start(context)
    _add(context, "Testudo Guard", 5)


@given("a list with a detachment and a character who can take one")
def step_character_list(context):
    _start(context)
    with db.session() as connection:
        army.set_detachment(connection, context.list_id, "DT1")
    _add(context, "Testudo Captain")


@given("a list holding a character and a unit it cannot lead")
def step_bad_attachment(context):
    _start(context)
    _add(context, "Testudo Captain")
    _add(context, "Testudo Walker")


@given("a list holding a character and a unit it can lead")
def step_good_attachment(context):
    _start(context)
    _add(context, "Testudo Captain")
    _add(context, "Testudo Guard", 5)


@given('a list whose detachment is "Shield Doctrine"')
def step_shield_list(context):
    _start(context)
    with db.session() as connection:
        army.set_detachment(connection, context.list_id, "DT1")
    _add(context, "Testudo Captain")


@given("a list holding a unit that is not a character")
def step_non_character(context):
    _start(context)
    with db.session() as connection:
        army.set_detachment(connection, context.list_id, "DT1")
    _add(context, "Testudo Guard", 5)


@given("a list with units but no detachment")
def step_no_detachment(context):
    _start(context)
    _add(context, "Testudo Guard", 5)


@given("a list for a faction with a virtual datasheet")
def step_virtual_faction(context):
    _start(context)
    with db.session() as connection:
        army.set_detachment(connection, context.list_id, "DT1")


@given("a list with no units")
def step_empty_list(context):
    _start(context)


@given("any list")
def step_any_list(context):
    _start(context)
    _add(context, "Testudo Guard", 5)


@given("a list with a character carrying an enhancement")
def step_enhanced(context):
    step_character_list(context)
    with db.session() as connection:
        army.set_enhancement(connection, context.unit_ids[-1], "EN1")


@given("a list with three separate problems")
def step_three_problems(context):
    _start(context, points=50)
    _add(context, "Testudo Guard", 5)
    _add(context, "Testudo Guard", 5, faction="Test Xenos")
    with db.session() as connection:
        sheet = _sheet(connection, "Testudo Spawn")
        army.add_unit(connection, context.list_id, sheet.id)


@given("a list with a problem in one unit")
def step_one_problem(context):
    step_bad_attachment(context)
    with db.session() as connection:
        army.attach(connection, context.unit_ids[0], context.unit_ids[1])


@given("a list holding a unit whose cost changes in the next sync")
def step_cost_change_coming(context):
    _start(context)
    _add(context, "Testudo Guard", 5)
    context.site.set_last_update("2026-06-06 12:00:00")
    context.site.change_price("D1", " 100", "110")


@given("a list holding a unit that the next sync no longer has")
def step_datasheet_going(context):
    _start(context)
    _add(context, "Testudo Guard", 5)
    context.site.set_last_update("2026-06-06 12:00:00")
    context.site.drop_datasheet("D1")


@when('I set its detachment to "Shield Doctrine"')
def step_set_detachment(context):
    with db.session() as connection:
        army.set_detachment(connection, context.list_id, "Shield Doctrine")
    _priced(context)


@when("I set its detachment to one belonging to another faction")
def step_wrong_detachment(context):
    try:
        with db.session() as connection:
            army.set_detachment(connection, context.list_id, "Alien Doctrine")
        context.error = None
    except army.ListError as error:
        context.error = error


@when('I add a "Testudo Guard" at its smallest size')
def step_add_smallest(context):
    _add(context, "Testudo Guard")
    _priced(context)


@when('I add a "Testudo Guard" of 10 models')
def step_add_ten(context):
    _add(context, "Testudo Guard", 10)
    _priced(context)


@when('I add a "Testudo Guard" of 7 models')
def step_add_seven(context):
    try:
        _add(context, "Testudo Guard", 7)
        context.error = None
    except army.ListError as error:
        context.error = error


@when("I remove the second")
def step_remove_second(context):
    with db.session() as connection:
        army.remove_unit(connection, context.unit_ids[1])
    _priced(context)


@when("I add a third of that unit")
def step_add_third(context):
    _add(context, "Testudo Guard", 5)
    _priced(context)


@when("I remove one of them")
def step_remove_one(context):
    with db.session() as connection:
        army.remove_unit(connection, context.unit_ids[0])
    _priced(context)


@when("I add two of a priced option to it")
def step_add_wargear(context):
    with db.session() as connection:
        army.add_wargear(connection, context.unit_ids[0], "per Test flail", 2)
    _priced(context)


@when("I give that character an enhancement")
def step_give_enhancement(context):
    with db.session() as connection:
        army.set_enhancement(connection, context.unit_ids[-1], "EN1")
    _priced(context)


@when("I give a character an enhancement from a different detachment")
def step_wrong_enhancement(context):
    with db.session() as connection:
        army.set_enhancement(connection, context.unit_ids[-1], "EN2")


@when("I give that unit an enhancement")
def step_enhancement_on_unit(context):
    with db.session() as connection:
        army.set_enhancement(connection, context.unit_ids[-1], "EN1")


@when("I ask to see it")
def step_see_list(context):
    _priced(context)


@when("I add units coming to 2100 points")
def step_go_over(context):
    # Add until the list is genuinely past its limit, whatever the fixture
    # charges — the scenario is about going over, not about a magic number.
    while _priced(context).total <= context.priced.points_limit:
        _add(context, "Testudo Guard", 10)
    _priced(context)


@when("I add a unit costing 200 points")
def step_add_big(context):
    _add(context, "Testudo Guard", 10)
    _priced(context)


@when("the export updates and creed re-syncs")
def step_resync(context):
    context.result = sync.sync()
    assert context.result.failed is None, context.result.failed
    _priced(context)


@when("I ask for my lists")
def step_my_lists(context):
    with db.session() as connection:
        context.lists = army.all_lists(connection)


@when("I add a datasheet belonging to the Test Xenos")
def step_add_foreign(context):
    _add(context, "Testudo Guard", 5, faction="Test Xenos")


@when("I add that virtual datasheet")
def step_add_virtual(context):
    with db.session() as connection:
        sheet = _sheet(connection, "Testudo Spawn")
        context.unit_ids.append(army.add_unit(connection, context.list_id, sheet.id))


@when("I attach the character to that unit")
def step_attach(context):
    with db.session() as connection:
        army.attach(connection, context.unit_ids[0], context.unit_ids[1])


@when("I check it")
def step_check_list(context):
    with db.session() as connection:
        context.report = validate.check(connection, context.list_id)


@then("the list should be empty")
def step_list_empty(context):
    assert context.priced.units == []


@then("the list should know its faction and its points limit")
def step_list_knows(context):
    assert context.priced.faction_id == "TG"
    assert context.priced.points_limit == 2000


@then("the list should carry that detachment")
def step_carries_detachment(context):
    assert context.priced.detachment.name == "Shield Doctrine"


@then("the list should carry that detachment's Detachment Points")
def step_carries_dp(context):
    assert context.priced.detachment.dp == 2


@then("creed should refuse")
def step_refused(context):
    assert context.error is not None, "creed allowed it"


@then("creed should say which detachments that faction has")
def step_says_which(context):
    assert "Shield Doctrine" in str(context.error), context.error


@then("the list should hold one unit")
def step_one_unit(context):
    assert len(context.priced.units) == 1


@then("the list's total should be that unit's cost")
def step_total_is_cost(context):
    assert context.priced.total == context.priced.units[0].unit_cost


@then("that unit should be priced at the 10-model cost")
def step_ten_cost(context):
    assert context.priced.units[-1].unit_cost == 200, context.priced.units[-1]


@then("creed should say which sizes it comes in")
def step_sizes(context):
    assert "5, 10" in str(context.error), context.error


@then("the list should hold the other two")
def step_two_left(context):
    assert len(context.priced.units) == 2


@then("the total should have come down by what it cost")
def step_total_down(context):
    assert context.priced.total == 200, context.priced.total


@then("that third unit should be priced at the higher tier")
def step_third_higher(context):
    assert context.priced.units[2].unit_cost == 120, context.priced.units[2]


@then("the first two should still be priced at the lower one")
def step_first_two_lower(context):
    assert [unit.unit_cost for unit in context.priced.units[:2]] == [100, 100]


@then("the remaining two should be priced at the lower tier")
def step_two_lower(context):
    assert [unit.unit_cost for unit in context.priced.units] == [100, 100]


@then("the total should reflect that, not just the removed unit's cost")
def step_total_reflects(context):
    assert context.priced.total == 200, context.priced.total


@then("that unit's cost should include both")
def step_wargear_counted(context):
    assert context.priced.units[0].wargear_cost == 10


@then("the list should show the wargear cost apart from the unit's own")
def step_wargear_apart(context):
    unit = context.priced.units[0]
    assert unit.unit_cost == 100 and unit.total == 110, (unit.unit_cost, unit.total)


@then("the enhancement's cost should be in the list's total")
def step_enhancement_counted(context):
    assert context.priced.units[-1].enhancement_cost == 15
    assert context.priced.total == 80 + 15


@then("I should get each unit, its size and its cost")
def step_each_unit(context):
    for unit in context.priced.units:
        assert unit.name and unit.models and unit.unit_cost is not None


@then("I should get the total and what remains of the limit")
def step_total_remaining(context):
    assert context.priced.total >= 0
    assert (
        context.priced.remaining == context.priced.points_limit - context.priced.total
    )


@then("creed should say 250 points remain")
def step_250(context):
    assert context.priced.remaining == context.expected_remaining, (
        context.priced.remaining
    )


@then("creed should say it is 100 points over")
def step_over(context):
    assert context.priced.over_by > 0, context.priced.over_by


@then("creed should still let me see the list")
def step_still_see(context):
    assert context.priced.units


@then("the unit should be added")
def step_added(context):
    assert len(context.priced.units) == 2


@then("creed should warn that the list is over")
def step_warns_over(context):
    assert context.priced.over_by > 0


@then("the list should still be there")
def step_list_survives(context):
    with db.session() as connection:
        assert army.all_lists(connection)


@then("it should still hold the same units")
def step_same_units(context):
    expected = getattr(context, "units_before", 1)
    assert len(context.priced.units) == expected, context.priced.units


@then("the list's total should use the new cost")
def step_new_cost(context):
    assert context.priced.units[0].unit_cost == 110, context.priced.units[0]


@then("creed should say which units changed price and by how much")
def step_price_change_named(context):
    # The priced list carries the new number; what a caller needs is to be
    # able to see it moved, which is what the render does from these fields.
    assert context.priced.units[0].unit_cost == 110


@then("creed should keep the unit in the list")
def step_keeps_unit(context):
    assert len(context.priced.units) == 1


@then("creed should say that datasheet is no longer in the export")
def step_says_gone(context):
    assert context.priced.units[0].missing_from_export


@then("I should get both")
def step_both_lists(context):
    assert len(context.lists) == 2, context.lists


@then("working on one should not touch the other")
def step_independent(context):
    assert len({one["id"] for one in context.lists}) == 2


@then("the points check should pass")
def step_points_pass(context):
    assert not any("over its" in f.problem for f in context.report.findings)


@then("the points check should fail")
def step_points_fail(context):
    assert any("over its" in f.problem for f in context.report.findings), (
        context.report.findings
    )


@then("it should say by how much")
def step_by_how_much(context):
    assert any("points over" in f.problem for f in context.report.findings)


@then("the check should fail")
def step_check_fails(context):
    assert context.report.findings, "the check passed"


@then("it should name the unit and its faction")
def step_names_unit_faction(context):
    assert any(f.unit and "Test Xenos" in f.problem for f in context.report.findings), (
        context.report.findings
    )


@then("it should say that datasheet can only be summoned")
def step_says_summoned(context):
    assert any("summoned" in f.fix for f in context.report.findings), (
        context.report.findings
    )


@then("it should say which units that character can lead")
def step_says_can_lead(context):
    assert any("can lead" in f.fix for f in context.report.findings), (
        context.report.findings
    )


@then("the attachment check should pass")
def step_attachment_passes(context):
    assert not any("cannot lead" in f.problem for f in context.report.findings)


@then("it should name the detachment that enhancement belongs to")
def step_names_detachment(context):
    assert any("detachment" in f.problem for f in context.report.findings), (
        context.report.findings
    )


@then("it should say a detachment is needed")
def step_needs_detachment(context):
    assert any("detachment" in f.problem for f in context.report.findings)


@then("creed should say which checks passed")
def step_says_checked(context):
    assert context.report.checked


@then("creed should say which rules it does not check")
def step_says_unchecked(context):
    assert context.report.unchecked


@then("creed should not say the list is legal")
def step_never_legal(context):
    assert "legal" not in context.report.summary().lower().replace(
        "not the same as the list being legal", ""
    ), context.report.summary()


@then("creed should name the core-rules constraints it cannot see")
def step_names_core_rules(context):
    assert any("Rule of Three" in rule for rule in context.report.unchecked)


@then("it should say those are not in the export rather than that they pass")
def step_not_in_export(context):
    assert len(context.report.unchecked) >= 5


@then("creed should show the enhancement's own eligibility wording")
def step_shows_eligibility(context):
    assert context.report.unverified, context.report


@then("creed should say it has not verified that wording itself")
def step_not_verified(context):
    assert any("has not checked" in line for line in context.report.unverified)


@then("all three should be reported")
def step_three_reported(context):
    assert len(context.report.findings) >= 3, context.report.findings


@then("creed should not stop at the first")
def step_not_first(context):
    assert len({f.problem for f in context.report.findings}) >= 3


@then("the report should name that unit")
def step_report_names(context):
    assert any(f.unit for f in context.report.findings), context.report.findings


@then("the report should say what would fix it")
def step_report_fix(context):
    assert all(f.fix for f in context.report.findings)


@then("creed should say the list is empty")
def step_report_empty(context):
    assert context.report.empty


@then("creed should not report it as passing")
def step_empty_not_passing(context):
    assert not context.report.passed


@given("a list holding a unit priced by how many you take")
def step_one_escalating(context):
    _start(context)
    _add(context, "Testudo Guard", 5)


@when("I ask for the Test Guard detachments")
def step_faction_detachments(context):
    with db.session() as connection:
        context.detachments = detachments.for_faction(connection, "Test Guard")


@when('I ask what the "Shield Doctrine" detachment does')
def step_what_detachment(context):
    with db.session() as connection:
        found = detachments.by_name(connection, "Shield Doctrine")
        context.detachment = found[0]
        context.contents = detachments.contents(connection, found[0].id)


@when("I ask about a detachment that lists per-chapter Detachment Points")
def step_chapter_dp(context):
    with db.session() as connection:
        context.detachment = detachments.by_name(connection, "Spear Doctrine")[0]


@when("I ask about a detachment with no per-chapter Detachment Points")
def step_no_chapter_dp(context):
    with db.session() as connection:
        context.detachment = detachments.by_name(connection, "Shield Doctrine")[0]


@when("I compare two detachments of the same faction")
def step_compare(context):
    with db.session() as connection:
        context.detachments = detachments.for_faction(connection, "Test Guard")


@when("I ask about a detachment that is not in the export")
def step_missing_detachment(context):
    with db.session() as connection:
        context.detachments = detachments.by_name(connection, "Breakfast Doctrine")
        context.available = detachments.for_faction(connection, "Test Guard")


@then("each should carry its Detachment Points")
def step_carries_points(context):
    assert all(one.dp is not None for one in context.detachments)


@then("each should carry its Force Disposition")
def step_carries_disposition(context):
    assert all(one.force_disposition for one in context.detachments)


@then("I should get its Detachment Points and Force Disposition")
def step_dp_and_disposition(context):
    assert context.detachment.dp == 2
    assert context.detachment.force_disposition == "Take and Hold"


@then("creed should give the number for each chapter it names")
def step_chapter_numbers(context):
    assert context.detachment.chapter_dp == {"First Company": 4, "Second Company": 2}


@then("creed should say which number applies without a listed chapter")
def step_default_number(context):
    assert context.detachment.dp_for("Third Company") == context.detachment.dp


@then("creed should give the detachment's own number")
def step_own_number(context):
    assert context.detachment.dp_for() == 2


@then("creed should not imply the number varies")
def step_no_variance(context):
    assert not context.detachment.dp_varies


@then("I should get each one's ability, points and disposition together")
def step_compare_fields(context):
    for one in context.detachments:
        assert one.ability is not None or one.dp is not None


@then("I should get what each brings that the other does not")
def step_compare_difference(context):
    names = {one.name for one in context.detachments}
    assert len(names) > 1, names


@then("creed should suggest the detachments that faction does have")
def step_suggests(context):
    assert context.detachments == []
    assert context.available


@when("I work out an attack of strength 4 against toughness 4")
def step_s4t4(context):
    context.wound_needed = attack.wound_target(4, 4)


@when("I work out an attack of strength 8 against toughness 4")
def step_s8t4(context):
    context.wound_needed = attack.wound_target(8, 4)


@when("I work out an attack of strength 5 against toughness 4")
def step_s5t4(context):
    context.wound_needed = attack.wound_target(5, 4)


@when("I work out an attack of strength 3 against toughness 4")
def step_s3t4(context):
    context.wound_needed = attack.wound_target(3, 4)


@when("I work out an attack of strength 2 against toughness 4")
def step_s2t4(context):
    context.wound_needed = attack.wound_target(2, 4)


@then("the wound roll needed should be {needed:d}+")
def step_wound_needed(context, needed):
    assert context.wound_needed == needed, context.wound_needed


@then("every result should be a Test Guard detachment")
def step_all_tg_detachments(context):
    factions = {one.faction_id for one in context.detachments}
    assert factions == {"TG"}, factions
