import tempfile
from pathlib import Path

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.timers import (
    MEASURE_TYPE_TO_HEADERS,
    MeasureType,
    report_time_measurements,
    timer,
)


def test_timers__happy_path(mocker):
    """
    Given -
        method to measure it's run time
    When -
        running this method
    Then -
        verify the output as expected and the csv file output was created
    """
    mocker.patch.object(logger, "info")

    @timer(group_name="test_group")
    def some_func():
        pass

    # call some method with timer decorator
    some_func()
    some_func()

    with tempfile.TemporaryDirectory() as dir:
        report_time_measurements(
            group_name="test_group", time_measurements_dir=str(dir)
        )
        assert some_func.stat_info().call_count == 2
        assert all(
            header in logger.info.call_args[0][0]
            for header in MEASURE_TYPE_TO_HEADERS[MeasureType.FUNCTIONS]
        )
        assert (Path(dir) / "test_group_time_measurements.csv").exists()


def test_timers__no_group_exist(mocker):
    """
    Given -
        time_measurements_reporter to report for non existing group
    When -
        running this method
    Then -
        verify the output as expected
    """

    mocker.patch.object(logger, "debug")
    mocker.patch("demisto_sdk.commands.common.timers.write_measure_to_file")

    @timer(group_name="test_group")
    def some_func():
        pass

    # call some method with timer decorator
    not_exist_group = "not_exist_group"
    some_func()
    report_time_measurements(not_exist_group)

    assert some_func.stat_info().call_count == 1
    assert (
        f"There is no timers registered for the group {not_exist_group}"
        in logger.debug.call_args[0][0]
    )
