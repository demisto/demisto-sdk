import os
from datetime import datetime

import pytest

from demisto_sdk.commands.coverage_analyze.tests.helpers_test import (
    JSON_MIN_DATA_FILE,
    TEST_DATA_DIR,
    read_file,
)
from demisto_sdk.commands.coverage_analyze.tools import (
    HISTORY_URL,
    LATEST_URL,
    get_total_coverage,
)


class TestGetTotalCoverage:
    def test_get_total_coverage_from_json_min_file(self):
        assert get_total_coverage(filename=JSON_MIN_DATA_FILE) == 52.38326848249027

    def test_get_total_coverage_from_json_file(self):
        assert (
            get_total_coverage(filename=os.path.join(TEST_DATA_DIR, "coverage.json"))
            == 52.38326848249027
        )

    def test_get_total_coverage_from_latest_url(self, requests_mock):
        requests_mock.get(LATEST_URL, json=read_file(JSON_MIN_DATA_FILE))
        assert get_total_coverage() == 52.38326848249027

    def test_get_total_coverage_from_history_url(self, requests_mock):
        date = datetime.now()
        requests_mock.get(
            HISTORY_URL.format(date=date.strftime("%Y-%m-%d")),
            json=read_file(JSON_MIN_DATA_FILE),
        )
        assert get_total_coverage(date=date) == 52.38326848249027

    def test_get_total_coverage_assert(self):
        with pytest.raises(AssertionError):
            get_total_coverage(filename=JSON_MIN_DATA_FILE, date=datetime.now())
