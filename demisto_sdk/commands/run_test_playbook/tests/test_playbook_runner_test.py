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

WAITING_MASSAGE = "Waiting for the test playbook to finish running.."
LINK_MASSAGE = 'To see the test playbook run in real-time please go to :'
SUCCESS_MASSAGE = 'The test playbook has completed its run successfully'
FAILED_MASSAGE = 'The test playbook finished running with status: FAILED'


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
        mocker.patch.object(TestPlaybookRunner, 'print_tpb_error_details')
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={"state": tpb_result})
        result = click.Context(command=run_test_playbook).invoke(run_test_playbook, test_playbook_path=TEST_PLAYBOOK)
        assert result == res

    @pytest.mark.parametrize(argnames='tpb_result, res, massage', argvalues=[('failed', 1, FAILED_MASSAGE),
                                                                             ('success', 0, SUCCESS_MASSAGE)])
    def test_run_pack_test_playbooks(self, mocker, tpb_result, res, massage, capsys):
        """
        Given:
            - run all pack test playbooks with result as True or False
        When:
            - run the run_test_playbook command
        Then:
            - validate the results is aas expected
            - validate the num of tpb is as expected (4 tpb in Azure Pack)
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'print_tpb_error_details')
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={"state": tpb_result})
        result = click.Context(command=run_test_playbook).invoke(run_test_playbook, test_playbook_path=VALID_PACK)
        assert result == res

        stdout, _ = capsys.readouterr()
        assert stdout.count(massage) == 4

    @pytest.mark.parametrize(argnames='tpb_result, res, massage', argvalues=[('failed', 1, FAILED_MASSAGE),
                                                                             ('success', 0, SUCCESS_MASSAGE)])
    def test_run_repo_test_playbooks(self, mocker, tpb_result, res, massage, capsys):
        """
        Given:
            - run all repo test playbook with result as True or False
        When:
            - run the run_test_playbook command
        Then:
            - validate the results is aas expected
            - validate the num of tpb is as expected (7 tpb in CONTENT_REPO_EXAMPLE_ROOT)
        """
        with ChangeCWD(CONTENT_REPO_EXAMPLE_ROOT):
            mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
            mocker.patch.object(TestPlaybookRunner, 'print_tpb_error_details')
            mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
            mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict',
                                return_value={"state": tpb_result})
            result = click.Context(command=run_test_playbook).invoke(run_test_playbook, all=True, test_playbook_path='')
            assert result == res

            stdout, _ = capsys.readouterr()
            assert stdout.count(massage) == 7

    @pytest.mark.parametrize(argnames='input_tpb, exit_code, err',
                             argvalues=[(VALID_PACK, 0, ''),
                                        (TEST_PLAYBOOK, 0, '')])
    def test_run_test_playbook_manager(self, mocker, input_tpb, exit_code, err, capsys):
        """
        Given:
            - arguments to the run-test-playbook
        When:
            - check that the run-test-playbook works as expected
        Then:
            - validate the error code is as expected.
            - validate the Error massage when the argument is missing
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'print_tpb_error_details')
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={'state': 'success'})

        self.test_playbook_input = input_tpb
        test_playbook = TestPlaybookRunner(test_playbook_path=self.test_playbook_input)
        error_code = test_playbook.manage_and_run_test_playbooks()
        assert error_code == exit_code

        stdout, _ = capsys.readouterr()
        if err:
            assert err in stdout

    @pytest.mark.parametrize(argnames='input_tpb, exit_code, err',
                             argvalues=[('', 1, "Error: Missing option '-tpb' / '--test-playbook-path'."),
                                        ('BlaBla', 1, 'Error: Given input path: BlaBla does not exist')])
    def test_failed_run_test_playbook_manager(self, mocker, input_tpb, exit_code, err, capsys):
        """
        Given:
            - arguments to the run-test-playbook
        When:
            - check that the run-test-playbook works as expected
        Then:
            - validate the error code is as expected.
            - validate the Error massage when the argument is missing
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={'state': 'success'})

        self.test_playbook_input = input_tpb
        test_playbook = TestPlaybookRunner(test_playbook_path=self.test_playbook_input)
        error_code = test_playbook.manage_and_run_test_playbooks()
        assert error_code == exit_code

        stdout, _ = capsys.readouterr()
        if err:
            assert err in stdout

    @pytest.mark.parametrize(argnames='playbook_id, tpb_results, exit_code',
                             argvalues=[(VALID_PACK, "success", 0),
                                        (TEST_PLAYBOOK, "success", 0)])
    def test_run_test_playbook_by_id(self, mocker, playbook_id, tpb_results, exit_code, capsys):
        """
        Given:
            - arguments to the xsoar-configuration-file
        When:
            - check that the run_test_playbook_by_id works as expected
        Then:
            - validate the error code is as expected.
            - validate all the massage is as expected.
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'print_tpb_error_details')
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={'state': tpb_results})

        self.test_playbook_input = TEST_PLAYBOOK
        test_playbook_runner = TestPlaybookRunner(test_playbook_path=self.test_playbook_input)
        res = test_playbook_runner.run_test_playbook_by_id(playbook_id)

        assert res == exit_code

        stdout, _ = capsys.readouterr()
        assert WAITING_MASSAGE in stdout
        assert LINK_MASSAGE in stdout
        assert SUCCESS_MASSAGE in stdout

    @pytest.mark.parametrize(argnames='playbook_id, tpb_results, exit_code',
                             argvalues=[('VALID_PACK', "failed", 1),
                                        ('TEST_PLAYBOOK', "failed", 1)])
    def test_failed_run_test_playbook_by_id(self, mocker, playbook_id, tpb_results, exit_code, capsys):
        """
        Given:
            - arguments to the xsoar-configuration-file
        When:
            - check that the run_test_playbook_by_id works as expected
        Then:
            - validate the error code is as expected.
            - validate the all the massages is as expected.
        """
        mocker.patch.object(demisto_client, 'configure', return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, 'print_tpb_error_details')
        mocker.patch.object(TestPlaybookRunner, 'create_incident_with_test_playbook', return_value='1234')
        mocker.patch.object(TestPlaybookRunner, 'get_test_playbook_results_dict', return_value={'state': tpb_results})

        self.test_playbook_input = TEST_PLAYBOOK
        test_playbook_runner = TestPlaybookRunner(test_playbook_path=self.test_playbook_input)
        res = test_playbook_runner.run_test_playbook_by_id(playbook_id)

        assert res == exit_code

        stdout, _ = capsys.readouterr()
        assert WAITING_MASSAGE in stdout
        assert LINK_MASSAGE in stdout
        assert FAILED_MASSAGE in stdout
