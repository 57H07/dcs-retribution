"""API key protecting the local server (WEB-00.6).

The server only listens on the loopback interface, but any web page open in the
player's browser can still send requests to it. A key generated at launch and
known only to the pages the game opens itself (QLiberationMap passes it in the
URL) keeps those pages from changing the game or reading the event stream.

- Commands (every POST, PUT, PATCH and DELETE route) require the `X-API-Key`
  header, or answer 401.
- The `/eventstream` websocket requires the `apiKey` query parameter (browsers
  cannot set headers on a websocket, and websockets are not subject to CORS).
- Reads (GET) stay open: they change nothing, CORS already keeps other origins
  from reading their responses, and some are loaded by URL by the map (basemap
  tiles), where no header can be added.
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import HTTPException, WebSocketException, status
from starlette.requests import HTTPConnection

from .settings import ServerSettings

API_KEY_HEADER = "X-API-Key"
API_KEY_QUERY_PARAM = "apiKey"
COMMAND_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class ApiKeyManager:
    _key: Optional[str] = None

    @classmethod
    def key(cls) -> str:
        """The key of this launch: random, unless fixed by `SERVER_API_KEY`.

        A fixed key (in serverconfig.env) lets a client started on its own (the
        Vite dev server in a browser or Electron) send it from `VITE_API_KEY`.
        """
        if cls._key is None:
            cls._key = ServerSettings.get().server_api_key or secrets.token_urlsafe()
        return cls._key

    @classmethod
    def is_valid(cls, supplied: Optional[str]) -> bool:
        return supplied is not None and secrets.compare_digest(
            supplied.encode(), cls.key().encode()
        )


def require_api_key(connection: HTTPConnection) -> None:
    """App-wide dependency: checks the key on commands and on the websocket."""
    if connection.scope["type"] == "websocket":
        if not ApiKeyManager.is_valid(connection.query_params.get(API_KEY_QUERY_PARAM)):
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API key."
            )
        return
    if connection.scope.get("method") not in COMMAND_METHODS:
        return
    if not ApiKeyManager.is_valid(connection.headers.get(API_KEY_HEADER)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
        )
