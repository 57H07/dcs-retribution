# Web UI: what is already on `dev` (for sub-agents)

Read with `implementation-brief.md`. Updated by the orchestrator as lots land.

- **Client:** Vite 8, TS 5.9, Vitest (`npm test` runs once), React 18, RTK Query generated offline (`python -m game.server.openapischema` then `npm run regenerate-api`).
- **Design system:** `client/src/ui/` (tokens `--ui-*`, Radix-based components, `MilSymbol`, `TaskTag`, `Menu`, `Toast`, …). Dev catalog: `client/catalog.html`. Add a component there only if it is generic.
- **Shell:** `client/src/shell/` — hash router (`routes.tsx`, `paths.ts`), `AppBar.tsx` = full top bar (WEB-01.1), menus `appMenus`, shortcuts (`shortcuts.ts`; layer toggles via `client/src/maplayers/layerToggle.ts` `toggleOverlay()`), `QtScreen.tsx` fallback that opens a Qt dialog through `POST /qt/dialogs/{dialog}`.
- **Command view:** `client/src/command/` — `CommandView.tsx` with slots: left panel (WEB-01.2), right inspector (WEB-01.3), bottom timeline (WEB-01.4); `TurnActions.tsx` (End turn / Take off with confirmations); `useTakeOff.ts` (`POST /game/mission` → Qt waiting window through `QtCallbacks.mission_generated`, until WEB-05.1).
- **Server:** every route `@locked` (`game/gamelock.py`, enforced by a test; native dialog routes use `@locks_game_itself`); business logic in `game/commands/`; errors `CommandError` → 409; API key `X-API-Key` on non-GET, `?apiKey=` on `/eventstream`; Qt notifications through `QtCallbacks` (`game/server/dependencies.py`) emitting queued signals on `QLiberationWindow`.
- **Existing web screens:** `/settings` (`client/src/settings/`, `game/server/gamesettings/`), top bar data `GET /game/top-bar`, native bridge `/native/*` (`game/native/`, `qt_ui/nativebridge.py`).
- **Guide:** `docs/dev/api-commands.md` (§1-§9). Keep it updated when you add a pattern.
- **Transition rule:** the web UI stays OFF by default until WEB-05.2 flips it. Keep Qt screens working in Qt mode; in web mode stop using them. List in your PR what WEB-05.2/WEB-09 must delete.
- **Parallel work:** several agents run at once. Generated files (`client/openapi.json`, `client/src/api/_liberationApi.ts`) and `changelog.md` often conflict: on conflict, merge `origin/dev`, take dev's generated files and regenerate; never force-push.
