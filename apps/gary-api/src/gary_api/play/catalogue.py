"""Read-only catalogue of systems, modules, and runnable models."""

from fastapi import status

from gary_api import narration, systems
from gary_api.auth import Refusal
from gary_api.play.router import router
from gary_api.play.schemas import ModelResponse, SystemResponse

def _as_system(ruleset: systems.Ruleset) -> dict:
    return {
        "slug": ruleset.slug,
        "name": ruleset.name,
        "blurb": ruleset.blurb,
        "classes": list(ruleset.classes),
        "abilities": list(ruleset.abilities),
        "degrees": [degree.value for degree in ruleset.degrees],
        "methods": [
            {
                "slug": method.slug,
                "name": method.name,
                "blurb": method.blurb,
                "generates": method.generates,
                "arrange": method.arrange,
                "spends": method.spends,
            }
            for method in ruleset.methods
        ],
        "cannot_generate": ruleset.cannot_generate,
        "scores": list(ruleset.scores),
        "point_costs": ruleset.point_costs,
        "point_budget": ruleset.point_budget,
        "modules": [
            {
                "slug": module.slug,
                "title": module.title,
                "premise": module.premise,
                "hook": module.hook,
                "opening": module.opening,
            }
            for module in ruleset.modules
        ],
    }

@router.get("/catalogue")
async def read_catalogue() -> list[SystemResponse]:
    # No session: this is the menu, and what gary can play is the thing that
    # decides whether to make an account, not something an account unlocks.
    return [_as_system(ruleset) for ruleset in systems.rulesets()]


@router.get("/catalogue/{slug}")
async def read_system(slug: str) -> SystemResponse:
    try:
        return _as_system(systems.ruleset(slug))
    except systems.SystemError as error:
        raise Refusal(
            status.HTTP_404_NOT_FOUND, "no_such_system", str(error)
        ) from error


@router.get("/models")
async def read_models() -> list[ModelResponse]:
    # No session, like the catalogue: what gary can be run on is part of
    # deciding whether to make an account.
    return [
        {
            "id": model.id,
            "name": model.name,
            "prompt_cost": model.prompt_cost,
            "completion_cost": model.completion_cost,
            "context": model.context,
            "reasons": model.reasons,
            "suggested": model.suggested,
        }
        for model in narration.models.available()
    ]

