"""Dump the API's OpenAPI schema to a file, without starting the server (WEB-00.5).

The client generates its API code from that file (`client/openapi-config.ts`):

    python -m game.server.openapischema   # writes client/openapi.json
    cd client && npm run regenerate-api   # writes client/src/api/_liberationApi.ts

A test fails when the committed client/openapi.json no longer matches the server.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "client" / "openapi.json"


def openapi_schema() -> dict[str, Any]:
    """The schema the client is generated from (see `optional_nullable_fields`)."""
    from game.server.app import app

    return optional_nullable_fields(copy.deepcopy(app.openapi()))


def optional_nullable_fields(schema: dict[str, Any]) -> dict[str, Any]:
    """Describe required `X | None` model fields as optional `X`, as pydantic 1 did.

    Pydantic 2 describes them as required `anyOf: [X, null]`, which the client code
    (written against the pydantic 1 schema) does not expect: generated fixtures and
    props would all need explicit `null`s. The server still sends `null`; the client
    tests those fields with `!= null`, which covers both. Fields declared with an
    explicit `= None` default keep their `X | null` type. The live `/openapi.json`
    is left untouched.
    """
    for model in schema.get("components", {}).get("schemas", {}).values():
        required: list[str] = model.get("required", [])
        for name, prop in model.get("properties", {}).items():
            if name not in required:
                continue
            variants = prop.get("anyOf")
            if not isinstance(variants, list) or len(variants) != 2:
                continue
            others = [v for v in variants if v != {"type": "null"}]
            if len(others) != 1:
                continue
            del prop["anyOf"]
            prop.update(others[0])
            required.remove(name)
        if "required" in model and not required:
            del model["required"]
    return schema


def render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def dump(output: Path = DEFAULT_OUTPUT) -> None:
    output.write_text(render(openapi_schema()), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the schema (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args()
    dump(args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
