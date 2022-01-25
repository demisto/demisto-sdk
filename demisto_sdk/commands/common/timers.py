# STD python packages
import time
from collections import namedtuple
from contextlib import contextmanager
from functools import wraps

# Third party packages
from tabulate import tabulate

# Local packages
from demisto_sdk.commands.common.logger import Colors

# from typing import Dict, List


class TimeMeasureMgr:
    """
    Class to orgenaize the `timer` decorator and `time measurements reporter` usnage.
    when using the `timer` decorator it will register the wrapped function to be reported by `time measurements reporter`

    """
    StatInfo = namedtuple("StatInfo", ["total_time", "call_count", "avg_time"])

    registered_timers: dict = {}

    @staticmethod
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
                return TimeMeasureMgr.StatInfo(total_time, call_count, total_time / call_count if call_count != 0 else 0)

            wrapper_timer.stat_info = stat_info  # type: ignore[attr-defined]

            if group_name not in TimeMeasureMgr.registered_timers:
                TimeMeasureMgr.registered_timers[group_name] = set()

            TimeMeasureMgr.registered_timers[group_name].add(wrapper_timer)
            return wrapper_timer

        return group_timer

    @staticmethod
    @contextmanager
    def time_measurements_reporter(group_name='Common'):
        """
        Context manager for reporting time measurements

        Arg:
            group_name(str): the name of te timers group to be reported
        """
        try:
            yield
        finally:

            sentence = " Time measurements stat "
            print(f"\n{Colors.Fg.cyan}{'#' * len(sentence)}")
            print(f"{sentence}")
            print(f"{'#' * len(sentence)}{Colors.reset}")

            timers = TimeMeasureMgr.registered_timers.get(group_name)
            if timers:

                headers = ['Function', 'Avg', 'Total', 'Call count']
                timers = TimeMeasureMgr.registered_timers[group_name]
                method_states = [[func.__qualname__, func.stat_info().avg_time, func.stat_info().total_time,
                                  func.stat_info().call_count]
                                 for func in timers]
                list.sort(method_states, key=lambda method_stat: method_stat[2], reverse=True)
                stat_info_table = tabulate(method_states, headers=headers)
                print(stat_info_table)
            else:
                print(f'There is no timers registered for the group {group_name}')
