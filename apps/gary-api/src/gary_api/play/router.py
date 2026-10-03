"""The play router: assembles all endpoints under one tagged APIRouter."""

import uuid

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from gary_api import auth, scenes
from gary_api.models import Turn
from gary_api.play import campaigns, catalogue, world_read
from gary_api.play.campaigns import _mine, _party, _playable
from gary_api.play.engine import OPENING, _gary_for, _run, _stream
from gary_api.play.schemas import (
    CampaignResponse,
    CharacterResponse,
    EventResponse,
    ModelResponse,
    NewCampaign,
    NewCharacter,
    NewScene,
    NewTurn,
    SceneResponse,
    ScoresResponse,
    SystemResponse,
    TurnResponse,
    WantScores,
    WorldResponse,
)

router = APIRouter(tags=["play"])

# Catalogue
router.add_api_route(
    "/catalogue",
    catalogue.read_catalogue,
    methods=["GET"],
    response_model=list[SystemResponse],
)
router.add_api_route(
    "/catalogue/{slug}",
    catalogue.read_system,
    methods=["GET"],
    response_model=SystemResponse,
)
router.add_api_route(
    "/models",
    catalogue.read_models,
    methods=["GET"],
    response_model=list[ModelResponse],
)

# Campaigns and characters
router.add_api_route(
    "/campaigns",
    campaigns.start_campaign,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    response_model=CampaignResponse,
)
router.add_api_route(
    "/campaigns",
    campaigns.list_campaigns,
    methods=["GET"],
    response_model=list[CampaignResponse],
)
router.add_api_route(
    "/campaigns/{campaign_id}",
    campaigns.read_campaign,
    methods=["GET"],
    response_model=CampaignResponse,
)
router.add_api_route(
    "/campaigns/{campaign_id}",
    campaigns.change_campaign,
    methods=["PATCH"],
    response_model=CampaignResponse,
)
router.add_api_route(
    "/campaigns/{campaign_id}/scores",
    campaigns.roll_scores,
    methods=["POST"],
    response_model=ScoresResponse,
)
router.add_api_route(
    "/campaigns/{campaign_id}/characters",
    campaigns.add_character,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    response_model=CharacterResponse,
)
router.add_api_route(
    "/campaigns/{campaign_id}/characters",
    campaigns.read_party,
    methods=["GET"],
    response_model=list[CharacterResponse],
)
router.add_api_route(
    "/campaigns/{campaign_id}/characters/{character_id}/player",
    campaigns.take_over,
    methods=["POST"],
    response_model=list[CharacterResponse],
)

# World, transcript, scenes, history
router.add_api_route(
    "/campaigns/{campaign_id}/world",
    world_read.read_world,
    methods=["GET"],
    response_model=WorldResponse,
)
router.add_api_route(
    "/campaigns/{campaign_id}/turns",
    world_read.read_transcript,
    methods=["GET"],
    response_model=list[TurnResponse],
)
router.add_api_route(
    "/campaigns/{campaign_id}/scenes",
    world_read.read_scenes,
    methods=["GET"],
    response_model=list[SceneResponse],
)
router.add_api_route(
    "/campaigns/{campaign_id}/scenes",
    world_read.begin_scene,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    response_model=SceneResponse,
)
router.add_api_route(
    "/campaigns/{campaign_id}/history",
    world_read.read_history,
    methods=["GET"],
    response_model=list[EventResponse],
)


@router.post("/campaigns/{campaign_id}/turns")
async def take_turn(
    campaign_id: uuid.UUID, request: NewTurn, database: auth.Db, user: auth.CurrentUser
) -> StreamingResponse:
    """Say what you do, and have gary answer as it is generated.

    Everything that can be refused outright is refused here, before a byte is
    sent: no session, not your campaign, nothing said, nobody to play. Once
    the stream opens the status line is spent, so anything that goes wrong
    after that arrives as an event on it instead.
    """
    campaign = await _mine(database, user, campaign_id)

    party = await _party(database, campaign.id)
    _playable(party)

    gary = _gary_for(campaign)

    said = gary.sanitise(request.message) or request.message

    # A scene that has outgrown what may be sent every turn is broken here,
    # before the turn joins it, rather than after — so this turn starts the
    # new scene rather than being the straw that ended the old one. The bound
    # is applied whether or not gary ever asks for a break, which is the only
    # way a bound means anything.
    scene = await scenes.current(database, campaign.id)
    if await scenes.outgrown(database, scene):
        scene = await scenes.begin(database, campaign, party, _run)

    player_turn = Turn(
        campaign_id=campaign.id, scene_id=scene.id, role="player", content=said
    )
    database.add(player_turn)
    await database.commit()

    return StreamingResponse(
        _stream(campaign.id, scene.id, request.message, gary),
        media_type="text/event-stream",
        # Whatever sits in front of this must not collect the whole body
        # before passing it on, or streaming is a stream-shaped hole.
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


@router.post("/campaigns/{campaign_id}/opening")
async def begin_campaign(
    campaign_id: uuid.UUID, database: auth.Db, user: auth.CurrentUser
) -> StreamingResponse:
    """Have gary set the scene, once there is somebody to set it for.

    A campaign with a party and nothing said is a table where everyone has sat
    down and nobody has spoken. Somebody has to speak first, and it is not the
    player.
    """
    campaign = await _mine(database, user, campaign_id)

    party = await _party(database, campaign.id)
    _playable(party)

    said = await database.scalar(
        select(func.count()).select_from(Turn).where(Turn.campaign_id == campaign.id)
    )
    if said:
        # Refused here rather than left to the client to avoid, because a
        # reload and a second tab both reach this and neither knows about the
        # other. Two openings would be two beginnings, and the second narrated
        # to a table that had already started.
        raise auth.Refusal(
            status.HTTP_409_CONFLICT,
            "already_begun",
            "This campaign has already begun",
        )

    gary = _gary_for(campaign)

    scene = await scenes.current(database, campaign.id)
    await database.commit()

    return StreamingResponse(
        _stream(campaign.id, scene.id, OPENING, gary),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )
