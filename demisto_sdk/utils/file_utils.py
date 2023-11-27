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
            logger.error(f"Unable to calculate file diff, file not found: {enoent.strerror}")
        except Exception as e:
            logger.error(f"Unable to calculate file diff: {e}")
        finally:
            return file_diff


def merge_files(f1: Path, f2: Path, output_dir: str) -> Optional[Path]:
    """
    Merges 2 files into one.

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
        logger.error(f"Neither file '{f1.__str__()}' not '{f2.__str__()}' Exists.")
        return None
    
    # Check if the files are identical and return the original if they are
    try:
        if filecmp.cmp(f1, f2, shallow=False):
            logger.debug(f"Files '{f1.__str__()}' and '{f2.__str__()}' are identical. Returning '{f1.__str__()}'")
            return f1
    except PermissionError as pe:
        logger.error(f"Error comparing files '{f1.__str__()}' and '{f2.__str__()}': {str(pe)}. Returning '{f2.__str__()}'")
        return f2

    diff = get_file_diff(f1, f2)

    # In case we can't create a file diff, we want to return f2
    if not diff:
        logger.warning(f"Unable to calculate file diff between '{f1.__str__()}' and '{f2.__str__()}'. Returning '{f2.__str__()}'")
        return f2

    output_text = []
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
    # Lines that have '-' means that the line was removed from f2.
    # Lines that have '+' means that the line was added to f2.
    try:
        for i, line in enumerate(diff):

            # If the text is found in both, we want to add it.
            if line.startswith(TOKEN_BOTH):
                output_text.append(line.replace(TOKEN_BOTH, "", 2))

            # If the text has the following pattern:
            # - lorem
            # + loremm
            # ?      +
            # We want to take the original text and skip the following line
            elif line.startswith(TOKEN_REMOVED):
                try:
                    if diff[i+1].startswith(TOKEN_ADDED) and diff[i+2].startswith(TOKEN_NOT_PRESENT):
                        output_text.append(line.replace(TOKEN_REMOVED, "", 2))
                        diff.pop(i+1)
                    elif diff[i+1].startswith(TOKEN_NOT_PRESENT) and diff[i+2].startswith(TOKEN_ADDED):
                        diff.pop(i+1)
                    else:
                        output_text.append(line.replace(TOKEN_REMOVED, "", 2))
                except IndexError:
                    # If the next 2 lines don't exist, it means that the line was 
                    # removed and needs to be added
                    output_text.append(line.replace(TOKEN_REMOVED, "", 2))

            # We want to add any line
            elif line.startswith(TOKEN_ADDED):
                output_text.append(line.replace(TOKEN_ADDED, "", 2))

            # In cases when there's such a line:
            # ?              ++++++\n
            # Or:
            # ?              -----\n
            # it indicates characters that were added/removed
            # from line before.
            # Can be ignored
            elif line.startswith(TOKEN_NOT_PRESENT) and line.endswith("\n"):
                pass

    # If there are any errors during the processing of the diff
    # we return f2
    except Exception as e:
        logger.error(f"Erroring merging files: {str(e)}. Returning '{f2.__str__()}'...")
        return f2

    with output_file.open("w", newline='\n') as out:
        out.writelines(output_text)

    return output_file
