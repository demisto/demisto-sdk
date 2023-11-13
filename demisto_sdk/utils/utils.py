import os
import tempfile
from configparser import ConfigParser, MissingSectionHeaderError
from difflib import Differ
from pathlib import Path
from typing import List, Optional, Union

from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import (
    YAMLContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import (
    YAMLContentUnifiedObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack

ContentEntity = Union[YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject]


def get_containing_pack(content_entity: ContentEntity) -> Pack:
    """Get pack object that contains the content entity.

    Args:
        content_entity: Content entity object.

    Returns:
        Pack: Pack object that contains the content entity.
    """
    pack_path = content_entity.path
    while pack_path.parent.name.casefold() != "packs":
        pack_path = pack_path.parent
    return Pack(pack_path)


def check_configuration_file(command, args):
    config_file_path = ".demisto-sdk-conf"
    true_synonyms = ["true", "True", "t", "1"]
    if Path(config_file_path).is_file():
        try:
            config = ConfigParser(allow_no_value=True)
            config.read(config_file_path)

            if command in config.sections():
                for key in config[command]:
                    if key in args:
                        # if the key exists in the args we will run it over if it is either:
                        # a - a flag currently not set and is defined in the conf file
                        # b - not a flag but an arg that is currently None and there is a value for it in the conf file
                        if args[key] is False and config[command][key] in true_synonyms:
                            args[key] = True

                        elif args[key] is None and config[command][key] is not None:
                            args[key] = config[command][key]

                    # if the key does not exist in the current args, add it
                    else:
                        if config[command][key] in true_synonyms:
                            args[key] = True

                        else:
                            args[key] = config[command][key]

        except MissingSectionHeaderError:
            pass


class FileUtils:

    @staticmethod
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

        a = original.read_text().splitlines(keepends=True)
        b = modified.read_text().splitlines(keepends=True)

        return list(d.compare(a, b))
    
    @staticmethod
    def get_file_diff_words(original: Path, modified: Path) -> List[str]:
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

        a = original.read_text().splitlines(keepends=True)
        b = modified.read_text().splitlines(keepends=True)

        return list(d.compare(a, b))

    @staticmethod
    def merge_files(f1: Path, f2: Path, output_dir: str) -> Optional[Path]:
        """
        Merges 2 files into one.
        """

        TOKEN_REMOVED = "- "
        TOKEN_ADDED = "+ "
        TOKEN_NOT_PRESENT = "? "
        TOKEN_BOTH = " "

        if not f1.exists() or not f2.exists():
            print(f"Either file '{f1.__str__()}' or  '{f2.__str__()}' don't exist")
            return None

        diff = FileUtils.get_file_diff(f1, f2)

        output_text = []
        output_path = Path(output_dir)
        if output_path.is_dir():
            if output_path.exists():
                output_path.rmdir()
            output_file = Path(output_dir) / f"{f1.name}-merged{f1.suffix}"
        elif output_path.is_file():
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            output_file = output_path
        else:
            output_file = Path(os.path.join(tempfile.mkstemp(suffix=f1.suffix, prefix=f1.name)[1]))
        
        # We iterate over each line
        # Lines that have '-' means that the line was removed from f2.
        # Lines that have '+' means that the line was added to f2.
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

        with output_file.open("w", newline='\n') as out:
            out.writelines(output_text)

        return output_file
