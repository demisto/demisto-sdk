import json
import os
import shutil
import unittest

import mock
import pytest
from demisto_sdk.commands.common.git_tools import git_path
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
            "\n#### Layouts\n- **Hello World Layout**\n" \
            "- **Second Hello World Layout**\n" \
            "\n#### Playbooks\n##### Hello World Playbook\n- %%UPDATE_RN%%\n" \
            "\n#### Reports\n##### Hello World Report\n- %%UPDATE_RN%%\n" \
            "\n#### Scripts\n##### Hello World Script\n- %%UPDATE_RN%%\n" \
            "\n#### Widgets\n##### Hello World Widget\n- %%UPDATE_RN%%\n"

        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            "Hello World Integration": {"type": "Integration", "description": "", "is_new_file": False},
            "Hello World Playbook": {"type": "Playbook", "description": "", "is_new_file": False},
            "Hello World Script": {"type": "Script", "description": "", "is_new_file": False},
            "Hello World IncidentField": {"type": "Incident Fields", "description": "", "is_new_file": False},
            "Hello World Classifier": {"type": "Classifiers", "description": "", "is_new_file": False},
            "N/A": {"type": "Integration", "description": "", "is_new_file": False},
            "Hello World Layout": {"type": "Layouts", "description": "", "is_new_file": False},
            "Hello World Incident Type": {"type": "Incident Types", "description": "", "is_new_file": False},
            "Hello World Indicator Type": {"type": "Indicator Types", "description": "", "is_new_file": False},
            "Hello World Indicator Field": {"type": "Indicator Fields", "description": "", "is_new_file": False},
            "Second Hello World Layout": {"type": "Layouts", "description": "", "is_new_file": False},
            "Hello World Widget": {"type": "Widgets", "description": "", "is_new_file": False},
            "Hello World Dashboard": {"type": "Dashboards", "description": "", "is_new_file": False},
            "Hello World Connection": {"type": "Connections", "description": "", "is_new_file": False},
            "Hello World Report": {"type": "Reports", "description": "", "is_new_file": False},
            "N/A2": {"type": None, "description": "", "is_new_file": True},
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            "Hello World Playbook": {"type": "Playbook",
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            "Hello World Playbook": {"type": "Playbook",
                                     "description": "Hello World Playbook description", "is_new_file": False},
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            "Hello World IncidentField": {"type": "Incident Fields", "description": "", "is_new_file": False},
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='maintenance',
                             modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            "Hello World Integration": {"type": "Integration", "description": "", "is_new_file": False},
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='documentation',
                             modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        changed_items = {
            "Hello World Integration": {"type": "Integration", "description": "", "is_new_file": False},
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        filepath = 'Integration/HelloWorld.py'
        filename = update_rn.find_corresponding_yml(filepath)
        assert expected_result == filename

    @mock.patch.object(UpdateRN, 'get_master_version')
    def test_return_release_notes_path(self, mock_master):
        """
            Given:
                - a pack name and version
            When:
                - building the release notes file within the ReleaseNotes directory
            Then:
                - the filepath of the correct release notes.
        """
        expected_result = 'Packs/HelloWorld/ReleaseNotes/1_1_1.md'
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        input_version = '1.1.1'
        result = update_rn.return_release_notes_path(input_version)
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '0.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='major', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata_.json')
        self.assertRaises(SystemExit, update_rn.bump_version_number)

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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mock_master.return_value = '1.0.0'
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type=None, modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)

    def test_build_rn_desc_new_file(self):
        """
            Given
                - A new file
            When
                - Running the command build_rn_desc on a file in order to generate rn description.
            Then
                - Validate That from-version added to the rn description.
            """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())

        desc = update_rn.build_rn_desc(_type='Test_type', content_name='Hello World Test', desc='Test description',
                                       is_new_file=True, text='', from_version='5.5.0')
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())

        desc = update_rn.build_rn_desc(_type='Test_type', content_name='Hello World Test', desc='Test description',
                                       is_new_file=False, text='', from_version='5.5.0')
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        changed_items = {
            'Hello World Integration': {'type': 'Integration', 'description': "", 'is_new_file': True,
                                        'fromversion': '5.0.0'},
            'Hello World Playbook': {'type': 'Playbook', 'description': '', 'is_new_file': True,
                                     'fromversion': '5.5.0'},
            "Hello World Script": {'type': 'Script', 'description': '', 'is_new_file': True, 'fromversion': '6.0.0'},
        }
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())

        desc = update_rn.build_rn_template(changed_items=changed_items)
        assert '(Available from Cortex XSOAR 5.0.0).' in desc
        assert '(Available from Cortex XSOAR 5.5.0).' in desc
        assert '(Available from Cortex XSOAR 6.0.0).' in desc


class TestRNUpdateUnit:
    META_BACKUP = ""
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    CURRENT_RN = """
#### Incident Types
- **Cortex XDR Incident**

#### Incident Fields
- **XDR Alerts**
"""
    CHANGED_FILES = {
        "Cortex XDR Incident": {"type": "Incident Types", "description": "", "is_new_file": False},
        "XDR Alerts": {"type": "Incident Fields", "description": "", "is_new_file": False},
        "Sample IncidentField": {"type": "Incident Fields", "description": "", "is_new_file": False},
        "Cortex XDR - IR": {"type": "Integration", "description": "", "is_new_file": False},
        "Nothing": {"type": None, "description": "", "is_new_file": False},
        "Sample": {"type": "Integration", "description": "", "is_new_file": False},
    }
    EXPECTED_RN_RES = """
#### Incident Types
- **Cortex XDR Incident**

#### Incident Fields
- **Sample IncidentField**
- **XDR Alerts**

#### Integration
##### Sample
- %%UPDATE_RN%%

##### Cortex XDR - IR
- %%UPDATE_RN%%
"""

    diff_package = [('Packs/VulnDB', 'Packs/VulnDB/Layouts/VulnDB/VulnDB.json', ('VulnDB', 'Layouts')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Classifiers/VulnDB/VulnDB.json', ('VulnDB', 'Classifiers')),
                    ('Packs/VulnDB', 'Packs/VulnDB/IncidentTypes/VulnDB/VulnDB.json', ('VulnDB', 'Incident Types')),
                    ('Packs/VulnDB', 'Packs/VulnDB/IncidentFields/VulnDB/VulnDB.json', ('VulnDB', 'Incident Fields')),
                    ('Packs/CommonTypes', 'Packs/CommonTypes/IndicatorFields/VulnDB.json',
                     ('VulnDB', 'Indicator Fields')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Playbooks/VulnDB/VulnDB_playbook.yml', ('VulnDB', 'Playbook')),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/Playbooks/VulnDB/VulnDB_playbook.yml', ('VulnDB',
                                                                                                         'Playbook')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Scripts/VulnDB/VulnDB.py', ('VulnDB', 'Script')),
                    ('Packs/CommonPlaybooks', 'Packs/CommonPlaybooks/Scripts/VulnDB/VulnDB.py', ('VulnDB', 'Script')),
                    ('Packs/VulnDB', 'Packs/VulnDB/ReleaseNotes/1_0_1.md', ('N/A', None)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Integrations/VulnDB/VulnDB.yml', ('VulnDB', 'Integration')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Connections/VulnDB/VulnDB.yml', ('VulnDB', 'Connections')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Dashboards/VulnDB/VulnDB.yml', ('VulnDB', 'Dashboards')),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/Dashboards/VulnDB/VulnDB.yml',
                     ('VulnDB', 'Dashboards')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Widgets/VulnDB/VulnDB.yml', ('VulnDB', 'Widgets')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Reports/VulnDB/VulnDB.yml', ('VulnDB', 'Reports')),
                    ('Packs/VulnDB', 'Packs/VulnDB/IndicatorTypes/VulnDB/VulnDB.yml', ('VulnDB', 'Indicator Types')),
                    ('Packs/VulnDB', 'Packs/VulnDB/TestPlaybooks/VulnDB/VulnDB.yml', ('N/A', None)),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/TestPlaybooks/VulnDB/VulnDB.yml', ('N/A', None)),
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

    @pytest.mark.parametrize('pack_name, path, expected_result', diff_package)
    def test_ident_changed_file_type(self, pack_name, path, expected_result, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path=pack_name, update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, path)
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        new_rn = update_rn.update_existing_rn(self.CURRENT_RN, self.CHANGED_FILES)
        assert self.EXPECTED_RN_RES == new_rn

    def test_commit_to_bump(self, mocker):
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', modified_files_in_pack={'HelloWorld'},
                             added_files=set())
        shutil.copy(src=ORIGINAL, dst=TEMP_FILE)
        data_dict = get_json(TEMP_FILE)
        update_rn.metadata_path = TEMP_FILE
        update_rn.commit_to_bump(data_dict)
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        update_rn = UpdateRN(pack_path="Packs/Legacy", update_type='minor', modified_files_in_pack=set(),
                             added_files=set())
        update_rn.execute_update()

    diff_package = [
        ("1.0.1", "1.0.2", True),
        ("1.0.5", "1.0.4", False),
        ("1.0.5", "1.0.5", True),
        ("1.0.0", '99.99.99', True)
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        from subprocess import Popen
        import json
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
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

    def test_check_for_release_notes_valid_file_path(self):
        """
        Given:
            case 1: a description file
            case 2: an image file
            case 3: a non-image or description file
        When:
            running check_for_release_notes_valid_file_path method
        Then:
            case 1 & 2: change the file path to the corresponding yml file.
            case 3: file path remains unchnaged
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        image_file_path = "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2_image.png"
        description_file_path = "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2_description.md"
        yml_file_path = "Packs/DNSDB/Integrations/DNSDB_v2/DNSDB_v2.yml"

        assert yml_file_path == UpdateRN.check_for_release_notes_valid_file_path(image_file_path)
        assert yml_file_path == UpdateRN.check_for_release_notes_valid_file_path(description_file_path)
        assert yml_file_path == UpdateRN.check_for_release_notes_valid_file_path(yml_file_path)

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
        from demisto_sdk.commands.update_release_notes.update_rn import update_api_modules_dependents_rn
        if os.path.exists(DEFAULT_ID_SET_PATH):
            os.remove(DEFAULT_ID_SET_PATH)
        print_error_mock = mocker.patch.object(demisto_sdk.commands.update_release_notes.update_rn, "print_error")
        update_api_modules_dependents_rn(_pack='', pre_release='', update_type='', added='', modified='',
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        from demisto_sdk.commands.update_release_notes.update_rn import update_api_modules_dependents_rn
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

        update_api_modules_dependents_rn(_pack='ApiModules', pre_release=None, update_type=None, added=added,
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
        from demisto_sdk.commands.update_release_notes.update_rn import check_docker_image_changed

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

        is_docker_image_changed, docker_image_name = check_docker_image_changed('test.yml')
        assert is_docker_image_changed is False
        assert docker_image_name == ''

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
        import os
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json', 'r') as file:
            pack_data = json.load(file)
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command',
                     return_value='+  dockerimage:python/test:1243')
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.pack_name_to_path',
                     return_value='demisto_sdk/commands/update_release_notes/tests_data/Packs/Test')
        mocker.patch.object(UpdateRN, 'is_bump_required', return_value=False)
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value=pack_data)
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='Test')
        mocker.patch.object(UpdateRN, 'build_rn_template', return_value='##### Test')
        mocker.patch.object(UpdateRN, 'return_release_notes_path',
                            return_value='demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes'
                                         '/1_1_0.md')
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')

        client = UpdateRN(pack_path="Packs/Test", update_type='minor',
                          modified_files_in_pack={'Packs/Test/Integrations/Test.yml'},
                          added_files=set())
        client.execute_update()
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md', 'r') as file:
            RN = file.read()
        os.remove('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md')
        assert 'Updated the Docker image to: *dockerimage:python/test:1243*' in RN

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
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json', 'r') as file:
            pack_data = json.load(file)
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command',
                     return_value='+  dockerimage:python/test:1243')
        mocker.patch.object(UpdateRN, 'is_bump_required', return_value=False)
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value=pack_data)
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='Test')
        mocker.patch.object(UpdateRN, 'build_rn_template', return_value='##### Test\n')
        mocker.patch.object(UpdateRN, 'return_release_notes_path',
                            return_value='demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes'
                                         '/1_0_0.md')
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')

        client = UpdateRN(pack_path="Packs/Test", update_type='minor',
                          modified_files_in_pack={'Packs/Test/Integrations/Test.yml'}, added_files=set())
        client.execute_update()
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_0_0.md', 'r') as file:
            RN = file.read()
        assert 'Updated the Docker image to: *dockerimage:python/test:1243*' in RN

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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        import os
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/Test/pack_metadata.json', 'r') as file:
            pack_data = json.load(file)
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.run_command',
                     return_value='+  type:True')
        mocker.patch('demisto_sdk.commands.update_release_notes.update_rn.pack_name_to_path',
                     return_value='demisto_sdk/commands/update_release_notes/tests_data/Packs/Test')
        mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
        mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value=pack_data)
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='Test')
        mocker.patch.object(UpdateRN, 'build_rn_template', return_value='##### Test\n')
        mocker.patch.object(UpdateRN, 'return_release_notes_path', return_value='demisto_sdk/commands'
                                                                                '/update_release_notes/tests_data'
                                                                                '/Packs/release_notes/1_1_0.md')
        mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
        client = UpdateRN(pack_path="Packs/Test", update_type='minor', modified_files_in_pack={
            'Packs/Test/Integrations/Test.yml'}, added_files=set('Packs/Test/some_added_file.py'))
        client.execute_update()
        with open('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md', 'r') as file:
            RN = file.read()
        os.remove('demisto_sdk/commands/update_release_notes/tests_data/Packs/release_notes/1_1_0.md')
        assert 'Updated the Docker image to: *dockerimage:python/test:1243*' not in RN


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
    from demisto_sdk.commands.update_release_notes.update_rn import get_from_version_at_update_rn

    integration.yml.write_dict({'fromversion': '5.0.0'})
    fromversion = get_from_version_at_update_rn(integration.yml.path)
    assert fromversion == '5.0.0'
    fromversion = get_from_version_at_update_rn('fake_path.yml')
    assert fromversion is None
