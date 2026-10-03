"""The play module split does not drift its public surface.

These tests exist so a refactor of ``gary_api/play.py`` into a package can be
mechanically verified: every caller and test that reached into the old module
must still find the same names on the same object.
"""

import unittest

from fastapi import APIRouter

from gary_api import play


class ModuleSurfaceTests(unittest.TestCase):
    """Backward-compatible imports from ``gary_api.play``."""

    def test_router_is_still_an_api_router(self):
        self.assertIsInstance(play.router, APIRouter)

    def test_opening_constant_is_exported(self):
        self.assertIsInstance(play.OPENING, str)
        self.assertIn("Gary", play.OPENING)

    def test_turn_routines_are_exported(self):
        self.assertTrue(callable(play.take_turn))
        self.assertTrue(callable(play.begin_campaign))

    def test_test_helpers_are_exported(self):
        # test_rules.py reaches into these; the split keeps them reachable.
        self.assertTrue(callable(play._run))
        self.assertTrue(callable(play._sheet_for))

    def test_schema_classes_are_exported(self):
        expected = {
            "ModuleResponse",
            "MethodResponse",
            "SystemResponse",
            "ModelResponse",
            "NewCampaign",
            "CampaignResponse",
            "ChangeCampaign",
            "NewCharacter",
            "CharacterResponse",
            "MemberResponse",
            "FoeResponse",
            "InOrder",
            "FightResponse",
            "WorldResponse",
            "EventResponse",
            "TurnResponse",
            "SceneResponse",
            "NewScene",
            "WantScores",
            "ScoreResponse",
            "ScoresResponse",
            "NewTurn",
        }
        missing = expected - set(dir(play))
        self.assertFalse(missing, f"missing schema exports: {missing}")

    def test_route_handlers_are_exported(self):
        handlers = {
            "read_catalogue",
            "read_system",
            "read_models",
            "start_campaign",
            "list_campaigns",
            "read_campaign",
            "change_campaign",
            "roll_scores",
            "add_character",
            "read_party",
            "take_over",
            "read_world",
            "read_transcript",
            "read_scenes",
            "begin_scene",
            "read_history",
            "take_turn",
            "begin_campaign",
        }
        missing = handlers - set(dir(play))
        self.assertFalse(missing, f"missing handler exports: {missing}")


class RouteTableTests(unittest.TestCase):
    """The router still advertises every route play always had."""

    def paths(self):
        """Return {(method, path)} for registered API routes."""
        result = set()
        for route in play.router.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    result.add((method, route.path))
        return result

    def test_all_expected_routes_are_present(self):
        expected = {
            ("GET", "/catalogue"),
            ("GET", "/catalogue/{slug}"),
            ("GET", "/models"),
            ("POST", "/campaigns"),
            ("GET", "/campaigns"),
            ("GET", "/campaigns/{campaign_id}"),
            ("PATCH", "/campaigns/{campaign_id}"),
            ("POST", "/campaigns/{campaign_id}/scores"),
            ("POST", "/campaigns/{campaign_id}/characters"),
            ("GET", "/campaigns/{campaign_id}/characters"),
            ("POST", "/campaigns/{campaign_id}/characters/{character_id}/player"),
            ("GET", "/campaigns/{campaign_id}/world"),
            ("GET", "/campaigns/{campaign_id}/turns"),
            ("GET", "/campaigns/{campaign_id}/scenes"),
            ("POST", "/campaigns/{campaign_id}/scenes"),
            ("GET", "/campaigns/{campaign_id}/history"),
            ("POST", "/campaigns/{campaign_id}/turns"),
            ("POST", "/campaigns/{campaign_id}/opening"),
        }
        self.assertTrue(expected.issubset(self.paths()))


if __name__ == "__main__":
    unittest.main()
