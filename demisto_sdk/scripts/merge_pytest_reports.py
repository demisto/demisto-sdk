import shutil
import sqlite3
import tempfile
from pathlib import Path

import coverage
from junitparser import JUnitXml

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger, logging_setup


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
                    file = Path(file).relative_to("/src")
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
    coverage_path = CONTENT_PATH / ".coverage"
    coverage_path.unlink(missing_ok=True)
    cov = coverage.Coverage(data_file=coverage_path)
    # this is the path where the pre-commit created the coverage files
    created_coverage_path = CONTENT_PATH / ".pre-commit" / "coverage"
    if not created_coverage_path.exists() or not (
        files := list(created_coverage_path.iterdir())
    ):
        logger.warning("No coverage files found, skipping coverage report.")
        return
    fixed_files = [str(file) for file in files if fix_coverage_report_path(Path(file))]
    cov.combine(fixed_files)
    for file in files:
        Path(file).unlink(missing_ok=True)
    logger.info("Coverage report was successfully merged.")


def merge_junit_reports():
    junit_reports_path = CONTENT_PATH / ".pre-commit" / "pytest-junit"
    if not junit_reports_path.exists():
        logger.warning("No junit reports found, skipping junit report.")
        return
    report_files = junit_reports_path.iterdir()
    if reports := [JUnitXml.fromfile(str(file)) for file in report_files]:
        report = reports[0]
        for rep in reports[1:]:
            report += rep
        report.write(str(CONTENT_PATH / ".report_pytest.xml"))
        for file in report_files:
            Path(file).unlink(missing_ok=True)
    logger.info("Junit report was successfully merged.")


def main():
    try:
        logging_setup()
        merge_coverage_report()
        merge_junit_reports()
    except Exception as e:
        logger.warning(f"Failed to merge reports: {e}")
        raise


if __name__ == "__main__":
    SystemExit(main())
