from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.tools import get_dict_from_file, pascal_case
from demisto_sdk.commands.split.jsonsplitter import JsonSplitter
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    GENERIC_MODULE,
    LIST,
    UNIFIED_GENERIC_MODULE,
)
from TestSuite.test_tools import ChangeCWD

EXTRACTED_DASHBOARD = (
    UNIFIED_GENERIC_MODULE.get("views")[0].get("tabs")[0].get("dashboard")
)


def test_split_json(git_repo):
    """
    Given
        - Valid a unified generic module.

    When
        - Running split on it.

    Then
        - Ensure dashboard is extracted to the requested location.
        - Ensure the generic module file is edited properly in place.
    """
    pack = git_repo.create_pack("PackName")
    generic_module = pack.create_generic_module(
        "generic-module", UNIFIED_GENERIC_MODULE
    )
    json_splitter = JsonSplitter(
        input=generic_module.path, output=pack.path, file_type=FileType.GENERIC_MODULE
    )
    expected_dashboard_path = (
        str(pack.path) + "/" + EXTRACTED_DASHBOARD.get("name") + ".json"
    )

    with ChangeCWD(pack.repo_path):
        res = json_splitter.split_json()
        assert res == 0
        assert Path(expected_dashboard_path).is_file()

        with open(expected_dashboard_path) as f:
            result_dashboard = json.load(f)

        assert result_dashboard == EXTRACTED_DASHBOARD

        with open(generic_module.path) as f:
            result_generic_module = json.load(f)

        assert result_generic_module == GENERIC_MODULE


@pytest.mark.parametrize(
    "list_name, list_type, suffix, data",
    [
        ("test css", "css", ".css", "p {\n  color: red;\n  text-align: center;\n}"),
        ("test html", "html", ".html", "<h1>Hello World</h1>"),
        ("test txt", "text_plain", ".txt", "Hello World"),
        ("test markdown", "markdown", ".md", "# Hello World"),
        ("test json", "json", ".json", '{"name": "test"}'),
        ("test csv", "csv", ".txt", "name,value\ntest,test"),
    ],
)
def test_split_json_list(repo, list_name: str, list_type: str, suffix: str, data: str):
    """
    Given:
        - A list json file.
    When:
        - Running `JsonSplitter.split_json` on it.
    Then:
        - Ensure the specific list dir created.
        - Ensure the data file of the list with the extension matched has been created.
        - Ensure the data section in the json list file is filled with `-`.
    """
    pack = repo.create_pack("PackName")
    list_json = pack.create_list("test-list", LIST)
    list_json.update(
        {"id": list_name, "name": list_name, "type": list_type, "data": data}
    )
    json_splitter = JsonSplitter(
        input=list_json.path, output=pack.path, file_type=FileType.LISTS
    )

    folder_and_file_name = pascal_case(list_name)
    expected_list_path = (
        Path(pack.path) / "Lists" / folder_and_file_name / folder_and_file_name
    ).with_suffix(".json")

    with ChangeCWD(pack.repo_path):
        res = json_splitter.split_json()
        assert res == 0
        assert expected_list_path.is_file()
        assert (
            (expected_list_path.parent / f"{folder_and_file_name}_data")
            .with_suffix(suffix)
            .is_file()
        )
        assert get_dict_from_file(str(expected_list_path))[0]["data"] == "-"
