import shutil
import sqlite3
import tempfile
from pathlib import Path

import coverage

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.coverage_analyze.helpers import coverage_files


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
                    if not file.startswith("/content"):
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
        logger.warning(f"Broken .coverage file found: {file}, deleting it")
        file.unlink(missing_ok=True)
        return False


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
