"""Campaign and character endpoints, and the helpers they share."""

import uuid

from sqlalchemy import func, select

from gary_api import auth, logs, narration, systems, world
from gary_api.models import Campaign, Character, Turn
from gary_api.play.schemas import (
    CampaignResponse,
    ChangeCampaign,
    CharacterResponse,
    NewCampaign,
    NewCharacter,
    ScoresResponse,
    WantScores,
)

logger = logs.get_logger(__name__)


def _as_campaign(campaign: Campaign, turns: int = 0) -> dict:
    # The title is looked up rather than stored: it belongs to the module, and
    # a copy in the database is a copy that goes stale when the module is
    # reworded.
    module = systems.module(campaign.system_slug, campaign.module_slug)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "system": campaign.system_slug,
        "module": campaign.module_slug,
        "title": module.title,
        "premise": module.premise,
        "hook": module.hook,
        "place": module.opening,
        "turns": turns,
        "begun": turns > 0,
        "model": campaign.model or narration.models.default(),
        "model_chosen": campaign.model is not None,
    }


def _sheet_for(ruleset, wanted: dict[str, int] | None) -> dict[str, int]:
    """Six scores, checked against what this system has and allows.

    Nobody has to supply any: a campaign started before this existed has
    characters who never did, and not everybody wants to arrange six numbers
    before they can play. What is supplied has to be real.
    """
    sheet = {ability: ruleset.default_score for ability in ruleset.abilities}
    low, high = ruleset.scores

    for ability, score in (wanted or {}).items():
        if ability not in sheet:
            raise auth.Refusal(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "no_such_ability",
                f"{ability!r} is not an ability in this system",
            )
        if isinstance(score, bool):
            # Pydantic guarantees an int by here, and is happy to make one out
            # of a boolean: an ability sent as `true` arrives as a score of 1.
            # Only this half needs saying, because only this half gets through.
            raise auth.Refusal(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "bad_score",
                f"{score!r} is not a score",
            )
        if not low <= score <= high:
            raise auth.Refusal(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "bad_score",
                f"a score in this system is between {low} and {high}",
            )
        sheet[ability] = score

    return sheet


def _starting_experience(ruleset, level: int) -> int:
    """What that level costs to reach, or nothing when the system cannot say.

    Nothing rather than a refusal: a system with no advancement table still
    makes characters, and add-1e refusing to price a level is not a reason to
    refuse to build one.
    """
    try:
        return ruleset.experience_for(level)
    except systems.SystemError:
        return 0


def _as_character(character: Character) -> dict:
    return {
        "id": character.id,
        "name": character.name,
        "character_class": character.character_class,
        "level": character.level,
        "experience": character.experience,
        "max_hp": character.max_hp,
        "abilities": character.abilities or {},
        "played_by": character.played_by,
    }


def _runnable(identifier: str | None) -> str | None:
    """Check a chosen model, or pass None straight through.

    The one rule: it has to be able to call tools. gary asks for a check and
    the rules grade it — a model that cannot call a tool would narrate a
    plausible game that nothing was adjudicating, which fails silently and is
    the worst kind available here.
    """
    if identifier is None:
        return None

    try:
        return narration.models.model(identifier).id
    except narration.models.ModelError as error:
        raise auth.Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unsupported_model", str(error)
        ) from error


async def _party(database, campaign_id: uuid.UUID) -> list[Character]:
    return list(
        await database.scalars(
            select(Character)
            .where(Character.campaign_id == campaign_id)
            .order_by(Character.created_at, Character.name)
        )
    )


def _playable(party: list[Character]) -> None:
    """Refuse a party there is nobody in for you to be.

    Two refusals rather than one, because they are two different problems and
    only one of them is fixed by making another character: an empty campaign
    needs anybody, a campaign of companions needs one of them to be you.
    """
    if not party:
        raise auth.Refusal(
            status.HTTP_409_CONFLICT,
            "no_party",
            "There is nobody in this campaign to play yet",
        )
    if not any(character.played_by == "player" for character in party):
        raise auth.Refusal(
            status.HTTP_409_CONFLICT,
            "no_character",
            "None of these characters is yours to play",
        )


async def _mine(database, user, campaign_id: uuid.UUID) -> Campaign:
    """The campaign, if it is yours. 404 if it is not, or is not there."""
    found = await database.get(Campaign, campaign_id)
    if found is None or found.user_id != user.id:
        raise auth.Refusal(
            status.HTTP_404_NOT_FOUND, "no_such_campaign", "No such campaign"
        )
    return found


async def start_campaign(
    request: NewCampaign, database: auth.Db, user: auth.CurrentUser
) -> CampaignResponse:
    try:
        module = systems.module(request.system, request.module)
    except systems.SystemError as error:
        # Which half was wrong matters to whoever is filling in the form: a
        # system gary does not run is a different mistake from a module that
        # belongs to a different system.
        known = any(
            ruleset.slug == request.system for ruleset in systems.rulesets()
        )
        raise auth.Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "no_such_module" if known else "no_such_system",
            str(error),
        ) from error

    campaign = Campaign(
        user_id=user.id,
        name=request.name,
        system_slug=request.system,
        module_slug=request.module,
        model=_runnable(request.model),
    )
    database.add(campaign)
    await database.flush()

    # The world starts where the module says it starts. Letting the model
    # choose would mean the first fact about the world came from the least
    # reliable thing in the system.
    await world.record(database, campaign.id, world.MOVED, {"place": module.opening})
    await database.commit()

    return _as_campaign(campaign)


async def list_campaigns(
    database: auth.Db, user: auth.CurrentUser
) -> list[CampaignResponse]:
    rows = list(
        await database.scalars(
            select(Campaign)
            .where(Campaign.user_id == user.id)
            .order_by(Campaign.created_at.desc())
        )
    )

    # Counted here rather than left at the default, which is what this did
    # before: every campaign in the list reported nought turns and none of
    # them had begun. One grouped query rather than one per campaign, because
    # this is the page signing in lands on.
    counted = dict(
        (
            await database.execute(
                select(Turn.campaign_id, func.count())
                .where(Turn.campaign_id.in_([campaign.id for campaign in rows]))
                .group_by(Turn.campaign_id)
            )
        ).all()
    ) if rows else {}

    return [
        _as_campaign(campaign, counted.get(campaign.id, 0)) for campaign in rows
    ]


async def read_campaign(
    campaign_id: uuid.UUID, database: auth.Db, user: auth.CurrentUser
) -> CampaignResponse:
    campaign = await _mine(database, user, campaign_id)
    turns = await database.scalar(
        select(func.count()).select_from(Turn).where(Turn.campaign_id == campaign.id)
    )
    return _as_campaign(campaign, turns or 0)


async def change_campaign(
    campaign_id: uuid.UUID,
    request: ChangeCampaign,
    database: auth.Db,
    user: auth.CurrentUser,
) -> CampaignResponse:
    """Move a campaign to another model, mid-game.

    Switching to something cheap while iterating and back for a session that
    matters is the whole reason the choice is exposed, so it cannot be a
    create-time decision.
    """
    campaign = await _mine(database, user, campaign_id)
    campaign.model = _runnable(request.model)
    await database.commit()

    turns = await database.scalar(
        select(func.count()).select_from(Turn).where(Turn.campaign_id == campaign.id)
    )
    return _as_campaign(campaign, turns or 0)


async def roll_scores(
    campaign_id: uuid.UUID, request: WantScores, database: auth.Db, user: auth.CurrentUser
) -> ScoresResponse:
    """Six scores, by a method this system offers.

    gary-api's dice and not the browser's, for the reason they are not the
    model's either: a number a client sent is a number somebody typed.

    Nothing is stored. A set nobody made a character out of is not a fact
    about the campaign, which is also why re-rolling is not refused — it costs
    nothing that matters, and refusing would only make people delete the
    character and start again.
    """
    campaign = await _mine(database, user, campaign_id)
    ruleset = systems.ruleset(campaign.system_slug)

    try:
        wanted = ruleset.method(request.method)
        thrown = ruleset.generate(request.method)
    except systems.SystemError as error:
        raise auth.Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "no_such_method", str(error)
        ) from error

    return {
        "method": wanted.slug,
        "scores": thrown,
        # Placed already, when the method does not let you arrange them —
        # three dice straight down the page is the whole of first edition's
        # character creation and there is nothing left to decide.
        "assigned": (
            None
            if wanted.arrange
            else dict(
                zip(ruleset.abilities, [one["score"] for one in thrown], strict=True)
            )
        ),
    }


async def add_character(
    campaign_id: uuid.UUID,
    request: NewCharacter,
    database: auth.Db,
    user: auth.CurrentUser,
) -> CharacterResponse:
    campaign = await _mine(database, user, campaign_id)

    try:
        # Asked of the system rather than checked against a list here, so a
        # warlock is fine in a game that has warlocks and refused in one that
        # does not — before play, rather than mid-scene.
        spelled = systems.character_class(
            campaign.system_slug, request.character_class
        )
    except systems.SystemError as error:
        raise auth.Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "no_such_class", str(error)
        ) from error

    if request.mine:
        already = await database.scalar(
            select(func.count())
            .select_from(Character)
            .where(
                Character.campaign_id == campaign.id,
                Character.played_by == "player",
            )
        )
        if already:
            # One is the whole idea. Two would put somebody back to playing
            # the party rather than a person in it — and take over is how you
            # change your mind, so this is not a state anybody needs.
            raise auth.Refusal(
                status.HTTP_409_CONFLICT,
                "already_playing",
                "You are already playing somebody in this campaign",
            )

    ruleset = systems.ruleset(campaign.system_slug)
    abilities = _sheet_for(ruleset, request.abilities)

    character = Character(
        campaign_id=campaign.id,
        name=request.name,
        character_class=spelled,
        level=request.level,
        # The class's hit die plus what their constitution is worth. Asked of
        # the ruleset rather than worked out here, because it is a rule — and
        # a system with no hit dice typed in yet says so by handing back its
        # own default rather than by being special-cased.
        max_hp=(
            request.max_hp
            if request.max_hp is not None
            else ruleset.hit_points(spelled, abilities)
        ),
        # Where that level starts, so being made at level 3 and earning your
        # way to 3 are the same character afterwards. A system that does not
        # price a level leaves this at nothing, which is what every character
        # made before any of this existed has.
        experience=_starting_experience(ruleset, request.level),
        abilities=abilities,
        played_by="player" if request.mine else "gary",
    )
    database.add(character)
    await database.commit()

    return _as_character(character)


async def read_party(
    campaign_id: uuid.UUID, database: auth.Db, user: auth.CurrentUser
) -> list[CharacterResponse]:
    campaign = await _mine(database, user, campaign_id)
    return [
        _as_character(character)
        for character in await _party(database, campaign.id)
    ]


async def take_over(
    campaign_id: uuid.UUID,
    character_id: uuid.UUID,
    database: auth.Db,
    user: auth.CurrentUser,
) -> list[CharacterResponse]:
    """Play this one instead, and hand whoever it was to gary.

    The whole party comes back rather than the one character, because two of
    them changed and a client that had to work out the other from an absence
    would sometimes get it wrong.
    """
    campaign = await _mine(database, user, campaign_id)
    party = await _party(database, campaign.id)

    wanted = next(
        (one for one in party if one.id == character_id),
        None,
    )
    if wanted is None:
        raise auth.Refusal(
            status.HTTP_404_NOT_FOUND,
            "no_such_character",
            "No such character in this campaign",
        )

    for character in party:
        character.played_by = "player" if character is wanted else "gary"
    await database.commit()

    return [_as_character(character) for character in party]
