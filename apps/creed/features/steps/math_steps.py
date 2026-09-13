"""Steps for the attack arithmetic."""

from behave import then, when

from creed import attack, datasheets, db


def _weapon(connection, unit, name):
    sheet = datasheets.by_name(connection, unit, faction="Test Guard")[0]
    found = [w for w in sheet.wargear if name.lower() in w["name"].lower()]
    assert found, f"{unit} has no weapon like {name!r}"
    return sheet, found[0]


def _target(connection, name="Testudo Walker"):
    return datasheets.by_name(connection, name)[0]


def _resolve(context, unit, weapon_name, target_name="Testudo Walker", models=1):
    with db.session() as connection:
        sheet, weapon = _weapon(connection, unit, weapon_name)
        target = _target(connection, target_name)
        context.attack = attack.resolve(
            weapon,
            target.models[0],
            attacker=sheet.name,
            target=target.name,
            models=models,
            target_keywords=tuple(target.keywords + target.faction_keywords),
        )
    return context.attack


@when('I work out "Testudo Guard" shooting at a target datasheet')
def step_basic(context):
    _resolve(context, "Testudo Guard", "Test rifle")


@when("I work out a weapon with Torrent")
def step_torrent(context):
    _resolve(context, "Testudo Walker", "Test flamer")


@when("I work out a weapon with Sustained Hits")
def step_sustained(context):
    # Compared against the same profile without the ability, because extra
    # hits do not make hits exceed attacks — at BS 3+ they never could, which
    # is what the first version of this step wrongly asserted.
    profile = {"name": "w", "A": "2", "BS_WS": "3", "S": "4", "AP": "-1", "D": "1"}
    target = {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"}
    context.attack = attack.resolve({**profile, "profile": "SUSTAINED HITS 1"}, target)
    context.baseline = attack.resolve(profile, target)


@when("I work out a weapon carrying an ability creed cannot apply")
def step_unmodelled(context):
    _resolve(context, "Testudo Guard", "Test flail")


@when("I work out any attack")
def step_any_attack(context):
    _resolve(context, "Testudo Guard", "Test rifle")


@when("I work out an attack whose profile has a value creed cannot parse")
def step_unparseable(context):
    try:
        attack.resolve(
            {
                "name": "broken",
                "A": "lots",
                "BS_WS": "3",
                "S": "4",
                "AP": "0",
                "D": "1",
            },
            {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"},
        )
        context.error = None
    except attack.UnreadableProfileError as error:
        context.error = error


@when("I work out an attack with AP -1 against a 3+ save")
def step_ap1(context):
    context.save = _save(ap="-1", armour="3+")


@when("I work out an attack with AP -3 against a 3+ save and a 4+ invulnerable")
def step_ap3_inv(context):
    context.save = _save(ap="-3", armour="3+", invulnerable="4")


@when("I work out an attack with AP -1 against a 2+ save and a 4+ invulnerable")
def step_ap1_inv(context):
    context.save = _save(ap="-1", armour="2+", invulnerable="4")


@when("I work out an attack with AP -4 against a 5+ save and no invulnerable")
def step_ap4(context):
    context.save = _save(ap="-4", armour="5+")


def _save(ap, armour, invulnerable=""):
    return attack.resolve(
        {"name": "w", "A": "1", "BS_WS": "3", "S": "4", "AP": ap, "D": "1"},
        {"T": "4", "Sv": armour, "invulnerable": invulnerable, "W": "1"},
    )


@when("I work out a damage 3 weapon against a 1-wound model")
def step_overkill(context):
    context.attack = attack.resolve(
        {"name": "w", "A": "1", "BS_WS": "3", "S": "8", "AP": "-4", "D": "3"},
        {"T": "4", "Sv": "6+", "invulnerable": "", "W": "1"},
    )


@when("I work out a damage 1 weapon against a 3-wound model")
def step_multi_wound(context):
    context.attack = attack.resolve(
        {"name": "w", "A": "6", "BS_WS": "2", "S": "8", "AP": "-4", "D": "1"},
        {"T": "4", "Sv": "6+", "invulnerable": "", "W": "3"},
    )


@when("I work out a weapon whose attacks are a dice roll")
def step_dice_attacks(context):
    _resolve(context, "Testudo Walker", "Test flamer")


@when("I work out a weapon with Twin-linked")
def step_twin(context):
    context.attack = attack.resolve(
        {
            "name": "w",
            "A": "2",
            "BS_WS": "3",
            "S": "4",
            "AP": "-1",
            "D": "1",
            "profile": "TWIN-LINKED",
        },
        {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"},
    )
    context.baseline = attack.resolve(
        {"name": "w", "A": "2", "BS_WS": "3", "S": "4", "AP": "-1", "D": "1"},
        {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"},
    )


@when("I work out a weapon with Lethal Hits")
def step_lethal(context):
    context.attack = attack.resolve(
        {
            "name": "w",
            "A": "6",
            "BS_WS": "3",
            "S": "3",
            "AP": "-1",
            "D": "1",
            "profile": "LETHAL HITS",
        },
        {"T": "8", "Sv": "3+", "invulnerable": "", "W": "1"},
    )
    context.baseline = attack.resolve(
        {"name": "w", "A": "6", "BS_WS": "3", "S": "3", "AP": "-1", "D": "1"},
        {"T": "8", "Sv": "3+", "invulnerable": "", "W": "1"},
    )


@when("I work out a weapon with Devastating Wounds")
def step_devastating(context):
    context.attack = attack.resolve(
        {
            "name": "w",
            "A": "6",
            "BS_WS": "3",
            "S": "4",
            "AP": "0",
            "D": "1",
            "profile": "DEVASTATING WOUNDS",
        },
        {"T": "4", "Sv": "2+", "invulnerable": "", "W": "1"},
    )
    context.baseline = attack.resolve(
        {"name": "w", "A": "6", "BS_WS": "3", "S": "4", "AP": "0", "D": "1"},
        {"T": "4", "Sv": "2+", "invulnerable": "", "W": "1"},
    )


@when("I compare two of my units shooting the same target")
def step_compare_units(context):
    with db.session() as connection:
        target = _target(connection)
        context.comparison = []
        for unit, weapon in (
            ("Testudo Guard", "Test rifle"),
            ("Testudo Captain", "Test blade"),
        ):
            sheet, profile = _weapon(connection, unit, weapon)
            context.comparison.append(
                attack.resolve(profile, target.models[0], attacker=sheet.name)
            )


@when("I ask what a unit's weapons are best into")
def step_best_into(context):
    with db.session() as connection:
        _, weapon = _weapon(connection, "Testudo Guard", "Test rifle")
        context.spread = [
            attack.resolve(
                weapon, {"T": str(t), "Sv": save, "invulnerable": "", "W": "2"}
            )
            for t in (4, 8)
            for save in ("3+", "6+")
        ]


@then("I should get the chance to hit")
def step_hit_chance(context):
    assert any(step.label == "hit" for step in context.attack.steps)


@then("I should get the chance to wound")
def step_wound_chance(context):
    assert any(step.label == "wound" for step in context.attack.steps)


@then("I should get the chance the save fails")
def step_save_chance(context):
    assert any(step.label == "save" for step in context.attack.steps)


@then("I should get the damage I should expect")
def step_expected_damage(context):
    assert context.attack.expected_damage > 0


@then("the save needed should be {needed:d}+")
def step_save_needed(context, needed):
    assert context.save.save_needed == needed, context.save.save_needed


@then("the save used should be the invulnerable one")
def step_uses_invuln(context):
    assert context.save.save_used == "invulnerable", context.save.save_used


@then("the save used should be the armour one")
def step_uses_armour(context):
    assert context.save.save_used == "armour", context.save.save_used


@then("there should be no save")
def step_no_save(context):
    assert context.save.save_needed is None, context.save.save_needed


@then("the spilled damage should not carry to the next model")
def step_no_spill(context):
    assert context.attack.expected_kills < context.attack.expected_damage


@then("the expected kills should reflect that")
def step_kills_capped(context):
    assert context.attack.expected_kills == context.attack.expected_unsaved


@then("the expected kills should account for the wounds needed")
def step_kills_multi_wound(context):
    assert context.attack.expected_kills == context.attack.expected_damage / 3


@then("the expected attacks should use the average of that dice")
def step_dice_average(context):
    assert context.attack.attacks == 3.5, context.attack.attacks


@then("the hit step should be skipped")
def step_hit_skipped(context):
    assert context.attack.hit_needed is None


@then("the answer should say why")
def step_says_why(context):
    assert any("Torrent" in step.detail for step in context.attack.steps)


@then("the wound chance should account for the re-roll")
def step_reroll(context):
    assert context.attack.expected_damage > context.baseline.expected_damage


@then("the extra hits should be in the expected damage")
def step_sustained_more(context):
    assert context.attack.expected_hits > context.baseline.expected_hits
    assert context.attack.expected_damage > context.baseline.expected_damage


@then("the hits that wound automatically should skip the wound roll")
def step_lethal_more(context):
    assert context.attack.expected_wounds > context.baseline.expected_wounds


@then("the critical wounds should bypass the save")
def step_devastating_more(context):
    assert context.attack.expected_unsaved > context.baseline.expected_unsaved


@then("the answer should name that ability")
def step_names_ability(context):
    assert context.attack.not_applied, context.attack


@then("the answer should say it was not applied")
def step_says_not_applied(context):
    assert "CLEAVE 2" in context.attack.not_applied[0], context.attack.not_applied


@then("the answer should still give the arithmetic it did do")
def step_still_arithmetic(context):
    assert context.attack.expected_damage > 0


@then("the answer should state the modifiers it applied")
def step_states_modifiers(context):
    assert context.attack.steps


@then("the answer should be reproducible from what it states")
def step_reproducible(context):
    assert context.attack.wound_needed and context.attack.attacks


@then("I should get the expected damage of each")
def step_each_damage(context):
    assert len(context.comparison) == 2
    assert all(result.expected_damage >= 0 for result in context.comparison)


@then("I should get which is better and by how much")
def step_which_better(context):
    first, second = context.comparison
    assert first.expected_damage != second.expected_damage


@then("I should get its expected damage against a spread of toughness and saves")
def step_spread(context):
    assert len(context.spread) == 4
    assert len({round(r.expected_damage, 4) for r in context.spread}) > 1


@then("creed should say which value it could not read")
def step_names_value(context):
    assert context.error is not None
    assert "lots" in str(context.error), context.error


@then("creed should not substitute a number of its own")
def step_no_substitute(context):
    assert isinstance(context.error, attack.UnreadableProfileError)
