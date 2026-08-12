"""Nothing outside gary_api.systems may know which system is running.

This is the rule that makes adding a system a one-file job, and it is exactly
the kind of rule that erodes one convenient ``if`` at a time — a special case
for 5e here, a Pathfinder-shaped branch there, and a year later adding a
system means grepping the whole app.

So it is enforced rather than asserted in a README. The check is deliberately
crude: if a registered slug appears in the source of any module outside the
package, something has learned a name it should not know.
"""

import pathlib
import unittest

from gary_api import systems

SOURCE = pathlib.Path(systems.__file__).parent.parent
ALLOWED = SOURCE / "systems"


def modules_outside_systems() -> list[pathlib.Path]:
    return [
        path
        for path in sorted(SOURCE.rglob("*.py"))
        if ALLOWED not in path.parents
    ]


class SystemsStayPluggable(unittest.TestCase):
    def test_no_module_outside_systems_names_a_system(self):
        slugs = [ruleset.slug for ruleset in systems.rulesets()]
        offences = []

        for path in modules_outside_systems():
            source = path.read_text()
            for number, line in enumerate(source.splitlines(), start=1):
                for slug in slugs:
                    if f'"{slug}"' in line or f"'{slug}'" in line:
                        offences.append(f"{path.name}:{number} names {slug!r}")

        self.assertEqual(
            offences,
            [],
            "these should ask the registry rather than name a system:\n"
            + "\n".join(offences),
        )

    def test_no_module_outside_systems_names_an_ability(self):
        # The subtler half of the same rule, and the one that actually
        # happened: nothing named a *system*, but the router spelled "con"
        # to work out hit points and "str" to work out an attack bonus. A
        # system whose vocabulary differs — or that has no constitution at
        # all — would then need this module changed to be added, which is
        # exactly what one file per system is supposed to prevent.
        names = {
            ability
            for ruleset in systems.rulesets()
            for ability in ruleset.abilities
        }
        offences = []

        for path in modules_outside_systems():
            for number, line in enumerate(path.read_text().splitlines(), start=1):
                for ability in names:
                    if f'"{ability}"' in line or f"'{ability}'" in line:
                        offences.append(f"{path.name}:{number} names {ability!r}")

        self.assertEqual(
            offences,
            [],
            "these should ask the ruleset rather than name an ability:\n"
            + "\n".join(offences),
        )

    def test_the_check_can_actually_fail(self):
        # A check that cannot fail is worse than no check. This proves the
        # scan reads the files it claims to.
        self.assertTrue(modules_outside_systems())
        self.assertIn("app.py", [path.name for path in modules_outside_systems()])

    def test_every_registered_system_is_complete(self):
        for ruleset in systems.rulesets():
            with self.subTest(ruleset.slug):
                self.assertTrue(ruleset.slug)
                self.assertTrue(ruleset.name)
                self.assertTrue(ruleset.blurb)
                self.assertTrue(ruleset.classes, "a system with no classes")
                self.assertTrue(ruleset.modules, "a system with nothing to play")
                self.assertTrue(ruleset.abilities)
                self.assertTrue(ruleset.degrees)
                # The briefing is what the model is told, so it names the
                # system the way a person would and not the way a URL does.
                self.assertIn(ruleset.name, ruleset.briefing())
                for degree in ruleset.degrees:
                    self.assertIn(degree.value, ruleset.briefing())

    def test_every_registered_system_makes_a_character(self):
        # Whatever it offers, it has to answer the two questions creating a
        # character asks — otherwise a new system is registered and then
        # discovered to be unplayable at the first party page.
        for ruleset in systems.rulesets():
            with self.subTest(ruleset.slug):
                self.assertTrue(ruleset.methods, "no way to make a character")
                self.assertIn(
                    "manual",
                    [method.slug for method in ruleset.methods],
                    "every system has to let scores be typed in",
                )
                if not any(method.generates for method in ruleset.methods):
                    self.assertTrue(
                        ruleset.cannot_generate,
                        "a system that generates nothing has to say why",
                    )

                sheet = {
                    ability: ruleset.default_score for ability in ruleset.abilities
                }
                for character_class in ruleset.classes:
                    self.assertGreaterEqual(
                        ruleset.hit_points(character_class, sheet), 1
                    )
                self.assertIsInstance(ruleset.attack_bonus(sheet), int)

                for method in ruleset.methods:
                    if not method.generates:
                        # Offered, and nothing for gary to produce: point buy
                        # is a budget you spend and typing them in is you.
                        with self.assertRaises(systems.SystemError):
                            ruleset.generate(method.slug)
                        continue
                    rolled = ruleset.generate(method.slug)
                    self.assertEqual(len(rolled), len(ruleset.abilities))
                    low, high = ruleset.scores
                    for one in rolled:
                        self.assertTrue(low <= one["score"] <= high, one)

    def test_every_registered_system_resolves_a_check(self):
        for ruleset in systems.rulesets():
            with self.subTest(ruleset.slug):
                outcome = ruleset.resolve(dc=10, modifier=2, reason="Perception")
                self.assertIn(outcome.degree, ruleset.degrees)
                self.assertEqual(outcome.dc, 10)
                self.assertEqual(outcome.reason, "Perception")

    def test_slugs_and_module_slugs_are_unique(self):
        slugs = [ruleset.slug for ruleset in systems.rulesets()]
        self.assertEqual(len(slugs), len(set(slugs)))

        for ruleset in systems.rulesets():
            with self.subTest(ruleset.slug):
                modules = [module.slug for module in ruleset.modules]
                self.assertEqual(len(modules), len(set(modules)))


if __name__ == "__main__":
    unittest.main()
