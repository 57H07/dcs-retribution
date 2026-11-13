"""Reduced F10 markers: which ground objects keep their marker."""

from types import SimpleNamespace
from uuid import uuid4

from dcs.mapping import Point as DcsPoint
from dcs.terrain import Caucasus

from game.missiongenerator.marks import MarkFilter
from game.objectives import CampaignObjective, CampaignObjectives, ObjectiveKind
from game.utils import nautical_miles

TERRAIN = Caucasus()


def point(x_nm: float, y_nm: float = 0) -> DcsPoint:
    return DcsPoint(nautical_miles(x_nm).meters, nautical_miles(y_nm).meters, TERRAIN)


def control_point(front: bool = False) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), has_active_frontline=front)


def tgo(x_nm: float, cp: SimpleNamespace | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(), position=point(x_nm), control_point=cp or control_point()
    )


def game(
    reduced: bool = True,
    targets: tuple[object, ...] = (),
    objectives: list[CampaignObjective] | None = None,
) -> SimpleNamespace:
    # One front line along the y axis, at x = 0.
    front = SimpleNamespace(points=[point(0, -20), point(0, 20)])
    return SimpleNamespace(
        settings=SimpleNamespace(reduced_marks=reduced, reduced_marks_range_nm=30),
        theater=SimpleNamespace(conflicts=lambda: iter([front])),
        blue=SimpleNamespace(
            ato=SimpleNamespace(packages=[SimpleNamespace(target=t) for t in targets])
        ),
        objectives=CampaignObjectives(objectives=objectives or []),
    )


def test_every_ground_object_is_marked_by_default() -> None:
    assert MarkFilter(game(reduced=False)).marks(tgo(300))  # type: ignore[arg-type]


def test_reduced_marks_keep_the_ground_objects_near_the_front() -> None:
    marks = MarkFilter(game())  # type: ignore[arg-type]
    assert marks.marks(tgo(25))  # type: ignore[arg-type]
    assert not marks.marks(tgo(35))  # type: ignore[arg-type]


def test_reduced_marks_keep_package_targets() -> None:
    target = tgo(300)
    assert MarkFilter(game(targets=(target,))).marks(target)  # type: ignore[arg-type]


def test_reduced_marks_keep_the_ground_objects_of_front_bases() -> None:
    far = tgo(300, control_point(front=True))
    assert MarkFilter(game()).marks(far)  # type: ignore[arg-type]


def test_reduced_marks_keep_objective_targets() -> None:
    target = tgo(300)
    objective = CampaignObjective(
        title="Destroy",
        kind=ObjectiveKind.DESTROY,
        target="Squid",
        deadline=None,
        ground_object_ids=[target.id],
    )
    assert MarkFilter(game(objectives=[objective])).marks(target)  # type: ignore[arg-type]
