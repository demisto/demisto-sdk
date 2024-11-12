import demisto_client
import pytest
import typer
from demisto_client.demisto_api import DefaultApi
from typer.testing import CliRunner

from demisto_sdk.__main__ import app
from demisto_sdk.commands.run_test_playbook.test_playbook_runner import (
    TestPlaybookRunner,
)
from demisto_sdk.tests.constants_test import (
    CONTENT_REPO_EXAMPLE_ROOT,
    TEST_PLAYBOOK,
    VALID_PACK,
)
from TestSuite.test_tools import ChangeCWD

WAITING_MESSAGE = "Waiting for the test playbook to finish running.."
LINK_MESSAGE = "To see the test playbook run in real-time please go to :"
SUCCESS_MESSAGE = "The test playbook has completed its run successfully"
FAILED_MESSAGE = "The test playbook finished running with status: FAILED"


class TestTestPlaybookRunner:
    @pytest.mark.parametrize(
        argnames="tpb_result, res",
        argvalues=[("failed", 1), ("success", 0)],
    )
    def test_run_specific_test_playbook(self, mocker, tpb_result, res):
        """
        Given:
            - run specific test playbook with result as True or False
        When:
            - run the run_test_playbook command
        Then:
            - validate the results is as expected
        """
        mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, "print_tpb_error_details")
        mocker.patch.object(TestPlaybookRunner, "upload_tpb")
        mocker.patch.object(
            TestPlaybookRunner,
            "create_incident_with_test_playbook",
            return_value="1234",
        )
        mocker.patch.object(
            TestPlaybookRunner,
            "get_test_playbook_results_dict",
            return_value={"state": tpb_result},
        )
        runner = CliRunner()

        # Use pytest.raises to catch the Exit exception
        result = runner.invoke(
            app, args=["run-test-playbook", "--test-playbook-path", TEST_PLAYBOOK]
        )

        # Assert the exit code is as expected
        assert result.exit_code == res

    @pytest.mark.parametrize(
        argnames="tpb_result, res, message",
        argvalues=[("failed", 1, FAILED_MESSAGE), ("success", 0, SUCCESS_MESSAGE)],
    )
    def test_run_pack_test_playbooks(self, mocker, tpb_result, res, message):
        """
        Given:
            - run all pack test playbooks with result as True or False
        When:
            - run the run_test_playbook command
        Then:
            - validate the results is as expected
            - validate the num of tpb is as expected (4 tpb in Azure Pack)
        """

        mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, "print_tpb_error_details")
        mocker.patch.object(TestPlaybookRunner, "upload_tpb")
        mocker.patch.object(
            TestPlaybookRunner,
            "create_incident_with_test_playbook",
            return_value="1234",
        )
        mocker.patch.object(
            TestPlaybookRunner,
            "get_test_playbook_results_dict",
            return_value={"state": tpb_result},
        )
        runner = CliRunner()

        result = runner.invoke(
            app,
            args=["run-test-playbook", "--test-playbook-path", TEST_PLAYBOOK],
            catch_exceptions=False,
        )
        # Assert the exit code is as expected
        assert result.exit_code == res
        assert message in result.output

    @pytest.mark.parametrize(
        argnames="tpb_result, expected_exit_code, message",
        argvalues=[
            ("failed", 1, FAILED_MESSAGE),
            ("success", 0, SUCCESS_MESSAGE),
        ],
    )
    def test_run_repo_test_playbooks(
        self, mocker, tpb_result: str, expected_exit_code: int, message: str
    ):
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
            mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
            mocker.patch.object(TestPlaybookRunner, "print_tpb_error_details")
            mocker.patch.object(TestPlaybookRunner, "upload_tpb")
            mocker.patch.object(
                TestPlaybookRunner,
                "create_incident_with_test_playbook",
                return_value="1234",
            )
            mocker.patch.object(
                TestPlaybookRunner,
                "get_test_playbook_results_dict",
                return_value={"state": tpb_result},
            )
            result = CliRunner(mix_stderr=False).invoke(
                app, ["run-test-playbook", "--all", "-tpb", "", "-t", "5"]
            )
            assert result.exit_code == expected_exit_code
            assert message in result.output

    @pytest.mark.parametrize(
        argnames="input_tpb, exit_code, err",
        argvalues=[(VALID_PACK, 0, ""), (TEST_PLAYBOOK, 0, "")],
    )
    def test_run_test_playbook_manager(self, mocker, input_tpb, exit_code, err, capsys):
        """
        Given:
            - arguments to the run-test-playbook
        When:
            - check that the run-test-playbook works as expected
        Then:
            - validate the error code is as expected.
            - validate the Error message when the argument is missing
        """
        mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, "print_tpb_error_details")
        mocker.patch.object(TestPlaybookRunner, "upload_tpb")

        mocker.patch.object(
            TestPlaybookRunner,
            "create_incident_with_test_playbook",
            return_value="1234",
        )
        mocker.patch.object(
            TestPlaybookRunner,
            "get_test_playbook_results_dict",
            return_value={"state": "success"},
        )

        self.test_playbook_input = input_tpb
        test_playbook = TestPlaybookRunner(test_playbook_path=self.test_playbook_input)
        # Use pytest.raises to capture typer.Exit
        with pytest.raises(typer.Exit) as exc_info:
            test_playbook.manage_and_run_test_playbooks()

        # Check the exit code from typer.Exit
        assert exc_info.value.exit_code == exit_code

        # Capture the output and verify if needed
        stdout, _ = capsys.readouterr()
        if err:
            assert err in stdout

    @pytest.mark.parametrize(
        argnames="input_tpb, exit_code, err",
        argvalues=[
            ("", 1, "Missing option '-tpb' / '--test-playbook-path'."),
            ("BlaBla", 1, "Given input path: BlaBla does not exist"),
        ],
    )
    def test_failed_run_test_playbook_manager(
        self, mocker, input_tpb, exit_code, err, caplog
    ):
        """
        Given:
            - arguments to the run-test-playbook
        When:
            - check that the run-test-playbook works as expected
        Then:
            - validate the error code is as expected.
            - validate the Error message when the argument is missing
        """

        mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
        mocker.patch.object(
            TestPlaybookRunner,
            "create_incident_with_test_playbook",
            return_value="1234",
        )
        mocker.patch.object(
            TestPlaybookRunner,
            "get_test_playbook_results_dict",
            return_value={"state": "success"},
        )

        self.test_playbook_input = input_tpb
        test_playbook = TestPlaybookRunner(test_playbook_path=self.test_playbook_input)
        # Use pytest.raises to capture typer.Exit
        with pytest.raises(typer.Exit) as exc_info:
            test_playbook.manage_and_run_test_playbooks()

        # Check the exit code from typer.Exit
        assert exc_info.value.exit_code == exit_code

        # Capture the output and verify if needed
        if err:
            assert err in caplog.text

    @pytest.mark.parametrize(
        argnames="playbook_id, tpb_results, exit_code",
        argvalues=[(VALID_PACK, "success", 0), (TEST_PLAYBOOK, "success", 0)],
    )
    def test_run_test_playbook_by_id(
        self, mocker, playbook_id, tpb_results, exit_code, caplog
    ):
        """
        Given:
            - arguments to the xsoar-configuration-file
        When:
            - check that the run_test_playbook_by_id works as expected
        Then:
            - validate the error code is as expected.
            - validate all the message is as expected.
        """

        mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, "print_tpb_error_details")
        mocker.patch.object(TestPlaybookRunner, "upload_tpb")

        mocker.patch.object(
            TestPlaybookRunner,
            "create_incident_with_test_playbook",
            return_value="1234",
        )
        mocker.patch.object(
            TestPlaybookRunner,
            "get_test_playbook_results_dict",
            return_value={"state": tpb_results},
        )

        self.test_playbook_input = TEST_PLAYBOOK
        test_playbook_runner = TestPlaybookRunner(
            test_playbook_path=self.test_playbook_input
        )
        with pytest.raises(typer.Exit) as exc_info:
            test_playbook_runner.run_test_playbook_by_id(playbook_id)

        assert exc_info.value.exit_code == exit_code
        assert WAITING_MESSAGE in caplog.text
        assert LINK_MESSAGE in caplog.text
        assert SUCCESS_MESSAGE in caplog.text

    @pytest.mark.parametrize(
        argnames="playbook_id, tpb_results, exit_code",
        argvalues=[("VALID_PACK", "failed", 1), ("TEST_PLAYBOOK", "failed", 1)],
    )
    def test_failed_run_test_playbook_by_id(
        self, mocker, playbook_id, tpb_results, exit_code, caplog
    ):
        """
        Given:
            - arguments to the xsoar-configuration-file
        When:
            - check that the run_test_playbook_by_id works as expected
        Then:
            - validate the error code is as expected.
            - validate the all the messages is as expected.
        """

        mocker.patch.object(demisto_client, "configure", return_value=DefaultApi())
        mocker.patch.object(TestPlaybookRunner, "print_tpb_error_details")
        mocker.patch.object(TestPlaybookRunner, "upload_tpb")

        mocker.patch.object(
            TestPlaybookRunner,
            "create_incident_with_test_playbook",
            return_value="1234",
        )
        mocker.patch.object(
            TestPlaybookRunner,
            "get_test_playbook_results_dict",
            return_value={"state": tpb_results},
        )
        test_playbook_runner = TestPlaybookRunner(test_playbook_path=TEST_PLAYBOOK)
        with pytest.raises(typer.Exit) as exc_info:
            test_playbook_runner.run_test_playbook_by_id(playbook_id)

        assert exc_info.value.exit_code == exit_code
        assert WAITING_MESSAGE in caplog.text
        assert LINK_MESSAGE in caplog.text
        assert FAILED_MESSAGE in caplog.text
