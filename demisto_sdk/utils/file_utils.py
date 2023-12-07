import filecmp
import tempfile
from difflib import Differ
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.logger import logger

TOKEN_REMOVED = "- "
TOKEN_ADDED = "+ "
TOKEN_NOT_PRESENT = "? "
TOKEN_BOTH = " "


def get_file_diff(original: Path, modified: Path) -> List[str]:
    """
    Helper function to generate a list of differences between 2 files.

    Args:
        - `original` (``Path``): The path to the original file.
        - `modified` (``Path``): The path to the modified file.

    Returns:
        - `List[str]` of the differences between the files.
        Each line that is different between the two has a +, - or ? depending
        if the line was added, changed or removed.
    """

    d = Differ()

    file_diff: List[str] = []
    try:
        a = original.read_text().splitlines(keepends=True)
        b = modified.read_text().splitlines(keepends=True)

        file_diff.extend(list(d.compare(a, b)))
    except FileNotFoundError as enoent:
        logger.error(
            f"Unable to calculate file diff, file not found: {enoent.strerror}"
        )
    except Exception as e:
        logger.error(f"Unable to calculate file diff: {e}")
    finally:
        return file_diff


def merge_files(f1: Path, f2: Path, output_dir: str) -> Optional[Path]:
    """
    Merges 2 files into one. The merged file will include all lines that were
    removed from the original (`f1`) and append all lines added to the modified
    (`f2`). For example, if we have a file `f1`:

    ```markdown
    # Title

    # Section 1
    lorem ipsum

    # Section 2
    dolor sit amet
    ```

    and `f2`:
    ```markdown
    # Title

    # Section 1
    lorem ipsum

    # Section 3
    consectetur adipiscing elit
    ```

    The merged file will contain:

    ```markdown
    # Title

    # Section 1
    lorem ipsum

    # Section 2
    dolor sit amet

    # Section 3
    consectetur adipiscing elit
    ```

    Args:
    - `f1` (``Path``): The path to the original file.
    - `f2` (``Path``): The path to the modified file.
    - `output_dir` (``str``): The path where the merged file will be saved.

    Returns:
    - `Path` of the output file. If neither `f1` nor `f2` exists, returns `None`.
    """

    # Check if the files exist
    # If 1 exists but the other doesn't, return the one that does
    # If neither exists, return None
    if not f1.exists() and f2.exists():
        logger.warn(f"File '{f1.__str__()}' doesn't exist. Returning '{f2.__str__()}'")
        return f2
    elif not f2.exists() and f1.exists():
        logger.warn(f"File '{f2.__str__()}' doesn't exist. Returning '{f1.__str__()}'")
        return f1
    elif not f1.exists() and not f2.exists():
        logger.error(f"Neither file '{f1.__str__()}' nor '{f2.__str__()}' exist.")
        return None

    # Check if the files are identical and return the original if they are
    try:
        if filecmp.cmp(f1, f2, shallow=False):
            logger.debug(
                f"Files '{f1.__str__()}' and '{f2.__str__()}' are identical. Returning '{f1.__str__()}'"
            )
            return f1
    except PermissionError as pe:
        logger.error(
            f"Error comparing files '{f1.__str__()}' and '{f2.__str__()}': {str(pe)}. Returning '{f2.__str__()}'"
        )
        return f2

    diff = get_file_diff(f1, f2)

    # In case we can't create a file diff, we want to return f2
    if not diff:
        logger.warning(
            f"Unable to calculate file diff between '{f1.__str__()}' and '{f2.__str__()}'. Returning '{f2.__str__()}'"
        )
        return f2

    output_path = Path(output_dir)

    # If the path is a directory, we create a file path to save the output to
    if output_path.is_dir():
        output_file = output_path / f"{f1.name}-merged{f1.suffix}"

    # If the path is a file, we delete it first
    elif output_path.is_file():
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        output_file = output_path

    # If it's neither, we create a temporary directory and dir
    else:
        output_file = Path(tempfile.mkstemp(suffix=f1.suffix, prefix=f1.name)[1])

    # We iterate over each line
    # Lines that have '-' means that the line was removed from f1.
    # Lines that have '+' means that the line was added to f2.
    try:
        for i, line in enumerate(diff):
            # If the text is found in both, we want to add it.
            if line.startswith(TOKEN_BOTH):
                diff[i] = line.replace(TOKEN_BOTH, "", 2)

            elif line.startswith(TOKEN_REMOVED):
                try:
                    # If the text has the following pattern:
                    # - lorem
                    # + loremm
                    # ?      +
                    # We want to take the original text
                    if diff[i + 1].startswith(TOKEN_ADDED) and diff[i + 2].startswith(
                        TOKEN_NOT_PRESENT
                    ):
                        diff[i] = line.replace(TOKEN_REMOVED, "", 2)

                    # If the text has the following pattern:
                    # - lore
                    # ?     -
                    # + lorem
                    # We want to take the modified text and skip the following line

                    elif diff[i + 1].startswith(TOKEN_NOT_PRESENT) and diff[
                        i + 2
                    ].startswith(TOKEN_ADDED):
                        diff[i] = diff[i + 2].replace(TOKEN_ADDED, "", 2)
                        diff[i + 2] = ""

                    # If no removal pattern found, add removed line
                    else:
                        diff[i] = line.replace(TOKEN_REMOVED, "", 2)
                except IndexError:
                    # If the next 2 lines don't exist, it means that the line was
                    # removed and needs to be added
                    diff[i] = line.replace(TOKEN_REMOVED, "", 2)

            # If the line was added, we append it to the end of the output file
            elif line.startswith(TOKEN_ADDED):
                diff[i] = ""
                diff.append(line.replace(TOKEN_ADDED, "", 2))

            # In cases when there's such a line:
            # ?              ++++++\n
            # Or:
            # ?              -----\n
            # it indicates characters that were added/removed
            # from line before.
            # Can be ignored
            elif line.startswith(TOKEN_NOT_PRESENT) and line.endswith("\n"):
                diff[i] = ""

    # If there are any errors during the processing of the diff
    # we return the modified file
    except Exception as e:
        logger.error(f"Erroring merging files: {str(e)}. Returning '{f2.__str__()}'...")
        return f2

    # Filter out empty strings
    output_text = [s for s in diff if s]

    with output_file.open("w", newline="\n") as out:
        out.writelines(output_text)

    return output_file
