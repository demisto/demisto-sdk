# STD python packages
import logging
import time
from collections import defaultdict, namedtuple
from dataclasses import astuple, dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Dict, Optional, Sequence

# Third party packages
from tabulate import tabulate

# Local packages
from demisto_sdk.commands.common.logger import Colors

logger = logging.getLogger("demisto-sdk")

StatInfo = namedtuple("StatInfo", ["total_time", "call_count", "avg_time"])

registered_timers: dict = defaultdict(set)

packs: dict = {}


class MeasureType(Enum):
    FUNCTIONS = "functions"
    PACKS = "packs"


MEASURE_TYPE_TO_HEADERS: Dict[MeasureType, Sequence[str]] = {
    MeasureType.FUNCTIONS: ["Function", "Avg", "Total", "Call count"],
    MeasureType.PACKS: ["Pack", "Start Time", "End Time", "Total Time"],
}


class PackStatInfoException(Exception):
    pass


@dataclass()
class PackStatInfo:
    start_time: str
    end_time: Optional[str] = None
    total_time: Optional[str] = None

    def __iter__(self):
        return iter(astuple(self))

    def __lt__(self, other):
        if not isinstance(other, PackStatInfo):
            raise PackStatInfoException(
                f"Cannot compare `PackStatInfo` with `{type(other)}"
            )
        if self.total_time is None or other.total_time is None:
            # If the pack didn't finish, we don't really care about their order
            return True
        return float(self.total_time) < float(other.total_time)


def timer(group_name="Common"):
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
            if group_name == "lint":
                pack_name, run_count = start_measure_pack(args)
            tic = time.perf_counter()
            value = func(*args, **kwargs)
            toc = time.perf_counter()

            elapsed_time = toc - tic

            total_time += elapsed_time
            call_count += 1

            if group_name == "lint":
                end_measure_pack(pack_name, run_count, elapsed_time)
            return value

        def start_measure_pack(args):
            """
            start measuring the time of the pack
            Args:
                args: the args to the function

            Returns:
                The pack name and the time that this function run in the pack

            """
            pack_name = args[0]._pack_name
            # __qualname__ is the function full name
            if func.__qualname__ not in packs:
                packs[func.__qualname__] = {}
            if pack_name not in packs[func.__qualname__]:
                packs[func.__qualname__][pack_name] = []
            run_count = len(packs[func.__qualname__][pack_name])
            packs[func.__qualname__][pack_name].append(
                PackStatInfo(start_time=datetime.now().isoformat())
            )
            return pack_name, run_count

        def end_measure_pack(pack_name, run_count, elapsed_time):
            # __qualname__ is the function full name
            packs[func.__qualname__][pack_name][
                run_count
            ].end_time = datetime.now().isoformat()
            packs[func.__qualname__][pack_name][
                run_count
            ].total_time = f"{elapsed_time:0.4f}"

        def stat_info():
            return StatInfo(
                total_time,
                call_count,
                total_time / call_count if call_count != 0 else 0,
            )

        wrapper_timer.stat_info = stat_info  # type: ignore[attr-defined]

        registered_timers[group_name].add(wrapper_timer)
        return wrapper_timer

    return group_timer


def report_time_measurements(
    group_name="Common", time_measurements_dir="time_measurements"
):
    """
    Report the time measurements

    Arg:
        group_name(str): the name of te timers group to be reported
        time_measurements_dir(str): directory for the time measurements report file
    """
    if group_name == "lint":
        for func_name, data in packs.items():
            data = {
                k: v
                for k, v in sorted(data.items(), key=lambda x: max(x[1]), reverse=True)
            }
            data = [(k, *v1) for k, v in data.items() for v1 in v]

            if "run_pack" in func_name:  # don't spam stdout too much
                write_measure_to_logger(func_name, data, MeasureType.PACKS, debug=False)
            else:
                write_measure_to_logger(func_name, data, MeasureType.PACKS, debug=True)
            write_measure_to_file(
                time_measurements_dir, func_name, data, measure_type=MeasureType.PACKS
            )
    timers = registered_timers.get(group_name)
    if timers:

        method_states = [
            [
                func.__qualname__,
                f"{func.stat_info().avg_time:0.4f}",
                f"{func.stat_info().total_time:0.4f}",
                f"{func.stat_info().call_count}",
            ]
            for func in timers
        ]

        # sort by the total time
        list.sort(
            method_states, key=lambda method_stat: float(method_stat[2]), reverse=True
        )

        write_measure_to_logger(group_name, csv_data=method_states)
        write_measure_to_file(
            time_measurements_dir=time_measurements_dir,
            name=group_name,
            csv_data=method_states,
        )

    else:
        logger.debug(f"There is no timers registered for the group {group_name}")


def write_measure_to_logger(
    name: str,
    csv_data,
    measure_type: MeasureType = MeasureType.FUNCTIONS,
    debug: bool = False,
):
    """

    Args:
        debug: if write to debug
        name: name of the table
        csv_data: the data
        measure_type: The measure type (default is functions)

    Returns:

    """
    sentence = f"Time measurements stat for {name}"
    output_msg = (
        f"\n{Colors.Fg.cyan}{'#' * len(sentence)}\n"
        f"{sentence}\n"
        f"{'#' * len(sentence)}\n{Colors.reset}"
    )
    stat_info_table = tabulate(csv_data, headers=MEASURE_TYPE_TO_HEADERS[measure_type])
    output_msg += stat_info_table
    if debug:
        logger.debug(output_msg)
    else:
        logger.info(output_msg)


def write_measure_to_file(
    time_measurements_dir,
    name,
    csv_data,
    measure_type: MeasureType = MeasureType.FUNCTIONS,
):
    """

    Args:
        time_measurements_dir: Directory to save the data
        name: name of the table
        csv_data: the data
        measure_type: The measure type (default is functions)

    Returns:

    """
    try:
        time_measurements_path = Path(time_measurements_dir)
        if not time_measurements_path.exists():
            time_measurements_path.mkdir(parents=True)
        with open(
            time_measurements_path / f"{name}_time_measurements.csv", "w+"
        ) as file:
            # if we construct packs measurement we will use PACK_CSV_HEADERS
            file.write(",".join(MEASURE_TYPE_TO_HEADERS[measure_type]))
            for stat in csv_data:
                file.write(f"\n{','.join(stat)}")
    except Exception as e:
        logger.error(f"can't write time measure to file {e}")
