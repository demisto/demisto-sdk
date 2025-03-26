import glob
import os
import re
import shutil
import textwrap
import traceback
import zipfile
from collections import defaultdict
from datetime import datetime
from io import StringIO
from pathlib import Path
from string import punctuation
from typing import Any, Dict, List, Optional, Tuple
from zipfile import ZipFile

from packaging.version import Version

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    AUTOMATION,
    ENTITY_TYPE_TO_DIR,
    INTEGRATION,
    INTEGRATIONS_DIR,
    MARKETPLACE_LIVE_DISCUSSIONS,
    MARKETPLACES,
    PACK_INITIAL_VERSION,
    PACKS_README_FILE_NAME,
    PLAYBOOKS_DIR,
    SCRIPT,
    SCRIPTS_DIR,
    XSOAR_AUTHOR,
    XSOAR_SUPPORT,
    XSOAR_SUPPORT_URL,
    ContentItems,
    FileType,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    capital_case,
    find_type,
    get_child_directories,
    get_child_files,
    get_display_name,
    get_pack_metadata,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.generate_docs.generate_integration_doc import (
    generate_integration_doc,
)
from demisto_sdk.commands.generate_docs.generate_playbook_doc import (
    generate_playbook_doc,
)
from demisto_sdk.commands.generate_docs.generate_script_doc import generate_script_doc
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from demisto_sdk.commands.update_release_notes.update_rn_manager import (
    UpdateReleaseNotesManager,
)


def get_previous_nonempty_line(lines: List[str], index: int):
    """
    Given a list of lines and a certain index, returns the previous line of the given line while ignoring newlines.
    Args:
        index: the current lines index.
        lines: the lines.
    """
    j = 1
    previous_line = ""
    if lines[index] == "\n":
        return previous_line

    while index - j > 0:
        previous_line = lines[index - j]
        if previous_line != "\n":
            return previous_line
        j += 1

    return previous_line


class ContributionConverter:
    """ContributionConverter converts contribution zip files to valid pack formats

    Class Variables:
        DATE_FORMAT (str): The date format to use in the pack metadata

    Instance Variables:
        name (str): The name for the pack
        configuration (Configuration): Configuration instance
        contribution (str|Nonetype): The path to a contribution zip file
        description (str): Description to attach to a converted contribution pack (in pack_metadata.json)
        author (str): Author to ascribe to a pack converted from a contribution zip (in pack_metadata.json)
        contrib_conversion_errs (List[str]): Messages of errors that occurred during a contribution conversion process
        packs_dir_path (str): The path to the 'Packs' subdirectory of the local content repo
        pack_dir_path (str): The path to the specific pack directory being created or updated, e.g. .../Packs/AbuseDB
        dir_name (str): The directory name of a pack's containing folder
        create_new (bool): True if creating a new pack (default), False if updating an existing pack
        gh_user (str): The github username of the person contributing the pack
        readme_files (List[str]): The readme files paths that is generated for new content items.
        update_type (str): The type of update being done. For exiting pack only.
        release_notes (str): The release note text. For exiting pack only.
        detected_content_items (List[str]):
            List of the detected content items objects in the contribution. For exiting pack only.
        working_dir_path (str): This directory is where contributions are processed before they are copied to the
            content pack directory.
    """

    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    SOURCE_FIELD_NAMES = {
        "sourcemoduleid",
        "sourcescripid",
        "sourceplaybookid",
        "sourceClassifierId",
    }

    def __init__(
        self,
        contribution: str,
        name: str = "",
        description: str = "",
        pack_readme: str = "",
        author: str = "",
        gh_user: str = "",
        create_new: bool = True,
        pack_dir_name: Optional[str] = None,
        update_type: str = "",
        release_notes: str = "",
        detected_content_items: list = [],
        base_dir: Optional[str] = None,
        working_dir_path: str = "",
    ):
        """Initializes a ContributionConverter instance

        Note that when recieving a contribution that is an update to an existing pack that the values of 'name',
        'description' and 'author' will be those of the existing pack.

        Args:
            name (str, optional): The name of the pack. Defaults to ''.
            contribution (str): The path to the contribution zipfile.
            description (str, optional): The description for the contribution. Defaults to ''.
            author (str, optional): The author of the contribution. Defaults to ''.
            gh_user (str, optional): The github username of the person contributing. Defaults to ''.
            create_new (bool, optional): Whether the contribution is intended as a new pack. When the contribution is
                intended as an update to an existing pack, the value passed should be False. Defaults to True.
            pack_dir_name (Union[str], optional): Explicitly pass the name of the pack directory. Only useful when
                updating an existing pack and the pack's directory is not equivalent to the value returned from
                running `self.format_pack_dir_name(name)`
            base_dir (Union[str], optional): Used to explicitly pass the path to the top-level directory of the
                local content repo. If no value is passed, the `CONTENT_PATH` variable is used to determine
                the path. Defaults to None.
            pack_readme (str): The content of the new pack readme, if create_new == True.

        """
        self.pack_readme = pack_readme
        self.configuration = Configuration()
        self.contribution = contribution
        self.description = description
        self.author = author
        self.update_type = update_type or "revision"
        self.release_notes = release_notes
        self.detected_content_items = detected_content_items or []
        self.gh_user = gh_user
        self.contrib_conversion_errs: List[str] = []
        self.create_new = create_new
        self.contribution_items_version: Dict[str, Dict[str, str]] = {}
        self.contribution_items_version_note = ""
        base_dir = base_dir or CONTENT_PATH  # type: ignore
        self.packs_dir_path: str = os.path.join(base_dir, "Packs")  # type: ignore
        if not os.path.isdir(self.packs_dir_path):
            os.makedirs(self.packs_dir_path)

        self.name = name
        self.dir_name = pack_dir_name or ContributionConverter.format_pack_dir_name(
            name
        )
        if create_new:
            # make sure that it doesn't conflict with an existing pack directory
            self.dir_name = self.ensure_unique_pack_dir_name(self.dir_name)
        self.pack_dir_path = Path(self.packs_dir_path, self.dir_name)
        if not self.pack_dir_path.is_dir():
            os.makedirs(str(self.pack_dir_path))
        self.readme_files: List[str] = []
        self.api_module_path: Optional[str] = None
        self.working_dir_path = (
            Path(working_dir_path) if working_dir_path else self.pack_dir_path
        )

    @staticmethod
    def format_pack_dir_name(name: str) -> str:
        """Formats a (pack) name to a valid value

        Specification:
            A valid pack name does not contain any whitespace and may only contain alphanumeric, underscore, and
            dash characters. The name must begin and end with an alphanumeric character. If it begins with an
            alphabetical character, that character must be capitalized.

        Behavior:
            Individual words are titlecased, whitespace is stripped, and disallowed punctuation and space
            characters are replaced with underscores.

        Args:
            name (str): The proposed pack name to convert to valid pack name format

        Returns:
            str: The reformatted pack name
        """
        temp = capital_case(name.strip().strip("-_"))
        punctuation_to_replace = punctuation.replace("-", "").replace("_", "")
        translation_dict = {x: "_" for x in punctuation_to_replace}
        translation_table = str.maketrans(translation_dict)
        temp = temp.translate(translation_table).strip("-_")
        temp = re.sub(r"-+", "-", re.sub(r"_+", "_", temp))
        comparator = capital_case(temp.replace("_", " ").replace("-", " "))
        result = ""
        i = j = 0
        while i < len(temp):
            temp_char = temp[i]
            comp_char = comparator[j]
            if temp_char.casefold() != comp_char.casefold():
                while temp_char in {" ", "_", "-"}:
                    result += f"{temp_char}"
                    i += 1
                    temp_char = temp[i]
                while comp_char in {" "}:
                    j += 1
                    comp_char = comparator[j]
            else:
                result += comparator[j]
                i += 1
                j += 1
        result = result.replace(" ", "")
        result = re.sub(r"-+", "-", re.sub(r"_+", "_", result))
        return result

    def ensure_unique_pack_dir_name(self, pack_dir: str) -> str:
        """When creating a brand new pack, ensures the name used for the pack directory is unique

        If the proposed pack directory name already exists under the 'content/Packs' directory, then
        a 'V2' is appended to the proposed name. If the proposed name already ends with a digit, the
        digit is incremented. The adjusted pack directory name (if the name wasn't already unique)
        is returned.

        Args:
            pack_dir (str): The proposed name of the pack directory

        Returns:
            str: A unique pack directory name
        """
        while Path(self.packs_dir_path, pack_dir).exists():
            logger.info(
                f"Modifying pack name because pack {pack_dir} already exists in the content repo"
            )
            if (
                len(pack_dir) >= 2
                and pack_dir[-2].lower() == "v"
                and pack_dir[-1].isdigit()
            ):
                # increment by one
                pack_dir = pack_dir[:-1] + str(int(pack_dir[-1]) + 1)
            else:
                pack_dir += "V2"
            logger.info(f'New pack name is "{pack_dir}"')
        return pack_dir

    def unpack_contribution_to_dst_pack_directory(self) -> None:
        """Unpacks the contribution zip's contents to the destination pack directory and performs some cleanup"""
        shutil.unpack_archive(
            filename=self.contribution, extract_dir=str(self.working_dir_path)
        )
        # remove metadata.json file
        Path(self.working_dir_path, "metadata.json").unlink()

    def convert_contribution_dir_to_pack_contents(
        self, unpacked_contribution_dir: str
    ) -> None:
        """Converts a directory and its contents unpacked from the contribution zip file to the appropriate structure

        Example:
            The pack directory after `unpack_contribution_to_dst_pack_directory` has been executed:

            ExamplePack
            ├── automation
            │   └── automation-ExampleAutomation.yml
            ├── integration
            │   └── integration-ExampleIntegration.yml
            ├── playbook
            │   └── playbook-ExamplePlaybook.yml
            ├── report
            │   └── report-ExampleReport.json
            └── reputation
                └── reputation-ExampleReputation.json

            The updated pack directory structure after `convert_contribution_dir_to_pack_contents` has been
            executed, passing the path of .../ExamplePack/integration as the argument, would appear as so:

            ExamplePack
            ├── automation
            │   └── automation-ExampleAutomation.yml
            ├── Integrations
            │   └── integration-ExampleIntegration.yml
            ├── playbook
            │   └── playbook-ExamplePlaybook.yml
            ├── report
            │   └── report-ExampleReport.json
            └── reputation
                └── reputation-ExampleReputation.json

        Args:
            unpacked_contribution_dir (str): The directory to convert
        """
        basename = Path(unpacked_contribution_dir).name
        if basename in ENTITY_TYPE_TO_DIR:
            dst_name = ENTITY_TYPE_TO_DIR.get(basename, "")
            src_path = str(Path(self.working_dir_path, basename))
            dst_path = str(Path(self.working_dir_path, dst_name))
            if Path(dst_path).exists():
                # move src folder files to dst folder
                for _, _, files in os.walk(src_path, topdown=False):
                    for name in files:
                        src_file_path = os.path.join(src_path, name)
                        dst_file_path = os.path.join(dst_path, name)
                        shutil.move(src_file_path, dst_file_path)
                shutil.rmtree(src_path, ignore_errors=True)
            else:
                # replace dst folder with src folder
                shutil.move(src_path, dst_path)

    def format_converted_pack(self) -> None:
        """Runs the demisto-sdk's format command on the pack converted from the contribution zipfile"""
        logger.info(
            f"Executing 'format' on the restructured contribution zip new/modified files at {self.pack_dir_path}"
        )
        from_version = "6.0.0" if self.create_new else ""
        format_manager(
            from_version=from_version,
            no_validate=True,
            update_docker=True,
            assume_answer=True,
            include_untracked=False,
            interactive=False,
        )

    def generate_readme_for_pack_content_item(
        self, yml_path: str, is_contribution: bool = False
    ) -> str:
        """Runs the demisto-sdk's generate-docs command on a pack content item

        Args:
            yml_path: str: Content item yml path.
            is_contribution: bool: Check if the content item is a new integration contribution or not.

        Returns:
            `str` path to the generated `README.md`.
        """
        file_type = find_type(yml_path)
        file_type = file_type.value if file_type else file_type
        if file_type == "integration":
            generate_integration_doc(
                yml_path, is_contribution=is_contribution, examples=None
            )
        elif file_type == "script":
            generate_script_doc(input_path=yml_path, examples=None, use_graph=False)
        elif file_type == "playbook":
            generate_playbook_doc(yml_path)

        dir_output = os.path.dirname(os.path.realpath(yml_path))
        if file_type == "playbook":
            readme_path = yml_path.replace(".yml", "_README.md")
        else:
            readme_path = os.path.join(dir_output, PACKS_README_FILE_NAME)

        return readme_path

    def generate_readmes_for_new_content_pack(self, is_contribution=False) -> List[str]:
        """
        Generate the readme files for a new content pack.
        Update the pack README file if such information was given (self.pack_readme != None).

        Returns:
        - `List[str]` with the paths to all the generated `README`s.
        """

        readmes_generated: List[str] = []
        for pack_subdir in get_child_directories(str(self.working_dir_path)):
            basename = Path(pack_subdir).name
            if basename in {SCRIPTS_DIR, INTEGRATIONS_DIR}:
                directories = get_child_directories(pack_subdir)
                for directory in directories:
                    files = get_child_files(directory)
                    for file in files:
                        file_name = Path(file).name
                        if (
                            file_name.startswith("integration-")
                            or file_name.startswith("script-")
                            or file_name.startswith("automation-")
                        ):
                            unified_file = file
                            readme = self.generate_readme_for_pack_content_item(
                                unified_file, is_contribution
                            )
                            readmes_generated.append(readme)
                            Path(unified_file).unlink()
            elif basename == PLAYBOOKS_DIR:
                files = get_child_files(pack_subdir)
                for file in files:
                    file_name = Path(file).name
                    if file_name.startswith("playbook") and file_name.endswith(".yml"):
                        readme = self.generate_readme_for_pack_content_item(file)
                        readmes_generated.append(readme)

        if self.pack_readme:
            Path(self.working_dir_path, PACKS_README_FILE_NAME).write_text(
                self.pack_readme
            )

        return readmes_generated

    def rearranging_before_conversion(self) -> None:
        """
        Rearrange content items that were mapped incorrectly by the server zip
          - indicatorfields rearranged to be under indicatorfield directory instead of incidentfields.
        """
        unpacked_contribution_dirs = get_child_directories(str(self.working_dir_path))
        for unpacked_contribution_dir in unpacked_contribution_dirs:
            dir_name = Path(unpacked_contribution_dir).name

            # incidentfield directory may contain indicator-fields files
            if dir_name == FileType.INCIDENT_FIELD.value:
                dst_ioc_fields_dir = str(
                    Path(self.working_dir_path, FileType.INDICATOR_FIELD.value)
                )
                src_path = str(Path(self.working_dir_path, dir_name))

                for file in os.listdir(src_path):
                    if file.startswith(FileType.INDICATOR_FIELD.value):
                        # At first time, create another dir for all indicator-fields files and move them there
                        Path(dst_ioc_fields_dir).mkdir(parents=True, exist_ok=True)
                        file_path = str(Path(self.working_dir_path, dir_name, file))
                        shutil.move(file_path, dst_ioc_fields_dir)  # type: ignore

                # If there were only indicatorfiled files, the original folder will remain empty, so we will delete it
                if len(os.listdir(src_path)) == 0:
                    shutil.rmtree(src_path, ignore_errors=True)

    def convert_contribution_to_pack(self):
        """Create or updates a pack in the content repo from the contents of a contribution zipfile"""
        try:
            # only create pack_metadata.json and base pack files if creating a new pack
            if self.create_new:
                # create pack metadata file
                with zipfile.ZipFile(self.contribution) as zipped_contrib:
                    with zipped_contrib.open("metadata.json") as metadata_file:
                        logger.info(
                            f"Pulling relevant information from {metadata_file.name}"
                        )
                        metadata = json.loads(metadata_file.read())
                        self.create_metadata_file(metadata)
                # create base files
                self.create_pack_base_files()

            # We need to fix the modified
            # content items paths and filenames and generate a new zip
            # with a mapping of the changes done.
            # We then set the contribution zip to the modified one.
            modified_contribution_zip, mapping = self.fixup_detected_content_items()
            self.contribution = modified_contribution_zip

            # unpack
            self.unpack_contribution_to_dst_pack_directory()
            # convert
            self.rearranging_before_conversion()
            unpacked_contribution_dirs = get_child_directories(
                str(self.working_dir_path)
            )
            for unpacked_contribution_dir in unpacked_contribution_dirs:
                self.convert_contribution_dir_to_pack_contents(
                    unpacked_contribution_dir
                )
            # extract to package format
            for pack_subdir in get_child_directories(self.working_dir_path):
                basename = Path(pack_subdir).name
                if basename in {SCRIPTS_DIR, INTEGRATIONS_DIR}:
                    self.content_item_to_package_format(
                        pack_subdir,
                        del_unified=(not self.create_new),
                        source_mapping=mapping,
                    )

            self.create_contribution_items_version_note()

            # Create documentation

            generated_readmes: List[str] = []

            # If it's a new Pack, we recursively create READMEs for all content items
            if self.create_new:
                logger.info("Creating documentation for a new Pack...")
                generated_readmes = self.generate_readmes_for_new_content_pack(
                    is_contribution=True
                )

            # If it's an existing Pack, we need to iterate over
            # all content items that were added and create READMEs for them
            else:
                logger.info("Creating documentation for existing Pack...")
                contributed_ymls = glob.glob(
                    f"{self.working_dir_path}/**/*.yml", recursive=True
                )
                for yml in contributed_ymls:
                    generated_readme = self.generate_readme_for_pack_content_item(
                        yml_path=yml, is_contribution=True
                    )

                    logger.debug(f"{generated_readme=}")

                    # Construct the path to the README from the content path
                    try:
                        # If it's a README for a playbook
                        # e.g. 'Playbooks/playbook-New-PB_README.md'
                        if PLAYBOOKS_DIR in generated_readme:
                            # e.g. 'playbook-New-PB_README.md'
                            playbook_readme_filename = Path(generated_readme).name
                            relative_path = os.path.join(
                                PLAYBOOKS_DIR, playbook_readme_filename
                            )

                            # TODO move to debug
                            logger.info(
                                f"Generated README for Playbook with '{relative_path}'"
                            )
                        # If it's either a script or integration, the absolute path will be:
                        # e.g. 'Integrations/HelloWorld/README.md'
                        else:
                            # e.g. 'Integrations'
                            content_item_type = Path(generated_readme).parts[-3]
                            # e.g. 'HelloWorld'
                            content_item_name = Path(generated_readme).parts[-2]
                            relative_path = os.path.join(
                                content_item_type,
                                content_item_name,
                                PACKS_README_FILE_NAME,
                            )

                            # TODO move to debug
                            logger.info(
                                f"Generated README for {content_item_type} with '{relative_path}'"
                            )

                        # e.g. 'tmp_path/to/content/Packs/HelloWorld/Playbooks/playbook-New-PB_README.md'
                        relative_path_from_content = os.path.join(
                            str(self.pack_dir_path), relative_path
                        )

                        # TODO move to debug
                        logger.info(
                            f"Adding '{relative_path_from_content}' to list of generated READMEs..."
                        )
                        generated_readmes.append(relative_path_from_content)

                    except IndexError:
                        logger.warning(
                            f"Failed to construct relative path of the generated README '{generated_readme}'. Skipping addition of README to list of generated READMEs..."
                        )
                        continue

            self.readme_files = generated_readmes

        except Exception as e:
            logger.info(
                f"Creating a Pack from the contribution zip failed with error: {e}\n {traceback.format_exc()}",
                "red",
            )
        finally:
            if self.contrib_conversion_errs:
                logger.info(
                    "The following errors occurred while converting unified content YAMLs to package structure:"
                )
                logger.info(
                    textwrap.indent("\n".join(self.contrib_conversion_errs), "\t")
                )

    @staticmethod
    def extract_pack_version(script: Optional[str]) -> str:
        """
        extract the pack version from script if exists, returns 0.0.0 if version was not found.
        """
        if script:
            try:
                if pack_version_reg := re.search(
                    r"(?:###|//) pack version: (\d+\.\d+\.\d+)", script
                ):
                    return pack_version_reg.groups()[0]
            except Exception as e:
                logger.warning(f"Failed extracting pack version from script: {e}")
        return "0.0.0"

    def create_contribution_items_version_note(self):
        """
        creates note that can be paste on the created PR containing the
        contributed item versions.
        """
        if self.contribution_items_version:
            self.contribution_items_version_note = "> **Warning**\n"
            self.contribution_items_version_note += (
                "> The changes in the contributed files were not made on the "
                "most updated pack versions\n"
            )
            self.contribution_items_version_note += "> | **Item Name** | **Contribution Pack Version** | **Latest Pack Version**\n"
            self.contribution_items_version_note += (
                "> | --------- | ------------------------- | -------------------\n"
            )

            for item_name, item_versions in self.contribution_items_version.items():
                self.contribution_items_version_note += (
                    f"> | {item_name} | {item_versions.get('contribution_version', '')} | "
                    f"{item_versions.get('latest_version', '')}\n"
                )

            self.contribution_items_version_note += (
                ">\n"
                "> **For the Reviewer:**\n"
                "> 1. Currently the diff you see on Github is between the contribution original version and the contribution changes "
                "since the contribution was made on an outdated version.\n"
                "> 2. You will see the diff between the contribution changes and Content master only after you fix all conflicts.\n"
                "> 3. Fix conflicts only after completing the review process "
                "and once the contributor has finished resubmitting changes.\n"
                "> For more details see "
                "Confluence page [link](https://confluence-dc.paloaltonetworks.com/display/DemistoContent/Conducting+Code+Review).\n"
            )

    def content_item_to_package_format(
        self,
        content_item_dir: str,
        del_unified: bool = True,
        source_mapping: Dict[str, Dict[str, str]] = None,
    ):
        """
        Iterate over the YAML files in a directory and create packages (a containing directory and
        component files) from the YAMLs of integrations and scripts

        Args:
            content_item_dir (str): Path to the directory containing the content item YAML file(s)
            del_unified (bool): Whether to delete the unified yaml the package was extracted from
            source_mapping (Union[Dict], optional): Can be used when updating an existing pack and
                the package directory of a content item is not what would ordinarily be set by the
                `demisto-sdk` `split` command. Sample value would be,
                `{'integration-AbuseIPDB.yml': {'containing_dir_name': 'AbuseDB', 'base_name': 'AbuseDB'}}`
                - the split command would create a containing directory of `AbuseIPDB` for the file
                `integration-AbuseIPDB.yml` and we need the containing directory of the package to match
                what already exists in the repo.
        """
        child_files = get_child_files(content_item_dir)
        for child_file in child_files:
            cf_name_lower = Path(child_file).name.lower()
            if cf_name_lower.startswith(
                (SCRIPT, AUTOMATION, INTEGRATION)
            ) and cf_name_lower.endswith("yml"):
                content_item_file_path = child_file
                file_type = find_type(content_item_file_path)
                file_type = file_type.value if file_type else file_type
                try:
                    child_file_name = Path(child_file).name
                    if source_mapping and child_file_name in source_mapping.keys():
                        child_file_mapping = source_mapping.get(child_file_name, {})
                        base_name = child_file_mapping.get("base_name", "")
                        containing_dir_name = child_file_mapping.get(
                            "containing_dir_name", ""
                        )
                        # for legacy unified yamls in the repo, their containing directory will be that of their
                        # entity type directly instead of the typical package format. For those cases, we need the
                        # extractor to auto create the containing directory. An example would be -
                        # 'content/Packs/AbuseDB/Scripts/script-AbuseIPDBPopulateIndicators.yml'
                        autocreate_dir = containing_dir_name == ENTITY_TYPE_TO_DIR.get(
                            file_type, ""
                        )
                        output_dir = str(
                            Path(
                                self.working_dir_path,
                                ENTITY_TYPE_TO_DIR.get(file_type, ""),
                            )
                        )
                        if not autocreate_dir:
                            output_dir = os.path.join(output_dir, containing_dir_name)
                        os.makedirs(output_dir, exist_ok=True)
                        extractor = YmlSplitter(
                            input=content_item_file_path,
                            file_type=file_type,
                            output=output_dir,
                            no_readme=True,
                            base_name=base_name,
                            no_auto_create_dir=(not autocreate_dir),
                        )

                    else:
                        extractor = YmlSplitter(
                            input=content_item_file_path,
                            file_type=file_type,
                            output=content_item_dir,
                            no_readme=True,
                        )
                    try:
                        content_item = BaseContent.from_path(
                            Path(content_item_file_path)
                        )
                        if isinstance(content_item, IntegrationScript):
                            script = content_item.code
                            contributor_item_version = self.extract_pack_version(script)
                            current_pack_version = get_pack_metadata(
                                file_path=str(self.pack_dir_path)
                            ).get("currentVersion", "0.0.0")
                            if contributor_item_version != "0.0.0" and Version(
                                current_pack_version
                            ) > Version(contributor_item_version):
                                self.contribution_items_version[content_item.name] = {
                                    "contribution_version": contributor_item_version,
                                    "latest_version": current_pack_version,
                                }

                    except Exception as e:
                        logger.warning(
                            f"Could not parse {content_item_file_path} contribution item version: {e}.",
                        )
                    extractor.extract_to_package_format(
                        executed_from_contrib_converter=True
                    )
                    self.api_module_path = extractor.api_module_path
                except Exception as e:
                    err_msg = (
                        f'Error occurred while trying to split the unified YAML "{content_item_file_path}" '
                        f'into its component parts.\nError: "{e}"'
                    )
                    self.contrib_conversion_errs.append(err_msg)
                finally:
                    output_path = extractor.get_output_path()
                    if self.create_new:
                        # Moving the unified file to its package.
                        shutil.move(content_item_file_path, output_path)
                    if del_unified:
                        Path(content_item_file_path).unlink(missing_ok=True)
                        moved_unified_dst = os.path.join(output_path, child_file_name)
                        Path(moved_unified_dst).unlink(missing_ok=True)

    def create_pack_base_files(self):
        """
        Create empty 'README.md', '.secrets-ignore', and '.pack-ignore' files that are expected
        to be in the base directory of a pack
        """
        logger.info("Creating pack base files")
        Path(self.working_dir_path, PACKS_README_FILE_NAME).touch()

        Path(self.working_dir_path, ".secrets-ignore").touch()

        Path(self.working_dir_path, ".pack-ignore").touch()

    def create_metadata_file(self, zipped_metadata: Dict) -> None:
        """Create the pack_metadata.json file in the base directory of the pack

        Args:
            zipped_metadata (Dict): The metadata that came in the zipfile
        """
        metadata_dict = {}

        # a description passed on the cmd line should take precedence over one pulled
        # from contribution metadata
        metadata_dict["description"] = self.description or zipped_metadata.get(
            "description"
        )
        metadata_dict["name"] = self.name
        metadata_dict["author"] = self.author or zipped_metadata.get("author", "")
        metadata_dict["support"] = "community"
        metadata_dict["url"] = zipped_metadata.get("supportDetails", {}).get(
            "url", MARKETPLACE_LIVE_DISCUSSIONS
        )
        metadata_dict["categories"] = (
            zipped_metadata.get("categories")
            if zipped_metadata.get("categories")
            else []
        )
        metadata_dict["tags"] = (
            zipped_metadata.get("tags") if zipped_metadata.get("tags") else []
        )
        metadata_dict["useCases"] = (
            zipped_metadata.get("useCases") if zipped_metadata.get("useCases") else []
        )
        metadata_dict["keywords"] = (
            zipped_metadata.get("keywords") if zipped_metadata.get("keywords") else []
        )
        metadata_dict["githubUser"] = [self.gh_user] if self.gh_user else []
        metadata_dict["marketplaces"] = (
            zipped_metadata.get("marketplaces") or MARKETPLACES
        )
        metadata_dict = ContributionConverter.create_pack_metadata(data=metadata_dict)
        metadata_path = str(Path(self.working_dir_path, "pack_metadata.json"))
        with open(metadata_path, "w") as pack_metadata_file:
            json.dump(metadata_dict, pack_metadata_file, indent=4)

    @staticmethod
    def create_pack_metadata(data: Dict = None) -> Dict:
        """Builds pack metadata JSON content.

        Args:
            data (dict): Dictionary keys and value to insert into the pack metadata.

        Returns:
            Dict. Pack metadata JSON content.
        """
        pack_metadata = {
            "name": "## FILL MANDATORY FIELD ##",
            "description": "## FILL MANDATORY FIELD ##",
            "support": XSOAR_SUPPORT,
            "currentVersion": PACK_INITIAL_VERSION,
            "author": XSOAR_AUTHOR,
            "url": XSOAR_SUPPORT_URL,
            "email": "",
            "created": datetime.utcnow().strftime(ContributionConverter.DATE_FORMAT),
            "categories": [],
            "tags": [],
            "useCases": [],
            "keywords": [],
            "marketplaces": [],
        }

        if data:
            pack_metadata.update(data)

        return pack_metadata

    def execute_update_rn(self):
        """
        Bump the pack version in the pack metadata according to the update type
        and create a release-note file using the release-notes text.

        """
        try:
            rn_mng = UpdateReleaseNotesManager(
                user_input=self.dir_name,
                update_type=self.update_type,
            )
            rn_mng.manage_rn_update()
            if rn_mng.rn_path:
                self.replace_RN_template_with_value(rn_mng.rn_path[0])
        except Exception:
            logger.error("Failed updating release notes", exc_info=True)

    def format_user_input(self) -> Dict[str, str]:
        """
        Replace the content item name with the content item display name if exists
        to match the template that being generated by the UpdateRN class by calling
        the function get_display_name(file_path)

        Build a dictionary with the release notes text per content item detected.

        Returns:
            Dict: Key is content item name, value is release note entry
        """
        entity_identifier = "##### "
        content_item_type_identifier = "#### "
        rn_per_content_item: dict = defaultdict(str)
        entity_name = "NonEntityRelated"

        items_path = {
            content_item.get("source_id"): content_item.get("source_file_name")
            for content_item in self.detected_content_items
        }

        for line in filter(None, self.release_notes.splitlines()):
            if line.startswith(entity_identifier):
                entity_name = line.lstrip(entity_identifier)
                if items_path.get(entity_name):
                    entity_name = get_display_name(items_path[entity_name])
            elif not line.startswith(content_item_type_identifier):
                rn_per_content_item[entity_name] = (
                    rn_per_content_item[entity_name] + line + "\n"
                )
        return rn_per_content_item

    def replace_RN_template_with_value(self, rn_path: str):
        """
        Replace the release notes template for a given release-note file path
        with the contributor's text.
        Will only affect the detected content items template text.
        New items rn entries and updated docker image entries for the detected items won't get changed.

        Args:
            rn_path: path to the rn file created.
        """
        entity_identifier = "##### "
        new_entity_identifier = "##### New: "
        template_text = "%%UPDATE_RN%%"

        rn_per_content_item = self.format_user_input()

        with open(rn_path, "r+") as rn_file:
            lines = rn_file.readlines()
            for index in range(len(lines)):
                previous_line = get_previous_nonempty_line(lines, index)
                if template_text in lines[index] or previous_line.startswith(
                    new_entity_identifier
                ):
                    # when contributing a new entity to existing pack, the release notes will look something like that:
                    # "##### New: entity name". The following code will extract the entity name in each case.
                    if previous_line.startswith(new_entity_identifier):
                        template_entity = previous_line.lstrip(
                            new_entity_identifier
                        ).rstrip("\n")
                    else:
                        template_entity = previous_line.lstrip(
                            entity_identifier
                        ).rstrip("\n")
                    curr_content_items = rn_per_content_item.get(template_entity)
                    if curr_content_items:
                        lines[index] = curr_content_items

            rn_file.seek(0)
            rn_file.writelines(lines)
            rn_file.truncate()

    def get_source_integration_display_field(
        self, src_integration_yml_path: str
    ) -> Optional[str]:
        """Fetch the value of the 'display' field from the source integration yaml

        Args:
            src_integration_yml_path (AnyStr): The path to the source integration yaml file

        Returns:
            Optional[str]: The value of the 'display' field if found, otherwise None
        """
        exists = Path(src_integration_yml_path).exists()
        is_file = Path(src_integration_yml_path).is_file()
        is_yaml = os.path.splitext(src_integration_yml_path)[1] == ".yml"
        if exists and is_file and is_yaml:
            ryaml = YAML_Handler()
            with open(src_integration_yml_path, "r") as df:
                data_obj = ryaml.load(df)
                display_field = data_obj.get("display")
                return display_field
        else:
            path_as_string = str(src_integration_yml_path)
            if not exists:
                logger.warning(
                    f'"{path_as_string}" was not found to exist in the local file system.'
                )
            elif not is_file:
                logger.warning(f'"{path_as_string}" was not found to be a file.')
            else:
                logger.warning(f'"{path_as_string}" was not found to be a yaml file.')
            logger.warning(
                'Therefore skipping fetching the "display" field from the source integration.'
            )
            return None

    def fixup_detected_content_items(
        self,
    ) -> Tuple[str, Dict[str, Dict[str, str]]]:
        """Create new zip from old zip, modifying the files that need to be modified

        Returns:
            Tuple[str, Dict[str, Dict[str, str]]]: The path to the updated zip file, and the mapping of zip's content file
                names to eachs associated basename and containing directory name
        """
        id_to_data = {
            id_val: info_dict
            for info_dict in self.detected_content_items
            if (id_val := info_dict.get("id"))
        }
        integrations_path_pattern = r"^Packs/\S+?/Integrations/.*"
        for info_dict in id_to_data.values():
            source_file_path = info_dict.get("source_file_name", "")
            if re.search(integrations_path_pattern, source_file_path):
                fetched_display_field = self.get_source_integration_display_field(
                    Path(self.packs_dir_path).parent / source_file_path
                )
                if fetched_display_field:
                    info_dict["source_display"] = fetched_display_field
        ids_to_modify = id_to_data.keys()

        filename_to_basename_and_containing_dir = {}

        ryaml = YAML_Handler()
        modified_contribution_zip_path = os.path.join(
            self.working_dir_path, "modified_contribution.zip"
        )
        tmp_zf = ZipFile(modified_contribution_zip_path, "w")
        with ZipFile(self.contribution, "r") as zf:
            for item in zf.infolist():
                if item.filename.endswith(".yml"):
                    data_worker: Any = ryaml
                elif item.filename.endswith(".json"):
                    data_worker = json
                else:
                    continue
                with zf.open(item, "r") as df:
                    data_obj = data_worker.load(df)
                content_id = (
                    data_obj["commonfields"].get("id", "")
                    if "commonfields" in data_obj.keys()
                    else data_obj.get("id", "")
                )
                # replace fields with originals
                if content_id in ids_to_modify:
                    replacement_info = id_to_data.get(content_id, {})
                    original_name = replacement_info.get("source_name", "")
                    original_id = replacement_info.get("source_id", "")
                    original_file_path = replacement_info.get("source_file_name", "")
                    original_display = replacement_info.get("source_display", "")
                    data_obj["name"] = original_name
                    if (
                        (display := data_obj.get("display", ""))
                        and original_display
                        and display != original_display
                    ):
                        # should only occur for integration yamls
                        data_obj["display"] = original_display
                    if "commonfields" in data_obj.keys():
                        data_obj["commonfields"]["id"] = original_id
                    else:
                        data_obj["id"] = original_id
                    # wipe source fields
                    for source_field in self.SOURCE_FIELD_NAMES.intersection(
                        set(data_obj.keys())
                    ):
                        if source_field == "sourceClassifierId":
                            data_obj[source_field] = ""
                        else:
                            del data_obj[source_field]

                    original_file_name = Path(original_file_path).name
                    if any(
                        original_file_name.startswith(prefix.value)
                        for prefix in ContentItems
                    ):
                        # deal with the prefixes that have '-' in the prefix themselves
                        if original_file_name.startswith(
                            (
                                "classifier-mapper-incoming-",
                                "classifier-mapper-outgoing-",
                            )
                        ):
                            long_classifier_prefix = len("classifier-mapper-incoming-")
                            original_file_name = original_file_name[
                                long_classifier_prefix - 1 :
                            ]
                        else:
                            prefix = f'{original_file_name.split("-")[0]}-'
                            if any(
                                prefix.casefold().startswith(item.value)
                                for item in ContentItems
                            ):
                                original_file_name = original_file_name.replace(
                                    prefix, ""
                                )
                    file_name_prefix = Path(item.filename).name.split("-")[0].casefold()
                    file_dir = os.path.dirname(item.filename)
                    # rename file
                    new_file_name = f"{file_name_prefix}-{original_file_name}"
                    new_file_path = os.path.join(file_dir, new_file_name)
                    # map new file to source basename and source containing directory name
                    filename_to_basename_and_containing_dir[new_file_name] = {
                        "base_name": original_file_name.replace(".yml", ""),
                        "containing_dir_name": Path(
                            os.path.dirname(original_file_path)
                        ).name,
                    }

                    formatted_data_dump = StringIO()
                    data_worker.dump(data_obj, formatted_data_dump)
                    tmp_zf.writestr(new_file_path, formatted_data_dump.getvalue())
                else:
                    tmp_zf.writestr(item, zf.read(item.filename))
        return modified_contribution_zip_path, filename_to_basename_and_containing_dir

    def delete_contrib_zip(self):
        """
        Delete the contribution zip.
        """

        Path(self.contribution).unlink()
