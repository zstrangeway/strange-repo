"""The remaining branches: edge cases the specs and the CLI do not walk."""

import os
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta

from scratch import CreedTestCase

from creed import (
    answers,
    army,
    attack,
    datasheets,
    db,
    detachments,
    export,
    fetch,
    markup,
    paths,
    pricing,
    render,
    rules,
    sync,
    validate,
)


class TestProvenance(CreedTestCase):
    def test_it_carries_the_fields_a_caller_needs(self):
        with db.session() as connection:
            block = answers.provenance(connection).as_dict()
        self.assertEqual(block["data_as_of"], "2026-01-01 00:00:00")
        self.assertIn("Wahapedia", block["source"])
        self.assertEqual(block["warnings"], [])

    def test_a_check_older_than_a_week_warns(self):
        stale = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        with db.session() as connection:
            db.set_state(connection, sync.LAST_CHECKED_KEY, stale)
        with db.session() as connection:
            self.assertTrue(answers.provenance(connection).warnings)

    def test_a_recent_check_does_not_warn(self):
        with db.session() as connection:
            self.assertEqual(answers.provenance(connection).warnings, [])

    def test_a_timestamp_it_cannot_parse_is_not_a_warning(self):
        with db.session() as connection:
            db.set_state(connection, sync.LAST_CHECKED_KEY, "the day before yesterday")
        with db.session() as connection:
            self.assertEqual(answers.provenance(connection).warnings, [])

    def test_no_timestamp_at_all(self):
        with db.session() as connection:
            db.set_state(connection, sync.LAST_CHECKED_KEY, None)
        with db.session() as connection:
            self.assertEqual(answers.provenance(connection).warnings, [])


class TestPaths(unittest.TestCase):
    def test_creed_home_wins(self):
        with unittest.mock.patch.dict(os.environ, {"CREED_HOME": "/tmp/somewhere"}):
            self.assertEqual(str(paths.home()), "/tmp/somewhere")

    def test_it_falls_back_to_the_cache_directory(self):
        environment = {k: v for k, v in os.environ.items() if k != "CREED_HOME"}
        environment["XDG_CACHE_HOME"] = "/tmp/cache"
        with unittest.mock.patch.dict(os.environ, environment, clear=True):
            self.assertEqual(str(paths.home()), "/tmp/cache/creed")

    def test_and_to_a_default_when_there_is_no_xdg(self):
        environment = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CREED_HOME", "XDG_CACHE_HOME")
        }
        with unittest.mock.patch.dict(os.environ, environment, clear=True):
            self.assertTrue(str(paths.home()).endswith("/.cache/creed"))


class TestMarkup(unittest.TestCase):
    def test_nothing_at_all(self):
        self.assertEqual(markup.to_markdown(None), "")
        self.assertEqual(markup.to_markdown(""), "")

    def test_wahapedias_own_keyword_tag(self):
        self.assertEqual(markup.to_markdown("<ky>ORKS</ky>"), "**ORKS**")

    def test_a_span_that_is_not_a_keyword(self):
        self.assertEqual(markup.to_markdown('<span class="plain">x</span>'), "x")

    def test_the_version_marker_is_parenthesised_not_welded(self):
        rendered = markup.to_markdown(
            '<div class="abName">DEEP STRIKE<span class="h_number">24.09</span></div>'
        )
        self.assertEqual(rendered, "DEEP STRIKE (24.09)")

    def test_an_empty_div_adds_nothing(self):
        self.assertEqual(markup.to_markdown("<div></div>"), "")

    def test_a_table_keeps_its_cells_apart(self):
        rendered = markup.to_markdown(
            "<table><tbody><tr><td>one</td><td>two</td></tr></tbody></table>"
        )
        self.assertNotIn("onetwo", rendered)


class TestFetch(CreedTestCase):
    sync_on_setup = False

    def test_a_status_that_is_neither_200_nor_304(self):
        table = export.TABLES_BY_NAME["Factions"]
        with (
            unittest.mock.patch.object(self.site, "tables", {}),
            fetch.Fetcher() as fetcher,
            self.assertRaises(fetch.ExportUnreachableError) as caught,
        ):
            fetcher.get(table, fetch.Validators())
        self.assertIn("404", str(caught.exception))

    def test_a_connection_that_fails(self):
        self.site.close()
        with (
            fetch.Fetcher() as fetcher,
            self.assertRaises(fetch.ExportUnreachableError),
        ):
            fetcher.get(export.TABLES_BY_NAME["Factions"], fetch.Validators())

    def test_a_matching_validator_gives_a_304(self):
        table = export.TABLES_BY_NAME["Factions"]
        with fetch.Fetcher() as fetcher:
            first = fetcher.get(table, fetch.Validators())
            self.assertTrue(first.changed)
            again = fetcher.get(table, fetch.Validators(etag=first.etag))
        self.assertTrue(again.not_modified)
        self.assertIsNone(again.text)


class TestSync(CreedTestCase):
    def test_check_reports_whether_anything_moved(self):
        self.assertFalse(sync.check()["stale"])
        self.site.set_last_update("2027-01-01 00:00:00")
        self.assertTrue(sync.check()["stale"])

    def test_an_empty_marker_file(self):
        self.site.tables["Last_update"] = "﻿last_update|\n"
        with self.assertRaises(sync.MalformedTableError):
            sync.sync(force=True)

    def test_a_record_with_the_wrong_number_of_fields(self):
        self.site.tables["Factions"] = "﻿id|name|link|\nTG|only-two|\n"
        self.site.set_last_update("2027-01-01 00:00:00")
        result = sync.sync()
        self.assertIn("fields", result.failed)

    def test_a_borrowed_fetcher_is_not_closed(self):
        with fetch.Fetcher() as fetcher:
            sync.check(fetcher)
            # Still usable afterwards, which is the point of borrowing.
            self.assertTrue(sync.read_marker(fetcher))

    def test_status_before_any_sync_has_no_counts(self):
        with db.session() as connection:
            db.set_state(connection, sync.LAST_UPDATE_KEY, None)
        state = sync.status()
        self.assertFalse(state["synced"])
        self.assertEqual(state["rows"], 0)


class TestArmyEdges(CreedTestCase):
    def _list(self):
        with db.session() as connection:
            return army.create(connection, "edges", "Test Guard", 2000)

    def test_adding_a_datasheet_id_that_is_not_there(self):
        list_id = self._list()
        with db.session() as connection, self.assertRaises(army.ListError):
            army.add_unit(connection, list_id, "NOPE")

    def test_a_list_that_is_not_there(self):
        with db.session() as connection, self.assertRaises(army.ListError):
            army.price(connection, 999)

    def test_wargear_on_a_unit_that_is_not_there(self):
        with db.session() as connection, self.assertRaises(army.ListError):
            army.add_wargear(connection, 999, "per Test flail")

    def test_wargear_the_datasheet_does_not_price(self):
        list_id = self._list()
        with db.session() as connection:
            unit_id = army.add_unit(connection, list_id, "D1", 5)
            with self.assertRaises(army.ListError) as caught:
                army.add_wargear(connection, unit_id, "per Nothing")
        self.assertIn("per Test flail", str(caught.exception))

    def test_wargear_on_a_datasheet_that_prices_none(self):
        list_id = self._list()
        with db.session() as connection:
            unit_id = army.add_unit(connection, list_id, "D3")
            with self.assertRaises(army.ListError) as caught:
                army.add_wargear(connection, unit_id, "per Anything")
        self.assertIn("none", str(caught.exception))

    def test_an_enhancement_on_a_unit_that_is_not_there(self):
        with db.session() as connection, self.assertRaises(army.ListError):
            army.set_enhancement(connection, 999, "EN1")

    def test_an_enhancement_id_that_is_not_there_is_simply_absent(self):
        list_id = self._list()
        with db.session() as connection:
            unit_id = army.add_unit(connection, list_id, "D2")
            army.set_enhancement(connection, unit_id, "NOPE")
            priced = army.price(connection, list_id)
        self.assertIsNone(priced.units[0].enhancement)

    def test_a_datasheet_that_leaves_the_export(self):
        list_id = self._list()
        with db.session() as connection:
            army.add_unit(connection, list_id, "D1", 5)
            connection.execute("DELETE FROM Datasheets WHERE id = 'D1'")
            priced = army.price(connection, list_id)
        self.assertTrue(priced.units[0].missing_from_export)
        self.assertEqual(priced.total, 0)

    def test_a_detachment_named_rather_than_given_by_id(self):
        list_id = self._list()
        with db.session() as connection:
            army.set_detachment(connection, list_id, "Shield Doctrine")
            self.assertEqual(army.price(connection, list_id).detachment.id, "DT1")

    def test_a_detachment_name_that_matches_nothing(self):
        list_id = self._list()
        with db.session() as connection, self.assertRaises(army.ListError):
            army.set_detachment(connection, list_id, "Nothing Like This")

    def test_detaching_a_leader(self):
        list_id = self._list()
        with db.session() as connection:
            leader = army.add_unit(connection, list_id, "D2")
            army.attach(connection, leader, None)
            self.assertIsNone(army.price(connection, list_id).units[0].attached_to)


class TestAttackEdges(unittest.TestCase):
    def test_an_empty_value_with_a_default(self):
        self.assertEqual(attack.average("", default=1.0), 1.0)

    def test_an_empty_value_with_no_default(self):
        with self.assertRaises(attack.UnreadableProfileError):
            attack.average("")

    def test_a_value_that_is_not_a_number_at_all(self):
        with self.assertRaises(attack.UnreadableProfileError):
            attack.average("lots")

    def test_a_target_number_off_the_dice_is_clamped(self):
        self.assertEqual(attack.chance(1), attack.chance(2))
        self.assertEqual(attack.chance(9), attack.chance(6))
        self.assertEqual(attack.chance(None), 0.0)

    def test_anti_keyword_improves_the_wound_roll(self):
        weapon = {
            "name": "w",
            "A": "1",
            "BS_WS": "3",
            "S": "3",
            "AP": "0",
            "D": "1",
            "profile": "ANTI-VEHICLE 2+",
        }
        target = {"T": "10", "Sv": "3+", "invulnerable": "", "W": "1"}
        without = attack.resolve(weapon, target)
        with_keyword = attack.resolve(weapon, target, target_keywords=("Vehicle",))
        self.assertEqual(without.wound_needed, 6)
        self.assertEqual(with_keyword.wound_needed, 2)

    def test_an_ability_with_no_effect_here_is_not_reported(self):
        result = attack.resolve(
            {
                "name": "w",
                "A": "1",
                "BS_WS": "3",
                "S": "4",
                "AP": "0",
                "D": "1",
                "profile": "Pistol, Assault",
            },
            {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"},
        )
        self.assertEqual(result.not_applied, [])

    def test_a_modelled_ability_that_changes_nothing_here(self):
        result = attack.resolve(
            {
                "name": "w",
                "A": "1",
                "BS_WS": "3",
                "S": "4",
                "AP": "0",
                "D": "1",
                "profile": "PSYCHIC",
            },
            {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"},
        )
        self.assertEqual(result.not_applied, [])

    def test_abilities_read_from_description_when_there_is_no_profile(self):
        result = attack.resolve(
            {
                "name": "w",
                "A": "1",
                "BS_WS": "3",
                "S": "4",
                "AP": "0",
                "D": "1",
                "description": "CLEAVE 2",
            },
            {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"},
        )
        self.assertEqual(result.not_applied, ["CLEAVE 2"])

    def test_a_conditional_sustained_hits_is_not_applied(self):
        profile = {"name": "w", "A": "6", "BS_WS": "3", "S": "4", "AP": "0", "D": "1"}
        target = {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"}
        conditional = attack.resolve(
            {**profile, "profile": "SUSTAINED HITS 1: non-VEHICLE"}, target
        )
        plain = attack.resolve(profile, target)
        self.assertEqual(conditional.expected_hits, plain.expected_hits)
        self.assertTrue(conditional.not_applied)


class TestQueryEdges(CreedTestCase):
    def test_a_datasheet_id_that_is_not_there(self):
        with db.session() as connection:
            self.assertIsNone(datasheets.get(connection, "NOPE"))

    def test_an_empty_search(self):
        with db.session() as connection:
            result = datasheets.search(connection, "   ")
        self.assertEqual(result.total, 0)
        self.assertFalse(result.truncated)

    def test_a_datasheet_with_no_role_keyword(self):
        self.assertEqual(datasheets.role_from_keywords(["Smoke", "Grenades"]), "")

    def test_the_most_specific_role_wins(self):
        self.assertEqual(
            datasheets.role_from_keywords(["Infantry", "Character"]), "Character"
        )

    def test_a_stratagem_with_no_turn_is_usable_in_either(self):
        with db.session() as connection:
            core = rules.stratagems(connection, name="COMMAND RE-ROLL")[0]
        self.assertTrue(core.either_turn)

    def test_an_ability_search_matching_nothing(self):
        with db.session() as connection:
            self.assertEqual(rules.abilities(connection, "Nothing"), [])

    def test_enhancements_filtered_by_faction(self):
        with db.session() as connection:
            found = rules.enhancements(connection, faction="TG")
        self.assertEqual(len(found), 2)

    def test_a_stratagem_whose_cp_is_not_a_number(self):
        with db.session() as connection:
            connection.execute("UPDATE Stratagems SET cp_cost = '' WHERE id = 'ST1'")
            found = rules.stratagems(connection, name="BRACE")
        self.assertIsNone(found[0].cp)
        # A stratagem with no printed cost still matches a CP filter, because
        # excluding it would hide it exactly when somebody is short of CP.
        with db.session() as connection:
            self.assertTrue(rules.stratagems(connection, name="BRACE", max_cp=0))

    def test_a_detachment_id_that_is_not_there(self):
        with db.session() as connection:
            self.assertIsNone(detachments.get(connection, "NOPE"))
            self.assertEqual(detachments.contents(connection, "NOPE"), {})

    def test_a_detachment_with_no_ability(self):
        with db.session() as connection:
            connection.execute("DELETE FROM Detachment_abilities")
            found = detachments.by_name(connection, "Shield Doctrine")[0]
        self.assertIsNone(found.ability)

    def test_a_detachment_whose_points_are_not_a_number(self):
        with db.session() as connection:
            connection.execute("UPDATE Detachments SET dp = '' WHERE id = 'DT1'")
            found = detachments.by_name(connection, "Shield Doctrine")[0]
        self.assertIsNone(found.dp)

    def test_a_chapter_override_that_is_not_a_number_is_ignored(self):
        with db.session() as connection:
            connection.execute("UPDATE Detachments_chapter_dp SET dp = 'x'")
            found = detachments.by_name(connection, "Spear Doctrine")[0]
        self.assertFalse(found.dp_varies)


class TestValidateEdges(CreedTestCase):
    def _list(self, points=2000):
        with db.session() as connection:
            return army.create(connection, "checks", "Test Guard", points)

    def test_a_unit_at_a_size_with_no_price(self):
        list_id = self._list()
        with db.session() as connection:
            army.set_detachment(connection, list_id, "DT1")
            unit_id = army.add_unit(connection, list_id, "D1", 5)
            connection.execute(
                "UPDATE list_units SET models = 7 WHERE id = ?", (unit_id,)
            )
            report = validate.check(connection, list_id)
        self.assertTrue(any("no price" in f.problem for f in report.findings))

    def test_a_datasheet_that_left_the_export(self):
        list_id = self._list()
        with db.session() as connection:
            army.set_detachment(connection, list_id, "DT1")
            army.add_unit(connection, list_id, "D1", 5)
            connection.execute("DELETE FROM Datasheets WHERE id = 'D1'")
            report = validate.check(connection, list_id)
        self.assertTrue(
            any("no longer in the export" in f.problem for f in report.findings)
        )

    def test_a_leader_attached_to_something_it_can_lead(self):
        list_id = self._list()
        with db.session() as connection:
            army.set_detachment(connection, list_id, "DT1")
            leader = army.add_unit(connection, list_id, "D2")
            target = army.add_unit(connection, list_id, "D1", 5)
            army.attach(connection, leader, target)
            report = validate.check(connection, list_id)
        self.assertFalse(any("cannot lead" in f.problem for f in report.findings))

    def test_a_datasheet_that_can_lead_nothing_at_all(self):
        list_id = self._list()
        with db.session() as connection:
            army.set_detachment(connection, list_id, "DT1")
            connection.execute("DELETE FROM Datasheets_leader")
            leader = army.add_unit(connection, list_id, "D2")
            target = army.add_unit(connection, list_id, "D1", 5)
            army.attach(connection, leader, target)
            report = validate.check(connection, list_id)
        self.assertTrue(any("cannot lead anything" in f.fix for f in report.findings))

    def test_a_report_with_nothing_wrong_does_not_pass_as_legal(self):
        list_id = self._list()
        with db.session() as connection:
            army.set_detachment(connection, list_id, "DT1")
            army.add_unit(connection, list_id, "D1", 5)
            report = validate.check(connection, list_id)
        self.assertTrue(report.passed)
        self.assertIn("not the same as the list being legal", report.summary())

    def test_an_empty_list_does_not_pass(self):
        list_id = self._list()
        with db.session() as connection:
            report = validate.check(connection, list_id)
        self.assertFalse(report.passed)
        self.assertIn("nothing to check", report.summary())

    def test_the_summary_counts_the_problems(self):
        list_id = self._list(points=10)
        with db.session() as connection:
            army.add_unit(connection, list_id, "D1", 5)
            report = validate.check(connection, list_id)
        self.assertIn("problem(s) found", report.summary())

    def test_eligibility_prose_is_shown_and_not_decided(self):
        list_id = self._list()
        with db.session() as connection:
            army.set_detachment(connection, list_id, "DT1")
            unit_id = army.add_unit(connection, list_id, "D2")
            army.set_enhancement(connection, unit_id, "EN1")
            report = validate.check(connection, list_id)
        self.assertTrue(any("has not checked" in line for line in report.unverified))

    def test_a_sentence_with_no_full_stop(self):
        self.assertEqual(
            validate._first_sentence("no full stop here"), "no full stop here"
        )


class TestRender(CreedTestCase):
    def _provenance(self):
        with db.session() as connection:
            return answers.provenance(connection)

    def test_a_virtual_datasheet_says_so(self):
        with db.session() as connection:
            sheet = datasheets.get(connection, "D4")
        rendered = render.datasheet(sheet, self._provenance())
        self.assertIn("cannot be taken in an army list", rendered)

    def test_a_datasheet_with_no_points_at_all(self):
        self.assertIn("no points", render.points_block(pricing.Pricing()))

    def test_points_with_a_variant_and_a_note(self):
        parsed = pricing.parse(
            [
                {"line": "1", "description": '<div class="x">Agent</div>', "cost": ""},
                {"line": "2", "description": "YOUR UNIT COSTS", "cost": ""},
                {"line": "3", "description": "1 model", "cost": "100"},
                {"line": "4", "description": "WARGEAR COSTS REMOVED", "cost": ""},
            ]
        )
        rendered = render.points_block(parsed)
        self.assertIn("_Agent_", rendered)
        self.assertIn("WARGEAR COSTS REMOVED", rendered)

    def test_a_warning_rides_along_with_the_answer(self):
        provenance = self._provenance()
        provenance.warnings.append("this data is old")
        self.assertIn("this data is old", render.provenance_block(provenance))

    def test_a_search_that_matched_nothing(self):
        with db.session() as connection:
            result = datasheets.search(connection, "Breakfast Cereal")
        self.assertIn(
            "Nothing matched", render.search_results(result, self._provenance())
        )

    def test_a_truncated_search_says_how_to_narrow_it(self):
        with (
            unittest.mock.patch.object(datasheets, "SEARCH_LIMIT", 1),
            db.session() as connection,
        ):
            result = datasheets.search(connection, "Testudo")
        rendered = render.search_results(result, self._provenance())
        self.assertIn("Narrow it", rendered)

    def test_no_stratagems(self):
        self.assertIn("No stratagems", render.stratagems([], self._provenance()))

    def test_a_list_with_wargear_an_enhancement_and_a_missing_datasheet(self):
        with db.session() as connection:
            list_id = army.create(connection, "rendered", "Test Guard", 2000)
            unit = army.add_unit(connection, list_id, "D1", 5)
            army.add_wargear(connection, unit, "per Test flail", 2)
            character = army.add_unit(connection, list_id, "D2")
            army.set_enhancement(connection, character, "EN1")
            army.set_detachment(connection, list_id, "DT1")
            priced = army.price(connection, list_id)
        rendered = render.army_list(priced, self._provenance())
        self.assertIn("Test flail", rendered)
        self.assertIn("Enhancement", rendered)
        self.assertIn("points remain", rendered)

    def test_a_list_over_its_limit(self):
        with db.session() as connection:
            list_id = army.create(connection, "over", "Test Guard", 10)
            army.add_unit(connection, list_id, "D1", 5)
            priced = army.price(connection, list_id)
        self.assertIn("Over by", render.army_list(priced, self._provenance()))

    def test_a_list_with_no_detachment(self):
        with db.session() as connection:
            list_id = army.create(connection, "bare", "Test Guard", 2000)
            priced = army.price(connection, list_id)
        self.assertIn("none chosen", render.army_list(priced, self._provenance()))

    def test_an_attack_with_a_note_and_an_unapplied_ability(self):
        result = attack.resolve(
            {
                "name": "w",
                "A": "1",
                "BS_WS": "3",
                "S": "8",
                "AP": "-4",
                "D": "3",
                "profile": "CLEAVE 2",
            },
            {"T": "4", "Sv": "6+", "invulnerable": "", "W": "1"},
            attacker="A",
            target="B",
        )
        rendered = render.attack_result(result, self._provenance())
        self.assertIn("Not applied", rendered)
        self.assertIn("excess is lost", rendered)

    def test_a_detachment_with_no_ability_and_no_contents(self):
        with db.session() as connection:
            found = detachments.by_name(connection, "Alien Doctrine")[0]
        rendered = render.detachment(found, {}, self._provenance())
        self.assertIn("Alien Doctrine", rendered)


class TestLastBranches(CreedTestCase):
    """The branches nothing else happens to walk."""

    def _provenance(self):
        with db.session() as connection:
            return answers.provenance(connection)

    def test_a_naive_timestamp_is_read_as_utc(self):
        naive = (datetime.now(UTC) - timedelta(days=30)).replace(tzinfo=None)
        with db.session() as connection:
            db.set_state(connection, sync.LAST_CHECKED_KEY, naive.isoformat())
        with db.session() as connection:
            self.assertTrue(answers.provenance(connection).warnings)

    def test_chapter_points_for_a_chapter_that_is_not_listed(self):
        with db.session() as connection:
            found = detachments.by_name(connection, "Spear Doctrine")[0]
        self.assertEqual(found.dp_for("Third Company"), found.dp)
        self.assertEqual(found.dp_for("first company"), 4)

    def test_a_tier_does_not_cover_an_ordinal_below_it(self):
        tier = pricing.Tier(first=3, last=None)
        self.assertFalse(tier.covers(2))
        self.assertTrue(tier.covers(3))
        self.assertTrue(tier.covers(99))

    def test_a_wargear_row_with_no_section_header_at_all(self):
        parsed = pricing.parse([{"line": "1", "description": "1 model", "cost": "10"}])
        self.assertEqual(len(parsed.variants), 1)
        self.assertEqual(parsed.cost_for(1), 10)

    def test_stratagems_filtered_by_faction(self):
        with db.session() as connection:
            found = rules.stratagems(connection, faction="TG")
        names = {stratagem.name for stratagem in found}
        self.assertIn("BRACE", names)
        # The core stratagem has no faction, so it is available to everyone.
        self.assertIn("COMMAND RE-ROLL", names)

    def test_a_table_that_comes_back_completely_empty(self):
        self.site.tables["Factions"] = ""
        self.site.set_last_update("2027-01-01 00:00:00")
        result = sync.sync()
        self.assertIn("empty", result.failed)

    def test_a_model_with_an_invulnerable_note(self):
        with db.session() as connection:
            connection.execute(
                "UPDATE Datasheets_models SET inv_sv_descr = "
                "'<b>Only against ranged attacks.</b>' WHERE datasheet_id = 'D1'"
            )
            sheet = datasheets.get(connection, "D1")
        rendered = render.datasheet(sheet, self._provenance())
        self.assertIn("Only against ranged attacks", rendered)

    def test_an_ability_with_a_parameter(self):
        with db.session() as connection:
            connection.execute(
                "UPDATE Datasheets_abilities SET parameter = '6+' WHERE line = '2'"
            )
            sheet = datasheets.get(connection, "D1")
        self.assertIn("Shield Wall 6+", render.datasheet(sheet, self._provenance()))

    def test_a_datasheet_with_nothing_optional_on_it(self):
        with db.session() as connection:
            for table in (
                "Datasheets_abilities",
                "Datasheets_keywords",
                "Datasheets_unit_composition",
                "Datasheets_wargear",
                "Datasheets_leader",
                "Datasheets_models_cost",
            ):
                connection.execute(f"DELETE FROM {table}")
            connection.execute("UPDATE Datasheets SET link = '' WHERE id = 'D1'")
            sheet = datasheets.get(connection, "D1")
        rendered = render.datasheet(sheet, self._provenance())
        self.assertNotIn("## Weapons", rendered)
        self.assertNotIn("## Abilities", rendered)
        self.assertNotIn("Keywords", rendered)
        self.assertIn("no points", rendered)

    def test_a_weapon_with_no_ability_line(self):
        with db.session() as connection:
            sheet = datasheets.get(connection, "D2")
        rendered = render.datasheet(sheet, self._provenance())
        self.assertIn("Test blade", rendered)

    def test_a_stratagem_with_neither_turn_nor_phase(self):
        with db.session() as connection:
            found = rules.stratagems(connection, name="COMMAND RE-ROLL")
        rendered = render.stratagems(found, self._provenance())
        self.assertIn("Core", rendered)

    def test_an_attack_whose_save_is_off_the_table(self):
        result = attack.resolve(
            {"name": "w", "A": "1", "BS_WS": "3", "S": "4", "AP": "-4", "D": "1"},
            {"T": "4", "Sv": "5+", "invulnerable": "", "W": "1"},
        )
        rendered = render.attack_result(result, self._provenance())
        self.assertIn("no save", rendered)

    def test_an_attack_with_neither_attacker_nor_target_named(self):
        result = attack.resolve(
            {"name": "w", "A": "1", "BS_WS": "3", "S": "4", "AP": "0", "D": "1"},
            {"T": "4", "Sv": "3+", "invulnerable": "", "W": "1"},
        )
        self.assertNotIn("into", render.attack_result(result, self._provenance()))

    def test_a_detachment_whose_points_do_not_vary_renders_no_chapter_line(self):
        with db.session() as connection:
            found = detachments.by_name(connection, "Shield Doctrine")[0]
            contents = detachments.contents(connection, found.id)
        rendered = render.detachment(found, contents, self._provenance())
        self.assertNotIn("differ by chapter", rendered)
        self.assertIn("Bulwark", rendered)

    def test_a_check_with_no_eligibility_prose_to_show(self):
        with db.session() as connection:
            connection.execute("UPDATE Enhancements SET description = ''")
            list_id = army.create(connection, "bare-enh", "Test Guard", 2000)
            army.set_detachment(connection, list_id, "DT1")
            unit = army.add_unit(connection, list_id, "D2")
            army.set_enhancement(connection, unit, "EN1")
            report = validate.check(connection, list_id)
        self.assertEqual(report.unverified, [])
        self.assertNotIn(
            "Shown but not decided", render.report(report, self._provenance())
        )


class TestFinalBranches(CreedTestCase):
    """The last few: each is a thing that renders differently when absent."""

    def _provenance(self):
        with db.session() as connection:
            return answers.provenance(connection)

    def test_an_ability_with_a_name_but_no_text(self):
        with db.session() as connection:
            connection.execute(
                "UPDATE Datasheets_abilities SET description = '' WHERE line = '2'"
            )
            sheet = datasheets.get(connection, "D1")
        rendered = render.datasheet(sheet, self._provenance())
        self.assertIn("Shield Wall", rendered)

    def test_a_detachment_with_no_points_and_no_disposition(self):
        with db.session() as connection:
            connection.execute(
                "UPDATE Detachments SET dp = '', force_disposition = '' "
                "WHERE id = 'DT1'"
            )
            found = detachments.by_name(connection, "Shield Doctrine")[0]
            contents = detachments.contents(connection, "DT1")
        rendered = render.detachment(found, contents, self._provenance())
        self.assertNotIn("Detachment Points", rendered)
        self.assertNotIn("Force Disposition", rendered)

    def test_an_enhancement_with_no_eligibility_wording(self):
        with db.session() as connection:
            connection.execute("UPDATE Enhancements SET description = ''")
            found = detachments.by_name(connection, "Shield Doctrine")[0]
            contents = detachments.contents(connection, "DT1")
        self.assertIn("Bulwark", render.detachment(found, contents, self._provenance()))

    def test_a_detachment_with_no_stratagems(self):
        with db.session() as connection:
            connection.execute("DELETE FROM Stratagems")
            found = detachments.by_name(connection, "Shield Doctrine")[0]
            contents = detachments.contents(connection, "DT1")
        rendered = render.detachment(found, contents, self._provenance())
        self.assertNotIn("## Stratagems", rendered)

    def test_a_lists_detachment_with_no_points(self):
        with db.session() as connection:
            connection.execute("UPDATE Detachments SET dp = '' WHERE id = 'DT1'")
            list_id = army.create(connection, "nodp", "Test Guard", 2000)
            army.set_detachment(connection, list_id, "DT1")
            priced = army.price(connection, list_id)
        rendered = render.army_list(priced, self._provenance())
        self.assertIn("Shield Doctrine", rendered)
        self.assertNotIn("DP)", rendered)

    def test_a_lists_detachment_with_points_but_no_disposition(self):
        with db.session() as connection:
            connection.execute(
                "UPDATE Detachments SET force_disposition = '' WHERE id = 'DT1'"
            )
            list_id = army.create(connection, "nodisp", "Test Guard", 2000)
            army.set_detachment(connection, list_id, "DT1")
            priced = army.price(connection, list_id)
        self.assertIn("(2 DP)", render.army_list(priced, self._provenance()))

    def test_a_unit_with_no_price_renders_a_question_mark(self):
        with db.session() as connection:
            list_id = army.create(connection, "unpriced", "Test Guard", 2000)
            unit = army.add_unit(connection, list_id, "D1", 5)
            connection.execute("UPDATE list_units SET models = 7 WHERE id = ?", (unit,))
            priced = army.price(connection, list_id)
        self.assertIn("?pts", render.army_list(priced, self._provenance()))

    def test_a_report_with_a_finding_that_names_no_unit(self):
        with db.session() as connection:
            list_id = army.create(connection, "nodetach", "Test Guard", 2000)
            army.add_unit(connection, list_id, "D1", 5)
            report = validate.check(connection, list_id)
        rendered = render.report(report, self._provenance())
        self.assertIn("no detachment has been chosen", rendered)

    def test_an_attack_with_nothing_applied_and_nothing_skipped(self):
        result = attack.resolve(
            {"name": "w", "A": "1", "BS_WS": "3", "S": "4", "AP": "0", "D": "1"},
            {"T": "4", "Sv": "3+", "invulnerable": "", "W": "2"},
        )
        rendered = render.attack_result(result, self._provenance())
        self.assertNotIn("Applied:", rendered)
        self.assertNotIn("Not applied", rendered)


class TestRemainingBranches(CreedTestCase):
    def test_a_fetcher_handed_a_client_does_not_close_it(self):
        import httpx

        client = httpx.Client()
        with fetch.Fetcher(client) as fetcher:
            fetcher.get(export.TABLES_BY_NAME["Factions"], fetch.Validators())
        # Still open, because the fetcher did not own it.
        self.assertFalse(client.is_closed)
        client.close()

    def test_a_conditional_get_with_only_a_last_modified(self):
        table = export.TABLES_BY_NAME["Factions"]
        with fetch.Fetcher() as fetcher:
            first = fetcher.get(table, fetch.Validators())
            again = fetcher.get(
                table, fetch.Validators(last_modified=first.last_modified)
            )
        self.assertTrue(first.changed)
        self.assertIsNotNone(again)

    def test_a_stratagem_search_with_no_phase_given(self):
        with db.session() as connection:
            self.assertTrue(rules.stratagems(connection))

    def test_a_duplicate_keyword_is_recorded_once(self):
        with db.session() as connection:
            connection.execute(
                "INSERT INTO Datasheets_keywords "
                "(datasheet_id, keyword, model, is_faction_keyword) "
                "VALUES ('D1', 'Infantry', '', 'false')"
            )
            sheet = datasheets.get(connection, "D1")
        self.assertEqual(sheet.keywords.count("Infantry"), 1)

    def test_an_empty_keyword_is_skipped(self):
        with db.session() as connection:
            connection.execute(
                "INSERT INTO Datasheets_keywords "
                "(datasheet_id, keyword, model, is_faction_keyword) "
                "VALUES ('D1', '', '', 'false')"
            )
            sheet = datasheets.get(connection, "D1")
        self.assertNotIn("", sheet.keywords)

    def test_by_name_skips_a_row_whose_datasheet_has_gone(self):
        with db.session() as connection:
            found = datasheets.by_name(connection, "Testudo Walker")
        self.assertEqual(len(found), 1)

    def test_a_first_sync_with_no_database_to_copy(self):
        # The staging copy is skipped when there is nothing to copy from,
        # which is every first run.
        paths.database_path().unlink()
        result = sync.sync(force=True)
        self.assertIsNone(result.failed)
        self.assertTrue(result.downloaded)


class TestLastSix(CreedTestCase):
    def _provenance(self):
        with db.session() as connection:
            return answers.provenance(connection)

    def test_a_list_rendering_a_datasheet_that_left_the_export(self):
        with db.session() as connection:
            list_id = army.create(connection, "ghost", "Test Guard", 2000)
            army.add_unit(connection, list_id, "D1", 5)
            connection.execute("DELETE FROM Datasheets WHERE id = 'D1'")
            priced = army.price(connection, list_id)
        rendered = render.army_list(priced, self._provenance())
        self.assertIn("no longer in the export", rendered)

    def test_a_report_rendering_the_wording_it_could_not_decide(self):
        with db.session() as connection:
            list_id = army.create(connection, "prose", "Test Guard", 2000)
            army.set_detachment(connection, list_id, "DT1")
            unit = army.add_unit(connection, list_id, "D2")
            army.set_enhancement(connection, unit, "EN1")
            report = validate.check(connection, list_id)
        rendered = render.report(report, self._provenance())
        self.assertIn("Shown but not decided", rendered)
        self.assertIn("creed cannot check them", rendered)

    def test_an_attack_rendering_what_it_applied(self):
        result = attack.resolve(
            {
                "name": "w",
                "A": "2",
                "BS_WS": "3",
                "S": "4",
                "AP": "0",
                "D": "1",
                "profile": "TWIN-LINKED",
            },
            {"T": "4", "Sv": "3+", "invulnerable": "", "W": "2"},
        )
        self.assertIn(
            "**Applied:** Twin-linked", render.attack_result(result, self._provenance())
        )

    def test_a_value_row_under_a_variant_with_no_tier_header(self):
        parsed = pricing.parse(
            [
                {"line": "1", "description": '<div class="x">Agent</div>', "cost": ""},
                {"line": "2", "description": "1 model", "cost": "90"},
            ]
        )
        self.assertEqual(parsed.variants[0].name, "Agent")
        self.assertEqual(parsed.cost_for(1), 90)


class TestEmptyReportRendering(CreedTestCase):
    def test_an_empty_list_renders_without_a_checked_section(self):
        with db.session() as connection:
            list_id = army.create(connection, "nothing", "Test Guard", 2000)
            report = validate.check(connection, list_id)
            provenance = answers.provenance(connection)
        rendered = render.report(report, provenance)
        self.assertNotIn("## Checked", rendered)
        self.assertIn("nothing to check", rendered)
        # The unchecked core rules are still named: an empty list is not a
        # list creed has approved of.
        self.assertIn("## Not checked", rendered)
