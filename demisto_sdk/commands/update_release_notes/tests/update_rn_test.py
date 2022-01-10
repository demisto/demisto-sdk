import json
import os
import shutil
import unittest
from typing import Dict, Optional

import mock
import pytest

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_TO_VERSION, FileType)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.common.update_id_set import DEFAULT_ID_SET_PATH
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN


class TestRNUpdate(unittest.TestCase):
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_build_rn_template_integration(self, mock_master):
        """
            Given:
                - a dict of changed items
            When:
                - we want to produce a release notes template
            Then:
                - return a markdown string
        """
        expected_result = \
            "\n#### Classifiers\n##### Hello World Classifier\n- %%UPDATE_RN%%\n" \
            "\n#### Connections\n- **Hello World Connection**\n" \
            "\n#### Dashboards\n##### Hello World Dashboard\n- %%UPDATE_RN%%\n" \
            "\n#### Incident Fields\n- **Hello World IncidentField**\n" \
            "\n#### Incident Types\n- **Hello World Incident Type**\n" \
            "\n#### Indicator Fields\n- **Hello World Indicator Field**\n" \
            "\n#### Indicator Types\n- **Hello World Indicator Type**\n" \
            "\n#### Integrations\n##### Hello World Integration\n- %%UPDATE_RN%%\n" \
            "\n#### Jobs\n##### Hello World Job #1\n- %%UPDATE_RN%%" \
            "\n##### Hello World Job #2\n- %%UPDATE_RN%%\n" \
            "\n#### Layouts\n- **Hello World Layout**\n" \
            "- **Second Hello World Layout**\n" \
            "\n#### Modules\n##### Hello World Generic Module\n- %%UPDATE_RN%%\n" \
            "\n#### Objects\n##### Hello World Generic Definition\n- %%UPDATE_RN%%\n" \
            "\n#### Playbooks\n##### Hello World Playbook\n- %%UPDATE_RN%%\n" \
            "\n#### Reports\n##### Hello World Report\n- %%UPDATE_RN%%\n" \
            "\n#### Scripts\n##### Hello World Script\n- %%UPDATE_RN%%\n" \
            "\n#### Widgets\n##### Hello World Widget\n- %%UPDATE_RN%%\n"

        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            ("Hello World Integration", FileType.INTEGRATION): {"description": "", "is_new_file": False},
            ("Hello World Playbook", FileType.PLAYBOOK): {"description": "", "is_new_file": False},
            ("Hello World Script", FileType.SCRIPT): {"description": "", "is_new_file": False},
            ("Hello World IncidentField", FileType.INCIDENT_FIELD): {"description": "", "is_new_file": False},
            ("Hello World Classifier", FileType.CLASSIFIER): {"description": "", "is_new_file": False},
            ("N/A", FileType.INTEGRATION): {"description": "", "is_new_file": False},
            ("Hello World Layout", FileType.LAYOUT): {"description": "", "is_new_file": False},
            ("Hello World Incident Type", FileType.INCIDENT_TYPE): {"description": "", "is_new_file": False},
            ("Hello World Indicator Type", FileType.REPUTATION): {"description": "", "is_new_file": False},
            ("Hello World Indicator Field", FileType.INDICATOR_FIELD): {"description": "", "is_new_file": False},
            ("Second Hello World Layout", FileType.LAYOUT): {"description": "", "is_new_file": False},
            ("Hello World Widget", FileType.WIDGET): {"description": "", "is_new_file": False},
            ("Hello World Dashboard", FileType.DASHBOARD): {"description": "", "is_new_file": False},
            ("Hello World Connection", FileType.CONNECTION): {"description": "", "is_new_file": False},
            ("Hello World Report", FileType.REPORT): {"description": "", "is_new_file": False},
            ("N/A2", None): {"description": "", "is_new_file": True},
            ("Hello World Generic Module", FileType.GENERIC_MODULE): {"description": "", "is_new_file": False},
            ("Hello World Generic Definition", FileType.GENERIC_DEFINITION): {"description": "", "is_new_file": False},
            ("Hello World Job #1", FileType.JOB): {"description": "sample job", "is_new_file": False},
            ("Hello World Job #2", FileType.JOB): {"description": "yet another job", "is_new_file": False}
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_build_rn_template_integration_for_generic(self, mock_master):
        """
            Given:
                - a dict of changed generic items
            When:
                - we want to produce a release notes template
            Then:
                - return a markdown string
        """
        expected_result = \
            "\n#### Object Fields\n- **(Object) - Sample Generic Field**\n" \
            "\n#### Object Types\n- **(Object) - Sample Generic Type**\n"

        pack_path = TestRNUpdate.FILES_PATH + "/generic_testing"
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path=pack_path, update_type='minor', modified_files_in_pack={'Sample'},
                             added_files=set())
        changed_items = {
            ("Sample Generic Field", FileType.GENERIC_FIELD): {"description": "", "is_new_file": False,
                                                               "path": pack_path + "/GenericFields/Object"
                                                                                   "/genericfield-Sample.json"},
            ("Sample Generic Type", FileType.GENERIC_TYPE): {"description": "", "is_new_file": False,
                                                             "path": pack_path + "/GenericTypes/Object/generictype-Sample.json"}
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_build_rn_template_playbook_new_file(self, mock_master):
        """
            Given:
                - a dict of changed items
            When:
                - we want to produce a release notes template for new file
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Playbooks\n##### New: Hello World Playbook\n- Hello World Playbook description\n"
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            ("Hello World Playbook", FileType.PLAYBOOK): {
                "description": "Hello World Playbook description", "is_new_file": True},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_build_rn_template_playbook_modified_file(self, mock_master):
        """
            Given:
                - a dict of changed items
            When:
                - we want to produce a release notes template for modified file
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Playbooks\n##### Hello World Playbook\n- %%UPDATE_RN%%\n"
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            ("Hello World Playbook", FileType.PLAYBOOK): {"description": "Hello World Playbook description",
                                                          "is_new_file": False},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
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
        expected_result = "\n#### Incident Fields\n- **Hello World IncidentField**\n"
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            ("Hello World IncidentField", FileType.INCIDENT_FIELD): {"description": "", "is_new_file": False},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_build_rn_template_file__maintenance(self, mock_master):
        """
            Given:
                - a dict of changed items, with a maintenance rn update
            When:
                - we want to produce a release notes template for files without descriptions like :
                'Connections', 'Incident Types', 'Indicator Types', 'Layouts', 'Incident Fields'
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Integrations\n##### Hello World Integration\n" \
                          "- Maintenance and stability enhancements.\n"
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='maintenance',
                             modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            ("Hello World Integration", FileType.INTEGRATION): {"description": "", "is_new_file": False},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_build_rn_template_file__documentation(self, mock_master):
        """
            Given:
                - a dict of changed items, with a maintenance rn update
            When:
                - we want to produce a release notes template for files without descriptions like :
                'Connections', 'Incident Types', 'Indicator Types', 'Layouts', 'Incident Fields'
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Integrations\n##### Hello World Integration\n" \
                          "- Documentation and metadata improvements.\n"
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='documentation',
                             modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            ("Hello World Integration", FileType.INTEGRATION): {"description": "", "is_new_file": False},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_build_rn_template_when_only_pack_metadata_changed(self, mock_master):
        """
        Given:
            - an empty dict of changed items
        When:
            - we want to produce release notes template for a pack where only the pack_metadata file changed
        Then:
            - return a markdown string
        """
        expected_result = "\n#### Integrations\n##### HelloWorld\n- Documentation and metadata improvements.\n"
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack=set(),
                             added_files=set(),
                             pack_metadata_only=True)
        changed_items = {}
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    @mock.patch.object(UpdateRN, 'get_master_version')
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'

        # case 1:
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor',
                             modified_files_in_pack={'HelloWorld/README.md'},
                             added_files=set())
        assert update_rn.only_docs_changed()

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack=set(),
                             added_files={'HelloWorld/README.md'})
        assert update_rn.only_docs_changed()

        # case 2:
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor',
                             modified_files_in_pack={'HelloWorld/README.md'},
                             added_files={'HelloWorld/HelloWorld.py'})
        assert not update_rn.only_docs_changed()

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor',
                             modified_files_in_pack={'HelloWorld/HelloWorld.yml', 'HelloWorld/README.md'},
                             added_files=set())
        assert not update_rn.only_docs_changed()

        # case 3:
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack=set(),
                             added_files={'HelloWorld/doc_files/added_params.png'})
        assert update_rn.only_docs_changed()

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor',
                             modified_files_in_pack={'HelloWorld/README.md'},
                             added_files={'HelloWorld/doc_files/added_params.png'})
        assert update_rn.only_docs_changed()

        # case 4:
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack=set(),
                             added_files={'HelloWorld/doc_files/added_params.png', 'HelloWorld/HelloWorld.yml'})
        assert not update_rn.only_docs_changed()

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor',
                             modified_files_in_pack={'HelloWorld/README.md', 'HelloWorld/HelloWorld.yml'},
                             added_files=set())
        assert not update_rn.only_docs_changed()

    @mock.patch.object(UpdateRN, 'get_master_version')
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        filepath = 'Integration/HelloWorld.py'
        filename = update_rn.find_corresponding_yml(filepath)
        assert expected_result == filename

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_get_release_notes_path(self, mock_master):
        """
            Given:
                - a pack name and version
            When:
                - building the release notes file within the ReleaseNotes directory
            Then:
                - the filepath of the correct release notes.
        """
        expected_result = 'Packs/HelloWorld/ReleaseNotes/1_1_1.md'
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        input_version = '1.1.1'
        result = update_rn.get_release_notes_path(input_version)
        assert expected_result == result

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_number_minor(self, mock_master):
        """
            Given:
                - a pack name and version
            When:
                - bumping the version number in the metadata.json
            Then:
                - return the correct bumped version number
        """
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'))
        expected_version = '1.1.0'
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False, specific_version=None)
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_number_major(self, mock_master):
        """
            Given:
                - a pack name and version
            When:
                - bumping the version number in the metadata.json
            Then:
                - return the correct bumped version number
        """
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'))
        expected_version = '2.0.0'
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='major', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False, specific_version=None)
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_number_revision(self, mock_master):
        """
            Given:
                - a pack name and version
            When:
                - bumping the version number in the metadata.json
            Then:
                - return the correct bumped version number
        """
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'))
        expected_version = '1.0.1'
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='revision',
                             modified_files_in_pack={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False, specific_version=None)
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_number_specific(self, mock_master):
        """
            Given:
                - a pack name and specific version
            When:
                - bumping the version number in the metadata.json
            Then:
                - return the correct bumped version number
        """
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'))
        expected_version = '2.0.0'
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type=None, specific_version='2.0.0',
                             modified_files_in_pack={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH,
                                               'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False,
                                                          specific_version='2.0.0')
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_number_revision_overflow(self, mock_master):
        """
            Given:
                - a pack name and a version before an overflow condition
            When:
                - bumping the version number in the metadata.json
            Then:
                - return ValueError
        """
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'))
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '0.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='revision',
                             modified_files_in_pack={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_number_minor_overflow(self, mock_master):
        """
            Given:
                - a pack name and a version before an overflow condition
            When:
                - bumping the version number in the metadata.json
            Then:
                - return ValueError
        """
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'))
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '0.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_number_major_overflow(self, mock_master):
        """
            Given:
                - a pack name and a version before an overflow condition
            When:
                - bumping the version number in the metadata.json
            Then:
                - return ValueError
        """
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'))
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '0.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='major', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_file_not_found(self, mock_master):
        """
            Given:
                - a pack name and a metadata which does not exist
            When:
                - bumping the version number in the metadata.json
            Then:
                - return ValueError
        """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '0.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='major', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata_.json')
        with pytest.raises(Exception) as execinfo:
            update_rn.bump_version_number()
        assert 'Pack HelloWorld was not found. Please verify the pack name is correct.' in execinfo.value.args[0]

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_bump_version_no_version(self, mock_master):
        """
            Given:
                - a pack name and a version before an overflow condition
            When:
                - bumping the version number in the metadata.json
            Then:
                - return ValueError
        """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type=None, modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        with pytest.raises(ValueError) as execinfo:
            update_rn.bump_version_number()
        assert 'Received no update type when one was expected.' in execinfo.value.args[0]

    def test_build_rn_desc_new_file(self):
        """
            Given
                - A new file
            When
                - Running the command build_rn_desc on a file in order to generate rn description.
            Then
                - Validate That from-version added to the rn description.
            """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())

        desc = update_rn.build_rn_desc(_type=FileType.TEST_SCRIPT, content_name='Hello World Test',
                                       desc='Test description', is_new_file=True, text='', from_version='5.5.0',
                                       docker_image=None)
        assert '(Available from Cortex XSOAR 5.5.0).' in desc

    def test_build_rn_desc_old_file(self):
        """
            Given
                - An old file
            When
                - Running the command build_rn_desc on a file in order to generate rn description.
            Then
                - Validate That from-version was not added to the rn description.
            """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())

        desc = update_rn.build_rn_desc(_type=FileType.TEST_SCRIPT, content_name='Hello World Test',
                                       desc='Test description', is_new_file=False, text='', from_version='5.5.0',
                                       docker_image=None)
        assert '(Available from Cortex XSOAR 5.5.0).' not in desc

    def test_build_rn_template_with_fromversion(self):
        """
            Given
                - New playbook integration and script.
            When
                - running the command build_rn_template on this files in order to generate rn description.
            Then
                - Validate That from-version added to each of rn descriptions.
            """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN

        changed_items = {
            ('Hello World Integration', FileType.INTEGRATION): {'description': "", 'is_new_file': True,
                                                                'fromversion': '5.0.0'},
            ('Hello World Playbook', FileType.PLAYBOOK): {'description': '', 'is_new_file': True,
                                                          'fromversion': '5.5.0'},
            ("Hello World Script", FileType.SCRIPT): {'description': '', 'is_new_file': True, 'fromversion': '6.0.0'},
        }
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())

        desc = update_rn.build_rn_template(changed_items=changed_items)
        assert '(Available from Cortex XSOAR 5.0.0).' in desc
        assert '(Available from Cortex XSOAR 5.5.0).' in desc
        assert '(Available from Cortex XSOAR 6.0.0).' in desc

    @mock.patch.object(UpdateRN, 'bump_version_number')
    @mock.patch.object(UpdateRN, 'is_bump_required')
    def test_execute_with_bump_version_raises_error(self, mock_bump_version_number, mock_is_bump_required):
        """
            Given
                - Pack path for update release notes
            When
                - bump_version_number function raises valueError
            Then
               - could not bump version number and system exit occurs
            """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_bump_version_number.side_effect = ValueError('Test')
        mock_is_bump_required.return_value = True
        with pytest.raises(ValueError) as e:
            client = UpdateRN(pack_path="Packs/Test", update_type='minor', modified_files_in_pack={
                'Packs/Test/Integrations/Test.yml'}, added_files=set('Packs/Test/some_added_file.py'))
            client.execute_update()
        assert e.value.args[0] == 'Test'

    @mock.patch.object(UpdateRN, 'only_docs_changed')
    def test_only_docs_changed_bump_not_required(self, mock_master):
        """
            Given
                - Pack to update release notes
            When
                - Only doc files have changed
            Then
               - bump version number is not required
            """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mock_master.return_value = True
        client = UpdateRN(pack_path="Packs/Test", update_type='minor', modified_files_in_pack={
            'Packs/Test/Integrations/Test.yml'}, added_files=set('Packs/Test/some_added_file.py'))
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
        from demisto_sdk.commands.update_release_notes.update_rn_manager import \
            UpdateReleaseNotesManager
        from demisto_sdk.commands.validate.validate_manager import \
            ValidateManager
        manager = UpdateReleaseNotesManager(user_input='BitcoinAbuse')
        validate_manager: ValidateManager = ValidateManager(check_is_unskipped=False)
        filtered_set, old_format_files = manager.filter_to_relevant_files(
            {'.gitlab/ci/.gitlab-ci.yml'}, validate_manager)
        assert filtered_set == set()
        assert old_format_files == set()


class TestRNUpdateUnit:
    META_BACKUP = ""
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    CURRENT_RN = """
#### Incident Types
- **Cortex XDR Incident**

#### Incident Fields
- **XDR Alerts**

#### Object Types
- **(Asset) - Sample GenericType**

#### Object Fields
- **(Asset) - Sample GenericField**
"""
    CHANGED_FILES = {
        ("Cortex XDR Incident", FileType.INCIDENT_TYPE): {"description": "", "is_new_file": False},
        ("XDR Alerts", FileType.INCIDENT_FIELD): {"description": "", "is_new_file": False},
        ("Sample IncidentField", FileType.INCIDENT_FIELD): {"description": "", "is_new_file": False},
        ("Cortex XDR - IR", FileType.INTEGRATION): {"description": "", "is_new_file": False},
        ("Nothing", None): {"description": "", "is_new_file": False},
        ("Sample", FileType.INTEGRATION): {"description": "", "is_new_file": False},
        ("Sample GenericField", FileType.GENERIC_FIELD): {"description": "", "is_new_file": False, "path": "Packs"
                                                          "/HelloWorld/GenericField/asset/Sample_GenericType"},
        ("Sample GenericType", FileType.GENERIC_TYPE): {"description": "", "is_new_file": False, "path": "Packs"
                                                        "/HelloWorld/GenericType/asset/Sample_GenericType"}
    }
    EXPECTED_RN_RES = """
#### Incident Types
- **Cortex XDR Incident**

#### Incident Fields
- **Sample IncidentField**
- **XDR Alerts**

#### Object Types
- **(Asset) - Sample GenericType**

#### Object Fields
- **(Asset) - Sample GenericField**

#### Integrations
##### Cortex XDR - IR
- %%UPDATE_RN%%

##### Sample
- %%UPDATE_RN%%
"""

    diff_package = [('Packs/VulnDB', 'Packs/VulnDB/Layouts/VulnDB/VulnDB.json', FileType.LAYOUT,
                     ('VulnDB', FileType.LAYOUT)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Classifiers/VulnDB/VulnDB.json', FileType.CLASSIFIER,
                     ('VulnDB', FileType.CLASSIFIER)),
                    ('Packs/VulnDB', 'Packs/VulnDB/IncidentTypes/VulnDB/VulnDB.json', FileType.INCIDENT_TYPE,
                     ('VulnDB', FileType.INCIDENT_TYPE)),
                    ('Packs/VulnDB', 'Packs/VulnDB/IncidentFields/VulnDB/VulnDB.json', FileType.INCIDENT_FIELD,
                     ('VulnDB', FileType.INCIDENT_FIELD)),
                    ('Packs/CommonTypes', 'Packs/CommonTypes/IndicatorFields/VulnDB.json', FileType.INDICATOR_FIELD,
                     ('VulnDB', FileType.INDICATOR_FIELD)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Playbooks/VulnDB/VulnDB_playbook.yml', FileType.PLAYBOOK,
                     ('VulnDB', FileType.PLAYBOOK)),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/Playbooks/VulnDB/VulnDB_playbook.yml',
                     FileType.PLAYBOOK, ('VulnDB', FileType.PLAYBOOK)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Scripts/VulnDB/VulnDB.py', FileType.SCRIPT,
                     ('VulnDB', FileType.SCRIPT)),
                    ('Packs/CommonPlaybooks', 'Packs/CommonPlaybooks/Scripts/VulnDB/VulnDB.py', FileType.SCRIPT,
                     ('VulnDB', FileType.SCRIPT)),
                    ('Packs/VulnDB', 'Packs/VulnDB/ReleaseNotes/1_0_1.md', FileType.RELEASE_NOTES,
                     ('VulnDB', FileType.RELEASE_NOTES)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Integrations/VulnDB/VulnDB.yml', FileType.INTEGRATION,
                     ('VulnDB', FileType.INTEGRATION)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Connections/VulnDB/VulnDB.yml', FileType.CONNECTION,
                     ('VulnDB', FileType.CONNECTION)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Dashboards/VulnDB/VulnDB.yml', FileType.DASHBOARD,
                     ('VulnDB', FileType.DASHBOARD)),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/Dashboards/VulnDB/VulnDB.yml', FileType.DASHBOARD,
                     ('VulnDB', FileType.DASHBOARD)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Widgets/VulnDB/VulnDB.yml', FileType.WIDGET,
                     ('VulnDB', FileType.WIDGET)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Reports/VulnDB/VulnDB.yml', FileType.REPORT,
                     ('VulnDB', FileType.REPORT)),
                    ('Packs/VulnDB', 'Packs/VulnDB/IndicatorTypes/VulnDB/VulnDB.yml', FileType.REPUTATION,
                     ('VulnDB', FileType.REPUTATION)),
                    ('Packs/VulnDB', 'Packs/VulnDB/TestPlaybooks/VulnDB/VulnDB.yml', FileType.TEST_PLAYBOOK,
                     ('VulnDB', FileType.TEST_PLAYBOOK)),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/TestPlaybooks/VulnDB/VulnDB.yml',
                     FileType.TEST_PLAYBOOK, ('VulnDB', FileType.TEST_PLAYBOOK)),
                    ]

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Tests below modify the file: 'demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json'
        We back it up and restore when done.

        """
        self.meta_backup = str(tmp_path / 'pack_metadata-backup.json')
        shutil.copy('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json',
                    self.meta_backup)

    def teardown(self):
        if self.meta_backup:
            shutil.copy(self.meta_backup,
                        'demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json')
        else:
            raise Exception('Expecting self.meta_backup to be set inorder to restore pack_metadata.json file')

    @pytest.mark.parametrize('pack_name, path, find_type_result, expected_result', diff_package)
    def test_get_changed_file_name_and_type(self, pack_name, path, find_type_result, expected_result, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path=pack_name, update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, path)
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.find_type', return_value=find_type_result)
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'ReleaseNotes')
        update_rn = UpdateRN(pack_path="Packs/VulnDB", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/VulnDB", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'ReleaseNotes/1_1_1.md')
        md_string = '### Test'
        update_rn.create_markdown(release_notes_path=filepath, rn_string=md_string, changed_files={})

    def test_update_existing_rn(self, mocker):
        """
            Given:
                - Existing release notes and set of changed files
            When:
                - rerunning the update command
            Then:
                - return updated release notes while preserving the integrity of the existing notes.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.get_definition_name', return_value="Asset")
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
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
        ORIGINAL = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        TEMP_FILE = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json')
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        shutil.copy(src=ORIGINAL, dst=TEMP_FILE)
        data_dict = get_json(TEMP_FILE)
        update_rn.metadata_path = TEMP_FILE
        update_rn.write_metadata_to_file(data_dict)
        os.remove(ORIGINAL)
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        added_files = {'HelloWorld/something_new.md', 'HelloWorld/test_data/nothing.md'}
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack=set(),
                             added_files=added_files)
        update_rn.find_added_pack_files()
        assert update_rn.modified_files_in_pack == {'HelloWorld/something_new.md'}

    def test_does_pack_metadata_exist_no(self, mocker):
        """
            Given:
                - Checking for the existance of a pack metadata file
            When:
                - metadata path is invalid
            Then:
                - return False to indicate it does not exist.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack=set(),
                             added_files=set())
        update_rn.metadata_path = 'This/Doesnt/Exist'
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/Legacy", update_type='minor', modified_files_in_pack=set(),
                             added_files=set())
        update_rn.execute_update()

    diff_package = [
        ("1.0.1", "1.0.2", True),
        ("1.0.5", "1.0.4", False),
        ("1.0.5", "1.0.5", True),
        ("1.0.0", DEFAULT_CONTENT_ITEM_TO_VERSION, True)
    ]

    @pytest.mark.parametrize('pack_current_version, git_current_version, expected_result', diff_package)
    def test_is_bump_required(self, pack_current_version, git_current_version, expected_result, mocker):
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
        import json
        from subprocess import Popen

        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value=git_current_version)
        update_rn = UpdateRN(pack_path="Packs/Base", update_type='minor', modified_files_in_pack=set(),
                             added_files=set())
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={"currentVersion": pack_current_version})
        # mocking the only_docs_changed to test only the is_bump_required
        mocker.patch.object(UpdateRN, 'only_docs_changed', return_value=False)
        mocker.patch.object(Popen, 'communicate',
                            return_value=(json.dumps({"currentVersion": git_current_version}), ''))
        mocker.patch('sys.exit', return_value=None)
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        modified_files = {
            'file1',
            ('file2', 'file2_new'),
            'file3'
        }
        update_rn = UpdateRN(pack_path="Packs/Base", update_type='minor', modified_files_in_pack=modified_files,
                             added_files=set())

        assert 'file1' in update_rn.modified_files_in_pack
        assert 'file2_new' in update_rn.modified_files_in_pack
        assert ('file2', 'file2_new') not in update_rn.modified_files_in_pack
        assert 'file3' in update_rn.modified_files_in_pack

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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        image_file_path = "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2_image.png"
        description_file_path = "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2_description.md"
        yml_file_path = "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2.yml"

        assert yml_file_path == UpdateRN.change_image_or_desc_file_path(image_file_path)
        assert yml_file_path == UpdateRN.change_image_or_desc_file_path(description_file_path)
        assert yml_file_path == UpdateRN.change_image_or_desc_file_path(yml_file_path)

    def test_update_api_modules_dependents_rn__no_id_set(self, mocker):
        """
        Given:
            - The file system has no id_set.json in its root
        When:
            - update_api_modules_rn is called without an id_set.json
        Then:
            - Call print_error with the appropriate error message
        """
        import demisto_sdk.commands.update_release_notes.update_rn
        from demisto_sdk.commands.update_release_notes.update_rn import \
            update_api_modules_dependents_rn
        if os.path.exists(DEFAULT_ID_SET_PATH):
            os.remove(DEFAULT_ID_SET_PATH)
        print_error_mock = mocker.patch.object(demisto_sdk.commands.update_release_notes.update_rn, "print_error")
        update_api_modules_dependents_rn(pre_release='', update_type='', added='', modified='',
                                         id_set_path=None)
        assert 'no id_set.json is available' in print_error_mock.call_args[0][0]

    def test_update_api_modules_dependents_rn__happy_flow(self, mocker, tmpdir):
        """
        Given
            - ApiModules_script.yml which is part of APIModules pack was changed.
            - id_set.json indicates FeedTAXII uses APIModules

        When
            - update_api_modules_rn is called with an id_set.json

        Then
            - Ensure execute_update_mock is called
        """
        from demisto_sdk.commands.update_release_notes.update_rn import (
            UpdateRN, update_api_modules_dependents_rn)
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')

        modified = {'/Packs/ApiModules/Scripts/ApiModules_script/ApiModules_script.yml'}
        added = {}
        id_set_content = {'integrations':
                          [
                              {'FeedTAXII_integration':
                               {'name': 'FeedTAXII_integration',
                                'file_path': '/FeedTAXII_integration.yml',
                                'pack': 'FeedTAXII',
                                'api_modules': 'ApiModules_script'
                                }
                               }
                          ]}
        id_set_f = tmpdir / "id_set.json"
        id_set_f.write(json.dumps(id_set_content))

        execute_update_mock = mocker.patch.object(UpdateRN, "execute_update")

        update_api_modules_dependents_rn(pre_release=None, update_type=None, added=added,
                                         modified=modified, id_set_path=id_set_f.strpath)
        assert execute_update_mock.call_count == 1

    def test_update_docker_image_when_yml_has_changed_but_not_docker_image_property(self, mocker):
        """
        Given
            - Modified .yml file
        When
            - Working on an integration's yml, but haven't update docker image

        Then
            - No changes should be done in release notes
        """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            check_docker_image_changed

        return_value = '+category: Utilities\
                        +commonfields:\
                        +  id: Test\
                        +  version: -1\
                        +configuration:\
                        +- defaultvalue: https://soar.test.com\
                        +  display: Server URL (e.g. https://soar.test.com)\
                        +- display: Fetch incidents\
                        +  name: isFetch\
                        +- display: Incident type'

        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command', return_value=return_value)

        assert check_docker_image_changed(main_branch='origin/master', packfile='test.yml') is None

    def test_update_docker_image_in_yml(self, mocker):
        """
        Given
            - Modified .yml file
        When
            - Updating docker image tag

        Then
            - A new release notes is created. and it has a new record for updating docker image.
        """
        import os

        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        expected_res = "diff --git a/Packs/test1/Integrations/test1/test1.yml b/Packs/test1/Integrations/test1/test1.yml\n" \
                       "--- a/Packs/test1/Integrations/test1/test1.yml\n" \
                       "+++ b/Packs/test1/Integrations/test1/test1.yml\n" \
                       "@@ -1270,7 +1270,7 @@ script:\n" \
                       "description: update docker image.\n" \
                       "execution: false\n" \
                       "name: test1\n" \
                       "-  dockerimage: demisto/python3:3.9.6.22912\n" \
                       "+  dockerimage: demisto/python3:3.9.6.22914\n" \
                       "feed: false\n" \
                       "isfetch: false\n" \
                       "longRunning: false\n"

        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json', 'r') as file:
            pack_data = json.load(file)
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command',
                     return_value=expected_res)
        mocker.patch.object(UpdateRN, 'is_bump_required', return_value=False)
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value=pack_data)
        mocker.patch.object(UpdateRN, 'get_changed_file_name_and_type', return_value=('Test', FileType.INTEGRATION))
        mocker.patch.object(UpdateRN, 'get_release_notes_path',
                            return_value='demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes'
                                         '/1_1_0.md')
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')

        client = UpdateRN(pack_path="demisto_sdk/commands/update_release_notes/tests_data/Packs/Test",
                          update_type='minor', modified_files_in_pack={'Packs/Test/Integrations/Test.yml'},
                          added_files=set())
        client.execute_update()
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md', 'r') as file:
            RN = file.read()
        os.remove('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md')
        assert 'Updated the Docker image to: *demisto/python3:3.9.6.22914*.' in RN

    def test_update_docker_image_in_yml_when_RN_aleady_exists(self, mocker):
        """
        Given
            - Modified .yml file, but relevant release notes is already exist.
        When
            - Updating docker image tag.

        Then
            - A new record with the updated docker image is added.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json', 'r') as file:
            pack_data = json.load(file)
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_0_0.md', 'w') as file:
            file.write('### Integrations\n')
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command',
                     return_value='+  dockerimage:python/test:1243')
        mocker.patch.object(UpdateRN, 'is_bump_required', return_value=False)
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value=pack_data)
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='Test')
        mocker.patch.object(UpdateRN, 'build_rn_template', return_value='##### Test\n')
        mocker.patch.object(UpdateRN, 'get_release_notes_path',
                            return_value='demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes'
                                         '/1_0_0.md')
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        mocker.patch.object(UpdateRN, 'get_changed_file_name_and_type', return_value=('Test', FileType.INTEGRATION))

        client = UpdateRN(pack_path="Packs/Test", update_type=None,
                          modified_files_in_pack={'Packs/Test/Integrations/Test.yml'}, added_files=set())
        client.execute_update()
        client.execute_update()
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_0_0.md', 'r') as file:
            RN = file.read()
        assert RN.count('Updated the Docker image to: *dockerimage:python/test:1243*.') == 1

        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_0_0.md', 'w') as file:
            file.write('')

    def test_add_and_modify_files_without_update_docker_image(self, mocker):
        """
        Given
            - Modified .yml file, but relevant release notes is already exist.
        When
            - Updating docker image tag.

        Then
            - A new record with the updated docker image is added.
        """
        import os

        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json', 'r') as file:
            pack_data = json.load(file)
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command',
                     return_value='+  type:True')
        mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value=pack_data)
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='Test')
        mocker.patch.object(UpdateRN, 'build_rn_template', return_value='##### Test\n')
        mocker.patch.object(UpdateRN, 'get_release_notes_path', return_value='demisto_sdk/commands'
                                                                             '/update_release_notes/tests_data'
                                                                             '/Packs/release_notes/1_1_0.md')
        mocker.patch.object(UpdateRN, 'get_changed_file_name_and_type', return_value=('Test', FileType.INTEGRATION))
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        client = UpdateRN(pack_path="demisto_sdk/commands/update_release_notes/tests_data/Packs/Test",
                          update_type='minor', modified_files_in_pack={
                              'Packs/Test/Integrations/Test.yml'}, added_files=set('Packs/Test/some_added_file.py'))
        client.execute_update()
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md', 'r') as file:
            RN = file.read()
        os.remove('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md')
        assert 'Updated the Docker image to: *dockerimage:python/test:1243*' not in RN

    def test_new_integration_docker_not_updated(self, mocker):
        """
        Given
            - New integration created.
        When
            - Running update-release-notes command

        Then
            - Docker is not indicated as updated.
        """
        import os

        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json', 'r') as file:
            pack_data = json.load(file)
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command',
                     return_value='+  dockerimage:python/test:1243')
        mocker.patch.object(UpdateRN, 'is_bump_required', return_value=False)
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value=pack_data)
        mocker.patch.object(UpdateRN, 'build_rn_template', return_value='##### Test')
        mocker.patch.object(UpdateRN, 'get_changed_file_name_and_type', return_value=('Test', FileType.INTEGRATION))
        mocker.patch.object(UpdateRN, 'get_release_notes_path',
                            return_value='demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes'
                                         '/1_1_0.md')
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')

        client = UpdateRN(pack_path="demisto_sdk/commands/update_release_notes/tests_data/Packs/Test",
                          update_type='minor', modified_files_in_pack={'Packs/Test/Integrations/Test.yml'},
                          added_files={'Packs/Test/Integrations/Test.yml'})
        client.execute_update()
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md', 'r') as file:
            RN = file.read()
        os.remove('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md')
        assert 'Updated the Docker image to: *dockerimage:python/test:1243*' not in RN

    docker_image_test_rn = '#### Integrations\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n- Updated the Docker image ' \
                           'to: *demisto/python3:3.9.1.149615*.\n'
    docker_image_test_data = [
        ('#### Integrations\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n', None,
         '#### Integrations\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n', False),
        ('#### Integrations\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n', 'demisto/python3:3.9.1.149615',
         docker_image_test_rn, True),
        (docker_image_test_rn, 'demisto/python3:3.9.1.149615', docker_image_test_rn, False),
        (docker_image_test_rn, 'demisto/python3:3.9.1.149616',
         '#### Integrations\n##### BitcoinAbuse Feed\n- %%UPDATE_RN%%\n- Updated the Docker image '
         'to: *demisto/python3:3.9.1.149616*.\n', True)
    ]

    BUILD_RN_CONFIG_FILE_INPUTS = [(False, None, None),
                                   (True, None, {'breakingChanges': True, 'breakingChangesNotes': None}),
                                   (True, {'breakingChanges': True},
                                    {'breakingChanges': True, 'breakingChangesNotes': None}),
                                   (True, {'breakingChanges': True, 'breakingChangesNotes': 'bc notes'},
                                    {'breakingChanges': True, 'breakingChangesNotes': 'bc notes'})
                                   ]

    @pytest.mark.parametrize('is_bc, existing_conf_data, expected_conf_data', BUILD_RN_CONFIG_FILE_INPUTS)
    def test_build_rn_config_file(self, pack, is_bc: bool, existing_conf_data: Optional[Dict],
                                  expected_conf_data: Optional[Dict]):
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
        from demisto_sdk.commands.update_release_notes.update_rn import \
            UpdateRN
        client = UpdateRN(pack_path=pack.path, update_type=None, modified_files_in_pack=set(), added_files=set(),
                          is_bc=is_bc)
        conf_path: str = f'{pack.path}/ReleaseNotes/1_0_1.json'
        if existing_conf_data:
            with open(conf_path, 'w') as f:
                f.write(json.dumps(existing_conf_data))
        client.build_rn_config_file('1.0.1')
        if expected_conf_data:
            assert os.path.exists(conf_path)
            with open(conf_path, 'r') as f:
                assert json.loads(f.read()) == expected_conf_data
        else:
            assert not os.path.exists(conf_path)


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
    from demisto_sdk.commands.update_release_notes.update_rn import \
        get_from_version_at_update_rn

    integration.yml.write_dict({'fromversion': '5.0.0'})
    fromversion = get_from_version_at_update_rn(integration.yml.path)
    assert fromversion == '5.0.0'
    fromversion = get_from_version_at_update_rn('fake_path.yml')
    assert fromversion is None


@pytest.mark.parametrize('data, answer', [({'brandName': 'TestBrand'}, 'TestBrand'), ({'id': 'TestID'}, 'TestID'),
                                          ({'name': 'TestName'}, 'TestName'), ({'TypeName': 'TestType'}, 'TestType'),
                                          ({'display': 'TestDisplay'}, 'TestDisplay'),
                                          ({'layout': {'id': 'Testlayout'}}, 'Testlayout')])
def test_get_display_name(data, answer, mocker):
    """
        Given
            - Pack to update release notes
        When
            - get_display_name with file path is called
        Then
           - Returned name determined by the key of the data loaded from the file
        """
    from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
    mock_object = mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.StructureValidator')
    mock_structure_validator = mock_object.return_value
    mock_structure_validator.load_data_from_file.return_value = data
    client = UpdateRN(pack_path="Packs/Test", update_type='minor', modified_files_in_pack={
        'Packs/Test/Integrations/Test.yml'}, added_files=set('Packs/Test/some_added_file.py'))
    assert client.get_display_name('Packs/Test/test.yml') == answer


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
    yml_mock = {'display': 'test', 'script': {'type': 'python', 'dockerimage': 'demisto/python3:3.9.5.123'}}
    pack = repo.create_pack('PackName')
    mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.check_docker_image_changed',
                 return_value='demisto/python3:3.9.5.124')
    integration = pack.create_integration('integration', 'bla', yml_mock)
    integration.create_default_integration()
    integration.yml.update({'display': 'Sample1'})
    integration2 = pack.create_integration('integration2', 'bla2', yml_mock)
    integration2.create_default_integration()
    integration2.yml.update({'display': 'Sample2'})
    pack.pack_metadata.write_json({'currentVersion': '0.0.0'})
    client = UpdateRN(pack_path=str(pack.path), update_type='revision',
                      modified_files_in_pack={f'{str(integration.path)}/integration.yml',
                                              f'{str(integration2.path)}/integration2.yml'}, added_files=set())
    client.execute_update()
    with open(str(f'{pack.path}/ReleaseNotes/0_0_1.md')) as f:
        rn_text = f.read()
    assert rn_text.count('Updated the Docker image to: *demisto/python3:3.9.5.124*.') == 2
    mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.check_docker_image_changed',
                 return_value='demisto/python3:3.9.5.125')
    client = UpdateRN(pack_path=str(pack.path), update_type=None,
                      modified_files_in_pack={f'{str(integration.path)}/integration.yml',
                                              f'{str(integration2.path)}/integration2.yml'}, added_files=set())
    client.execute_update()
    with open(str(f'{pack.path}/ReleaseNotes/0_0_1.md')) as f:
        rn_text = f.read()
    assert rn_text.count('Updated the Docker image to: *demisto/python3:3.9.5.124*.') == 0
    assert rn_text.count('Updated the Docker image to: *demisto/python3:3.9.5.125*.') == 2


HANDLE_EXISTING_RN_WITH_DOCKER_IMAGE_INPUTS = [
    ('#### Integrations\n##### IBM QRadar v2\n- %%UPDATE_RN%%\n##### IBM QRadar v3\n- %%UPDATE_RN%%',
     'Integrations', 'demisto/python3:3.9.5.21276', 'IBM QRadar v3',
     '#### Integrations\n##### IBM QRadar v2\n- %%UPDATE_RN%%\n##### IBM QRadar v3\n- Updated the Docker image to: '
     '*demisto/python3:3.9.5.21276*.\n- %%UPDATE_RN%%'),
    ('#### Integrations\n##### IBM QRadar v3\n- %%UPDATE_RN%%',
     'Integrations', 'demisto/python3:3.9.5.21276', 'IBM QRadar v3',
     '#### Integrations\n##### IBM QRadar v3\n- Updated the Docker image to: '
     '*demisto/python3:3.9.5.21276*.\n- %%UPDATE_RN%%')]


@pytest.mark.parametrize('new_rn, header_by_type, docker_image, content_name, expected',
                         HANDLE_EXISTING_RN_WITH_DOCKER_IMAGE_INPUTS)
def test_handle_existing_rn_with_docker_image(new_rn: str, header_by_type: str, docker_image: str,
                                              content_name: str, expected: str):
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
    assert UpdateRN.handle_existing_rn_with_docker_image(new_rn, header_by_type, docker_image,
                                                         content_name) == expected


@pytest.mark.parametrize('text, expected_rn_string',
                         [('Testing the upload', '##### PackName\n- Testing the upload\n')])
def test_force_and_text_update_rn(repo, text, expected_rn_string):
    """
    Given:
    - New release note

    When:
    - Updating release notes with *--force* and *--text* flags

    Then:
    - Ensure the release note includes the given text
    """
    pack = repo.create_pack('PackName')
    client = UpdateRN(pack_path=str(pack.path), update_type=None, modified_files_in_pack=set(), added_files=set(),
                      is_force=True, text=text)

    rn_string = client.build_rn_template({})
    assert rn_string == expected_rn_string
