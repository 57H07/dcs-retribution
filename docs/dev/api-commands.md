# API commands

How to add a command (an API route that changes the game) for the web UI. Spec:
WEB-00.5 and decisions W2/W3 in `docs/dev/design/specification-interface-web.md`.
Worked example: `POST /game/turn/pass` (`game/server/game/routes.py`,
`game/commands/turn.py`, `tests/server/test_pass_turn_command.py`,
`client/src/api/commands.test.ts`).

## 1. Business logic in `game/commands/`

The rules live in a plain function under `game/commands/`, shared by the API route
and any remaining Qt widget (extract it from `qt_ui/` if it lives there today, and
make the Qt code call it). It takes a `Game`, knows nothing about HTTP or Qt, and
raises `CommandError("readable message")` when the action is not allowed.

```python
def skip_turn(game: Game) -> TurnState:
    if game.check_win_loss() is not TurnState.CONTINUE:
        raise CommandError("The campaign is over: no further turn can be played.")
    game.pass_turn(no_action=True)
    return game.check_win_loss()
```

## 2. Route: REST per resource (W3)

- Reads are `GET` returning a `*Js` pydantic DTO. Commands use the verb that fits
  the resource: `POST /packages`, `DELETE /packages/{id}`, `PUT
  /control-points/{id}/destination`, `POST /game/turn/pass`...
- Give every route an `operation_id` (it names the generated client hook:
  `pass_turn` becomes `usePassTurnMutation`) and a `response_model`, or
  `status_code=204` with `response_class=Response` when nothing is returned.
- Document business errors with `responses=command_error_responses("when...")`.

## 3. The game lock (W2)

Decorate every route with `@locked` (from `game.gamelock`), under the router
decorator. `tests/server/test_game_lock.py` fails on any route without it. While
holding the lock never wait on another thread (no modal dialog, no blocking signal).

## 3b. The API key (WEB-00.6)

Nothing to do per route: `require_api_key` (`game/server/security.py`) is an
app-wide dependency of `game/server/app.py`.

- Every `POST`, `PUT`, `PATCH` and `DELETE` request must carry the key of this
  launch in the `X-API-Key` header, or gets `401 {"detail": "Missing or invalid
  API key."}`. The `/eventstream` websocket needs it as the `apiKey` query
  parameter (browsers cannot set websocket headers), or is closed with 1008.
- `GET` routes stay open: they change nothing, CORS keeps other origins from
  reading them, and the map loads some of them by URL (basemap tiles), where no
  header can be set. A read that changes the game is therefore a bug: make it a
  command.
- The key is random per launch (`ApiKeyManager.key()`). `QLiberationMap` passes
  it to the page as `?apiKey=`; `client/src/api/backend.ts` reads it once and
  adds the header to commands of the generated hooks (`baseApi.ts`) and of the
  `backend` axios instance, and appends it to `WEBSOCKET_URL`. Use those, never a
  bare `fetch`/`axios`.
- A client started on its own (Vite dev server in a browser, `npm run electron`)
  has no `?apiKey=`: set `SERVER_API_KEY=<anything>` in `serverconfig.env` (with
  `CORS_ALLOW_DEBUG_SERVER=true`) and the same value as `VITE_API_KEY` in
  `client/.env.local`. The Qt `--dev` mode needs neither: it passes the key.
- The server keeps listening on loopback only (`server_bind_address`).
- Route tests through the ASGI app send the key: see `_post` in
  `tests/server/test_pass_turn_command.py`, and `tests/server/test_api_key.py`.

## 4. Events: refresh every open screen

A command publishes what it changed on the event stream so that every open screen
updates without a full reload:

```python
from game.server import EventStream

with EventStream.event_context() as events:
    events.update_control_point(cp)
```

Pick the `GameUpdateEvents` methods matching what changed (`update_flight`,
`update_tgo`, `begin_new_turn`...). Engine code that already publishes (like
`Game.pass_turn`, which sends `new_turn`) needs nothing more. When a Qt widget must
also refresh, add a callback to `QtCallbacks` (`game/server/dependencies.py`) that
emits a signal of `QLiberationWindow`: the route runs on a worker thread, and the
signal queues the refresh onto the Qt main thread (see `turn_passed`).

## 5. Errors

- Business refusal: raise `CommandError(message)` -> `409` with
  `{"detail": message}` (`CommandError(message, status_code=...)` for another
  4xx). The handler is registered in `game/server/app.py`.
- Unknown id: `HTTPException(404, detail=...)`, as the existing routes do.
- Bad payload: FastAPI answers `422` on its own.

The message is shown to the player as is: short, plain English, no stack trace.
On the client, `commandErrorMessage(error)` (`client/src/api/commands.ts`) turns
a failed mutation into that text.

## 6. Regenerate the client (offline)

Every PR that changes the API regenerates the client; no server needs to run:

```sh
python -m game.server.openapischema     # writes client/openapi.json
cd client && npm run regenerate-api     # writes client/src/api/_liberationApi.ts
```

Commit both files. `test_committed_openapi_json_is_up_to_date` fails when
`client/openapi.json` is stale. The dump describes required `X | None` fields as
optional `X` (as pydantic 1 did, which the client was written against); the server
still sends `null`, so test such fields with `!= null` on the client. Avoid
`Enum`s whose values are tuples in DTOs: their OpenAPI enum is a list of arrays
that codegen cannot handle (send a string or a list of strings instead).

## 7. Tests

- Server: unit-test the `game/commands` function with a small fake `Game`, then
  the route through the ASGI app (`_post` in `test_pass_turn_command.py` drives
  the app without a server or httpx): status, JSON body, error `detail`, events.
- Client: stub `fetch`, dispatch `_liberationApi.endpoints.<name>.initiate()` on
  `setupStore()` and check the request and result (see `commands.test.ts`).

## 8. Screens not migrated yet: `/qt/*` (WEB-00.3)

Until a screen has its web version, its client route opens the Qt dialog through
a target route (`/qt/create-package/...`, `/qt/info/...`,
`/qt/edit-package/...`; `/qt/info/tgo/...` only serves the Qt map and answers 503 in
web mode, where its callback is `None`). The route only calls a `QtCallbacks` callback that emits
a `QLiberationWindow` signal, so the dialog opens on the Qt main thread after the
lock is released. A migrated screen removes its route, its Qt slot and the dialog
itself (W9), and replaces its `QtScreen` element in
`client/src/shell/routes.tsx`. The generic `POST /qt/dialogs/{dialog}` left with
its last dialog, the air wing (WEB-03). A tool with no file UI needs no dialog at
all: `POST /tools/import-layouts` and `POST /tools/pretense-campaign` (WEB-08.2) are
plain commands that answer once the work is done.

The bare map embedded in the Qt window (Qt mode) has no router: its clicks keep
going through `/qt/*`, and the web shell overrides them through a context
(`MapSelectionContext`, `NewPackageContext` in `client/src/maplayers/mapSelection.tsx`).
A right-click on a target thus plans a package with `POST /packages` and opens
`/packages/{id}` in the web shell, and `/qt/create-package/...` in Qt mode.

A base screen tab does not fetch through `GET /control-points/{id}/base` when it
has its own read model (`/ground-forces`, `/convoys`, `/actions`, WEB-02.3): they all
provide `Tags.BASE`, so a base event refreshes them together.
`POST /control-points/{id}/convoys/{destination}/package` opens the package editor on
a convoy or cargo ship (they have no id of their own, hence the origin, destination
and `kind`); WEB-04.1 moves it to the web editor with `POST /packages`.

A command may also hand over to a Qt window that is not migrated yet, through a
`QtCallbacks` callback emitting a `QLiberationWindow` signal (WEB-05.1 did so for
the debriefing, until WEB-05.2 replaced it with the web after-action report).

## 8a. An editor with no save step: the package editor (WEB-04.1)

Each change of `/packages/{id}` is a command that applies at once and answers the
whole read model (`PackageDetailJs`), and each form is a `GET` of what the engine
offers (`/flight-options`, `/auto-create`): the client lists and sends, the engine
decides. Rules a Qt dialog checked when saved move to the command that would break
them: an escort cannot come first, the last escorted flight cannot leave. Qt dialogs
stay in Qt mode and call the same functions (`game/commands/packageflights.py`), which
`tests/flightplans` (W16) drives against unchanged references.

The Payload tab (WEB-04.3, `game/commands/flightpayload.py`, `game/server/flightpayload/`,
`GET /packages/{id}/flights/{id}/payload`) works the same way. Its read model separates what
is stored from what flies: with the date restriction on, a read shows the degraded loadout
and never writes it, and turning on the custom loadout starts from what was shown.

## 8b. Background work: status + event + commands (WEB-05.1)

Work that waits on something outside the API (DCS writing `state.json`) runs on
its own thread and is exposed as a resource: `GET /game/mission/result` returns
its status, every change publishes an event flag (`mission_result_updated`) that
the client turns into a tag invalidation (`Tags.MISSION_RESULT` in
`client/src/api/eventstream.tsx`), and commands act on it (`POST
/game/mission/result/{file,cancel,accept}`). The state lives in
`MissionResultWaiter` (`game/commands/missionresult.py`) behind its own small
lock, so reading the status never waits for the game lock; the watch thread
(`PollDebriefingFileThread`) takes the game lock only to read a new file, and a
generation counter drops callbacks of a watch stopped in between.

The after-action report (WEB-05.2, `GET /game/mission/result/report`) is a read
model built in `game/debriefingreport.py`, shared with the Qt debriefing. A
command whose outcome is only known once it ran keeps both halves on the engine
side: `accept_and_report` reads the report before applying the result (this
turn's ATO is gone afterwards), calls the same `accept_results` as the Qt path,
then completes the report (prisoners, budget, messages logged meanwhile) and
keeps it in `MissionResultWaiter.last_report()` for the screen to refetch.

## 9. System actions: the native bridge `/native/*` (WEB-00.7, W7)

What a web page cannot do goes through `NativeBridge` (`game/native/bridge.py`),
which the shell implements (`qt_ui/nativebridge.py` today, Electron or a browser
later): `POST /native/save`, `/native/save-as`, `/native/open`, `/native/new-game`,
`/native/quit`, `/native/open-folder/{saves|missions}`,
`/native/open-link/{link}` (`ExternalLink` in `game/native/places.py`), and
`/native/pick-folder` (`{"purpose": "saved-games"|"dcs-install", "start"}` ->
`{"path"}`, null when cancelled; WEB-07.2), which never touches the campaign.

- The file routes answer **when the player closes the dialog**, with
  `FileActionResult` (`{"outcome": "saved"|"opened"|"cancelled", "path"}`), or a
  `CommandError` (409: no campaign, a dialog already open, campaign changed during
  the dialog, incompatible save; 500: the file cannot be written). The request
  itself carries the result back: no correlation id, and the client simply awaits
  the mutation to show a toast. A loaded campaign then reaches every screen through
  the usual `game_loaded` event.
- They hold the game lock only to read and write the campaign, never while the
  dialog waits (`game/native/files.py`), so they are marked `@locks_game_itself`
  instead of `@locked`. The other `/native/*` routes only queue work and use
  `@locked`.
- Another file dialog (any file, Qt filter syntax) is `NativeBridge.choose_file`,
  guarded by `one_dialog()`: see `POST /game/mission/result/file`.
- `game/native/files.py` holds the save/open rules (last save file, migration,
  cancel); the Qt menus call the same functions.
