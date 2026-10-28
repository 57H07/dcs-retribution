import json
from pathlib import Path

import pytest

from qt_ui import liberation_theme
from qt_ui.design_tokens import (
    REPO_ROOT,
    generated_files,
    load_tokens,
    parse_tokens,
    px_to_points,
    render_css,
    render_qss,
)


def test_every_token_is_defined_in_both_variants() -> None:
    design = load_tokens()
    assert set(design.variants) == {"dark", "light"}
    assert design.variant("dark").keys() == design.variant("light").keys()
    for tokens in design.variants.values():
        for category in ("color-", "font-", "space-", "radius-"):
            assert any(name.startswith(category) for name in tokens), category


def test_dark_is_the_default_variant() -> None:
    assert load_tokens().default_variant == "dark"


def test_generation_is_deterministic() -> None:
    assert generated_files() == generated_files()


def test_generated_files_are_up_to_date() -> None:
    for relative_path, content in generated_files().items():
        committed = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert committed == content, (
            f"{relative_path.as_posix()} is stale: run "
            "`python -m qt_ui.design_tokens`"
        )


def test_generated_qss_has_no_placeholder_left() -> None:
    for relative_path, content in generated_files().items():
        if relative_path.suffix == ".qss":
            assert "var(--" not in content


def test_variant_missing_a_token_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing"):
        parse_tokens(
            {
                "base": {"space": {"sm": "4px"}},
                "variants": {
                    "dark": {"color": {"bg": "#000", "text": "#fff"}},
                    "light": {"color": {"bg": "#fff"}},
                },
            }
        )


def test_invalid_token_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="kebab-case"):
        parse_tokens({"variants": {"dark": {"color": {"bgCanvas": "#000"}}}})


def test_qss_template_substitution() -> None:
    tokens = {"color-bg": "#123456", "space-sm": "4px"}
    qss = render_qss(
        "QWidget { background: var(--color-bg); padding: var( --space-sm ); }", tokens
    )
    assert "QWidget { background: #123456; padding: 4px; }" in qss


def test_unknown_token_in_qss_template_is_rejected() -> None:
    with pytest.raises(ValueError, match="color-nope"):
        render_qss("QWidget { color: var(--color-nope); }", {})


def test_css_declares_default_variant_on_root() -> None:
    design = parse_tokens(
        {
            "defaultVariant": "dark",
            "base": {"radius": {"sm": "2px"}},
            "variants": {
                "dark": {"color": {"bg": "#000"}},
                "light": {"color": {"bg": "#fff"}},
            },
        }
    )
    css = render_css(design)
    assert ':root,\n:root[data-theme="dark"] {\n  --color-bg: #000;\n' in css
    assert (
        ':root[data-theme="light"] {\n  --color-bg: #fff;\n  --radius-sm: 2px;\n}'
        in css
    )


def test_px_to_points() -> None:
    assert px_to_points("12px") == 9
    with pytest.raises(ValueError):
        px_to_points("9pt")


def test_every_theme_has_a_stylesheet_and_token_variant() -> None:
    variants = load_tokens().variants
    for theme in liberation_theme.THEMES.values():
        assert (REPO_ROOT / "resources/stylesheets" / theme["themeFile"]).is_file()
        assert theme["tokenVariant"] in variants


def test_theme_indices_stay_stable() -> None:
    names = {i: t["themeName"] for i, t in liberation_theme.THEMES.items()}
    assert names == {0: "Vanilla", 1: "DCS World", 2: "Dark", 3: "Light"}


@pytest.fixture
def theme_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_fresh_install_starts_dark(theme_dir: Path) -> None:
    liberation_theme.init(theme_dir / "missing_preferences.json")
    assert liberation_theme.get_theme_name() == "Dark"
    assert liberation_theme.get_token_variant() == "dark"
    assert not (theme_dir / liberation_theme.THEME_PREFERENCES_FILE_PATH).exists()


def test_existing_install_without_saved_theme_keeps_dcs_world(
    theme_dir: Path,
) -> None:
    preferences = theme_dir / "retribution_preferences.json"
    preferences.write_text("{}")
    liberation_theme.init(preferences)
    assert liberation_theme.get_theme_name() == "DCS World"
    saved = json.loads(
        (theme_dir / liberation_theme.THEME_PREFERENCES_FILE_PATH).read_text()
    )
    assert saved == {"theme_index": 1}


def test_saved_theme_is_kept(theme_dir: Path) -> None:
    (theme_dir / liberation_theme.THEME_PREFERENCES_FILE_PATH).write_text(
        json.dumps({"theme_index": 0})
    )
    liberation_theme.init(theme_dir / "missing_preferences.json")
    assert liberation_theme.get_theme_name() == "Vanilla"
