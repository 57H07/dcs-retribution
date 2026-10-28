"""GFX-01.3: widget colours come from the design tokens, not from qt_ui code.

Colours belong in resources/design/tokens.json and reach the widgets through
the stylesheets (theme_manager.set_style_class), theme_manager.token_color()
or the palette. This check fails on a colour literal in qt_ui/: a hex colour,
rgb()/hsl() or a CSS colour declaration inside a string, or a QColor / Qt
global colour built from a constant in code.

A line that genuinely needs a fixed colour (for instance a colour carried by
the game data) can be exempted with a trailing ``# colour-ok: <reason>``.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest

from qt_ui.design_tokens import REPO_ROOT

QT_UI_DIR = REPO_ROOT / "qt_ui"
EXEMPTION = "colour-ok:"

STRING_PATTERNS = [
    re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3}(?:[0-9a-fA-F]{2})?)?\b"),
    re.compile(r"\b(?:rgba?|hsla?)\s*\("),
    re.compile(
        r"(?<![\w-])(?:color|background(?:-color)?|border(?:-[a-z]+)?-color)"
        r"\s*:\s*(?!\s*(?:transparent|none|inherit)\b)[#\w]"
    ),
]

CODE_PATTERNS = [
    # QColor("white"), QColor("#fff"), QColor(52, 68, 85), QColor(Qt.red)...
    re.compile(r"\bQColor\(\s*(?:[\"'\d]|Qt\b|QtCore\b)"),
    re.compile(r"\bGlobalColor\.(?!transparent\b)"),
    re.compile(r"\bQColorConstants\b"),
]


def find_hardcoded_colours(source: str) -> list[tuple[int, str]]:
    """Returns (line number, offending text) for each colour literal."""
    exempt = {
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if f"# {EXEMPTION}" in line
    }
    found: list[tuple[int, str]] = []
    code_by_line: dict[int, list[str]] = {}
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        first, last = token.start[0], token.end[0]
        if token.type == tokenize.STRING:
            # A multi-line string can carry the exemption on any of its lines.
            if exempt.isdisjoint(range(first, last + 1)):
                for pattern in STRING_PATTERNS:
                    found.extend(
                        (first, m.group(0)) for m in pattern.finditer(token.string)
                    )
        elif token.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE):
            code_by_line.setdefault(first, []).append(token.string)
    for line, parts in code_by_line.items():
        if line in exempt:
            continue
        code = "".join(parts)
        for pattern in CODE_PATTERNS:
            found.extend((line, m.group(0)) for m in pattern.finditer(code))
    return sorted(found)


def qt_ui_sources() -> list[Path]:
    return sorted(QT_UI_DIR.rglob("*.py"))


def test_qt_ui_has_no_hardcoded_colour() -> None:
    offenders = []
    for path in qt_ui_sources():
        source = path.read_text(encoding="utf-8")
        for line, text in find_hardcoded_colours(source):
            offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{line}: {text}")
    assert not offenders, (
        "Hard-coded colours in qt_ui/ (use design tokens, see "
        "qt_ui/theme_manager.py):\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize(
    "source",
    [
        'label.setStyleSheet("color: white")',
        'label.setStyleSheet("color:orange")',
        "box.setStyleSheet(\"font-family: 'Courier New'; background: #1D2731;\")",
        'html = \'<a href="x" style="color: #ffffff">x</a>\'',
        "html = '<span style=\"color:#FFFFFF;\">x</span>'",
        'css = "QWidget { background-color: rgba(0, 0, 0, 0.5); }"',
        'painter.fillRect(rect, QtGui.QColor("#D3D3D3"))',
        "painter.setBrush(QtGui.QColor(52, 68, 85))",
        "serie.setColor(Qt.GlobalColor.red)",
        "fmt.setForeground(QtCore.Qt.GlobalColor.darkGray)",
        "pen = QPen(QColorConstants.White)",
    ],
)
def test_check_catches_hardcoded_colours(source: str) -> None:
    assert find_hardcoded_colours(source)


@pytest.mark.parametrize(
    "source",
    [
        'set_style_class(label, "text-warning")',
        'painter.setBrush(token_color("color-accent-default"))',
        "color = QColor(liberation_theme.get_token(name))",
        "brush = Qt.GlobalColor.transparent",
        'widget.setStyleSheet("QGroupBox { margin-right: 0px; border-left: 0px; }")',
        "# Issue #123, see colour: white in the old code\nx = 1",
        'log("Lost %d units, colour unknown", n)',
        'serie.setColor(QColor("#ff0000"))  # colour-ok: faction colour from data',
    ],
)
def test_check_accepts_tokens_and_exemptions(source: str) -> None:
    assert find_hardcoded_colours(source) == []
