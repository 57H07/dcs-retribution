import pytest

from resources.tools.design_tokens import (
    REPO_ROOT,
    generated_files,
    load_tokens,
    parse_tokens,
    render_css,
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
            "`python -m resources.tools.design_tokens`"
        )


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
