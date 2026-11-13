"""#221: the CMDS programs of a cartridge, checked against the module's editor."""

import pytest

from game.missiongenerator.dtc.cmds import ALE47, VIPER


def test_every_program_has_every_field_by_default() -> None:
    for schema in (ALE47, VIPER):
        values = schema.values({})
        assert set(values) == {program for program, _ in schema.programs}
        for program in values.values():
            assert set(program) == {f.id for f in schema.fields}


def test_the_defaults_are_those_of_the_module_editor() -> None:
    assert ALE47.values({})["MAN_6"] == {
        "chaff_quantity": 2,
        "chaff_repeat": 20,
        "chaff_interval": 0.75,
        "flare_quantity": 2,
    }
    assert VIPER.values({})["MAN5"]["chaff_burst_interval"] == 0.05


def test_clean_keeps_only_what_differs_from_the_defaults() -> None:
    changes = ALE47.clean(
        {"MAN_1": {"chaff_quantity": 1, "flare_quantity": 4}, "MAN_2": {}}
    )
    assert changes == {"MAN_1": {"flare_quantity": 4}}


def test_clean_refuses_values_out_of_the_limits_of_the_module() -> None:
    with pytest.raises(ValueError, match="MAN 1: Chaff must be from 0 to 99"):
        ALE47.clean({"MAN_1": {"chaff_quantity": 120}})
    with pytest.raises(ValueError, match="steps of 0.25"):
        ALE47.clean({"MAN_1": {"chaff_interval": 0.3}})
    with pytest.raises(ValueError, match="whole number"):
        VIPER.clean({"MAN1": {"chaff_salvo_quantity": 2.5}})
    with pytest.raises(ValueError, match="No CMDS program"):
        VIPER.clean({"MAN_1": {"chaff_salvo_quantity": 2}})
    with pytest.raises(ValueError, match="No CMDS setting"):
        VIPER.clean({"MAN1": {"chaff_repeat": 2}})


def test_program_settings_never_change_the_defaults() -> None:
    ALE47.program_settings({"MAN_1": {"chaff_quantity": 9}})
    assert ALE47.values({})["MAN_1"]["chaff_quantity"] == 1
