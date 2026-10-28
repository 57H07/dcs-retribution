"""Design tokens (GFX-01): one JSON file generating the Qt QSS and the map CSS.

``resources/design/tokens.json`` holds ``base`` tokens shared by every theme
variant and one tree per variant (``dark``, ``light``). A token path such as
``color.bg.canvas`` is exposed everywhere under its CSS variable name,
``--color-bg-canvas``:

* the map client gets ``client/src/theme/tokens.css``, which declares the
  variables on ``:root`` for each variant (selected by ``data-theme`` on the
  document element, the default variant applying when it is absent);
* Qt stylesheets have no variables, so ``theme.qss.template`` is written with
  ``var(--color-bg-canvas)`` placeholders that are substituted once per variant
  into ``resources/stylesheets/generated/retribution-<variant>.qss``.

The generated files are committed (the PyInstaller package and the client build
need no extra step) and a test fails when they are stale. Regenerate them with::

    python -m qt_ui.design_tokens

This module does not import Qt so that it can run in tests and build scripts.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKENS_PATH = Path("resources/design/tokens.json")
QSS_TEMPLATE_PATH = Path("resources/stylesheets/theme.qss.template")
GENERATED_QSS_DIR = Path("resources/stylesheets/generated")
MAP_CSS_PATH = Path("client/src/theme/tokens.css")

_PLACEHOLDER = re.compile(r"var\(\s*--([a-z0-9-]+)\s*\)")
_VALID_KEY = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

_HEADER = (
    "/* Generated from resources/design/tokens.json by qt_ui/design_tokens.py.\n"
    " * Do not edit: change the tokens and run `python -m qt_ui.design_tokens`. */\n"
)

#: A flattened variant: CSS variable name without the leading ``--`` -> value.
TokenSet = Dict[str, str]


@dataclass(frozen=True)
class DesignTokens:
    default_variant: str
    variants: Dict[str, TokenSet]

    def variant(self, name: str) -> TokenSet:
        try:
            return self.variants[name]
        except KeyError:
            raise ValueError(
                f"Unknown theme variant {name!r}; known: {sorted(self.variants)}"
            ) from None


def _flatten(tree: Mapping[str, Any], prefix: str = "") -> TokenSet:
    flat: TokenSet = {}
    for key, value in tree.items():
        if not _VALID_KEY.match(key):
            raise ValueError(
                f"Invalid token key {prefix + key!r}: use lower-case kebab-case"
            )
        name = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(_flatten(value, f"{name}-"))
        elif isinstance(value, str):
            flat[name] = value
        else:
            raise ValueError(f"Token {name!r} must be a string or an object")
    return flat


def parse_tokens(data: Mapping[str, Any]) -> DesignTokens:
    """Resolves the raw JSON document into one flat token set per variant."""
    base = _flatten(data.get("base", {}))
    raw_variants = data.get("variants", {})
    if not raw_variants:
        raise ValueError("The design tokens define no variant")
    variants = {name: {**base, **_flatten(tree)} for name, tree in raw_variants.items()}

    reference_name = sorted(variants)[0]
    reference = set(variants[reference_name])
    for name, tokens in variants.items():
        missing = reference - set(tokens)
        extra = set(tokens) - reference
        if missing or extra:
            raise ValueError(
                f"Theme variant {name!r} does not define the same tokens as "
                f"{reference_name!r}: missing {sorted(missing)}, "
                f"extra {sorted(extra)}"
            )

    default_variant = data.get("defaultVariant", reference_name)
    if default_variant not in variants:
        raise ValueError(f"Default theme variant {default_variant!r} is not defined")
    return DesignTokens(default_variant, variants)


def load_tokens(path: Path = REPO_ROOT / TOKENS_PATH) -> DesignTokens:
    with path.open(encoding="utf-8") as tokens_file:
        return parse_tokens(json.load(tokens_file))


def render_qss(template: str, tokens: Mapping[str, str]) -> str:
    """Substitutes every ``var(--name)`` of a QSS template with its token value."""
    unknown = sorted(
        {name for name in _PLACEHOLDER.findall(template) if name not in tokens}
    )
    if unknown:
        raise ValueError(f"Unknown design tokens in QSS template: {unknown}")
    return _HEADER + _PLACEHOLDER.sub(lambda match: tokens[match[1]], template)


def render_css(design: DesignTokens) -> str:
    """Renders the CSS variables of every variant for the map client."""
    blocks = []
    for name in sorted(design.variants):
        selector = f':root[data-theme="{name}"]'
        if name == design.default_variant:
            selector = f":root,\n{selector}"
        declarations = "".join(
            f"  --{token}: {value};\n"
            for token, value in sorted(design.variants[name].items())
        )
        blocks.append(f"{selector} {{\n{declarations}}}\n")
    return _HEADER + "\n" + "\n".join(blocks)


def qss_file_name(variant: str) -> str:
    return f"retribution-{variant}.qss"


def generated_files(root: Path = REPO_ROOT) -> Dict[Path, str]:
    """Returns the content of every generated file, keyed by repo-relative path."""
    design = load_tokens(root / TOKENS_PATH)
    template = (root / QSS_TEMPLATE_PATH).read_text(encoding="utf-8")
    files = {MAP_CSS_PATH: render_css(design)}
    for name in sorted(design.variants):
        files[GENERATED_QSS_DIR / qss_file_name(name)] = render_qss(
            template, design.variants[name]
        )
    return files


def write_generated_files(root: Path = REPO_ROOT) -> list[Path]:
    written = []
    for relative_path, content in generated_files(root).items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as output:
            output.write(content)
        written.append(relative_path)
    return written


def px_to_points(value: str) -> float:
    """Converts a ``"12px"`` token to Qt points (96 logical DPI, 72 pt per inch).

    Qt 6 scales logical pixels and points alike on high-DPI screens, so a font
    sized from a px token renders at the same physical size as the QSS rules.
    """
    if not value.endswith("px"):
        raise ValueError(f"Expected a px value, got {value!r}")
    return float(value[:-2]) * 72 / 96


def main() -> int:
    for path in write_generated_files():
        print(f"Wrote {path.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
