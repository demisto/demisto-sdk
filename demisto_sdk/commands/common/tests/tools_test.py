import glob
import logging
import os
import shutil
from configparser import ConfigParser
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Callable, List, Optional, Tuple, Union

import pytest
import requests

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    DEMISTO_GIT_PRIMARY_BRANCH,
    DOC_FILES_DIR,
    INDICATOR_TYPES_DIR,
    INTEGRATIONS_DIR,
    LAYOUTS_DIR,
    MARKETPLACE_TO_CORE_PACKS_FILE,
    PACKS_DIR,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME,
    PLAYBOOKS_DIR,
    SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR,
    TRIGGER_DIR,
    XPANSE_INLINE_PREFIX_TAG,
    XPANSE_INLINE_SUFFIX_TAG,
    XPANSE_PREFIX_TAG,
    XPANSE_SUFFIX_TAG,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_INLINE_PREFIX_TAG,
    XSIAM_INLINE_SUFFIX_TAG,
    XSIAM_PREFIX_TAG,
    XSIAM_REPORTS_DIR,
    XSIAM_SUFFIX_TAG,
    XSOAR_CONFIG_FILE,
    XSOAR_INLINE_PREFIX_TAG,
    XSOAR_INLINE_SUFFIX_TAG,
    XSOAR_ON_PREM_INLINE_PREFIX_TAG,
    XSOAR_ON_PREM_INLINE_SUFFIX_TAG,
    XSOAR_ON_PREM_PREFIX_TAG,
    XSOAR_ON_PREM_SUFFIX_TAG,
    XSOAR_PREFIX_TAG,
    XSOAR_SAAS_INLINE_PREFIX_TAG,
    XSOAR_SAAS_INLINE_SUFFIX_TAG,
    XSOAR_SAAS_PREFIX_TAG,
    XSOAR_SAAS_SUFFIX_TAG,
    XSOAR_SUFFIX_TAG,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.content.tests.objects.pack_objects.pack_ignore.pack_ignore_test import (
    PACK_IGNORE,
)
from demisto_sdk.commands.common.git_content_config import (
    GitContentConfig,
    GitCredentials,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import (
    MarketplaceTagParser,
    TagParser,
    arg_to_list,
    check_timestamp_format,
    compare_context_path_in_yml_and_readme,
    extract_field_from_mapping,
    field_to_cli_name,
    filter_files_by_type,
    filter_files_on_pack,
    filter_packagify_changes,
    find_type,
    find_type_by_path,
    generate_xsiam_normalized_name,
    get_code_lang,
    get_current_repo,
    get_dict_from_file,
    get_display_name,
    get_entity_id_by_entity_type,
    get_file,
    get_file_displayed_name,
    get_file_version_suffix_if_exists,
    get_files_in_dir,
    get_from_version,
    get_ignore_pack_skipped_tests,
    get_item_marketplaces,
    get_last_release_version,
    get_last_remote_release_version,
    get_latest_release_notes_text,
    get_marketplace_to_core_packs,
    get_pack_metadata,
    get_pack_names_from_files,
    get_relative_path_from_packs_dir,
    get_release_note_entries,
    get_release_notes_file_path,
    get_scripts_and_commands_from_yml_data,
    get_test_playbook_id,
    get_to_version,
    get_yaml,
    has_remote_configured,
    is_content_item_dependent_in_conf,
    is_object_in_id_set,
    is_origin_content_repo,
    is_pack_path,
    is_uuid,
    parse_multiple_path_inputs,
    run_command_os,
    search_and_delete_from_conf,
    server_version_compare,
    set_value,
    str2bool,
    string_to_bool,
    to_kebab_case,
)
from demisto_sdk.tests.constants_test import (
    DUMMY_SCRIPT_PATH,
    IGNORED_PNG,
    INDICATORFIELD_EXTRA_FIELDS,
    SOURCE_FORMAT_INTEGRATION_COPY,
    TEST_PLAYBOOK,
    VALID_BETA_INTEGRATION_PATH,
    VALID_DASHBOARD_PATH,
    VALID_GENERIC_DEFINITION_PATH,
    VALID_GENERIC_FIELD_PATH,
    VALID_GENERIC_MODULE_PATH,
    VALID_GENERIC_TYPE_PATH,
    VALID_INCIDENT_FIELD_PATH,
    VALID_INCIDENT_TYPE_FILE,
    VALID_INCIDENT_TYPE_FILE__RAW_DOWNLOADED,
    VALID_INCIDENT_TYPE_PATH,
    VALID_INTEGRATION_TEST_PATH,
    VALID_LAYOUT_PATH,
    VALID_LIST_PATH,
    VALID_MD,
    VALID_PLAYBOOK_ID_PATH,
    VALID_PRE_PROCESSING_RULE_PATH,
    VALID_REPUTATION_FILE,
    VALID_SCRIPT_PATH,
    VALID_WIDGET_PATH,
    VULTURE_WHITELIST_PATH,
)
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    LAYOUT,
    MAPPER,
    OLD_CLASSIFIER,
    REPUTATION,
)
from TestSuite.file import File
from TestSuite.pack import Pack
from TestSuite.playbook import Playbook
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list

GIT_ROOT = git_path()


SENTENCE_WITH_UMLAUTS = "Nett hier. Aber waren Sie schon mal in Baden-Württemberg?"


class TestGenericFunctions:
    PATH_TO_HERE = f"{GIT_ROOT}/demisto_sdk/tests/test_files/"
    FILE_PATHS = [
        (os.path.join(PATH_TO_HERE, "fake_integration.yml"), tools.get_yaml),
        (
            os.path.join(
                PATH_TO_HERE, "test_playbook_value_starting_with_equal_sign.yml"
            ),
            tools.get_yaml,
        ),
        (
            str(
                Path(PATH_TO_HERE, "test_playbook_value_starting_with_equal_sign.yaml")
            ),
            tools.get_yaml,
        ),
        (str(Path(PATH_TO_HERE, "fake_json.json")), tools.get_json),
    ]

    @pytest.mark.parametrize("file_path, func", FILE_PATHS)
    def test_get_file(self, file_path, func):
        assert func(file_path)

    @pytest.mark.parametrize("file_path, _", FILE_PATHS)
    def test_get_file_or_remote_with_local(self, file_path: str, _):
        """
        Given:
            file_path to a file

        When:
            Calling `get_file_or_remote` when the file exists locally

        Then
            Ensure that the file data is returned
        """
        absolute_path = Path(file_path)
        relative_path = absolute_path.relative_to(GIT_ROOT)

        assert (result_non_relative := tools.get_file_or_remote(absolute_path))
        assert (result_relative := tools.get_file_or_remote(relative_path))
        assert result_non_relative == result_relative

    @pytest.mark.parametrize("file_path, _", FILE_PATHS)
    def test_get_file_or_remote_with_origin(self, mocker, file_path: str, _):
        """
        Given:
            file_path to a file

        When:
            Calling `get_file_or_remote` when the file doesn't exist locally, but exists on origin

        Then
            Ensure that the file data is returned
        """
        path = Path(file_path)
        content = path.read_text()
        mocker.patch.object(tools, "get_file", side_effect=FileNotFoundError)
        mocker.patch.object(GitUtil, "get_local_remote_file_path")
        mocker.patch.object(
            GitUtil, "get_local_remote_file_content", return_value=content
        )
        mocker.patch.object(tools, "get_content_path", return_value=Path(GIT_ROOT))
        relative_path = path.relative_to(GIT_ROOT)

        assert (result_non_relative := tools.get_file_or_remote(path))
        assert (result_relative := tools.get_file_or_remote(relative_path))
        assert result_non_relative == result_relative

    @pytest.mark.parametrize("file_path, _", FILE_PATHS)
    def test_get_file_or_remote_with_api(
        self, mocker, requests_mock, file_path: str, _
    ):
        """
        Given:
            file_path to a file

        When:
            Calling `get_file_or_remote` when the file doesn't exist locally, and not on origin, but exists GitHub

        Then
            Ensure that the file data is returned
        """

        path = Path(file_path)
        content = path.read_text()
        mocker.patch.object(tools, "get_file", side_effect=FileNotFoundError)
        mocker.patch.object(tools, "get_local_remote_file", side_effect=ValueError)
        mocker.patch.object(tools, "get_content_path", return_value=Path(GIT_ROOT))
        relative_path = path.relative_to(GIT_ROOT)
        requests_mock.get("https://api.github.com/repos/demisto/demisto-sdk")
        requests_mock.get(
            f"https://raw.githubusercontent.com/demisto/demisto-sdk/master/{relative_path}",
            text=content,
        )
        assert (result_non_relative := tools.get_file_or_remote(path))
        assert (result_relative := tools.get_file_or_remote(relative_path))
        assert result_non_relative == result_relative

    @staticmethod
    @pytest.mark.parametrize(
        "suffix,dumps_method", ((".json", json.dumps), (".yml", yaml.dumps))
    )
    def test_get_file_non_unicode(
        tmp_path,
        suffix: str,
        dumps_method: Callable,
    ):
        """Tests reading a non-unicode file"""
        path = (tmp_path / "non_unicode").with_suffix(suffix)

        path.write_bytes(
            dumps_method({"text": SENTENCE_WITH_UMLAUTS}, ensure_ascii=False).encode(
                "latin-1"
            )
        )
        assert "ü" in path.read_text(encoding="latin-1")
        assert get_file(path) == {"text": SENTENCE_WITH_UMLAUTS}

    @pytest.mark.parametrize(
        "file_name, prefix, result",
        [
            ("test.json", "parsingrule", "parsingrule-external-test.json"),
            (
                "parsingrule-external-test.json",
                "parsingrule",
                "external-parsingrule-test.json",
            ),
            ("parsingrule-test.json", "parsingrule", "external-parsingrule-test.json"),
        ],
    )
    def test_generate_xsiam_normalized_name(self, file_name, prefix, result):
        assert generate_xsiam_normalized_name(file_name, prefix)

    @pytest.mark.parametrize(
        "dir_path", ["demisto_sdk", f"{GIT_ROOT}/demisto_sdk/tests/test_files"]
    )
    def test_get_yml_paths_in_dir(self, dir_path):
        yml_paths, first_yml_path = tools.get_yml_paths_in_dir(dir_path)
        yml_paths_test = glob.glob(os.path.join(dir_path, "*yml"))
        assert sorted(yml_paths) == sorted(yml_paths_test)
        if yml_paths_test:
            assert first_yml_path == yml_paths_test[0]
        else:
            assert not first_yml_path

    data_test_get_dict_from_file = [
        (VALID_REPUTATION_FILE, True, "json"),
        (VALID_SCRIPT_PATH, True, "yml"),
        ("test", True, None),
        (None, True, None),
        ("invalid-path.json", False, None),
        (VALID_INCIDENT_TYPE_FILE__RAW_DOWNLOADED, False, "json"),
    ]

    @pytest.mark.parametrize("path, raises_error, _type", data_test_get_dict_from_file)
    def test_get_dict_from_file(self, path, raises_error, _type):
        output = get_dict_from_file(str(path), raises_error=raises_error)[1]
        assert (
            output == _type
        ), f"get_dict_from_file({path}) returns: {output} instead {_type}"

    data_test_find_type = [
        (VALID_DASHBOARD_PATH, FileType.DASHBOARD),
        (VALID_INCIDENT_FIELD_PATH, FileType.INCIDENT_FIELD),
        (VALID_INCIDENT_TYPE_PATH, FileType.INCIDENT_TYPE),
        (INDICATORFIELD_EXTRA_FIELDS, FileType.INDICATOR_FIELD),
        (VALID_INTEGRATION_TEST_PATH, FileType.INTEGRATION),
        (VALID_LAYOUT_PATH, FileType.LAYOUT),
        (VALID_PLAYBOOK_ID_PATH, FileType.PLAYBOOK),
        (VALID_REPUTATION_FILE, FileType.REPUTATION),
        (VALID_SCRIPT_PATH, FileType.SCRIPT),
        (VALID_WIDGET_PATH, FileType.WIDGET),
        (VALID_GENERIC_TYPE_PATH, FileType.GENERIC_TYPE),
        (VALID_GENERIC_FIELD_PATH, FileType.GENERIC_FIELD),
        (VALID_GENERIC_MODULE_PATH, FileType.GENERIC_MODULE),
        (VALID_GENERIC_DEFINITION_PATH, FileType.GENERIC_DEFINITION),
        (VALID_LIST_PATH, FileType.LISTS),
        (IGNORED_PNG, None),
        ("Author_image.png", FileType.AUTHOR_IMAGE),
        (FileType.PACK_IGNORE.value, FileType.PACK_IGNORE),
        (FileType.SECRET_IGNORE.value, FileType.SECRET_IGNORE),
        (Path(DOC_FILES_DIR) / "foo", FileType.DOC_FILE),
        (PACKS_PACK_META_FILE_NAME, FileType.METADATA),
        ("", None),
        (VULTURE_WHITELIST_PATH, FileType.VULTURE_WHITELIST),
        (VALID_PRE_PROCESSING_RULE_PATH, FileType.PRE_PROCESS_RULES),
    ]

    @pytest.mark.parametrize("path, _type", data_test_find_type)
    def test_find_type(self, path, _type):
        output = find_type(str(path))
        assert output == _type, f"find_type({path}) returns: {output} instead {_type}"

    def test_find_type_ignore_sub_categories(self):
        output = find_type(VALID_BETA_INTEGRATION_PATH)
        assert (
            output == FileType.BETA_INTEGRATION
        ), f"find_type({VALID_BETA_INTEGRATION_PATH}) returns: {output} instead {FileType.BETA_INTEGRATION}"

        output = find_type(VALID_BETA_INTEGRATION_PATH, ignore_sub_categories=True)
        assert (
            output == FileType.INTEGRATION
        ), f"find_type({VALID_BETA_INTEGRATION_PATH}) returns: {output} instead {FileType.INTEGRATION}"

    def test_find_type_with_invalid_yml(self, malformed_integration_yml):
        """
        Given
        - A malformed yml file.

        When
        - Running find_type.

        Then
        - Ensure no exception/error is raised and None is returned.
        """
        try:
            assert not find_type(
                malformed_integration_yml.path, ignore_invalid_schema_file=True
            )
        except ValueError as err:
            assert False, str(err)

    def test_find_type_with_invalid_json(self, malformed_incident_field):
        """
        Given
        - A malformed json file.

        When
        - Running find_type.

        Then
        - Ensure no exception/error is raised and None is returned.
        """
        try:
            assert not find_type(
                malformed_incident_field.path, ignore_invalid_schema_file=True
            )
        except ValueError as err:
            assert False, str(err)

    def test_find_type_no_file(self):
        """
        Given
        - A non existing file path.

        When
        - Running find_type.

        Then
        - Ensure None is returned
        """
        madeup_path = "some/path"
        output = find_type(madeup_path)
        assert not output

    test_path_md = [VALID_MD]

    @pytest.mark.parametrize("path", test_path_md)
    def test_filter_packagify_changes(self, path):
        modified, added, removed = filter_packagify_changes(
            modified_files=[], added_files=[], removed_files=[path]
        )
        assert modified == []
        assert added == set()
        assert removed == [VALID_MD]

    test_content_path_on_pack = [
        (
            "AbuseDB",
            {
                "Packs/AbuseDB/Integrations/AbuseDB/AbuseDB.py",
                "Packs/Another_pack/Integrations/example/example.py",
            },
        )
    ]

    @pytest.mark.parametrize("pack, file_paths_list", test_content_path_on_pack)
    def test_filter_files_on_pack(self, pack, file_paths_list):
        """
        Given
        - Set of files and pack name.
        When
        - Want to filter the list by specific pack.
        Then:
        - Ensure the set of file paths contains only files located in the given pack.
        """
        files_paths = filter_files_on_pack(pack, file_paths_list)
        assert files_paths == {"Packs/AbuseDB/Integrations/AbuseDB/AbuseDB.py"}

    for_test_filter_files_by_type = [
        (
            {VALID_INCIDENT_FIELD_PATH, VALID_PLAYBOOK_ID_PATH},
            [FileType.PLAYBOOK],
            {VALID_INCIDENT_FIELD_PATH},
        ),
        (
            {VALID_INCIDENT_FIELD_PATH, VALID_INCIDENT_TYPE_PATH},
            [],
            {VALID_INCIDENT_FIELD_PATH, VALID_INCIDENT_TYPE_PATH},
        ),
        (set(), [FileType.PLAYBOOK], set()),
    ]

    @pytest.mark.parametrize("files, types, output", for_test_filter_files_by_type)
    def test_filter_files_by_type(self, files, types, output, mocker):
        """
        Given
        - Sets of content files and file types to skip.
        When
        - Want to filter the lists by file typs.
        Then:
        - Ensure the list returned Whiteout the files to skip.
        """
        mocker.patch(
            "demisto_sdk.commands.common.tools.is_file_path_in_pack",
            return_value="True",
        )
        files = filter_files_by_type(files, types)

        assert files == output

    @pytest.mark.parametrize(
        "data, entity, output",
        [
            ({"script": {"type": "javascript"}}, INTEGRATIONS_DIR, "javascript"),
            ({"type": "javascript"}, SCRIPTS_DIR, "javascript"),
            ({}, LAYOUTS_DIR, ""),
        ],
    )
    def test_get_code_lang(self, data, entity, output):
        assert get_code_lang(data, entity) == output

    def test_camel_to_snake(self):
        snake = tools.camel_to_snake("CamelCase")

        assert snake == "camel_case"


class TestGetRemoteFile:
    content_repo = "demisto/content"

    def test_get_remote_file_sanity(self):
        hello_world_yml = tools.get_remote_file(
            "Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert hello_world_yml
        assert hello_world_yml["commonfields"]["id"] == "HelloWorld"

    def test_get_remote_file_content_sanity(self):
        hello_world_py = tools.get_remote_file(
            "Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.py",
            return_content=True,
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert hello_world_py

    def test_get_remote_file_content(self):
        hello_world_py = tools.get_remote_file(
            "Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.py",
            return_content=True,
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        hello_world_text = hello_world_py.decode()
        assert isinstance(hello_world_py, bytes)
        assert hello_world_py
        assert "main()" in hello_world_text
        assert (
            """HelloWorld Integration for Cortex XSOAR (aka Demisto)"""
            in hello_world_text
        )

    def test_get_remote_file_origin(self):
        hello_world_yml = tools.get_remote_file(
            "Packs/HelloWorld/Integrations/HelloWorld/HelloWorld.yml",
            "master",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert hello_world_yml
        assert hello_world_yml["commonfields"]["id"] == "HelloWorld"

    def test_get_remote_file_tag(self):
        gmail_yml = tools.get_remote_file(
            "Integrations/Gmail/Gmail.yml",
            "19.10.0",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert gmail_yml
        assert gmail_yml["commonfields"]["id"] == "Gmail"

    def test_get_remote_file_origin_tag(self):
        gmail_yml = tools.get_remote_file(
            "Integrations/Gmail/Gmail.yml",
            "origin/19.10.0",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert gmail_yml
        assert gmail_yml["commonfields"]["id"] == "Gmail"

    def test_get_remote_file_invalid(self):
        invalid_yml = tools.get_remote_file(
            "Integrations/File/File.yml",
            "19.10.0",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert not invalid_yml

    def test_get_remote_file_invalid_branch(self):
        invalid_yml = tools.get_remote_file(
            "Integrations/Gmail/Gmail.yml",
            "NoSuchBranch",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert not invalid_yml

    def test_get_remote_file_invalid_origin_branch(self):
        invalid_yml = tools.get_remote_file(
            "Integrations/Gmail/Gmail.yml",
            "origin/NoSuchBranch",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert not invalid_yml

    def test_get_remote_md_file_origin(self):
        hello_world_readme = tools.get_remote_file(
            "Packs/HelloWorld/README.md",
            "master",
            git_content_config=GitContentConfig(repo_name=self.content_repo),
        )
        assert hello_world_readme == {}

    def test_should_file_skip_validation_negative(self):
        should_skip = tools.should_file_skip_validation(
            "Packs/HelloWorld/Integrations/HelloWorld/search_alerts.json"
        )
        assert not should_skip

    SKIPPED_FILE_PATHS = [
        "some_text_file.txt",
        "pack_metadata.json",
        "testdata/file.json",
        "test_data/file.json",
        "data_test/file.json",
        "testcommandsfunctions/file.json",
        "testhelperfunctions/file.json",
        "StixDecodeTest/file.json",
        "TestCommands/file.json",
        "SetGridField_test/file.json",
        "IPNetwork_test/file.json",
        "test-data/file.json"
        "some_file/integration_DESCRIPTION.md"
        "some_file/integration_CHANGELOG.md"
        "some_file/integration_unified.md",
    ]

    @pytest.mark.parametrize("file_path", SKIPPED_FILE_PATHS)
    def test_should_file_skip_validation_positive(self, file_path):
        should_skip = tools.should_file_skip_validation(file_path)
        assert should_skip


class TestGetRemoteFileLocally:
    REPO_NAME = "example_repo"
    FILE_NAME = "somefile.json"
    FILE_CONTENT = '{"id": "some_file"}'

    git_util = Content.git_util()
    main_branch = DEMISTO_GIT_PRIMARY_BRANCH

    def setup_method(self):
        # create local git repo
        example_repo = GitUtil.REPO_CLS.init(self.REPO_NAME)
        origin_branch = self.main_branch
        if not origin_branch.startswith("origin"):
            origin_branch = "origin/" + origin_branch
        example_repo.git.checkout("-b", f"{origin_branch}")
        with open(os.path.join(self.REPO_NAME, self.FILE_NAME), "w+") as somefile:
            somefile.write(self.FILE_CONTENT)
        example_repo.git.add(self.FILE_NAME)
        example_repo.git.config("user.email", "automatic@example.com")
        example_repo.git.config("user.name", "AutomaticTest")
        example_repo.git.commit("-m", "test_commit", "-a")
        example_repo.git.checkout("-b", self.main_branch)

    def test_get_file_from_master_when_in_private_repo(self, mocker):
        mocker.patch.object(tools, "is_external_repository", return_value=True)

        class Response:
            ok = False

        mocker.patch.object(requests, "get", return_value=Response)
        mocker.patch.dict(
            os.environ,
            {
                GitCredentials.ENV_GITHUB_TOKEN_NAME: "",
                GitCredentials.ENV_GITLAB_TOKEN_NAME: "",
            },
        )
        with ChangeCWD(self.REPO_NAME):
            some_file_json = tools.get_remote_file(self.FILE_NAME)
        assert some_file_json
        assert some_file_json["id"] == "some_file"

    def teardown_method(self):
        shutil.rmtree(self.REPO_NAME)


class TestServerVersionCompare:
    V5 = "5.0.0"
    V0 = "0.0.0"
    EQUAL = 0
    LEFT_IS_LATER = 1
    RIGHT_IS_LATER = -1
    INPUTS = [
        (V0, V5, RIGHT_IS_LATER),
        (V5, V0, LEFT_IS_LATER),
        (V5, V5, EQUAL),
        ("4.5.0", "4.5", EQUAL),
    ]

    @pytest.mark.parametrize("left, right, answer", INPUTS)
    def test_server_version_compare(self, left, right, answer):
        assert server_version_compare(left, right) == answer


def test_pascal_case():
    res = tools.pascal_case("PowerShell Remoting")
    assert res == "PowerShellRemoting"
    res = tools.pascal_case("good life")
    assert res == "GoodLife"
    res = tools.pascal_case("good_life-here v2")
    assert res == "GoodLifeHereV2"


def test_capital_case():
    res = tools.capital_case("PowerShell Remoting")
    assert res == "PowerShell Remoting"
    res = tools.capital_case("good life")
    assert res == "Good Life"
    res = tools.capital_case("good_life-here v2")
    assert res == "Good_life-here V2"
    res = tools.capital_case("")
    assert res == ""


class TestReleaseVersion:
    def test_get_last_release(self, mocker):
        mocker.patch(
            "demisto_sdk.commands.common.tools.run_command",
            return_value="1.2.3\n4.5.6\n3.2.1\n20.0.0",
        )

        tag = get_last_release_version()

        assert tag == "20.0.0"


class TestEntityAttributes:
    @pytest.mark.parametrize(
        "data, entity",
        [
            ({"commonfields": {"id": 1}}, INTEGRATIONS_DIR),
            ({"typeId": 1}, LAYOUTS_DIR),
            ({"id": 1}, PLAYBOOKS_DIR),
        ],
    )
    def test_get_entity_id_by_entity_type(self, data, entity):
        assert get_entity_id_by_entity_type(data, entity) == 1


class TestGetFilesInDir:
    def test_project_dir_is_file(self):
        project_dir = "demisto_sdk/commands/download/downloader.py"
        assert get_files_in_dir(project_dir, ["py"]) == [project_dir]

    def test_not_recursive(self):
        project_dir = "demisto_sdk/commands/download"
        files = [
            f"{project_dir}/__init__.py",
            f"{project_dir}/downloader.py",
            f"{project_dir}/README.md",
        ]
        assert sorted(get_files_in_dir(project_dir, ["py", "md"], False)) == sorted(
            files
        )

    def test_recursive(self):
        integrations_dir = "demisto_sdk/commands/download/tests/tests_env/content/Packs/TestPack/Integrations"
        integration_instance_dir = f"{integrations_dir}/TestIntegration"
        files = [
            f"{integration_instance_dir}/TestIntegration.py",
            f"{integration_instance_dir}/TestIntegration_testt.py",
        ]
        assert sorted(get_files_in_dir(integrations_dir, ["py"])) == sorted(files)

    def test_recursive_pack(self):
        pack_dir = (
            "demisto_sdk/commands/download/tests/tests_env/content/Packs/TestPack"
        )
        files = [
            f"{pack_dir}/Integrations/TestIntegration/TestIntegration.py",
            f"{pack_dir}/Integrations/TestIntegration/TestIntegration_testt.py",
            f"{pack_dir}/Scripts/TestScript/TestScript.py",
        ]
        assert sorted(get_files_in_dir(pack_dir, ["py"])) == sorted(files)


run_command_os_inputs = [("ls", os.getcwd()), ("ls", Path(os.getcwd()))]


@pytest.mark.parametrize("command, cwd", run_command_os_inputs)
def test_run_command_os(command, cwd):
    """Tests a simple command, to check if it works"""
    stdout, stderr, return_code = run_command_os(command, cwd=cwd)
    assert 0 == return_code
    assert stdout
    assert not stderr


class TestGetFile:
    def test_get_yaml(self):
        file_data = get_yaml(SOURCE_FORMAT_INTEGRATION_COPY)
        assert file_data
        assert file_data.get("name") is not None


def test_get_latest_release_notes_text_invalid():
    """
    Given
    - Invalid release notes

    When
    - Running validation on release notes.

    Then
    - Ensure None is returned
    """
    PATH_TO_HERE = f"{GIT_ROOT}/demisto_sdk/tests/test_files/"
    file_path = os.path.join(PATH_TO_HERE, "empty-RN.md")
    assert get_latest_release_notes_text(file_path) == ""


def test_get_release_notes_file_path_valid():
    """
    Given
    - Valid release notes path

    When
    - Running validation on release notes.

    Then
    - Ensure valid file path is returned
    """
    filepath = "/SomePack/1_1_1.md"
    assert get_release_notes_file_path(filepath) == filepath


def test_get_release_notes_file_path_invalid():
    """
    Given
    - Invalid release notes path

    When
    - Running validation on release notes.

    Then
    - Ensure None is returned
    """
    filepath = "/SomePack/1_1_1.json"
    assert get_release_notes_file_path(filepath) is None


remote_testbank = [
    ("origin  https://github.com/turbodog/content.git", False),
    ("upstream  https://github.com/demisto/content.git", True),
]


@pytest.mark.parametrize("git_value, response", remote_testbank)
def test_has_remote(mocker, git_value, response):
    """
    While: Testing if the remote upstream contains demisto/content
    Given:
      1. Origin string not containing demisto/content
      2. Upstream string containing demisto/content
    Expects:
      1. Test condition fails
      2. Test condition passes
    :param git_value: Git string from `git remotes -v`
    """
    mocker.patch(
        "demisto_sdk.commands.common.tools.git_remote_v", return_value=git_value
    )
    test_remote = has_remote_configured()
    assert response == test_remote


origin_testbank = [
    ("origin  https://github.com/turbodog/content.git", False),
    ("origin  https://github.com/demisto/content.git", True),
]


@pytest.mark.parametrize("git_value, response", origin_testbank)
def test_origin_content(mocker, git_value, response):
    """
    While: Testing if the remote origin contains demisto/content
    Given:
      1. Origin string not containing demisto/content
      2. Origin string containing demisto/content
    Expects:
      1. Test condition fails
      2. Test condition passes
    :param git_value: Git string from `git remotes -v`
    """
    mocker.patch(
        "demisto_sdk.commands.common.tools.git_remote_v", return_value=git_value
    )
    test_remote = is_origin_content_repo()
    assert response == test_remote


def test_get_ignore_pack_tests__no_pack():
    """
    Given
    - Pack that doesn't exist
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns an empty set
    """
    nonexistent_pack = "NonexistentFakeTestPack"
    ignore_test_set = get_ignore_pack_skipped_tests(
        nonexistent_pack, {nonexistent_pack}, {}
    )
    assert len(ignore_test_set) == 0


def test_get_ignore_pack_tests__no_ignore_pack(tmpdir):
    """
    Given
    - Pack doesn't have .pack-ignore file
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns an empty set
    """
    fake_pack_name = "FakeTestPack"

    # prepare repo
    repo = Repo(tmpdir)
    repo_path = Path(repo.path)
    pack = Pack(repo_path / PACKS_DIR, fake_pack_name, repo)
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # remove .pack-ignore if exists
    Path(pack_ignore_path).unlink(missing_ok=True)

    ignore_test_set = get_ignore_pack_skipped_tests(
        fake_pack_name, {fake_pack_name}, {}
    )
    assert len(ignore_test_set) == 0


def test_get_ignore_pack_tests__test_not_ignored(tmpdir):
    """
    Given
    - Pack have .pack-ignore file
    - There are no skipped tests in .pack-ignore
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns an empty set
    """
    fake_pack_name = "FakeTestPack"

    # prepare repo
    repo = Repo(tmpdir)
    repo_path = Path(repo.path)
    pack = Pack(repo_path / PACKS_DIR, fake_pack_name, repo)
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # prepare .pack-ignore
    open(pack_ignore_path, "a").close()

    ignore_test_set = get_ignore_pack_skipped_tests(
        fake_pack_name, {fake_pack_name}, {}
    )
    assert len(ignore_test_set) == 0


def test_get_ignore_pack_tests__ignore_test(tmpdir, mocker):
    """
    Given
    - Pack have .pack-ignore file
    - There are skipped tests in .pack-ignore
    - Set of modified packs.
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns a list with the skipped tests
    """
    fake_pack_name = "FakeTestPack"
    fake_test_name = "FakeTestPlaybook"
    expected_id = "SamplePlaybookTest"

    # prepare repo
    repo = Repo(tmpdir)
    packs_path = Path(repo.path) / PACKS_DIR
    pack = Pack(packs_path, fake_pack_name, repo)
    test_playbook_path = packs_path / fake_pack_name / TEST_PLAYBOOKS_DIR
    test_playbook = Playbook(
        test_playbook_path, fake_test_name, repo, is_test_playbook=True
    )
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # prepare .pack-ignore
    with open(pack_ignore_path, "a") as pack_ignore_f:
        pack_ignore_f.write(
            "[file:TestIntegration.yml]\nignore=IN126\n\n"
            f"[file:{test_playbook.name}]\nignore=auto-test"
        )

    # prepare mocks
    mocker.patch.object(
        tools, "get_pack_ignore_file_path", return_value=pack_ignore_path
    )
    mocker.patch.object(
        os.path,
        "join",
        return_value=str(test_playbook_path / (test_playbook.name + ".yml")),
    )
    mocker.patch.object(
        tools,
        "get_test_playbook_id",
        return_value=("SamplePlaybookTest", "FakeTestPack"),
    )

    ignore_test_set = get_ignore_pack_skipped_tests(
        fake_pack_name, {fake_pack_name}, {}
    )
    assert len(ignore_test_set) == 1
    assert expected_id in ignore_test_set


def test_get_ignore_pack_tests__ignore_missing_test(tmpdir, mocker):
    """
    Given
    - Pack have .pack-ignore file
    - There are skipped tests in .pack-ignore
    - The tests are missing from the content pack
    When
    - Collecting packs' ignored tests - running `get_ignore_pack_tests()`
    Then:
    - returns a list with the skipped tests
    """
    fake_pack_name = "FakeTestPack"
    fake_test_name = "FakeTestPlaybook.yml"

    # prepare repo
    repo = Repo(tmpdir)
    packs_path = Path(repo.path) / PACKS_DIR
    pack = Pack(packs_path, fake_pack_name, repo)
    test_playbook_path = packs_path / fake_pack_name / TEST_PLAYBOOKS_DIR
    pack_ignore_path = os.path.join(pack.path, PACKS_PACK_IGNORE_FILE_NAME)

    # prepare .pack-ignore
    with open(pack_ignore_path, "a") as pack_ignore_f:
        pack_ignore_f.write(
            "[file:TestIntegration.yml]\nignore=IN126\n\n"
            f"[file:{fake_test_name}]\nignore=auto-test"
        )

    # prepare mocks
    mocker.patch.object(
        tools, "get_pack_ignore_file_path", return_value=pack_ignore_path
    )
    mocker.patch.object(
        os.path, "join", return_value=str(test_playbook_path / fake_test_name)
    )
    mocker.patch.object(
        tools, "get_test_playbook_id", return_value=(None, "FakeTestPack")
    )

    ignore_test_set = get_ignore_pack_skipped_tests(
        fake_pack_name, {fake_pack_name}, {}
    )
    assert len(ignore_test_set) == 0


@pytest.mark.parametrize(
    argnames="pack_ignore_content, expected_object",
    argvalues=[
        (
            "[file:README.md]\nignore=RM106\n\n[known_words]\ntest1\ntest2\n\n[tests_require_network]\ntest",
            ConfigParser(),
        ),
        (
            "[known_words]\ntest1\ntest2\n\n[tests_require_network]\ntest",
            ConfigParser(),
        ),
        (
            "[file:README.md]\nignore=RM106\n\n[tests_require_network]\ntest",
            ConfigParser(),
        ),
        (
            "[file:README.md]\nignore=RM106\n\n[known_words]\ntest1\ntest2",
            ConfigParser(),
        ),
        ("", ConfigParser()),
        ("test", None),
        ("test[dssa]sdf", None),
    ],
)
def test_get_pack_ignore_content(pack: Pack, pack_ignore_content: str, expected_object):
    """
    Given
    - Case a: full valid .pack-ignore content
    - Case b: valid .pack-ignore content without validations sections
    - Case c: valid .pack-ignore content without known words section
    - Case d: valid .pack-ignore content without tests_require_network section
    - Case e: empty .pack-ignore
    - case f: invalid .pack-ignore file
    - case g: another version of invalid .pack-ignore file

    When
    - executing get_pack_ignore_content function

    Then:
    - Case a: ConfigParser is returned
    - Case b: ConfigParser is returned
    - Case c: ConfigParser is returned
    - Case d: ConfigParser is returned
    - Case e: ConfigParser is returned
    - case f: None is returned
    - case g: None is returned

    """
    from demisto_sdk.commands.common.tools import get_pack_ignore_content

    pack.pack_ignore.write_text(pack_ignore_content)
    with ChangeCWD(pack.repo_path):
        assert type(get_pack_ignore_content(pack.name)) is type(expected_object)


@pytest.mark.parametrize(
    argnames="arg, expected_result",
    argvalues=[
        ["a1,b2,c3", ["a1", "b2", "c3"]],
        ['["a1","b2","c3"]', ["a1", "b2", "c3"]],
        [["a1", "b2", "c3"], ["a1", "b2", "c3"]],
        ["", []],
        [[], []],
    ],
)
def test_arg_to_list(arg: Union[List[str], str], expected_result: List[str]):
    """
    Given
    - String or list of strings.
    Case a: comma-separated string.
    Case b: a string representing a list.
    Case c: python list.
    Case d: empty string.
    Case e: empty list.

    When
    - Convert given string to list of strings, for example at unify.add_contributors_support.

    Then:
    - Ensure a Python list is returned with the relevant values.
    """
    func_result = arg_to_list(arg=arg, separator=",")
    assert func_result == expected_result


V2_VALID = {
    "display": "integrationname v2",
    "name": "integrationname v2",
    "id": "integrationname v2",
}
V2_WRONG_DISPLAY = {
    "display": "integrationname V2",
    "name": "integrationname v2",
    "id": "integrationname V2",
}
NOT_V2_VIA_DISPLAY_NOR_NAME = {
    "display": "integrationname",
    "name": "integrationv2name",
    "id": "integrationv2name",
}
NOT_V2_VIA_DISPLAY = {
    "display": "integrationname",
    "name": "integrationname v2",
    "id": "integrationv2name",
}
NOT_V2_VIA_NAME = {
    "display": "integrationname V2",
    "name": "integrationname",
    "id": "integrationv2name",
}
V3_VALID = {
    "display": "integrationname v3",
    "name": "integrationname v3",
    "id": "integrationname v3",
}
V3_WRONG_DISPLAY = {
    "display": "integrationname V3",
    "name": "integrationname v3",
    "id": "integrationname V3",
}
NOT_V3_VIA_DISPLAY_NOR_NAME = {
    "display": "integrationname",
    "name": "integrationv3name",
    "id": "integrationv3name",
}
NOT_V3_VIA_DISPLAY = {
    "display": "integrationname",
    "name": "integrationname v3",
    "id": "integrationv3name",
}
NOT_V3_VIA_NAME = {
    "display": "integrationname V3",
    "name": "integrationname",
    "id": "integrationv3Gname",
}
GET_FILE_VERSION_SUFFIX_IF_EXISTS_NAME_INPUTS = [
    (V2_VALID, "2"),
    (V2_WRONG_DISPLAY, "2"),
    (NOT_V2_VIA_DISPLAY_NOR_NAME, None),
    (NOT_V2_VIA_NAME, None),
    (NOT_V2_VIA_DISPLAY, "2"),
    (V3_VALID, "3"),
    (V3_WRONG_DISPLAY, "3"),
    (NOT_V3_VIA_DISPLAY_NOR_NAME, None),
    (NOT_V3_VIA_NAME, None),
    (NOT_V3_VIA_DISPLAY, "3"),
]


@pytest.mark.parametrize(
    "current, answer", GET_FILE_VERSION_SUFFIX_IF_EXISTS_NAME_INPUTS
)
def test_get_file_version_suffix_if_exists_via_name(current, answer):
    assert get_file_version_suffix_if_exists(current) is answer


GET_FILE_VERSION_SUFFIX_IF_EXIST_INPUTS = [
    (V2_VALID, "2"),
    (V2_WRONG_DISPLAY, "2"),
    (NOT_V2_VIA_DISPLAY, None),
    (NOT_V2_VIA_NAME, "2"),
    (NOT_V2_VIA_DISPLAY_NOR_NAME, None),
    (V3_VALID, "3"),
    (V3_WRONG_DISPLAY, "3"),
    (NOT_V3_VIA_DISPLAY, None),
    (NOT_V3_VIA_NAME, "3"),
    (NOT_V3_VIA_DISPLAY_NOR_NAME, None),
]


@pytest.mark.parametrize("current, answer", GET_FILE_VERSION_SUFFIX_IF_EXIST_INPUTS)
def test_get_file_version_suffix_if_exists_via_display(current, answer):
    assert get_file_version_suffix_if_exists(current, check_in_display=True) is answer


def test_test_get_file_version_suffix_if_exists_no_name_and_no_display():
    """
    Given:
    - 'current_file': Dict representing YML data of an integration or script.

    When:
    - Invalid dict given, not containing display and name values.

    Then:
    - Ensure None is returned.
    """
    assert get_file_version_suffix_if_exists(dict(), check_in_display=True) is None
    assert get_file_version_suffix_if_exists(dict(), check_in_display=False) is None


def test_get_to_version_with_to_version(repo):
    pack = repo.create_pack("Pack")
    integration = pack.create_integration("INT", yml={"toversion": "4.5.0"})
    with ChangeCWD(repo.path):
        to_ver = get_to_version(integration.yml.path)

        assert to_ver == "4.5.0"


def test_get_to_version_no_to_version(repo):
    pack = repo.create_pack("Pack")
    integration = pack.create_integration("INT", yml={})
    with ChangeCWD(repo.path):
        to_ver = get_to_version(integration.yml.path)

        assert to_ver == DEFAULT_CONTENT_ITEM_TO_VERSION


def test_get_file_displayed_name__integration(repo):
    """
    Given
    - The path to an integration.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the display field.
    """
    pack = repo.create_pack("MyPack")
    integration = pack.create_integration("MyInt")
    integration.create_default_integration()
    yml_content = integration.yml.read_dict()
    yml_content["display"] = "MyDisplayName"
    integration.yml.write_dict(yml_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(integration.yml.path)
        assert display_name == "MyDisplayName"


def test_get_file_displayed_name__script(repo):
    """
    Given
    - The path to a script.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the name field.
    """
    pack = repo.create_pack("MyPack")
    script = pack.create_script("MyScr")
    script.create_default_script()
    yml_content = script.yml.read_dict()
    yml_content["name"] = "MyDisplayName"
    script.yml.write_dict(yml_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(script.yml.path)
        assert display_name == "MyDisplayName"


def test_get_file_displayed_name__playbook(repo):
    """
    Given
    - The path to a playbook.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the name field.
    """
    pack = repo.create_pack("MyPack")
    playbook = pack.create_playbook("MyPlay")
    playbook.create_default_playbook()
    yml_content = playbook.yml.read_dict()
    yml_content["name"] = "MyDisplayName"
    playbook.yml.write_dict(yml_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(playbook.yml.path)
        assert display_name == "MyDisplayName"


def test_get_file_displayed_name__mapper(repo):
    """
    Given
    - The path to a mapper.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the name field.
    """
    pack = repo.create_pack("MyPack")
    mapper = pack.create_mapper("MyMap", content=MAPPER)
    json_content = mapper.read_json_as_dict()
    json_content["name"] = "MyDisplayName"
    mapper.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(mapper.path)
        assert display_name == "MyDisplayName"


def test_get_file_displayed_name__old_classifier(repo):
    """
    Given
    - The path to an old classifier.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the brandName field.
    """
    pack = repo.create_pack("MyPack")
    old_classifier = pack.create_classifier("MyClas", content=OLD_CLASSIFIER)
    json_content = old_classifier.read_json_as_dict()
    json_content["brandName"] = "MyDisplayName"
    old_classifier.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(old_classifier.path)
        assert display_name == "MyDisplayName"


def test_get_file_displayed_name__layout(repo):
    """
    Given
    - The path to a layout.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the TypeName field.
    """
    pack = repo.create_pack("MyPack")
    layout = pack.create_layout("MyLay", content=LAYOUT)
    json_content = layout.read_json_as_dict()
    json_content["TypeName"] = "MyDisplayName"
    layout.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(layout.path)
        assert display_name == "MyDisplayName"


def test_get_file_displayed_name__reputation(repo):
    """
    Given
    - The path to a reputation.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the id field.
    """
    pack = repo.create_pack("MyPack")
    reputation = pack._create_json_based(
        "MyRep", content=REPUTATION, prefix="reputation"
    )
    json_content = reputation.read_json_as_dict()
    json_content["id"] = "MyDisplayName"
    reputation.write_json(json_content)
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(reputation.path)
        assert display_name == "MyDisplayName"


def test_get_file_displayed_name__image(repo):
    """
    Given
    - The path to an image.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the file name.
    """
    pack = repo.create_pack("MyPack")
    integration = pack.create_integration("MyInt")
    integration.create_default_integration()
    with ChangeCWD(repo.path):
        display_name = get_file_displayed_name(integration.image.path)
        assert display_name == Path(integration.image.rel_path).name


INCIDENTS_TYPE_FILES_INPUTS = [
    (VALID_INCIDENT_TYPE_FILE__RAW_DOWNLOADED, "Access v2"),
    (VALID_INCIDENT_TYPE_FILE, "Access v2"),
]


@pytest.mark.parametrize("input_path, expected_name", INCIDENTS_TYPE_FILES_INPUTS)
def test_get_file_displayed_name__incident_type(input_path: str, expected_name: str):
    """
    Given
    - The path to an incident type file.

    When
    - Running get_file_displayed_name.

    Then:
    - Ensure the returned name is the incident type name.
    """

    assert get_file_displayed_name(input_path) == expected_name


def test_get_pack_metadata(repo):
    """
    Given
    - The path to some file in the repo.

    When
    - Running get_pack_metadata.

    Then:
    - Ensure the returned pack metadata of the file's pack.
    """
    metadata_json = {"name": "MyPack", "support": "xsoar", "currentVersion": "1.1.0"}

    pack = repo.create_pack("MyPack")
    pack_metadata = pack.pack_metadata
    pack_metadata.write_json(metadata_json)

    result = get_pack_metadata(pack.path)

    assert metadata_json == result


def test_get_last_remote_release_version(requests_mock):
    """
    When
    - Get latest release tag from remote pypi api

    Then:
    - Ensure the returned version is as expected
    """
    os.environ["DEMISTO_SDK_SKIP_VERSION_CHECK"] = ""
    os.environ["CI"] = ""
    expected_version = "1.3.8"
    requests_mock.get(
        r"https://pypi.org/pypi/demisto-sdk/json",
        json={"info": {"version": expected_version}},
    )
    assert get_last_remote_release_version() == expected_version


IS_PACK_PATH_INPUTS = [
    ("Packs/BitcoinAbuse", True),
    ("Packs/BitcoinAbuse/Layouts", False),
    ("Packs/BitcoinAbuse/Classifiers", False),
    ("Unknown", False),
]


@pytest.mark.parametrize("input_path, expected", IS_PACK_PATH_INPUTS)
def test_is_pack_path(input_path: str, expected: bool):
    """
    Given:
        - 'input_path': Path to some file or directory

    When:
        - Checking whether pack is to a pack directory.

    Then:
        - Ensure expected boolean is returned.

    """
    assert is_pack_path(input_path) == expected


@pytest.mark.parametrize(
    "s, is_valid_uuid",
    [
        ("", False),
        ("ffc9fbb0-1a73-448c-89a8-fe979e0f0c3e", True),
        ("somestring", False),
    ],
)
def test_is_uuid(s, is_valid_uuid):
    """
    Given:
        - Case A: Empty string
        - Case B: Valid UUID
        - Case C: Invalid UUID

    When:
        - Checking if the string is a valid UUID

    Then:
        - Case A: False as it is an empty string
        - Case B: True as it is a valid UUID
        - Case C: False as it is a string which is not a valid UUID
    """
    if is_valid_uuid:
        assert is_uuid(s)
    else:
        assert not is_uuid(s)


def test_get_relative_path_from_packs_dir():
    """
    Given:
        - 'input_path': Path to some file or directory

    When:
        - Running get_relative_path_from_packs_dir

    Then:
        - Ensure that:
          - If it is an absolute path to a pack related object - it returns the relative path from Packs dir.
          - If it is a relative path from Packs dir or an unrelated path - return the path unchanged.

    """
    abs_path = "/Users/who/dev/demisto/content/Packs/Accessdata/Integrations/Accessdata/Accessdata.yml"
    rel_path = "Packs/Accessdata/Integrations/Accessdata/Accessdata.yml"
    unrelated_path = "/Users/who/dev/demisto"

    assert get_relative_path_from_packs_dir(abs_path) == rel_path
    assert get_relative_path_from_packs_dir(rel_path) == rel_path
    assert get_relative_path_from_packs_dir(unrelated_path) == unrelated_path


@pytest.mark.parametrize(
    "version,expected_result",
    [
        ("1.3.8", ["* Updated the **secrets** command to work on forked branches."]),
        ("1.3", []),
    ],
)
def test_get_release_note_entries(requests_mock, version, expected_result):
    """
    Given:
        - Version of the demisto-sdk.

    When:
        - Running get_release_note_entries.

    Then:
        - Ensure that the result as expected.
    """
    requests_mock.get("https://api.github.com/repos/demisto/demisto-sdk")
    #
    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/common/tests/test_files/test_changelog.md",
        "rb",
    ) as f:
        changelog = f.read()
    requests_mock.get(
        "https://raw.githubusercontent.com/demisto/demisto-sdk/master/CHANGELOG.md",
        content=changelog,
    )

    assert get_release_note_entries(version) == expected_result


def test_suppress_stdout(capsys):
    """
    Given:
        - Messages to print.

    When:
        - Printing a message inside the suppress_stdout context manager.
        - Printing message after the suppress_stdout context manager is used.
    Then:
        - Ensure that messages are not printed to console while suppress_stdout is enabled.
        - Ensure that messages are printed to console when suppress_stdout is disabled.
    """
    print("You can see this")  # noqa: T201
    captured = capsys.readouterr()
    assert captured.out == "You can see this\n"
    with tools.suppress_stdout():
        print("You cannot see this")  # noqa: T201
        captured = capsys.readouterr()
    assert captured.out == ""
    print("And you can see this again")  # noqa: T201
    captured = capsys.readouterr()
    assert captured.out == "And you can see this again\n"


def test_suppress_stdout_exception(capsys):
    """
    Given:
        - Messages to print.

    When:
        - Performing an operation which throws an exception inside the suppress_stdout context manager.
        - Printing something after the suppress_stdout context manager is used.
    Then:
        - Ensure that the context manager do not not effect exception handling.
        - Ensure that messages are printed to console when suppress_stdout is disabled.

    """
    with pytest.raises(Exception) as excinfo:
        with tools.suppress_stdout():
            2 / 0
    assert str(excinfo.value) == "division by zero"
    print("After error prints are enabled again.")  # noqa: T201
    captured = capsys.readouterr()
    assert captured.out == "After error prints are enabled again.\n"


def test_compare_context_path_in_yml_and_readme_non_vs_code_format_valid():
    """
    Given:
        - a yml for an integration.
        - a valid readme in a non-vs code format

    When:
        - running compare_context_path_in_yml_and_readme.

    Then:
        - Ensure that no differences are found.
    """
    yml_dict = {
        "script": {
            "commands": [
                {
                    "name": "servicenow-create-ticket",
                    "outputs": [
                        {
                            "contextPath": "ServiceNow.Ticket.ID",
                            "description": "Ticket ID.",
                            "type": "string",
                        },
                        {
                            "contextPath": "ServiceNow.Ticket.OpenedBy",
                            "description": "Ticket opener ID.",
                            "type": "string",
                        },
                    ],
                }
            ]
        }
    }
    readme_content = (
        "### servicenow-create-ticket\n"
        "***\n"
        "Creates new ServiceNow ticket.\n\n\n"
        "#### Base Command\n\n"
        "`servicenow-create-ticket`\n"
        "#### Input\n\n"
        "| **Argument Name** | **Description** | **Required** |\n"
        "| --- | --- | --- |\n"
        "| short_description | Short description of the ticket. | Optional |\n\n\n"
        " #### Context Output\n\n"
        "| **Path** | **Type** | **Description** |\n"
        "| --- | --- | --- |\n"
        "| ServiceNow.Ticket.ID | string | ServiceNow ticket ID. |\n"
        "| ServiceNow.Ticket.OpenedBy | string | ServiceNow ticket opener ID. |\n"
    )

    diffs = compare_context_path_in_yml_and_readme(yml_dict, readme_content)
    assert not diffs


def test_compare_context_path_in_yml_and_readme_non_vs_code_format_invalid():
    """
    Given:
        - a yml for an integration.
        - an invalid readme in a non-vs code format

    When:
        - running compare_context_path_in_yml_and_readme.

    Then:
        - Ensure that differences are found.
    """
    yml_dict = {
        "script": {
            "commands": [
                {
                    "name": "servicenow-create-ticket",
                    "outputs": [
                        {
                            "contextPath": "ServiceNow.Ticket.ID",
                            "description": "Ticket ID.",
                            "type": "string",
                        },
                        {
                            "contextPath": "ServiceNow.Ticket.OpenedBy",
                            "description": "Ticket opener ID.",
                            "type": "string",
                        },
                    ],
                }
            ]
        }
    }
    readme_content = (
        "### servicenow-create-ticket\n"
        "***\n"
        "Creates new ServiceNow ticket.\n\n\n"
        "#### Base Command\n\n"
        "`servicenow-create-ticket`\n"
        "#### Input\n\n"
        "| **Argument Name** | **Description** | **Required** |\n"
        "| --- | --- | --- |\n"
        "| short_description | Short description of the ticket. | Optional |\n\n\n"
        " #### Context Output\n\n"
        "| **Path** | **Type** | **Description** |\n"
        "| --- | --- | --- |\n"
        "| ServiceNow.Ticket.ID | string | ServiceNow ticket ID. |\n"
    )

    diffs = compare_context_path_in_yml_and_readme(yml_dict, readme_content)
    assert "ServiceNow.Ticket.OpenedBy" in diffs.get("servicenow-create-ticket").get(
        "only in yml"
    )


def test_compare_context_path_in_yml_and_readme_vs_code_format_valid():
    """
    Given:
        - a yml for an integration.
        - a valid readme in a vs code format

    When:
        - running compare_context_path_in_yml_and_readme.

    Then:
        - Ensure that no differences are found.
    """
    yml_dict = {
        "script": {
            "commands": [
                {
                    "name": "servicenow-create-ticket",
                    "outputs": [
                        {
                            "contextPath": "ServiceNow.Ticket.ID",
                            "description": "Ticket ID.",
                            "type": "string",
                        },
                        {
                            "contextPath": "ServiceNow.Ticket.OpenedBy",
                            "description": "Ticket opener ID.",
                            "type": "string",
                        },
                    ],
                }
            ]
        }
    }
    readme_content = (
        "### servicenow-create-ticket\n"
        "***\n"
        "Creates new ServiceNow ticket.\n\n\n"
        "#### Base Command\n\n"
        "`servicenow-create-ticket`\n"
        "#### Input\n\n"
        "| **Argument Name** | **Description**                  | **Required** |\n"
        "| ----------------- | -------------------------------- | ------------ |\n"
        "| short_description | Short description of the ticket. | Optional     |\n\n\n"
        " #### Context Output\n\n"
        "| **Path**                   | **Type** | **Description**              |\n"
        "| -------------------------- | -------- | ---------------------------- |\n"
        "| ServiceNow.Ticket.ID       | string   | ServiceNow ticket ID.        |\n"
        "| ServiceNow.Ticket.OpenedBy | string   | ServiceNow ticket opener ID. |\n"
    )

    diffs = compare_context_path_in_yml_and_readme(yml_dict, readme_content)
    assert not diffs


def test_compare_context_path_in_yml_and_readme_vs_code_format_invalid():
    """
    Given:
        - a yml for an integration.
        - an invalid readme in a vs code format

    When:
        - running compare_context_path_in_yml_and_readme.

    Then:
        - Ensure that differences are found.
    """
    yml_dict = {
        "script": {
            "commands": [
                {
                    "name": "servicenow-create-ticket",
                    "outputs": [
                        {
                            "contextPath": "ServiceNow.Ticket.ID",
                            "description": "Ticket ID.",
                            "type": "string",
                        },
                        {
                            "contextPath": "ServiceNow.Ticket.OpenedBy",
                            "description": "Ticket opener ID.",
                            "type": "string",
                        },
                    ],
                }
            ]
        }
    }
    readme_content = (
        "### servicenow-create-ticket\n"
        "***\n"
        "Creates new ServiceNow ticket.\n\n\n"
        "#### Base Command\n\n"
        "`servicenow-create-ticket`\n"
        "#### Input\n\n"
        "| **Argument Name** | **Description**                  | **Required** |\n"
        "| ----------------- | -------------------------------- | ------------ |\n"
        "| short_description | Short description of the ticket. | Optional     |\n\n\n"
        " #### Context Output\n\n"
        "| **Path**             | **Type** | **Description**       |\n"
        "| -------------------- | -------- | --------------------- |\n"
        "| ServiceNow.Ticket.ID | string   | ServiceNow ticket ID. |\n"
    )

    diffs = compare_context_path_in_yml_and_readme(yml_dict, readme_content)
    assert "ServiceNow.Ticket.OpenedBy" in diffs.get("servicenow-create-ticket").get(
        "only in yml"
    )


def test_get_definition_name():
    """
    Given
    - The path to a generic field/generic type file.

    When
    - the file has a connected generic definition

    Then:
    - Ensure the returned name is the connected definitions name.
    """

    pack_path = f"{GIT_ROOT}/demisto_sdk/tests/test_files/generic_testing"
    field_path = pack_path + "/GenericFields/Object/genericfield-Sample.json"
    type_path = pack_path + "/GenericTypes/Object/generictype-Sample.json"

    assert tools.get_definition_name(field_path, pack_path) == "Object"
    assert tools.get_definition_name(type_path, pack_path) == "Object"


def test_gitlab_ci_yml_load():
    """
    Given:
        - a yml file with gitlab ci data

    When:
        - trying to load it to the sdk  - like via find_type

    Then:
        - Ensure that the load does not fail.
        - Ensure the file has no identification
    """
    test_file = f"{GIT_ROOT}/demisto_sdk/tests/test_files/gitlab_ci_test_file.yml"
    try:
        res = find_type(test_file)
    except Exception:
        # if we got here an error has occurred when trying to load the file
        assert False

    assert res is None


IRON_BANK_CASES = [
    ({"tags": []}, False),  # case no tags
    ({"tags": ["iron bank"]}, False),  # case some other tags than "Iron Bank"
    ({"tags": ["Iron Bank", "other_tag"]}, True),  # case Iron Bank tag exist
    ({}, False),  # case no tags
]


@pytest.mark.parametrize("metadata, expected", IRON_BANK_CASES)
def test_is_iron_bank_pack(mocker, metadata, expected):
    mocker.patch.object(tools, "get_pack_metadata", return_value=metadata)
    res = tools.is_iron_bank_pack("example_path")
    assert res == expected


def test_get_test_playbook_id():
    """
    Given:
        - A list of test playbooks from id_set
        - Test playbook file name

    When:
        - trying to get the pack and name of the test playbook - via running get_test_playbook_id command

    Then:
        - Ensure that the currect pack name returned.
        - Ensure that the currect test name returned.

    """
    test_playbook_id_set = [
        {
            "HelloWorld-Test": {
                "name": "HelloWorld-Test",
                "file_path": "Packs/HelloWorld/TestPlaybooks/playbook-HelloWorld-Test.yml",
                "fromversion": "5.0.0",
                "implementing_scripts": [
                    "HelloWorldScript",
                    "DeleteContext",
                    "FetchFromInstance",
                ],
                "command_to_integration": {
                    "helloworld-say-hello": "",
                    "helloworld-search-alerts": "",
                },
                "pack": "HelloWorld",
            }
        },
        {
            "HighlightWords_Test": {
                "name": "HighlightWords - Test",
                "file_path": "Packs/CommonScripts/TestPlaybooks/playbook-HighlightWords_-_Test.yml",
                "implementing_scripts": [
                    "VerifyHumanReadableContains",
                    "HighlightWords",
                ],
                "pack": "CommonScripts",
            }
        },
        {
            "HTTPListRedirects - Test SSL": {
                "name": "HTTPListRedirects - Test SSL",
                "file_path": "Packs/CommonScripts/TestPlaybooks/playbook-HTTPListRedirects_-_Test_SSL.yml",
                "implementing_scripts": [
                    "PrintErrorEntry",
                    "HTTPListRedirects",
                    "DeleteContext",
                ],
                "pack": "CommonScripts",
            }
        },
    ]

    test_name = "playbook-HelloWorld-Test.yml"
    test_playbook_name, test_playbook_pack = get_test_playbook_id(
        test_playbook_id_set, test_name
    )
    assert test_playbook_name == "HelloWorld-Test"
    assert test_playbook_pack == "HelloWorld"


@pytest.mark.parametrize(
    "url, expected_name",
    [
        (
            "ssh://git@github.com/demisto/content-dist.git",
            ("github.com", "demisto", "content-dist"),
        ),
        (
            "git@github.com:demisto/content-dist.git",
            ("github.com", "demisto", "content-dist"),
        ),
        (
            "https://github.com/demisto/content-dist.git",
            ("github.com", "demisto", "content-dist"),
        ),
        (
            "https://github.com/demisto/content-dist",
            ("github.com", "demisto", "content-dist"),
        ),
        (
            "https://code.pan.run/xsoar/content-dist",
            ("code.pan.run", "xsoar", "content-dist"),
        ),  # gitlab
        (
            "https://code.pan.run/xsoar/content-dist.git",
            ("code.pan.run", "xsoar", "content-dist"),
        ),
        (
            "https://gitlab-ci-token:token@code.pan.run/xsoar/content-dist.git",
            ("code.pan.run", "xsoar", "content-dist"),
        ),
    ],
)
def test_get_current_repo(mocker, url, expected_name):
    import giturlparse

    mocker.patch.object(giturlparse, "parse", return_value=giturlparse.parse(url))
    name = get_current_repo()
    assert name == expected_name


KEBAB_CASES = [
    ("Scan File", "scan-file"),
    ("Scan File-", "scan-file"),
    ("Scan.File", "scan-file"),
    ("*scan,file", "scan-file"),
    ("Scan     File", "scan-file"),
    ("Scan - File", "scan-file"),
    ("Scan-File", "scan-file"),
    ("Scan- File", "scan-file"),
    ("Scan -File", "scan-file"),
    ("Audit - 'X509 Sessions'", "audit-x509-sessions"),
    ("Scan IPs", "scan-ips"),
    ("URL Finder", "url-finder"),
    ("1URL2 3Finder4 5", "1url2-3finder4-5"),
]


@pytest.mark.parametrize("input_str, output_str", KEBAB_CASES)
def test_to_kebab_case(input_str, output_str):
    assert to_kebab_case(input_str) == output_str


YML_DATA_CASES = [
    (
        get_yaml(VALID_INTEGRATION_TEST_PATH),
        FileType.INTEGRATION,
        [
            {"id": "PagerDutyGetAllSchedules"},
            {"id": "PagerDutyGetUsersOnCall"},
            {"id": "PagerDutyGetUsersOnCallNow"},
            {"id": "PagerDutyIncidents"},
            {"id": "PagerDutySubmitEvent"},
            {"id": "PagerDutyGetContactMethods"},
            {"id": "PagerDutyGetUsersNotification"},
        ],
        [],
    ),
    (
        get_yaml(VALID_SCRIPT_PATH),
        FileType.SCRIPT,
        [{"id": "send-notification"}],
        ["TestCreateDuplicates"],
    ),
    (
        get_yaml(TEST_PLAYBOOK),
        FileType.TEST_PLAYBOOK,
        [{"id": "gmail-search", "source": "Gmail"}],
        ["ReadFile", "Get Original Email - Gmail"],
    ),
    (
        get_yaml(VALID_PLAYBOOK_ID_PATH),
        FileType.PLAYBOOK,
        [
            {"id": "setIncident", "source": "Builtin"},
            {"id": "closeInvestigation", "source": "Builtin"},
            {"id": "setIncident", "source": "Builtin"},
        ],
        [
            "Account Enrichment - Generic",
            "EmailAskUser",
            "ADGetUser",
            "IP Enrichment - Generic",
            "IP Enrichment - Generic",
            "AssignAnalystToIncident",
            "access_investigation_-_generic",
        ],
    ),
    (
        get_yaml(VALID_INTEGRATION_TEST_PATH),
        FileType.INTEGRATION,
        [
            {"id": "PagerDutyGetAllSchedules"},
            {"id": "PagerDutyGetUsersOnCall"},
            {"id": "PagerDutyGetUsersOnCallNow"},
            {"id": "PagerDutyIncidents"},
            {"id": "PagerDutySubmitEvent"},
            {"id": "PagerDutyGetContactMethods"},
            {"id": "PagerDutyGetUsersNotification"},
        ],
        [],
    ),
    (
        get_yaml(DUMMY_SCRIPT_PATH),
        FileType.SCRIPT,  # Empty case
        [],
        ["DummyScriptUnified"],
    ),
]


@pytest.mark.parametrize(
    "data, file_type, expected_commands, expected_scripts", YML_DATA_CASES
)
def test_get_scripts_and_commands_from_yml_data(
    data, file_type, expected_commands, expected_scripts
):
    commands, scripts = get_scripts_and_commands_from_yml_data(
        data=data, file_type=file_type
    )
    assert commands == expected_commands
    assert scripts == expected_scripts


class TestIsObjectInIDSet:
    PACK_INFO = {
        "name": "Sample1",
        "current_version": "1.1.1",
        "source": [],
        "categories": ["Data Enrichment & Threat Intelligence"],
        "ContentItems": {
            "incidentTypes": [
                "Phishing",
                "Test Type",
            ],
            "layouts": [
                "Phishing layout",
            ],
            "scripts": [
                "Script1",
                "Script2",
            ],
            "indicatorTypes": ["JARM"],
            "integrations": ["Proofpoint Threat Response"],
        },
    }

    def test_sanity(self):
        """
        Given:
            - Pack object.
            - Object type.
            - ID set.
        When:
            - Searching for an item in a pack.
        Then:
            - Return if the item is in the id set or not.
        """
        assert is_object_in_id_set("Script2", FileType.SCRIPT.value, self.PACK_INFO)
        assert not is_object_in_id_set("Script", FileType.SCRIPT.value, self.PACK_INFO)

    def test_no_such_type(self):
        """
        Given:
            - Pack object.
            - Object type.
            - ID set.
        When:
            - Searching for an item in a pack.
            - Pack doesn't include items of the given type.
        Then:
            - Return if the item is in the id set or not.
        """
        assert not is_object_in_id_set(
            "Integration", FileType.INTEGRATION.value, self.PACK_INFO
        )

    def test_no_item_id_in_specific_type(self):
        """
        Given:
            - Pack object.
            - Object type.
            - ID set.
        When:
            - Searching for an item in a pack.
            - Item ID exists for a different type.
        Then:
            - Return if the item is in the id set or not.
        """
        assert is_object_in_id_set(
            "Phishing layout", FileType.LAYOUTS_CONTAINER.value, self.PACK_INFO
        )
        assert not is_object_in_id_set(
            "Phishing", FileType.LAYOUTS_CONTAINER.value, self.PACK_INFO
        )

    @pytest.mark.parametrize(
        "entity_id, entity_type",
        [
            ("JARM", FileType.REPUTATION.value),
            ("Proofpoint Threat Response", FileType.BETA_INTEGRATION.value),
        ],
    )
    def test_convertion_to_id_set_name(self, entity_id, entity_type):
        """
        Given:
            - Pack object with indicatorType(s)
            - Pack object with beta integration

        When:
            - Searching for an IndicatorType in the id_set.
            - Searching for an beta integration in the id_set.

        Then:
            - make sure the indicator type is found.
            - make sure the beta integration is found.
        """
        assert is_object_in_id_set(entity_id, entity_type, self.PACK_INFO)


class TestGetItemMarketplaces:
    @staticmethod
    def test_item_has_marketplaces_field():
        """
        Given
            - item declares marketplaces
        When
            - getting the marketplaces of an item
        Then
            - return the item's marketplaces
        """
        item_data = {
            "name": "Integration",
            "marketplaces": ["xsoar", "marketplacev2"],
        }
        marketplaces = get_item_marketplaces(
            "Packs/PackID/Integrations/Integration/Integration.yml", item_data=item_data
        )

        assert "xsoar" in marketplaces
        assert "marketplacev2" in marketplaces

    @staticmethod
    def test_only_pack_has_marketplaces():
        """
        Given
            - item does not declare marketplaces
            - pack declares marketplaces
        When
            - getting the marketplaces of an item
        Then
            - return the pack's marketplaces
        """
        item_data = {
            "name": "Integration",
            "pack": "PackID",
        }
        packs = {
            "PackID": {
                "id": "PackID",
                "marketplaces": ["xsoar", "marketplacev2"],
            }
        }
        marketplaces = get_item_marketplaces(
            "Packs/PackID/Integrations/Integration/Integration.yml",
            item_data=item_data,
            packs=packs,
        )

        assert "xsoar" in marketplaces
        assert "marketplacev2" in marketplaces

    @staticmethod
    def test_no_marketplaces_specified():
        """
        Given
            - item does not declare marketplaces
            - pack does not declare marketplaces
        When
            - getting the marketplaces of an item
        Then
            - return the default marketplaces (only xsoar)
        """
        item_data = {
            "name": "Integration",
            "pack": "PackID",
        }
        packs = {
            "PackID": {
                "id": "PackID",
            }
        }
        marketplaces = get_item_marketplaces(
            "Packs/PackID/Integrations/Integration/Integration.yml",
            item_data=item_data,
            packs=packs,
        )

        assert len(marketplaces) == 1
        assert "xsoar" in marketplaces

    @staticmethod
    def test_pack_not_in_cache(mocker):
        """
        Given
            - item does not declare marketplaces
            - pack does not appear in pack cache
        When
            - getting the marketplaces of an item
        Then
            - return the marketplaces from the pack_metadata
        """
        item_data = {
            "name": "Integration",
            "pack": "PackID",
        }
        packs = {
            "PackID2": {
                "id": "PackID2",
            }
        }
        mocker.patch(
            "demisto_sdk.commands.common.tools.get_mp_types_from_metadata_by_item",
            return_value=["marketplacev2"],
        )
        marketplaces = get_item_marketplaces(
            "Packs/PackID/Integrations/Integration/Integration.yml",
            item_data=item_data,
            packs=packs,
        )

        assert len(marketplaces) == 1
        assert "marketplacev2" in marketplaces


class TestTagParser:
    def test_no_text_to_remove(self):
        """
        Given:
            - prefix <>
            - suffix </>
            - text with no prefix / suffix
        When:
            - Calling TagParser.parse()
        Then:
            - Text shouldn't change
        """
        prefix = "<>"
        suffix = "</>"
        text = "some text"
        tag_parser = TagParser("FAKE_LABEL")
        for tag in (prefix, suffix):
            assert tag_parser.parse(text + tag) == text + tag

    def test_remove_text(self):
        """
        Given:
            - prefix <>
            - suffix </>
            - text with prefix + suffix
        When:
            - Calling TagParser.parse() with text removal
        Then:
            - Text shouldn't have tags or their text
        """
        text = "some text<~>more text</~>"
        expected_text = "some text"
        tag_parser = TagParser("")
        assert tag_parser.parse(text, True) == expected_text

    def test_remove_tags_only(self):
        """
        Given:
            - prefix <>
            - suffix </>
            - text with prefix + suffix
        When:
            - Calling TagParser.parse() without text removal
        Then:
            - Text shouldn't have tags, but keep the text
        """
        text = "some text <~>tag text</~>"
        expected_text = "some text tag text"
        tag_parser = TagParser("")
        assert tag_parser.parse(text) == expected_text


class TestMarketplaceTagParser:
    MARKETPLACE_TAG_PARSER = MarketplaceTagParser()
    XSOAR_PREFIX = XSOAR_PREFIX_TAG
    XSOAR_SUFFIX = XSOAR_SUFFIX_TAG
    XSOAR_INLINE_PREFIX = XSOAR_INLINE_PREFIX_TAG
    XSOAR_INLINE_SUFFIX = XSOAR_INLINE_SUFFIX_TAG

    XSIAM_PREFIX = XSIAM_PREFIX_TAG
    XSIAM_SUFFIX = XSIAM_SUFFIX_TAG
    XSIAM_INLINE_PREFIX = XSIAM_INLINE_PREFIX_TAG
    XSIAM_INLINE_SUFFIX = XSIAM_INLINE_SUFFIX_TAG

    XPANSE_PREFIX = XPANSE_PREFIX_TAG
    XPANSE_SUFFIX = XPANSE_SUFFIX_TAG
    XPANSE_INLINE_PREFIX = XPANSE_INLINE_PREFIX_TAG
    XPANSE_INLINE_SUFFIX = XPANSE_INLINE_SUFFIX_TAG

    XSOAR_SAAS_PREFIX = XSOAR_SAAS_PREFIX_TAG
    XSOAR_SAAS_SUFFIX = XSOAR_SAAS_SUFFIX_TAG
    XSOAR_SAAS_INLINE_PREFIX = XSOAR_SAAS_INLINE_PREFIX_TAG
    XSOAR_SAAS_INLINE_SUFFIX = XSOAR_SAAS_INLINE_SUFFIX_TAG

    XSOAR_ON_PREM_PREFIX = XSOAR_ON_PREM_PREFIX_TAG
    XSOAR_ON_PREM_SUFFIX = XSOAR_ON_PREM_SUFFIX_TAG
    XSOAR_ON_PREM_INLINE_PREFIX = XSOAR_ON_PREM_INLINE_PREFIX_TAG
    XSOAR_ON_PREM_INLINE_SUFFIX = XSOAR_ON_PREM_INLINE_SUFFIX_TAG

    TEXT_WITH_TAGS = f"""
### Sections:
{XSOAR_PREFIX} - ALL XSOAR MARKETPLACE PARAGRAPH {XSOAR_SUFFIX}
{XSIAM_PREFIX} - XSIAM PARAGRAPH {XSIAM_SUFFIX}
{XPANSE_PREFIX} - XPANSE PARAGRAPH {XPANSE_SUFFIX}
{XSOAR_SAAS_PREFIX} - ONLY XSOAR_SAAS PARAGRAPH {XSOAR_SAAS_SUFFIX}
{XSOAR_ON_PREM_PREFIX} - ONLY XSOAR_ON_PREM PARAGRAPH {XSOAR_ON_PREM_SUFFIX}
### Inline:
{XSOAR_INLINE_PREFIX} all xsoar marketplaces inline text {XSOAR_INLINE_SUFFIX}
{XSIAM_INLINE_PREFIX} xsiam inline text {XSIAM_INLINE_SUFFIX}
{XPANSE_INLINE_PREFIX} xpanse inline text {XPANSE_INLINE_SUFFIX}
{XSOAR_SAAS_INLINE_PREFIX} xsoar_saas inline test {XSOAR_SAAS_INLINE_SUFFIX}
{XSOAR_ON_PREM_INLINE_PREFIX} xsoar_on_prem inline test {XSOAR_ON_PREM_INLINE_SUFFIX}"""

    @pytest.mark.parametrize(
        "res_file, marketplace_version",
        [
            ("EDL_xsoar_res.md", MarketplaceVersions.XSOAR.value),
            ("EDL_xsiam_res.md", MarketplaceVersions.MarketplaceV2.value),
        ],
    )
    def test_xsoar_tag_only_on_edl_description(self, res_file, marketplace_version):
        """
        Given:
            - Am example of a real complex file with tags of xsoar and xsiam.
        When:
            - Parsing with the tag parser for xsoar mp
            - Parsing with the tag parser for xsiam mp
        Then:
            - Validate the results fit the prepared marketplace
        """
        test_files_folder = Path(os.path.abspath(__file__)).parent / "test_files"
        edl_test_file = test_files_folder / "EDL_description.md"
        res_text_after_filter_by_mp = test_files_folder / res_file

        self.MARKETPLACE_TAG_PARSER.marketplace = marketplace_version
        with open(edl_test_file, "r") as f:
            edl_content = f.read()

        actual = self.MARKETPLACE_TAG_PARSER.parse_text(edl_content)

        with open(res_text_after_filter_by_mp, "r") as f:
            res = f.read()

        assert actual == res

    def check_prefix_not_in_text(self, actual):
        assert self.XSOAR_PREFIX not in actual
        assert self.XSIAM_PREFIX not in actual
        assert self.XPANSE_PREFIX not in actual
        assert self.XSOAR_SAAS_PREFIX not in actual
        assert self.XSOAR_ON_PREM_PREFIX not in actual

    def check_xsiam_not_in_text(self, actual):
        assert "XSIAM" not in actual
        assert "xsiam" not in actual

    def check_xpanse_not_in_text(self, actual):
        assert "XPANSE" not in actual
        assert "xpanse" not in actual

    def check_xsoar_saas_not_in_text(self, actual):
        assert "XSOAR_SAAS" not in actual
        assert "XSOAR saas" not in actual

    def check_xsoar_on_prem_not_in_text(self, actual):
        assert "XSOAR_ON_PREM" not in actual
        assert "xsoar_on_prem" not in actual

    def check_all_xsoar_not_in_text(self, actual):
        assert "ALL XSOAR MARKETPLACE PARAGRAPH" not in actual
        assert "all xsoar marketplaces inline text" not in actual

    def test_invalid_marketplace_version(self):
        """
        Given:
            - Invalid marketplace version
            - Text with XSOAR, XPANSE and XSIAM tags
        When:
            - Calling MarketplaceTagParser.parse_text()
        Then:
            - Remove all tags and their text
        """
        self.MARKETPLACE_TAG_PARSER.marketplace = "invalid"
        actual = self.MARKETPLACE_TAG_PARSER.parse_text(self.TEXT_WITH_TAGS)
        assert "### Sections:" in actual
        assert "### Inline:" in actual
        self.check_prefix_not_in_text(actual)
        self.check_xsiam_not_in_text(actual)
        self.check_xpanse_not_in_text(actual)
        self.check_xsoar_saas_not_in_text(actual)
        self.check_xsoar_on_prem_not_in_text(actual)
        self.check_all_xsoar_not_in_text(actual)

    def test_xsoar_marketplace_version(self):
        """
        Given:
            - xsoar marketplace version
            - Text with XSOAR tags and XSIAM tags
        When:
            - Calling MarketplaceTagParser.parse_text()
        Then:
            - Remove all XSIAM and XPANSE tags and their text, and keep XSOAR text with tags
        """
        self.MARKETPLACE_TAG_PARSER.marketplace = MarketplaceVersions.XSOAR.value
        actual = self.MARKETPLACE_TAG_PARSER.parse_text(self.TEXT_WITH_TAGS)
        assert "### Sections:" in actual
        assert "### Inline:" in actual
        assert "ALL XSOAR MARKETPLACE PARAGRAPH" in actual
        assert "all xsoar marketplaces inline text" in actual
        assert "xsoar_on_prem" in actual
        assert "XSOAR_ON_PREM" in actual
        self.check_prefix_not_in_text(actual)
        self.check_xsiam_not_in_text(actual)
        self.check_xpanse_not_in_text(actual)
        self.check_xsoar_saas_not_in_text(actual)

    def test_xsiam_marketplace_version(self):
        """
        Given:
            - xsiam marketplace version
            - Text with XSOAR, XPANSE and XSIAM tags
        When:
            - Calling MarketplaceTagParser.parse_text()
        Then:
            - Remove all XSOAR and XPANSE tags and their text, and keep XSIAM text with tags
        """
        self.MARKETPLACE_TAG_PARSER.marketplace = (
            MarketplaceVersions.MarketplaceV2.value
        )
        actual = self.MARKETPLACE_TAG_PARSER.parse_text(self.TEXT_WITH_TAGS)
        assert "### Sections:" in actual
        assert "### Inline:" in actual
        assert "XSIAM" in actual
        assert "xsiam" in actual
        self.check_all_xsoar_not_in_text(actual)
        self.check_xpanse_not_in_text(actual)
        self.check_xsoar_on_prem_not_in_text(actual)
        self.check_xsoar_saas_not_in_text(actual)
        self.check_prefix_not_in_text(actual)

    def test_xpanse_marketplace_version(self):
        """
        Given:
            - xpanse marketplace version
            - Text with XSOAR, XPANSE and XSIAM tags
        When:
            - Calling MarketplaceTagParser.parse_text()
        Then:
            - Remove all XSOAR and XSIAM tags and their text, and keep XPANSE text with tags
        """
        self.MARKETPLACE_TAG_PARSER.marketplace = MarketplaceVersions.XPANSE.value
        actual = self.MARKETPLACE_TAG_PARSER.parse_text(self.TEXT_WITH_TAGS)
        assert "### Sections:" in actual
        assert "### Inline:" in actual
        assert "XPANSE" in actual
        assert "xpanse" in actual
        self.check_prefix_not_in_text(actual)
        self.check_all_xsoar_not_in_text(actual)
        self.check_xsiam_not_in_text(actual)
        self.check_xsoar_on_prem_not_in_text(actual)
        self.check_xsoar_saas_not_in_text(actual)

    def test_xsoar_saas_marketplace_version(self):
        """
        Check that xsoar_saas text and xsoar text is in text
        """
        self.MARKETPLACE_TAG_PARSER.marketplace = MarketplaceVersions.XSOAR_SAAS.value
        actual = self.MARKETPLACE_TAG_PARSER.parse_text(self.TEXT_WITH_TAGS)
        assert "### Sections:" in actual
        assert "### Inline:" in actual
        assert "xsoar_saas" in actual
        assert "XSOAR_SAAS" in actual
        assert "ALL XSOAR MARKETPLACE PARAGRAPH" in actual
        assert "all xsoar marketplaces inline text" in actual
        self.check_prefix_not_in_text(actual)
        self.check_xsiam_not_in_text(actual)
        self.check_xpanse_not_in_text(actual)
        self.check_xsoar_on_prem_not_in_text(actual)

    def test_xsoar_on_prem_marketplace_version(self):
        """
        Check that xsoar_saas text and xsoar text is in text
        """
        self.MARKETPLACE_TAG_PARSER.marketplace = (
            MarketplaceVersions.XSOAR_ON_PREM.value
        )
        actual = self.MARKETPLACE_TAG_PARSER.parse_text(self.TEXT_WITH_TAGS)
        assert "### Sections:" in actual
        assert "### Inline:" in actual
        assert "xsoar_on_prem" in actual
        assert "XSOAR_ON_PREM" in actual
        assert "ALL XSOAR MARKETPLACE PARAGRAPH" in actual
        assert "all xsoar marketplaces inline text" in actual
        self.check_prefix_not_in_text(actual)
        self.check_xsiam_not_in_text(actual)
        self.check_xpanse_not_in_text(actual)
        self.check_xsoar_saas_not_in_text(actual)

    def test_xsoar_should_remove_text(self):
        """
        Check that if xsoar tag is specified all the xsoar-saas marketplaces will be should removed true.
        """
        mtp = MarketplaceTagParser(MarketplaceVersions.XSOAR.value)
        assert mtp._should_remove_xsoar_text is False
        assert mtp._should_remove_xsoar_on_prem_text is False
        assert mtp._should_remove_xsoar_saas_text is True
        mtp = MarketplaceTagParser(MarketplaceVersions.XSOAR_SAAS.value)
        assert mtp._should_remove_xsoar_text is False
        assert mtp._should_remove_xsoar_on_prem_text is True
        assert mtp._should_remove_xsoar_saas_text is False
        mtp = MarketplaceTagParser(MarketplaceVersions.XSOAR_ON_PREM.value)
        assert mtp._should_remove_xsoar_text is False
        assert mtp._should_remove_xsoar_on_prem_text is False
        assert mtp._should_remove_xsoar_saas_text is True
        mtp = MarketplaceTagParser(MarketplaceVersions.MarketplaceV2.value)
        assert mtp._should_remove_xsoar_text is True


@pytest.mark.parametrize(
    "data, answer",
    [
        ({"brandName": "TestBrand"}, "TestBrand"),
        ({"id": "TestID"}, "TestID"),
        ({"name": "TestName"}, "TestName"),
        ({"TypeName": "TestType"}, "TestType"),
        ({"display": "TestDisplay"}, "TestDisplay"),
        ({"trigger_name": "T Name"}, "T Name"),
        ({"layout": {"id": "Testlayout"}}, "Testlayout"),
        ({"dashboards_data": [{"name": "D Name"}]}, "D Name"),
        ({"templates_data": [{"report_name": "R Name"}]}, "R Name"),
        ({"id": "Test1", "details": "Test2"}, "Test2"),  # IndicatorType Content Items
    ],
)
def test_get_display_name(data, answer, tmpdir):
    """
    Given
        - Pack to update release notes
    When
        - get_display_name with file path is called
    Then
       - Returned name determined by the key of the data loaded from the file
    """
    file = File(tmpdir / "test_file.json", "", json.dumps(data))
    assert get_display_name(file.path) == answer


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
    "path,expected_type",
    (
        ("Packs/myPack/Scripts/README.md", FileType.README),
        ("Packs/myPack/ReleaseNotes/1_0_0.md", FileType.RELEASE_NOTES),
        ("Packs/myPack/ReleaseNotes/1_0_0.json", FileType.RELEASE_NOTES_CONFIG),
        ("Packs/myPack/Lists/list.json", FileType.LISTS),
        ("Packs/myPack/Jobs/job.json", FileType.JOB),
        (f"Packs/myPack/{INDICATOR_TYPES_DIR}/indicator.json", FileType.REPUTATION),
        (
            f"Packs/myPack/{XSIAM_DASHBOARDS_DIR}/dashboard.json",
            FileType.XSIAM_DASHBOARD,
        ),
        (
            f"Packs/myPack/{XSIAM_DASHBOARDS_DIR}/dashboard_image.png",
            FileType.XSIAM_DASHBOARD_IMAGE,
        ),
        (f"Packs/myPack/{XSIAM_REPORTS_DIR}/report.json", FileType.XSIAM_REPORT),
        (
            f"Packs/myPack/{XSIAM_REPORTS_DIR}/report_image.png",
            FileType.XSIAM_REPORT_IMAGE,
        ),
        (f"Packs/myPack/{TRIGGER_DIR}/trigger.json", FileType.TRIGGER),
        ("Packs/myPack/pack_metadata.json", FileType.METADATA),
        (XSOAR_CONFIG_FILE, FileType.XSOAR_CONFIG),
        ("CONTRIBUTORS.json", FileType.CONTRIBUTORS),
        ("Packs/myPack/Author_image.png", FileType.AUTHOR_IMAGE),
        (f"{DOC_FILES_DIR}/image.png", FileType.DOC_IMAGE),
        ("Packs/myPack/Integrations/myIntegration/some_image.png", FileType.IMAGE),
        (
            "Packs/myPack/Integrations/myIntegration/myIntegration.ps1",
            FileType.POWERSHELL_FILE,
        ),
        (
            "Packs/myPack/Integrations/myIntegration/myIntegration.py",
            FileType.PYTHON_FILE,
        ),
        (
            "Packs/myPack/Integrations/myIntegration/myIntegration.js",
            FileType.JAVASCRIPT_FILE,
        ),
        (
            "Packs/myPack/Integrations/myIntegration/myIntegration.xif",
            FileType.XIF_FILE,
        ),
        (".gitlab/some_file.yml", FileType.BUILD_CONFIG_FILE),
        (".circleci/some_file.yml", FileType.BUILD_CONFIG_FILE),
        ("Packs/myPack/Scripts/myScript/myScript.yml", FileType.SCRIPT),
        ("Packs/myPack/Scripts/script-myScript.yml", FileType.SCRIPT),
        (f"Packs/myPack/{PACK_IGNORE}", FileType.PACK_IGNORE),
        (f"Packs/myPack/{FileType.SECRET_IGNORE}", FileType.SECRET_IGNORE),
        (f"Packs/myPack/{DOC_FILES_DIR}/foo.md", FileType.DOC_FILE),
        ("Packs/myPack/some_random_file", None),
        ("some_random_file_not_under_Packs", None),
    ),
)
def test_find_type_by_path(path: Path, expected_type: Optional[FileType]):
    assert find_type_by_path(path) == expected_type


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Employee Number", "employeenumber"),
        ("Employee_Number", "employeenumber"),
        ("Employee & Number", "employeenumber"),
        ("Employee, Number?", "employeenumber"),
        ("Employee Number!!!", "employeenumber"),
    ],
)
def test_field_to_cliname(value: str, expected: str):
    assert field_to_cli_name(value) == expected


def test_get_core_packs(mocker):
    def mock_get_remote_file(full_file_path, git_content_config):
        if MARKETPLACE_TO_CORE_PACKS_FILE[MarketplaceVersions.XSOAR] in full_file_path:
            return {
                "core_packs_list": ["Base", "CommonScripts", "Active_Directory_Query"]
            }
        elif (
            MARKETPLACE_TO_CORE_PACKS_FILE[MarketplaceVersions.MarketplaceV2]
            in full_file_path
        ):
            return {"core_packs_list": ["Base", "CommonScripts", "Core"]}
        elif (
            MARKETPLACE_TO_CORE_PACKS_FILE[MarketplaceVersions.XPANSE] in full_file_path
        ):
            return ["Base", "CommonScripts", "Core"]
        return None

    mocker.patch.object(tools, "get_remote_file", side_effect=mock_get_remote_file)
    mp_to_core_packs = get_marketplace_to_core_packs()
    assert len(mp_to_core_packs) == len(MarketplaceVersions)
    for mp_core_packs in mp_to_core_packs.values():
        assert "Base" in mp_core_packs


@pytest.mark.parametrize(
    "mapping_value, expected_output",
    [
        ("employeeid", "employeeid"),
        ("${employeeid}", "employeeid"),
        ("employeeid.hello", "employeeid"),
        ("employeeid.[0].hi", "employeeid"),
        ("${employeeid.hello}", "employeeid"),
        ("${employeeid.[0]}", "employeeid"),
        ("${.=1}", ""),
        (".", ""),
        ('"not a field"', ""),
    ],
)
def test_extract_field_from_mapping(mapping_value, expected_output):
    assert extract_field_from_mapping(mapping_value) == expected_output


def test_get_from_version(mocker):
    mocker.patch.object(tools, "get_yaml", return_value={"fromversion": "6.1.0"})
    assert get_from_version("fake_file_path.yml") == "6.1.0"


def test_get_from_version_error(mocker):
    mocker.patch.object(tools, "get_yaml", return_value=["item1, item2"])
    with pytest.raises(ValueError) as e:
        get_from_version("fake_file_path.yml")

    assert str(e.value) == "yml file returned is not of type dict"


@pytest.mark.parametrize(
    "value, expected_output",
    [
        (None, False),
        (True, True),
        (False, False),
        ("yes", True),
        ("Yes", True),
        ("YeS", True),
        ("True", True),
        ("t", True),
        ("y", True),
        ("Y", True),
        ("1", True),
        ("no", False),
        ("No", False),
        ("nO", False),
        ("NO", False),
        ("false", False),
        ("False", False),
        ("F", False),
        ("n", False),
        ("N", False),
        ("0", False),
    ],
)
def test_str2bool(value, expected_output):
    assert str2bool(value) == expected_output


PATH_1 = Path("1.yml")
PATH_2 = Path("2.yml")


@pytest.mark.parametrize(
    "input_paths, expected",
    [
        (PATH_1, (PATH_1,)),
        (str(PATH_1), (PATH_1,)),
        (",".join((str(PATH_1), str(PATH_2))), (PATH_1, PATH_2)),
        (
            (
                PATH_1,
                PATH_2,
            ),
            (PATH_1, PATH_2),
        ),
        ([PATH_1, PATH_2], (PATH_1, PATH_2)),
        ((), ()),
        ("", ()),
        (None, ()),
        (
            "test/test.yml,test1/test1.yml",
            (Path("test/test.yml"), Path("test1/test1.yml")),
        ),
    ],
)
def test_parse_multiple_path_inputs(input_paths, expected: Tuple[Path, ...]):
    """
    Given:
        Some variations of inputs
    When:
        - Running parse_multiple_path_inputs
    Then:
        - Ensure that a tuple of Path is always returned
        - Ensure input is handled when a comma-separated string is sent

    """
    assert parse_multiple_path_inputs(input_paths) == expected


@pytest.mark.parametrize("input_paths", (1, True))
def test_parse_multiple_path_inputs_error(input_paths):
    """
    Given:
        An unsupported input to test_parse_multiple_path_inputs
    When:
        - Running parse_multiple_path_inputs fomction
    Then:
        - Ensure an error is raised

    """
    with pytest.raises(ValueError, match=f"Cannot parse paths from {input_paths}"):
        parse_multiple_path_inputs(input_paths)


@pytest.mark.parametrize(
    "content_item_id, file_type, test_playbooks, no_test_playbooks_explicitly, expected_test_list",
    [
        (
            "PagerDuty v2",
            "integration",
            ["No tests"],
            True,
            [
                {"integrations": ["PagerDuty v1"], "playbookID": "PagerDutyV1 Test"},
                {"integrations": ["PagerDuty v1"], "playbookID": "PagerDuty Test"},
                {
                    "integrations": "Account Enrichment",
                    "playbookID": "Account Enrichment Test",
                },
                {
                    "integrations": "TestCreateDuplicates",
                    "playbookID": "TestCreateDuplicates Test",
                },
            ],
        ),
        (
            "PagerDuty v2",
            "integration",
            ["PagerDutyV2 Test"],
            False,
            [
                {"integrations": ["PagerDuty v1"], "playbookID": "PagerDutyV1 Test"},
                {"integrations": ["PagerDuty v1"], "playbookID": "PagerDuty Test"},
                {
                    "integrations": "Account Enrichment",
                    "playbookID": "Account Enrichment Test",
                },
                {
                    "integrations": "TestCreateDuplicates",
                    "playbookID": "TestCreateDuplicates Test",
                },
            ],
        ),
        (
            "Account Enrichment",
            "integration",
            ["No tests"],
            False,
            [
                {"integrations": ["PagerDuty v1"], "playbookID": "PagerDutyV1 Test"},
                {
                    "integrations": ["PagerDuty v1", "PagerDuty v2"],
                    "playbookID": "PagerDuty Test",
                },
                {"integrations": "PagerDuty v2", "playbookID": "PagerDutyV2 Test"},
                {"integrations": "PagerDuty v2", "playbookID": "PagerDutyV2 Test"},
                {
                    "integrations": "TestCreateDuplicates",
                    "playbookID": "TestCreateDuplicates Test",
                },
            ],
        ),
        (
            "Account Enrichment Test",
            "playbook",
            ["No tests"],
            False,
            [
                {"integrations": ["PagerDuty v1"], "playbookID": "PagerDutyV1 Test"},
                {
                    "integrations": ["PagerDuty v1", "PagerDuty v2"],
                    "playbookID": "PagerDuty Test",
                },
                {"integrations": "PagerDuty v2", "playbookID": "PagerDutyV2 Test"},
                {"integrations": "PagerDuty v2", "playbookID": "PagerDutyV2 Test"},
                {
                    "integrations": "TestCreateDuplicates",
                    "playbookID": "TestCreateDuplicates Test",
                },
            ],
        ),
    ],
)
def test_search_and_delete_from_conf(
    content_item_id,
    file_type,
    test_playbooks,
    no_test_playbooks_explicitly,
    expected_test_list,
):
    """
    Given:
          content_item_id, file_type, test_playbooks, no_test_playbooks_explicitly
        - Case A: PagerDuty v2 integration without tests.
        - Case B: PagerDuty v2 integration with tests.
        - Case C: Account Enrichment integration without tests.
        - Case D: Account Enrichment playbook without tests.

    When:
        - check that the test_search_and_delete_from_conf works as expected.

    Then:
        - Case A: Delete PagerDuty v2 integration.
        - Case B: Delete PagerDuty v2 integration.
        - Case C: Delete Account Enrichment integration.
        - Case D: Delete Account Enrichment integration.
    """
    CONF_JSON_ORIGINAL_CONTENT = {
        "tests": [
            {"integrations": ["PagerDuty v1"], "playbookID": "PagerDutyV1 Test"},
            {
                "integrations": ["PagerDuty v1", "PagerDuty v2"],
                "playbookID": "PagerDuty Test",
            },
            {"integrations": "PagerDuty v2", "playbookID": "PagerDutyV2 Test"},
            {"integrations": "PagerDuty v2", "playbookID": "PagerDutyV2 Test"},
            {
                "integrations": "Account Enrichment",
                "playbookID": "Account Enrichment Test",
            },
            {
                "integrations": "TestCreateDuplicates",
                "playbookID": "TestCreateDuplicates Test",
            },
        ]
    }
    conf_test = search_and_delete_from_conf(
        CONF_JSON_ORIGINAL_CONTENT["tests"],
        content_item_id,
        file_type,
        test_playbooks,
        no_test_playbooks_explicitly,
    )
    assert conf_test == expected_test_list


@pytest.mark.parametrize(
    "test_config, file_type, expected_result",
    [
        (
            {"integrations": "PagerDuty v2", "playbookID": "PagerDutyV2 Test"},
            "integration",
            False,
        ),
        (
            {"integrations": ["PagerDuty v2"], "playbookID": "PagerDutyV2 Test"},
            "integration",
            False,
        ),
        (
            {
                "integrations": ["PagerDuty v2", "PagerDuty v3"],
                "playbookID": "PagerDuty Test",
            },
            "playbook",
            False,
        ),
        (
            {
                "integrations": ["PagerDuty v2", "PagerDuty v3"],
                "playbookID": "PagerDuty Test",
            },
            "integration",
            True,
        ),
    ],
)
def test_is_content_item_dependent_in_conf(test_config, file_type, expected_result):
    """
    Given:
          test_config - A line from the conf.json and file_type.
        - Case A: test_config with a string in the "integrations" key and integration file type.
        - Case B: test_config with an array with len 1 in the "integrations" key and playbook file type.
        - Case C: test_config with an array with len 2 in the "integrations" key and testplaybook file type.
        - Case D: test_config with an array in the "integrations" key and integration file type.

    When:
        - check that the is_content_item_dependent_in_conf works as expected.

    Then:
        - Ensure that the result in correct.
    """
    result = is_content_item_dependent_in_conf(test_config, file_type)
    assert result == expected_result


@pytest.mark.parametrize(
    "file_paths, skip_file_types, expected_packs",
    [
        (
            [
                "Packs/PackA/pack_metadata.json",
                "Tests/scripts/infrastructure_tests/tests_data/collect_tests/R/Packs/PackB/pack_metadata.json",
            ],
            None,
            {"PackA"},
        ),
        (
            [("Packs/PackA/pack_metadata.json", "Packs/PackB/pack_metadata.json")],
            None,
            {"PackB"},
        ),
        (
            ["Packs/PackA/pack_metadata.json", "Packs/PackB/ReleaseNotes/1_0_0.md"],
            {FileType.RELEASE_NOTES},
            {"PackA"},
        ),
    ],
)
def test_get_pack_names_from_files(file_paths, skip_file_types, expected_packs):
    """
    Given:
        - Case A: Real packs paths and infra file paths.
        - Case B: File paths in tuple.
        - Case C: File paths and file types to skip.

    When:
        - Running get_pack_names_from_files.

    Then:
        - Ensure that the result is as expected.
    """
    packs_result = get_pack_names_from_files(file_paths, skip_file_types)
    assert packs_result == expected_packs


@pytest.mark.parametrize(
    "file_name, expected_hash",
    [
        ("file.txt", "c8c54e11b1cb27c3376fa82520d53ef9932a02c0"),
        ("file2.txt", "f1e01f0882e1f08f00f38d0cd60a850dc9288188"),
    ],
)
def test_sha1_file(file_name, expected_hash):
    """
    Given:
        - A file path
    When:
        - Checking the hash
    Then:
        Validate that the hash is correct, even after moving to a different location
    """
    path_str = f"{GIT_ROOT}/demisto_sdk/commands/common/tests/test_files/test_sha1/content/{file_name}"
    assert tools.sha1_file(path_str) == expected_hash
    assert tools.sha1_file(Path(path_str)) == expected_hash
    # move file to a different location and check that the hash is still the same
    with NamedTemporaryFile() as temp_dir:
        shutil.copy(path_str, temp_dir.name)
        assert tools.sha1_file(temp_dir.name) == expected_hash


def test_sha1_dir():
    """
    Given:
        - A directory path
    When:
        - Checking the hash
    Then:
        Validate that the hash is correct, even after moving to a different location
    """
    path_str = f"{GIT_ROOT}/demisto_sdk/commands/common/tests/test_files/test_sha1"
    expected_hash = "70feabcd73ccbcb14201453942edf4a5fb4c4aac"
    assert tools.sha1_dir(path_str) == expected_hash
    assert tools.sha1_dir(Path(path_str)) == expected_hash
    # move dir to a different location and check that the hash is still the same
    with TemporaryDirectory() as temp_dir:
        dest = Path(temp_dir, "dest")
        shutil.copytree(path_str, dest)
        assert tools.sha1_dir(dest) == expected_hash


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
    output = tools.find_pack_folder(input_path)
    assert expected_output == str(output)


@pytest.mark.parametrize(
    "input_path, expected_output",
    [
        (
            Path(
                "/User/username/content/Packs/MyPack/Integrations/MyIntegration/MyIntegration.yml"
            ),
            Path("/User/username/content"),
        ),
        (Path("/User/username/content/Packs"), Path("/User/username/content")),
    ],
)
def test_get_content_path(input_path, expected_output):
    """
    Given:
        - A path to a file or directory in the content repo
    When:
        - Running get_content_path
    Then:
        Validate that the given path is correct
    """
    assert tools.get_content_path(input_path) == expected_output


def test_get_content_path_no_remote(mocker):
    """
    Given:
        - A path to a file or directory in the content repo, with no remote
    When:
        - Running get_content_path
    Then:
        Validate that a warning is issued as (resulting from a raised exception).
    """
    from git import Repo  # noqa: TID251

    def raise_value_exception(name):
        raise ValueError()

    mocker.patch.object(Repo, "remote", side_effect=raise_value_exception)
    mocker.patch(
        "demisto_sdk.commands.common.tools.is_external_repository", return_value=False
    )
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    tools.get_content_path(Path("/User/username/test"))
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "[yellow]Please run demisto-sdk in content repository![/yellow]",
    )


@pytest.mark.parametrize(
    "string, expected_result",
    [
        ("1", True),
        ("12345678", True),
        ("1689889076", True),
        ("1626858896", True),
        ("d", False),
        ("123d", False),
        ("123d", False),
        ("2023-07-21T12:34:56Z", False),
        ("07/21/23", False),
        ("21 July 2023", False),
        ("Thu, 21 Jul 2023 12:34:56 +0000", False),
    ],
)
def test_is_epoch_datetime(string: str, expected_result: bool):
    """
    Given:
          test_config - A line from the conf.json and file_type.
        - Case A + B + C + D: valid epoch_datetime
        - Case E + F + G + H + I + J + K: ivalid epoch datetime

    When:
        - run test_is_epoch_datetime

    Then:
        - Ensure that the result in correct.
    """
    from demisto_sdk.commands.common.tools import is_epoch_datetime

    assert is_epoch_datetime(string) == expected_result


@pytest.mark.parametrize(
    "dict, paths, value, expected_dict",
    [
        ({"test": "1"}, ["test"], 2, {"test": 2}),
        ({"test": [1, 2, 3, 4]}, ["test[3]"], 2, {"test": [1, 2, 3, 2]}),
        ({"test1": "1"}, ["test2", "test1"], 2, {"test1": 2}),
        ({"test": "1"}, ["test2", "test1"], 2, {"test": "1", "test1": 2}),
        ({"test": {"test2": 1}}, ["test.test2"], 2, {"test": {"test2": 2}}),
    ],
)
def test_set_value(dict, paths, value, expected_dict):
    """
    Given:
        a dictionary, path / list of paths, and a value to insert to the dict.
        - Case 1: dict with items only in the root, a list with a path that exist in the dict, and a value to set there.
        - Case 2: dict with a list in the root, a list with a path with the index in the list to replace, and a value to set there.
        - Case 3: dict with items only in the root, a list of possible paths where one of them is in the dict, and a value to set there.
        - Case 4: dict with items only in the root, a list of possible paths where none of them is in the dict, and a value to set there.
        - Case 5: dict with items not only in the root, a list with a path not to the root that exist in the dict, and a value to set there.

    When:
        - run set_value
    Then:
        - Ensure that the value was inserted in the right place.
        - Case 1: the dict should replce the value in the key.
        - Case 2: the dict will have the value in the right index in the list.
        - Case 3: the dict has the value changed in the key that existed and will not add keys in paths that doesn't exist.
        - Case 4: the dict has the value added in the last given key.
        - Case 5: the dict should replce the value in the key.
    """
    set_value(dict, paths, value)
    assert expected_dict == dict


def test_check_timestamp_format():
    """
    Given
    - timestamps in various formats.

    When
    - Running check_timestamp_format on them.

    Then
    - Ensure True for iso format and False for any other format.
    """
    good_format_timestamp = "2020-04-14T00:00:00Z"
    missing_z = "2020-04-14T00:00:00"
    missing_t = "2020-04-14 00:00:00Z"
    only_date = "2020-04-14"
    with_hyphen = "2020-04-14T00-00-00Z"
    assert check_timestamp_format(good_format_timestamp)
    assert not check_timestamp_format(missing_t)
    assert not check_timestamp_format(missing_z)
    assert not check_timestamp_format(only_date)
    assert not check_timestamp_format(with_hyphen)
