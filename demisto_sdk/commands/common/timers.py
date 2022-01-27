# STD python packages
import logging
import time
from collections import defaultdict, namedtuple
from functools import wraps
from pathlib import Path

# Third party packages
from tabulate import tabulate

# Local packages
from demisto_sdk.commands.common.logger import Colors

logger = logging.getLogger('demisto-sdk')

CSV_HEADERS = ['Function', 'Avg', 'Total', 'Call count']

StatInfo = namedtuple("StatInfo", ["total_time", "call_count", "avg_time"])

registered_timers: dict = defaultdict(set)


def timer(group_name='Common'):
    """
    Decorate the functions using this decorator for time measurement

    Arg:
        group_name(str): the timers group name this timer will add to (individual group for each command)
    """
    def group_timer(func):
        total_time = 0.0
        call_count = 0

        @wraps(func)
        def wrapper_timer(*args, **kwargs):
            nonlocal total_time, call_count

            tic = time.perf_counter()
            value = func(*args, **kwargs)
            toc = time.perf_counter()

            elapsed_time = toc - tic

            total_time += elapsed_time
            call_count += 1

            return value

        def stat_info():
            return StatInfo(total_time, call_count, total_time / call_count if call_count != 0 else 0)

        wrapper_timer.stat_info = stat_info  # type: ignore[attr-defined]

        registered_timers[group_name].add(wrapper_timer)
        return wrapper_timer

    return group_timer


def report_time_measurements(group_name='Common', time_measurements_dir='time_measurements'):
    """
    Report the time measurements

    Arg:
        group_name(str): the name of te timers group to be reported
        time_measurements_dir(str): directory for the time measurements report file
    """

    timers = registered_timers.get(group_name)
    if timers:

        method_states = [
            [
                func.__qualname__,
                f'{func.stat_info().avg_time:0.4f}',
                f'{func.stat_info().total_time:0.4f}',
                f'{func.stat_info().call_count}',
            ]
            for func in timers]

        # sort by the total time
        list.sort(method_states, key=lambda method_stat: float(method_stat[2]), reverse=True)

        write_mesure_to_logger(csv_data=method_states)
        write_measure_to_file(time_measurements_dir=time_measurements_dir, group_name=group_name, csv_data=method_states)

    else:
        logger.debug(f'There is no timers registered for the group {group_name}')


def write_mesure_to_logger(csv_data):

    sentence = 'Time measurements stat'
    output_msg = f"\n{Colors.Fg.cyan}{'#' * len(sentence)}\n"\
        f"{sentence}\n"\
        f"{'#' * len(sentence)}\n{Colors.reset}"

    stat_info_table = tabulate(csv_data, headers=CSV_HEADERS)
    output_msg += stat_info_table
    logger.info(output_msg)


def write_measure_to_file(time_measurements_dir, group_name, csv_data):

    try:
        time_measurements_path = Path(time_measurements_dir)
        if not time_measurements_path.exists():
            time_measurements_path.mkdir(parents=True)
        with open(time_measurements_path / f'{group_name}_time_measurements.csv', 'w+') as file:
            file.write(','.join(CSV_HEADERS))
            for stat in csv_data:
                file.write(f"\n{','.join(stat)}")
    except Exception as e:
        logger.error(f"can't write time measure to file {e}")
