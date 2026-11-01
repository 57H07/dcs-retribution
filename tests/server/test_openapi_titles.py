"""Two API models with one title silently share one generated client type."""

from collections import Counter

from game.server.app import app


def test_api_model_titles_are_unique() -> None:
    schemas = app.openapi()["components"]["schemas"]
    titles = Counter(schema.get("title", name) for name, schema in schemas.items())
    assert [title for title, count in titles.items() if count > 1] == []
