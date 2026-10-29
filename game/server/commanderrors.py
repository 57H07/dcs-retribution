"""HTTP side of `game.commands.CommandError` (WEB-00.5, see docs/dev/api-commands.md)."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from game.commands import CommandError


class CommandErrorJs(BaseModel):
    """Body of a refused command: a message the client can show as is."""

    detail: str

    class Config:
        title = "CommandError"


def command_error_responses(description: str) -> dict[int | str, dict[str, Any]]:
    """`responses=` entry documenting a command's business errors in the OpenAPI."""
    return {409: {"model": CommandErrorJs, "description": description}}


async def command_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, CommandError)
    return JSONResponse(
        status_code=exc.status_code,
        content=CommandErrorJs(detail=exc.message).model_dump(),
    )
