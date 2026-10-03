"""Characterisation tests for the play.py refactor.

These tests pin behaviour that must not drift when the single 1900-line
module is split into a package. They deliberately use the public
``gary_api.play`` surface and a few of the new submodules so the refactor
cannot accidentally break old imports or the new boundaries.
"""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status

from gary_api import narration, play
from gary_api.auth import Refusal


class Stub:
    """Just enough campaign/character for the engine-level tests."""

    system_slug = "dnd-5e"

    def __init__(self, name="Bramble"):
        self.id = uuid.uuid4()
        self.name = name


class _Fights:
    """Minimal database double for combat refusals that never touch a row."""

    async def scalars(self, *_args, **_kwargs):
        return []

    async def scalar(self, *_args, **_kwargs):
        return 0

    def add(self, *_args, **_kwargs):
        pass

    async def flush(self):
        pass


class RouteSurfaceTests(unittest.TestCase):
    """The public HTTP surface is unchanged by the split."""

    def test_all_routes_are_registered(self):
        paths = {(frozenset(route.methods), route.path) for route in play.router.routes}
        expected = {
            (frozenset({"GET"}), "/catalogue"),
            (frozenset({"GET"}), "/catalogue/{slug}"),
            (frozenset({"GET"}), "/models"),
            (frozenset({"POST"}), "/campaigns"),
            (frozenset({"GET"}), "/campaigns"),
            (frozenset({"GET"}), "/campaigns/{campaign_id}"),
            (frozenset({"PATCH"}), "/campaigns/{campaign_id}"),
            (frozenset({"POST"}), "/campaigns/{campaign_id}/scores"),
            (frozenset({"POST"}), "/campaigns/{campaign_id}/characters"),
            (frozenset({"GET"}), "/campaigns/{campaign_id}/characters"),
            (frozenset({"POST"}), "/campaigns/{campaign_id}/characters/{character_id}/player"),
            (frozenset({"GET"}), "/campaigns/{campaign_id}/world"),
            (frozenset({"GET"}), "/campaigns/{campaign_id}/turns"),
            (frozenset({"GET"}), "/campaigns/{campaign_id}/scenes"),
            (frozenset({"POST"}), "/campaigns/{campaign_id}/scenes"),
            (frozenset({"GET"}), "/campaigns/{campaign_id}/history"),
            (frozenset({"POST"}), "/campaigns/{campaign_id}/turns"),
            (frozenset({"POST"}), "/campaigns/{campaign_id}/opening"),
        }
        self.assertEqual(paths, expected)

    def test_router_keeps_its_tag(self):
        self.assertEqual(play.router.tags, ["play"])


class ImportSurfaceTests(unittest.TestCase):
    """Existing importers keep working after the split."""

    def test_play_re_exports_router(self):
        self.assertIsNotNone(play.router)

    def test_play_re_exports_run(self):
        self.assertTrue(callable(play._run))

    def test_play_re_exports_sheet_for(self):
        self.assertTrue(callable(play._sheet_for))

    def test_new_submodules_are_reachable(self):
        # If any of these imports fail, the package layout is wrong.
        from gary_api.play import schemas, catalogue, campaigns, world_read
        from gary_api.play import engine, router

        self.assertTrue(schemas.SystemResponse)
        self.assertTrue(callable(catalogue.read_catalogue))
        self.assertTrue(callable(campaigns.start_campaign))
        self.assertTrue(callable(world_read.read_world))
        self.assertTrue(callable(engine._run))
        self.assertTrue(router.router)


class RunToolTests(unittest.TestCase):
    """Tool dispatch behaviour cannot drift."""

    def run_call(self, name, arguments):
        who = Stub()
        return asyncio.run(
            play._run(
                _Fights(),
                Stub(),
                [who],
                narration.Call(name, arguments),
                uuid.uuid4(),
                uuid.uuid4(),
            )
        )

    def test_unknown_tool_is_refused(self):
        result, frames = self.run_call("summon_dragon", {})
        self.assertTrue(result.failed)
        self.assertIn("summon_dragon", result.summary)
        self.assertTrue(frames)

    def test_move_party_records_a_world_event(self):
        result, frames = self.run_call("move_party", {"place": "the belfry"})
        self.assertFalse(result.failed)
        self.assertIn("the belfry", result.summary)
        self.assertEqual(len(frames), 1)
        self.assertIn('"kind": "moved"', frames[0])
        self.assertIn('"place": "the belfry"', frames[0])

    def test_remember_records_a_world_event(self):
        result, frames = self.run_call("remember", {"key": "bell-rings", "value": "4"})
        self.assertFalse(result.failed)
        self.assertIn("bell-rings", result.summary)
        self.assertEqual(len(frames), 1)
        self.assertIn('"kind": "remembered"', frames[0])


class SheetTests(unittest.TestCase):
    """_sheet_for is part of the public test surface."""

    def test_sheet_for_defaults_every_ability(self):
        ruleset = next(iter(__import__("gary_api.systems", fromlist=["rulesets"]).rulesets()))
        sheet = play._sheet_for(ruleset, None)
        self.assertEqual(set(sheet), set(ruleset.abilities))
        self.assertEqual(set(sheet.values()), {ruleset.default_score})


class ModuleBoundaryTests(unittest.TestCase):
    """The split does not create import cycles or drop names."""

    def test_play_package_imports_cleanly(self):
        # Force a fresh import of the package would require reloading; instead
        # we simply assert the submodules we need are importable without an
        # ImportError, which the import statements above already proved.
        from gary_api.play import router as router_mod

        self.assertIs(router_mod.router, play.router)


if __name__ == "__main__":
    unittest.main()
