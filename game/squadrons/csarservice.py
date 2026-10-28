from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from dcs.mapping import Point
from shapely.geometry import LineString, Point as ShapelyPoint

from game.squadrons.csarplacement import find_downed_pilot_position
from game.squadrons.downedpilot import DownedPilot
from game.utils import nautical_miles

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.coalition import Coalition
    from game.game import Game
    from game.squadrons.pilot import Pilot
    from game.squadrons.squadron import Squadron
    from game.theater import ControlPoint
    from game.theater.player import Player

#: A downed pilot this close to a front line is treated as being in contested
#: territory and gets the shorter survival window.
_FRONT_LINE_DANGER = nautical_miles(30)

#: Fallback scatter radius (metres) when a loss has no DCS-reported position.
_FALLBACK_SCATTER_METERS = 5000.0


@dataclass(frozen=True)
class CapturedPilot:
    """A pilot taken prisoner this turn, for the debriefing report.

    Recorded rather than derived, because by the time the debrief is drawn the
    only trace on the pilot is a ``held_at`` id -- which says where they are, not
    that it happened this turn.
    """

    name: str
    aircraft: str
    squadron: str
    player: Player
    control_point: str


class CsarService:
    """Creates and resolves downed pilots for a game."""

    def __init__(self, game: Game) -> None:
        self.game = game

    def csar_enabled_for(self, player: Player) -> bool:
        settings = self.game.settings
        return settings.csar_enabled if player.is_blue else settings.csar_enabled_red

    def down_pilot(
        self,
        flight: Flight,
        pilot: Pilot,
        was_player: bool,
        position: Point,
    ) -> Optional[DownedPilot]:
        """Decides what becomes of the pilot of a lost aircraft.

        Returns the downed pilot if one was placed on the map, or None if their
        fate was settled here -- killed, captured, or walked home. Either way the
        pilot's own state is set before returning, so callers have nothing left to
        do.
        """
        squadron = flight.squadron
        player = squadron.player

        resolved = self._resolve_near_control_point(
            pilot, position, player, was_player, squadron
        )
        if resolved:
            return None

        if self._resolve_in_safe_zone(pilot, position, player, was_player):
            return None

        valid = find_downed_pilot_position(self.game.theater, position)
        if valid is None:
            # Nowhere survivable to put them.
            pilot.kill()
            return None

        downed = DownedPilot(
            pilot=pilot,
            squadron=squadron,
            _position=valid,
            player=player,
            turn_downed=self.game.turn,
            turns_remaining=self._survival_turns(valid, player),
            was_player=was_player,
            aircraft_name=squadron.aircraft.display_name,
            in_water=self.game.theater.is_in_sea(valid),
        )
        pilot.go_down()
        squadron.coalition.downed_pilots.append(downed)
        self.game.db.downed_pilots.add(downed.id, downed)
        logging.info(
            "%s from %s is down near %s; awaiting CSAR (%d turns).",
            pilot.name,
            squadron,
            valid,
            downed.turns_remaining,
        )
        return downed

    def _record_capture(
        self,
        name: str,
        aircraft: str,
        squadron: str,
        player: Player,
        control_point: str,
    ) -> None:
        self.game.pilots_captured_this_turn.append(
            CapturedPilot(
                name=name,
                aircraft=aircraft,
                squadron=squadron,
                player=player,
                control_point=control_point,
            )
        )

    def _resolve_near_control_point(
        self,
        pilot: Pilot,
        position: Point,
        player: Player,
        was_player: bool,
        squadron: Squadron,
    ) -> bool:
        """Settles a pilot who came down on top of a control point, if they did.

        Close enough to a base and there is nothing for a rescue flight to do: on
        friendly ground they walk back and go into recovery, on enemy ground they
        are captured. Returns whether the pilot was dealt with here.
        """
        radius = nautical_miles(self.game.settings.csar_control_point_radius)
        if radius.meters <= 0:
            return False

        nearest = self.game.theater.closest_control_point(position)
        if nearest.position.distance_to_point(position) > radius.meters:
            return False

        # They did come down, whatever happens next. Also what lets
        # take_prisoner() accept them: it only transitions a Downed pilot.
        pilot.go_down()
        if nearest.is_friendly(player):
            turns = (
                self.game.settings.csar_player_recovery_turns
                if was_player
                else self.game.settings.csar_ai_recovery_turns
            )
            pilot.begin_recovery(turns)
            self.game.message(
                "Pilot recovered",
                f"{pilot.name} came down inside friendly lines near {nearest.name}. "
                f"Recovered by Control Point. They return to duty in {turns} "
                f"turn(s).",
            )
        elif not self.game.settings.csar_prisoners_of_war:
            pilot.kill()
            self.game.message(
                "Pilot killed",
                f"{pilot.name} came down inside enemy lines near {nearest.name} "
                f"and did not survive.",
            )
        else:
            # Held by the base that took them, so retaking it brings them home.
            pilot.take_prisoner(held_at=nearest.id)
            self._record_capture(
                pilot.name,
                squadron.aircraft.display_name,
                str(squadron),
                player,
                nearest.name,
            )
            self.game.message(
                "Pilot captured",
                f"{pilot.name} came down inside enemy lines near {nearest.name} "
                f"and is now held there.",
            )
        return True

    def _resolve_in_safe_zone(
        self, pilot: Pilot, position: Point, player: Player, was_player: bool
    ) -> bool:
        """Recovers a pilot who came down in a safe zone, if the setting is on.

        Safe means on land over friendly territory, at least
        csar_safe_zone_threat_distance outside the enemy's threat zones and
        csar_safe_zone_front_line_distance from every front line. Friendly forces
        pick them up without a rescue flight, so they go straight into recovery
        and are back on duty from the next turn. Returns whether the pilot was
        dealt with here.
        """
        if not self.game.settings.csar_safe_zone_recovery:
            return False
        if not self.is_safe_zone(position, player):
            return False

        pilot.go_down()
        turns = (
            self.game.settings.csar_player_recovery_turns
            if was_player
            else self.game.settings.csar_ai_recovery_turns
        )
        pilot.begin_recovery(turns)
        self.game.message(
            "Pilot recovered",
            f"{pilot.name} came down in a safe zone and was picked up by friendly "
            f"forces. They return to duty in {turns} turn(s).",
        )
        return True

    def is_safe_zone(self, position: Point, player: Player) -> bool:
        """Whether a pilot of ``player`` coming down at ``position`` is safe."""
        settings = self.game.settings
        theater = self.game.theater

        if theater.is_in_sea(position):
            # Nobody walks home from the water: a ditched pilot needs a hoist.
            return False
        if not theater.closest_control_point(position).is_friendly(player):
            return False

        threats = self.game.threat_zone_for(player.opponent)
        if not threats.all.is_empty:
            if threats.threatened(position):
                return False
            min_threat = nautical_miles(settings.csar_safe_zone_threat_distance)
            if threats.distance_to_threat(position) < min_threat:
                return False

        min_front = nautical_miles(settings.csar_safe_zone_front_line_distance)
        here = ShapelyPoint(position.x, position.y)
        for front_line in theater.conflicts():
            points = [(p.x, p.y) for p in front_line.points]
            line = LineString(points) if len(points) > 1 else ShapelyPoint(points[0])
            if line.distance(here) < min_front.meters:
                return False
        return True

    def fallback_position_for(self, flight: Flight) -> Point:
        """A scattered position near the flight's target for losses with no
        DCS-reported position (AI kills, skipped/simulated turns)."""
        target = flight.package.target
        return target.position.random_point_within(_FALLBACK_SCATTER_METERS)

    def _survival_turns(self, position: Point, player: Player) -> int:
        settings = self.game.settings
        theater = self.game.theater

        nearest_cp = theater.closest_control_point(position)
        in_hostile_territory = not nearest_cp.is_friendly(player)

        near_front = False
        for front_line in theater.conflicts():
            if (
                front_line.position.distance_to_point(position)
                < _FRONT_LINE_DANGER.meters
            ):
                near_front = True
                break

        if in_hostile_territory or near_front:
            return settings.csar_survival_turns_hostile
        return settings.csar_survival_turns

    # Rescue resolution ------------------------------------------------------

    def rescue(self, downed: DownedPilot) -> None:
        """Removes a downed pilot from the map and puts them into recovery."""
        settings = self.game.settings
        turns = (
            settings.csar_player_recovery_turns
            if downed.was_player
            else settings.csar_ai_recovery_turns
        )
        downed.pilot.begin_recovery(turns)
        self._remove(downed)
        self.game.message(
            "Pilot rescued",
            f"{downed.pilot.name} ({downed.aircraft_name}) was recovered by CSAR "
            f"and will return to {downed.squadron} in {turns} turn(s).",
        )

    def expire(self, downed: DownedPilot) -> None:
        """Settles a downed pilot whose survival countdown ran out.

        Dead, unless prisoners are taken and an enemy base is close enough to
        hold them.
        """
        captor = (
            self._nearest_enemy_control_point(downed)
            if self.game.settings.csar_prisoners_of_war
            else None
        )
        self._remove(downed)
        if captor is not None:
            downed.pilot.take_prisoner(held_at=captor.id)
            self._record_capture(
                downed.pilot.name,
                downed.aircraft_name,
                str(downed.squadron),
                downed.player,
                captor.name,
            )
            self.game.message(
                "Pilot captured",
                f"{downed.pilot.name} ({downed.aircraft_name}) was never rescued and "
                f"is now held at {captor.name}. Taking it would bring them home.",
            )
        else:
            downed.pilot.kill()
            # Their sortie ended in an ejection, not a death: count it now.
            downed.pilot.record.credit_death()
            self.game.message(
                "Pilot killed",
                f"{downed.pilot.name} ({downed.aircraft_name}) was never rescued and "
                f"is now listed as dead.",
            )

    def _nearest_enemy_control_point(
        self, downed: DownedPilot
    ) -> Optional[ControlPoint]:
        """The enemy base that took this pilot prisoner, if any did.

        Two conditions, both required: they have to be in enemy-held territory
        (the nearest base is hostile) *and* within csar_capture_radius of it.
        Without the distance test an unrescued pilot was recorded as captured by
        whatever enemy base happened to be nearest, even one on the far side of
        the map.

        Its own setting rather than the landing radius that resolves a pilot when
        they first come down: anyone still on the map is by definition outside
        that one, so reusing it here would mean nobody is ever captured.

        Anyone else dies: nobody reached them either way.
        """
        radius = nautical_miles(self.game.settings.csar_capture_radius)
        if radius.meters <= 0:
            return None

        nearest = self.game.theater.closest_control_point(downed.position)
        if nearest.is_friendly(downed.player):
            return None
        if nearest.position.distance_to_point(downed.position) > radius.meters:
            return None
        return nearest

    def liberate_prisoners_at(self, control_point: ControlPoint) -> None:
        """Frees any pilots held at a control point that has just changed hands.

        Called for every capture, so it also has to check the base actually
        belongs to the prisoner's coalition now -- losing a base does not free the
        prisoners in it, and a base can be taken by the side already holding them.
        """
        for coalition in (self.game.blue, self.game.red):
            if not control_point.is_friendly(coalition.player):
                continue
            for squadron in coalition.air_wing.iter_squadrons():
                for pilot in list(squadron.prisoners_of_war):
                    if pilot.held_at != control_point.id:
                        continue
                    # Per pilot, not per coalition: whether a human flew them is
                    # what the two recovery settings distinguish, exactly as for a
                    # CSAR rescue. Keying off the coalition gave every blue pilot
                    # the (shorter) player figure.
                    turns = (
                        self.game.settings.csar_player_recovery_turns
                        if pilot.player
                        else self.game.settings.csar_ai_recovery_turns
                    )
                    if squadron.release_prisoner(pilot, turns):
                        outcome = f"returns to {squadron} in {turns} turn(s)"
                    else:
                        outcome = f"is on leave until {squadron} has a free slot"
                    self.game.message(
                        "Prisoner of war freed",
                        f"{pilot.name} was freed by the capture of "
                        f"{control_point.name} and {outcome}.",
                    )

    def _remove(self, downed: DownedPilot) -> None:
        coalition = downed.squadron.coalition
        if downed in coalition.downed_pilots:
            coalition.downed_pilots.remove(downed)
        try:
            self.game.db.downed_pilots.remove(downed.id)
        except KeyError:
            pass

    def advance_turn_for(self, coalition: Coalition) -> None:
        """Decrements a coalition's downed pilots' countdowns, expiring them.

        Called at coalition turn end. Iterates a copy since ``expire`` mutates the
        underlying list.

        A pilot who went down in the mission that just ended is not aged: that
        mission was no rescue opportunity. ``Game.finish_turn`` has already
        incremented the turn counter, so they are the ones downed on the
        previous turn. Without this, survival S gave only S - 1 rescue missions
        (#70); with it, ``turns_remaining`` is the number of rescue missions left.
        """
        just_ended = self.game.turn - 1
        for downed in list(coalition.downed_pilots):
            if downed.turn_downed >= just_ended:
                continue
            downed.turns_remaining -= 1
            if downed.turns_remaining <= 0:
                self.expire(downed)
