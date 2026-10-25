# TRN-01.1: airlift delivery and player assignment (investigation)

Issue #28, epic #27 (TRN-01). Code state: `dev` @ `ed2c4764` plus the fixes made in the same PR (marked **fixed**). Line numbers refer to that state.

This note answers the three questions of #28 and gives the next agents a design for #29 (player-created Transport missions) and #30 (playable transfer-generated transport flights).

## 1. How an airlift works today

### Lifecycle

1. **Order.** A `TransferOrder` (`game/transfers.py:91`) is created by the player from the base menu (`qt_ui/windows/basemenu/NewUnitTransferDialog.py:310-332`, "Transfer Units" button in `QBaseMenu2.py:156-160`) or by the AI (`game/groundunitorders.py:111`). The dialog already has a "Requested transport type: Auto / Airlift" combo (`NewUnitTransferDialog.py:85-106`), which sets `request_airflift=True`.
2. **Registration.** `PendingTransfers.new_transfer` (`transfers.py:651`) removes the units from the origin base (`commit_losses`) and calls `arrange_transport` (`:632`). With a road or shipping link and no airlift request, a convoy or cargo ship is used; otherwise `AirliftPlanner(game, transfer, next_stop).create_package_for_airlift(now)` (`:271-392`). With `request_airflift`, `next_stop` is the final destination.
3. **Planning.** `create_package_for_airlift` (`:320`) walks the closest friendly airfields, takes squadrons from `air_wing.auto_assignable_for_task_at(FlightType.TRANSPORT, cp)` (`:329`), filters them with `compatible_with_mission` (`:287`), and creates one or more `TRANSPORT` flights in a new auto-ASAP package (`create_airlift_flight`, `:349`). Capacity is 1 vehicle per helicopter, 2 per plane (`:351`); a transfer larger than the flight is split (`split_transfer`, `:657`). Each flight gets `cargo=transfer`, and `transfer.transport = Airlift(transfer, flight, next_stop)` (`:242`, `:386-387`). If no squadron qualifies, the transfer stays pending with no transport ("No transports available") and is retried at the next turn start (`plan_transports`, `:742`, called from `Coalition.initialize_turn`, `game/coalition.py:190`).
4. **Flight plan.** `AirliftFlightPlan` (`game/ato/flightplans/airlift.py`) needs `flight.cargo` (raises `PlanningError` otherwise, `:130-134`). It adds cargo-stop waypoints when the pickup or drop-off differs from departure/arrival, and for helicopters `PICKUP_ZONE` / `DROPOFF_ZONE` waypoints flagged `only_for_player` (`:183-194`). Their positions come from `generate_random_ctld_point` (`_common_ctld.py:13`): a random point in one of the base's `ctld_zones`, or, when the base has none, a random point 200-2000 m from the base reference point.
5. **Mission generation.** With the CTLD plugin enabled, `FlightGroupConfigurator.configure` (`game/missiongenerator/aircraft/flightgroupconfigurator.py:104-117`) runs `LogisticsGenerator` for `TRANSPORT` and `AIR_ASSAULT` flights, passing the transfer found by `transfer_for_flight` (`transfers.py:865`). `LogisticsGenerator` (`logisticsgenerator.py`) creates the CTLD pickup and drop-off trigger zones (only when the flight has a client, for `only_for_player` waypoints), and for client airlifts **spawnable crates matching the transfer's units** (`:78-91`), optionally auto-spawned (CTLD option `airliftcrates`). `UnitMap.add_aircraft` (`game/unitmap.py:72-81`) registers each transport unit with its slice of the cargo (`add_airlift_units`, `:162-182`).
6. **Results.** `Debriefing.dead_ground_units` maps killed aircraft names to `AirliftUnits` (`debriefing.py:570-576`); `MissionResultsProcessor.commit_airlift_losses` (`game/sim/missionresultsprocessor.py:161-174`) calls `transfer.kill_unit` for each unit of that aircraft's slice.
7. **Delivery.** `Coalition.end_turn` calls `PendingTransfers.perform_transfers` (`coalition.py:164`, `transfers.py:725`). For each pending transfer `TransferOrder.proceed` (`:227`) moves it to `transport.destination` and, if that is the final destination, `disband_at` commissions the remaining units at the base (`:160-163`). Transfers whose next stop was captured are disbanded first (`disband_uncompletable_transfers`, `:754`); an `Airlift` has no escape route (`:258-262`), so its units die if the destination was lost.

## 2. Answers to #28

### Q1. When does an airlift deliver? What if the flight is not flown?

At **turn end, unconditionally**, as long as the transfer still has its `Airlift` transport and its units are not all dead. Nothing checks that the flight took off, landed, or unloaded with CTLD:

- A flight that never spawns (an empty client slot, a mission ended before take-off, a skipped turn via `pass_turn`) still delivers its cargo.
- CTLD unloading in DCS has no campaign effect: crates spawned for client airlifts are cosmetic; delivery is decided only by `perform_transfers`.
- If the flight is removed from the ATO (package deleted), `Package.remove_flight` clears `cargo.transport` (`game/ato/package.py:142-143`); `proceed` then does nothing and the transfer is re-planned at the next turn start, i.e. delivered one turn later.

So TRN-01 requirement 4 ("delivered next turn on success") is already true for any surviving flight. Making delivery depend on an actual landing/unload would be a new mechanic (rule 1: behind a setting) and needs DCS-side events (landing at destination or CTLD unload event written to `state.json`); not needed for #29/#30.

### Q2. Is cargo loss on shoot-down fully handled?

Mostly, with one gap that this PR **fixes**:

- **DCS kills:** handled per aircraft. A killed transport loses exactly its cargo slice (`unitmap.py:162-182`, `debriefing.py:570-576`, `missionresultsprocessor.py:161-174`). Death is any of unit-lost, kill, crash or dead events (`debriefing.py:188-205`), so crash and ejection count. `TransferOrder.kill_all` (`transfers.py:138`) is **not** used for airlifts (only for cargo ships, `missionresultsprocessor.py:158`); it is fine that way since losses are per aircraft.
- **Auto-resolved kills (gap, fixed):** a flight killed by the simulation (`Flight.kill`, `game/ato/flight.py:331`, from `game/sim/combat/*`) is only recorded in `SimulationResults.air_losses`; it is then not spawned (`aircraftgenerator.py:152`), so no DCS event reports its airlift units and the cargo used to be **delivered anyway**. `Debriefing.merge_simulation_results` (`debriefing.py:290`) now adds an `AirliftUnits` loss with the flight's whole cargo, once per flight. Test: `tests/test_airlift_losses.py`.
- **Partial cargo when the transfer is shared:** `add_airlift_units` slices `transfer.iter_units()` by `ceil(size / units)`; fine because each flight has its own (split) transfer.

### Q3. Can a player pilot be assigned to a transfer-generated transport flight?

**Yes, nothing blocks it** in the current code:

- The ATO flight editor's "Player" checkbox is enabled for any flyable aircraft, whatever the task (`qt_ui/windows/mission/flight/settings/QFlightSlotEditor.py:153-163`).
- Mission generation handles client transport flights: CTLD zones and crates are created only when `client_count > 0` (`logisticsgenerator.py:56-91`), helicopter pickup/drop-off waypoints are shown only to players (`airlift.py:193-194`), client ground spawns are preferred (`flightgroupspawner.py:200-289`).
- Losses and delivery do not depend on who flies (`UnitMap.add_aircraft` registers client units like AI units).

What gets in the way in practice:

1. **Changing the squadron of a transfer flight breaks it.** `QFlightSlotEditor._change_squadron` (`:340-360`) creates a new `Flight` with `cargo=self.flight.cargo`, then deletes the old one; `Package.remove_flight` sets `cargo.transport = None`. The transfer loses its `Airlift`: no delivery this turn, `transfer_for_flight` returns `None` (no crates), and re-planning a helicopter flight plan raises `RuntimeError("Could not generate CTLD dropoff")` (`airlift.py:265-269`). This is the main #30 fix.
2. **Squadron choice.** `AirliftPlanner` only uses squadrons auto-assignable to `TRANSPORT` (`transfers.py:329`). A squadron the player kept for themselves (TRANSPORT removed from auto-assignable tasks) is never picked, so the player cannot get a transfer flight on their own squadron. #29 solves it (explicit squadron choice).
3. **Timing.** The package is ASAP (`auto_asap=True`, `transfers.py:285`); the player must use the normal package TOT controls. Not a blocker.
4. **Helicopter range check bug (fixed).** `compatible_with_mission` measured the pickup-to-drop-off leg from the pickup to itself (`drop_off = self.transfer.position.position`), so helicopters were accepted for any distance. It now uses `self.next_stop.position` (`transfers.py:308`). Test: `tests/test_airlift_losses.py`.

## 3. Design for #29: player-created Transport missions

Requirements: Transport mission from a friendly base (base tab or map right-click): origin, destination, cargo (ground units in reserve) or troops; delivery next turn; shoot-down loses cargo; kneeboard shows pickup zone, drop zone, cargo and time slot. No CTLD crates (D13).

Key point: a Transport mission **is** an airlift transfer with a player-chosen squadron. Reuse `TransferOrder` + `Airlift` so delivery, losses, cancellation and persistence come for free.

### Proposed code path

1. **Domain: one entry point in `game/transfers.py`.**
   Add to `AirliftPlanner` (or a sibling function) a way to plan with an explicit squadron, bypassing auto-assignment:
   ```python
   def create_package_for_squadron(self, squadron: Squadron, now: datetime) -> Package
   ```
   It validates `squadron.aircraft.capable_of(FlightType.TRANSPORT)`, `compatible_with_mission(squadron.aircraft, squadron.location)` and available aircraft/pilots, then reuses `create_airlift_flight(squadron)`. Splitting stays as is; if one flight cannot carry everything, the rest is a separate transfer that the auto planner handles (or the dialog limits the cargo to the flight capacity, simpler). Add to `PendingTransfers`:
   ```python
   def new_player_airlift(self, transfer: TransferOrder, squadron: Squadron, now: datetime) -> Package
   ```
   doing `commit_losses` + append + planning, mirroring `new_transfer` (`:651`). This is the unit-testable seam for the automated criteria ("creates a flight with the cargo", "losing the flight kills the cargo": build the transfer, kill the flight through `Debriefing`/`MissionResultsProcessor` as in `tests/test_airlift_losses.py`).
2. **Mission type.** Add `FlightType.TRANSPORT` to `Airfield.mission_types` and `Fob.mission_types` when friendly (`controlpoint.py:1328-1348`, `:1747-1760`), gated in `QFlightTypeComboBox` (`qt_ui/widgets/combos/QFlightTypeComboBox.py:24-31`) like Air Assault (CTLD enabled for helicopters; fixed wing can land at the destination without CTLD). `tests/theater/test_controlpoint.py` and `test_mission_types_no_duplicates.py` pin the current lists and must be updated.
   - Caveat: the generic package dialog (`QFlightCreator.create_flight`, `qt_ui/windows/mission/flight/QFlightCreator.py:195-229`) builds a `Flight` without cargo, which fails in `AirliftFlightPlan` (`PlanningError`). Either special-case `TRANSPORT` in `QFlightCreator` to open the transport dialog, or (simpler) do not list TRANSPORT in the package dialog and offer a dedicated entry point (next item).
3. **UI entry points.**
   - Base tab: extend `NewUnitTransferDialog` (it already lists reserve units, `ScrollingUnitTransferGrid`, and has the Airlift option) with a squadron selector shown when "Airlift" is chosen, listing friendly squadrons capable of TRANSPORT that can operate at origin and destination (reuse `QSquadronSelector`-style filtering). Submitting calls `new_player_airlift`. Rename the button/title to "Transport mission" when a squadron is chosen.
   - Map right-click: `game/server/qt/routes.py:51-66` (`/create-package/control-point/{cp_id}`) opens the package dialog; add a sibling route (e.g. `/create-transport/control-point/{cp_id}`) wired through `QtCallbacks` (`game/server/dependencies.py:38-43`) that opens the same dialog, plus a client context-menu item. Client work requires `npm test`/`npm run build`.
   - "Troops": a Transport with no ground-unit cargo has no campaign effect. Options: (a) troops only for CTLD play (preload troops, no delivery), which needs `AirliftFlightPlan` to accept `cargo=None`; (b) defer. **Open question for the spec owner**; recommended: defer, ship cargo first.
4. **Kneeboard (requirement 3).** `KneeboardGenerator.generate_task_page` (`game/missiongenerator/kneeboard.py:886-891`) only has SEAD/DEAD and Strike pages. Add a `TransportTaskPage` for `FlightType.TRANSPORT` listing pickup zone and drop zone (names and coordinates from `LogisticsInfo` / the `PICKUP_ZONE` and `DROPOFF_ZONE` waypoints), cargo (`transfer.units`, display names and counts) and the time slot (package TOT / departure). `FlightData` must carry the cargo; add an optional field filled in `FlightGroupConfigurator.configure` from `transfer_for_flight`.
5. **CTLD crates.** D13 excludes crates as cargo. Today client airlifts already spawn crates matching the transfer (`logisticsgenerator.py:78-91`). Keep them as a visual aid only; delivery stays turn-based.

### Risks

- `QFlightSlotEditor._change_squadron` bug (above) also hits player-created transports; fix it in #30 first or together.
- `Package.remove_flight` clears `cargo.transport`; deleting a player transport package leaves the transfer pending and the auto planner will airlift it next turn with AI squadrons. Decide whether cancelling a player Transport should cancel the transfer (`PendingTransfers.cancel_transfer`, `:718`) instead; recommended yes for player-created ones, which requires knowing the origin of the transfer (add a `player_requested: bool` field, default False in `__setstate__`/class attribute for saves).
- Helicopter capacity is 1 vehicle per aircraft, which makes UH-1H transports of armour odd; keep, out of scope.
- Squadron `mission_types` (#21, merged) restrict auto-assignment; for an explicit player choice, offer squadrons where `squadron.capable_of(FlightType.TRANSPORT)` (`game/squadrons/squadron.py:349`), not `can_auto_assign`, so the player can use a squadron kept off auto-planning.

## 4. Design for #30: playable transfer-generated transport flights

Already possible (Q3). Remaining work:

1. **Fix `_change_squadron` for cargo flights** (`QFlightSlotEditor.py:340-360`): after replacing the flight, re-point the transport: `self.flight.cargo.transport = Airlift(cargo, new_flight, next_stop)` captured before deletion, or add a domain helper `PendingTransfers.reassign_airlift(old_flight, new_flight)` that is unit-testable. Also refuse squadrons that fail `AirliftPlanner.compatible_with_mission` or cannot operate at pickup/drop-off.
2. **Automated test** for the acceptance criterion: build a transfer + airlift flight via `AirliftPlanner.create_airlift_flight`, set `pilot.player = True` on a roster pilot, check `flight.client_count == 1`, `transfer_for_flight(flight) is transfer` and the flight plan still has its pickup/drop-off waypoints after `recreate_flight_plan()`.
3. **Manual check** (needs DCS): the flight is a client slot in the generated mission, CTLD zones and crates appear, delivery happens next turn.
4. Optional: let `AirliftPlanner` prefer squadrons with player pilots when the player requested the airlift. Not required.

## 5. Related: default CTLD zones (#31, this PR)

New CTLD plugin option **"Create default pickup/drop zones at bases without CTLD zones"** (`ctld.defaultzones`, off by default, rule 1). When on, each airfield and FOB/FARP without designer zones (`<name> CTLD`) gets generated zones at turn initialisation (`Game.update_default_ctld_zones`, `game/theater/ctldzones.py`): two zones of 250 m radius 750 m on each side of the main runway for airfields, two zones of 150 m radius 300 m north and south of FOBs, dropped when not on land. Designer zones are never touched; disabling the option removes generated zones. `ctld_zone_unavailable_reason(cp)` returns the warning text for ships, off-map spawns and bases with no dry land around; #29 should show it when a Transport mission cannot be offered at a base.
