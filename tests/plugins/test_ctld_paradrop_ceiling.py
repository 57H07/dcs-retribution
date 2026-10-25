"""The player paradrop ceiling is a CTLD plugin option (TRN-02, requirement 2)."""

from __future__ import annotations

from pathlib import Path

from game.plugins import LuaPluginManager
from game.plugins.luaplugin import LuaPlugin

CTLD_CONFIG = Path("resources/plugins/ctld/ctld-config.lua")


def _ctld() -> LuaPlugin:
    return next(
        p for p in LuaPluginManager.plugins() if p.definition.identifier == "ctld"
    )


def test_paradrop_ceiling_option_defaults_to_3000_ft() -> None:
    option = next(o for o in _ctld().options if o.identifier == "ctld.paradropMaxAglFt")
    assert option.get_value == 3000
    assert option.min is not None and option.min > 0
    assert option.max is not None and option.max >= 3000


def test_ctld_config_reads_paradrop_ceiling_option() -> None:
    lua = CTLD_CONFIG.read_text(encoding="utf-8")
    assert "dcsRetribution.plugins.ctld.paradropMaxAglFt" in lua
