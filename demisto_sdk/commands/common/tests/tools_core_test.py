from pathlib import Path

import pytest

from demisto_sdk.commands.common.tools_core import find_pack_folder, string_to_bool


@pytest.mark.parametrize("value", ("true", "True", 1, "1", "yes", "y"))
def test_string_to_bool_true(value: str):
    assert string_to_bool(value)


@pytest.mark.parametrize("value", ("", None))
def test_string_to_bool_default_true(value: str):
    assert string_to_bool(value, True)


@pytest.mark.parametrize("value", ("false", "False", 0, "0", "n", "no"))
def test_string_to_bool_false(value: str):
    assert not string_to_bool(value)


@pytest.mark.parametrize("value", ("", " ", "כן", None, "None"))
def test_string_to_bool_error(value: str):
    with pytest.raises(ValueError):
        string_to_bool(value)


@pytest.mark.parametrize(
    "input_path,expected_output",
    [
        (
            Path("root/Packs/MyPack/Integrations/MyIntegration/MyIntegration.yml"),
            "root/Packs/MyPack",
        ),
        (Path("Packs/MyPack1/Scripts/MyScript/MyScript.py"), "Packs/MyPack1"),
        (Path("Packs/MyPack2/Scripts/MyScript"), "Packs/MyPack2"),
        (Path("Packs/MyPack3/Scripts"), "Packs/MyPack3"),
        (Path("Packs/MyPack4"), "Packs/MyPack4"),
    ],
)
def test_find_pack_folder(input_path, expected_output):
    output = find_pack_folder(input_path)
    assert expected_output == str(output)
