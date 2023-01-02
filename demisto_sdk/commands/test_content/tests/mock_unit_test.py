import time
from threading import Thread

from demisto_sdk.commands.test_content.mock_server import (
    MITMProxy,
    clean_filename,
    get_folder_path,
    get_log_file_path,
    get_mock_file_path,
)


def test_clean_filename():
    assert (
        clean_filename("th)))i(s) is a (test8)8   8") == "th___i_s__is_a__test8_8___8"
    )
    assert clean_filename("n&%ew $r#eplac@es", replace="&%$#@") == "n__ew _r_eplac_es"


def test_get_paths():
    test_playbook_id = "test_playbook"
    assert get_mock_file_path(test_playbook_id) == "test_playbook/test_playbook.mock"
    assert (
        get_log_file_path(test_playbook_id)
        == "test_playbook/test_playbook_playback.log"
    )
    assert (
        get_log_file_path(test_playbook_id, record=True)
        == "test_playbook/test_playbook_record.log"
    )
    assert get_folder_path(test_playbook_id) == "test_playbook/"


def test_push_mock_files_thread_safety(mocker):
    """
    Given:
        - A proxy instance
    When:
        - Mocking the subprocess's 'check_output' command with a method that increments a counter with 1
        and running the 'push_mock_files' with 5 threads at the same time.
    Then:
        - Ensure thread safety is achieved and that the counter equals 5 at the end of the test
        - Ensure that each thread has entered the 'increment_counter' method alone
    """

    class Counter:
        counter = 0
        modifying_dates = []

    def increment_counter(*_, **__):
        time.sleep(2)
        Counter.counter += 1
        Counter.modifying_dates.append(time.time())
        return

    # Mocking
    mocker.patch.object(MITMProxy, "__init__", lambda *args, **kwargs: None)
    proxy_instance = MITMProxy(
        "public_ip", "logging_module", "build_number", "branch_name"
    )
    # Replacing the ami instance with MagicMock instance so that the check_output command will be mocked as well
    proxy_instance.ami = mocker.MagicMock()
    proxy_instance.logging_module = mocker.MagicMock()
    proxy_instance.counter = 0
    proxy_instance.ami.check_output = increment_counter

    # Creating 10 threads that will push together
    threads = []
    for i in range(5):
        threads.append(Thread(target=proxy_instance.push_mock_files))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert Counter.counter == 5
    for i in range(4):
        assert Counter.modifying_dates[i] < Counter.modifying_dates[i + 1]
        assert Counter.modifying_dates[i + 1] - Counter.modifying_dates[i] > 1
