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
3. `scenarios.py` plans one blue package per scenario.
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

## What the web commands must reproduce

`POST /packages` only opens a Qt dialog today, so `scenarios.py` calls the engine
functions the Qt dialogs call. When a command replaces a dialog, change the scenario to
go through that command and keep the references untouched.

| Future command | Qt code it replaces | Engine sequence in `scenarios.py` |
| --- | --- | --- |
| WEB-04.1 create package | `QNewPackageDialog` | `Package(target, game.db.flights, auto_asap=True)`, then `ato.add_package` on save |
| WEB-04.1 auto-create | `QAutoCreateDialog.on_create_clicked` | `PackageFulfiller.plan_mission(ProposedMission(..., asap=True), 1, now, tracer, ignore_range=True)`, then `set_tot_asap` |
| WEB-04.2 add flight | `QFlightCreator.create_flight`, `QPackageDialog.add_flight` | `FlightRoster`, `Flight(...)` with `Settings.start_type_for`, `add_flight`, `recreate_flight_plan`, `set_tot_asap` |
| WEB-04.3 default loadout | `QFlightCreator._init_loadout_selector` | First name from `Loadout.default_loadout_names_for` that exists, else the first loadout |

`plan_manual` leaves out the player laser code step of `QFlightCreator.create_flight`
(no player pilot here, and the fingerprint has no laser code).

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
