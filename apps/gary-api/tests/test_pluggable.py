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
