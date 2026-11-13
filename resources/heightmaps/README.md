# Height maps of the DCS maps

`<terrain>.dem` holds the ground height of a DCS map every 100 m, measured in DCS
itself with `land.getHeight`, so it matches the terrain of the sim. Retribution reads
it through `game/theater/groundheight.py`, for the elevations of the data cartridges
(F-14 JDAM targets, reference points).

The files are too large for git (15 to 20 MB each): they are ignored here and ship in
the release zip, which PyInstaller builds with the whole `resources` folder. **Put them
here before building a release.** Without a map's file, the cartridges of that map
keep an elevation of 0.

To measure a map (in DCS, with Retribution open so that the mission can write files):

1. `python scripts/heightmaps/make_scan_missions.py` writes the scan missions in
   `Saved Games/DCS/Missions/Retribution_heightscan_*.miz`.
2. Run the mission of the map in DCS; it writes
   `Saved Games/DCS/Retribution/Heightmaps/<map>_100m.bin` and `.json` (about 1 to 2
   minutes).
3. `python scripts/heightmaps/pack_heightmap.py <map>_100m <Terrain.name>` writes
   `resources/heightmaps/<Terrain.name>.dem`.

Measured in November 2026: Caucasus, PersianGulf, Syria. On land, the 100 m grid is
within 1.7 m of the exact height for 95% of points (4.3 m on slopes over 15°).
