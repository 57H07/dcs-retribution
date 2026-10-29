"""DTOs of the settings screen (WEB-07.1), built from `game.commands.settings`."""

from __future__ import annotations

from enum import Enum
from typing import Union

from pydantic import BaseModel

from game.commands.settings import SettingEntry, SettingsPage, SettingsSection
from game.settings import Settings

# bool first: pydantic keeps JSON true/false as booleans, numbers as numbers.
SettingValueJs = Union[bool, int, float, str]


class SettingKindJs(str, Enum):
    BOOL = "bool"
    CHOICE = "choice"
    INT = "int"
    FLOAT = "float"
    MINUTES = "minutes"


class SettingJs(BaseModel):
    key: str
    label: str
    detail: str | None
    tooltip: str | None
    kind: SettingKindJs
    value: SettingValueJs
    default: SettingValueJs
    modified: bool
    min: float | None
    max: float | None
    step: float | None
    choices: list[str] | None

    class Config:
        title = "Setting"

    @staticmethod
    def from_entry(entry: SettingEntry, settings: Settings) -> SettingJs:
        return SettingJs(
            key=entry.key,
            label=entry.label,
            detail=entry.detail,
            tooltip=entry.tooltip,
            kind=SettingKindJs(entry.kind),
            value=entry.value(settings),
            default=entry.default,
            modified=entry.is_modified(settings),
            min=entry.min,
            max=entry.max,
            step=entry.step,
            choices=list(entry.choices) if entry.choices is not None else None,
        )


class SettingsSectionJs(BaseModel):
    name: str
    description: str | None
    settings: list[SettingJs]

    class Config:
        title = "SettingsSection"

    @staticmethod
    def from_section(section: SettingsSection, settings: Settings) -> SettingsSectionJs:
        return SettingsSectionJs(
            name=section.name,
            description=section.description,
            settings=[SettingJs.from_entry(e, settings) for e in section.entries],
        )


class SettingsPageJs(BaseModel):
    id: str
    name: str
    sections: list[SettingsSectionJs]

    class Config:
        title = "SettingsPage"

    @staticmethod
    def from_page(page: SettingsPage, settings: Settings) -> SettingsPageJs:
        return SettingsPageJs(
            id=page.id,
            name=page.name,
            sections=[
                SettingsSectionJs.from_section(s, settings) for s in page.sections
            ],
        )


class SettingsJs(BaseModel):
    pages: list[SettingsPageJs]

    class Config:
        title = "Settings"


class SettingValueUpdateJs(BaseModel):
    value: SettingValueJs

    class Config:
        title = "SettingValueUpdate"
