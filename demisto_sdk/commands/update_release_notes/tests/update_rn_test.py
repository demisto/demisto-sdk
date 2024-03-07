import glob
import os
import pathlib
import shutil
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional
from unittest import mock

import pytest

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    FileType,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.markdown_lint import run_markdownlint
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_integration,
)
from demisto_sdk.commands.update_release_notes.update_rn import (
    CLASS_BY_FILE_TYPE,
    UpdateRN,
    deprecated_commands,
    get_deprecated_comment_from_desc,
    get_deprecated_rn,
    get_file_description,
)


class TestRNUpdate:
    FILES_PATH = os.path.normpath(
        os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files")
    )
    NOT_DEP_INTEGRATION_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "not_deprecated_integration.yml"
    )
    DEP_INTEGRATION_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "deprecated_integration.yml"
    )
    DEP_DESC_INTEGRATION_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "deprecated_desc_integration.yml"
    )
    NOT_DEP_PLAYBOOK_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "not_deprecated_playbook.yml"
    )
    DEP_PLAYBOOK_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "deprecated_playbook.yml"
    )
    DEP_DESC_PLAYBOOK_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "deprecated_desc_playbook.yml"
    )
    NOT_DEP_SCRIPT_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "not_deprecated_script.yml"
    )
    DEP_SCRIPT_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "deprecated_script.yml"
    )
    DEP_DESC_SCRIPT_PATH = pathlib.Path(
        FILES_PATH, "deprecated_rn_test", "deprecated_desc_script.yml"
    )

    def test_build_rn_template_integration(self, mocker):
        """
        Given:
            - a dict of changed items
        When:
            - we want to produce a release notes template
        Then:
            - return a markdown string
        """
        expected_result = (
            "\n#### Classifiers\n\n##### Hello World Classifier\n\n- %%UPDATE_RN%%\n"
            "\n#### Connections\n\n- **Hello World Connection**\n"
            "\n#### Dashboards\n\n##### Hello World Dashboard\n\n- %%UPDATE_RN%%\n"
            "\n#### Incident Fields\n\n- **Hello World IncidentField**\n"
            "\n#### Incident Types\n\n- **Hello World Incident Type**\n"
            "\n#### Indicator Fields\n\n- **Hello World Indicator Field**\n"
            "\n#### Indicator Types\n\n- **Hello World Indicator Type**\n"
            "\n#### Integrations\n\n##### Hello World Integration\n\n- %%UPDATE_RN%%\n"
            "\n#### Jobs\n\n##### Hello World Job #1\n\n- %%UPDATE_RN%%\n"
            "##### Hello World Job #2\n\n- %%UPDATE_RN%%\n"
            "\n#### Layouts\n\n- **Hello World Layout**\n"
            "- **Second Hello World Layout**\n"
            "\n#### Modules\n\n- **Hello World Generic Module**\n"
            "\n#### Objects\n\n- **Hello World Generic Definition**\n"
            "\n#### Playbooks\n\n##### Hello World Playbook\n\n- %%UPDATE_RN%%\n"
            "\n#### Reports\n\n##### Hello World Report\n\n- %%UPDATE_RN%%\n"
            "\n#### Scripts\n\n##### Hello World Script\n\n- %%UPDATE_RN%%\n"
            "\n#### Widgets\n\n##### Hello World Widget\n\n- %%UPDATE_RN%%\n"
            "\n#### Wizards\n\n##### Hello World Wizard\n\n- %%UPDATE_RN%%\n"
        )
        mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
            return_value="",
        )
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        changed_items = {
            ("Hello World Integration", FileType.INTEGRATION): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Playbook", FileType.PLAYBOOK): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Script", FileType.SCRIPT): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World IncidentField", FileType.INCIDENT_FIELD): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Classifier", FileType.CLASSIFIER): {
                "description": "",
                "is_new_file": False,
            },
            ("N/A", FileType.INTEGRATION): {"description": "", "is_new_file": False},
            ("Hello World Layout", FileType.LAYOUT): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Incident Type", FileType.INCIDENT_TYPE): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Indicator Type", FileType.REPUTATION): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Indicator Field", FileType.INDICATOR_FIELD): {
                "description": "",
                "is_new_file": False,
            },
            ("Second Hello World Layout", FileType.LAYOUT): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Widget", FileType.WIDGET): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Dashboard", FileType.DASHBOARD): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Connection", FileType.CONNECTION): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Report", FileType.REPORT): {
                "description": "",
                "is_new_file": False,
            },
            ("N/A2", None): {"description": "", "is_new_file": True},
            ("Hello World Generic Module", FileType.GENERIC_MODULE): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Generic Definition", FileType.GENERIC_DEFINITION): {
                "description": "",
                "is_new_file": False,
            },
            ("Hello World Job #1", FileType.JOB): {
                "description": "sample job",
                "is_new_file": False,
            },
            ("Hello World Job #2", FileType.JOB): {
                "description": "yet another job",
                "is_new_file": False,
            },
            ("Hello World Wizard", FileType.WIZARD): {
                "description": "sample wizard",
                "is_new_file": False,
            },
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result in release_notes

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_build_rn_template_integration_for_generic(self, mock_master):
        """
        Given:
            - a dict of changed generic items
        When:
            - we want to produce a release notes template
        Then:
            - return a markdown string
        """
        expected_result = (
            "\n#### Object Fields\n\n- **Sample Generic Field**\n"
            "\n#### Object Types\n\n- **Sample Generic Type**\n"
        )

        pack_path = TestRNUpdate.FILES_PATH + "/generic_testing"
        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path=pack_path,
            update_type="minor",
            modified_files_in_pack={"Sample"},
            added_files=set(),
        )
        changed_items = {
            ("Sample Generic Field", FileType.GENERIC_FIELD): {
                "description": "",
                "is_new_file": False,
                "path": pack_path + "/GenericFields/Object" "/genericfield-Sample.json",
            },
            ("Sample Generic Type", FileType.GENERIC_TYPE): {
                "description": "",
                "is_new_file": False,
                "path": pack_path + "/GenericTypes/Object/generictype-Sample.json",
            },
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_build_rn_template_playbook_new_file(self, mock_master):
        """
        Given:
            - a dict of changed items
        When:
            - we want to produce a release notes template for new file
        Then:
            - return a markdown string
        """
        expected_result = (
            "\n#### Playbooks\n\n##### New: Hello World Playbook\n\n"
            "- New: Hello World Playbook description\n"
        )
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        changed_items = {
            ("Hello World Playbook", FileType.PLAYBOOK): {
                "description": "Hello World Playbook description",
                "is_new_file": True,
            },
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_build_rn_template_markdown_valid(self, mock_master, mocker):
        """
        Given:
            - a dict of changed items
        When:
            - we want to produce a release notes template for new file
        Then:
            - return a markdown string
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_pack_metadata", return_value={})

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        changed_items = {
            ("Hello World Integration", FileType.INTEGRATION): {
                "description": "",
                "is_new_file": True,
                "fromversion": "5.0.0",
            },
            ("Hello World Playbook", FileType.PLAYBOOK): {
                "description": "",
                "is_new_file": True,
                "fromversion": "5.5.0",
            },
            ("Hello World Script", FileType.SCRIPT): {
                "description": "",
                "is_new_file": True,
                "fromversion": "6.0.0",
            },
        }
        release_notes = update_rn.build_rn_template(changed_items)

        with ReadMeValidator.start_mdx_server():
            markdownlint = run_markdownlint(release_notes)
            assert not markdownlint.has_errors, (
                release_notes + f"\nValidations: {markdownlint.validations}"
            )

    def test_build_rn_template_playbook_modified_file(self, mocker):
        """
        Given:
            - a dict of changed items
        When:
            - we want to produce a release notes template for modified file
        Then:
            - return a markdown string
        """
        expected_result = (
            "\n#### Playbooks\n\n##### Hello World Playbook\n\n- %%UPDATE_RN%%\n"
        )
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
            return_value="",
        )
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        changed_items = {
            ("Hello World Playbook", FileType.PLAYBOOK): {
                "description": "Hello World Playbook description",
                "is_new_file": False,
            },
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_build_rn_template_file_without_description(self, mock_master):
        """
        Given:
            - a dict of changed items
        When:
            - we want to produce a release notes template for files without descriptions like :
            'Connections', 'Incident Types', 'Indicator Types', 'Layouts', 'Incident Fields'
        Then:
            - return a markdown string
        """
        expected_result = "\n#### Incident Fields\n\n- **Hello World IncidentField**\n"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        changed_items = {
            ("Hello World IncidentField", FileType.INCIDENT_FIELD): {
                "description": "",
                "is_new_file": False,
            },
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_build_rn_template_file__documentation(self, mock_master):
        """
        Given:
            - a dict of changed items, with a documentation rn update
        When:
            - we want to produce a release notes template for files without descriptions like :
            'Connections', 'Incident Types', 'Indicator Types', 'Layouts', 'Incident Fields'
        Then:
            - return a markdown string
        """
        expected_result = (
            "\n#### Integrations\n\n##### Hello World Integration\n\n"
            "- Documentation and metadata improvements.\n"
        )
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="documentation",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        changed_items = {
            ("Hello World Integration", FileType.INTEGRATION): {
                "description": "",
                "is_new_file": False,
            },
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    def test_build_rn_template_when_only_pack_metadata_changed(self, mocker):
        """
        Given:
            - an empty dict of changed items
        When:
            - we want to produce release notes template for a pack where only the pack_metadata file changed
        Then:
            - return a markdown string
        """
        expected_result = "## HelloWorld\n\n- %%UPDATE_RN%%\n"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(
            UpdateRN, "get_pack_metadata", return_value={"name": "HelloWorld"}
        )
        mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files=set(),
            pack_metadata_only=True,
        )
        changed_items = {}
        release_notes = update_rn.build_rn_template(changed_items)
        assert release_notes == expected_result

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_only_docs_changed(self, mock_master):
        """
        Given:
            - case 1: only the readme was added/modified
            - case 2: other files except the readme were added/modified
            - case 3: only docs images were added/modified
            - case 4: readme and py files were added/modified
        When:
            - calling the function that check if only the readme changed
        Then:
            - case 1: validate that the output of the function is True
            - case 2: validate that the output of the function is False
            - case 3: validate that the output of the function is True
            - case 4: validate that the output of the function is False
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"

        # case 1:
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld/README.md"},
            added_files=set(),
        )
        assert update_rn.only_docs_changed()

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files={"HelloWorld/README.md"},
        )
        assert update_rn.only_docs_changed()

        # case 2:
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld/README.md"},
            added_files={"HelloWorld/HelloWorld.py"},
        )
        assert not update_rn.only_docs_changed()

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={
                "HelloWorld/HelloWorld.yml",
                "HelloWorld/README.md",
            },
            added_files=set(),
        )
        assert not update_rn.only_docs_changed()

        # case 3:
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files={"HelloWorld/doc_files/added_params.png"},
        )
        assert update_rn.only_docs_changed()

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld/README.md"},
            added_files={"HelloWorld/doc_files/added_params.png"},
        )
        assert update_rn.only_docs_changed()

        # case 4:
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files={
                "HelloWorld/doc_files/added_params.png",
                "HelloWorld/HelloWorld.yml",
            },
        )
        assert not update_rn.only_docs_changed()

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={
                "HelloWorld/README.md",
                "HelloWorld/HelloWorld.yml",
            },
            added_files=set(),
        )
        assert not update_rn.only_docs_changed()

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_find_corresponding_yml(self, mock_master):
        """
        Given:
            - a filepath containing a python file
        When:
            - determining the changed file
        Then:
            - return only the yml of the changed file
        """
        expected_result = "Integration/HelloWorld.yml"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        filepath = "Integration/HelloWorld.py"
        filename = update_rn.find_corresponding_yml(filepath)
        assert expected_result == filename

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_get_release_notes_path(self, mock_master):
        """
        Given:
            - a pack name and version
        When:
            - building the release notes file within the ReleaseNotes directory
        Then:
            - the filepath of the correct release notes.
        """
        expected_result = "Packs/HelloWorld/ReleaseNotes/1_1_1.md"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        input_version = "1.1.1"
        result = update_rn.get_release_notes_path(input_version)
        assert expected_result == result

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_number_minor(self, mock_master):
        """
        Given:
            - a pack name and version
        When:
            - bumping the version number in the metadata.json
        Then:
            - return the correct bumped version number
        """
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
        )
        expected_version = "1.1.0"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"
        )
        version_number, _ = update_rn.bump_version_number(
            pre_release=False, specific_version=None
        )
        assert version_number == expected_version
        Path(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json").unlink()
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_number_major(self, mock_master):
        """
        Given:
            - a pack name and version
        When:
            - bumping the version number in the metadata.json
        Then:
            - return the correct bumped version number
        """
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
        )
        expected_version = "2.0.0"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="major",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"
        )
        version_number, _ = update_rn.bump_version_number(
            pre_release=False, specific_version=None
        )
        assert version_number == expected_version
        Path(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json").unlink()
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_number_revision(self, mock_master):
        """
        Given:
            - a pack name and version
        When:
            - bumping the version number in the metadata.json
        Then:
            - return the correct bumped version number
        """
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
        )
        expected_version = "1.0.1"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="revision",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"
        )
        version_number, _ = update_rn.bump_version_number(
            pre_release=False, specific_version=None
        )
        assert version_number == expected_version
        Path(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json").unlink()
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_number_specific(self, mock_master):
        """
        Given:
            - a pack name and specific version
        When:
            - bumping the version number in the metadata.json
        Then:
            - return the correct bumped version number
        """
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
        )
        expected_version = "2.0.0"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type=None,
            specific_version="2.0.0",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"
        )
        version_number, _ = update_rn.bump_version_number(
            pre_release=False, specific_version="2.0.0"
        )
        assert version_number == expected_version
        Path(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json").unlink()
        shutil.copy(
            src=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/_pack_metadata.json"),
            dst=os.path.join(TestRNUpdate.FILES_PATH, "fake_pack/pack_metadata.json"),
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_number_revision_overflow(self, mock_master):
        """
        Given:
            - a pack name and a version before an overflow condition
        When:
            - bumping the version number in the metadata.json
        Then:
            - return ValueError
        """
        shutil.copy(
            src=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
            ),
            dst=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/_pack_metadata.json"
            ),
        )
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "0.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="revision",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
        )
        with pytest.raises(ValueError):
            update_rn.bump_version_number()
        Path(TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json").unlink()
        shutil.copy(
            src=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/_pack_metadata.json"
            ),
            dst=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
            ),
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_number_minor_overflow(self, mock_master):
        """
        Given:
            - a pack name and a version before an overflow condition
        When:
            - bumping the version number in the metadata.json
        Then:
            - return ValueError
        """
        shutil.copy(
            src=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
            ),
            dst=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/_pack_metadata.json"
            ),
        )
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "0.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
        )
        with pytest.raises(ValueError):
            update_rn.bump_version_number()
        Path(TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json").unlink()
        shutil.copy(
            src=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/_pack_metadata.json"
            ),
            dst=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
            ),
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_number_major_overflow(self, mock_master):
        """
        Given:
            - a pack name and a version before an overflow condition
        When:
            - bumping the version number in the metadata.json
        Then:
            - return ValueError
        """
        shutil.copy(
            src=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
            ),
            dst=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/_pack_metadata.json"
            ),
        )
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "0.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="major",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
        )
        with pytest.raises(ValueError):
            update_rn.bump_version_number()
        Path(TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json").unlink()
        shutil.copy(
            src=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/_pack_metadata.json"
            ),
            dst=os.path.join(
                TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
            ),
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_file_not_found(self, mock_master):
        """
        Given:
            - a pack name and a metadata which does not exist
        When:
            - bumping the version number in the metadata.json
        Then:
            - return ValueError
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "0.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="major",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata_.json"
        )
        with pytest.raises(Exception) as execinfo:
            update_rn.bump_version_number()
        assert (
            "The metadata file of pack HelloWorld was not found."
            " Please verify the pack name is correct, and that the file exists."
            in execinfo.value.args[0]
        )

    @mock.patch.object(UpdateRN, "get_master_version")
    def test_bump_version_no_version(self, mock_master):
        """
        Given:
            - a pack name and a version before an overflow condition
        When:
            - bumping the version number in the metadata.json
        Then:
            - return ValueError
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = "1.0.0"
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type=None,
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.metadata_path = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
        )
        with pytest.raises(ValueError) as execinfo:
            update_rn.bump_version_number()
        assert (
            "Received no update type when one was expected." in execinfo.value.args[0]
        )

    new_file_test_params = [
        (FileType.TEST_SCRIPT.value, "(Available from Cortex XSOAR 5.5.0).", ["xsoar"]),
        (
            FileType.MODELING_RULE.value,
            "(Available from Cortex XSIAM %%XSIAM_VERSION%%).",
            ["marketplacev2"],
        ),
    ]

    @pytest.mark.parametrize(
        "file_type, expected_result, marketplaces", new_file_test_params
    )
    def test_build_rn_desc_new_file(
        self, mocker, file_type, expected_result, marketplaces
    ):
        """
        Given
            - A new file
        When
            - Running the command build_rn_desc on a file in order to generate rn description.
        Then
            - Validate That from-version added to the rn description.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(
            UpdateRN, "get_pack_metadata", return_value={"marketplaces": marketplaces}
        )

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )

        desc = update_rn.build_rn_desc(
            _type=file_type,
            content_name="Hello World Test",
            desc="Test description",
            is_new_file=True,
            text="",
            from_version="5.5.0",
            docker_image=None,
        )
        assert expected_result in desc

    @pytest.mark.parametrize(
        "file_type, marketplaces, expected_result, not_expected",
        [
            (
                # Case 1: xsoar file type and xsoar marketplace, should only have xsoar.
                FileType.TEST_SCRIPT.value,
                ["xsoar"],
                "<~XSOAR> (Available from Cortex XSOAR 5.5.0).</~XSOAR>",
                "<~XSIAM> (Available from Cortex XSIAM %%XSIAM_VERSION%%).</~XSIAM>",
            ),
            (
                # Case 2: xsoar file type and xsiam marketplace, should only have xsiam.
                FileType.TEST_SCRIPT.value,
                ["marketplacev2"],
                "<~XSIAM> (Available from Cortex XSIAM %%XSIAM_VERSION%%).</~XSIAM>",
                "<~XSOAR> (Available from Cortex XSOAR 5.5.0).</~XSOAR>",
            ),
            (
                # Case 3: xsoar file type and xsoar & xsiam marketplaces, should have both.
                FileType.TEST_SCRIPT.value,
                ["xsoar", "marketplacev2"],
                "<~XSIAM> (Available from Cortex XSIAM %%XSIAM_VERSION%%).</~XSIAM>\n"
                "<~XSOAR> (Available from Cortex XSOAR 5.5.0).</~XSOAR>",
                "",
            ),
            (
                # Case 4: xsiam file type and xsiam marketplace, should only have xsiam.
                FileType.MODELING_RULE.value,
                ["marketplacev2"],
                "<~XSIAM> (Available from Cortex XSIAM %%XSIAM_VERSION%%).</~XSIAM>",
                "<~XSOAR> (Available from Cortex XSOAR 5.5.0).</~XSOAR>",
            ),
            (
                # Case 5: xsiam file type and xsoar & xsiam marketplaces, should only have xsiam.
                FileType.MODELING_RULE.value,
                ["xsoar", "marketplacev2"],
                "<~XSIAM> (Available from Cortex XSIAM %%XSIAM_VERSION%%).</~XSIAM>",
                "<~XSOAR> (Available from Cortex XSOAR 5.5.0).</~XSOAR>",
            ),
        ],
    )
    def test_build_rn_desc_new_file_several_marketplaces(
        self, pack, file_type, marketplaces, expected_result, not_expected
    ):
        """
        Given: New pack supported in different marketplaces with new file of type file_type.

        When: Running build_rn_desc when updating release notes.

        Then: Check the marketplace specific from version string is as expected.

        Cases:
            Case 1: xsoar file type and xsoar marketplace, should only have xsoar.
            Case 2: xsoar file type and xsiam marketplace, should only have xsiam.
            Case 3: xsoar file type and xsoar & xsiam marketplaces, should have both.
            Case 4: xsiam file type and xsiam marketplace, should only have xsiam.
            Case 5: xsiam file type and xsoar & xsiam marketplaces, should only have xsiam.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        pack.pack_metadata.write_json(
            {
                "name": "HelloWorld",
                "description": "This pack.",
                "support": "xsoar",
                "currentVersion": "1.0.1",
                "author": "Cortex XSOAR",
                "url": "https://www.paloaltonetworks.com/cortex",
                "email": "",
                "created": "2021-06-07T07:45:21Z",
                "categories": [],
                "tags": [],
                "useCases": [],
                "keywords": [],
                "marketplaces": marketplaces,
            }
        )

        update_rn = UpdateRN(
            pack_path=pack.path,
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )

        desc = update_rn.build_rn_desc(
            _type=file_type,
            content_name="Hello World Test",
            desc="Test description",
            is_new_file=True,
            text="",
            from_version="5.5.0",
            docker_image=None,
        )
        assert expected_result in desc
        if not_expected:
            assert not_expected not in desc

    def test_build_rn_desc_old_file(self):
        """
        Given
            - An old file
        When
            - Running the command build_rn_desc on a file in order to generate rn description.
        Then
            - Validate That from-version was not added to the rn description.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )

        desc = update_rn.build_rn_desc(
            _type=FileType.TEST_SCRIPT,
            content_name="Hello World Test",
            desc="Test description",
            is_new_file=False,
            text="",
            from_version="5.5.0",
            docker_image=None,
        )
        assert "(Available from Cortex XSOAR 5.5.0)." not in desc

    def test_build_rn_template_with_fromversion(self, mocker):
        """
        Given
            - New playbook integration and script.
        When
            - running the command build_rn_template on this files in order to generate rn description.
        Then
            - Validate That from-version added to each of rn descriptions.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_pack_metadata", return_value={})

        changed_items = {
            ("Hello World Integration", FileType.INTEGRATION): {
                "description": "",
                "is_new_file": True,
                "fromversion": "5.0.0",
            },
            ("Hello World Playbook", FileType.PLAYBOOK): {
                "description": "",
                "is_new_file": True,
                "fromversion": "5.5.0",
            },
            ("Hello World Script", FileType.SCRIPT): {
                "description": "",
                "is_new_file": True,
                "fromversion": "6.0.0",
            },
        }
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )

        desc = update_rn.build_rn_template(changed_items=changed_items)
        assert "(Available from Cortex XSOAR 5.0.0)." in desc
        assert "(Available from Cortex XSOAR 5.5.0)." in desc
        assert "(Available from Cortex XSOAR 6.0.0)." in desc

    def test_build_rn_desc_event_collector(self):
        """
        Given
            - A new event collector file.
        When
            - Running the command build_rn_desc on a file in order to generate rn description.
        Then
            - Validate that XSIAM from-version added to the rn description.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorldEventCollector",
            update_type="minor",
            modified_files_in_pack={"HelloWorldEventCollector"},
            added_files=set(),
        )

        desc = update_rn.build_rn_desc(
            content_name="Hello World Event Collector",
            is_new_file=True,
            desc="Test description",
            text="",
            docker_image=None,
        )
        assert "(Available from Cortex XSIAM %%XSIAM_VERSION%%)." in desc

    @mock.patch.object(UpdateRN, "bump_version_number")
    @mock.patch.object(UpdateRN, "is_bump_required")
    def test_execute_with_bump_version_raises_error(
        self, mock_bump_version_number, mock_is_bump_required
    ):
        """
        Given
            - Pack path for update release notes
        When
            - bump_version_number function raises valueError
        Then
           - could not bump version number and system exit occurs
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_bump_version_number.side_effect = ValueError("Test")
        mock_is_bump_required.return_value = True
        with pytest.raises(ValueError) as e:
            client = UpdateRN(
                pack_path="Packs/Test",
                update_type="minor",
                modified_files_in_pack={"Packs/Test/Integrations/Test.yml"},
                added_files=set("Packs/Test/some_added_file.py"),
            )
            client.execute_update()
        assert e.value.args[0] == "Test"

    @mock.patch.object(UpdateRN, "only_docs_changed")
    def test_only_docs_changed_bump_not_required(self, mock_master):
        """
        Given
            - Pack to update release notes
        When
            - Only doc files have changed
        Then
           - bump version number is not required
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mock_master.return_value = True
        client = UpdateRN(
            pack_path="Packs/Test",
            update_type="minor",
            modified_files_in_pack={"Packs/Test/Integrations/Test.yml"},
            added_files=set("Packs/Test/some_added_file.py"),
        )
        assert client.is_bump_required() is False

    def test_filter_to_relevant_files_pack_not_found(self):
        """
        Given:
        - Pack input.
        - File difference of a file outside of Packs structure.

        When:
        - Executing filter relevant files from given pack.

        Then:
        - Ensure file is filtered.
        """
        from demisto_sdk.commands.update_release_notes.update_rn_manager import (
            UpdateReleaseNotesManager,
        )
        from demisto_sdk.commands.validate.old_validate_manager import (
            OldValidateManager,
        )

        manager = UpdateReleaseNotesManager(user_input="BitcoinAbuse")
        validate_manager: OldValidateManager = OldValidateManager(
            check_is_unskipped=False
        )
        filtered_set, old_format_files, _ = manager.filter_to_relevant_files(
            {".gitlab/ci/.gitlab-ci.yml"}, validate_manager
        )
        assert filtered_set == set()
        assert old_format_files == set()

    @staticmethod
    def test_update_rn_new_dashboard(repo):
        """
        Case - new dashboard, XSOAR, fromversion exists, description exists
        Expected - release note should contain New, description and version
        """
        pack = repo.create_pack("test_pack")
        new_dashboard = pack.create_dashboard(
            name="dashboard",
            content={"description": "description for testing", "fromversion": "6.0.0"},
        )
        update_rn = UpdateRN(
            pack_path=pack.path,
            update_type="minor",
            added_files=new_dashboard.path,
            modified_files_in_pack=set(),
        )

        rn_desc = update_rn.build_rn_desc(
            _type=FileType.DASHBOARD,
            content_name=pack.name,
            is_new_file=True,
            desc=new_dashboard.read_json_as_dict().get("description"),
            from_version=new_dashboard.read_json_as_dict().get("fromversion"),
        )

        assert (
            "##### New:" in rn_desc
        )  # check if release note contains New - when new file
        assert (
            "description for testing" in rn_desc
        )  # check if release note contains description when description not empty
        assert (
            "(Available from Cortex XSOAR 6.0.0)." in rn_desc
        )  # check if release note contains fromversion when exists

    @staticmethod
    def test_update_rn_new_mapper(repo):
        """
        Case - new mapper, XSOAR, fromversion exists, description exists
        Expected - release note should contain New but should not contain description and version
        """
        pack = repo.create_pack("test_pack")
        new_mapper = pack.create_mapper(name="mapper", content={"description": ""})
        update_rn = UpdateRN(
            pack_path=pack.path,
            update_type="minor",
            added_files=new_mapper.path,
            modified_files_in_pack=set(),
        )

        rn_desc = update_rn.build_rn_desc(
            _type=FileType.MAPPER,
            content_name=pack.name,
            is_new_file=True,
            desc=new_mapper.read_json_as_dict().get("description"),
            from_version=new_mapper.read_json_as_dict().get("fromversion"),
        )

        assert (
            "##### New:" in rn_desc
        )  # check if release note contains New - when new file
        assert (
            "description for testing" not in rn_desc
        )  # check if release note does not contain description when description is empty
        assert (
            "(Available from Cortex XSOAR 6.0.0)." not in rn_desc
        )  # check if release note does not contain fromversion when None

    @staticmethod
    def test_update_rn_new_incident_field(repo):
        """
        Case - new incident field, XSOAR, fromversion exists, description exists
        Expected - release note should not contain new and version
        """
        pack = repo.create_pack("test_pack")
        new_incident_field = pack.create_incident_field(
            name="incident field", content={"fromversion": "6.5.0"}
        )
        update_rn = UpdateRN(
            pack_path=pack.path,
            update_type="minor",
            added_files=new_incident_field.path,
            modified_files_in_pack=set(),
        )

        rn_desc = update_rn.build_rn_desc(
            _type=FileType.INCIDENT_FIELD,
            content_name=pack.name,
            is_new_file=True,
            desc=new_incident_field.read_json_as_dict().get("description"),
            from_version=new_incident_field.read_json_as_dict().get("fromversion"),
        )

        assert f"- New: **{new_incident_field}**" not in rn_desc
        assert "test_pack" in rn_desc
        assert "(Available from Cortex XSOAR 6.5.0)." not in rn_desc

    def test_update_rn_with_deprecated_and_text(self, mocker):
        """
        Given:
            - Path to a Integration
        When:
            - Calling build_rn_desc function
        Then:
            Ensure the function returns a valid rn when the command is deprecated compared to last yml and the
             text is added
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        FILES_PATH = os.path.normpath(
            os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files")
        )
        NOT_DEP_INTEGRATION_PATH = pathlib.Path(
            FILES_PATH, "deprecated_rn_test", "not_deprecated_integration.yml"
        )

        update_rn = UpdateRN(
            pack_path="Packs/Test",
            update_type="minor",
            modified_files_in_pack={"Integration"},
            added_files=set(),
        )
        old_yml_obj, new_yml_obj = get_mock_yml_obj(
            NOT_DEP_INTEGRATION_PATH, FileType.INTEGRATION, False
        )
        new_yml_obj.script["commands"][0]["deprecated"] = True

        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_yml_objects",
            return_value=(old_yml_obj, new_yml_obj),
        )

        desc = update_rn.build_rn_desc(
            _type=FileType.INTEGRATION,
            content_name="Integration test",
            desc="Test description",
            text="text for test",
            from_version="5.5.0",
            docker_image=None,
            path=NOT_DEP_INTEGRATION_PATH,
        )

        assert (
            desc
            == "##### Integration test\n\n- text for test\n- Command ***xdr-get-incidents*** is deprecated. Use "
            "%%% instead.\n"
        )

    def test_deprecated_rn_integration_command(self, mocker):
        """
        Given:
            - Path to a Integration
        When:
            - Calling get_deprecated_rn function
        Then:
            Ensure the function returns a valid rn when the command is deprecated compared to last yml
        """
        FILES_PATH = os.path.normpath(
            os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files")
        )
        NOT_DEP_INTEGRATION_PATH = pathlib.Path(
            FILES_PATH, "deprecated_rn_test", "not_deprecated_integration.yml"
        )

        old_yml_obj, new_yml_obj = get_mock_yml_obj(
            NOT_DEP_INTEGRATION_PATH, FileType.INTEGRATION, False
        )
        new_yml_obj.script["commands"][0]["deprecated"] = True

        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_yml_objects",
            return_value=(old_yml_obj, new_yml_obj),
        )
        # When command is newly deprecated
        res = get_deprecated_rn(NOT_DEP_INTEGRATION_PATH, FileType.INTEGRATION)
        assert (
            res == "- Command ***xdr-get-incidents*** is deprecated. Use %%% instead.\n"
        )

        # When the command is already deprecated
        old_yml_obj["script"]["commands"][0]["deprecated"] = True
        res = get_deprecated_rn(NOT_DEP_INTEGRATION_PATH, FileType.INTEGRATION)
        assert res == ""

    @pytest.mark.parametrize(
        "path, file_type, deprecated, expected_res",
        [
            (NOT_DEP_INTEGRATION_PATH, FileType.INTEGRATION, True, ""),
            (NOT_DEP_INTEGRATION_PATH, FileType.INTEGRATION, False, ""),
            (
                DEP_INTEGRATION_PATH,
                FileType.INTEGRATION,
                False,
                "- Deprecated. Use %%% instead.\n",
            ),
            (
                DEP_DESC_INTEGRATION_PATH,
                FileType.INTEGRATION,
                False,
                "- Deprecated. Use Other Integration instead.\n",
            ),
            (DEP_INTEGRATION_PATH, FileType.INTEGRATION, True, ""),
            (NOT_DEP_PLAYBOOK_PATH, FileType.PLAYBOOK, True, ""),
            (NOT_DEP_PLAYBOOK_PATH, FileType.PLAYBOOK, False, ""),
            (
                DEP_PLAYBOOK_PATH,
                FileType.PLAYBOOK,
                False,
                "- Deprecated. Use %%% instead.\n",
            ),
            (
                DEP_DESC_PLAYBOOK_PATH,
                FileType.PLAYBOOK,
                False,
                "- Deprecated. Use another playbook instead.\n",
            ),
            (DEP_PLAYBOOK_PATH, FileType.PLAYBOOK, True, ""),
            (NOT_DEP_SCRIPT_PATH, FileType.SCRIPT, True, ""),
            (NOT_DEP_SCRIPT_PATH, FileType.SCRIPT, False, ""),
            (
                DEP_SCRIPT_PATH,
                FileType.SCRIPT,
                False,
                "- Deprecated. Use %%% instead.\n",
            ),
            (
                DEP_DESC_SCRIPT_PATH,
                FileType.SCRIPT,
                False,
                "- Deprecated. No available replacement.\n",
            ),
            (DEP_SCRIPT_PATH, FileType.SCRIPT, True, ""),
        ],
    )
    def test_deprecated_rn_yml(self, mocker, path, file_type, deprecated, expected_res):
        """
        Given:
            - Path to a yml Object, and if the last yml was deprecated
            (1) - (4)- Integration
            (5) - (8) - Playbook
            (9) - (12)- Script
        When:
            - Calling get_deprecated_rn function
        Then:
            Ensure the function returns a valid rn when the yml is deprecated.
        """
        old_yml_obj, new_yml_obj = get_mock_yml_obj(path, file_type, deprecated)
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_yml_objects",
            return_value=(old_yml_obj, new_yml_obj),
        )
        res = get_deprecated_rn(path, file_type)
        assert res == expected_res

    def test_deprecated_rn_yml_no_commands_section(self, mocker, pack):
        """
        Given:
            - deprecated integration which does not have "commands" section
        When:
            - Calling get_deprecated_rn function
        Then:
            - Ensure the function returns a valid rn when the yml is deprecated without the "commands" section

        """
        integration = pack.create_integration(
            name="test",
            yml={
                "commonfields": {"id": "test", "version": -1},
                "name": "test",
                "display": "test",
                "description": "this is an integration test",
                "category": "category",
                "script": {
                    "type": "python",
                    "subtype": "python3",
                    "script": "",
                    "dockerimage": "",
                },
                "configuration": [],
            },
        )

        assert get_deprecated_rn(integration.path, FileType.INTEGRATION) == ""


def get_mock_yml_obj(path, file_type, deprecated) -> dict:
    new_yml_obj = CLASS_BY_FILE_TYPE[file_type](path)
    if file_type == FileType.INTEGRATION:
        old_yml_dict = {
            "script": {"commands": deepcopy(new_yml_obj.script.get("commands"))},
            "deprecated": deprecated,
        }
    else:
        old_yml_dict = {"deprecated": deprecated}

    return old_yml_dict, new_yml_obj


class TestRNUpdateUnit:
    META_BACKUP = ""
    FILES_PATH = os.path.normpath(
        os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files")
    )
    CURRENT_RN = """
#### Incident Types

- **Cortex XDR Incident**

#### Incident Fields

- **XDR Alerts**

#### Object Types

- **Sample GenericType**

#### Object Fields

- **Sample GenericField**
"""
    CHANGED_FILES = {
        ("Cortex XDR Incident", FileType.INCIDENT_TYPE): {
            "description": "",
            "is_new_file": False,
        },
        ("XDR Alerts", FileType.INCIDENT_FIELD): {
            "description": "",
            "is_new_file": False,
        },
        ("Sample IncidentField", FileType.INCIDENT_FIELD): {
            "description": "",
            "is_new_file": False,
        },
        ("Cortex XDR - IR", FileType.INTEGRATION): {
            "description": "",
            "is_new_file": False,
        },
        ("Nothing", None): {"description": "", "is_new_file": False},
        ("Sample", FileType.INTEGRATION): {"description": "", "is_new_file": False},
        ("Sample GenericField", FileType.GENERIC_FIELD): {
            "description": "",
            "is_new_file": False,
            "path": "Packs" "/HelloWorld/GenericField/asset/Sample_GenericType",
        },
        ("Sample GenericType", FileType.GENERIC_TYPE): {
            "description": "",
            "is_new_file": False,
            "path": "Packs" "/HelloWorld/GenericType/asset/Sample_GenericType",
        },
    }
    EXPECTED_RN_RES = """
#### Incident Types

- **Cortex XDR Incident**

#### Incident Fields

- **Sample IncidentField**

- **XDR Alerts**

#### Object Types

- **Sample GenericType**

#### Object Fields

- **Sample GenericField**

#### Integrations

##### Cortex XDR - IR

- %%UPDATE_RN%%

##### Sample

- %%UPDATE_RN%%

"""

    diff_package = [
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Layouts/VulnDB/VulnDB.json",
            FileType.LAYOUT,
            ("VulnDB", FileType.LAYOUT),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Classifiers/VulnDB/VulnDB.json",
            FileType.CLASSIFIER,
            ("VulnDB", FileType.CLASSIFIER),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/IncidentTypes/VulnDB/VulnDB.json",
            FileType.INCIDENT_TYPE,
            ("VulnDB", FileType.INCIDENT_TYPE),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/IncidentFields/VulnDB/VulnDB.json",
            FileType.INCIDENT_FIELD,
            ("VulnDB", FileType.INCIDENT_FIELD),
        ),
        (
            "Packs/CommonTypes",
            "Packs/CommonTypes/IndicatorFields/VulnDB.json",
            FileType.INDICATOR_FIELD,
            ("VulnDB", FileType.INDICATOR_FIELD),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Playbooks/VulnDB/VulnDB_playbook.yml",
            FileType.PLAYBOOK,
            ("VulnDB", FileType.PLAYBOOK),
        ),
        (
            "Packs/CommonScripts",
            "Packs/CommonScripts/Playbooks/VulnDB/VulnDB_playbook.yml",
            FileType.PLAYBOOK,
            ("VulnDB", FileType.PLAYBOOK),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Scripts/VulnDB/VulnDB.py",
            FileType.SCRIPT,
            ("VulnDB", FileType.SCRIPT),
        ),
        (
            "Packs/CommonPlaybooks",
            "Packs/CommonPlaybooks/Scripts/VulnDB/VulnDB.py",
            FileType.SCRIPT,
            ("VulnDB", FileType.SCRIPT),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/ReleaseNotes/1_0_1.md",
            FileType.RELEASE_NOTES,
            ("VulnDB", FileType.RELEASE_NOTES),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Integrations/VulnDB/VulnDB.yml",
            FileType.INTEGRATION,
            ("VulnDB", FileType.INTEGRATION),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Connections/VulnDB/VulnDB.yml",
            FileType.CONNECTION,
            ("VulnDB", FileType.CONNECTION),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Dashboards/VulnDB/VulnDB.yml",
            FileType.DASHBOARD,
            ("VulnDB", FileType.DASHBOARD),
        ),
        (
            "Packs/CommonScripts",
            "Packs/CommonScripts/Dashboards/VulnDB/VulnDB.yml",
            FileType.DASHBOARD,
            ("VulnDB", FileType.DASHBOARD),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Widgets/VulnDB/VulnDB.yml",
            FileType.WIDGET,
            ("VulnDB", FileType.WIDGET),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/Reports/VulnDB/VulnDB.yml",
            FileType.REPORT,
            ("VulnDB", FileType.REPORT),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/IndicatorTypes/VulnDB/VulnDB.yml",
            FileType.REPUTATION,
            ("VulnDB", FileType.REPUTATION),
        ),
        (
            "Packs/VulnDB",
            "Packs/VulnDB/TestPlaybooks/VulnDB/VulnDB.yml",
            FileType.TEST_PLAYBOOK,
            ("VulnDB", FileType.TEST_PLAYBOOK),
        ),
        (
            "Packs/CommonScripts",
            "Packs/CommonScripts/TestPlaybooks/VulnDB/VulnDB.yml",
            FileType.TEST_PLAYBOOK,
            ("VulnDB", FileType.TEST_PLAYBOOK),
        ),
    ]

    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        """Tests below modify the file: 'demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json'
        We back it up and restore when done.

        """
        self.meta_backup = str(tmp_path / "pack_metadata-backup.json")
        shutil.copy(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json",
            self.meta_backup,
        )

    def teardown_method(self):
        if self.meta_backup:
            shutil.copy(
                self.meta_backup,
                "demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json",
            )
        else:
            raise Exception(
                "Expecting self.meta_backup to be set inorder to restore pack_metadata.json file"
            )

    @pytest.mark.parametrize(
        "pack_name, path, find_type_result, expected_result", diff_package
    )
    def test_get_changed_file_name_and_type(
        self, pack_name, path, find_type_result, expected_result, mocker
    ):
        """
        Given:
            - a filepath of a changed file
        When:
            - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
        Then:
            - return tuple where first value is the pack name, and second is the item type
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        update_rn = UpdateRN(
            pack_path=pack_name,
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        filepath = os.path.join(TestRNUpdate.FILES_PATH, path)
        mocker.patch.object(
            UpdateRN,
            "find_corresponding_yml",
            return_value="Integrations/VulnDB/VulnDB.yml",
        )
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_display_name",
            return_value="VulnDB",
        )
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.find_type",
            return_value=find_type_result,
        )
        result = update_rn.get_changed_file_name_and_type(filepath)
        assert expected_result == result

    def test_check_rn_directory(self, mocker):
        """
        Given:
            - a filepath for a release notes directory
        When:
            - determining if the directory exists
        Then:
            - create the directory if it does not exist
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        filepath = os.path.join(TestRNUpdate.FILES_PATH, "ReleaseNotes")
        update_rn = UpdateRN(
            pack_path="Packs/VulnDB",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        update_rn.check_rn_dir(filepath)

    def test_create_markdown(self, mocker):
        """
        Given:
            - a filepath for a release notes file and a markdown string
        When:
            - creating a new markdown file
        Then:
            - create the file or skip if it exists.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        update_rn = UpdateRN(
            pack_path="Packs/VulnDB",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        filepath = os.path.join(TestRNUpdate.FILES_PATH, "ReleaseNotes/1_1_67.md")
        md_string = "### Shelly"
        update_rn.create_markdown(
            release_notes_path=filepath, rn_string=md_string, changed_files={}
        )

    def test_update_existing_rn(self, mocker):
        """
        Given:
            - Existing release notes and set of changed files
        When:
            - rerunning the update command
        Then:
            - return updated release notes while preserving the integrity of the existing notes.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
            return_value="",
        )

        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        new_rn = update_rn.update_existing_rn(self.CURRENT_RN, self.CHANGED_FILES)
        assert self.EXPECTED_RN_RES == new_rn

    def test_write_metadata_To_file(self, mocker):
        """
        Given:
            - No inputs, but a condition where bumping the version is ready
        When:
            - running update
        Then:
            - update the metadata json by the version designated.
        """
        ORIGINAL = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack_invalid/pack_metadata.json"
        )
        TEMP_FILE = os.path.join(
            TestRNUpdate.FILES_PATH, "fake_pack_invalid/_pack_metadata.json"
        )
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack={"HelloWorld"},
            added_files=set(),
        )
        shutil.copy(src=ORIGINAL, dst=TEMP_FILE)
        data_dict = get_json(TEMP_FILE)
        update_rn.metadata_path = TEMP_FILE
        update_rn.write_metadata_to_file(data_dict)
        Path(ORIGINAL).unlink()
        shutil.copy(src=TEMP_FILE, dst=ORIGINAL)

    def test_find_added_pack_files(self, mocker):
        """
        Given:
            - List of added files
        When:
            - searching for relevant pack files
        Then:
            - return a list of relevant pack files which were added.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        added_files = {"HelloWorld/something_new.md", "HelloWorld/test_data/nothing.md"}
        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files=added_files,
        )
        update_rn.find_added_pack_files()
        assert update_rn.modified_files_in_pack == {"HelloWorld/something_new.md"}

    def test_does_pack_metadata_exist_no(self, mocker):
        """
        Given:
            - Checking for the existance of a pack metadata file
        When:
            - metadata path is invalid
        Then:
            - return False to indicate it does not exist.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        update_rn = UpdateRN(
            pack_path="Packs/HelloWorld",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files=set(),
        )
        update_rn.metadata_path = "This/Doesnt/Exist"
        result = update_rn._does_pack_metadata_exist()
        assert result is False

    def test_execute_update_invalid(self, mocker):
        """
        Given:
            - A protected pack name
        When:
            - running the update command
        Then:
            - return an error message and exit.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        update_rn = UpdateRN(
            pack_path="Packs/Legacy",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files=set(),
        )
        update_rn.execute_update()

    diff_package = [
        ("1.0.1", "1.0.2", True),
        ("1.0.5", "1.0.4", False),
        ("1.0.5", "1.0.5", True),
        ("1.0.0", DEFAULT_CONTENT_ITEM_TO_VERSION, True),
    ]

    @pytest.mark.parametrize(
        "pack_current_version, git_current_version, expected_result", diff_package
    )
    def test_is_bump_required(
        self, pack_current_version, git_current_version, expected_result, mocker
    ):
        """
        Given:
            - Case 1: Version in origin/master is higher than the current version for the pack
            - Case 2: Version of origin/master is lower than current version (indicating bump has
                      happened already.
            - Case 3: Version is the same indicating a bump is necessary.
            - Case 4: Version was not found so default of 99.99.99 is used.
        When:
            - Case 1: Bumping release notes with update-release-notes command.
            - Case 2: Bumping release notes with update-release-notes command.
            - Case 3: Bumping release notes with update-release-notes command.
            - Case 4: Bumping release notes with update-release-notes command.
        Then:
            - Case 1: Return True and throw error saying "The master branch is currently ahead of
                      your pack's version. Please pull from master and re-run the command."
            - Case 2: Return False since bump has already happened.
            - Case 3: Return True since a bump is necessary.
            - Case 4: Return True and throw error saying "The master branch is currently ahead of
                      your pack's version. Please pull from master and re-run the command."
        """
        from subprocess import Popen

        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(
            UpdateRN, "get_master_version", return_value=git_current_version
        )
        update_rn = UpdateRN(
            pack_path="Packs/Base",
            update_type="minor",
            modified_files_in_pack=set(),
            added_files=set(),
        )
        mocker.patch.object(
            UpdateRN,
            "get_pack_metadata",
            return_value={"currentVersion": pack_current_version},
        )
        # mocking the only_docs_changed to test only the is_bump_required
        mocker.patch.object(UpdateRN, "only_docs_changed", return_value=False)
        mocker.patch.object(
            Popen,
            "communicate",
            return_value=(json.dumps({"currentVersion": git_current_version}), ""),
        )
        mocker.patch("sys.exit", return_value=None)
        bump_result = update_rn.is_bump_required()
        assert bump_result is expected_result

    def test_renamed_files(self, mocker):
        """
        Given:
            A file was renamed
        When:
            Bumping release notes with update-release-notes command.
        Then:
            file list should contain the new file path and ignore the old path.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        modified_files = {"file1", ("file2", "file2_new"), "file3"}
        update_rn = UpdateRN(
            pack_path="Packs/Base",
            update_type="minor",
            modified_files_in_pack=modified_files,
            added_files=set(),
        )

        assert "file1" in update_rn.modified_files_in_pack
        assert "file2_new" in update_rn.modified_files_in_pack
        assert ("file2", "file2_new") not in update_rn.modified_files_in_pack
        assert "file3" in update_rn.modified_files_in_pack

    def test_change_image_or_desc_file_path(self):
        """
        Given:
            case 1: a description file
            case 2: an image file
            case 3: a non-image or description file
        When:
            running change_image_or_desc_file_path method
        Then:
            case 1 & 2: change the file path to the corresponding yml file.
            case 3: file path remains unchnaged
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        integration_image_file_path = (
            "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2_image.png"
        )
        xsiam_image_file_path = (
            "Packs/Dropbox/XSIAMDashboards/DropboxDashboard_image.png"
        )
        description_file_path = (
            "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2_description.md"
        )
        yml_file_path = "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2.yml"
        json_file_path = "Packs/Dropbox/XSIAMDashboards/DropboxDashboard.json"

        assert yml_file_path == UpdateRN.change_image_or_desc_file_path(
            integration_image_file_path
        )
        assert yml_file_path == UpdateRN.change_image_or_desc_file_path(
            description_file_path
        )
        assert json_file_path == UpdateRN.change_image_or_desc_file_path(
            xsiam_image_file_path
        )
        assert yml_file_path == UpdateRN.change_image_or_desc_file_path(yml_file_path)

    def test_update_api_modules_dependents_rn__happy_flow(self, mocker):
        """
        Given
        - ApiModules_script.yml which is part of APIModules pack was changed.

        When
        - update_api_modules_rn is called

        Then
        - Ensure execute_update_mock is called
        """
        from demisto_sdk.commands.update_release_notes.update_rn import (
            UpdateRN,
            update_api_modules_dependents_rn,
        )

        modified = {"/Packs/ApiModules/Scripts/ApiModules_script/ApiModules_script.yml"}
        added = {}

        integration_mock = mock_integration("SmapleIntegration")
        mocker.patch.object(ContentGraphInterface, "__init__", return_value=None)
        mocker.patch.object(ContentGraphInterface, "__exit__", return_value=None)
        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")

        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.update_content_graph",
            return_value=None,
        )
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_api_module_dependencies_from_graph",
            return_value=[integration_mock],  # Mock the integration path
        )

        execute_update_mock = mocker.patch.object(UpdateRN, "execute_update")

        update_api_modules_dependents_rn(
            pre_release=None,
            update_type=None,
            added=added,
            modified=modified,
        )
        assert execute_update_mock.call_count == 1

    def test_update_docker_image_when_yml_has_changed_but_not_docker_image_property(
        self, mocker
    ):
        """
        Given
            - Modified .yml file
        When
            - Working on an integration's yml, but haven't update docker image

        Then
            - No changes should be done in release notes
        """
        from demisto_sdk.commands.update_release_notes.update_rn import (
            check_docker_image_changed,
        )

        return_value = "+category: Utilities\
                        +commonfields:\
                        +  id: Test\
                        +  version: -1\
                        +configuration:\
                        +- defaultvalue: https://soar.test.com\
                        +  display: Server URL (e.g. https://soar.test.com)\
                        +- display: Fetch incidents\
                        +  name: isFetch\
                        +- display: Incident type"

        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.run_command",
            return_value=return_value,
        )

        assert (
            check_docker_image_changed(main_branch="origin/master", packfile="test.yml")
            is None
        )

    @pytest.mark.parametrize(
        "return_value_mock",
        [
            ("+  dockerimage: demisto/python3:3.9.8.24399"),
            ("+dockerimage: demisto/python3:3.9.8.24399"),
        ],
    )
    def test_check_docker_image_changed(self, mocker, return_value_mock):
        """
        This test checks that for both integration and script YMLs, where the docker image resides at a different level,
        changes made to this key are found correctly by 'check_docker_image_changed' function.
        Given
            - Case 1: a git diff mock of a modified integration .yml file where the docker is changed and there're spaces between the
            '+' and the dockerimage
            - Case 2: a git diff mock of a modified sccript .yml file where the docker is changed and there's no space between the
            '+' and the dockerimage
        When
            - calling the check_docker_image_changed function
        Then
            Ensure that the dockerimage was extracted correctly for each case where each case demonstrate either integration
            yml or Script yml.
            - Case 1: Should extract the dockerimage version for integration yml demonstration.
            - Case 2: Should extract the dockerimage version for script yml demonstration.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import (
            check_docker_image_changed,
        )

        return_value = "+  dockerimage: demisto/python3:3.9.8.24399"

        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.run_command",
            return_value=return_value,
        )
        assert (
            check_docker_image_changed(main_branch="origin/master", packfile="test.yml")
            == "demisto/python3:3.9.8.24399"
        )

    def test_update_docker_image_in_yml(self, mocker):
        """
        Given
            - Modified .yml file
        When
            - Updating docker image tag

        Then
            - A new release notes is created. and it has a new record for updating docker image.
        """

        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        expected_res = (
            "diff --git a/Packs/test1/Integrations/test1/test1.yml b/Packs/test1/Integrations/test1/test1.yml\n"
            "--- a/Packs/test1/Integrations/test1/test1.yml\n"
            "+++ b/Packs/test1/Integrations/test1/test1.yml\n"
            "@@ -1270,7 +1270,7 @@ script:\n"
            "description: update docker image.\n"
            "execution: false\n"
            "name: test1\n"
            "-  dockerimage: demisto/python3:3.9.6.22912\n"
            "+  dockerimage: demisto/python3:3.9.6.22914\n"
            "feed: false\n"
            "isfetch: false\n"
            "longRunning: false\n"
        )

        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json"
        ) as file:
            pack_data = json.load(file)
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.run_command",
            return_value=expected_res,
        )
        mocker.patch.object(UpdateRN, "is_bump_required", return_value=False)
        mocker.patch.object(UpdateRN, "get_pack_metadata", return_value=pack_data)
        mocker.patch.object(
            UpdateRN,
            "get_changed_file_name_and_type",
            return_value=("Test", FileType.INTEGRATION),
        )
        mocker.patch.object(
            UpdateRN,
            "get_release_notes_path",
            return_value="demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes"
            "/1_1_0.md",
        )
        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
            return_value="",
        )

        client = UpdateRN(
            pack_path="demisto_sdk/commands/update_release_notes/tests_data/Packs/Test",
            update_type="minor",
            modified_files_in_pack={"Packs/Test/Integrations/Test.yml"},
            added_files=set(),
        )
        client.execute_update()
        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md"
        ) as file:
            RN = file.read()
        Path(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md"
        ).unlink()
        assert "Updated the Docker image to: *demisto/python3:3.9.6.22914*." in RN

    def test_update_docker_image_in_yml_when_RN_aleady_exists(self, mocker):
        """
        Given
            - Modified .yml file, but relevant release notes is already exist.
        When
            - Updating docker image tag.

        Then
            - A new record with the updated docker image is added.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json"
        ) as file:
            pack_data = json.load(file)
        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_0_0.md",
            "w",
        ) as file:
            file.write("### Integrations\n")
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.run_command",
            return_value="+  dockerimage:python/test:1243",
        )
        mocker.patch.object(UpdateRN, "is_bump_required", return_value=False)
        mocker.patch.object(UpdateRN, "get_pack_metadata", return_value=pack_data)
        mocker.patch(
            "demisto_sdk.commands.common.tools.get_display_name", return_value="Test"
        )
        mocker.patch.object(UpdateRN, "build_rn_template", return_value="##### Test\n")
        mocker.patch.object(
            UpdateRN,
            "get_release_notes_path",
            return_value="demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes"
            "/1_0_0.md",
        )
        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        mocker.patch.object(
            UpdateRN,
            "get_changed_file_name_and_type",
            return_value=("Test", FileType.INTEGRATION),
        )
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
            return_value="",
        )

        client = UpdateRN(
            pack_path="Packs/Test",
            update_type=None,
            modified_files_in_pack={"Packs/Test/Integrations/Test.yml"},
            added_files=set(),
        )
        client.execute_update()
        client.execute_update()
        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_0_0.md"
        ) as file:
            RN = file.read()
        assert (
            RN.count("Updated the Docker image to: *dockerimage:python/test:1243*.")
            == 1
        )

        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_0_0.md",
            "w",
        ) as file:
            file.write("")

    def test_add_and_modify_files_without_update_docker_image(self, mocker):
        """
        Given
            - Modified .yml file, but relevant release notes is already exist.
        When
            - Updating docker image tag.

        Then
            - A new record with the updated docker image is added.
        """

        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json"
        ) as file:
            pack_data = json.load(file)
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.run_command",
            return_value="+  type:True",
        )
        mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
        mocker.patch.object(UpdateRN, "get_pack_metadata", return_value=pack_data)
        mocker.patch(
            "demisto_sdk.commands.common.tools.get_display_name", return_value="Test"
        )
        mocker.patch.object(UpdateRN, "build_rn_template", return_value="##### Test\n")
        mocker.patch.object(
            UpdateRN,
            "get_release_notes_path",
            return_value="demisto_sdk/commands"
            "/update_release_notes/tests_data"
            "/Packs/release_notes/1_1_0.md",
        )
        mocker.patch.object(
            UpdateRN,
            "get_changed_file_name_and_type",
            return_value=("Test", FileType.INTEGRATION),
        )
        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
        client = UpdateRN(
            pack_path="demisto_sdk/commands/update_release_notes/tests_data/Packs/Test",
            update_type="minor",
            modified_files_in_pack={"Packs/Test/Integrations/Test.yml"},
            added_files=set("Packs/Test/some_added_file.py"),
        )
        client.execute_update()
        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md"
        ) as file:
            RN = file.read()
        Path(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md"
        ).unlink()
        assert "Updated the Docker image to: *dockerimage:python/test:1243*" not in RN

    def test_new_integration_docker_not_updated(self, mocker):
        """
        Given
            - New integration created.
        When
            - Running update-release-notes command

        Then
            - Docker is not indicated as updated.
        """

        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json"
        ) as file:
            pack_data = json.load(file)
        mocker.patch(
            "demisto_sdk.commands.update_release_notes.update_rn.run_command",
            return_value="+  dockerimage:python/test:1243",
        )
        mocker.patch.object(UpdateRN, "is_bump_required", return_value=False)
        mocker.patch.object(UpdateRN, "get_pack_metadata", return_value=pack_data)
        mocker.patch.object(UpdateRN, "build_rn_template", return_value="##### Test")
        mocker.patch.object(
            UpdateRN,
            "get_changed_file_name_and_type",
            return_value=("Test", FileType.INTEGRATION),
        )
        mocker.patch.object(
            UpdateRN,
            "get_release_notes_path",
            return_value="demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes"
            "/1_1_0.md",
        )
        mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")

        client = UpdateRN(
            pack_path="demisto_sdk/commands/update_release_notes/tests_data/Packs/Test",
            update_type="minor",
            modified_files_in_pack={"Packs/Test/Integrations/Test.yml"},
            added_files={"Packs/Test/Integrations/Test.yml"},
        )
        client.execute_update()
        with open(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md"
        ) as file:
            RN = file.read()
        Path(
            "demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md"
        ).unlink()
        assert "Updated the Docker image to: *dockerimage:python/test:1243*" not in RN

    docker_image_test_rn = (
        "#### Integrations\n\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n- Updated the Docker image "
        "to: *demisto/python3:3.9.1.149615*.\n"
    )
    docker_image_test_data = [
        (
            "#### Integrations\n\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n",
            None,
            "#### Integrations\n\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n",
            False,
        ),
        (
            "#### Integrations\n\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n",
            "demisto/python3:3.9.1.149615",
            docker_image_test_rn,
            True,
        ),
        (
            docker_image_test_rn,
            "demisto/python3:3.9.1.149615",
            docker_image_test_rn,
            False,
        ),
        (
            docker_image_test_rn,
            "demisto/python3:3.9.1.149616",
            "#### Integrations\n\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n- Updated the Docker image "
            "to: *demisto/python3:3.9.1.149616*.\n",
            True,
        ),
    ]

    BUILD_RN_CONFIG_FILE_INPUTS = [
        (False, None, None),
        (True, None, {"breakingChanges": True, "breakingChangesNotes": None}),
        (
            True,
            {"breakingChanges": True},
            {"breakingChanges": True, "breakingChangesNotes": None},
        ),
        (
            True,
            {"breakingChanges": True, "breakingChangesNotes": "bc notes"},
            {"breakingChanges": True, "breakingChangesNotes": "bc notes"},
        ),
    ]

    @pytest.mark.parametrize(
        "is_bc, existing_conf_data, expected_conf_data", BUILD_RN_CONFIG_FILE_INPUTS
    )
    def test_build_rn_config_file(
        self,
        pack,
        is_bc: bool,
        existing_conf_data: Optional[Dict],
        expected_conf_data: Optional[Dict],
    ):
        """
        Given:
        - BC flag - indicating whether new version introduced has breaking changes.

        When:
        - Generating conf file for new RN.
        Case a: BC flag was not specified.
        Case b: BC flag was specified, no conf exists.
        Case c: BC flag was specified, conf exists, breakingChanges field is false.
        Case c: BC flag was specified, conf exists, breakingChangesNotes field is not empty.

        Then:
        - Ensure expected results happen.
        Case a: No conf JSON file generated.
        Case b: Conf JSON file generated with null value for breakingChangesNotes, and true value for breakingChanges.
        Case c: Conf JSON file generated with null value for breakingChangesNotes, and true value for breakingChanges.
        Case d: Conf JSON file generated with old value for breakingChangesNotes, and true value for breakingChanges.

        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        client = UpdateRN(
            pack_path=pack.path,
            update_type=None,
            modified_files_in_pack=set(),
            added_files=set(),
            is_bc=is_bc,
        )
        conf_path: str = f"{pack.path}/ReleaseNotes/1_0_1.json"
        if existing_conf_data:
            with open(conf_path, "w") as f:
                f.write(json.dumps(existing_conf_data))
        client.build_rn_config_file("1.0.1")
        if expected_conf_data:
            assert Path(conf_path).exists()
            with open(conf_path) as f:
                assert json.loads(f.read()) == expected_conf_data
        else:
            assert not Path(conf_path).exists()


def test_get_from_version_at_update_rn(integration):
    """
    Given
        - Case 1: An integration path
        - Case 2: A fake integration path
    When
        - Updating release notes for integration, trying to extract the 'fromversion' key from the integration yml.
    Then
        - Case 1: Assert that the `fromversion` value is 5.0.0
        - Case 2: Assert that the `fromversion` value is None
    """
    from demisto_sdk.commands.update_release_notes.update_rn import (
        get_from_version_at_update_rn,
    )

    integration.yml.write_dict({"fromversion": "5.0.0"})
    fromversion = get_from_version_at_update_rn(integration.yml.path)
    assert fromversion == "5.0.0"
    fromversion = get_from_version_at_update_rn("fake_path.yml")
    assert fromversion is None


def test_docker_image_is_added_for_every_integration(mocker, repo):
    """
    Given:
    - Pack to update with release notes.

    When:
    - First call to update release notes: Two YMLs had their docker image updated.
    - Second call to update release notes: Two YMLs were updated again.

    Then:
    - Ensure two entries for update docker image are added to release notes, one for each YML.
    - Ensure two entries for update docker images are added to release notes, one for each YML, with the
      newer docker image.

    """
    yml_mock = {
        "display": "test",
        "script": {"type": "python", "dockerimage": "demisto/python3:3.9.5.123"},
    }
    pack = repo.create_pack("PackName")
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.check_docker_image_changed",
        return_value="demisto/python3:3.9.5.124",
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
        return_value="",
    )
    integration = pack.create_integration("integration", "bla", yml_mock)
    integration.create_default_integration()
    integration.yml.update({"display": "Sample1"})
    integration2 = pack.create_integration("integration2", "bla2", yml_mock)
    integration2.create_default_integration()
    integration2.yml.update({"display": "Sample2"})
    pack.pack_metadata.write_json({"currentVersion": "0.0.0"})
    client = UpdateRN(
        pack_path=str(pack.path),
        update_type="revision",
        modified_files_in_pack={
            f"{str(integration.path)}/integration.yml",
            f"{str(integration2.path)}/integration2.yml",
        },
        added_files=set(),
    )
    client.execute_update()
    with open(str(f"{pack.path}/ReleaseNotes/0_0_1.md")) as f:
        rn_text = f.read()
    assert (
        rn_text.count("Updated the Docker image to: *demisto/python3:3.9.5.124*.") == 2
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.check_docker_image_changed",
        return_value="demisto/python3:3.9.5.125",
    )
    client = UpdateRN(
        pack_path=str(pack.path),
        update_type=None,
        modified_files_in_pack={
            f"{str(integration.path)}/integration.yml",
            f"{str(integration2.path)}/integration2.yml",
        },
        added_files=set(),
    )
    client.execute_update()
    with open(str(f"{pack.path}/ReleaseNotes/0_0_1.md")) as f:
        rn_text = f.read()
    assert (
        rn_text.count("Updated the Docker image to: *demisto/python3:3.9.5.124*.") == 0
    )
    assert (
        rn_text.count("Updated the Docker image to: *demisto/python3:3.9.5.125*.") == 2
    )


HANDLE_EXISTING_RN_WITH_DOCKER_IMAGE_INPUTS = [
    (
        "#### Integrations\n\n##### IBM QRadar v2\n- %%UPDATE_RN%%\n\n##### IBM QRadar v3\n- %%UPDATE_RN%%",
        "Integrations",
        "demisto/python3:3.9.5.21276",
        "IBM QRadar v3",
        "#### Integrations\n\n##### IBM QRadar v2\n- %%UPDATE_RN%%\n\n##### IBM QRadar v3\n- Updated the Docker image to: "
        "*demisto/python3:3.9.5.21276*.\n- %%UPDATE_RN%%",
    ),
    (
        "#### Integrations\n\n##### IBM QRadar v3\n- %%UPDATE_RN%%",
        "Integrations",
        "demisto/python3:3.9.5.21276",
        "IBM QRadar v3",
        "#### Integrations\n\n##### IBM QRadar v3\n- Updated the Docker image to: "
        "*demisto/python3:3.9.5.21276*.\n- %%UPDATE_RN%%",
    ),
]


@pytest.mark.parametrize(
    "new_rn, header_by_type, docker_image, content_name, expected",
    HANDLE_EXISTING_RN_WITH_DOCKER_IMAGE_INPUTS,
)
def test_handle_existing_rn_with_docker_image(
    new_rn: str,
    header_by_type: str,
    docker_image: str,
    content_name: str,
    expected: str,
):
    """
    Given:
    - 'new_rn': new RN.
    - 'header_by_type': Header of the RN to add docker image to, e.g 'Integrations', 'Scripts'
    - 'docker_image': Docker image to add
    - 'content_name': The content name to add the docker image entry to, e.g integration name, script name.

    When:
    - Adding docker image entry to the relevant RN.
    Case a: Two integrations, adding docker image only to QRadar v3.
    Case b: One integration.

    Then:
    - Ensure expected entry of docker image is added in the expected spot.
    Case a: Added only to QRadar v3 but not to QRadar v2.
    Case b: Added to the integration as expected.

    """
    assert (
        UpdateRN.handle_existing_rn_with_docker_image(
            new_rn, header_by_type, docker_image, content_name
        )
        == expected
    )


@pytest.mark.parametrize(
    "text, expected_rn_string",
    [
        ("Testing the upload", "## PackName\n\n- Testing the upload\n"),
        ("", "## PackName\n\n- %%UPDATE_RN%%\n"),
    ],
)
def test_force_and_text_update_rn(repo, text, expected_rn_string):
    """
    Given:
    - New release note

    When:
    - Updating release notes with *--force* and *--text* flags
    - Updating release notes with *--force* and without the *--text* flag

    Then:
    - Ensure the release note includes the "Testing the upload" text
    - Ensure the release note includes the "%%UPDATE_RN%%" text
    """
    pack = repo.create_pack("PackName")
    client = UpdateRN(
        pack_path=str(pack.path),
        update_type=None,
        modified_files_in_pack=set(),
        added_files=set(),
        is_force=True,
        text=text,
    )

    rn_string = client.build_rn_template({})
    assert rn_string == expected_rn_string


CREATE_MD_IF_CURRENTVERSION_IS_HIGHER_TEST_BANK_ = [(["0_0_1"], ["0_0_1", "0_0_3"])]


@pytest.mark.parametrize(
    "first_expected_results, second_expected_results",
    CREATE_MD_IF_CURRENTVERSION_IS_HIGHER_TEST_BANK_,
)
def test_create_md_if_currentversion_is_higher(
    mocker, first_expected_results, second_expected_results, repo
):
    """
    Given:
        - Case 1: the expected RN files.
    When:
        - creating a new markdown file.
    Then:
        Ensure that the creation was done correctly although the currentversion wasn't matching the latest RN.
        - Case 1: Should create a new RN according to currentversion.
    """
    yml_mock = {
        "display": "test",
        "script": {"type": "python", "dockerimage": "demisto/python3:3.9.5.123"},
    }
    pack = repo.create_pack("PackName")
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.check_docker_image_changed",
        return_value="demisto/python3:3.9.5.124",
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
        return_value="",
    )
    integration = pack.create_integration("integration", "bla", yml_mock)
    integration.create_default_integration()
    integration.yml.update({"display": "Sample1"})
    pack.pack_metadata.write_json({"currentVersion": "0.0.1"})
    client = UpdateRN(
        pack_path=str(pack.path),
        update_type="revision",
        modified_files_in_pack={f"{str(integration.path)}/integration.yml"},
        added_files=set(),
    )
    client.execute_update()
    updated_rn_folder = glob.glob(pack.path + "/ReleaseNotes/*")
    updated_versions_list = [rn[rn.rindex("/") + 1 : -3] for rn in updated_rn_folder]
    assert Counter(first_expected_results) == Counter(updated_versions_list)
    pack.pack_metadata.write_json({"currentVersion": "0.0.3"})
    client.execute_update()
    updated_rn_folder = glob.glob(pack.path + "/ReleaseNotes/*")
    updated_versions_list = [rn[rn.rindex("/") + 1 : -3] for rn in updated_rn_folder]
    assert Counter(second_expected_results) == Counter(updated_versions_list)


def test_deprecated_commands():
    """
    Given:
        - List of commands
    When:
        - Calling deprecated_commands function
    Then:
        Ensure the function return a set of the deprecated commands only.
    """
    commands = [
        {"name": "command_1", "deprecated": True},
        {"name": "command_2", "deprecated": False},
    ]
    res = deprecated_commands(commands)
    assert res == {"command_1"}


def test_get_deprecated_comment_from_desc():
    """
    Given:
        - Description of  yml as string
    When:
        - Calling get_deprecated_comment_from_desc function
    Then:
        Ensure the function returns a deprecated comment from the string, if found.
    """
    original_desc = (
        "Cortex XDR is the world's first detection and response app that natively\n integrates network, "
        "endpoint and cloud data to stop sophisticated attacks. "
    )
    deprecate_with_replacement = (
        "Deprecated. Use Cortex XDR v2 instead." + original_desc
    )
    deprecate_without_replacement = (
        "Deprecated. No available replacement." + original_desc
    )

    assert get_deprecated_comment_from_desc(original_desc) == ""
    assert (
        get_deprecated_comment_from_desc(deprecate_with_replacement)
        == "Use Cortex XDR v2 instead"
    )
    assert (
        get_deprecated_comment_from_desc(deprecate_without_replacement)
        == "No available replacement"
    )


def test_handle_existing_rn_version_path(mocker, repo):
    """
    Given:
        - Release notes update when there is an existing file.
    When:
        - Calling handle_existing_rn_version_path function
    Then:
        Ensure the function does not sets should delete existing rn property to True when paths are identical.
    """
    pack = repo.create_pack("test")
    mocker.patch.object(UpdateRN, "CONTENT_PATH", return_value=repo.path)
    pack.create_release_notes(version="1_0_1")
    client = UpdateRN(
        pack_path=str(pack.path),
        update_type="revision",
        modified_files_in_pack=set(),
        added_files=set(),
    )
    client.existing_rn_version_path = "ReleaseNotes/1_0_1.md"
    client.handle_existing_rn_version_path(f"{str(pack.path)}/ReleaseNotes/1_0_1.md")
    assert not client.should_delete_existing_rn


@pytest.mark.parametrize(
    "path, file_type, expected_results",
    [
        (
            "demisto_sdk/commands/update_release_notes/tests_data/modeling_rules_yml_mock.yml",
            FileType.MODELING_RULE,
            "testing modeling rules description extraction.",
        )
    ],
)
def test_get_file_description(path, file_type, expected_results):
    """
    Given:
        - File type and file path.
    When:
        - Calling get_file_description function.
    Then:
        Ensure the function extracted the information from the right field.
    """
    assert get_file_description(path, file_type) == expected_results


def test_no_release_notes_for_first_version(mocker):
    """
    Given:
        - Changes made in the content repo.
    When:
        - runing update release notes for the first version of the pack (1.0.0).
    Then
        - validate the a proper error message is raised.
    """
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=False)
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    update_rn = UpdateRN(
        pack_path="Packs/HelloWorld",
        update_type="minor",
        modified_files_in_pack=set(),
        added_files=set(),
        pack_metadata_only=True,
    )

    with pytest.raises(ValueError) as e:
        update_rn.get_new_version_and_metadata()
        assert str(e) == "Release notes do not need to be updated for version '1.0.0'."


def test_git_add_release_notes(mocker):
    """
    Given:
        - a filepath for a release notes file and a markdown string
    When:
        - creating a new markdown file and adding it
    Then:
        - create the file and then remove it.
    """
    from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    update_rn = UpdateRN(
        pack_path="Packs/VulnDB",
        update_type="minor",
        modified_files_in_pack={"HelloWorld"},
        added_files=set(),
    )
    filepath = os.path.join(TestRNUpdate.FILES_PATH, "ReleaseNotes/1_1_2.md")
    md_string = "### Test Release Notes"
    update_rn.create_markdown(
        release_notes_path=filepath, rn_string=md_string, changed_files={}
    )
    assert Path(filepath).exists()
    Path(filepath).unlink()
    assert not Path(filepath).exists()
