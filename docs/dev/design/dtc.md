# Native data cartridge (DTC) export (#191)

Research note written before coding, as #191 asks. Written in November 2026; recheck it
against a `.dtc` exported from a current DCS build before adding a module.

## What DCS accepts

| Module | Native DTC | Since | What the cartridge holds |
|---|---|---|---|
| F/A-18C | yes | 2.9.15.9408 | `COMM` (COMM1/COMM2, 20 named presets + G/M/C/S), `WYPT` (steerpoints, routes 1-3, TACAN/ICLS/ACLS pre-tune, FPAS home waypoint), `SA` (CAP points, corridor, FAOR/FLOT, MEZ threats), `TCN` (TACAN station list) |
| F-16C | yes | 2.9.15.9408 | `MPD` (steerpoints, GEO lines, threat and destination points), `COMM` (UHF/VHF, no channel names), `CMDS`, ROE/IFF, `COLR` |
| AH-64D | reported, not confirmed | later 2025 update | not researched |
| F-15E, JF-17, F-14 | no | | keep the kneeboard and the miz waypoints (`M{n}.{i}`, PP, ST/IP) |

Sources: ED changelog 2.9.15.9408 and news of 2025-04-11; the third-party generator
`KaiserHomeLab/dcs-mission-maker` (`app/dtc.py`); the draft upstream PR
`dcs-retribution/dcs-retribution#966`, whose author checked the schema against
`MissionEditor/modules/me_managerDTC.lua` and `CoreMods/aircraft/<type>/DTC`. ED does not
publish the schema.

## File format

- A cartridge is a JSON file `<name>.dtc`:
  `{"data": {...}, "name": <name>, "type": <DCS unit type>}`. `data` repeats `name`, `type`
  and `terrain` and holds one table per partition. A partition left out keeps the module's
  defaults.
- Inside a mission it is stored at `DTC/<name>.dtc` in the `.miz`, and each unit that uses
  it carries a `DTC` block in the mission's unit table:
  `{"Cartridges": {1: {"name": <name>, "default": true}}, "AutoLoad": true}`.
  With `AutoLoad`, the jet loads it at spawn; without it, the pilot loads it from the DTC
  page. The file travels with the mission, so multiplayer clients get it too.
- The DCS DTC manager keeps the player's own cartridges in `Saved Games\DCS\DTC`
  (unconfirmed by ED).

## What Retribution does

- **First module: F/A-18C.** Its schema is the richest and most regular, and its COMM
  presets have names, which the miz cannot carry. The F-16C comes in the next PR.
- **Partitions written:** `COMM` and `WYPT`. Frequencies and waypoints come from the same
  `FlightData` the mission uses: the unit's `Radio` presets and the flight's waypoints, so
  no value is computed twice. Steerpoint `n` is waypoint `n` of the kneeboard (the take-off
  point, number 0, is left out). `NAV_SETTINGS` pre-tunes the TACAN and ICLS of the
  recovery carrier, or else the TACAN of the departure or arrival field.
- **Not in the cartridge:** laser codes and the Link 16 datalink. The Hornet cartridge has
  no partition for them; Retribution already writes them in the unit properties of the
  miz. `SA` and `TCN` are left for later PRs.
- **Where it goes:** for each player flight of a supported module, the cartridge is
  embedded in the `.miz` and auto-loaded at spawn, and a copy is written next to the
  mission, in `retribution_nextturn_DTC\`. The Radios & TACAN tab of the flight saves that
  copy where the player wants (for example `Saved Games\DCS\DTC`).
- **Unsupported module or failure:** nothing is written and the mission is generated as
  before; the kneeboard stays the fallback.
