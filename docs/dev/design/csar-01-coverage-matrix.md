# CSAR-01 coverage matrix

Coverage of the CSAR-01 requirements (`specification-fonctionnelle.md` §3, epic #12) by the upstream PR `upstream#929` (Drexyl), taken over in #13. File references are to the branch of the #13 PR, after merging `dev`.

Status: **covered** = meets the requirement as written; **partial** = exists but deviates or is incomplete; **missing** = not implemented.

| # | Requirement | Status | Evidence | Gap / follow-up |
|---|---|---|---|---|
| 1 | Ejection recorded in `state.json`; aircraft lost, pilot not killed | covered | `resources/plugins/base/dcs_retribution.lua:325-358` (ejection, then landing position), `:119-120` (written to state); `game/debriefing.py:180-186`, `:225-242`, `:373-389` (side and pilot resolved from the unit map); `game/sim/missionresultsprocessor.py:176-190` | Side and pilot are resolved in Python, not written by Lua (equivalent). The landing refinement pairs events by order, not by unit name (`dcs_retribution.lua:342-356`): low risk. |
| 2 | Statuses MIA, then Rescued (rest N turns) or Dead; POW optional | partial | `game/squadrons/pilot.py:51-61` (Downed, Recovering, MissingInAction), `:139-150`; `game/squadrons/squadron.py:300-311` | No `Dead` outcome on expiry, and no POW status (MIA + `held_at`): #64 |
| 3 | Downed pilot on the map with countdown, shorter near front / enemy territory; keeps squadron slot while MIA | partial | `client/src/components/downedpilots/DownedPilot.tsx`, `game/server/downedpilots/models.py`; `game/squadrons/csarservice.py:188-206` | MIA pilot loses their slot (`squadron.py:393-399`): #63. Front proximity measured to a single point: #71. Countdown loses one turn: #70 |
| 4 | Ejection in a safe zone recovered automatically next turn (setting) | partial | `game/squadrons/csarservice.py:127-180`; `csar_control_point_radius` (`game/settings/settings.py:723-736`, default 15 nm, 0 disables) | Distance to a friendly control point only; no threat-zone or front-line test: #14 |
| 5 | CSAR mission for player and autoplanner, both sides; helicopters with `cabin_size > 0`; escorts CAP, SEAD, CAS; no helicopter into an active SAM zone; per-side per-turn cap | partial | `game/ato/flighttype.py:64`; `game/dcs/aircrafttype.py:686-702` (helicopter with a cabin); `game/commander/tasks/primitive/csar.py:13-47`; `game/commander/tasks/packageplanningtask.py:128-131`, `:188`; cap `max_csar_flights` (`settings.py:369`) | No CAS escort, CAP only via ESCORT: #65. The SAM check covers the pickup point only and is disabled at aggressiveness 100: #66 |
| 6 | Player slot with beacon, MAYDAY, F10 menu, smoke; landed or hoist pickup, hoist mandatory at sea | partial | `resources/plugins/opscsar/OpsCSAR.lua:258-288` (MOOSE Ops.CSAR registration: beacon, MAYDAY, F10), `:374-396` (smoke), `:182-185` (hover settings); `game/squadrons/downedpilot.py:85-91` | Hoist at sea is forced for AI flights only: #67 |
| 7 | Pilot dropped at a friendly base or FARP; event to `state.json`, mission status, debriefing, squadron window | partial | Player: MOOSE `OnAfterRescued` (`resources/plugins/base/Moose.lua:79255-79272`, `OpsCSAR.lua:232-242`). Pipeline: `game/sim/missionresultsprocessor.py:72-135`, `game/squadrons/csarservice.py:210-224`, `qt_ui/windows/QDebriefingWindow.py:79`, `qt_ui/windows/SquadronDialog.py:64` | AI rescues are credited at pickup, with false positives (vanish heuristic, simulated-flight fallback at `missionresultsprocessor.py:102-130`): #68 |
| 8 | Countdown expiry: Dead, or POW if enabled | partial | `game/squadrons/csarservice.py:226-276`; `csar_capture_radius` (`settings.py:738-755`) | Expiry gives MIA or capture, never Dead; capture is a radius, not an option: #64 |
| 9 | Player pilot: invulnerable setting kept; otherwise same rules | covered | `game/sim/missionresultsprocessor.py:169-170`; `game/squadrons/csarservice.py:213-217` | none |
| 10 | Settings: enable per side, ejection chance, survival, rest, hoisting, AI rescue, open door, start type, max CSAR per side | partial | `game/settings/settings.py:369`, `:696-819`, `:1140-1197` | All present, but "rescue AI pilots" has no effect: #69 |
| 11 | Optional bounty for a successful rescue | missing | none | #15 |

The follow-up issues were written before `dev` was merged into this branch, so some of their line numbers are a few lines off.

## Changes made in #13

- CSAR is disabled by default for both sides (`csar_enabled`, `csar_enabled_red`), as spec rule 1 requires; upstream enables it. Saves made before CSAR therefore load with CSAR off (`tests/test_csar_old_save.py`).
- After merging `dev`: `INGRESS_CSAR` and `CSAR_PICKUP` waypoint types are renumbered 37 and 38 (dev's `DECOY_RELEASE` holds 36), and the downed pilot map layers use the overlay constants and appear in the map legend.

## Other risks (no issue opened)

- `Migrator` sets CSAR settings with `try_set_attr` (`game/migrator.py:50-67`), but `Settings.__setstate__` has already merged the dataclass defaults (`game/settings/settings.py:1778`), so those calls are no-ops. Only `csar_hover_extraction` differs (the migrator intends False, old saves get True).
- Enemy downed pilots are sent to the client with a right-click CSAR action, but `DownedPilot.mission_types` returns nothing for them (`game/squadrons/downedpilot.py:122-128`): probably an empty dialog. Unverified.
- `csar_ejection_chance` help text lacks a space between sentences (`settings.py:710-721`).
