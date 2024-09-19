"""
This file contains functions that are related to the coverage reports but not used in the demisto-sdk source.
"""

from datetime import datetime, timedelta
from typing import Optional

import requests

from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger

ONE_DAY = timedelta(days=1)
LATEST_URL = f"https://storage.googleapis.com/{DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV}/code-coverage-reports/coverage-min.json"
HISTORY_URL = "https://storage.googleapis.com/{DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV}/code-coverage-reports/history/coverage-min/{date}.json"


def get_total_coverage(
    filename: Optional[str] = None, date: Optional[datetime] = None
) -> float:
    """
    Args:
        filename:   The path to the coverage.json/coverage-min.json file.
        date:       A datetime object.
    Returns:
        A float representing the total coverage that was found.
            from file in case that filename was given.
            from history bucket in case that date was given.
            from latest bucket in any other case.
        Or
            0.0 if any errors were encountered.
    """
    coverage_field = "total_coverage"
    assert not (filename and date), "Provide either a filename or a date, not both."
    try:
        if filename:
            with open(filename) as report_file:
                result = json.load(report_file)
            try:
                return result[coverage_field]
            except KeyError:
                return result["totals"]["percent_covered"]
        elif date is None:
            url = LATEST_URL
        else:
            url = HISTORY_URL.format(
                DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV=DEMISTO_SDK_MARKETPLACE_XSOAR_DIST_DEV,
                date=date.strftime("%Y-%m-%d"),
            )

        res = requests.get(url)
        res.raise_for_status()
        return res.json()[coverage_field]
    except Exception as error:
        logger.info(error)
        return 0.0


def yield_dates(start_date: datetime, end_date: datetime):
    temp_time = start_date
    while temp_time <= end_date:
        yield temp_time
        temp_time += ONE_DAY


def create_coverage_graph(start_date: datetime, filename: str):
    """
    Args:
        start_date: The date to start collecting coverage information.
        filename:   The path to the png file containing the coverage graph.
    Creates:
        A graph of the coverage information per day.
    Note:
        This function uses the `matplotlib` package, but it is not an sdk requirement please make sure that it is installed.
    """
    cover_list = []
    date_list = []
    for date in yield_dates(start_date, datetime.now()):
        cover = get_total_coverage(date=date)
        if cover:
            cover_list.append(cover)
            date_list.append(date)

    x, y = cover_list, date_list
    import matplotlib.pyplot as plt

    plt.plot(x, y)
    plt.xlabel(f"current coverage: {y[-1]}")
    plt.savefig(fname=filename)
