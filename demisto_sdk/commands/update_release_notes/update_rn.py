"""
This script is used to create a release notes template
"""

import copy
import errno
import os
import re
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST,
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
    EVENT_COLLECTOR,
    IGNORED_PACK_NAMES,
    PB_RELEASE_NOTES_FORMAT,
    RN_HEADER_BY_FILE_TYPE,
    SIEM_ONLY_ENTITIES,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import (
    YAMLContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import (
    YAMLContentUnifiedObject,
)
from demisto_sdk.commands.common.content.objects_factory import (
    TYPE_CONVERSION_BY_FileType,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_api_module_dependencies_from_graph,
    get_api_module_ids,
    get_content_path,
    get_display_name,
    get_from_version,
    get_json,
    get_latest_release_notes_text,
    get_pack_name,
    get_remote_file,
    get_yaml,
    pack_name_to_path,
    run_command,
)
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import (
    Argument,
    Command,
    Integration,
    Parameter,
)
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script


class content_type(Enum):
    PARAMETER = "parameter"
    COMMAND = "command"
    ARGUMENT = "argument"


NEW_RN_TEMPLATE = "- New: Added a new {type}- {name} that {description}\n"
GENERAL_DEPRECATED_RN = "- Deprecated the **{name}** {type}. {replacement}.\n"
GENERAL_BC = "- Deleted the **{name}** {type}.\n"
DEPRECATED_ARGUMENT = (
    "- Deprecated the *{name}* {type} inside the **{command_name}** command.\n"
)
ARGUMENT_BC = "- Updated the **{command_name}** command to not use the *{argument_name}* argument.\n"
DEPRECATED_CONTENT_ITEM_RN = "- Deprecated. {replacement}.\n"
GENERAL_UPDATE_RN = (
    "- Updated the {name} {type} to %%UPDATE_CONTENT_ITEM_CHANGE_DESCRIPTION%%.\n"
)
ADDED_ARGUMENT_RN = (
    "- Added support for *{name}* argument in the **{parent}** command.\n"
)
ADDED_CONTENT_RN = "- Added support for **{name}** {content_type}{extra_description}\n"
NEW_COMMANDS_RN = "\n- Added the following commands:\n"


def get_description(content_item):
    if isinstance(content_item, Parameter):
        return content_item.additionalinfo or ""
    # in cases content item is instance of argument, command, integration, script
    return content_item.description or ""


def get_name(content_item):
    if isinstance(content_item, Parameter):
        return content_item.display or content_item.displaypassword
    # in cases content item is instance of argument, command, integration, script
    return content_item.name


def get_deprecated_comment_from_desc(description: str) -> str:
    """
    find deprecated comment from description
    Args:
        description: The yml description

    Returns:
        If a deprecated description is found return it for rn.
    """
    deprecate_line_with_replacement = re.findall(DEPRECATED_DESC_REGEX, description)
    deprecate_line_no_replacement = re.findall(
        DEPRECATED_NO_REPLACE_DESC_REGEX, description
    )

    deprecate_line = deprecate_line_with_replacement + deprecate_line_no_replacement
    return deprecate_line[0] if deprecate_line else ""


def create_content_item_object(
    path: str, prev_ver: Union[str, None], is_new_file: bool
) -> Optional["BaseContent"]:
    """
    Generate yml files from master and from the current branch
    Args:
        path: The requested file path
        prev_ver: the git sha from which to extract the previous version
        is_new_file: is the update occurred on a new file

    Returns:
        Two YML objects, the first of the yml at master (old yml) and the second from the current branch (new yml)
    """
    path_object = Path(path)
    if not path_object.is_file():
        logger.info(
            f'<yellow>Cannot get content item name: "{path}" file does not exist</yellow>'
        )
        return None
    changed_content_item = None
    try:
        changed_content_item = BaseContent.from_path(path_object)
        if changed_content_item and prev_ver and not is_new_file:
            try:
                old_obj = BaseContent.from_path(
                    path_object, git_sha=prev_ver, raise_on_exception=True
                )
                changed_content_item.old_base_content_object = old_obj
            except Exception as e:
                logger.error(
                    f"<red>Cannot create old base content object from {prev_ver} with error {e}.</error>"
                )
                return None
        return changed_content_item
    except Exception as e:
        logger.error(
            f"<red>Cannot create content object in path {path} with error {e}.</error>"
        )
        return None


def create_rn_for_deleted_content(
    old_content_dict: dict[str, Union[Parameter, Argument, Command]],
    new_content_dict: dict[str, Union[Parameter, Argument, Command]],
    type,
    parent_name=None,
):
    """Generates release notes for deleted content items.

    Args:
        old_content_dict (dict[str, Any]): A dictionary of Parameter/Argument/Command in the current version,
                                           where keys are item names and values are the objects.
        new_content_dict (dict[str, Any]): A dictionary of Parameter/Argument/Command after local updates,
                                           where keys are item names and values are the objects.
        type (str): The type of the content item.
        parent_name (str, optional): The name of the parent command (in cases type is an argument), else None.

    Returns:
        str: A release note describing the deleted content items.
    """
    rn = ""
    deleted_content_names = set(old_content_dict.keys()) - set(new_content_dict.keys())
    for deleted_content_name in deleted_content_names:
        name = get_name(old_content_dict[deleted_content_name])
        if type == content_type.ARGUMENT and parent_name:
            rn += ARGUMENT_BC.format(command_name=parent_name, argument_name=name)
        else:
            rn += GENERAL_BC.format(name=name, type=type.value)
        logger.info(
            f"<yellow>Please add a breaking changes json file for deleting the {name} {type.value}</yellow>"
        )
    return rn


def generate_content_deprecation_rn(
    name: str,
    new_content: Union[Parameter, Argument, Command],
    old_content: Union[Parameter, Argument, Command],
    content_type: content_type,
    parent: Union[str, None] = None,
) -> str:
    """Generates release notes for deprecated content of an existing content item.

    Args:
        name (str): The name of the content item being deprecated.
        old_content (Union[Parameter, Argument, Command]): The previous version of the content item.
        new_content (Union[Parameter, Argument, Command]): The updated version of the content item.
        content_type (content_type): The type of the content item (e.g., argument, command, parameter).
        parent (Union[str, None], optional): The name of the parent content item, if applicable
                                             (e.g., the command name for a deprecated argument). Defaults to None.

    Returns:
        str: A formatted release note indicating the deprecation of content of an existing content item.
        Returns an empty string if no deprecation is detected.
    """
    if not isinstance(new_content, Parameter) and not isinstance(
        old_content, Parameter
    ):
        if new_content.deprecated and not old_content.deprecated:
            if isinstance(new_content, Argument) and parent:
                return DEPRECATED_ARGUMENT.format(
                    name=name, type=content_type.value, command_name=parent
                )
            return GENERAL_DEPRECATED_RN.format(
                name=name,
                type=content_type.value,
                replacement=(
                    get_deprecated_comment_from_desc(get_description(new_content))
                    or "Use %%% instead"
                ),
            )
    return ""


def generate_required_content_rn(
    name: str,
    new_content: Union[Parameter, Argument, Command],
    old_content: Union[Parameter, Argument, Command],
    content_type: content_type,
) -> str:
    """Generates release notes for content items that have been updated to be required.

    Args:
        name (str): The name of the content item being updated.
        new_content (Union[Parameter, Argument, Command]): The updated version of the content item.
        old_content (Union[Parameter, Argument, Command]): The previous version of the content item.
        content_type (content_type): The type of the content item (e.g., parameter, argument, command).

    Returns:
        str: A formatted release note indicating that the specified content item is now required.
             Returns an empty string if no changes to the "required" status are detected.
    """
    if (
        (
            (isinstance(new_content, Parameter) and isinstance(old_content, Parameter))
            or (isinstance(new_content, Argument) and isinstance(old_content, Argument))
        )
        and new_content.required
        and not old_content.required
    ):
        return f"- Updated the **{name}** {content_type.value} to be required.\n"
    return ""


def generate_new_content_rn(
    name: str,
    new_content: Union[Parameter, Argument, Command],
    content_type: content_type,
    parent: Union[str, None] = None,
) -> str:
    """Generates release notes for newly added content of content items.

    Args:
        item_name (str): The name of the new content item.
        new_content_data (dict[str, Any]): The data for the new content item.
        content_type (content_type): The type of the content item (e.g., parameter, argument, command).
        parent_name (str | None, optional): The name of the parent content item, if applicable (e.g., command name for arguments).

    Returns:
        str: A formatted release note describing the addition of the content item.
    """
    description = get_description(new_content).replace("-", "").lower()
    display_name = get_name(new_content)
    if isinstance(new_content, Argument) and parent:
        return ADDED_ARGUMENT_RN.format(name=name, parent=parent)
    extra_description = f" that {description.rstrip('.')}." if description else "."
    return ADDED_CONTENT_RN.format(
        name=display_name,
        content_type=content_type.value,
        extra_description=extra_description,
    )


def create_rn_for_added_or_updated_content(
    old_content_dict: dict[str, Union[Parameter, Argument, Command]],
    new_content_dict: dict[str, Union[Parameter, Argument, Command]],
    type: content_type,
    parent_name: Union[str, None],
) -> str:
    """Generates release notes for added or updated content in content items.

    Args:
        old_content_dict (dict[str, Union[Parameter, Argument, Command]]): A dictionary of Parameter/Argument/Command in the current version,
                                           where keys are item names and values are the objects.
        new_content_dict (dict[str, Union[Parameter, Argument, Command]]): A dictionary of Parameter/Argument/Command after local updates,
                                           where keys are item names and values are the objects.
        type (content_type): The type of the content item.
        parent_name (str | None): The name of the parent content item, if applicable
                                  (used for arguments within commands).

    Returns:
        str: A release note describing the added or updated content items.
    """
    rn = ""
    new_content_names = set(new_content_dict.keys()) - set(old_content_dict.keys())
    old_existing_content_names = set(new_content_dict.keys()) - new_content_names
    # loop new content of an existing content item
    for new_content_name in new_content_names:
        rn += generate_new_content_rn(
            new_content_name, new_content_dict[new_content_name], type, parent_name
        )
    # loop Optional(updated) content of an existing content item
    for old_existing_content_name in old_existing_content_names:
        old_content_object = old_content_dict[old_existing_content_name]
        new_content_object = new_content_dict[old_existing_content_name]
        rn += generate_content_deprecation_rn(
            old_existing_content_name,
            new_content_object,
            old_content_object,
            type,
            parent_name,
        )
        rn += generate_required_content_rn(
            old_existing_content_name, new_content_object, old_content_object, type
        )
        if isinstance(new_content_object, Command) and isinstance(
            old_content_object, Command
        ):
            # loop over arguments list of a command
            rn += compare_content_item_changes(
                old_content_object.args,
                new_content_object.args,
                content_type.ARGUMENT,
                old_existing_content_name,
            )

    return rn


def compare_content_item_changes(
    old_content_item_data: Union[list[Parameter], list[Argument], list[Command]],
    new_content_item_data: Union[list[Parameter], list[Argument], list[Command]],
    type,
    parent_name=None,
):
    """Compares old and new versions of a content in content item to generate release notes.

    Args:
        old_content_item_data (Union[list[Parameter], list[Argument], list[Command]]): A list of ("BaseModel") representing the old content item data.
        new_content_item_data (Union[list[Parameter], list[Argument], list[Command]]): A list of ("BaseModel") representing the new content item data.
        type (str): The type of the content item.
        parent_name (str, optional): The name of the parent content item, if applicable.

    Returns:
        str: A release note describing changes, including deleted, added, updated content.
    """
    rn = ""
    old_content_dict = {old_data.name: old_data for old_data in old_content_item_data}
    new_content_dict = {new_data.name: new_data for new_data in new_content_item_data}
    # search for deleted content of an existing content item
    rn += create_rn_for_deleted_content(
        old_content_dict, new_content_dict, type, parent_name
    )
    # search for added and updated content of an existing content item
    rn += create_rn_for_added_or_updated_content(
        old_content_dict, new_content_dict, type, parent_name
    )
    return rn


def generate_deprecated_content_item_rn(
    changed_content_object: Union[Integration, Script, Playbook],
):
    """Checks if a content item of type integration/script/playbook is deprecated and generates a deprecation release note if applicable.

    Args:
        changed_content_object: Content object of type integration/script/playbook.

    Returns:
        The deprecated content item rn.
    """
    deprecated_rn = ""
    if (
        changed_content_object
        and isinstance(changed_content_object, Integration)
        or isinstance(changed_content_object, Script)
        or isinstance(changed_content_object, Playbook)
    ):
        deprecated_rn += get_deprecated_rn(changed_content_object)
    return deprecated_rn


def generate_rn_for_updated_content_items(
    changed_content_object: Union[Integration, Script, Playbook],
):
    """Generates a release note description for updated content items.

    Args:
        changed_content_object(Union[Integration, Script, Playbook]): The changed content item object.

    Returns:
        str: A release note description for the updated content item, including deprecation and enhancement details.
    """
    rn_desc = ""
    if changed_content_object:
        # Is the content item deprecated.
        deprecate_rn = generate_deprecated_content_item_rn(changed_content_object)
        if deprecate_rn:
            rn_desc += deprecate_rn
        else:
            rn_desc += generate_rn_for_content_item_updates(changed_content_object)
    return rn_desc


def generate_rn_for_content_item_updates(
    changed_content_object: Union[Integration, Script, Playbook],
):
    """Generates release notes for updates to a specific content item.

    Args:
        changed_content_object(Union[Integration, Script, Playbook]): The changed content item object.

    Returns:
        str: A release note describing the updates made to the content item,
             such as parameter changes, command updates.
    """
    rn_desc = ""
    # if the content item is an integration
    if (
        isinstance(changed_content_object, Integration)
        and changed_content_object.old_base_content_object
        and isinstance(changed_content_object.old_base_content_object, Integration)
    ):
        # searching changes in parameters
        rn_desc += compare_content_item_changes(
            changed_content_object.old_base_content_object.params,
            changed_content_object.params,
            content_type.PARAMETER,
        )
        # searching changes in commands
        rn_desc += compare_content_item_changes(
            changed_content_object.old_base_content_object.commands,
            changed_content_object.commands,
            content_type.COMMAND,
        )
    # if the content item is a script
    elif (
        isinstance(changed_content_object, Script)
        and changed_content_object.old_base_content_object
        and isinstance(changed_content_object.old_base_content_object, Script)
    ):
        # searching changes in arguments
        rn_desc += compare_content_item_changes(
            changed_content_object.old_base_content_object.args,
            changed_content_object.args,
            content_type.ARGUMENT,
        )
    return rn_desc


def get_deprecated_rn(changed_object: Union[Integration, Script, Playbook]):
    """Generates a release note for deprecated content items.

    Args:
        changed_object (Union[Integration, Script, Playbook]): The content object being checked for deprecation status.

    Returns:
        str: A formatted release note indicating the deprecation status of the content item.
             Returns an empty string if the content item is not deprecated or if no changes to the deprecation status are detected.
    """
    if (
        changed_object.old_base_content_object
        and isinstance(
            changed_object.old_base_content_object, (Integration, Script, Playbook)
        )
        and not changed_object.old_base_content_object.deprecated
        and changed_object.deprecated
    ):
        rn_from_description = get_deprecated_comment_from_desc(
            get_description(changed_object)
        )
        return DEPRECATED_CONTENT_ITEM_RN.format(
            replacement=(rn_from_description or "Use %%% instead")
        )
    return ""


class UpdateRN:
    CONTENT_PATH = Path(get_content_path())  # type: ignore[arg-type]

    def __init__(
        self,
        pack_path: str,
        update_type: Union[str, None],
        modified_files_in_pack: set,
        added_files: set,
        specific_version: str = None,
        pre_release: bool = False,
        pack: str = None,
        pack_metadata_only: bool = False,
        text: str = "",
        existing_rn_version_path: str = "",
        is_force: bool = False,
        is_bc: bool = False,
        prev_ver: Optional[str] = "",
    ):
        self.pack = pack if pack else get_pack_name(pack_path)
        self.update_type = update_type
        self.pack_path = pack_path
        # renamed files will appear in the modified list as a tuple: (old path, new path)
        modified_files_in_pack = {
            file_[1] if isinstance(file_, tuple) else file_
            for file_ in modified_files_in_pack
        }
        self.modified_files_in_pack = set()
        for file_path in modified_files_in_pack:
            self.modified_files_in_pack.add(
                self.change_image_or_desc_file_path(
                    (self.CONTENT_PATH / file_path).as_posix()
                )
            )

        self.added_files = added_files
        self.pre_release = pre_release
        self.specific_version = specific_version
        self.existing_rn_changed = False
        self.text = text
        self.existing_rn_version_path = existing_rn_version_path
        self.should_delete_existing_rn = False
        self.pack_metadata_only = pack_metadata_only
        self.is_force = is_force
        git_util = Content.git_util()
        self.main_branch = git_util.handle_prev_ver()[1]
        self.metadata_path = os.path.join(self.pack_path, "pack_metadata.json")
        self.master_version = self.get_master_version()
        self.rn_path = ""
        self.is_bc = is_bc
        self.bc_path = ""
        self.prev_ver = prev_ver

    @staticmethod
    def change_image_or_desc_file_path(file_path: str) -> str:
        """Changes image and description file paths to the corresponding yml file path.
        if a non-image or description file path is given, it remains unchanged.

        :param file_path: The file path to check

        :rtype: ``str``
        :return
            The new file path if was changed
        """

        def validate_new_path(expected_path: str):
            if not Path(expected_path).exists():
                logger.info(
                    f"<yellow>file {file_path} implies the existence of {str(expected_path)}, which is missing. "
                    f"Did you mistype {file_path}?</yellow>"
                )

        if file_path.endswith("_image.png"):
            if Path(file_path).parent.name in (XSIAM_DASHBOARDS_DIR, XSIAM_REPORTS_DIR):
                new_path = file_path.replace("_image.png", ".json")
            else:
                new_path = file_path.replace("_image.png", ".yml")
            validate_new_path(new_path)
            return new_path

        elif file_path.endswith("_description.md"):
            new_path = file_path.replace("_description.md", ".yml")
            validate_new_path(new_path)
            return new_path

        return file_path

    def handle_existing_rn_version_path(self, rn_path: str) -> str:
        """Checks whether the existing RN version path exists and return it's content.

        :param rn_path: The rn path to check

        :rtype: ``str``
        :return
            The content of the rn
        """
        if self.existing_rn_version_path:
            existing_rn_abs_path = self.CONTENT_PATH / self.existing_rn_version_path
            rn_path_abs_path = self.CONTENT_PATH / rn_path
            self.should_delete_existing_rn = str(existing_rn_abs_path) != str(
                rn_path_abs_path
            )
            try:
                return existing_rn_abs_path.read_text()
            except Exception as e:
                logger.info(
                    f"<red>Failed to load the previous release notes file content: {e}</red>"
                )
        return ""

    def execute_update(self) -> bool:
        """Obtains the information needed in order to update the pack and executes the update.

        :rtype: ``bool``
        :return
            Whether the RN was updated successfully or not
        """
        if self.pack in IGNORED_PACK_NAMES:
            logger.info(
                f"<yellow>Release notes are not required for the {self.pack} pack since this pack"
                f" is not versioned.</yellow>"
            )
            return False
        new_version, new_metadata = self.get_new_version_and_metadata()
        rn_path = self.get_release_notes_path(new_version)
        self.check_rn_dir(rn_path)
        self.rn_path = rn_path
        self.find_added_pack_files()
        changed_files = {}
        for packfile in self.modified_files_in_pack:
            file_name, file_type = self.get_changed_file_name_and_type(packfile)
            if file_type == FileType.METADATA:
                self.pack_metadata_only = True
                continue
            is_new_file = packfile in self.added_files
            content_item_object = (
                create_content_item_object(packfile, self.prev_ver, is_new_file)
                if file_type
                in [
                    FileType.INTEGRATION,
                    FileType.BETA_INTEGRATION,
                    FileType.SCRIPT,
                    FileType.PLAYBOOK,
                ]
                else None
            )
            name, description = (
                (
                    get_name(content_item_object),
                    get_description(content_item_object),
                )
                if content_item_object and isinstance(content_item_object, ContentItem)
                else (get_content_item_details(packfile, file_type))
            )
            changed_files[(file_name, file_type)] = {
                "description": description,
                "is_new_file": packfile in self.added_files,
                "fromversion": get_from_version_at_update_rn(packfile),
                "dockerimage": self.get_docker_image_if_changed(
                    content_item_object, packfile
                ),
                "path": packfile,
                "name": name,
                "changed_content_object": content_item_object,
            }
        self.pack_metadata_only = (not changed_files) and self.pack_metadata_only
        return self.create_pack_rn(rn_path, changed_files, new_metadata, new_version)

    def get_docker_image_if_changed(
        self, content_item_object: Optional["BaseContent"], packfile
    ) -> Optional[str]:
        """
        Checks if the Docker image of a content item has changed.

        Args:
            content_item_object (Optional[BaseContent]): The content item being checked, which can be an `Integration` or `Script`.
            packfile (str): The path to the file being checked.

        Returns:
            Optional[str]: The updated Docker image tag if it has changed, otherwise `None`.
        """
        if (
            content_item_object
            and isinstance(content_item_object, (Integration, Script))
            and "yml" in packfile
            and packfile not in self.added_files
            and (old_base_content_object := content_item_object.old_base_content_object)
            and isinstance(old_base_content_object, (Integration, Script))
            and content_item_object.docker_image != old_base_content_object.docker_image
        ):
            return content_item_object.docker_image
        return None

    def create_pack_rn(
        self, rn_path: str, changed_files: dict, new_metadata: dict, new_version: str
    ) -> bool:
        """Checks whether the pack requires a new rn and if so, creates it.

        :param
            rn_path (str): The rn path
            changed_files (dict): The changed files details
            new_metadata (dict): The new pack metadata
            new_version (str): The new version str representation, e.g 1.0.2, 1.11.2 etc.


        :rtype: ``bool``
        :return
            Whether the RN was updated successfully or not
        """
        rn_string = self.handle_existing_rn_version_path(rn_path)
        if not rn_string:
            rn_string = self.build_rn_template(changed_files)
        if len(rn_string) > 0 or self.is_force:
            if self.is_bump_required():
                self.write_metadata_to_file(new_metadata)
            self.create_markdown(rn_path, rn_string, changed_files)
            self.build_rn_config_file(new_version)
            if self.existing_rn_changed:
                logger.info(
                    f"<green>Finished updating release notes for {self.pack}.</green>"
                )
                if not self.text:
                    logger.info(
                        f"\n<green>Next Steps:\n - Please review the "
                        f"created release notes found at {rn_path} and document any changes you "
                        f"made by replacing '%%UPDATE_RN%%'/'%%UPDATE_CONTENT_ITEM_CHANGE_DESCRIPTION%%'"
                        f"/'%%UPDATE_CONTENT_ITEM_DESCRIPTION%%'/'%%UPDATE_CONTENT_ITEM_NAME%%'/'%%UPDATE_CONTENT_ITEM_TYPE%%' or deleting it.\n - Commit "
                        f"the new release notes to your branch.\nFor information regarding proper"
                        f" format of the release notes, please refer to "
                        f"https://xsoar.pan.dev/docs/integrations/changelog</green>"
                    )
                return True
            else:
                logger.info(
                    f"<green>No changes to {self.pack} pack files were detected from the previous time "
                    "this command was run. The release notes have not been "
                    "changed.</green>"
                )
        else:
            logger.info(
                "<yellow>No changes which would belong in release notes were detected.</yellow>"
            )
        return False

    def build_rn_config_file(self, new_version: str) -> None:
        """
        Builds RN config file if needed. Currently, we use RN config file only for cases where version has breaking
        changes.
        Args:
            new_version (str): The new version number representation, e.g 1.2.1, 1.22.1, etc.

        Returns:
            (None): Creates/updates config file with BC entries, if -bc flag was given.
        """
        # Currently, we only use config file if version is BC. If version is not BC no need to create config file.
        if not self.is_bc:
            return
        bc_file_path: str = (
            f"""{self.pack_path}/ReleaseNotes/{new_version.replace('.', '_')}.json"""
        )
        self.bc_path = bc_file_path
        bc_file_data: dict = dict()
        if Path(bc_file_path).exists():
            with open(bc_file_path) as f:
                bc_file_data = json.loads(f.read())
        bc_file_data["breakingChanges"] = True
        bc_file_data["breakingChangesNotes"] = bc_file_data.get("breakingChangesNotes")
        with open(bc_file_path, "w") as f:
            f.write(json.dumps(bc_file_data, indent=4))
        logger.info(
            f"<green>Finished creating config file for RN version {new_version}.\n"
            "If the breaking changes apply only for specific marketplaces, add those values under the `marketplaces` field.\n"
            "If you wish only specific text to be shown as breaking changes, please fill the "
            "`breakingChangesNotes` field with the appropriate breaking changes text.</green>"
        )

    def get_new_version_and_metadata(self) -> Tuple[str, dict]:
        """
        Gets the new version and the new metadata after version bump or by getting it from the pack metadata if
        bump is not required.

        :rtype: ``(str, dict)``
        :return: The new version and new metadata dictionary
        """
        if self.is_bump_required():
            if self.update_type is None:
                self.update_type = "revision"
            new_version, new_metadata = self.bump_version_number(
                self.specific_version, self.pre_release
            )
            if self.is_force:
                logger.info(
                    f"Bumping {self.pack} to version: {new_version}",
                )
            else:
                logger.info(
                    f"Changes were detected. Bumping {self.pack} to version: {new_version}",
                )
        else:
            new_metadata = self.get_pack_metadata()
            new_version = new_metadata.get("currentVersion", "99.99.99")

        if self.master_version == "0.0.0" and new_version == "1.0.0":
            raise ValueError(
                "Release notes do not need to be updated for version '1.0.0'."
            )

        return new_version, new_metadata

    def _does_pack_metadata_exist(self) -> bool:
        """Check if pack_metadata.json exists

        :rtype: ``bool``
        :return
            Whether the pack metadata exists
        """
        if not Path(self.metadata_path).is_file():
            logger.info(
                f'<red>"{self.metadata_path}" file does not exist, create one in the root of the pack</red>'
            )
            return False

        return True

    def get_master_version(self) -> str:
        """
        Gets the current version from origin/master or origin/main if available, otherwise return '0.0.0'.

        :rtype: ``str``
        :return
            The master version

        """
        master_current_version = "0.0.0"
        master_metadata = None
        try:
            master_metadata = get_remote_file(self.metadata_path, tag=self.main_branch)
        except Exception:
            logger.exception(
                f"<red>Failed fetching {self.metadata_path} from remote master branch."
                "Using the local version (if exists), instead</red>",
            )
        if master_metadata:
            master_current_version = master_metadata.get("currentVersion", "0.0.0")
        return master_current_version

    def is_bump_required(self) -> bool:
        """
        Checks if the currentVersion in the pack metadata has been changed or not. Additionally, it will verify
        that there is no conflict with the currentVersion in then Master branch.

        :rtype: ``bool``
        :return
            Whether a version bump is required
        """
        try:
            if self.only_docs_changed() and not self.is_force:
                return False
            new_metadata = self.get_pack_metadata()
            new_version = new_metadata.get("currentVersion", "99.99.99")
            if Version(self.master_version) >= Version(new_version):
                return True
            return False
        except RuntimeError as e:
            raise RuntimeError(
                f"Unable to locate a pack with the name {self.pack} in the git diff.\n"
                f"Please verify the pack exists and the pack name is correct."
            ) from e

    def only_docs_changed(self) -> bool:
        """
        Checks if the only files that were changed are documentation files.

        :rtype: ``bool``
        :return
            Whether only the docs were changed
        """
        changed_files = self.added_files.union(self.modified_files_in_pack)
        changed_files_copy = copy.deepcopy(
            changed_files
        )  # copying as pop will leave the file out of the set
        if (len(changed_files) == 1 and "README" in changed_files_copy.pop()) or (
            all(
                "README" in file or (".png" in file and "_image.png" not in file)
                for file in changed_files
            )
        ):
            return True
        return False

    def find_added_pack_files(self):
        """
        Checks if the added files in the given pack require RN and if so, adds them to the modified files in the
        pack.
        """
        for a_file in self.added_files:
            if self.pack in a_file:
                if any(
                    item in a_file for item in ALL_FILES_VALIDATION_IGNORE_WHITELIST
                ):
                    continue
                else:
                    self.modified_files_in_pack.add(
                        self.change_image_or_desc_file_path(a_file)
                    )

    def get_release_notes_path(self, input_version: str) -> str:
        """Gets the release notes path.

        :param input_version: The new rn version

        :rtype: ``bool``
        :return
        Whether the RN was updated successfully or not
        """
        _new_version = input_version.replace(".", "_")
        new_version = _new_version.replace("_prerelease", "")
        return os.path.join(self.pack_path, "ReleaseNotes", f"{new_version}.md")

    @staticmethod
    def find_corresponding_yml(file_path) -> str:
        """Gets the pack's corresponding yml file from the python/yml file.

        :param file_path: The pack python/yml file

        :rtype: ``str``
        :return
        The path to the pack's yml file
        """
        if file_path.endswith(".py"):
            yml_filepath = file_path.replace(".py", ".yml")
        else:
            yml_filepath = file_path
        return yml_filepath

    def get_changed_file_name_and_type(
        self, file_path
    ) -> Tuple[str, Optional[FileType]]:
        """Gets the changed file name and type.

        :param file_path: The file path

        :rtype: ``str, FileType``
        :return
        The changed file name and type
        """
        _file_type = None
        file_name = "N/A"

        if self.pack + "/" in file_path and ("README" not in file_path):
            _file_path = self.find_corresponding_yml(file_path)
            file_name = get_display_name(_file_path)
            _file_type = find_type(_file_path)

        return file_name, _file_type

    def get_pack_metadata(self) -> dict:
        """Gets the pack metadata.

        :rtype: ``dict``
        :return
        The pack metadata dictionary
        """
        try:
            data_dictionary = get_json(self.metadata_path, cache_clear=True)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"The metadata file of pack {self.pack} was not found. Please verify the pack name is correct, and that the file exists."
            ) from e
        return data_dictionary

    def bump_version_number(
        self, specific_version: str = None, pre_release: bool = False
    ) -> Tuple[str, dict]:
        """Increases the version number by user input or update type.

        :param
            specific_version: The specific version to change the version to
            pre_release: Indicates that the change should be designated a pre-release version

        :rtype: ``str, dict``
        :return
        The new version number (for example: 1.0.3) and the new pack metadata after version bump
        """
        if self.update_type is None and specific_version is None:
            raise ValueError("Received no update type when one was expected.")
        new_version = ""  # This will never happen since we pre-validate the argument
        data_dictionary = self.get_pack_metadata()
        current_version = (
            self.master_version
            if self.master_version != "0.0.0"
            else self.get_pack_metadata().get("currentVersion", "99.99.99")
        )
        if specific_version:
            logger.info(
                f"Bumping {self.pack} to the version {specific_version}. If you need to update"
                f" the release notes a second time, please remove the -v flag.",
            )
            data_dictionary["currentVersion"] = specific_version
            return specific_version, data_dictionary
        elif self.update_type == "major":
            version = current_version.split(".")
            version[0] = str(int(version[0]) + 1)
            if int(version[0]) > 99:
                raise ValueError(
                    f"Version number is greater than 99 for the {self.pack} pack. "
                    f"Please verify the currentVersion is correct."
                )
            version[1] = "0"
            version[2] = "0"
            new_version = ".".join(version)
        elif self.update_type == "minor":
            version = current_version.split(".")
            version[1] = str(int(version[1]) + 1)
            if int(version[1]) > 99:
                raise ValueError(
                    f"Version number is greater than 99 for the {self.pack} pack. "
                    f"Please verify the currentVersion is correct. If it is, "
                    f"then consider bumping to a new Major version."
                )
            version[2] = "0"
            new_version = ".".join(version)
        # We validate the input via click

        elif self.update_type in ["revision", "documentation"]:
            version = current_version.split(".")
            version[2] = str(int(version[2]) + 1)
            if int(version[2]) > 99:
                raise ValueError(
                    f"Version number is greater than 99 for the {self.pack} pack. "
                    f"Please verify the currentVersion is correct. If it is, "
                    f"then consider bumping to a new Minor version."
                )
            new_version = ".".join(version)
        elif self.update_type == "maintenance":
            raise ValueError(
                "The *maintenance* option is no longer supported."
                ' Please use the "revision" option and make sure to provide informative release notes.'
            )
        if pre_release:
            new_version = new_version + "_prerelease"
        data_dictionary["currentVersion"] = new_version
        return new_version, data_dictionary

    def write_metadata_to_file(self, metadata_dict: dict):
        """Writes the new metadata to the pack metadata file.

        :param
            metadata_dict: The new metadata to write

        """
        if self._does_pack_metadata_exist():
            with open(self.metadata_path, "w") as file_path:
                json.dump(metadata_dict, file_path, indent=4)
                logger.info(
                    f"<green>Updated pack metadata version at path : {self.metadata_path}</green>"
                )
            try:
                run_command(f"git add {self.metadata_path}", exit_on_error=False)
            except RuntimeError:
                logger.error(f"<red>Failed git-adding {self.metadata_path}</red>")

    @staticmethod
    def check_rn_dir(rn_path: str):
        """Checks whether the release notes folder exists and if not creates it.

        :param rn_path: The RN path to check/create

        """
        if not Path(rn_path).parent.exists():
            try:
                os.makedirs(os.path.dirname(rn_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def build_rn_template(self, changed_items: dict) -> str:
        """Builds the new release notes template.

        :param
            changed_items: The changed items data dictionary

        :rtype: ``str``
        :return
        The new release notes template
        """
        rn_string = ""

        if self.pack_metadata_only:
            pack_display_name = self.get_pack_metadata().get("name", self.pack)
            rn_string += f"## {pack_display_name}\n\n- %%UPDATE_RN%%\n"
            return rn_string
        rn_template_as_dict: dict = {}
        if self.is_force:
            pack_display_name = self.get_pack_metadata().get("name", self.pack)
            rn_string = self.build_rn_desc(
                content_name=pack_display_name, text=self.text
            )
        # changed_items.items() looks like that: [((name, type), {...}), (name, type), {...}] and we want to sort
        # them by type (x[0][1])

        for (content_name, _type), data in sorted(
            changed_items.items(),
            key=lambda x: RN_HEADER_BY_FILE_TYPE[x[0][1]] if x[0] and x[0][1] else "",
        ):  # Sort RN by header
            desc = data.get("description", "")
            is_new_file = data.get("is_new_file", False)
            from_version = data.get("fromversion", "")
            docker_image = data.get("dockerimage")
            path = data.get("path")
            name = data.get("name")
            changed_content_object = data.get("changed_content_object")
            # Skipping the invalid files
            if not _type or content_name == "N/A":
                continue
            rn_desc = self.build_rn_desc(
                _type=_type,
                content_name=content_name,
                desc=desc,
                is_new_file=is_new_file,
                text=self.text,
                docker_image=docker_image,
                from_version=from_version,
                path=path,
                name=name,
                changed_content_object=changed_content_object,
            )

            header = f"\n#### {RN_HEADER_BY_FILE_TYPE[_type]}\n\n"
            rn_template_as_dict[header] = rn_template_as_dict.get(header, "") + rn_desc

        for key, val in rn_template_as_dict.items():
            rn_string = f"{rn_string}{key}{val}"

        return rn_string

    def build_rn_desc(
        self,
        _type: FileType = None,
        content_name: str = "",
        desc: str = "",
        is_new_file: bool = False,
        text: str = "",
        docker_image: Optional[str] = "",
        from_version: str = "",
        path: str = "",
        name: str = "",
        changed_content_object: Optional[Union[Integration, Script, Playbook]] = None,
    ) -> str:
        """Builds the release notes description.

        :param
            _type: The file type
            content_name: The pack name
            desc: The pack description
            is_new_file: True if the file is new
            text: Text to add to the release notes files
            from_version: From version
            name: The name of the content item

        :rtype: ``str``
        :return
        The release notes description
        """
        text = text.encode("utf-8").decode("unicode_escape")
        if self.is_force:
            rn_desc = f"## {content_name}\n\n"
            rn_desc += f'- {text or "%%UPDATE_RN%%"}\n'
        else:
            type_value = (
                RN_HEADER_BY_FILE_TYPE.get(_type, _type.value).rstrip("s").lower()
                if _type
                else ""
            )
            if is_new_file:
                # new content items
                rn_desc = f"##### New: {content_name}\n\n"
                if desc and _type == FileType.PLAYBOOK:
                    rn_desc += format_playbook_description(desc)
                else:
                    rn_desc += NEW_RN_TEMPLATE.format(
                        type=type_value,
                        name=name,
                        description=desc or "%%UPDATE_CONTENT_ITEM_DESCRIPTION%%.",
                    )
                rn_desc += self.generate_rn_marketplaces_availability(
                    _type, content_name, from_version
                )
                rn_desc += self.generate_rn_list_new_commands(changed_content_object)
            else:
                # Updated content items
                rn_desc = f"##### {content_name}\n\n"
                if self.update_type == "documentation":
                    rn_desc += "- Documentation and metadata improvements.\n"
                else:
                    current_rn = ""
                    if changed_content_object:
                        current_rn = generate_rn_for_updated_content_items(
                            changed_content_object
                        )
                        rn_desc += current_rn
                    if not any([current_rn, text, docker_image]):
                        rn_desc += GENERAL_UPDATE_RN.format(
                            name=(name or "%%UPDATE_CONTENT_ITEM_NAME%%"),
                            type=(type_value or "%%UPDATE_CONTENT_ITEM_TYPE%%"),
                        )
                    elif text:
                        rn_desc += f"- {text}\n"

        if docker_image:
            rn_desc += f"- Updated the Docker image to: *{docker_image}*.\n\n"
        return rn_desc

    def generate_rn_list_new_commands(
        self, changed_content_object: Optional[Union[Integration, Script, Playbook]]
    ) -> str:
        """Generates a release note description for newly added commands in an integration.

        Args:
            changed_content_object (BaseContent): The content object being checked for new commands.
                                                Must be an instance of `Integration` to generate release notes.

        Returns:
            str: A formatted release note listing the new commands, or an empty string if no commands are found.
        """
        rn_desc = ""
        if (
            changed_content_object
            and isinstance(changed_content_object, Integration)
            and changed_content_object.commands
        ):
            rn_desc = NEW_COMMANDS_RN
            for command in changed_content_object.commands:
                rn_desc += f"\t- ***{get_name(command)}***\n"
        return rn_desc

    def generate_rn_marketplaces_availability(self, _type, content_name, from_version):
        """Generates a release note description indicating marketplace availability.

        Args:
            _type (str): The type of the content.
            content_name (str): The name of the content item.
            from_version (str): The minimum version of Cortex XSOAR where the content is available.

        Returns:
            str: A release note description specifying availability in Cortex XSOAR and/or Cortex XSIAM.
        """
        rn_desc = ""
        if _type in SIEM_ONLY_ENTITIES or content_name.replace(
            " ", ""
        ).lower().endswith(EVENT_COLLECTOR.lower()):
            rn_desc += (
                "<~XSIAM> (Available from Cortex XSIAM %%XSIAM_VERSION%%).</~XSIAM>"
            )
        elif from_version and _type not in SIEM_ONLY_ENTITIES:
            pack_marketplaces = self.get_pack_metadata().get(
                "marketplaces", [MarketplaceVersions.XSOAR.value]
            )
            if MarketplaceVersions.MarketplaceV2.value in pack_marketplaces:
                rn_desc += "<~XSIAM> (Available from Cortex XSIAM %%XSIAM_VERSION%%).</~XSIAM>\n"
            if (
                not pack_marketplaces
                or MarketplaceVersions.XSOAR.value in pack_marketplaces
            ):
                rn_desc += (
                    f"<~XSOAR> (Available from Cortex XSOAR {from_version}).</~XSOAR>"
                )
        rn_desc += "\n"
        return rn_desc

    def does_content_item_header_exist_in_rns(
        self, current_rn: str, content_name: str
    ) -> bool:
        """
        Checks whether the content item header exists in the release notes.

        Args:
            current_rn: The current release notes.
            content_name: The content item name.
        Returns:
            True if the content item header exists in the release notes, False otherwise.
        """
        for line in current_rn.replace("#####", "").replace("**", "").split("\n"):
            if content_name == re.sub(r"^-|New:", "", line.strip()).strip():
                return True
        return False

    def update_existing_rn(self, current_rn, changed_files) -> str:
        """Update the existing release notes.

        :param
            current_rn: The existing rn
            changed_files: The new data to add

        :rtype: ``str``
        :return
        The updated release notes
        """
        update_docker_image_regex = r"- Updated the Docker image to: \*.*\*\."
        # Deleting old entry for docker images, will re-write later, this allows easier generating of updated rn.
        current_rn_without_docker_images = re.sub(
            update_docker_image_regex, "", current_rn
        )
        new_rn = current_rn_without_docker_images
        # changed_files.items() looks like that: [((name, type), {...}), (name, type), {...}] and we want to sort
        # them by name (x[0][0])
        for (content_name, _type), data in sorted(
            changed_files.items(),
            key=lambda x: x[0][0] if x[0][0] else "",
            reverse=True,
        ):
            is_new_file = data.get("is_new_file")
            desc = data.get("description", "")
            docker_image = data.get("dockerimage")
            rn_desc = ""
            path = data.get("path")
            name = data.get("name")
            changed_content_object = data.get("changed_content_object")
            if _type is None:
                continue

            _header_by_type = RN_HEADER_BY_FILE_TYPE.get(_type)
            rn_desc += "\n\n" + self.build_rn_desc(
                _type=_type,
                content_name=content_name,
                desc=desc,
                is_new_file=is_new_file,
                docker_image=docker_image,
                path=path,
                name=name,
                changed_content_object=changed_content_object,
            )
            if _header_by_type and _header_by_type in current_rn_without_docker_images:
                if self.does_content_item_header_exist_in_rns(
                    current_rn_without_docker_images, content_name
                ):
                    if docker_image:
                        new_rn = self.handle_existing_rn_with_docker_image(
                            new_rn, _header_by_type, docker_image, content_name
                        )
                else:
                    self.existing_rn_changed = True
                    rn_parts = new_rn.split(_header_by_type)
                    new_rn_part = rn_desc
                    if len(rn_parts) > 1:
                        new_rn = f"{rn_parts[0]}{_header_by_type}{new_rn_part[:-1]}{rn_parts[1]}"
                    else:
                        new_rn = "".join(rn_parts) + new_rn_part
            else:
                self.existing_rn_changed = True
                if _header_by_type and _header_by_type in new_rn:
                    rn_parts = new_rn.split(_header_by_type)
                    new_rn_part = rn_desc
                    if len(rn_parts) > 1:
                        new_rn = f"{rn_parts[0]}{_header_by_type}{new_rn_part[:-1]}{rn_parts[1]}"
                else:
                    new_rn_part = f"\n#### {_header_by_type}{rn_desc}\n"
                    new_rn += new_rn_part
        if new_rn != current_rn:
            self.existing_rn_changed = True
        return new_rn

    @staticmethod
    def handle_existing_rn_with_docker_image(
        new_rn: str, header_by_type: str, docker_image: str, content_name: str
    ) -> str:
        """
        Receives the new RN to be written, performs operations to add the docker image to the given RN.
        Args:
            new_rn (str): new RN.
            header_by_type (str): Header of the RN to add docker image to, e.g 'Integrations', 'Scripts'
            docker_image (str): Docker image to add
            content_name (str): The content name to add the docker image entry to, e.g integration name, script name.

        Returns:
            (str): Updated RN
        """
        # Writing or re-writing docker image to release notes.
        rn_parts = new_rn.split(header_by_type)
        new_rn_part = f"- Updated the Docker image to: *{docker_image}*."
        if len(rn_parts) > 1:
            # Splitting again by content name to append the docker image release note to corresponding
            # content entry only
            content_parts = rn_parts[1].split(f"{content_name}\n")
            new_rn = (
                f"{rn_parts[0]}{header_by_type}{content_parts[0]}{content_name}\n{new_rn_part}\n"
                f"{content_parts[1]}"
            )
        else:
            logger.info(
                f"<yellow>Could not parse release notes {new_rn} by header type: {header_by_type}</yellow>"
            )
        return new_rn

    def create_markdown(
        self, release_notes_path: str, rn_string: str, changed_files: dict
    ):
        """Creates the new markdown and writes it to the release notes file.

        :param
            release_notes_path: The release notes file path
            rn_string: The rn data (if exists)
            changed_files: The changed files details
            docker_image_name: The docker image name

        """
        if Path(release_notes_path).exists() and self.update_type is not None:
            logger.info(
                f"<yellow>Release notes were found at {release_notes_path}. Skipping</yellow>"
            )
        elif self.update_type is None and self.specific_version is None:
            current_rn = get_latest_release_notes_text(release_notes_path)
            updated_rn = self.update_existing_rn(current_rn, changed_files)
            with open(release_notes_path, "w") as fp:
                fp.write(updated_rn)
        else:
            self.existing_rn_changed = True
            with open(release_notes_path, "w") as fp:
                fp.write(rn_string)
        try:
            run_command(f"git add {release_notes_path}", exit_on_error=False)
        except RuntimeError:
            logger.warning(
                f"Could not add the release note files to git: {release_notes_path}"
            )

    def rn_with_docker_image(self, rn_string: str, docker_image: Optional[str]) -> str:
        """
        Receives existing release notes, if docker image was updated, adds docker_image to release notes.
        Taking care of cases s.t:
        1) no docker image update have occurred ('docker_image' is None).
        2) Release notes did not contain updated docker image note.
        3) Release notes contained updated docker image notes, with the newest updated docker image.
        4) Release notes contained updated docker image notes, but docker image was updated again since last time
           release notes have been updated.

        param:
            rn_string (str): The current text contained in the release note
            docker_image (Optional[str]): The docker image str, if given

        :rtype: ``str``
        :return
            The release notes, with the most updated docker image release note, if given
        """
        if not docker_image:
            return rn_string
        docker_image_str = f"- Updated the Docker image to: *{docker_image}*."
        if docker_image_str in rn_string:
            return rn_string
        self.existing_rn_changed = True
        if "- Updated the Docker image to" not in rn_string:
            return rn_string + f"{docker_image_str}\n"
        update_docker_image_regex = r"- Updated the Docker image to: \*.*\*\."
        updated_rn = re.sub(update_docker_image_regex, docker_image_str, rn_string)
        self.existing_rn_changed = True
        return updated_rn


def get_content_item_details(path, file_type) -> Tuple[str, str]:
    """Gets the file details.

    :param
        path: The file path

    :rtype: ``str``
    :return
    The file description if exists otherwise returns %%UPDATE_RN%%
    """
    if not Path(path).is_file():
        logger.info(
            f'<yellow>Cannot get file description: "{path}" file does not exist</yellow>'
        )
        return ("", "")

    if path.endswith(".yml") and (
        issubclass(TYPE_CONVERSION_BY_FileType[file_type], YAMLContentObject)
        or isinstance(file_type, YAMLContentUnifiedObject)
    ):
        file = get_yaml(path)
    elif path.endswith(".json") and issubclass(
        TYPE_CONVERSION_BY_FileType[file_type], JSONContentObject
    ):
        file = get_json(path)
    else:
        return ("%%UPDATE_CONTENT_ITEM_NAME%%", "%%UPDATE_CONTENT_ITEM_DESCRIPTION%%")

    description = ""
    if file_type == FileType.XSIAM_DASHBOARD:
        dashboards_data = file.get("dashboards_data", [])
        description = dashboards_data[0].get("description") if dashboards_data else ""
    description = description or file.get(
        "description", "%%UPDATE_CONTENT_ITEM_DESCRIPTION%%"
    )

    name = ""
    if file_type == FileType.TRIGGER:
        name = file.get("trigger_name")
    elif file_type == FileType.XSIAM_DASHBOARD:
        dashboards_data = file.get("dashboards_data", [])
        name = dashboards_data[0].get("name") if dashboards_data else ""
    elif file.get("display"):
        name = file.get("display")
    name = name or file.get("name", "%%UPDATE_CONTENT_ITEM_NAME%%.")

    return (name, description)


def update_api_modules_dependents_rn(
    pre_release: bool,
    update_type: Union[str, None],
    added: Iterable[str],
    modified: Iterable[str],
    text: str = "",
) -> set:
    """Updates release notes for any pack that depends on API module that has changed.
    :param
        pre_release: Indicates whether the change should be designated as a pre-release version
        update_type: The update type
        added: The added files
        modified: The modified files
        id_set_path: The id set path
        text: Text to add to the release notes files

    :rtype: ``set``
    :return
    A set of updated packs
    """
    total_updated_packs: set = set()
    api_module_set = get_api_module_ids(added)
    api_module_set = api_module_set.union(get_api_module_ids(modified))
    logger.info(
        f"<yellow>Changes were found in the following APIModules : {api_module_set}, updating all dependent "
        f"integrations.</yellow>"
    )
    with ContentGraphInterface() as graph:
        update_content_graph(graph, use_git=True, dependencies=True)
        integrations = get_api_module_dependencies_from_graph(api_module_set, graph)
        if integrations:
            logger.info("Executing update-release-notes on those as well.")
        for integration in integrations:
            integration_pack_name = integration.pack_id
            integration_path = integration.path
            integration_pack_path = pack_name_to_path(integration_pack_name)
            update_pack_rn = UpdateRN(
                pack_path=integration_pack_path,
                update_type=update_type,
                modified_files_in_pack={integration_path},
                pre_release=pre_release,
                added_files=set(),
                pack=integration_pack_name,
                text=text,
            )
            updated = update_pack_rn.execute_update()
            if updated:
                total_updated_packs.add(integration_pack_name)
        return total_updated_packs


def get_from_version_at_update_rn(path: str) -> Optional[str]:
    """
    param:
        path (str): path to yml file, if exists

    :rtype: ``Optional[str]``
    :return:
        Fromversion if there is a fromversion key in the yml file

    """
    if not Path(path).is_file():
        logger.info(
            f'<yellow>Cannot get file fromversion: "{path}" file does not exist</yellow>'
        )
        return None
    return get_from_version(path)


def format_playbook_description(desc: str) -> str:
    """Format a playbook description for RN.

    :param:
        desc (str): The description to format.

    :rtype: ``str``
    :return:
        The formatted description.
    """
    desc = f"\n{desc}"
    for phrase, hdr in PB_RELEASE_NOTES_FORMAT.items():
        desc = desc.replace(f"\n{phrase}\n", f'\n{"#" * hdr} {phrase}\n')
    return desc.lstrip("\n")
