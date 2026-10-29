# DCS Retribution — Feature Ideas PRD

**Status:** Draft for discussion — brainstorm output, not a committed roadmap
**Date:** 2026-07-02
**Scope:** Product/feature ideas only (not code-quality work). Grounded in the current architecture: Python campaign engine (`game/`), HTN theater commander (`game/commander`), fast-forward simulation (`game/sim`), FastAPI server (`game/server`) + React/Leaflet map client (`client/`), pydcs mission generation (`game/missiongenerator`), Lua plugin system (`game/plugins`, Skynet IADS, EW script, artillery scripts), Pretense export (`game/pretense`), and YAML-driven campaigns/factions/squadrons (`resources/`).

---

## Vision

Retribution already answers *"give me a realistic, persistent air war I can fly in DCS."* The next leap is to make it:

1. **Consequential** — every sortie should ripple through a living logistics, intel, and human layer (pilots, stockpiles, morale), not just move a front line.
2. **Frictionless** — collapse the loop between planning, flying, and debriefing until running a campaign feels like one continuous experience, including on dedicated servers.
3. **Shared** — turn the existing web server + client into a first-class multi-user planning and squadron experience.
4. **Narrated** — surface the story the campaign engine already generates (aces, lost pilots, falling bases) so players *feel* the war.
5. **Open** — make the campaign engine scriptable and the ecosystem (mods, community campaigns, external tools) pluggable.

**Legend** — Priority: P1 (high value, feasible next), P2 (valuable, larger), P3 (moonshot). Effort: S (< 1 wk), M (1–4 wk), L (1–3 mo), XL (3 mo+). Impact: ★ to ★★★.

---

## Top 10 Shortlist

| # | Feature | Why it wins |
|---|---------|-------------|
| 1 | [F-10 Intel & Fog of War](#f-10) | Transforms strategy layer; makes recon a real mission |
| 2 | [F-20 Weapon Stockpiles](#f-20) | Most-requested realism/economy feature since Liberation |
| 3 | [F-31 Pilot Career & CSAR Persistence](#f-30) | Emotional attachment; DCS players love their pilots |
| 4 | [F-60 Headless Mode & Dedicated-Server Loop](#f-60) | Unlocks 24/7 co-op servers; nothing else in ecosystem does this |
| 5 | [F-50 Full Web Planning UI (Multi-User)](#f-50) | Squadron co-op planning is Retribution's killer differentiator |
| 6 | [F-70 Debrief Analytics & Tacview Ingestion](#f-70) | Closes the loop; data already exists, nobody surfaces it |
| 7 | [F-63 DTC / Data-Cartridge Export](#f-63) | Massive QoL for F-16/F/A-18/F-15E owners; saves 15 min per sortie |
| 8 | [F-41 Target Deck & BDA Workflow](#f-41) | Makes strike planning feel like a real air campaign |
| 9 | [F-90 Live Persistence Bridge](#f-90) | Mid-mission state sync; foundation for "always-on" campaigns |
| 10 | [F-80 Difficulty Personas & Commander Assistant](#f-80) | Onboarding fix; the 100+ settings scare new players away |

---

## 1. Strategic Campaign Depth

<a id="f-01"></a>
### F-01 — Campaign Objectives & Victory Conditions
**Priority:** P1 · **Effort:** M · **Impact:** ★★★
Campaigns currently end by attrition/base capture. Add a YAML-defined objective system for campaign designers: phased goals ("Achieve air superiority over sector X", "Destroy 75% of enemy oil infrastructure", "Capture Kutaisi by turn 20"), time limits, scoring, and explicit win/lose/draw endings with an end-of-campaign summary screen. Builds on `game/campaignloader` and the existing TGO categories in `game/theater`.
*Why:* Gives campaigns narrative arcs and replayability; designers of the 136 bundled campaigns get expressive power for free.

<a id="f-02"></a>
### F-02 — Scripted Campaign Events & Branching
**Priority:** P2 · **Effort:** L · **Impact:** ★★★
Event engine for campaign YAML: triggers (turn N, base captured, unit type destroyed, objective met) fire effects (reinforcement wave, new squadron arrives, faction switches sides, ceasefire offer, new front opens, briefing message). Extends the existing "rebel zones" random-spawn concept into a general mechanism.
*Why:* Turns static scenarios into dynamic stories — "Turn 8: China intervenes" — with zero engine forks.

<a id="f-03"></a>
### F-03 — Political & ROE Layer
**Priority:** P2 · **Effort:** L · **Impact:** ★★
Track collateral damage (strikes on civilian-categorized statics, weapons in restricted zones) against a "political capital" resource. Campaign-designer-defined ROE phases: escalation ladder that unlocks target categories and weapon classes (e.g., no strikes across a border until provoked). Violations cost income or trigger events (F-02).
*Why:* Adds the classic Cold-War-gone-hot tension: hitting the wrong target should matter.

<a id="f-04"></a>
### F-04 — OPFOR Commander Personalities
**Priority:** P1 · **Effort:** M · **Impact:** ★★
The HTN theater commander (`game/commander/theatercommander.py`) plans identically every campaign. Add selectable doctrine profiles — Aggressive (deep strikes, sweeps), Defensive (CAP walls, IADS focus), Attritional (frontline grinding), Guerrilla (dispersal, ambush CAPs) — as weighting sets over existing task types, plus an optional "adaptive" mode that reacts to player behavior (counters your favorite tactics).
*Why:* Cheap replayability multiplier using infrastructure that already exists.

<a id="f-05"></a>
### F-05 — Named Enemy Operations with Intel Warnings
**Priority:** P2 · **Effort:** M · **Impact:** ★★
When the enemy commander commits to a major push (front-line stance changes, large package waves), name it ("Operation Sever") and leak warnings through the intel system (F-10) 1–2 turns ahead: "SIGINT indicates buildup near Gudauta." Player gets a chance to blunt or ambush it.
*Why:* Converts invisible AI state into dramatic, actionable gameplay moments.

<a id="f-06"></a>
### F-06 — Persistent Weather System & Forecasts
**Priority:** P1 · **Effort:** M · **Impact:** ★★
Weather (`game/weather`) is re-rolled per turn from archetypes. Model moving fronts instead: weather evolves plausibly turn-over-turn, and briefings include a 2–3 turn forecast so players plan around it ("window for the strike closes Thursday"). Optional: fetch real historical METAR for the campaign date/region.
*Why:* Weather becomes a planning factor (CASE III nights, IMC grounding CAS) instead of random noise.

<a id="f-07"></a>
### F-07 — Multi-Mission Turns (Full ATO Day Cycle)
**Priority:** P3 · **Effort:** XL · **Impact:** ★★★
Allow several player-flown (or simulated) mission windows per campaign day — dawn strike, afternoon CAS, night SEAD — with the fast-forward sim (`game/sim`) resolving everything between windows. The ATO becomes a true 24-hour document; squadrons have sortie rates rather than one flight per turn.
*Why:* The single biggest step toward "real air campaign" feel; heavy but transformative.

---

## 2. Intelligence & Fog of War

<a id="f-10"></a>
### F-10 — Intel Levels & Fog of War
**Priority:** P1 · **Effort:** L · **Impact:** ★★★
Today the map is omniscient: every SAM, ship, and parked aircraft is visible. Introduce per-object intel states (Unknown → Detected → Identified → Targetable) driven by: EWR/AWACS coverage, overflights, and dedicated recon. Unidentified sites show as "possible SAM" rings with positional uncertainty; strike planning against low-intel targets suffers coordinate error or requires a recon prerequisite. Toggleable (off = current behavior) to preserve casual play. Touches `game/server` map layers and the threat-zone renderer.
*Why:* The single largest strategic-depth feature available; makes SEAD/recon/AWACS placement meaningful instead of cosmetic.

<a id="f-11"></a>
### F-11 — Reconnaissance Mission Type
**Priority:** P1 · **Effort:** M · **Impact:** ★★★
New `FlightType.RECON` (photo/TARP/drone): fly a route over target areas to raise intel level (F-10), confirm BDA (F-41), and reveal enemy ground movements for the next turn. AI-flyable and player-flyable (score based on overflight parameters); losses hurt, creating escort demand. MQ-9/drones become genuinely useful.
*Why:* Fills an obvious mission-type gap (the enum in `game/ato/flighttype.py` has 24 types but no recon) and feeds the fog-of-war loop.

<a id="f-12"></a>
### F-12 — SIGINT/ELINT & Emitter Mapping
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Radars that emit during a mission (recorded in the debrief/state.json) become located on the campaign map; cold sites stay hidden. ELINT aircraft (RC-135, ELINT-capable pods) accelerate this passively. Pairs with Skynet IADS behavior where sites go dark.
*Why:* Creates the classic SEAD cat-and-mouse: force them to emit, then kill them.

<a id="f-13"></a>
### F-13 — Deception & Decoys
**Priority:** P3 · **Effort:** M · **Impact:** ★
Both coalitions can buy decoy SAM sites/aircraft (visually real, strategically worthless) that consume enemy strike sorties. Player decoys mislead the OPFOR commander's targeting; enemy decoys waste yours (revealed by high intel levels — rewarding F-11).
*Why:* Cheap counterplay layer on top of fog of war.

---

## 3. Logistics & Economy

<a id="f-20"></a>
### F-20 — Weapon Stockpile Management
**Priority:** P1 · **Effort:** L · **Impact:** ★★★
Finite munitions inventory per coalition (optionally per base): every GBU-31 loaded consumes stock; resupply arrives by turn schedule/convoy/airlift. Low PGM stocks push players toward dumb bombs and prioritization — exactly like real air wars. UI: stockpile panel + warnings in the payload editor; AI loadout selection (`game/ato/loadouts.py`) respects stock. Off by default for save-compat and casual players.
*Why:* Top-tier community request since Liberation days; makes the economy about more than buying airframes.

<a id="f-21"></a>
### F-21 — Fuel & Supply as Strategic Resources
**Priority:** P2 · **Effort:** L · **Impact:** ★★★
Bases hold fuel/ammo stocks fed by supply lines (`game/theater/transitnetwork.py`, `transfers.py` already model convoys/airlift). Strikes on fuel farms and interdiction of convoys reduce base sortie capacity and SAM reload; cut-off bases degrade over turns and eventually can't launch. Front-line strength already ties to supply routes — extend that to air operations.
*Why:* Makes BAI/Strike target selection strategic ("starve Mozdok") and gives the transport/convoy layer real teeth.

<a id="f-22"></a>
### F-22 — Airframe Maintenance & Fatigue
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Aircraft accumulate flight hours; each sortie has a chance of unserviceability (higher after damage), sending airframes into maintenance for N turns. Hangar/shelter capacity affects repair throughput; strikes on maintenance buildings slow it. Squadron dialog (which already tracks initial/destroyed/purchased stats) shows availability: "12 assigned / 9 serviceable".
*Why:* Sortie availability becomes a resource to manage; OCA strikes gain a second-order payoff.

<a id="f-23"></a>
### F-23 — Base Infrastructure Upgrades
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Spend income on per-base improvements with build times: hardened shelters (reduce OCA losses), extended fuel storage (F-21 buffer), EWR upgrade, additional parking, FARP expansion, runway repair speedups (RunwayStatus repair is currently a fixed 4 turns). Enemy can too — creating evolving target value.
*Why:* Gives the economy a construction axis and long-term planning beyond unit purchases.

<a id="f-24"></a>
### F-24 — Captured Equipment & Battlefield Salvage
**Priority:** P3 · **Effort:** M · **Impact:** ★
Capturing a base intact (fast advance vs. besieged) yields usable enemy stock: fuel, vehicles, occasionally airframes (flyable if faction-compatible or sellable for income). Retreating AI can demolish assets ("scorched earth" doctrine flag per F-04).
*Why:* Rewards operational tempo and makes captures feel like events.

---

## 4. Squadron, Pilots & the Human Element

<a id="f-30"></a>
### F-30 — Pilot Career System
**Priority:** P1 · **Effort:** M · **Impact:** ★★★
The `Pilot` model is currently name + status + missions_flown. Extend to a career record: kills (air/ground, by type), medals with award criteria, ranks with promotion thresholds, per-mission-type experience that maps to DCS AI skill on generation, fatigue requiring leave rotation, and a squadron "wall of honor" for the fallen. Include an exportable pilot logbook for the player's own pilot.
*Why:* Persistent pilots are the #1 emotional hook in dynamic campaigns — losing "Mongo, 23 missions, 4 kills" hurts in a way losing an F-16 doesn't.

<a id="f-31"></a>
### F-31 — CSAR Campaign Loop
**Priority:** P1 · **Effort:** L · **Impact:** ★★★
When a pilot ejects over hostile/contested territory, they don't just die: they become a downed pilot on the campaign map with a survival/evasion timer and capture risk per turn. A CSAR mission type (helo + RESCAP package) can recover them; failure means KIA or POW (POWs recoverable by capturing the area or via F-02 events). AI plans CSAR for its own pilots too.
*Why:* Generates the most memorable emergent missions in all of DCS; deepens F-30 attachment. Builds on existing Air Assault/helicopter logistics machinery.

<a id="f-32"></a>
### F-32 — Squadron Morale & Traditions
**Priority:** P2 · **Effort:** M · **Impact:** ★
Squadron-level morale from loss rates, victories, leave policy, and base quality; affects generated AI skill and (optionally) availability. Squadrons accrue history (campaign battle honors shown in the Air Wing UI) and can be renamed/re-badged by the player.
*Why:* Makes the Air Wing screen a place you care about, not just a roster.

<a id="f-33"></a>
### F-33 — Enemy Aces & Nemesis System
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Track enemy pilots the same way (F-30 symmetry). High-scoring enemy pilots become named aces flown at higher DCS skill, mentioned in intel briefings ("MiG-29 flight led by Maj. Orlov, 5 kills, operating from Gudauta"), and killable — with confirmation via debrief. Optional "nemesis" flavor: the ace that shot you down keeps appearing.
*Why:* Free drama from data the sim already produces.

---

## 5. Mission Planning & Generation

<a id="f-40"></a>
### F-40 — Fuel-Aware Flight Planning & Vertical Profile Editor
**Priority:** P1 · **Effort:** L · **Impact:** ★★
There's already fuel-consumption measurement research in `docs/game`. Surface it: computed fuel plan per waypoint (trip fuel, joker/bingo suggestions, tanker requirement warnings) in the flight edit dialog and kneeboard, plus an altitude-profile side view for the route (terrain elevation vs. planned altitudes, threat-ring intersections shown vertically).
*Why:* Range/fuel is the thing every DCS flight-lead calculates by hand today; huge planning QoL.

<a id="f-41"></a>
### F-41 — Target Deck & BDA Workflow
**Priority:** P1 · **Effort:** L · **Impact:** ★★★
A campaign-level target list: every known TGO/building with priority, status (untouched / damaged / destroyed / repaired), assigned strikes, and BDA confidence (certain if recon'd per F-11, estimated otherwise). "Re-strike recommended" queue each turn. Package creation from the target deck ("plan strike on this") instead of only from the map.
*Why:* This is how real air campaigns are run (JIPTL); turns scattered clicking into an operational workflow.

<a id="f-42"></a>
### F-42 — Weaponeering Advisor
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Recommend loadouts per target: weapon effectiveness vs. target class (hardened/soft/area), standoff range vs. threat rings along the route, expected weapons-per-kill so a 2-ship with 8 GBU-12s isn't sent against 20 revetted tanks. Feeds AI auto-loadout too (`loadouts.py`).
*Why:* Bridges the knowledge gap for non-expert players and makes AI packages more credible.

<a id="f-43"></a>
### F-43 — Terrain-Following / Low-Level Route Option
**Priority:** P2 · **Effort:** L · **Impact:** ★★
Per-package routing preference: current threat-avoidance (navmesh + threat zones) vs. low-level penetration that trades exposure time for terrain masking — using terrain elevation data to weave valleys (critical for helicopters, Tornado/F-111-style strikers, and modern stealth-less strikers vs. big SAMs).
*Why:* Enables the classic low-level strike fantasy the current planner routes around, literally.

<a id="f-44"></a>
### F-44 — Package Templates & Doctrine Presets
**Priority:** P1 · **Effort:** S–M · **Impact:** ★★
Save/share package compositions ("Alpha Strike: 4×SEAD + 4×Strike + 2×Escort + tanker") as templates applicable to any target, with per-faction doctrine defaults (NATO vs. WP force packaging). One click from target → full package proposal (extends the existing "Auto-Create package" button).
*Why:* Removes the most repetitive part of turn planning for experienced players.

<a id="f-45"></a>
### F-45 — Mission Rehearsal Export
**Priority:** P2 · **Effort:** M · **Impact:** ★
Generate a consequence-free practice .miz of the current package: same weather, same target area, same threats (intel-known ones only, per F-10), unlimited restarts, no campaign state impact. "Fly the rehearsal, then fly the real thing."
*Why:* DCS squadrons literally build these by hand today for big ops; Retribution has all the data to do it in one click.

<a id="f-46"></a>
### F-46 — Dynamic Slots & Modern DCS Spawn Tech
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Adopt DCS dynamic-spawn slots so multiplayer clients can choose airframe/loadout at join time from squadron-available aircraft (respecting stockpiles per F-20), instead of pre-baked client slots. Reduces .miz size and re-planning churn for co-op groups.
*Why:* Aligns Retribution with where DCS multiplayer is going; big for the co-op audience.

---

## 6. Ground & Naval War

<a id="f-47"></a>
### F-47 — Operational Ground-War AI 2.0
**Priority:** P2 · **Effort:** XL · **Impact:** ★★★
Front lines currently grind along transit links. Add operational maneuvers: multi-axis pushes, breakthroughs that exploit undefended links, encirclement (pocketed units lose supply per F-21 and surrender), reserves, and withdrawal decisions. Visualize unit concentrations and axes on the map (intel-gated per F-10).
*Why:* Makes the CAS/BAI air war serve a ground war that visibly thinks.

<a id="f-48"></a>
### F-48 — Naval Campaign Layer
**Priority:** P2 · **Effort:** L · **Impact:** ★★
Player-issued fleet movement orders (carrier group stations, SAG patrol boxes) on the campaign map with turn-based movement; ASW gameplay (enemy submarines threaten convoys/carriers, S-3/helo ASW missions with sonobuoy plugin support); mine-laying missions that close ports/straits until swept. Convoy escort as a plannable mission with real stakes (F-21 supply).
*Why:* Carriers are currently near-static set pieces; naval players deserve a maneuver game.

<a id="f-49"></a>
### F-49 — FARP & Forward-Base Construction
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Build new FARPs/road-base sites at campaign-designer-allowed locations by delivering engineering supplies (helo sling-load or convoy). Construction over N turns, then a functioning helicopter/STOVL base. Enemy can strike partially-built sites.
*Why:* Gives helicopter players agency over campaign geography; pairs with existing road-base support.

---

## 7. Player Experience & UI

<a id="f-50"></a>
### F-50 — Full Web Planning UI (Multi-User Co-op Planning)
**Priority:** P1 · **Effort:** XL · **Impact:** ★★★
The FastAPI server and React map client already exist for the embedded map. Grow the client into a complete planning surface: browse the ATO, create/edit packages and flights, edit loadouts, read briefings — from any browser/tablet. Then multi-user: several squadron members plan concurrently (package-level locking), each claiming their own flight, with a commander role approving the ATO. Qt stays as the local "host" app.
*Why:* This is the feature that makes Retribution the operating system for DCS squadrons. Nothing else in the ecosystem offers collaborative ATO planning.

<a id="f-51"></a>
### F-51 — F10-Map Drawing Sync & Planning Overlays
**Priority:** P1 · **Effort:** M · **Impact:** ★★
Drawing tools on the campaign map (lines, arrows, zones, text, MGRS grid, range rings, bulls-eye calls) that export into the generated .miz as F10 map drawings — so the plan you sketched is visible in-cockpit to all clients. Import direction too where feasible.
*Why:* Squadrons currently juggle external whiteboards; this closes the loop with almost pure pydcs plumbing.

<a id="f-52"></a>
### F-52 — Briefing 2.0 (Web + PDF + Audio)
**Priority:** P1 · **Effort:** M · **Impact:** ★★
Generated per-package briefing page: situation, weather + forecast (F-06), threat assessment with map extract, comm ladder, TOT line-up card, divert info — as shareable web page and printable PDF for kneeboard-on-your-desk flyers. Optional TTS "intel officer" audio rendition.
*Why:* Briefings are the product surface players share with friends; today's text briefing undersells the sim underneath.

<a id="f-53"></a>
### F-53 — Kneeboard Studio
**Priority:** P2 · **Effort:** M · **Impact:** ★
WYSIWYG editor for kneeboard templates (fields drag-drop from mission data: freqs, TOTs, codes, waypoints), per-squadron styles, live preview per airframe. Custom kneeboard injection already exists — this makes it accessible to non-modders.
*Why:* Every squadron reskins kneeboards by hand today.

<a id="f-80"></a>
### F-80 — Difficulty Personas & Commander Assistant
**Priority:** P1 · **Effort:** M · **Impact:** ★★★
The 1,646-line settings module (~100+ options) is powerful but hostile to newcomers. Bundle settings into personas — Relaxed / Simulation / Iron War — chosen at campaign start with a plain-language description of consequences, all still individually overridable. Add a "staff advisor" panel each turn: top 3 suggested actions with reasons ("Enemy IADS covers the front line — plan DEAD on SA-10 at Beslan before committing strikes"), backed by the theater commander's own analysis of the player's coalition.
*Why:* Single highest-leverage growth feature: converts overwhelmed downloaders into retained players by teaching the game with its own AI.

<a id="f-81"></a>
### F-81 — Turn Rollback & Versioned Autosaves
**Priority:** P1 · **Effort:** S–M · **Impact:** ★★
Automatic per-turn save snapshots with a "return to turn N" picker, plus pre-migration backups (the README currently tells users to back up saves by hand). Optional "honor mode" that disables rollback for the iron-man crowd.
*Why:* Save loss / bad-turn regret is a recurring pain; trivial storage cost since landmap data is already lazy-loaded.

<a id="f-82"></a>
### F-82 — Localization
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Externalize UI strings and ship community-translatable language packs (French, German, Spanish, Chinese, Russian first — matching DCS's player base). Include briefing/kneeboard template localization.
*Why:* DCS's audience is heavily non-anglophone; competitors (in-game DC) will be localized.

---

## 8. Debrief, Analytics & Narrative

<a id="f-70"></a>
### F-70 — Debrief Analytics & Tacview Ingestion
**Priority:** P1 · **Effort:** L · **Impact:** ★★★
Post-mission debrief screen beyond the current results list: kill/loss timeline, shot log (who fired what at whom, Pk), per-flight objective outcomes, and campaign-level dashboards (attrition curves, sortie effectiveness by mission type, front-line movement over time). Optionally parse the mission's Tacview ACMI (most players run it anyway) for precise event data and a mini 2D replay on the campaign map.
*Why:* The campaign generates rich data and then throws it away; analytics close the plan→fly→learn loop and feed F-30/F-33 pilot records.

<a id="f-71"></a>
### F-71 — War Diary & Campaign Report Export
**Priority:** P1 · **Effort:** M · **Impact:** ★★
Auto-generated narrative log per turn ("D+12: Sukhumi fell after three days of encirclement. Capt. Reyes made ace.") assembled from engine events, browsable as a timeline in-app and exportable as a shareable HTML/PDF campaign report with maps and squadron stats at campaign end.
*Why:* Players already write these by hand on forums/Discord — give them a one-click flex, which is also free marketing.

<a id="f-72"></a>
### F-72 — Campaign Map Time-Lapse Replay
**Priority:** P2 · **Effort:** M · **Impact:** ★
Scrub through campaign history on the map: front lines, base ownership, and major events animating turn by turn (data recorded per turn going forward). Export as video/GIF.
*Why:* The single most shareable artifact a dynamic campaign can produce.

---

## 9. Multiplayer & Co-op Operations

<a id="f-60"></a>
### F-60 — Headless Mode & Dedicated-Server Loop
**Priority:** P1 · **Effort:** L · **Impact:** ★★★
A no-GUI CLI/daemon mode: watch for mission end → process state.json → advance turn → auto-plan (existing auto-ATO) or wait for web-UI plans (F-50) → generate next .miz → upload to the DCS dedicated server (WebGUI API / file drop) → optionally rotate the mission. Result: a 24/7 self-running Retribution server where players just join DCS and fly the current turn.
*Why:* This is the most-wished-for deployment model for co-op communities; the FastAPI server and event stream are already halfway there.

<a id="f-61"></a>
### F-61 — Player Identity & Squadron Stats
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Map DCS multiplayer names to persistent campaign pilots (F-30): each human's kills, sorties, and losses tracked across the campaign; slot claiming in the web UI reserves a specific flight for a specific person; per-player leaderboards and logbooks.
*Why:* Squadrons run on identity and bragging rights.

<a id="f-62"></a>
### F-62 — PvP Dual-Commander Mode
**Priority:** P3 · **Effort:** L · **Impact:** ★★
Two humans command opposing coalitions. OPFOR planning UI already exists ("Allow planning as OPFOR"); add turn-exchange flow (hot-seat, save-file exchange, or both connected to one server with coalition-scoped views and fog of war per F-10) and simultaneous-commit turn resolution.
*Why:* Wargame audiences love asymmetric human-vs-human; Retribution is uniquely positioned to offer it inside DCS.

<a id="f-64"></a>
### F-64 — Discord Integration
**Priority:** P2 · **Effort:** S–M · **Impact:** ★★
Webhook/bot: post turn summaries, war-diary entries (F-71), the next mission's briefing link (F-52), and flight sign-up messages (claim a slot by reacting, wiring into F-61). Configurable per campaign.
*Why:* Discord is where every DCS squadron lives; meet them there.

---

## 10. Integration & Ecosystem

<a id="f-63"></a>
### F-63 — DTC / Data-Cartridge & Comm-Plan Export
**Priority:** P1 · **Effort:** L · **Impact:** ★★★
Export each flight's data into cockpit-ready form: DCS DTC for supported modules (F-16, F/A-18, AH-64…), .miz-embedded module setups where supported, plus SRS channel-plan presets and a CombatFlite-compatible export for tooling interop. Waypoints, radio freqs, laser codes, datalink nets — Retribution already computes all of it (`game/radio`, `game/lasercodes`, datalink setup).
*Why:* Eliminates 10–20 minutes of cockpit data entry per sortie — arguably the biggest per-mission QoL win available.

<a id="f-65"></a>
### F-65 — Mod Auto-Detection & Compatibility Guard
**Priority:** P1 · **Effort:** S–M · **Impact:** ★★
Scan the user's DCS Saved Games/mods folders to detect installed aircraft/asset mods and versions; auto-enable matching unit support, warn at campaign/faction selection when required mods are missing or version-mismatched (with download links), and gate generation with a clear pre-flight check.
*Why:* Mod mismatch is a top support-channel complaint for a project whose changelog is ~40% mod-support entries.

<a id="f-66"></a>
### F-66 — Public API & Python Plugin Hooks
**Priority:** P2 · **Effort:** M · **Impact:** ★★
Stabilize and document the FastAPI surface (OpenAPI config already exists in `client/`), and add Python-side extension hooks (on_turn_begin, on_mission_generated, on_debrief_processed, economy modifiers) with a plugin folder — the Lua plugin system's equivalent for campaign logic.
*Why:* Lets the community build the features you don't have time for; ecosystems outlive features.

<a id="f-67"></a>
### F-67 — Community Campaign & Faction Workshop
**Priority:** P2 · **Effort:** M · **Impact:** ★★
In-app browser for community campaigns/factions/squadron packs pulled from a curated Git-based index: search, screenshots, ratings, required mods (cross-checked via F-65), one-click install/update. Include an uploader path for creators.
*Why:* 136 bundled campaigns is great; a marketplace-style flow turns campaign design into a community engine.

<a id="f-68"></a>
### F-68 — Streamer/Companion Overlay
**Priority:** P3 · **Effort:** S · **Impact:** ★
Read-only OBS-friendly web overlay: campaign map state, current package, pilot roster ticker, war-diary headlines. Just a themed view over the existing event-stream websocket.
*Why:* Cheap visibility engine — every Retribution streamer becomes an advertisement.

---

## 11. Simulation Engine

<a id="f-90"></a>
### F-90 — Live Persistence Bridge (Mid-Mission Campaign Sync)
**Priority:** P3 · **Effort:** XL · **Impact:** ★★★
Today the campaign updates only when a mission ends; the Pretense generator shows the demand for persistent play. Build a live bridge: the in-mission Lua streams events (kills, captures, landings) to the Retribution server continuously; the campaign map updates in real time; and for long-running server missions, campaign consequences (reinforcements, next-wave packages via dynamic spawns per F-46) inject back into the running mission. End state: Retribution as the always-on "brain" of a persistent DCS server, with turns becoming optional.
*Why:* This is the end-game vision that unifies the turn-based and Pretense/Foothold worlds — nobody has shipped it well yet.

<a id="f-91"></a>
### F-91 — Higher-Fidelity Fast-Forward Combat
**Priority:** P2 · **Effort:** L · **Impact:** ★★
Extend the fast-forward simulation (`game/sim/combat`: currently air-to-air and SAM engagement zones) with resolution models for AI strike effectiveness (weapons vs. target class per F-42), naval engagements, and front-line ground combat — so "skip combat" turns produce believable attrition without generating a DCS mission at all. Enables fully simulated "commander-only" turns.
*Why:* Lets players run the campaign as a strategy game between the sorties they actually want to fly — and is the compute backbone for F-07's multi-mission days.

<a id="f-92"></a>
### F-92 — Ground-Unit Veterancy & Named Formations
**Priority:** P3 · **Effort:** M · **Impact:** ★
Front-line units aggregate into named brigades/battalions with experience, strength, and history (mirroring squadrons); veteran formations fight better in sim resolution and appear in intel/briefings ("elements of the 4th Guards approaching Gali").
*Why:* Symmetry with the air-side human layer; makes the ground war legible and narratable.

---

## Suggested Sequencing (opinionated)

1. **Wave 1 — Retention & QoL (P1/S–M):** F-80 personas+advisor, F-81 rollback saves, F-44 package templates, F-65 mod guard, F-51 F10 drawings, F-64 Discord webhook.
2. **Wave 2 — Depth (P1/L):** F-10/F-11 fog of war + recon, F-20 stockpiles, F-30/F-31 pilot careers + CSAR, F-41 target deck, F-06 weather continuity, F-01 objectives.
3. **Wave 3 — Platform (P1–P2/L–XL):** F-60 headless server loop, F-50 web planning UI, F-63 DTC export, F-70 debrief analytics, F-71 war diary, F-66 public API.
4. **Wave 4 — Moonshots (P3/XL):** F-90 live persistence bridge, F-07 multi-mission days, F-47 ground war 2.0, F-62 PvP commanders.

---

*Generated with Claude Code from analysis of the dcs-retribution codebase (branch `dev`). Each item references the modules it would build on; none have been validated for effort with the maintainers.*
