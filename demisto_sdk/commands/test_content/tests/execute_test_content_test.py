from queue import Queue

from demisto_sdk.commands.test_content.execute_test_content import \
    execute_test_content


class MockTestResults:
    playbook_skipped_integration = set()
    failed_playbooks = False

    @staticmethod
    def print_test_summary(is_ami, logging_module):
        return

    @staticmethod
    def create_result_files():
        return


class MockBuildContext:
    build_number = 123456
    instances_ips = {}
    unmockable_tests_to_run = Queue()
    mockable_tests_to_run = Queue()
    build_name = 'mock'
    is_nightly = False
    tests_data_keeper = MockTestResults
    isAMI = False


def test_execute_test_content(mocker):
    mocker.patch('demisto_sdk.commands.test_content.execute_test_content.BuildContext', return_value=MockBuildContext)

    execute_test_content(nightly=False)

    assert True
