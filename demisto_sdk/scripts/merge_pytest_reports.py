import shutil
import sqlite3
import tempfile
from pathlib import Path

import coverage
from junitparser import JUnitXml

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger


def fix_coverage_report_path(coverage_file: Path) -> bool:
    """
    Args:
        coverage_file: The coverage file to to fix (absolute file).
    Returns:
        True if the file was fixed, False otherwise.
    Notes:
        the .coverage files contain all the files list with their absolute path.
        but our tests (pytest step) are running inside a docker container.
        so we have to change the path to the correct one.
    """
    try:
        logger.debug(f"Editing coverage report for {coverage_file}")
        with tempfile.NamedTemporaryFile() as temp_file:
            # we use a tempfile because the original file could be readonly, this way we assure we can edit it.
            shutil.copy(coverage_file, temp_file.name)
            with sqlite3.connect(temp_file.name) as sql_connection:
                cursor = sql_connection.cursor()
                files = cursor.execute("SELECT * FROM file").fetchall()
                for id_, file in files:
                    if "conftest" in file:
                        cursor.execute(
                            "DELETE FROM file WHERE id = ?", (id_,)
                        )  # delete the file from the coverage report, as it is not relevant.
                    if not file.startswith("/src"):
                        # means that the .coverage file is already fixed
                        continue
                    file = Path(file).relative_to("/content")
                    if (
                        not (CONTENT_PATH / file).exists()
                        or file.parent.name
                        != file.stem  # For example, in `QRadar_v3` directory we only care for `QRadar_v3.py`
                    ):
                        logger.debug(f"Removing {file} from coverage report")
                        cursor.execute(
                            "DELETE FROM file WHERE id = ?", (id_,)
                        )  # delete the file from the coverage report, as it is not relevant.
                    else:
                        cursor.execute(
                            "UPDATE file SET path = ? WHERE id = ?",
                            (str(CONTENT_PATH / file), id_),
                        )
                sql_connection.commit()
                logger.debug("Done editing coverage report")
            coverage_file.unlink()
            shutil.copy(temp_file.name, coverage_file)
            return True
    except Exception:
        logger.warning(f"Broken .coverage file found: {coverage_file}, deleting it")
        coverage_file.unlink(missing_ok=True)
        return False


def merge_coverage_report():
    coverage_path = CONTENT_PATH / ".pre-commit" / "coverage"
    (CONTENT_PATH / ".coverage").unlink(missing_ok=True)
    cov = coverage.Coverage()
    cov.combine([str(coverage_file) for coverage_file in coverage_path.iterdir()])
    fix_coverage_report_path((CONTENT_PATH / ".coverage"))
    cov.xml_report(outfile=str(CONTENT_PATH / "coverage.xml"))
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
