import logging
import os
from typing import Dict, Optional, Union

import coverage

from demisto_sdk.commands.coverage_analyze.helpers import (CoverageSummary,
                                                           export_report,
                                                           get_coverage_obj,
                                                           get_report_str,
                                                           parse_report_type,
                                                           percent_to_float)

logger = logging.getLogger('demisto-sdk')


class CoverageReport:

    def __init__(self, default_min_coverage: float = 70.0, allowed_coverage_degradation_percentage: float = 1.0,
                 coverage_file: Optional[str] = os.path.join('coverage_report', '.coverage'), no_cache: Optional[bool] = False,
                 report_dir: str = 'coverage_report', report_type: Optional[str] = None,
                 no_degradation_check: Optional[bool] = False,
                 previous_coverage_report_url: Optional[str] = 'https://storage.googleapis.com/marketplace-dist-dev/code-coverage/coverage-min.json'):
        self.report_dir = report_dir
        self._cov: Optional[coverage.Coverage] = None
        self._report_str: Optional[str] = None
        self.degradation_check = not no_degradation_check
        self.coverage_file = coverage_file
        self.report_types = parse_report_type(report_type)

        if not self.degradation_check:
            return

        self.default = default_min_coverage
        self.epsilon = allowed_coverage_degradation_percentage

        cache_dir = str(os.path.join(self.report_dir, 'cache')) if not no_cache else None
        self._original_summary: Union[CoverageSummary, Dict[str, float]] = CoverageSummary(
            cache_dir=cache_dir,
            previous_coverage_report_url=previous_coverage_report_url,
            no_cache=no_cache
        )

    '''Properties'''

    @property
    def cov(self) -> coverage.Coverage:
        if self._cov is None:
            self._cov = get_coverage_obj(coverage_file=self.coverage_file, report_dir=self.report_dir, load_old=True)
        return self._cov

    @property
    def report_str(self) -> str:
        if self._report_str is None:
            self._report_str = get_report_str(self.cov)
        return self._report_str

    @property
    def files(self) -> Dict[str, float]:
        files_dict = {}
        report_lines = self.report_str.strip().split('\n')[2:-2]
        for line in map(lambda x: x.split(), report_lines):
            files_dict[os.path.relpath(line[0])] = percent_to_float(line[-1])

        return files_dict

    @property
    def original_summary(self) -> Dict[str, float]:
        if isinstance(self._original_summary, CoverageSummary):
            self._original_summary = self._original_summary.get_files_summary()
        return self._original_summary

    '''Member functions'''

    def file_min_coverage(self, abs_file_path: str) -> float:
        file_rel_path = os.path.relpath(abs_file_path)
        try:
            return self.original_summary[file_rel_path] - self.epsilon
        except KeyError:
            pass
        return self.default

    def coverage_report(self):
        if not os.path.exists(self.cov.config.data_file):
            logger.debug(f'skipping coverage report {self.cov.config.data_file} file not found.')
            return

        logger.info(f'\n{self.report_str}')

        if 'text' in self.report_types:
            txt_file_path = os.path.join(self.report_dir, 'coverage.txt')
            logger.info(f'exporting txt coverage report to {txt_file_path}')
            with open(txt_file_path, 'w') as txt_file:
                txt_file.write(self.report_str)
        if 'html' in self.report_types:
            export_report(self.cov.html_report, 'html', os.path.join(self.cov.config.html_dir, 'index.html'))
        if 'xml' in self.report_types:
            export_report(self.cov.xml_report, 'xml', self.cov.config.xml_output)
        if 'json' in self.report_types:
            export_report(self.cov.json_report, 'json', self.cov.config.json_output)
        if 'json-min' in self.report_types:
            json_min_dir = os.path.join(self.report_dir, 'coverage-min.json')
            logger.info(f'exporting json-min coverage report to {json_min_dir}')
            CoverageSummary.create(self.cov.config.json_output, json_min_dir)

    def coverage_diff_report(self) -> bool:
        coverage_ok = True
        for file_name, cov_precents in self.files.items():
            min_cov = self.file_min_coverage(file_name)
            if min_cov > cov_precents:
                logger.error(f'file: {file_name} unittests coverage should reach at least {min_cov} currently {cov_precents}.')
                coverage_ok = False
        return coverage_ok
