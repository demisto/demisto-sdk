from unittest.mock import patch

from demisto_sdk.commands.common.timers import TimeMeasureMgr


@patch('builtins.print')
def test_timers__happy_path(mock_print):
    """
    Given -
        method to measure it's run time
    When -
        running this method
    Then -
        verify the output as expected
    """
    @TimeMeasureMgr.timer(group_name='test_group')
    def some_func():
        pass

    # call some method with timer decorator
    with TimeMeasureMgr.time_measurements_reporter(group_name='test_group'):
        some_func()
        some_func()

    assert some_func.stat_info().call_count == 2

    headers = ['Function', 'Avg', 'Total', 'Call count']
    assert all(header in mock_print.call_args[0][0] for header in headers)


@patch('builtins.print')
def test_timers__no_group_exist(mock_print):
    """
    Given -
        time_measurements_reporter to report for non existing group
    When -
        running this method
    Then -
        verify the output as expected
    """
    @TimeMeasureMgr.timer(group_name='test_group')
    def some_func():
        pass

    # call some method with timer decorator
    not_exist_group = 'not_exist_group'
    with TimeMeasureMgr.time_measurements_reporter(group_name='not_exist_group'):
        some_func()

    assert some_func.stat_info().call_count == 1
    assert f'There is no timers registered for the group {not_exist_group}' in mock_print.call_args[0][0]
