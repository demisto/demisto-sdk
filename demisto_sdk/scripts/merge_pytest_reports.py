import shutil

import coverage
from junitparser import JUnitXml

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger


def merge_coverage_report():
    coverage_path = CONTENT_PATH / ".pre-commit" / "coverage"
    coverage_files = coverage_path.iterdir()
    coverage_path.unlink(missing_ok=True)
    cov = coverage.Coverage()
    cov.combine([str(coverage_file) for coverage_file in coverage_files])
    cov.xml_report(outfile=str(CONTENT_PATH / "coverage.xml"))
    cov.get_data()
    shutil.rmtree(coverage_path, ignore_errors=True)
    logger.info(f"Coverage report saved to {CONTENT_PATH / 'coverage.xml'}")


def merge_junit_reports():
    junit_reports_path = CONTENT_PATH / ".pre-commit" / "pytest-junit"

    report_files = junit_reports_path.iterdir()
    if reports := [JUnitXml.fromfile(str(file)) for file in report_files]:
        report = reports[0]
        for rep in reports[1:]:
            report += rep
        report.write(str(CONTENT_PATH / ".report_pytest.xml"))
        shutil.rmtree(junit_reports_path, ignore_errors=True)


def main():
    try:
        merge_coverage_report()
        merge_junit_reports()
    except Exception as e:
        logger.warning(f"Failed to merge reports: {e}")


if __name__ == "__main__":
    SystemExit(main())
