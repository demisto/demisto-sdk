from pathlib import Path

import coverage

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.coverage_analyze.helpers import coverage_files
from demisto_sdk.commands.run_unit_tests.unit_tests_runner import (
    fix_coverage_report_path,
)


def merge_coverage_report():
    coverage_path = CONTENT_PATH / ".coverage"
    coverage_path.unlink(missing_ok=True)
    cov = coverage.Coverage(data_file=coverage_path)
    if not (files := coverage_files()):
        logger.warning("No coverage files found, skipping coverage report.")
        return
    fixed_files = [file for file in files if fix_coverage_report_path(Path(file))]
    cov.combine(fixed_files)
    cov.xml_report(outfile=str(CONTENT_PATH / "coverage.xml"))
    logger.info(f"Coverage report saved to {CONTENT_PATH / 'coverage.xml'}")


def main():
    try:
        merge_coverage_report()
    except Exception as e:
        logger.warning(f"Failed to merge coverage report: {e}")


if __name__ == "__main__":
    SystemExit(main())
