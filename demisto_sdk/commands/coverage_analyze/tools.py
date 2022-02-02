import json
from datetime import datetime, timedelta
from typing import Optional

import requests

from demisto_sdk.commands.common.logger import logging_setup

ONE_DAY = timedelta(days=1)
IMAGE_URL = 'https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/coverage-graph.png'
LATEST_URL = 'https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/coverage-min.json'
HISTORY_URL = 'https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/history/coverage-min/{date}.json'


logger = logging_setup(2)


def get_coverage(date: Optional[datetime] = None, filename: Optional[str] = None) -> Optional[float]:
    coverage_field = 'total_coverage'
    try:
        if filename:
            with open(filename, 'r') as report_file:
                result = json.load(report_file)
            try:
                return result[coverage_field]
            except KeyError:
                return result['totals']['percent_covered']
        elif date is None:
            url = LATEST_URL
        else:
            url = HISTORY_URL.format(date=date.strftime('%Y-%m-%d'))

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


def create_coverage_graph(filename: str, start_date: datetime):
    cover_list = []
    date_list = []
    for date in yield_dates(start_date, datetime.now()):
        cover = get_coverage(date=date)
        if cover:
            cover_list.append(cover)
            date_list.append(date)

    x, y = cover_list, date_list
    import matplotlib.pyplot as plt
    plt.plot(x, y)
    plt.xlabel(f'current coverage: {y[-1]}')
    plt.savefig(fname=filename)
