import click
import demisto_client
import pytest
from demisto_client.demisto_api import DefaultApi

from demisto_sdk.__main__ import run_test_playbook
from demisto_sdk.commands.run_test_playbook.test_playbook_runner import \
    TestPlaybookRunner
from demisto_sdk.tests.constants_test import (CONTENT_REPO_EXAMPLE_ROOT,
                                              TEST_PLAYBOOK, VALID_PACK)
from TestSuite.test_tools import ChangeCWD


class TestTestPlaybookRunner:

    @pytest.mark.parametrize(argnames='tpb_result, res', argvalues=[('failed', 1),
                                                                    ('success', 0)])
    def test_run_specific_test_playbook(self, mocker, tpb_result, res):
        """
        Given:
            - run specific test playbook with result as True or False
        When:
            - run the run_test_playbook command
        Then:
            - validate the results is aas expected
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={"state": tpb_result})
        result = click.Context(command=run_test_playbook).invoke(run_test_playbook, input=TEST_PLAYBOOK)
        assert result == res

    @pytest.mark.parametrize(argnames='tpb_result, res', argvalues=[('failed', 1),
                                                                    ('success', 0)])
    def test_run_pack_test_playbooks(self, mocker, tpb_result, res):
        """
        Given:
            - run all pack test playbooks with result as True or False
        When:
            - run the run_test_playbook command
        Then:
            - validate the results is aas expected
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={"state": tpb_result})
        result = click.Context(command=run_test_playbook).invoke(run_test_playbook, input=VALID_PACK)
        assert result == res

    @pytest.mark.parametrize(argnames='tpb_result, res', argvalues=[('failed', 1),
                                                                    ('success', 0)])
    def test_run_repo_test_playbooks(self, mocker, tpb_result, res):
        """
        Given:
            - run all repo test playbook with result as True or False
        When:
            - run the run_test_playbook command
        Then:
            - validate the results is aas expected
        """
        with ChangeCWD(CONTENT_REPO_EXAMPLE_ROOT):
            mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
            mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
            mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={"state": tpb_result})
            result = click.Context(command=run_test_playbook).invoke(run_test_playbook, all=True, input='')
            assert result == res

    @pytest.mark.parametrize(argnames='input_tpb, exit_code, err',
                             argvalues=[('', 1, "Error: Missing option '-i' / '--input'."),
                                        ('BlaBla', 1, 'Error: Given input path: BlaBla does not exist'),
                                        (VALID_PACK, 0, ''),
                                        (TEST_PLAYBOOK, 0, '')])
    def test_update_config_file_manager(self, mocker, input_tpb, exit_code, err, capsys):
        """
        Given:
            - arguments to the xsoar-configuration-file
        When:
            - check that the update_config_file_manager works as expected
        Then:
            - validate the error code is as expected.
            - validate the Error massage when the argument is missing
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={'state': 'success'})

        self.test_playbook_input = input_tpb
        test_playbook = TestPlaybookRunner(input=self.test_playbook_input)
        error_code = test_playbook.run_test_playbooks_manager()
        assert error_code == exit_code

        stdout, _ = capsys.readouterr()
        if err:
            assert err in stdout

    # def test_run_test_playbook_by_id(self, mocker, playbook_id):
    #     mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
    #     mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={'state': 'success'})
