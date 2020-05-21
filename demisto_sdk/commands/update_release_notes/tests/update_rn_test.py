import os
import shutil
import unittest

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
        expected_result = "\n### Integrations\n- __Hello World Integration__\n%%UPDATE_RN%%\n" \
                          "\n### Playbooks\n- __Hello World Playbook__\n%%UPDATE_RN%%\n" \
                          "\n### Scripts\n- __Hello World Script__\n%%UPDATE_RN%%\n" \
                          "\n### IncidentFields\n- __Hello World IncidentField__\n%%UPDATE_RN%%\n" \
                          "\n### Classifiers\n- __Hello World Classifier__\n%%UPDATE_RN%%\n" \
                          "\n### Layouts\n- __Hello World Layout__\n%%UPDATE_RN%%\n" \
                          "\n### IncidentTypes\n- __Hello World Incident Type__\n%%UPDATE_RN%%\n"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        changed_items = {
            "Hello World Integration": "Integration",
            "Hello World Playbook": "Playbook",
            "Hello World Script": "Script",
            "Hello World IncidentField": "IncidentFields",
            "Hello World Classifier": "Classifiers",
            "N/A": "Integration",
            "Hello World Layout": "Layouts",
            "Hello World Incident Type": "IncidentTypes",
        }
        release_notes = update_rn.build_rn_template(changed_items)
        assert expected_result == release_notes

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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False)
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='major', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False)
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='revision', pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number, _ = update_rn.bump_version_number(pre_release=False)
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='revision', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='major', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='major', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="HelloWorld", update_type=None, pack_files={'HelloWorld'}, added_files=set())
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack_invalid/pack_metadata.json')
        version, data = update_rn.bump_version_number()
        assert version == '99.99.99'


class TestRNUpdateUnit:
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    CURRENT_RN = """
### IncidentTypes
- __Cortex XDR Incident__
%%UPDATE_RN%%

### IncidentFields
- __XDR Alerts__
%%UPDATE_RN%%
"""
    CHANGED_FILES = {
        "Cortex XDR Incident": "IncidentType",
        "XDR Alerts": "IncidentField",
        "Sample IncidentField": "IncidentField",
        "Cortex XDR - IR": "Integration",
        "Nothing": None,
        "Sample": "Integration",
    }
    EXPECTED_RN_RES = """
### IncidentTypes
- __Cortex XDR Incident__
%%UPDATE_RN%%

### IncidentFields
- __Sample IncidentField__
%%UPDATE_RN%%

- __XDR Alerts__
%%UPDATE_RN%%

### Integration
- __Sample__
%%UPDATE_RN%%

- __Cortex XDR - IR__
%%UPDATE_RN%%
"""

    def test_ident_changed_file_type_integration(self, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('VulnDB', 'Integration')
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'Integration/VulnDB/VulnDB.py')
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_ident_changed_file_type_release_notes(self):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('N/A', None)
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'ReleaseNotes/1_0_1.md')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_ident_changed_file_type_script(self, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('VulnDB', 'Script')
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'Script/VulnDB/VulnDB.py')
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_ident_changed_file_type_playbooks(self, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('VulnDB', 'Playbook')
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'Playbooks/VulnDB/VulnDB_playbook.yml')
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_ident_changed_file_type_incident_fields(self, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('VulnDB', 'IncidentFields')
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'IncidentFields/VulnDB/VulnDB.json')
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_ident_changed_file_type_incident_types(self, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('VulnDB', 'IncidentTypes')
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'IncidentTypes/VulnDB/VulnDB.json')
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_ident_changed_file_type_classifiers(self, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('VulnDB', 'Classifiers')
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'Classifiers/VulnDB/VulnDB.json')
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.identify_changed_file_type(filepath)
        assert expected_result == result

    def test_ident_changed_file_type_layouts(self, mocker):
        """
            Given:
                - a filepath of a changed file
            When:
                - determining the type of item changed (e.g. Integration, Script, Layout, etc.)
            Then:
                - return tuple where first value is the pack name, and second is the item type
        """
        expected_result = ('VulnDB', 'Layout')
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'Layouts/VulnDB/VulnDB.json')
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
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="VulnDB", update_type='minor', pack_files={'HelloWorld'}, added_files=set())
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files={'HelloWorld'},
                             added_files=set())
        new_rn = update_rn.update_existing_rn(self.CURRENT_RN, self.CHANGED_FILES)
        print(new_rn)
        assert new_rn == self.EXPECTED_RN_RES

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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files={'HelloWorld'},
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files=set(),
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor', pack_files=set(),
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
        update_rn = UpdateRN(pack="Legacy", update_type='minor', pack_files=set(),
                             added_files=set())
        update_rn.execute_update()
