# Flight-plan non-regression harness (WEB-04.0, decision W16)

Locks what the engine plans before the package and flight editor moves to the web UI
(WEB-04.1 to 04.5): for the same input, waypoints, times and loadouts must not change.

```
python -m pytest tests/flightplans -q
```

It takes about 6 seconds. A failure prints a unified diff of the fingerprint JSON.

## How it works

1. `test_flightplan_fingerprints.py` starts `runner.py` in a child process with
   `PYTHONHASHSEED=0`.
2. `referencegame.py` generates the reference game through the engine, without Qt:
   `Campaign` -> `GameGenerator` -> `Game.begin_turn_0`, on `golan_heights_lite` with
   Israel 2000 against Syria 2011. Generating takes a few seconds, so no save is
   committed.
3. `scenarios.py` plans one blue package per scenario, through the commands of the web
   editor (`game/commands/packages.py`, `packageflights.py`).
4. `fingerprint.py` reduces each package to JSON. The test compares it with
   `tests/data/flightplans/<scenario>.json`.
5. The child also pickles the planned game. The test loads it to check that a save keeps
   the same fingerprints, and to check that moving a waypoint, shifting a time or
   changing a pylon does change the fingerprint.

| Scenario | Target | Flights |
| --- | --- | --- |
| `barcap` | Ramat David | BARCAP F-15C x2 |
| `cas` | Front line | CAS AH-1W x2 |
| `sead` | Closest enemy SAM | SEAD F-16CM x2 |
| `dead` | Second closest enemy SAM | DEAD F-4E x2, SEAD Escort F-16CM x2 |
| `strike_escort` | Closest enemy building | Strike F-15E x2, Escort F-15C x2 |
| `csar` | Blue pilot down near Golan South | CSAR UH-1H x1 |
| `auto_bai` | Enemy armor closest to the front | BAI x2, auto-created |

The fingerprint keeps, for each package, the target, primary task and TOT, and for each
flight the task, aircraft, squadron, bases, size, start type, flight plan class,
startup, takeoff, TOT and landing times, every waypoint (type, name, position to the
meter, altitude to the foot, altitude reference, TOT, departure time) and the loadout of
each member, pylon by pylon (CLSID). Times are the ones the Qt waypoint list shows; most
waypoints have none of their own.

## Refreshing the references

A diff means the engine now plans something different. If that is intended, refresh and
review the JSON diff in the PR:

```
# Git Bash
UPDATE_FLIGHTPLAN_FINGERPRINTS=1 python -m pytest tests/flightplans -q
# PowerShell
$env:UPDATE_FLIGHTPLAN_FINGERPRINTS = "1"; python -m pytest tests/flightplans -q; Remove-Item Env:UPDATE_FLIGHTPLAN_FINGERPRINTS
```

An editor migration (WEB-04.1 to 04.5) should not need a refresh: W16 requires identical
plans before and after.

## What the web commands reproduce

The references were produced with the engine calls of the Qt dialogs. WEB-04.1 moved
those sequences into commands, which Qt now shares, and the scenarios go through them
with the references untouched. A later lot (WEB-04.2 to 04.5) that adds a command does
the same.

| Command | Qt code it replaced | Engine sequence |
| --- | --- | --- |
| `create_package` | `QNewPackageDialog` | `Package(target, game.db.flights, auto_asap=True)`, added to the ATO at once (Qt: on save) |
| `auto_create` | `QAutoCreateDialog.on_create_clicked` | `PackageFulfiller.plan_mission(ProposedMission(..., asap=True), 1, now, tracer, ignore_range=True)`, then `set_tot_asap` |
| `add_flight` | `QFlightCreator.create_flight`, `QPackageDialog.add_flight` | `FlightRoster`, `Flight(...)` with `Settings.start_type_for`, `add_flight`, `recreate_flight_plan`, `set_tot_asap` |
| `default_loadout` | `QFlightCreator._init_loadout_selector` | First name from `Loadout.default_loadout_names_for` that exists, else the first loadout |
| `change_flight_squadron` | `QFlightSlotEditor._change_squadron` | New `Flight(...)` with `Loadout.default_for`, divert within 150 NM, `reassign_airlift`, `recreate_flight_plan`, old flight removed |
| `set_flight_divert` | `FlightPlanPropertiesGroup.set_divert` | `flight.divert = ...`, `recreate_flight_plan`, restored if planning fails |
| `resize_flight`, `set_flight_pilot`, `set_flight_slot_player` | `QFlightSlotEditor`, `QFlightStartType.on_pilot_selected`, `QGeneralFlightSettingsTab.on_player_toggle` | `Flight.resize` or `set_pilot`, laser codes, `Settings.start_type_for`, `set_tot_asap` |
| `set_member_custom`, `set_member_loadout`, `set_member_pylon` (WEB-04.3) | `QFlightPayloadTab`, `QPylonEditor` | Custom: `Loadout("Custom", ...)` from what the date restriction leaves, as the Qt combos did; off: `default_loadout`; a pylon: `equip_pylon`. An editor round trip gives back the reference loadout |

The route commands (`game/commands/flightroute.py`, WEB-04.4) are changes the player
asks for after planning, so no scenario goes through them. `recreate_route` keeps the
sequence of `QFlightWaypointTab.confirm_recreate`: `set_flight_type`, then
`recreate_flight_plan(dump_debug_info=True)`. `test_reading_a_route_changes_no_fingerprint`
checks that the read model of the Route tab leaves the plans alone.

## Determinism

- **RNGs:** `seed_all` seeds `random` and Faker (pilot names use its own generator)
  before generation and again before planning. numpy is only used at mission generation.
- **Hash seed:** faction units are sets of objects hashed by name, so their order follows
  `PYTHONHASHSEED`. It cannot be changed in a running process, hence the child process.
- **Payloads:** `repository_payloads_only` reads `resources/customized_payloads` only. The
  app also reads the DCS install, mods and saved games, which differ between machines.
  The child also points the saved games folder at a temp directory.
- **Address-based hashes:** these changed on every run, even with a fixed hash seed, so
  they were fixed in the engine: `GroundUnitType` and `ShipUnitType` now hash by
  `variant_id`, and `ForceGroup` dedupes with ordered dicts instead of sets.
  `test_engine_determinism.py` covers them.
- **Platform:** references were produced on Windows, like CI. Layouts and factions load
  in file-system order, and positions go through float maths, so another OS may differ.
