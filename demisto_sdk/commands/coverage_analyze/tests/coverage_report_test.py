import logging
import os
import re
from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import (
    TEST_COVERAGE_DEFAULT_URL as DEFAULT_URL,
)
from demisto_sdk.commands.coverage_analyze.coverage_report import CoverageReport
from demisto_sdk.commands.coverage_analyze.helpers import (
    fix_file_path,
    get_coverage_obj,
)
from demisto_sdk.commands.coverage_analyze.tests.helpers_test import (
    COVERAGE_FILES_DIR,
    JSON_MIN_DATA_FILE,
    PYTHON_FILE_PATH,
    TEST_DATA_DIR,
    copy_file,
    read_file,
)
from TestSuite.test_tools import flatten_call_args

REPORT_STR_FILE = os.path.join(TEST_DATA_DIR, "coverage.txt")


class TestCoverageReport:
    @staticmethod
    def patern(r_type, file_name, suffix):
        return (
            rf"^exporting {r_type} coverage report to [\w\-\./]+/{file_name}\.{suffix}$"
        )

    def test_fail_without_coverage_file(self, monkeypatch, tmpdir):
        """
        Given:
            - no .coverage file is given or exists.
        When:
            - Running demisto-sdk coverage-analyze.
        Then:
            - Make sure that there is an exception to file not found and a warning was added to the logger.
        """
        monkeypatch.chdir(tmpdir)
        cov_report = CoverageReport()
        try:
            cov_report.coverage_report()
        except FileNotFoundError as e:
            assert str(e) == "The coverage file does not exist."

    def test_with_print_report(self, tmpdir, monkeypatch, mocker):
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

        monkeypatch.chdir(tmpdir)

        coverage_path = os.path.join(
            COVERAGE_FILES_DIR, "HealthCheckAnalyzeLargeInvestigations"
        )
        temp_cover_file = tmpdir.join(".coverage")
        copy_file(coverage_path, temp_cover_file)

        cov_report = CoverageReport(
            report_dir=str(tmpdir),
            report_type="html,json,xml",
            coverage_file=temp_cover_file,
            no_cache=True,
        )
        cov_report._report_str = Path(REPORT_STR_FILE).read_text()
        cov_report.coverage_report()
        assert (
            f"\n{Path(REPORT_STR_FILE).read_text()}"
            in flatten_call_args(logger_info.call_args_list)[0]
        )

    def test_with_export_report_function(self, tmpdir, monkeypatch, mocker):
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        monkeypatch.chdir(tmpdir)
        coverage_path = os.path.join(
            COVERAGE_FILES_DIR, "HealthCheckAnalyzeLargeInvestigations"
        )
        temp_cover_file = tmpdir.join(".coverage")
        copy_file(coverage_path, temp_cover_file)
        fix_file_path(temp_cover_file, PYTHON_FILE_PATH)
        cov_report = CoverageReport(
            report_dir=str(tmpdir),
            report_type="html,json,xml",
            coverage_file=temp_cover_file,
            no_cache=True,
        )
        cov_report.coverage_report()
        logger_args = flatten_call_args(logger_info.call_args_list)
        assert re.fullmatch(
            self.patern("html", "html/index", "html"),
            logger_args[1],
        )
        assert re.fullmatch(self.patern("xml", "coverage", "xml"), logger_args[2])
        assert re.fullmatch(self.patern("json", "coverage", "json"), logger_args[3])
        assert len(logger_args) == 4

    def test_with_txt_report(self, tmpdir, monkeypatch, caplog):
        monkeypatch.chdir(tmpdir)
        coverage_path = os.path.join(
            COVERAGE_FILES_DIR, "HealthCheckAnalyzeLargeInvestigations"
        )
        temp_cover_file = tmpdir.join(".coverage")
        copy_file(coverage_path, temp_cover_file)
        fix_file_path(temp_cover_file, PYTHON_FILE_PATH)
        cov_report = CoverageReport(
            report_dir=str(tmpdir),
            report_type="text",
            coverage_file=temp_cover_file,
            no_cache=True,
        )
        with caplog.at_level(logging.INFO, logger="demisto-sdk"):
            cov_report.coverage_report()
        # assert re.fullmatch(self.patern('txt', 'coverage', 'txt'), caplog.records[1].msg)
        assert Path(tmpdir.join("coverage.txt")).exists()

    def test_with_json_min_report(self, tmpdir, monkeypatch, caplog):
        monkeypatch.chdir(tmpdir)
        coverage_path = os.path.join(
            COVERAGE_FILES_DIR, "HealthCheckAnalyzeLargeInvestigations"
        )
        temp_cover_file = tmpdir.join(".coverage")
        copy_file(coverage_path, temp_cover_file)
        fix_file_path(temp_cover_file, PYTHON_FILE_PATH)
        cov_report = CoverageReport(
            report_dir=str(tmpdir),
            report_type="json,json-min",
            coverage_file=temp_cover_file,
        )
        with caplog.at_level(logging.INFO, logger="demisto-sdk"):
            cov_report.coverage_report()
        # assert re.fullmatch(self.patern('json-min', 'coverage-min', 'json'), caplog.records[2].msg)
        assert Path(tmpdir.join("coverage-min.json")).exists()

    def test_get_report_str(self, tmpdir, monkeypatch):
        monkeypatch.chdir(tmpdir)
        coverage_path = os.path.join(
            COVERAGE_FILES_DIR, "HealthCheckAnalyzeLargeInvestigations"
        )
        temp_coverage_path = tmpdir.join(".coverage")
        copy_file(coverage_path, temp_coverage_path)
        fix_file_path(temp_coverage_path, PYTHON_FILE_PATH)
        cov_report = CoverageReport(coverage_file=temp_coverage_path)
        cov_report._cov = get_coverage_obj(
            coverage_file=temp_coverage_path, report_dir=None, load_old=True
        )
        report_str = cov_report.report_str
        assert report_str.split("\n")[2].split() == [
            PYTHON_FILE_PATH,
            "38",
            "10",
            "73.68%",
        ]

    def test_cov_creation(self, tmpdir, monkeypatch, mocker):
        monkeypatch.chdir(tmpdir)
        cov_report = CoverageReport()
        assert cov_report._cov is None
        get_coverage_obj_mock = mocker.patch(
            "demisto_sdk.commands.coverage_analyze.coverage_report.get_coverage_obj"
        )
        cov_report.cov
        assert cov_report._cov is not None
        get_coverage_obj_mock.assert_called_once()

    def test_files(self, tmpdir, monkeypatch):
        monkeypatch.chdir(tmpdir)
        coverage_path = os.path.join(
            COVERAGE_FILES_DIR, "HealthCheckAnalyzeLargeInvestigations"
        )
        temp_coverage_path = tmpdir.join(".coverage")
        copy_file(coverage_path, temp_coverage_path)
        fix_file_path(temp_coverage_path, PYTHON_FILE_PATH)
        cov_report = CoverageReport(coverage_file=temp_coverage_path)
        cov_report._cov = get_coverage_obj(
            coverage_file=temp_coverage_path, report_dir=None, load_old=True
        )
        file_path, cover = list(cov_report.files.items())[0]
        assert os.path.abspath(file_path) == PYTHON_FILE_PATH
        assert isinstance(cover, float)

    def test_original_summary(self, tmpdir, monkeypatch, requests_mock):
        requests_mock.get(DEFAULT_URL, json=read_file(JSON_MIN_DATA_FILE))
        monkeypatch.chdir(tmpdir)
        assert (
            CoverageReport().original_summary == read_file(JSON_MIN_DATA_FILE)["files"]
        )


class TestFileMinCoverage:
    data_test_with_new_file = [
        ("test", 70.0),
        (
            "/Users/username/dev/content/Packs/SomePack/Integrations/SomeIntegration/SomeIntegration.py",
            80.0,
        ),
    ]

    @pytest.mark.parametrize("file_path, default_min_cover", data_test_with_new_file)
    def test_with_new_file(self, file_path, default_min_cover, tmpdir, monkeypatch):
        monkeypatch.chdir(tmpdir)
        cov_report = CoverageReport(default_min_coverage=default_min_cover)
        cov_report._original_summary = {}
        assert cov_report.file_min_coverage(file_path) == default_min_cover

    data_test_with_exist_file = [
        ("test", 70.0, 69.0),
        (
            "/Users/username/dev/content/Packs/SomePack/Integrations/SomeIntegration/SomeIntegration.py",
            80.0,
            79.0,
        ),
    ]

    @pytest.mark.parametrize(
        "file_path, current_cover, expected_min_cover", data_test_with_exist_file
    )
    def test_with_exist_file(
        self, file_path, current_cover, expected_min_cover, tmpdir, monkeypatch
    ):
        monkeypatch.chdir(tmpdir)
        cov_report = CoverageReport()
        cov_report._original_summary = {os.path.relpath(file_path): current_cover}
        assert cov_report.file_min_coverage(file_path) == expected_min_cover

    data_test_with_custom_epsilon_file = [
        ("test", 1.0, 79.0),
        (
            "/Users/username/dev/content/Packs/SomePack/Integrations/SomeIntegration/SomeIntegration.py",
            3.0,
            77.0,
        ),
    ]

    @pytest.mark.parametrize(
        "file_path, epsilon, expected_min_cover", data_test_with_custom_epsilon_file
    )
    def test_with_custom_epsilon_file(
        self, file_path, epsilon, expected_min_cover, tmpdir, monkeypatch
    ):
        monkeypatch.chdir(tmpdir)
        cov_report = CoverageReport(allowed_coverage_degradation_percentage=epsilon)
        cov_report._original_summary = {os.path.relpath(file_path): 80.0}
        assert cov_report.file_min_coverage(file_path) == expected_min_cover


class TestCoverageDiffReport:
    @staticmethod
    def get_coverage_report_obj():
        cov_report = CoverageReport()
        cov_report._original_summary = read_file(JSON_MIN_DATA_FILE)["files"]
        return cov_report

    def test_without_files(self, caplog, tmpdir, monkeypatch, mocker):
        monkeypatch.chdir(tmpdir)
        cov_report = self.get_coverage_report_obj()
        mocker.patch(
            "demisto_sdk.commands.coverage_analyze.coverage_report.CoverageReport.files",
            return_value={},
        )
        with caplog.at_level(logging.ERROR, logger="demisto-sdk"):
            assert cov_report.coverage_diff_report()
        assert caplog.records == []

    def test_with_degradated_files(self, tmpdir, monkeypatch, mocker):
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.chdir(tmpdir)
        cov_report = self.get_coverage_report_obj()
        cov_report._report_str = Path(REPORT_STR_FILE).read_text()
        mocker.patch.object(cov_report, "file_min_coverage", return_value=100.0)
        assert cov_report.coverage_diff_report() is False
        assert len(flatten_call_args(logger_info.call_args_list)) == 1

    def test_with_passed_files(self, caplog, tmpdir, monkeypatch, mocker):
        monkeypatch.chdir(tmpdir)
        cov_report = self.get_coverage_report_obj()
        cov_report._report_str = Path(REPORT_STR_FILE).read_text()
        mocker.patch.object(cov_report, "file_min_coverage", return_value=10.0)
        with caplog.at_level(logging.ERROR, logger="demisto-sdk"):
            assert cov_report.coverage_diff_report()
        assert caplog.records == []
