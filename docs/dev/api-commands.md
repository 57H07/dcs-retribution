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
