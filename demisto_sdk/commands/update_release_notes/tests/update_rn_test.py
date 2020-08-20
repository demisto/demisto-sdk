import os
import shutil
import unittest

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import get_json


class TestRNUpdate(unittest.TestCase):
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))

    def test_build_rn_template_integration(self):
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
            "\n#### Indicator Types\n- **Hello World Indicator Type**\n" \
            "\n#### Integrations\n##### Hello World Integration\n- %%UPDATE_RN%%\n" \
            "\n#### Layouts\n- **Hello World Layout**\n" \
            "- **Second Hello World Layout**\n" \
            "\n#### Playbooks\n##### Hello World Playbook\n- %%UPDATE_RN%%\n" \
            "\n#### Reports\n##### Hello World Report\n- %%UPDATE_RN%%\n" \
            "\n#### Scripts\n##### Hello World Script\n- %%UPDATE_RN%%\n" \
            "\n#### Widgets\n##### Hello World Widget\n- %%UPDATE_RN%%\n"

        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
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
            "Second Hello World Layout": {"type": "Layouts", "description": "", "is_new_file": False},
            "Hello World Widget": {"type": "Widgets", "description": "", "is_new_file": False},
            "Hello World Dashboard": {"type": "Dashboards", "description": "", "is_new_file": False},
            "Hello World Connection": {"type": "Connections", "description": "", "is_new_file": False},
            "Hello World Report": {"type": "Reports", "description": "", "is_new_file": False},
            "N/A2": {"type": None, "description": "", "is_new_file": True},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    def test_build_rn_template_playbook_new_file(self):
        """
            Given:
                - a dict of changed items
            When:
                - we want to produce a release notes template for new file
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Playbooks\n##### New: Hello World Playbook\n- Hello World Playbook description\n" \


        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        changed_items = {
            "Hello World Playbook": {"type": "Playbook",
                                     "description": "Hello World Playbook description", "is_new_file": True},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    def test_build_rn_template_playbook_modified_file(self):
        """
            Given:
                - a dict of changed items
            When:
                - we want to produce a release notes template for modified file
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Playbooks\n##### Hello World Playbook\n- %%UPDATE_RN%%\n" \


        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        changed_items = {
            "Hello World Playbook": {"type": "Playbook",
                                     "description": "Hello World Playbook description", "is_new_file": False},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    def test_build_rn_template_file_without_description(self):
        """
            Given:
                - a dict of changed items
            When:
                - we want to produce a release notes template for files without descriptions like :
                'Connections', 'Incident Types', 'Indicator Types', 'Layouts', 'Incident Fields'
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Incident Fields\n- **Hello World IncidentField**\n" \


        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        changed_items = {
            "Hello World IncidentField": {"type": "Incident Fields", "description": "", "is_new_file": False},
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    def test_build_rn_template_when_only_pack_metadata_changed(self):
        """
        Given:
            - an empty dict of changed items
        When:
            - we want to produce release notes template for a pack where only the pack_metadata file changed
        Then:
            - return a markdown string
        """
        expected_result = "\n#### Integrations\n##### HelloWorld\n- Documentation and metadata improvements.\n"\


        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files=set(), added_files=set(),
                             pack_metadata_only=True)
        changed_items = {}
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

    def test_only_readme_changed(self):
        """
        Given:
            - case 1: only the readme was added/modified
            - case 2: other files except the readme were added/modified
        When:
            - calling the function that check if only the readme changed
        Then:
            - case 1: validate that the output of the function is True
            - case 2: validate that the output of the function is False
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN

        # case 1:
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld/README.md'},
                             added_files=set())
        assert update_rn.only_readme_changed()

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files=set(),
                             added_files={'HelloWorld/README.md'})
        assert update_rn.only_readme_changed()

        # case 2:
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld/README.md'},
                             added_files={'HelloWorld/HelloWorld.py'})
        assert not update_rn.only_readme_changed()

        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor',
                             pack_files={'HelloWorld/HelloWorld.yml', 'HelloWorld/README.md'}, added_files=set())
        assert not update_rn.only_readme_changed()

    def test_find_corresponding_yml(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = 'Integration/HelloWorld.py'
        filename = update_rn.find_corresponding_yml(filepath)
        assert expected_result == filename

    def test_return_release_notes_path(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        input_version = '1.1.1'
        result = update_rn.return_release_notes_path(input_version)
        assert expected_result == result

    def test_bump_version_number_minor(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False, specific_version=None)
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    def test_bump_version_number_major(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='major', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False, specific_version=None)
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    def test_bump_version_number_revision(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='revision', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False, specific_version=None)
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    def test_bump_version_number_specific(self):
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
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type=None, specific_version='2.0.0',
                             pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH,
                                               'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False,
                                                          specific_version='2.0.0')
        assert version_number == expected_version
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json'))

    def test_bump_version_number_revision_overflow(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='revision', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))

    def test_bump_version_number_minor_overflow(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))

    def test_bump_version_number_major_overflow(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='major', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)
        os.remove(os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))
        shutil.copy(src=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/_pack_metadata.json'),
                    dst=os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json'))

    def test_bump_version_file_not_found(self):
        """
            Given:
                - a pack name and a metadata which does not exist
            When:
                - bumping the version number in the metadata.json
            Then:
                - return ValueError
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='major', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata_.json')
        self.assertRaises(SystemExit, update_rn.bump_version_number)

    def test_bump_version_no_version(self):
        """
            Given:
                - a pack name and a version before an overflow condition
            When:
                - bumping the version number in the metadata.json
            Then:
                - return ValueError
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type=None, pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        self.assertRaises(ValueError, update_rn.bump_version_number)


class TestRNUpdateUnit:
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
                    ('Packs/VulnDB', 'Packs/VulnDB/Playbooks/VulnDB/VulnDB_playbook.yml', ('VulnDB', 'Playbook')),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/Playbooks/VulnDB/VulnDB_playbook.yml', ('VulnDB',
                                                                                                         'Playbook')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Scripts/VulnDB/VulnDB.py', ('VulnDB', 'Script')),
                    ('Packs/CommonPlaybooks', 'Packs/CommonPlaybooks/Scripts/VulnDB/VulnDB.py', ('VulnDB', 'Script')),
                    ('Packs/VulnDB', 'Packs/VulnDB/ReleaseNotes/1_0_1.md', ('N/A', None)),
                    ('Packs/VulnDB', 'Packs/VulnDB/Integrations/VulnDB/VulnDB.yml', ('VulnDB', 'Integration')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Connections/VulnDB/VulnDB.yml', ('VulnDB', 'Connections')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Dashboards/VulnDB/VulnDB.yml', ('VulnDB', 'Dashboards')),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/Dashboards/VulnDB/VulnDB.yml', ('VulnDB', 'Dashboards')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Widgets/VulnDB/VulnDB.yml', ('VulnDB', 'Widgets')),
                    ('Packs/VulnDB', 'Packs/VulnDB/Reports/VulnDB/VulnDB.yml', ('VulnDB', 'Reports')),
                    ('Packs/VulnDB', 'Packs/VulnDB/IndicatorTypes/VulnDB/VulnDB.yml', ('VulnDB', 'Indicator Types')),
                    ('Packs/VulnDB', 'Packs/VulnDB/TestPlaybooks/VulnDB/VulnDB.yml', ('N/A', None)),
                    ('Packs/CommonScripts', 'Packs/CommonScripts/TestPlaybooks/VulnDB/VulnDB.yml', ('N/A', None)),
                    ]

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
        update_rn = UpdateRN(pack_path=pack_name, update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, path)
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_check_rn_directory(self):
        """
            Given:
                - a filepath for a release notes directory
            When:
                - determining if the directory exists
            Then:
                - create the directory if it does not exist
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'ReleaseNotes')
        update_rn = UpdateRN(pack_path="Packs/VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        update_rn.check_rn_dir(filepath)

    def test_create_markdown(self):
        """
            Given:
                - a filepath for a release notes file and a markdown string
            When:
                - creating a new markdown file
            Then:
                - create the file or skip if it exists.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'ReleaseNotes/1_1_1.md')
        md_string = '### Test'
        update_rn.create_markdown(release_notes_path=filepath, rn_string=md_string, changed_files={})

    def test_update_existing_rn(self):
        """
            Given:
                - Existing release notes and set of changed files
            When:
                - rerunning the update command
            Then:
                - return updated release notes while preserving the integrity of the existing notes.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'},
                             added_files=set())
        new_rn = update_rn.update_existing_rn(self.CURRENT_RN, self.CHANGED_FILES)
        assert self.EXPECTED_RN_RES == new_rn

    def test_commit_to_bump(self):
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
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files={'HelloWorld'},
                             added_files=set())
        shutil.copy(src=ORIGINAL, dst=TEMP_FILE)
        data_dict = get_json(TEMP_FILE)
        update_rn.metadata_path = TEMP_FILE
        update_rn.commit_to_bump(data_dict)
        os.remove(ORIGINAL)
        shutil.copy(src=TEMP_FILE, dst=ORIGINAL)

    def test_find_added_pack_files(self):
        """
            Given:
                - List of added files
            When:
                - searching for relevant pack files
            Then:
                - return a list of relevant pack files which were added.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        added_files = {'HelloWorld/something_new.md', 'HelloWorld/test_data/nothing.md'}
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files=set(),
                             added_files=added_files)
        update_rn.find_added_pack_files()
        assert update_rn.pack_files == {'HelloWorld/something_new.md'}

    def test_does_pack_metadata_exist_no(self):
        """
            Given:
                - Checking for the existance of a pack metadata file
            When:
                - metadata path is invalid
            Then:
                - return False to indicate it does not exist.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/HelloWorld", update_type='minor', pack_files=set(),
                             added_files=set())
        update_rn.metadata_path = 'This/Doesnt/Exist'
        result = update_rn._does_pack_metadata_exist()
        assert result is False

    def test_execute_update_invalid(self):
        """
            Given:
                - A protected pack name
            When:
                - running the update command
            Then:
                - return an error message and exit.
        """
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack_path="Packs/Legacy", update_type='minor', pack_files=set(),
                             added_files=set())
        update_rn.execute_update()
