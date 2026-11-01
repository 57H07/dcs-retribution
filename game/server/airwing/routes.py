"""Air wing screen (WEB-03). The rules are in `game.commands.squadrons`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from game import Game
from game.commands import (
    create_player_pilot,
    find_pilot,
    find_squadron,
    flight_type_named,
    livery_choices,
    rename_pilot,
    room_at_base,
    set_auto_assignable,
    set_pilot_on_leave,
    set_pilot_player,
    set_primary_task,
    set_squadron_livery,
    transfer_destinations,
    transfer_squadron,
)
from game.gamelock import locked
from game.squadrons import Pilot, Squadron
from game.theater.player import Player
from .models import (
    AirWingJs,
    AutoAssignJs,
    LiveryChoiceJs,
    NewPilotJs,
    PilotUpdateJs,
    PrimaryTaskJs,
    SetDestinationJs,
    SetLiveryJs,
    TransferDestinationJs,
    TransferOptionsJs,
)
from ..commanderrors import command_error_responses
from ..dependencies import GameContext, QtCallbacks, QtContext
from ..eventstream import EventStream

router: APIRouter = APIRouter()


def _squadron(game: Game, squadron_id: UUID) -> Squadron:
    squadron = find_squadron(game, squadron_id)
    if squadron is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no squadron with ID {squadron_id}",
        )
    return squadron


def _pilot(squadron: Squadron, pilot_id: UUID) -> Pilot:
    pilot = find_pilot(squadron, pilot_id)
    if pilot is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"{squadron.name} has no pilot with ID {pilot_id}",
        )
    return pilot


@router.get("/air-wing", operation_id="get_air_wing", response_model=AirWingJs | None)
@locked
def get_air_wing(
    enemy: bool = False, game: Game | None = Depends(GameContext.get)
) -> AirWingJs | None:
    """Squadrons by base, pilots and aircraft of a coalition; null without a campaign."""
    if game is None:
        return None
    return AirWingJs.for_coalition(game, Player.RED if enemy else Player.BLUE)


@router.put(
    "/squadrons/{squadron_id}/primary-task",
    operation_id="set_squadron_primary_task",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when the aircraft cannot fly this task"),
)
@locked
def put_primary_task(
    squadron_id: UUID,
    body: PrimaryTaskJs,
    game: Game = Depends(GameContext.require),
) -> None:
    set_primary_task(_squadron(game, squadron_id), flight_type_named(body.task))


@router.put(
    "/squadrons/{squadron_id}/auto-assign",
    operation_id="set_squadron_auto_assign",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when the aircraft cannot fly this task"),
)
@locked
def put_auto_assign(
    squadron_id: UUID,
    body: AutoAssignJs,
    game: Game = Depends(GameContext.require),
) -> None:
    set_auto_assignable(
        _squadron(game, squadron_id), flight_type_named(body.task), body.enabled
    )


@router.get(
    "/squadrons/{squadron_id}/liveries",
    operation_id="get_squadron_liveries",
    response_model=list[LiveryChoiceJs],
)
@locked
def get_liveries(
    squadron_id: UUID, game: Game = Depends(GameContext.require)
) -> list[LiveryChoiceJs]:
    choices = livery_choices(_squadron(game, squadron_id))
    return [LiveryChoiceJs.from_choice(choice) for choice in choices]


@router.put(
    "/squadrons/{squadron_id}/livery",
    operation_id="set_squadron_livery",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when the squadron cannot use this livery"),
)
@locked
def put_livery(
    squadron_id: UUID,
    body: SetLiveryJs,
    game: Game = Depends(GameContext.require),
) -> None:
    set_squadron_livery(
        _squadron(game, squadron_id), body.livery_id, body.use_livery_set
    )


@router.get(
    "/squadrons/{squadron_id}/destinations",
    operation_id="get_squadron_destinations",
    response_model=TransferOptionsJs,
)
@locked
def get_destinations(
    squadron_id: UUID, game: Game = Depends(GameContext.require)
) -> TransferOptionsJs:
    """Where the squadron can transfer. Costly: only asked when choosing."""
    squadron = _squadron(game, squadron_id)
    return TransferOptionsJs(
        room_here=room_at_base(squadron),
        destinations=[
            TransferDestinationJs.from_destination(squadron, destination)
            for destination in transfer_destinations(squadron)
        ],
    )


@router.put(
    "/squadrons/{squadron_id}/destination",
    operation_id="set_squadron_destination",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when there is no room at that base"),
)
@locked
def put_destination(
    squadron_id: UUID,
    body: SetDestinationJs,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks | None = Depends(QtContext.get_optional),
) -> None:
    """Orders or cancels a transfer: ferry flights join or leave the ATO."""
    squadron = _squadron(game, squadron_id)
    destination = None
    if body.destination_id is not None:
        try:
            destination = game.theater.find_control_point_by_id(body.destination_id)
        except KeyError:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"Game has no control point with ID {body.destination_id}",
            )
    now = GameContext.get_sim().current_time_in_sim
    with EventStream.event_context() as events:
        transfer_squadron(squadron, destination, now, events)
    if qt is not None and qt.packages_changed is not None:
        qt.packages_changed()


@router.post(
    "/squadrons/{squadron_id}/pilots",
    operation_id="create_player_pilot",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when the squadron is full or not flyable"),
)
@locked
def post_pilot(
    squadron_id: UUID,
    body: NewPilotJs,
    game: Game = Depends(GameContext.require),
) -> None:
    create_player_pilot(_squadron(game, squadron_id), body.name)


@router.patch(
    "/squadrons/{squadron_id}/pilots/{pilot_id}",
    operation_id="update_pilot",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=command_error_responses("when the pilot cannot change that way"),
)
@locked
def patch_pilot(
    squadron_id: UUID,
    pilot_id: UUID,
    body: PilotUpdateJs,
    game: Game = Depends(GameContext.require),
) -> None:
    squadron = _squadron(game, squadron_id)
    pilot = _pilot(squadron, pilot_id)
    with EventStream.event_context() as events:
        if body.player is not None:
            set_pilot_player(squadron, pilot, body.player, events)
        if body.on_leave is not None:
            set_pilot_on_leave(squadron, pilot, body.on_leave)
        if body.name is not None:
            rename_pilot(pilot, body.name)
