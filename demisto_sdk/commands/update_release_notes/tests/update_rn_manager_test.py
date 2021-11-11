import pytest

from demisto_sdk.commands.update_release_notes.update_rn_manager import \
    UpdateReleaseNotesManager


class TestUpdateRNManager:
    get_existing_rn_params = [('Test2', {'Test1': 'path_to_rn'}, None, ''),
                              ('Test1', {'Test1': 'path_to_rn'}, None, 'path_to_rn'),
                              ('Test1', {'Test1': 'path_to_rn'}, 'revision', None)]

    @pytest.mark.parametrize('pack_name, packs_existing_rn, update_type, expected_output', get_existing_rn_params)
    def test_get_existing_rn(self, mocker, pack_name, packs_existing_rn, update_type, expected_output):
        """
        Given:
            - case 1: pack was given but its not in the existing rn dict.
            - case 2: pack was given but no update type was given.
            - case 3: pack was given and update type was given.
        When:
            - get_existing_rn is called.
        Then:
            - case 1: an empty string should be returned.
            - case 2: the path to rn should be returned.
            - case 3: an error should be printed and None should be returned.
        """
        mng = UpdateReleaseNotesManager(update_type=update_type)
        mng.packs_existing_rn = packs_existing_rn
        res = mng.get_existing_rn(pack_name)
        assert res == expected_output

    check_existing_rn_params = [({'Packs/test1/ReleaseNotes/1_0_2.md', 'Packs/test2/ReleaseNotes/1_0_4.md'},
                                 {'test2': 'Packs/test2/ReleaseNotes/1_0_4.md',
                                  'test1': 'Packs/test1/ReleaseNotes/1_0_2.md'}),
                                ({'Packs/test1/1_0_2.md', 'Packs/test2/1_0_4.md'}, {})]

    @pytest.mark.parametrize('added_files, expected_output', check_existing_rn_params)
    def test_check_existing_rn(self, added_files, expected_output):
        """
        Given:
            - case 1: added files under release notes folder.
            - case 2: added files not under release notes folder.
        When:
            - check_existing_rn is called.
        Then:
            - case 1: the pack name and added file should be added to packs_existing_rn dict.
            - case 2: the pack name and added file should not be added to packs_existing_rn dict.
        """
        mng = UpdateReleaseNotesManager()
        mng.check_existing_rn(added_files)

        assert mng.packs_existing_rn == expected_output

    @pytest.mark.parametrize('path_to_api_module', ['Packs/ApiModules/Scripts/Test1', None])
    def test_handle_api_module_change(self, mocker, path_to_api_module):
        """
        Given:
            - case 1: User gave path to updated Api module.
            - case 2: User did not give path to updated Api module.
        When:
            - handle_api_module_change is called.
        Then:
            - case 1: update_api_modules_dependents_rn is called.
            - case 2: update_api_modules_dependents_rn is called.
        """
        from demisto_sdk.commands.update_release_notes import update_rn_manager
        mock_func = mocker.patch.object(update_rn_manager, 'update_api_modules_dependents_rn')
        mng = UpdateReleaseNotesManager(user_input=path_to_api_module)
        if not path_to_api_module:
            mng.changed_packs_from_git = 'Packs/ApiModules/Scripts/Test1'
        mng.handle_api_module_change(set(), set())
        assert mock_func.called

    create_release_notes_params = [('Packs/test1', {'Packs/test1', 'Packs/test2'},),
                                   (None, {'Packs/test1', 'Packs/test2'}),
                                   (None, None)]

    @pytest.mark.parametrize('user_input, git_changed_packs', create_release_notes_params)
    def test_create_release_notes(self, mocker, user_input, git_changed_packs):
        """
        Given:
            - case 1: a path was given by the user in order to update.
            - case 2: a path was not given by the user but files were changed.
            - case 2: a path was not given by the user and files were not changed.
        When:
            - create_release_notes is called.
        Then:
            - case 1: create_pack_release_notes should be called with the user's input as arg.
            - case 2: create_pack_release_notes should be called twice with changed files as args.
            - case 3: a warning should be printed as no changes were detected in order to update.
        """
        mng = UpdateReleaseNotesManager(user_input=user_input)
        mng.changed_packs_from_git = git_changed_packs
        err = mocker.patch('demisto_sdk.commands.update_release_notes.update_rn_manager.print_warning')
        mock_func = mocker.patch.object(UpdateReleaseNotesManager, 'create_pack_release_notes')
        mng.create_release_notes(set(), set(), set())
        if user_input:
            assert mock_func.call_count == 1
        elif git_changed_packs:
            assert mock_func.call_count == 2
        else:
            assert 'No changes that require release notes were detected.' in err.call_args[0][0]

    def test_create_pack_release_notes_pack_success(self, mocker):
        """
        Given:
            - a pack which is in the modified files set.
        When:
            - create_pack_release_notes is called.
        Then:
            - execute_update in UpdateRN should be called.
        """
        from demisto_sdk.commands.update_release_notes.update_rn_manager import \
            UpdateRN

        mng = UpdateReleaseNotesManager()
        mock_func = mocker.patch.object(UpdateRN, 'execute_update', return_result=True)
        mng.create_pack_release_notes('test1', {'Packs/test1', 'Packs/test2'}, set(), set())
        assert mock_func.call_count == 1

    def test_create_pack_release_notes_pack_fail(self, mocker):
        """
        Given:
            - a pack which is not in the modified files set.
        When:
            - create_pack_release_notes is called.
        Then:
            - a warning should be printed which says that no RN is needed here.
        """
        mng = UpdateReleaseNotesManager()
        err = mocker.patch('demisto_sdk.commands.update_release_notes.update_rn_manager.print_warning')
        mng.create_pack_release_notes('test1', {'Packs/test2', 'Packs/test3'}, set(), set())
        assert 'Either no changes were found in test1' in err.call_args[0][0]

    def test_manage_rn_update_fail(self):
        """
        Given:
            - a specific pack is given and -g flag was given.
        When:
            - manage_rn_update is called.
        Then:
            - an error message to remove the -g flag should be printed.
        """
        with pytest.raises(ValueError) as execinfo:
            UpdateReleaseNotesManager(user_input='Packs/test1', is_all=True)
        assert 'Please remove the -g flag' in execinfo.value.args[0]

    def test_manage_rn_update_success(self, mocker):
        """
        Given:
            - a specific pack to update is given.
        When:
            - manage_rn_update is called.
        Then:
            - The update is successfully executed and no error is raised.
        """
        from demisto_sdk.commands.update_release_notes.update_rn_manager import \
            UpdateReleaseNotesManager
        mocker.patch.object(UpdateReleaseNotesManager, 'get_git_changed_files',
                            return_value=({'Packs/test1', 'Packs/test2'}, set(), set()))
        mocker.patch.object(UpdateReleaseNotesManager, 'check_existing_rn')
        mocker.patch.object(UpdateReleaseNotesManager, 'handle_api_module_change')
        func_mock = mocker.patch.object(UpdateReleaseNotesManager, 'create_release_notes')
        mng = UpdateReleaseNotesManager(user_input='Packs/test1')
        mng.manage_rn_update()
        assert func_mock.called
