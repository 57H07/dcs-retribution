# Native data cartridge (DTC) export (#191)

Research note written before coding, as #191 asks. Written in November 2026; recheck it
against a `.dtc` exported from a current DCS build before adding a module.

## What DCS accepts

| Module | Native DTC | Since | What the cartridge holds |
|---|---|---|---|
| F/A-18C | yes | 2.9.15.9408 | `COMM` (COMM1/COMM2, 20 named presets + G/M/C/S), `WYPT` (steerpoints, routes 1-3, TACAN/ICLS/ACLS pre-tune, FPAS home waypoint), `SA` (CAP points, corridor, FAOR/FLOT, MEZ threats), `TCN` (TACAN station list) |
| F-16C | yes | 2.9.15.9408 | `MPD` (steerpoints, GEO lines, threat and destination points), `COMM` (UHF/VHF, no channel names), `CMDS`, ROE/IFF, `COLR` |
| AH-64D | yes | in the install checked in November 2026 | `NAV` (2 mission files of waypoints/hazards, control measures, targets/threats, lines, areas, zones, routes, ADF), radios and presets, IDM, weapons, laser codes |
| CH-47F, MiG-29 | yes | in the install checked in November 2026 | not researched |
| F-14BU | yes | in the install checked in November 2026 | `NAV` (12 flight plans of 50 points: waypoints, 4 lines, reference points; plan 1 is the mission route), `JDAM` (8 targets for each of STA 3-6), `CMDS`, `TIS` (datalink callsigns); no radios |
| F-15E, JF-17, other F-14 | no | | keep the kneeboard and the miz waypoints (`M{n}.{i}`, PP, ST/IP) |

Sources: ED changelog 2.9.15.9408 and news of 2025-04-11; the third-party generator
`KaiserHomeLab/dcs-mission-maker` (`app/dtc.py`); the draft upstream PR
`dcs-retribution/dcs-retribution#966`, whose author checked the schema against
`MissionEditor/modules/me_managerDTC.lua` and `CoreMods/aircraft/<type>/DTC`. ED does not
publish the schema.

Checked in November 2026 against a DCS install and against missions saved by the mission
editor: the unit `DTC` block and the file envelope match. The editors of each module, in
`CoreMods/aircraft/<type>/DTC/`, are the reference for default values: the fixed Hornet
presets (G 243 AM, M 122.8 AM, C 30 FM, S 156.05 FM), the FM bands of the ARC-210
(30-88 and 156-174 MHz) and the empty offset aimpoint of each steerpoint
(`WYPT/WYPT_NAV.lua`).

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
  presets have names, which the miz cannot carry.
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
- **F-14BU:** flight plan 1 holds the route of the mission editor, so its waypoints stay
  empty. The cartridge adds to it the front lines nearest the package target (at most 4,
  each from end to end) and the 20 enemy air defense sites nearest it, as reference points
  `THRT 1`..`THRT 20`, with the ground height in feet (see *Elevations*). `TIS` keeps
  the module's defaults; `CMDS` and `JDAM` are set as below (#221).
- **F-14BU editor:** the editor is `F14/DTC/F-14BU_DTC.lua`. The `CMDS/` folder next to
  it is a leftover of the ALE-47 the editor no longer reads: a cartridge saved by DCS has
  `CMDS.CMDSProgramSettings.PROG_1..PROG_8` (burst and salvo of each dispenser, and a
  priority), `CMDSBingoSettings`, `CMDSAutoPrograms` and `CMDSAutoOverrides`.
- **F-14BU JDAM:** `JDAM.stations` holds STA 3 to 6 (pydcs pylons 4 to 7), 8 targets
  each. A target carries its position (`x`, `y`, `lat`, `lon`), `elev` **in metres**
  (unlike the navigation points), `attack_heading` (grid degrees, the direction the jet
  flies), `drop_alt` (ft), `drop_spd` (kt), the launch acceptability region
  (`lar_rmin_nmi`, `lar_rmax_nmi`, `lar_half_angle_deg`, and `lar_polygon`, its 11
  points), the launch point (`launch_x`, `launch_y`, the centre of the region by
  default) and `active`. The region comes from `JDAM_LAR_TABLE` of the editor, by drop
  altitude and Mach, Mach from the ISA speed of sound; Retribution reproduces
  `lookupJDAMLAR` and `calcLARPoints`, and gives the region and launch point of a
  cartridge saved by the editor to the centimetre (`F14_Tuto_JDAM.miz`). Each station
  that carries a GBU-31, -32 or -38 on the player's jet gets the aim points of the
  package target (its standing units, at most 8, else its position), its own one first
  (`TGT1`..`TGT8`), released from the leg into the first target waypoint: its grid
  heading, its altitude and its ground speed from the times of the flight plan.
- **F-16C:** its cartridge cannot name a channel, and the miz already carries the route
  and the presets, so `NAV_PTS`, `DEST`, `COMM1` and `COMM2` mirror the mission
  (`mirror_* = true`). The cartridge adds, in `MPD`, the front lines nearest the package
  target as `GEO_LINES` (at most 4, each on its own HSD line `L1`..`L4`, geo points 31 to
  38) and the 15 enemy air defense sites nearest it as `THREAT_PTS` (points 56 to 70),
  labelled `T1`..`T15`, each ringed at the reach Retribution computes for the site, or at
  the 20 nm of the editor's custom threat when unknown. The DTC editor loads a partial
  cartridge and fills every missing field with its default
  (`setData` of `CoreMods/aircraft/F-16C/DTC/F-16C_50_DTC.lua`), so `CMDS`, `ROE`,
  `ELINT` and `COLR` are left out and keep the module's defaults.
- **Unsupported module or failure:** nothing is written and the mission is generated as
  before; the kneeboard stays the fallback.
- **AH-64D:** the miz carries the route, so mission file 1 leaves out waypoints, hazards
  and control measures (their `isEnabled` stays off: the helicopter keeps those of the
  mission). The cartridge adds the front lines nearest the package target as FLOT lines
  (at most 4, `type_num` 4 of `NAV/Lines.lua`) and the 20 enemy air defense sites nearest
  it as target points `T01`..`T20`, typed `GU` (generic air defense unit), with the site
  name as note (40 characters), at the ground height in metres. Radios, IDM, weapons and laser
  codes keep the module's defaults.

## What the player sets (#221)

The Radios & TACAN tab of a player flight sets what goes into the cartridges of its
squadron. The settings live on the squadron (`Squadron.dtc`, `DtcSettings`), not on the
flight: flights are planned anew each turn. A save without them reads as the module's
defaults.

- **Load at spawn:** the unit's `DTC` block carries `"AutoLoad": false` when it is off;
  the pilot loads the cartridge from the DTC page.
- **Front lines and enemy air defenses** (F-16C, F-14BU, AH-64D): off, the cartridge
  leaves those partitions to the module.
- **CMDS programs** (F/A-18C, F-16C, F-14BU): the programs of the module (MAN 1-6,
  AUTO 1-3 and BYPASS on the F/A-18C and F-16C, programs 1 to 8 and their priority on
  the F-14BU) start from the module's defaults (`CMDS_defs.lua`, or the `CMDS` table of
  `F-14BU_DTC.lua`) and keep to the limits of its spin boxes. Only the values that
  differ are kept, and values of programs a module no longer has are ignored; once one
  differs, the cartridge carries every program whole:
  `ALR67.CMDS.CMDSProgramSettings` (F/A-18C), `MPD.CMDS.CMDSProgramSettings` (F-16C),
  `CMDS.CMDSProgramSettings` (F-14BU). The bingo settings and the threat tables are left
  out and keep the module's defaults. The `Other1` and `Other2` dispensers are not
  offered and stay at the module's values.
- **JDAM targets** (F-14BU): off, the cartridge leaves `JDAM` to the module.
- **Apply to every squadron of the aircraft** copies the settings to the other squadrons
  of the coalition that fly the same DCS type.
- **Not done yet:** the F-16C ROE/IFF and colours.

## Elevations

DCS terrains have no height data Retribution can read, and a public elevation model
(SRTM, Copernicus) differs from the terrain of the sim: smoothed, flattened airfields,
and roofs and trees in a surface model. So the heights are measured in DCS itself:
`scripts/heightmaps/make_scan_missions.py` makes missions that walk a grid with
`land.getHeight` and write it to `Saved Games` (Retribution open, so the mission can
write files); `pack_heightmap.py` packs a scan into `resources/heightmaps/<terrain>.dem`,
read by `game/theater/groundheight.py`.

- Measured in November 2026, every 100 m: Caucasus, PersianGulf, Syria (1 to 1.5 min
  each in DCS). On the 4 JDAM targets of `F14_Tuto_JDAM.miz`, the editor's `elev` and
  `land.getHeight` agree (10.01 m), and the 100 m grid gives 9.88 to 10.0 m.
- A 10 m scan of 20 x 20 km near Batumi, up to 1,224 m, sets the step: on land, a 100 m
  grid is within 1.7 m of the exact height for 95% of points (4.3 m on slopes over
  15 degrees), 50 m within 0.6 m, 200 m within 4.9 m. With a 65 degree impact, an
  error of 1 m moves a JDAM about 0.5 m.
- Packed in whole metres, as row-wise differences in xz blocks of 64 rows: 15 MB
  (Caucasus), 8 MB (PersianGulf), 21 MB (Syria). A lookup decompresses only the blocks
  under the point.
- The files are too large for git: they are ignored and ship in the release zip (see
  `resources/heightmaps/README.md`). Without the file of a map, the elevations stay 0.
- Used for the F-14BU JDAM targets (metres) and reference points and lines (feet), and
  the AH-64D target points (metres).
