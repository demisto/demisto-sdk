from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import LISTS_DIR
from demisto_sdk.commands.common.tools import get_dict_from_file, pascal_case
from demisto_sdk.commands.prepare_content.list_unifier import ListUnifier, logger
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    LIST,
)
from TestSuite.test_tools import ChangeCWD


def create_split_list():
    list_json = LIST
    list_data = LIST["data"]
    list_json["data"] = "-"
    list_dir_name = Path(LISTS_DIR) / pascal_case(list_json["name"])
    return list_json, list_data, list_dir_name


def test_list_unify(repo):
    '''
    Given:
        - A list json file.
    When:
        - Running ListUnifier.unify on it.
    Then:
        - Ensure the list is unified as expected.
    '''
    pack = repo.create_pack("PackName")
    list_json, list_data, list_dir_name = create_split_list()
    list_dir_path = Path(pack.path) / list_dir_name
    list_dir_path.mkdir(parents=True, exist_ok=True)
    (list_dir_path / (list_dir_name.name + ".json")).write_text(str(list_json))
    (list_dir_path / (list_dir_name.name + "_data.css")).write_text(str(list_data))

    with ChangeCWD(pack.repo_path):
        list_unifier = ListUnifier.unify(
            path=list_dir_path / (list_dir_name.name + ".json"), data=list_json
        )
        assert list_unifier["data"] == list_data


@pytest.mark.parametrize("suffix", ["css", "json", "txt", "md", "csv", "html"])
def test_find_file_content_data(tmpdir, suffix):
    '''
    Given:
        - A data file with a suffix that is txt, json, css, md, csv or html.
    When:
        - Running `find_file_content_data` method.
    Then:
        - Ensure the path of the data file is returned.
    '''
    (Path(tmpdir) / f"_data.{suffix}").write_text("data")
    assert (
        ListUnifier.find_file_content_data(Path(tmpdir) / "_data")
        == Path(tmpdir) / f"_data.{suffix}"
    )


@pytest.mark.parametrize("suffix", ["jpg", "png", "gif", "bmp"])
def test_find_file_content_data_return_none(tmpdir, suffix):
    '''
    Given:
        - A data file with a suffix that is not txt, json, css, md, csv or html.
    When:
        - Running `find_file_content_data` method.
    Then:
        - Ensure None is returned.
    '''
    (Path(tmpdir) / f"_data.{suffix}").write_bytes(b"data")
    assert not ListUnifier.find_file_content_data(Path(tmpdir) / "_data")


def test_insert_data_to_json(tmpdir):
    '''
    Given:
        - A list (data section filled with a dash(-) or blank).
    When:
        - Running `insert_data_to_json` method.
    Then:
        - Ensure the data section is filled with the data from the data file.
    '''
    (Path(tmpdir) / "_data.txt").write_text("data")
    json_list = LIST
    json_list["data"] = "-"

    json_unified = ListUnifier.insert_data_to_json(
        json_list, Path(tmpdir) / "_data.txt"
    )
    assert json_unified["data"] == "data"


def test_insert_data_to_json_with_warning(mocker, tmpdir):
    '''
    Given:
        - A list with data section filled with something else than a dash(-) or blank.
    When:
        - Running `insert_data_to_json` method.
    Then:
        - Ensure the data section is filled with the data from the data file.
        - Ensure a warning is printed.
    '''
    mock_warning = mocker.patch.object(logger, "warning")
    list_dir_path = Path(tmpdir) / "Lists" / "TestList"
    list_dir_path.mkdir(parents=True, exist_ok=True)
    (list_dir_path / "_data.txt").write_text("data")
    json_list = LIST
    json_list["data"] = "test test test"

    json_unified = ListUnifier.insert_data_to_json(
        json_list, list_dir_path / "_data.txt"
    )
    assert json_unified["data"] == "data"
    assert mock_warning.call_count == 1
    mock_warning.assert_called_with(
        f"data section is not empty in {list_dir_path}/{list_dir_path.name}.json file. "
        f"It should be blank or a dash(-)."
    )
