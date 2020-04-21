import os

from demisto_sdk.commands.common.git_tools import git_path


class TestRNUpdate:
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))

    def test_build_rn_template(self):
        """
            Given:
                - a dict of changed items
            When:
                - we want to produce a release notes template
            Then:
                - return a markdown string
        """
        expected_result = "\n#### Integrations\n- __Hello World__\n%%UPDATE_RN%%\n"
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor')
        changed_items = {"Hello World": "Integration"}
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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor')
        filepath = 'Integration/HelloWorld.py'
        filename = update_rn.find_corresponding_yml(filepath)
        assert expected_result == filename

    def test_ident_changed_file_type(self, mocker):
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
        update_rn = UpdateRN(pack="VulnDB", update_type='minor')
        filepath = os.path.join(TestRNUpdate.FILES_PATH, 'Integration/VulnDB/VulnDB.py')
        mocker.patch.object(UpdateRN, 'find_corresponding_yml', return_value='Integrations/VulnDB/VulnDB.yml')
        mocker.patch.object(UpdateRN, 'get_display_name', return_value='VulnDB')
        result = update_rn.ident_changed_file_type(filepath)
        assert expected_result == result

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
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor')
        input_version = '1.1.1'
        result = update_rn.return_release_notes_path(input_version)
        assert expected_result == result

    def test_bump_version_number(self):
        """
            Given:
                - a pack name and version
            When:
                - bumping the version number in the metadata.json
            Then:
                - return the correct bumped version number
        """
        expected_version = '1.1.0'
        from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
        update_rn = UpdateRN(pack="HelloWorld", update_type='minor')
        update_rn.metadata_path = os.path.join(TestRNUpdate.FILES_PATH, 'fake_pack/pack_metadata.json')
        version_number = update_rn.bump_version_number(pre_release=False)
        assert version_number == expected_version
