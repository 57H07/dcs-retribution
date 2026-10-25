"""Data-driven ranks and decorations for player pilot careers (PER-03.3).

Rules live in YAML files (``resources/careers`` and the user's
``Retribution/Careers`` folder), one per country and/or period. A file looks
like::

    name: US Air Force
    countries: [USA]          # optional; omitted means any country
    from: 1947-09-18          # optional start of the period
    until: 2099-12-31         # optional end of the period
    ranks:                    # lowest first
      - name: Second Lieutenant
        abbreviation: 2nd Lt
      - name: First Lieutenant
        requires: {sorties: 10}
    decorations:
      - name: Ace
        description: Five aerial victories.
        requires: {air_kills: 5}

``requires`` maps logbook values (see ``STATISTICS``) to the minimum needed. An
empty or missing ``requires`` is met at once. Awards have no gameplay effect.
"""

from __future__ import annotations

import datetime
import logging
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

import yaml

from .pilot import Award, AwardKind, PilotRecord

if TYPE_CHECKING:
    from .airwing import AirWing

#: Logbook values usable in ``requires``.
STATISTICS: dict[str, Callable[[PilotRecord], float]] = {
    "sorties": lambda r: r.sorties,
    "combat_sorties": lambda r: r.combat_sorties,
    "air_kills": lambda r: r.air_kills,
    "ground_kills": lambda r: r.ground_kills,
    "naval_kills": lambda r: r.naval_kills,
    "total_kills": lambda r: r.total_kills,
    "deaths": lambda r: r.deaths,
    "flight_hours": lambda r: r.flight_time.total_seconds() / 3600,
}


def _requirements(data: Any, where: str) -> dict[str, float]:
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ValueError(f"{where}: requires must be a mapping")
    requirements = {}
    for stat, minimum in data.items():
        if stat not in STATISTICS:
            raise ValueError(
                f"{where}: unknown logbook value {stat!r}, expected one of "
                f"{', '.join(STATISTICS)}"
            )
        requirements[stat] = float(minimum)
    return requirements


@dataclass(frozen=True)
class AwardDefinition:
    kind: AwardKind
    name: str
    description: str = ""
    abbreviation: str = ""
    requires: Mapping[str, float] = field(default_factory=dict)

    def is_met_by(self, record: PilotRecord) -> bool:
        return all(
            STATISTICS[stat](record) >= minimum
            for stat, minimum in self.requires.items()
        )

    @classmethod
    def from_data(cls, kind: AwardKind, data: Any, where: str) -> AwardDefinition:
        if not isinstance(data, Mapping) or "name" not in data:
            raise ValueError(f"{where}: every {kind.value.lower()} needs a name")
        name = str(data["name"])
        return cls(
            kind,
            name,
            description=str(data.get("description", "")),
            abbreviation=str(data.get("abbreviation", "")),
            requires=_requirements(data.get("requires"), f"{where} ({name})"),
        )


def _date(value: Any, where: str) -> Optional[datetime.date]:
    if value is None:
        return None
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError as ex:
        raise ValueError(f"{where}: invalid date {value!r}") from ex


@dataclass(frozen=True)
class AwardRules:
    """The ranks and decorations of one country and/or period."""

    name: str
    #: DCS country names (``dcs.country.Country.name``); empty means any.
    countries: frozenset[str] = frozenset()
    start: Optional[datetime.date] = None
    end: Optional[datetime.date] = None
    #: Lowest rank first.
    ranks: tuple[AwardDefinition, ...] = ()
    decorations: tuple[AwardDefinition, ...] = ()

    def applies_to(self, country: str, day: datetime.date) -> bool:
        if self.countries and country not in self.countries:
            return False
        if self.start is not None and day < self.start:
            return False
        if self.end is not None and day > self.end:
            return False
        return True

    @property
    def specificity(self) -> tuple[bool, bool]:
        """Rules naming a country beat rules naming only a period."""
        return bool(self.countries), self.start is not None or self.end is not None

    def evaluate(
        self, record: PilotRecord, turn: int, date: datetime.datetime
    ) -> list[Award]:
        """Grants every rank and decoration newly earned; returns them.

        Ranks are granted in order, so a pilot skipping a grade still gets the
        grades in between in their history. Each award is granted once.
        """
        granted = []
        for definition in (*self.ranks, *self.decorations):
            if record.has_award(definition.kind, definition.name):
                continue
            if not definition.is_met_by(record):
                continue
            award = Award(
                definition.kind,
                definition.name,
                turn,
                date,
                definition.description,
            )
            record.awards.append(award)
            granted.append(award)
        return granted

    @classmethod
    def from_data(cls, data: Any, where: str) -> AwardRules:
        if not isinstance(data, Mapping):
            raise ValueError(f"{where}: expected a mapping")
        countries = data.get("countries") or []
        if isinstance(countries, str):
            countries = [countries]
        return cls(
            name=str(data.get("name", where)),
            countries=frozenset(str(c) for c in countries),
            start=_date(data.get("from"), where),
            end=_date(data.get("until"), where),
            ranks=tuple(
                AwardDefinition.from_data(AwardKind.Rank, r, where)
                for r in data.get("ranks") or []
            ),
            decorations=tuple(
                AwardDefinition.from_data(AwardKind.Decoration, d, where)
                for d in data.get("decorations") or []
            ),
        )

    @classmethod
    def from_file(cls, path: Path) -> AwardRules:
        with path.open(encoding="utf-8") as rules_file:
            return cls.from_data(yaml.safe_load(rules_file), str(path))


def load_rules(directories: Iterable[Path]) -> list[AwardRules]:
    """Loads every ``*.yaml`` of the directories; invalid files are skipped."""
    rules = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            try:
                rules.append(AwardRules.from_file(path))
            except (OSError, ValueError, yaml.YAMLError):
                logging.exception(f"Could not load career rules from {path}")
    return rules


def rules_directories() -> Iterator[Path]:
    from game import persistency

    yield persistency.base_path() / "Retribution" / "Careers"
    yield Path("resources/careers")


@cache
def default_rules() -> tuple[AwardRules, ...]:
    return tuple(load_rules(rules_directories()))


def rules_for(
    rules: Iterable[AwardRules], country: str, day: datetime.date
) -> Optional[AwardRules]:
    """The most specific rules for the country and day; the first wins ties."""
    best: Optional[AwardRules] = None
    for candidate in rules:
        if not candidate.applies_to(country, day):
            continue
        if best is None or candidate.specificity > best.specificity:
            best = candidate
    return best


def award_careers(
    air_wing: AirWing,
    turn: int,
    date: datetime.datetime,
    rules: Optional[Iterable[AwardRules]] = None,
) -> list[tuple[str, Award]]:
    """Evaluates the awards of every player pilot of the air wing.

    Returns ``(pilot name, award)`` for each award granted.
    """
    from .career import careers

    all_rules = tuple(default_rules() if rules is None else rules)
    granted = []
    for career in careers(air_wing):
        country_rules = rules_for(all_rules, career.squadron.country.name, date.date())
        if country_rules is None:
            continue
        for award in country_rules.evaluate(career.logbook, turn, date):
            granted.append((career.pilot.name, award))
    return granted
