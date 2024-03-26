from __future__ import annotations

import builtins
import logging
import os
import shutil
from io import TextIOWrapper
from pathlib import Path
from typing import Callable, Tuple

import demisto_client
import pytest
from urllib3.response import HTTPResponse

from demisto_sdk.commands.common.constants import (
    DEMISTO_BASE_URL,
    DEMISTO_KEY,
    JOBS_DIR,
    LAYOUTS_DIR,
    LISTS_DIR,
    PRE_PROCESS_RULES_DIR,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.tests.tools_test import SENTENCE_WITH_UMLAUTS
from demisto_sdk.commands.common.tools import get_child_files
from demisto_sdk.commands.download.downloader import *
from TestSuite.playbook import Playbook
from TestSuite.test_tools import str_in_call_args_list

TESTS_DATA_FOLDER = Path(__file__).parent / "tests_data"
TESTS_ENV_FOLDER = Path(__file__).parent / "tests_env"


@pytest.fixture(autouse=True)
def set_env_vars():
    # Avoid missing environment variables errors
    os.environ[DEMISTO_BASE_URL] = "https://fake-xsoar-server.com"
    os.environ[DEMISTO_KEY] = "fake_api_key"
    yield
    os.environ.pop(DEMISTO_BASE_URL, None)
    os.environ.pop(DEMISTO_KEY, None)


def load_test_data(file_name: str, folder: str | None = None) -> dict:
    """
    A function for loading and returning data from json files within the "test_data" folder.

    Args:
        file_name (str): Name of a json file to load data from.
        folder (str | None, optional): Name of the parent folder of the file within `test_data`. Defaults to None.

    Returns:
        dict: Dictionary data loaded from the json file.
    """
    if folder:
        path = TESTS_DATA_FOLDER / folder / f"{file_name}.json"

    else:
        path = TESTS_DATA_FOLDER / f"{file_name}.json"

    with open(path, "r") as f:
        return json.load(f)


class Environment:
    """
    Environment is class designed to spin up a virtual, temporary content repo and build all objects related to
    the Downloader (such as pack content & custom content)
    """

    def __init__(self, tmp_path):
        self.tmp_path = Path(tmp_path)
        tests_path: Path = self.tmp_path / "tests"
        tests_env_path: Path = tests_path / "tests_env"
        tests_data_path: Path = tests_path / "tests_data"
        shutil.copytree(src=str(TESTS_ENV_FOLDER), dst=str(tests_env_path))
        shutil.copytree(
            src=str(TESTS_DATA_FOLDER),
            dst=str(tests_data_path),
        )

        self.CONTENT_BASE_PATH = tests_path / "tests_env" / "content"
        self.CUSTOM_CONTENT_BASE_PATH = tests_path / "tests_data" / "custom_content"
        self.PACK_INSTANCE_PATH = self.CONTENT_BASE_PATH / "Packs" / "TestPack"
        self.INTEGRATION_INSTANCE_PATH = (
            self.PACK_INSTANCE_PATH / "Integrations" / "TestIntegration"
        )
        self.SCRIPT_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Scripts" / "TestScript"
        self.PLAYBOOK_INSTANCE_PATH = (
            self.PACK_INSTANCE_PATH / "Playbooks" / "playbook-DummyPlaybook.yml"
        )
        self.LAYOUT_INSTANCE_PATH = (
            self.PACK_INSTANCE_PATH / "Layouts" / "layout-details-TestLayout.json"
        )
        self.LAYOUTSCONTAINER_INSTANCE_PATH = (
            self.PACK_INSTANCE_PATH / "Layouts" / "layoutscontainer-mytestlayout.json"
        )
        self.PRE_PROCESS_RULES_INSTANCE_PATH = (
            self.PACK_INSTANCE_PATH / "PreProcessRules/preprocessrule-dummy.json"
        )
        self.LISTS_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Lists" / "list-dummy.json"
        self.JOBS_INSTANCE_PATH = self.PACK_INSTANCE_PATH / "Jobs" / "job-sample.json"
        self.CUSTOM_CONTENT_SCRIPT_PATH = (
            self.CUSTOM_CONTENT_BASE_PATH / "automation-TestScript.yml"
        )
        self.CUSTOM_CONTENT_INTEGRATION_PATH = (
            self.CUSTOM_CONTENT_BASE_PATH / "integration-Test_Integration.yml"
        )
        self.CUSTOM_CONTENT_LAYOUT_PATH = (
            self.CUSTOM_CONTENT_BASE_PATH / "layout-details-TestLayout.json"
        )
        self.CUSTOM_CONTENT_PLAYBOOK_PATH = (
            self.CUSTOM_CONTENT_BASE_PATH / "playbook-DummyPlaybook.yml"
        )
        self.CUSTOM_CONTENT_JS_INTEGRATION_PATH = (
            self.CUSTOM_CONTENT_BASE_PATH / "integration-DummyJSIntegration.yml"
        )
        self.CUSTOM_API_RESPONSE = self.CUSTOM_CONTENT_BASE_PATH / "api-response"

        self.INTEGRATION_PACK_OBJECT = {
            "Test Integration": [
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": self.INTEGRATION_INSTANCE_PATH / "TestIntegration.py",
                    "file_extension": "py",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": self.INTEGRATION_INSTANCE_PATH / "TestIntegration_testt.py",
                    "file_extension": "py",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": self.INTEGRATION_INSTANCE_PATH / "TestIntegration.yml",
                    "file_extension": "yml",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": self.INTEGRATION_INSTANCE_PATH
                    / "TestIntegration_image.png",
                    "file_extension": "png",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": self.INTEGRATION_INSTANCE_PATH / "CHANGELOG.md",
                    "file_extension": "md",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": self.INTEGRATION_INSTANCE_PATH
                    / "TestIntegration_description.md",
                    "file_extension": "md",
                },
                {
                    "name": "Test Integration",
                    "id": "Test Integration",
                    "path": self.INTEGRATION_INSTANCE_PATH / "README.md",
                    "file_extension": "md",
                },
            ]
        }
        self.SCRIPT_PACK_OBJECT = {
            "TestScript": [
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": self.SCRIPT_INSTANCE_PATH / "TestScript.py",
                    "file_extension": "py",
                },
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": self.SCRIPT_INSTANCE_PATH / "TestScript.yml",
                    "file_extension": "yml",
                },
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": self.SCRIPT_INSTANCE_PATH / "CHANGELOG.md",
                    "file_extension": "md",
                },
                {
                    "name": "TestScript",
                    "id": "TestScript",
                    "path": self.SCRIPT_INSTANCE_PATH / "README.md",
                    "file_extension": "md",
                },
            ]
        }
        self.PLAYBOOK_PACK_OBJECT = {
            "DummyPlaybook": [
                {
                    "name": "DummyPlaybook",
                    "id": "DummyPlaybook",
                    "path": self.PLAYBOOK_INSTANCE_PATH,
                    "file_extension": "yml",
                }
            ]
        }
        self.LAYOUT_PACK_OBJECT = {
            "Hello World Alert": [
                {
                    "name": "Hello World Alert",
                    "id": "Hello World Alert",
                    "path": self.LAYOUT_INSTANCE_PATH,
                    "file_extension": "json",
                }
            ]
        }
        self.LAYOUTSCONTAINER_PACK_OBJECT = {
            "mylayout": [
                {
                    "name": "mylayout",
                    "id": "mylayout",
                    "path": self.LAYOUTSCONTAINER_INSTANCE_PATH,
                    "file_extension": "json",
                }
            ]
        }
        self.PRE_PROCESS_RULES_PACK_OBJECT = {
            "DummyPreProcessRule": [
                {
                    "name": "DummyPreProcessRule",
                    "id": "DummyPreProcessRule",
                    "path": self.PRE_PROCESS_RULES_INSTANCE_PATH,
                    "file_extension": "json",
                }
            ]
        }
        self.LISTS_PACK_OBJECT = {
            "DummyList": [
                {
                    "name": "DummyList",
                    "id": "DummyList",
                    "path": self.LISTS_INSTANCE_PATH,
                    "file_extension": "json",
                }
            ]
        }
        self.JOBS_PACK_OBJECT = {
            "DummyJob": [
                {
                    "name": "DummyJob",
                    "id": "DummyJob",
                    "path": self.JOBS_INSTANCE_PATH,
                    "file_extension": "json",
                }
            ]
        }

        self.PACK_CONTENT = {
            INTEGRATIONS_DIR: self.INTEGRATION_PACK_OBJECT,
            SCRIPTS_DIR: self.SCRIPT_PACK_OBJECT,
            PLAYBOOKS_DIR: self.PLAYBOOK_PACK_OBJECT,
            LAYOUTS_DIR: {
                **self.LAYOUT_PACK_OBJECT,
                **self.LAYOUTSCONTAINER_PACK_OBJECT,
            },
        }

        self.INTEGRATION_CUSTOM_CONTENT_OBJECT = {
            "id": "Test Integration",
            "file_name": "integration-Test_Integration.yml",
            "name": "Test Integration",
            "entity": "Integrations",
            "type": FileType.INTEGRATION,
            "file_extension": "yml",
            "code_lang": "python",
            "file": StringIO(self.CUSTOM_CONTENT_INTEGRATION_PATH.read_text()),
        }
        self.SCRIPT_CUSTOM_CONTENT_OBJECT = {
            "id": "f1e4c6e5-0d44-48a0-8020-a9711243e918",
            "file_name": "script-TestScript.yml",
            "name": "TestScript",
            "entity": "Scripts",
            "type": FileType.SCRIPT,
            "file_extension": "yml",
            "code_lang": "python",
            "file": StringIO(self.CUSTOM_CONTENT_SCRIPT_PATH.read_text()),
        }
        self.PLAYBOOK_CUSTOM_CONTENT_OBJECT = {
            "id": "DummyPlaybook",
            "file_name": "DummyPlaybook.yml",
            "name": "DummyPlaybook",
            "entity": "Playbooks",
            "type": FileType.PLAYBOOK,
            "file_extension": "yml",
            "file": StringIO(self.CUSTOM_CONTENT_PLAYBOOK_PATH.read_text()),
        }
        self.LAYOUT_CUSTOM_CONTENT_OBJECT = {
            "id": "Hello World Alert",
            "file_name": "layout-details-TestLayout.json",
            "name": "Hello World Alert",
            "entity": "Layouts",
            "type": FileType.LAYOUT,
            "file_extension": "json",
            "file": StringIO(self.CUSTOM_CONTENT_LAYOUT_PATH.read_text()),
        }
        self.JS_INTEGRATION_CUSTOM_CONTENT_OBJECT = {
            "id": "SumoLogic",
            "name": "SumoLogic",
            "entity": "Integrations",
            "type": FileType.INTEGRATION,
            "file_extension": "yml",
            "code_lang": "javascript",
            "file": StringIO(self.CUSTOM_CONTENT_JS_INTEGRATION_PATH.read_text()),
        }

        self.CUSTOM_CONTENT = [
            self.INTEGRATION_CUSTOM_CONTENT_OBJECT,
            self.SCRIPT_CUSTOM_CONTENT_OBJECT,
            self.PLAYBOOK_CUSTOM_CONTENT_OBJECT,
            self.LAYOUT_CUSTOM_CONTENT_OBJECT,
            self.JS_INTEGRATION_CUSTOM_CONTENT_OBJECT,
        ]


class TestHelperMethods:
    def test_get_custom_content_objects(self, tmp_path, mocker):
        expected_results = load_test_data(
            file_name="tar_custom_content_objects", folder="expected_results"
        )
        env = Environment(tmp_path)
        downloader = Downloader()

        mock_bundle_data = (
            TESTS_DATA_FOLDER / "custom_content" / "download_tar.tar.gz"
        ).read_bytes()
        mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)
        mocker.patch.object(
            demisto_client,
            "generic_request_func",
            return_value=(mock_bundle_response, None, None),
        )

        downloader.custom_content_temp_dir = env.CUSTOM_CONTENT_BASE_PATH
        custom_content_data = downloader.download_custom_content()
        custom_content_objects = downloader.parse_custom_content_data(
            file_name_to_content_item_data=custom_content_data
        )

        for item in custom_content_objects.values():
            item.pop("file")
            item["type"] = item["type"].value

        assert custom_content_objects == expected_results

    @pytest.mark.parametrize(
        "name, output",
        [
            ("test", "test"),
            ("automation-demisto", "script-demisto"),
            ("playbook-demisto", "demisto"),
        ],
    )
    def test_update_file_prefix(self, name, output):
        downloader = Downloader()
        assert downloader.update_file_prefix(name) == output
        assert not downloader.update_file_prefix(name).startswith("playbook-")

    @pytest.mark.parametrize(
        "name", ["GSM", "G S M", "G_S_M", "G-S-M", "G S_M", "G_S-M"]
    )
    def test_create_dir_name(self, name):
        downloader = Downloader()
        assert downloader.create_directory_name(name) == "GSM"


class TestFlags:
    def test_missing_output_flag(self, mocker):
        """
        Given: A downloader object
        When: The user tries to download a system item without specifying the output flag
        Then: Ensure downloader returns a '1' error code and logs the error
        """
        downloader = Downloader(input=("test",))
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        assert downloader.download() == 1
        assert str_in_call_args_list(
            logger_error.call_args_list,
            "Error: Missing required parameter '-o' / '--output'.",
        )

    def test_missing_input_flag_system(self, mocker):
        """
        Given: A downloader object
        When: The user tries to download a system item without specifying any input flag
        Then: Ensure downloader returns a '1' error code and logs the error
        """
        downloader = Downloader(output="Output", input=tuple(), system=True)
        mocker.patch.object(Downloader, "verify_output_path", return_value=True)
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        assert downloader.download() == 1
        assert str_in_call_args_list(
            logger_info.call_args_list,
            "Error: Missing required parameter for downloading system items: '-i' / '--input'.",
        )

    def test_missing_input_flag_custom(self, mocker):
        """
        Given: A downloader object
        When: The user tries to download a custom content item without specifying any input flag
        Then: Ensure downloader returns a '1' error code and logs the error
        """
        downloader = Downloader(
            output="Output",
            input=tuple(),
            regex=None,
            all_custom_content=False,
            system=False,
        )
        mocker.patch.object(Downloader, "verify_output_path", return_value=True)
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        assert downloader.download() == 1
        assert str_in_call_args_list(
            logger_info.call_args_list,
            "Error: No input parameter has been provided ('-i' / '--input', '-r' / '--regex', '-a' / '--all).",
        )

    def test_missing_item_type(self, mocker):
        """
        Given: A downloader object
        When: The user tries to download a system item without specifying the item type
        Then: Ensure downloader.verify_flags() returns False and logs the error
        """
        downloader = Downloader(
            output="Output", input=("My Playbook",), system=True, item_type=None
        )
        mocker.patch.object(Downloader, "verify_output_path", return_value=True)
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        assert downloader.download() == 1
        assert str_in_call_args_list(
            logger_info.call_args_list,
            "Error: Missing required parameter for downloading system items: '-it' / '--item-type'.",
        )

    def test_all_flag(self, tmp_path, mocker):
        """
        Given: A downloader object
        When: The user tries to download all content items
        Then: Ensure all content items are downloaded
        """
        env = Environment(tmp_path)
        downloader = Downloader(
            all_custom_content=True, output=str(env.CONTENT_BASE_PATH)
        )

        mock_bundle_data = (
            TESTS_DATA_FOLDER / "custom_content" / "download_tar.tar.gz"
        ).read_bytes()
        mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)
        mocker.patch.object(
            demisto_client,
            "generic_request_func",
            return_value=(mock_bundle_response, None, None),
        )

        custom_content_data = downloader.download_custom_content()
        custom_content_objects = downloader.parse_custom_content_data(
            file_name_to_content_item_data=custom_content_data
        )
        filtered_custom_content_objects = downloader.filter_custom_content(
            custom_content_objects=custom_content_objects
        )

        # We subtract one since there is one JS script in the testing content bundle that is skipped during filtration.
        assert len(custom_content_data) - 1 == len(filtered_custom_content_objects)

    def test_init_flag(self, tmp_path, mocker):
        """
        Given: A downloader object
        When: The user uses the init flag in order to initialize a new pack
        Then: Ensure the pack is properly initialized
        """
        env = Environment(tmp_path)
        mock = mocker.patch.object(
            builtins, "input", side_effect=("test_pack_name", "n", "n")
        )

        downloader = Downloader(output=str(env.CONTENT_BASE_PATH), init=True)
        initialized_path = downloader.initialize_output_path(
            root_folder=env.CONTENT_BASE_PATH
        )

        assert mock.call_count == 3
        assert initialized_path == env.CONTENT_BASE_PATH / "Packs" / "test_pack_name"
        assert (initialized_path / "pack_metadata.json").exists()
        assert not (initialized_path / "Integrations").exists()
        for file in initialized_path.iterdir():
            assert not file.is_dir()


class TestBuildPackContent:
    def test_build_existing_pack_structure(self, tmp_path):
        env = Environment(tmp_path)
        test_path = Path(env.PACK_INSTANCE_PATH)
        downloader = Downloader(output=str(test_path))
        result = downloader.build_existing_pack_structure(existing_pack_path=test_path)
        expected_result = env.PACK_CONTENT
        assert len(result) == len(expected_result)

        for entity, items in expected_result.items():
            assert len(result[entity]) == len(items)

            for content_item_name, content_item_data in items.items():
                assert content_item_name in result[entity]
                assert sorted(content_item_data, key=lambda x: x["path"]) == sorted(
                    result[entity][content_item_name], key=lambda x: x["path"]
                )

    def test_build_pack_content_object(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "entity": INTEGRATIONS_DIR,
                "path": env.INTEGRATION_INSTANCE_PATH,
                "out": env.INTEGRATION_PACK_OBJECT,
            },
            {
                "entity": SCRIPTS_DIR,
                "path": env.SCRIPT_INSTANCE_PATH,
                "out": env.SCRIPT_PACK_OBJECT,
            },
            {
                "entity": PLAYBOOKS_DIR,
                "path": env.PLAYBOOK_INSTANCE_PATH,
                "out": env.PLAYBOOK_PACK_OBJECT,
            },
            {
                "entity": LAYOUTS_DIR,
                "path": env.LAYOUT_INSTANCE_PATH,
                "out": env.LAYOUT_PACK_OBJECT,
            },
            {
                "entity": LAYOUTS_DIR,
                "path": env.LAYOUTSCONTAINER_INSTANCE_PATH,
                "out": env.LAYOUTSCONTAINER_PACK_OBJECT,
            },
            {
                "entity": PRE_PROCESS_RULES_DIR,
                "path": env.PRE_PROCESS_RULES_INSTANCE_PATH,
                "out": [],
            },
            {"entity": LISTS_DIR, "path": env.LISTS_INSTANCE_PATH, "out": []},
            {"entity": JOBS_DIR, "path": env.JOBS_INSTANCE_PATH, "out": []},
        ]
        downloader = Downloader()
        for param in parameters:
            result = downloader.build_pack_content_object(
                content_entity=param["entity"],
                entity_instance_path=Path(param["path"]),
            )

            if result is None:
                assert param["out"] == []

            else:
                file_name, pack_content_object = result
                assert sorted(pack_content_object, key=lambda x: x["path"]) == sorted(
                    list(param["out"].values())[0], key=lambda x: x["path"]
                )

    def test_get_main_file_details(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "entity": INTEGRATIONS_DIR,
                "path": env.INTEGRATION_INSTANCE_PATH,
                "main_id": "Test Integration",
                "main_name": "Test Integration",
            },
            {
                "entity": LAYOUTS_DIR,
                "path": env.LAYOUT_INSTANCE_PATH,
                "main_id": "Hello World Alert",
                "main_name": "Hello World Alert",
            },
        ]
        downloader = Downloader()
        for param in parameters:
            data = downloader.get_metadata_file(
                content_type=param["entity"], content_item_path=param["path"]
            )
            assert param["main_id"] == get_id(file_content=data)
            assert param["main_name"] == get_display_name(
                file_path=param["path"], file_data=data
            )


class TestBuildCustomContent:
    def test_build_custom_content_object(self, tmp_path):
        env = Environment(tmp_path)
        parameters = [
            {
                "path": env.CUSTOM_CONTENT_SCRIPT_PATH,
                "output_custom_content_object": env.SCRIPT_CUSTOM_CONTENT_OBJECT,
            },
            {
                "path": env.CUSTOM_CONTENT_INTEGRATION_PATH,
                "output_custom_content_object": env.INTEGRATION_CUSTOM_CONTENT_OBJECT,
            },
            {
                "path": env.CUSTOM_CONTENT_LAYOUT_PATH,
                "output_custom_content_object": env.LAYOUT_CUSTOM_CONTENT_OBJECT,
            },
            {
                "path": env.CUSTOM_CONTENT_PLAYBOOK_PATH,
                "output_custom_content_object": env.PLAYBOOK_CUSTOM_CONTENT_OBJECT,
            },
        ]
        downloader = Downloader()
        for param in parameters:
            with open(param["path"], "rb") as file:
                loaded_file = StringIO(safe_read_unicode(file.read()))

            result = downloader.create_content_item_object(
                file_name=param["path"].name, file_data=loaded_file
            )

            # Assure these keys exist, and skip testing them
            # ('file' is StringIO bytes representation, and 'data' is the parsed file in dictionary format)
            assert "data" in result
            result.pop("data")
            assert "file" in result
            result.pop("file")
            param["output_custom_content_object"].pop("file")

            assert result == param["output_custom_content_object"]


class TestDownloadExistingFile:
    def test_download_and_extract_existing_file(self, tmp_path):
        env = Environment(tmp_path)
        downloader = Downloader(force=True)

        file_name = env.INTEGRATION_CUSTOM_CONTENT_OBJECT["file_name"]

        env.INTEGRATION_CUSTOM_CONTENT_OBJECT["data"] = get_file_details(
            file_content=env.INTEGRATION_CUSTOM_CONTENT_OBJECT["file"].getvalue(),
            full_file_path=str(env.CUSTOM_CONTENT_INTEGRATION_PATH),
        )

        assert downloader.write_files_into_output_path(
            downloaded_content_objects={
                file_name: env.INTEGRATION_CUSTOM_CONTENT_OBJECT
            },
            existing_pack_structure=env.PACK_CONTENT,
            output_path=env.PACK_INSTANCE_PATH,
        )

        expected_paths = [
            file["path"]
            for file in env.INTEGRATION_PACK_OBJECT[
                env.INTEGRATION_CUSTOM_CONTENT_OBJECT["name"]
            ]
        ]

        for path in expected_paths:
            assert Path(path).is_file()

        yml_data = get_yaml(env.INTEGRATION_PACK_OBJECT["Test Integration"][2]["path"])
        for field in KEEP_EXISTING_YAML_FIELDS:
            obj = yml_data
            dotted_path_list = field.split(".")
            for path_part in dotted_path_list:
                if path_part != dotted_path_list[-1]:
                    obj = obj.get(path_part)
                else:
                    assert obj.get(path_part)
        with open(
            env.INTEGRATION_PACK_OBJECT["Test Integration"][5]["path"]
        ) as description_file:
            description_data = description_file.read()
        assert "Test Integration Long Description TEST" in description_data
        with open(
            env.INTEGRATION_PACK_OBJECT["Test Integration"][0]["path"]
        ) as code_file:
            code_data = code_file.read()
        assert "# TEST" in code_data

    def test_download_existing_no_force_skip(self, tmp_path):
        """
        Given: A Downloader object
        When: The user tries to download a file that already exists in the pack, without using the 'force' flag.
        Then: Ensure the download of the file is skipped
        """
        env = Environment(tmp_path)
        downloader = Downloader(force=True)

        file_name = env.INTEGRATION_CUSTOM_CONTENT_OBJECT["file_name"]

        assert not downloader.write_files_into_output_path(
            downloaded_content_objects={
                file_name: env.INTEGRATION_CUSTOM_CONTENT_OBJECT
            },
            existing_pack_structure=env.PACK_CONTENT,
            output_path=env.PACK_INSTANCE_PATH,
        )

    def test_download_existing_file_playbook(self, tmp_path):
        """
        Given: A Downloader object
        When: Downloading a playbook that already exists in the pack, using the 'force' flag.
        Then: Ensure the download of the file is successful, and that the 'fromversion' and 'toversion' fields
            from the existing file are kept (even though they are not in the new file).
        """
        env = Environment(tmp_path)
        downloader = Downloader()
        file_name = env.PLAYBOOK_CUSTOM_CONTENT_OBJECT["file_name"]
        file_path = env.PLAYBOOK_INSTANCE_PATH

        playbook_data = get_file_details(
            file_content=env.PLAYBOOK_CUSTOM_CONTENT_OBJECT["file"],
            full_file_path=str(file_path),
        )

        playbook_data.pop("fromversion")
        playbook_data.pop("toversion")

        env.PLAYBOOK_CUSTOM_CONTENT_OBJECT["file"] = StringIO(yaml.dumps(playbook_data))

        assert downloader.write_files_into_output_path(
            downloaded_content_objects={file_name: env.PLAYBOOK_CUSTOM_CONTENT_OBJECT},
            existing_pack_structure=env.PACK_CONTENT,
            output_path=env.PACK_INSTANCE_PATH,
        )
        assert file_path.is_file()
        data = get_yaml(file_path)
        assert "fromversion" in data and data["fromversion"] == "TEST"
        assert "toversion" in data and data["toversion"] == "TEST"

    def test_download_existing_file_layout(self, tmp_path):
        """
        Given: A Downloader object
        When: Downloading a layout that already exists in the pack, using the 'force' flag.
        Then: Ensure the download of the file is successful, and that the 'fromversion' and 'toversion' fields
            from the existing file are kept (even though they are not in the new file).
        """
        env = Environment(tmp_path)
        downloader = Downloader(force=True)
        file_name = env.LAYOUT_CUSTOM_CONTENT_OBJECT["file_name"]
        file_path = env.LAYOUT_INSTANCE_PATH

        layout_data = get_file_details(
            file_content=env.LAYOUT_CUSTOM_CONTENT_OBJECT["file"].getvalue(),
            full_file_path=str(file_path),
        )

        layout_data.pop("fromVersion")
        layout_data.pop("toVersion")

        env.LAYOUT_CUSTOM_CONTENT_OBJECT["file"] = StringIO(json.dumps(layout_data))

        assert downloader.write_files_into_output_path(
            downloaded_content_objects={file_name: env.LAYOUT_CUSTOM_CONTENT_OBJECT},
            existing_pack_structure=env.PACK_CONTENT,
            output_path=env.PACK_INSTANCE_PATH,
        )
        assert file_path.is_file()
        data = get_yaml(file_path)
        assert "fromVersion" in data and data["fromVersion"] == "5.0.0"
        assert "toVersion" in data and data["toVersion"] == "5.9.9"

    def test_update_data_yml(self, tmp_path):
        env = Environment(tmp_path)
        downloader = Downloader()
        downloader.preserve_fields(
            file_to_update=env.CUSTOM_CONTENT_INTEGRATION_PATH,
            original_file=env.INTEGRATION_INSTANCE_PATH / "TestIntegration.yml",
            is_yaml=True,
        )
        file_data = get_yaml(env.CUSTOM_CONTENT_INTEGRATION_PATH)

        for field in KEEP_EXISTING_YAML_FIELDS:
            nested_keys = field.split(".")

            if len(nested_keys) > 1:
                iterated_value = file_data.get(nested_keys[0])

                for key in nested_keys[1:]:
                    assert iterated_value.get(key)
                    iterated_value = file_data[key]

            else:
                assert file_data.get(field)

    def test_update_data_json(self, tmp_path):
        env = Environment(tmp_path)
        downloader = Downloader()
        downloader.preserve_fields(
            file_to_update=env.CUSTOM_CONTENT_LAYOUT_PATH,
            original_file=env.LAYOUT_INSTANCE_PATH,
            is_yaml=False,
        )
        file_data: dict = get_json(env.CUSTOM_CONTENT_LAYOUT_PATH)

        for field in KEEP_EXISTING_JSON_FIELDS:
            nested_keys = field.split(".")

            if len(nested_keys) > 1:
                iterated_value = file_data.get(nested_keys[0])

                for key in nested_keys[1:]:
                    assert iterated_value.get(key)
                    iterated_value = file_data[key]

            else:
                assert file_data.get(field)


class TestDownloadNewFile:
    def test_download_and_extract_new_integration_file(self, tmp_path):
        env = Environment(tmp_path)
        raw_files = [
            "output_path/basename.py",
            "output_path/basename.yml",
            "output_path/basename_image.png",
            "output_path/basename_description.md",
            "output_path/README.md",
        ]

        temp_dir = (
            env.tmp_path / "temp_dir_test_download_and_extract_new_integration_file"
        )
        env.INTEGRATION_CUSTOM_CONTENT_OBJECT["data"] = get_file_details(
            file_content=env.INTEGRATION_CUSTOM_CONTENT_OBJECT["file"].getvalue(),
            full_file_path=str(env.CUSTOM_CONTENT_INTEGRATION_PATH),
        )

        downloader = Downloader(output=str(temp_dir))
        file_name = env.INTEGRATION_CUSTOM_CONTENT_OBJECT["file_name"]
        basename = downloader.create_directory_name(
            env.INTEGRATION_CUSTOM_CONTENT_OBJECT["name"]
        )
        output_dir_path = (
            temp_dir / env.INTEGRATION_CUSTOM_CONTENT_OBJECT["entity"] / basename
        )
        output_dir_path.mkdir(parents=True)

        files = [
            file.replace("output_path", str(output_dir_path)).replace(
                "basename", basename
            )
            for file in raw_files
        ]

        assert downloader.write_files_into_output_path(
            downloaded_content_objects={
                file_name: env.INTEGRATION_CUSTOM_CONTENT_OBJECT
            },
            existing_pack_structure={},
            output_path=temp_dir,
        )

        output_files = get_child_files(output_dir_path)
        assert sorted(output_files) == sorted(files)

    def test_download_and_extract_new_script_file(self, tmp_path):
        env = Environment(tmp_path)
        raw_files = [
            "output_path/basename.py",
            "output_path/basename.yml",
            "output_path/README.md",
        ]

        temp_dir = env.tmp_path / "temp_dir_test_download_and_extract_new_script_file"
        env.SCRIPT_CUSTOM_CONTENT_OBJECT["data"] = get_file_details(
            file_content=env.SCRIPT_CUSTOM_CONTENT_OBJECT["file"].getvalue(),
            full_file_path=str(env.CUSTOM_CONTENT_INTEGRATION_PATH),
        )

        downloader = Downloader(output=str(temp_dir))
        file_name = env.SCRIPT_CUSTOM_CONTENT_OBJECT["file_name"]
        basename = downloader.create_directory_name(
            env.SCRIPT_CUSTOM_CONTENT_OBJECT["name"]
        )
        output_dir_path = (
            temp_dir / env.SCRIPT_CUSTOM_CONTENT_OBJECT["entity"] / basename
        )
        output_dir_path.mkdir(parents=True)

        files = [
            file.replace("output_path", str(output_dir_path)).replace(
                "basename", basename
            )
            for file in raw_files
        ]

        assert downloader.write_files_into_output_path(
            downloaded_content_objects={file_name: env.SCRIPT_CUSTOM_CONTENT_OBJECT},
            existing_pack_structure={},
            output_path=temp_dir,
        )

        output_files = get_child_files(output_dir_path)
        assert sorted(output_files) == sorted(files)

    def test_download_new_file_playbook(self, tmp_path):
        env = Environment(tmp_path)
        output_path = env.tmp_path / "test_download_new_file_playbook"

        downloader = Downloader(output=str(output_path))
        file_name = env.PLAYBOOK_CUSTOM_CONTENT_OBJECT["file_name"]

        assert downloader.write_files_into_output_path(
            downloaded_content_objects={file_name: env.PLAYBOOK_CUSTOM_CONTENT_OBJECT},
            existing_pack_structure={},
            output_path=output_path,
        )
        expected_file_path = (
            output_path
            / env.PLAYBOOK_CUSTOM_CONTENT_OBJECT["entity"]
            / "DummyPlaybook.yml"
        )
        assert expected_file_path.is_file()
        assert get_yaml(env.CUSTOM_CONTENT_PLAYBOOK_PATH) == get_yaml(
            expected_file_path
        )

    def test_download_new_file_layout(self, tmp_path):
        env = Environment(tmp_path)
        output_path = env.tmp_path / "test_download_new_file_layout"

        file_name = env.LAYOUT_CUSTOM_CONTENT_OBJECT["file_name"]

        downloader = Downloader(output=str(output_path))
        assert downloader.write_files_into_output_path(
            downloaded_content_objects={file_name: env.LAYOUT_CUSTOM_CONTENT_OBJECT},
            existing_pack_structure={},
            output_path=output_path,
        )
        expected_file_path = (
            output_path
            / env.LAYOUT_CUSTOM_CONTENT_OBJECT["entity"]
            / "layout-details-TestLayout.json"
        )
        assert expected_file_path.is_file()
        assert get_json(env.CUSTOM_CONTENT_LAYOUT_PATH) == get_json(expected_file_path)


class TestVerifyPackPath:
    @pytest.mark.parametrize(
        "output_path, expected_result",
        [
            ("Integrations", False),
            ("Packs/TestPack/", True),
            ("Demisto", False),
            ("Packs", False),
            ("Packs/TestPack", True),
        ],
    )
    def test_verify_output_path_is_pack(self, tmp_path, output_path, expected_result):
        env = Environment(tmp_path)
        output_path = Path(f"{env.CONTENT_BASE_PATH}/{output_path}")
        assert (
            Downloader().verify_output_path(output_path=output_path) == expected_result
        )


@pytest.mark.parametrize(
    "input_content, item_type, insecure, expected_endpoint, expected_request_method, expected_request_body",
    [
        (
            ("PB1", "PB2"),
            "Playbook",
            False,
            "/playbook/search",
            "GET",
            {"query": "name:PB1 or PB2"},
        ),
        (
            ("Mapper1", "Mapper2"),
            "Mapper",
            True,
            "/classifier/search",
            "POST",
            {"query": "name:Mapper1 or Mapper2"},
        ),
        (("Field1", "Field2"), "Field", True, "/incidentfields", "GET", {}),
        (
            ("Classifier1", "Classifier2"),
            "Classifier",
            False,
            "/classifier/search",
            "POST",
            {"query": "name:Classifier1 or Classifier2"},
        ),
    ],
)
def test_build_req_params(
    input_content: tuple[str],
    item_type: str,
    insecure: bool,
    expected_endpoint: str,
    expected_request_method: str,
    expected_request_body: dict,
    monkeypatch,
):
    downloader = Downloader(
        system=True, input=input_content, item_type=item_type, insecure=insecure
    )
    endpoint, request_type, request_body = downloader.build_request_params(
        content_item_type=ContentItemType(item_type),
        content_item_names=list(input_content),
    )
    assert endpoint == expected_endpoint
    assert request_type == expected_request_method
    assert request_body == expected_request_body


@pytest.mark.parametrize(
    "content_item, content_type, expected_result",
    [
        ({"name": "name 1"}, ContentItemType.PLAYBOOK, "name_1.yml"),
        ({"name": "name 1"}, ContentItemType.FIELD, "name_1.json"),
        (
            {"name": "name with / slash in it"},
            ContentItemType.PLAYBOOK,
            "name_with_slash_in_it.yml",
        ),
        ({"id": "id 1"}, ContentItemType.FIELD, "id_1.json"),
    ],
)
def test_generate_system_content_file_name(
    content_item: dict, content_type: ContentItemType, expected_result: str
):
    downloader = Downloader()

    downloader.system_item_type = content_type
    file_name = downloader.generate_system_content_file_name(
        content_item_type=content_type,
        content_item=content_item,
    )

    assert file_name == expected_result


@pytest.mark.parametrize("source_is_unicode", (True, False))
@pytest.mark.parametrize(
    "suffix,dumps_method,write_method,fields",
    (
        (
            ".json",
            json.dumps,
            lambda f, data: json.dump(data, f),
            ("fromVersion", "toVersion"),
        ),
        (
            ".yml",
            yaml.dumps,
            lambda f, data: yaml.dump(data, f),
            ("fromversion", "toversion"),
        ),
    ),
)
def test_safe_write_unicode_to_non_unicode(
    tmp_path: Path,
    suffix: str,
    dumps_method: Callable,
    write_method: Callable[[TextIOWrapper, dict], None],
    source_is_unicode: bool,
    fields: Tuple[
        str, str
    ],  # not all field names are merged, and they depend on the file type
) -> None:
    """
    Given: A format to check (yaml/json), with its writing method
    When: Calling Downloader.update_data
    Then:
        1. Make sure that downloading unicode content into a non-unicode file works (result should be all unicode)
        2. Make sure that downloading non-unicode content into a unicode file works (result should be all unicode)
    """
    from demisto_sdk.commands.download.downloader import Downloader

    non_unicode_path = (tmp_path / "non_unicode").with_suffix(suffix)
    with non_unicode_path.open("wb") as f:
        f.write(
            dumps_method({fields[0]: SENTENCE_WITH_UMLAUTS}).encode(
                "latin-1", "backslashreplace"
            )
        )
    assert "ü" in non_unicode_path.read_text(
        encoding="latin-1"
    )  # assert it was written as latin-1

    unicode_path = (tmp_path / "unicode").with_suffix(suffix)
    with open(unicode_path, "w") as f:
        write_method(f, {fields[1]: SENTENCE_WITH_UMLAUTS})
    assert "ü" in unicode_path.read_text(
        encoding="utf-8"
    )  # assert the content was written as unicode

    source, dest = (
        (unicode_path, non_unicode_path)
        if source_is_unicode
        else (
            non_unicode_path,
            unicode_path,
        )
    )

    Downloader.preserve_fields(
        file_to_update=dest, original_file=source, is_yaml=(suffix == ".yml")
    )

    # make sure the two files were merged correctly
    result = get_file(dest)
    assert set(result.keys()) == set(fields)
    assert set(result.values()) == {SENTENCE_WITH_UMLAUTS}


def test_uuids_replacement_in_content_items(mocker):
    """
    Given:
        A mock tar file download_tar.tar
    When:
        Running the download command with "auto_replace_uuids" set to true
    Then:
        Assure UUIDs are properly mapped and replaced.
    """
    expected_mapping = {
        "e4c2306d-5d4b-4b19-8320-6fdad94595d4": "custom_automation",
        "de57b1f7-b754-43d2-8a8c-379d12bdddcd": "custom_script",
        "84731e69-0e55-40f9-806a-6452f97a01a0": "Custom Layout",
        "4d45f0d7-5fdd-4a4b-8f1e-5f2502f90a61": "ExampleType",
        "a53a2f17-2f05-486d-867f-a36c9f5b88d4": "custom_playbook",
    }

    mock_bundle_data = (
        TESTS_DATA_FOLDER / "custom_content" / "download_tar.tar.gz"
    ).read_bytes()
    mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)
    mocker.patch.object(
        demisto_client,
        "generic_request_func",
        return_value=(mock_bundle_response, None, None),
    )

    downloader = Downloader(
        all_custom_content=True,
        auto_replace_uuids=True,
    )

    all_custom_content_data = downloader.download_custom_content()
    all_custom_content_objects = downloader.parse_custom_content_data(
        file_name_to_content_item_data=all_custom_content_data
    )

    uuid_mapping = downloader.create_uuid_to_name_mapping(
        custom_content_objects=all_custom_content_objects
    )
    assert uuid_mapping == expected_mapping

    changed_uuids_count = 0
    for file_object in all_custom_content_objects.values():
        if downloader.replace_uuid_ids_for_item(
            custom_content_object=file_object, uuid_mapping=uuid_mapping
        ):
            changed_uuids_count += 1

    assert changed_uuids_count == 7


@pytest.mark.parametrize("content_item_name", ("Test: Test", "[Test] Test"))
def test_uuids_replacement_in_content_items_with_special_character_names(
    repo, mocker, content_item_name: str
):
    """
    Given: A YAML-based content item name that contains special YAML characters
          (that requires wrapping the string quotes)
    When: Calling 'self.replace_uuid_ids' method.
    Then: Ensure that the UUIDs are replaced properly and that the update YAML file is valid.
    """
    repo = repo.create_pack()
    playbook_data = {
        "name": content_item_name,
        "id": "d470522f-0a68-43c7-a62f-224f04b2e0c9",
    }
    playbook: Playbook = repo.create_playbook(yml=playbook_data)

    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")

    downloader = Downloader(
        all_custom_content=True,
        auto_replace_uuids=True,
    )

    file_name = playbook.obj_path.name
    file_object = downloader.create_content_item_object(
        file_name=file_name,
        file_data=StringIO(safe_read_unicode(playbook.obj_path.read_bytes())),
        _loaded_data=playbook_data,
    )
    custom_content_objects = {file_name: file_object}

    uuid_mapping = downloader.create_uuid_to_name_mapping(
        custom_content_objects=custom_content_objects
    )
    downloader.replace_uuid_ids(
        custom_content_objects=custom_content_objects, uuid_mapping=uuid_mapping
    )
    # Assert no warnings logged (error raised by 'get_file_details' in 'replace_uuid_ids_for_item' if YAML is invalid)
    assert logger_warning.call_count == 0
    # Assert ID value is always in quotes
    assert f"id: '{file_object['name']}'" in file_object["file"].getvalue()


@pytest.mark.parametrize("quote_type", ("'", '"'))
def test_uuids_replacement_in_content_items_with_quoted_id_field(
    repo, mocker, quote_type: str
):
    """
    Given: A YAML-based content item, with the ID surrounded in quotes on the file
    When: Calling 'self.replace_uuid_ids' method.
    Then: Ensure that the replaced ID is properly surrounded by quotes and doesn't have duplicate quotes.
    """
    repo = repo.create_pack()
    playbook_data = {"id": "d470522f-0a68-43c7-a62f-224f04b2e0c9", "name": "Test"}
    playbook: Playbook = repo.create_playbook(yml=playbook_data)

    with playbook.obj_path.open("w") as f:
        f.write(
            f"id: {quote_type}{playbook_data['id']}{quote_type}\nname: {playbook_data['name']}"
        )

    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")

    downloader = Downloader(
        all_custom_content=True,
        auto_replace_uuids=True,
    )

    file_name = playbook.obj_path.name
    file_object = downloader.create_content_item_object(
        file_name=file_name,
        file_data=StringIO(safe_read_unicode(playbook.obj_path.read_bytes())),
        _loaded_data=playbook_data,
    )
    custom_content_objects = {file_name: file_object}

    uuid_mapping = downloader.create_uuid_to_name_mapping(
        custom_content_objects=custom_content_objects
    )
    downloader.replace_uuid_ids(
        custom_content_objects=custom_content_objects, uuid_mapping=uuid_mapping
    )
    # Assert no warnings logged (error raised by 'get_file_details' in 'replace_uuid_ids_for_item' if YAML is invalid)
    assert logger_warning.call_count == 0
    # Assert ID value is always in quotes
    assert (
        file_object["file"].getvalue().splitlines()[0] == f"id: '{file_object['name']}'"
    )


def test_get_system_playbooks(mocker):
    """
    Given:
        A name of a playbook to download.
    When:
        Using the download command.
    Then:
        Ensure the function works as expected and returns the playbook.
    """
    playbook_path = TESTS_DATA_FOLDER / "playbook-DummyPlaybook2.yml"
    mocker.patch.object(
        demisto_client,
        "generic_request_func",
        return_value=(
            HTTPResponse(body=playbook_path.read_bytes(), status=200),
            200,
            None,
        ),
    )

    downloader = Downloader(
        system=True, input=("DummyPlaybook",), item_type="Playbook", output="test"
    )

    downloaded_playbooks = downloader.fetch_system_content(
        content_item_type=ContentItemType.PLAYBOOK, content_item_names=["DummyPlaybook"]
    )
    assert isinstance(downloaded_playbooks, dict)
    assert len(downloaded_playbooks) == 1
    assert downloaded_playbooks["DummyPlaybook.yml"]["data"] == get_yaml(playbook_path)


def test_get_system_playbooks_item_does_not_exist_by_name(mocker):
    """
    Given:
        A name of a playbook to download using the API.
    When:
        Using the download command, but the API call returns "Item not found" error for the playbook.
    Then:
        Ensure that the function tries to retrieve the playbook its ID instead.
    """
    playbook_path = TESTS_DATA_FOLDER / "playbook-DummyPlaybook2.yml"

    generic_request_func_mock = mocker.patch.object(
        demisto_client,
        "generic_request_func",
        side_effect=(
            ApiException(),
            (HTTPResponse(body=playbook_path.read_bytes(), status=200), 200, None),
        ),
    )

    downloader = Downloader(
        input=("DummyPlaybook-DifferentNameThanID",), output="DummyPlaybook"
    )

    get_playbook_id_by_playbook_name_mock = mocker.patch.object(
        downloader, "get_playbook_id_by_playbook_name", return_value="DummyPlaybook"
    )
    downloaded_playbooks = downloader.fetch_system_content(
        content_item_type=ContentItemType.PLAYBOOK,
        content_item_names=["DummyPlaybook-DifferentNameThanID"],
    )

    assert get_playbook_id_by_playbook_name_mock.call_count == 1
    assert generic_request_func_mock.call_count == 2
    assert (
        generic_request_func_mock.call_args_list[0][0][1]
        == "/playbook/DummyPlaybook-DifferentNameThanID/yaml"
    )
    assert (
        generic_request_func_mock.call_args_list[1][0][1]
        == "/playbook/DummyPlaybook/yaml"
    )

    assert isinstance(downloaded_playbooks, dict)
    assert len(downloaded_playbooks) == 1
    assert downloaded_playbooks["DummyPlaybook.yml"]["data"] == get_yaml(playbook_path)


def test_get_system_playbooks_non_api_failure(mocker):
    """
    Given: a mock exception
    When: calling get_system_playbooks function.
    Then: Ensure that when the API call throws a non-ApiException error,
          a second attempt is not made to retrieve the playbook by the ID.
    """
    mocker.patch.object(demisto_client, "generic_request_func", side_effect=Exception())
    downloader = Downloader(input=("Test",))

    get_playbook_id_by_playbook_name_spy = mocker.spy(
        downloader, "get_playbook_id_by_playbook_name"
    )
    results = downloader.get_system_playbooks(content_items=["Test"])

    assert get_playbook_id_by_playbook_name_spy.call_count == 0
    assert results == {}


def test_get_system_playbooks_api_failure(mocker):
    """
    Given: a mock exception
    When: calling get_system_playbooks function.
    Then: Ensure that when the API call throws an ApiException error and the id extraction fails,
          the function raises the same error.
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    mocker.patch.object(
        demisto_client,
        "generic_request_func",
        side_effect=ApiException(status="403", reason="Test Error Message"),
    )
    downloader = Downloader(input=("Test",))

    get_playbook_id_by_playbook_name_spy = mocker.patch.object(
        downloader, "get_playbook_id_by_playbook_name", return_value=None
    )

    results = downloader.get_system_playbooks(content_items=["Test"])

    assert get_playbook_id_by_playbook_name_spy.call_count == 1
    assert str_in_call_args_list(
        call_args_list=logger_error.call_args_list,
        required_str="Failed to fetch system playbook 'Test': (403)\nReason: Test Error Message\n",
    )
    assert str_in_call_args_list(
        call_args_list=logger_info.call_args_list,
        required_str="No system playbooks were downloaded.",
    )
    assert results == {}


def test_list_files_flag(mocker):
    """
    Given:
        list_files flag (-lf / --list-files) is set to True (and only that. Other flags are not required)
    When:
        Running the Download command
    Then:
        Ensure the command list all files available for download properly.
    """
    downloader = Downloader(list_files=True)
    mock_bundle_data = (
        TESTS_DATA_FOLDER / "custom_content" / "download_tar.tar.gz"
    ).read_bytes()
    mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)

    mocker.patch.object(
        demisto_client,
        "generic_request_func",
        return_value=(mock_bundle_response, None, None),
    )

    list_file_method_mock = mocker.spy(downloader, "list_all_custom_content")
    content_table_mock = mocker.spy(downloader, "create_custom_content_table")
    assert downloader.download() == 0

    expected_table = (
        "Content Name                Content Type\n"
        "--------------------------  ----------------\n"
        "CommonServerUserPowerShell  script\n"
        "CommonServerUserPython      script\n"
        "custom_automation           script\n"
        "custom_script               script\n"
        "custom_incident             incidentfield\n"
        "Custom_Layout               incidenttype\n"
        "custom_integration          integration\n"
        "Custom Layout               layoutscontainer\n"
        "ExampleType                 layoutscontainer\n"
        "custom_playbook             playbook"
    )

    assert list_file_method_mock.call_count == 1
    assert content_table_mock.call_count == 1
    assert expected_table in content_table_mock.spy_return


@pytest.mark.parametrize(
    "auto_replace_uuids",
    [True, False],
)
def test_auto_replace_uuids_flag(mocker, auto_replace_uuids: bool):
    """
    Given: auto_replace_uuids value.
    When: Downloading custom content items
    Then:
        - Ensure that when 'auto_replace_uuids' is set to true, the 'replace_uuid_ids' method is called.
        - Ensure that when 'auto_replace_uuids' is set to false, the 'replace_uuid_ids' method is not called.
    """
    mock_bundle_data = (
        TESTS_DATA_FOLDER / "custom_content" / "download_tar.tar.gz"
    ).read_bytes()
    mock_bundle_response = HTTPResponse(body=mock_bundle_data, status=200)
    mocker.patch.object(
        demisto_client,
        "generic_request_func",
        return_value=(mock_bundle_response, None, None),
    )

    downloader = Downloader(
        all_custom_content=True,
        auto_replace_uuids=auto_replace_uuids,
        output="fake_output_dir",
    )

    mocker.patch.object(downloader, "verify_output_path", return_value=True)
    mocker.patch.object(downloader, "build_existing_pack_structure", return_value={})
    mocker.patch.object(downloader, "write_files_into_output_path", return_value=True)
    mock_replace_uuids = mocker.spy(downloader, "replace_uuid_ids")

    downloader.download()

    if auto_replace_uuids:
        assert mock_replace_uuids.called

    else:
        assert not mock_replace_uuids.called


def test_invalid_regex_error(mocker):
    """
    Given: A regex that is not valid
    When: Calling the download command for custom content
    Then: Ensure that the command fails with an appropriate error message.
    """
    downloader = Downloader(regex="*invalid-regex*", output="fake_output_dir")
    mocker.patch.object(downloader, "verify_output_path", return_value=True)
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

    assert downloader.download() == 1
    assert str_in_call_args_list(
        logger_error.call_args_list,
        "Error: Invalid regex pattern provided: '*invalid-regex*'.",
    )
