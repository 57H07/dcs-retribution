"""What the player sets in the data cartridge of a squadron's flights (#221).

Kept on the squadron, not on the flight: flights are planned anew each turn, the
squadron stays. Each player flight of the squadron gets a cartridge built with it
(`game/missiongenerator/dtc/`).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DtcSettings:
    #: The jet loads the cartridge at spawn; off, the pilot loads it from the DTC page.
    auto_load: bool = True
    #: Front lines and enemy air defenses on the displays (F-16C, F-14BU).
    threats: bool = True
    #: The CMDS programs changed from the module's defaults:
    #: `{program: {field: value}}`, see `game.missiongenerator.dtc.cmds`.
    cmds: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def is_default(self) -> bool:
        return self == DtcSettings()

    def copy(self) -> DtcSettings:
        return DtcSettings(
            auto_load=self.auto_load,
            threats=self.threats,
            cmds={program: dict(values) for program, values in self.cmds.items()},
        )
