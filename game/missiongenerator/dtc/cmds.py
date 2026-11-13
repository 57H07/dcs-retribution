"""Countermeasure (CMDS) programs of a data cartridge (#221).

Each module stores its 10 programs (MAN 1-6, AUTO 1-3, BYPASS) in its own shape. A
`CmdsSchema` describes one: the programs, the fields the player may change, their
limits and the module's defaults, all taken from the module's DTC editor in
`CoreMods/aircraft/<type>/DTC/` (`CMDS_defs.lua` and the spin boxes of `CMDS.lua`).

The player's changes are kept as `{program: {field: value}}`; a program or field left
out keeps the module's default. `program_settings` turns them into the table the
cartridge carries, always whole, so the jet never reads a half-filled program.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

#: The player's changes: `{program id: {field id: value}}`.
CmdsValues = dict[str, dict[str, float]]


@dataclass(frozen=True)
class CmdsField:
    #: Identifier in `CmdsValues`, e.g. `chaff_quantity`.
    id: str
    label: str
    #: Where the module stores it: `CMDSProgramSettings[program][group][key]`.
    group: str
    key: str
    minimum: float
    maximum: float
    step: float

    @property
    def integer(self) -> bool:
        return float(self.step).is_integer()

    def check(self, value: float) -> float:
        """The value as the module stores it; ValueError when out of limits."""
        if not self.minimum <= value <= self.maximum:
            raise ValueError(
                f"{self.label} must be from {self.minimum:g} to {self.maximum:g}."
            )
        if self.integer:
            if not float(value).is_integer():
                raise ValueError(f"{self.label} must be a whole number.")
            return int(value)
        steps = round((value - self.minimum) / self.step)
        snapped = round(self.minimum + steps * self.step, 3)
        if abs(snapped - value) > 1e-6:
            raise ValueError(f"{self.label} goes by steps of {self.step:g}.")
        return snapped


@dataclass(frozen=True)
class CmdsSchema:
    #: Program id, as the module names it, and the label of the DTC editor.
    programs: tuple[tuple[str, str], ...]
    fields: tuple[CmdsField, ...]
    #: `CMDSProgramSettings` of the module's editor, every program whole.
    defaults: Mapping[str, Mapping[str, Mapping[str, float]]]

    def field(self, field_id: str) -> CmdsField:
        for f in self.fields:
            if f.id == field_id:
                return f
        raise ValueError(f"No CMDS setting {field_id}.")

    def default(self, program: str, field: CmdsField) -> float:
        return self.defaults[program][field.group][field.key]

    def values(self, changes: CmdsValues) -> CmdsValues:
        """Every field of every program: the player's value, else the default."""
        return {
            program: {
                f.id: changes.get(program, {}).get(f.id, self.default(program, f))
                for f in self.fields
            }
            for program, _ in self.programs
        }

    def clean(self, values: Mapping[str, Mapping[str, float]]) -> CmdsValues:
        """`values` checked, keeping only what differs from the module's defaults.

        ValueError names the first program or field out of limits.
        """
        known = dict(self.programs)
        changes: CmdsValues = {}
        for program, fields in values.items():
            if program not in known:
                raise ValueError(f"No CMDS program {program}.")
            for field_id, value in fields.items():
                f = self.field(field_id)
                try:
                    checked = f.check(float(value))
                except ValueError as error:
                    raise ValueError(f"{known[program]}: {error}") from error
                if checked != self.default(program, f):
                    changes.setdefault(program, {})[field_id] = checked
        return changes

    def program_settings(self, changes: CmdsValues) -> dict[str, Any]:
        """The module's `CMDSProgramSettings`, with the player's changes."""
        table: dict[str, Any] = copy.deepcopy(dict(self.defaults))
        for program, fields in changes.items():
            for field_id, value in fields.items():
                f = self.field(field_id)
                table[program][f.group][f.key] = value
        return table


# F/A-18C and F-14BU: the ALE-47 of both editors, same programs and defaults
# (`FA-18C/DTC/ALR67/CMDS_defs.lua`, `F14/DTC/CMDS/_defs.lua`).


def _ale47(chaff: int, repeat: int, interval: float, flare: int) -> dict[str, Any]:
    return {
        "Chaff": {"Quantity": chaff, "Repeat": repeat, "Interval": interval},
        "Flare": {"Quantity": flare},
        "Other1": {"Quantity": 0},
        "Other2": {"Quantity": 0},
    }


ALE47 = CmdsSchema(
    programs=(
        ("MAN_1", "MAN 1"),
        ("MAN_2", "MAN 2"),
        ("MAN_3", "MAN 3"),
        ("MAN_4", "MAN 4"),
        ("MAN_5", "MAN 5"),
        ("MAN_6", "MAN 6"),
        ("AUTO_1", "AUTO 1"),
        ("AUTO_2", "AUTO 2"),
        ("AUTO_3", "AUTO 3"),
        ("BYP", "BYPASS"),
    ),
    fields=(
        CmdsField("chaff_quantity", "Chaff", "Chaff", "Quantity", 0, 99, 1),
        CmdsField("chaff_repeat", "Repeat", "Chaff", "Repeat", 0, 99, 1),
        CmdsField("chaff_interval", "Interval (s)", "Chaff", "Interval", 0.25, 5, 0.25),
        CmdsField("flare_quantity", "Flares", "Flare", "Quantity", 0, 99, 1),
    ),
    defaults={
        "MAN_1": _ale47(1, 10, 1.0, 1),
        "MAN_2": _ale47(1, 10, 0.5, 1),
        "MAN_3": _ale47(2, 5, 1.0, 2),
        "MAN_4": _ale47(2, 10, 0.5, 2),
        "MAN_5": _ale47(1, 2, 1.0, 1),
        "MAN_6": _ale47(2, 20, 0.75, 2),
        "AUTO_1": _ale47(1, 4, 1.5, 0),
        "AUTO_2": _ale47(1, 6, 1.0, 0),
        "AUTO_3": _ale47(1, 8, 0.5, 0),
        "BYP": _ale47(2, 1, 1.0, 2),
    },
)


# F-16C: burst and salvo of each dispenser (`F-16C/DTC/MPD/CMDS_defs.lua`).


def _burst(quantity: int, interval: float, salvos: int, every: float) -> dict[str, Any]:
    return {
        "BurstQuantity": quantity,
        "BurstInterval": interval,
        "SalvoQuantity": salvos,
        "SalvoInterval": every,
    }


_NO_OTHER = _burst(0, 0.02, 0, 0.5)


def _viper(chaff: dict[str, Any], flare: dict[str, Any]) -> dict[str, Any]:
    return {
        "Chaff": chaff,
        "Flare": flare,
        "Other1": dict(_NO_OTHER),
        "Other2": dict(_NO_OTHER),
    }


def _same(quantity: int, interval: float, salvos: int, every: float) -> dict[str, Any]:
    return _viper(
        _burst(quantity, interval, salvos, every),
        _burst(quantity, interval, salvos, every),
    )


def _viper_fields(group: str, label: str) -> tuple[CmdsField, ...]:
    prefix = group.lower()
    return (
        CmdsField(
            f"{prefix}_burst_quantity", f"{label} BQ", group, "BurstQuantity", 0, 99, 1
        ),
        CmdsField(
            f"{prefix}_burst_interval",
            f"{label} BI (s)",
            group,
            "BurstInterval",
            0,
            10,
            0.001,
        ),
        CmdsField(
            f"{prefix}_salvo_quantity", f"{label} SQ", group, "SalvoQuantity", 0, 99, 1
        ),
        CmdsField(
            f"{prefix}_salvo_interval",
            f"{label} SI (s)",
            group,
            "SalvoInterval",
            0,
            10,
            0.01,
        ),
    )


_NO_FLARE = _burst(0, 0, 0, 0)

VIPER = CmdsSchema(
    programs=(
        ("MAN1", "MAN 1"),
        ("MAN2", "MAN 2"),
        ("MAN3", "MAN 3"),
        ("MAN4", "MAN 4"),
        ("MAN5", "MAN 5"),
        ("MAN6", "MAN 6"),
        ("AUTO1", "AUTO 1"),
        ("AUTO2", "AUTO 2"),
        ("AUTO3", "AUTO 3"),
        ("BYP", "BYPASS"),
    ),
    fields=_viper_fields("Chaff", "Chaff") + _viper_fields("Flare", "Flare"),
    defaults={
        "MAN1": _same(1, 0.02, 10, 1.0),
        "MAN2": _same(1, 0.02, 10, 0.5),
        "MAN3": _same(2, 0.1, 5, 1.0),
        "MAN4": _same(2, 0.1, 5, 0.5),
        "MAN5": _same(2, 0.05, 20, 0.75),
        "MAN6": _same(1, 0.02, 1, 0.5),
        "AUTO1": _viper(_burst(1, 0.02, 4, 1.5), dict(_NO_FLARE)),
        "AUTO2": _viper(_burst(1, 0.02, 6, 1.0), dict(_NO_FLARE)),
        "AUTO3": _viper(_burst(1, 0.02, 8, 0.5), dict(_NO_FLARE)),
        "BYP": _same(1, 0.02, 1, 0.5),
    },
)
