import io
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import coverage
import requests

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger

EXCLUDED_LINES = [
    "pragma: no cover",
    r"if __name__ in (\(|\[)[\W\w]+(\)|\]):",
    r"^\s*\"{3}([\s\S]*?)\"{3}",
    r"^\s*'{3}([\s\S]*?)'{3}",
]


def fix_file_path(coverage_file: str, code_file_absolute_path: str):
    """

    Args:
        coverage_file: the .coverage file this contains the coverage data in sqlite format.
        code_file_absolute_path: the real absolute path to the measured code file.

    Notes:
        the .coverage files contain all the files list with their absolute path.
        but our tests (pytest step) are running inside a docker container.
        so we have to change the path to the correct one.
    """
    with sqlite3.connect(coverage_file) as sql_connection:
        cursor = sql_connection.cursor()
        index = cursor.execute("SELECT count(*) FROM file").fetchall()[0][0]
        if not index == 1:
            logger.debug("unexpected file list in coverage report")
        else:
            cursor.execute(
                "UPDATE file SET path = ? WHERE id = ?", (code_file_absolute_path, 1)
            )
            sql_connection.commit()
        cursor.close()
    if not index == 1:
        logger.debug(f"removing coverage report for {code_file_absolute_path}")
        Path(coverage_file).unlink()


def get_coverage_obj(
    coverage_file: Optional[str],
    report_dir: Optional[str],
    load_old: bool = True,
    combine_from_content_repo: bool = False,
    precision: int = 2,
) -> coverage.Coverage:
    """
    Args:
        coverage_file(str): the coverage file path (the default is .coverage).
        report_dir(str): the directory where the reports files should be placed.
        load_old(bool): load the file (instead of overide).
        combine_from_content_repo(bool): load .coverage files from content repo.
        percision(int): digits after the decimal point (e.g. for percision=2 74.3586 -> 74.35)
    """
    coverage_obj = coverage.Coverage(config_file=False, auto_data=False)
    coverage_obj.set_option("report:precision", precision)
    coverage_obj.set_option("report:exclude_lines", EXCLUDED_LINES)

    if coverage_file:
        coverage_obj.set_option("run:data_file", coverage_file)
    if report_dir:
        coverage_obj.set_option("html:directory", os.path.join(report_dir, "html"))
        coverage_obj.set_option("xml:output", os.path.join(report_dir, "coverage.xml"))
        coverage_obj.set_option(
            "json:output", os.path.join(report_dir, "coverage.json")
        )
    if load_old:
        coverage_obj.load()
    if combine_from_content_repo:
        coverage_obj.combine(coverage_files())
    # uncomment the following for debug purposes
    # self._cov.set_option('json:pretty_print', True)

    return coverage_obj


def coverage_files() -> Iterable[str]:
    """
    iterate over the '.coverage' files in the repo.
    """
    packs_path = CONTENT_PATH / "Packs"
    for cov_path in packs_path.glob("*/Integrations/*/.coverage"):
        yield str(cov_path)
    for cov_path in packs_path.glob("*/Scripts/*/.coverage"):
        yield str(cov_path)


def get_report_str(coverage_obj) -> str:
    report_data = io.StringIO()
    coverage_obj.report(file=report_data)
    return report_data.getvalue()


def percent_to_float(percent: str) -> float:
    if percent.endswith("%"):
        percent = percent[:-1]
    return float(percent)


def parse_report_type(report_type_str: Optional[str]) -> List[str]:
    if report_type_str is None:
        return []

    allowed_types = ["text", "html", "xml", "json", "json-min"]
    if report_type_str == "all":
        return allowed_types

    report_types = report_type_str.split(",")

    for report_type in report_types:
        if report_type not in allowed_types:
            raise InvalidReportType(report_type)

    return report_types


class InvalidReportType(Exception):
    def __init__(self, invalid_report_type):
        self.invalid_report_type = invalid_report_type

    def __str__(self):
        if self.invalid_report_type == "all":
            return 'You may not use the "all" report type in addition to other report types.'
        return (
            f"{self.invalid_report_type} is not a valid report type. You can use the following report types as a "
            "comma separated value for the --report-type argument ('text', 'html', 'xml', 'json', 'json-min', 'all')."
        )


def export_report(report_call, format, dest):
    logger.info(f"exporting {format} coverage report to {dest}")
    try:
        report_call()
    except coverage.misc.CoverageException as warning:
        logger.warning(str(warning))


class CoverageSummary:
    def __init__(
        self,
        previous_coverage_report_url: str,
        cache_dir: Optional[str] = None,
        no_cache: bool = False,
    ):
        self.cache_dir = cache_dir
        self.url = previous_coverage_report_url
        self.use_cache = not no_cache

    @staticmethod
    def create(original_summary_path: str, min_summary_path: str):
        """
        Create a coverage-min.json file
        Args:
            original_summary_path(str): The path to the original coverage.json file.
            min_summary_path(str): The path to the coverage-min.json
        """
        with open(original_summary_path) as original_summary_file:
            original_summary = json.load(original_summary_file)

        min_summary_files = {}
        original_summary_files = original_summary["files"]
        for py_file_name, py_file_cov_data in original_summary_files.items():
            min_summary_files[py_file_name] = round(
                py_file_cov_data["summary"]["percent_covered"], 2
            )

        summary_time = original_summary["meta"]["timestamp"].split(".")[0]
        min_summary = {
            "files": min_summary_files,
            "last_updated": f"{summary_time}Z",
            "total_coverage": original_summary["totals"]["percent_covered"],
        }

        with open(min_summary_path, "w") as min_summary_file:
            json.dump(min_summary, min_summary_file)

    def get_files_summary(self) -> Dict[str, float]:
        """
        Getes the summary file
        based on the cache policy and the summary creation time.
        """
        json_path = (
            os.path.join(self.cache_dir, "coverage-min.json") if self.cache_dir else ""
        )
        if self.use_cache and self.cache_dir:
            try:
                with open(json_path) as coverage_summary_file:
                    full_coverage_summary = json.load(coverage_summary_file)
                last_updated = datetime.strptime(
                    full_coverage_summary["last_updated"], "%Y-%m-%dT%H:%M:%SZ"
                )
                next_update = last_updated + timedelta(days=1)
                if next_update > datetime.utcnow():
                    return full_coverage_summary["files"]
            except FileNotFoundError:
                logger.info(
                    "No cache file found. creatig a cache dir at %s", self.cache_dir
                )
                os.makedirs(self.cache_dir, exist_ok=True)
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.exception(exc)

        resp = requests.get(self.url)
        resp.raise_for_status()
        data = resp.json()
        if self.use_cache and self.cache_dir:
            with open(json_path, "w") as fp:
                json.dump(data, fp)

        return data["files"]
