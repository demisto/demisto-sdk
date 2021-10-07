import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Text

import coverage
import pytest
import requests
from freezegun import freeze_time

from demisto_sdk.commands.coverage_analyze.helpers import (CoverageSummary,
                                                           InvalidReportType,
                                                           coverage_files,
                                                           export_report,
                                                           fix_file_path,
                                                           get_coverage_obj,
                                                           get_report_str,
                                                           parse_report_type,
                                                           percent_to_float)

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
JSON_MIN_DATA_FILE = os.path.join(TEST_DATA_DIR, 'coverage-min.json')
COVERAGE_FILES_DIR = os.path.join(TEST_DATA_DIR, 'coverage_data_files')
PYTHON_FILE_PATH = os.path.join(TEST_DATA_DIR, 'HealthCheckAnalyzeLargeInvestigations_py')


def read_file(file_path):
    with open(file_path, 'r') as file_obj:
        return file_obj.read().strip()


def write_file(file_path, file_content):
    with open(file_path, 'w') as file_obj:
        file_obj.write(file_content)


def copy_file(origin, destination):
    with open(destination, 'wb') as destination_file:
        with open(origin, 'rb') as origin_file:
            destination_file.write(origin_file.read())


def test_get_report_str():
    data = 'coverage data'

    class foo:
        def __init__(self):
            pass

        def report(self, file):
            file.write(data)

    assert data == get_report_str(foo())


data_percent_to_float = [('75', 75.0), ('75.0', 75.0), ('75.0%', 75.0)]


@pytest.mark.parametrize('input_str, expected_result', data_percent_to_float)
def test_percent_to_float(input_str, expected_result):
    assert expected_result == percent_to_float(input_str)


class TestParseReportType:
    def test_with_none(self):
        assert parse_report_type(None) == []

    def test_with_one(self):
        assert parse_report_type('text') == ['text']

    def test_with_multiple(self):
        assert parse_report_type('text,json') == ['text', 'json']

    def test_with_all(self):
        assert sorted(parse_report_type('all')) == sorted(['text', 'json', 'json-min', 'html', 'xml'])

    def test_all_report_types_explicit(self):
        assert parse_report_type('text,json,json-min,html,xml') == ['text', 'json', 'json-min', 'html', 'xml']

    def test_one_invalid(self):
        with pytest.raises(InvalidReportType) as invalid_report_type:
            parse_report_type('test')
            assert str(invalid_report_type) == "test is not a valid report type. You can use the following report types as a " \
                "comma separated value for the --report-type argument ('text', 'html', 'xml', 'json', 'json-min', 'all')."

    def test_with_mixed_values(self):
        with pytest.raises(InvalidReportType) as invalid_report_type:
            parse_report_type('xml,test')
            assert str(invalid_report_type) == "test is not a valid report type. You can use the following report types as a " \
                "comma separated value for the --report-type argument ('text', 'html', 'xml', 'json', 'json-min', 'all')."

    def test_with_all_and_other_values(self):
        with pytest.raises(InvalidReportType) as invalid_report_type:
            parse_report_type('xml,all')
            assert str(invalid_report_type) == 'ou may not use the "all" report type in addition to other report types.'

    class TestInvalidReportType:

        def test_with_all(self):
            assert str(InvalidReportType('all')) == 'You may not use the "all" report type in addition to other report types.'

        def test_general(self):
            assert str(InvalidReportType('test')) == "test is not a valid report type. You can use the following report types as a " \
                "comma separated value for the --report-type argument ('text', 'html', 'xml', 'json', 'json-min', 'all')."


class TestExportReport:

    def foo(self):
        pass

    def foo_raises(self):
        raise coverage.misc.CoverageException('coverage.misc.CoverageException')

    def test_export_report(self, caplog, mocker):
        foo_mock = mocker.patch.object(self, 'foo')
        with caplog.at_level(logging.INFO):
            export_report(self.foo, 'the_format', 'the_path')
        foo_mock.assert_called_once()
        assert len(caplog.records) == 1
        assert caplog.records[0].msg == 'exporting the_format coverage report to the_path'

    def test_export_report_with_error(self, caplog):
        with caplog.at_level(logging.WARNING):
            export_report(self.foo_raises, 'the_format', 'the_path')
        assert len(caplog.records) == 1
        assert caplog.records[0].msg == 'coverage.misc.CoverageException'


class TestCoverageSummary:

    class TestGetFilesSummary:
        default_url = 'https://storage.googleapis.com/marketplace-dist-dev/code-coverage/coverage-min.json'

        @staticmethod
        def check_get_files(cache_dir, mock_min_cov_request, request_count):
            CoverageSummary(
                cache_dir=cache_dir, previous_coverage_report_url=TestCoverageSummary.TestGetFilesSummary.default_url
            ).get_files_summary()
            assert len(mock_min_cov_request.request_history) == request_count
            assert read_file(JSON_MIN_DATA_FILE) == read_file(cache_dir.join('coverage-min.json'))

        @staticmethod
        def validate_min_format(summary):
            summary['total_coverage']
            datetime.strptime(summary['last_updated'], '%Y-%m-%dT%H:%M:%SZ')
            files = summary['files']
            assert bool(files)
            for file_name, percent in files.items():
                assert isinstance(file_name, Text)
                assert isinstance(percent, float)

        def test_url_and_validate_data(self):
            res = requests.get(self.default_url)
            res.raise_for_status()
            summary = res.json()
            self.validate_min_format(summary)

        def test_the_data_file_is_valid(self):
            self.validate_min_format(json.loads(read_file(JSON_MIN_DATA_FILE)))

        def test_without_cached_data(self, tmpdir, requests_mock):
            mock_min_cov_request = requests_mock.get(self.default_url, text=read_file(JSON_MIN_DATA_FILE))
            files_data = CoverageSummary(
                cache_dir=tmpdir, previous_coverage_report_url=TestCoverageSummary.TestGetFilesSummary.default_url
            ).get_files_summary()
            assert len(mock_min_cov_request.request_history) == 1
            assert read_file(JSON_MIN_DATA_FILE) == read_file(tmpdir.join('coverage-min.json'))
            assert files_data == json.loads(read_file(JSON_MIN_DATA_FILE))['files']

        def test_with_invalid_cached_data_that_will_raise_key_error(self, tmpdir, requests_mock):
            json_data = read_file(JSON_MIN_DATA_FILE)
            mock_min_cov_request = requests_mock.get(self.default_url, text=json_data)
            json_data = json.loads(json_data)
            json_data.pop('files')
            cached_file = tmpdir.join('coverage-min.json')
            write_file(cached_file, json.dumps(json_data))
            self.check_get_files(tmpdir, mock_min_cov_request, 1)

        def test_with_invalid_cached_data_that_will_raise_value_error(self, tmpdir, requests_mock):
            json_data = read_file(JSON_MIN_DATA_FILE)
            mock_min_cov_request = requests_mock.get(self.default_url, text=json_data)
            json_data = json.loads(json_data)
            json_data['last_updated'] = 'test'
            cached_file = tmpdir.join('coverage-min.json')
            write_file(cached_file, json.dumps(json_data))
            self.check_get_files(tmpdir, mock_min_cov_request, 1)

        def test_with_invalid_cached_data_that_will_raise_json_parse_error(self, tmpdir, requests_mock):
            cached_file = tmpdir.join('coverage-min.json')
            json_data = read_file(JSON_MIN_DATA_FILE)
            mock_min_cov_request = requests_mock.get(self.default_url, text=json_data)
            write_file(cached_file, json_data.replace('{', '', 1))
            mock_min_cov_request = requests_mock.get(self.default_url, text=read_file(JSON_MIN_DATA_FILE))
            self.check_get_files(tmpdir, mock_min_cov_request, 1)

        def test_with_not_updated_file(self, tmpdir, requests_mock):
            cached_file = tmpdir.join('coverage-min.json')
            text_data = read_file(JSON_MIN_DATA_FILE)
            write_file(cached_file, text_data)
            mock_min_cov_request = requests_mock.get(self.default_url, text=text_data)
            self.check_get_files(tmpdir, mock_min_cov_request, 1)

        @ freeze_time('2021-10-1T00:00:00Z')
        def test_with_updated_file(self, tmpdir, requests_mock):
            cached_file = tmpdir.join('coverage-min.json')
            text_data = read_file(JSON_MIN_DATA_FILE)
            write_file(cached_file, text_data)
            mock_min_cov_request = requests_mock.get(self.default_url, text=text_data)
            self.check_get_files(tmpdir, mock_min_cov_request, 0)

        def test_with_no_cache(self, mocker, requests_mock):
            import builtins
            mock_min_cov_request = requests_mock.get(self.default_url, text=read_file(JSON_MIN_DATA_FILE))
            not_mocked_open = builtins.open
            open_file_mocker = mocker.patch('builtins.open')
            files_data = CoverageSummary(
                previous_coverage_report_url=TestCoverageSummary.TestGetFilesSummary.default_url, no_cache=True
            ).get_files_summary()
            assert open_file_mocker.call_count == 0
            builtins.open = not_mocked_open
            assert len(mock_min_cov_request.request_history) == 1
            assert files_data == json.loads(read_file(JSON_MIN_DATA_FILE))['files']

    class TestCreateCoverageSummaryFile:
        def test_creation(self, tmpdir):
            min_cov_path = tmpdir.join('coverage-min.json')
            CoverageSummary.create(os.path.join(TEST_DATA_DIR, 'coverage.json'), min_cov_path)
            assert read_file(JSON_MIN_DATA_FILE) == read_file(min_cov_path)


data_test_coverage_files = [
    ([], set()),
    (['Packs/SomePack'], set()),
    (['Packs/SomePack/Integrations/SomeIntegration'], {'Packs/SomePack/Integrations/SomeIntegration/.coverage'}),
    (['Packs/SomePack/Scripts/SomeScripts'], {'Packs/SomePack/Scripts/SomeScripts/.coverage'}),
    (
        ['Packs/SomePack/Scripts/SomeScript', 'Packs/SomePack/Integrations/SomeIntegration'],
        {'Packs/SomePack/Integrations/SomeIntegration/.coverage', 'Packs/SomePack/Scripts/SomeScript/.coverage'}
    ),
]


@pytest.mark.parametrize('dirs_list, files_set', data_test_coverage_files)
def test_coverage_files(tmpdir, monkeypatch, dirs_list, files_set):
    monkeypatch.chdir(tmpdir)
    for cov_dir in dirs_list:
        os.makedirs(cov_dir)
        with open(os.path.join(cov_dir, '.coverage'), 'wb') as coverage_file:
            coverage_file.write(b'test')
        with open(os.path.join(cov_dir, 'something.py'), 'wb') as coverage_file:
            coverage_file.write(b'test')

    assert set(coverage_files()) == files_set


class TestFixFilePath:

    data_test_fix_file_path = [
        ('HealthCheckAnalyzeLargeInvestigations', 'the_python_file_path'),
    ]

    @pytest.mark.parametrize('cov_file_name, python_file_dir', data_test_fix_file_path)
    def test_fix(self, tmpdir, cov_file_name, python_file_dir):
        dot_coverage_path = tmpdir.join('.coverage')
        copy_file(os.path.join(COVERAGE_FILES_DIR, cov_file_name), dot_coverage_path)
        fix_file_path(dot_coverage_path, python_file_dir)
        with sqlite3.connect(dot_coverage_path) as sql_connection:
            cursor = sql_connection.cursor()
            data = cursor.execute('SELECT * FROM file').fetchall()[0]
            assert data == (1, python_file_dir)
            cursor.close()

    data_test_with_two_files = [
        ['HealthCheckAnalyzeLargeInvestigations', 'Vertica']
    ]

    @pytest.mark.parametrize('cov_file_names', data_test_with_two_files)
    def test_with_two_files(self, caplog, tmpdir, cov_file_names):
        cov_files_paths = []
        for cov_file_name in cov_file_names:
            named_coverage_path = tmpdir.join(cov_file_name)
            copy_file(os.path.join(COVERAGE_FILES_DIR, cov_file_name), named_coverage_path)
            cov_files_paths.append(named_coverage_path)
        dot_cov_file_path = tmpdir.join('.covergae')
        cov_obj = coverage.Coverage(data_file=dot_cov_file_path)
        cov_obj.combine(cov_files_paths)

        with caplog.at_level(logging.ERROR & logging.DEBUG):
            fix_file_path(dot_cov_file_path, 'some_path')

        assert len(caplog.records) == 2
        assert caplog.records[0].msg == 'unexpected file list in coverage report'
        assert caplog.records[0].levelname == 'ERROR'
        assert caplog.records[1].msg == 'removing coverage report for some_path'
        assert caplog.records[1].levelname == 'DEBUG'
        assert not os.path.exists(dot_cov_file_path)


class TestGetCoverageObj:
    def test_without_data(self, monkeypatch, tmpdir):
        monkeypatch.chdir(tmpdir)
        with pytest.raises(coverage.misc.CoverageException):
            get_coverage_obj(None, None).report()

    def test_cov_file(self, tmpdir):
        cov_file = tmpdir.join('.coverage')
        coverage_obj = get_coverage_obj(coverage_file=cov_file, report_dir=None)
        assert coverage_obj.config.data_file == cov_file

    def test_report_dir(self, monkeypatch, tmpdir):
        monkeypatch.chdir(tmpdir)
        coverage_obj = get_coverage_obj(coverage_file=None, report_dir=tmpdir)
        assert coverage_obj.config.html_dir == tmpdir.join('html')
        assert coverage_obj.config.xml_output == tmpdir.join('coverage.xml')
        assert coverage_obj.config.json_output == tmpdir.join('coverage.json')

    def test_load_old(self, monkeypatch, tmpdir):
        monkeypatch.chdir(tmpdir)
        copy_file(os.path.join(COVERAGE_FILES_DIR, 'HealthCheckAnalyzeLargeInvestigations'), tmpdir.join('.coverage'))
        fix_file_path(tmpdir.join('.coverage'), PYTHON_FILE_PATH)
        # will raise 'coverage.misc.CoverageException' if the file will not be loaded
        get_coverage_obj(coverage_file=None, report_dir=None, load_old=True).report()

    def test_combine(self, monkeypatch, tmpdir, mocker):
        cov_file_names = ['HealthCheckAnalyzeLargeInvestigations', 'VirusTotalV3']
        tmp_cov_file_names = []
        monkeypatch.chdir(tmpdir)
        for cov_file_name in cov_file_names:
            tmp_cov_file_name = tmpdir.join(cov_file_name)
            tmp_cov_file_names.append(tmp_cov_file_name)
            copy_file(os.path.join(COVERAGE_FILES_DIR, cov_file_name), tmp_cov_file_name)
        mocker.patch('demisto_sdk.commands.coverage_analyze.helpers.coverage_files', return_value=map(lambda x: x, tmp_cov_file_names))

        # will raise 'coverage.misc.CoverageException' if the file will not be loaded
        coverage_obj = get_coverage_obj(coverage_file=None, report_dir=None, combine_from_content_repo=True)
        with sqlite3.connect(coverage_obj.config.data_file) as sql_connection:
            cursor = sql_connection.cursor()
            data = list(cursor.execute('SELECT * FROM file').fetchall())
            cursor.close()
        assert len(data) == 2
        assert data[0] == (1, '/Users/username/dev/demisto/content/Packs/HealthCheck/Scripts/'
                           'HealthCheckAnalyzeLargeInvestigations/HealthCheckAnalyzeLargeInvestigations.py')
        assert data[1] == (2, '/Users/username/dev/demisto/content/Packs/VirusTotal/Integrations/VirusTotalV3/VirusTotalV3.py')
