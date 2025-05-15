import os
import traceback
from typing import Dict, List, Optional, Tuple, Union

import click

from demisto_sdk.commands.common.constants import (
    BETA_INTEGRATION,
    ENTITY_TYPE_TO_DIR,
    FILETYPE_TO_DEFAULT_FROMVERSION,
    INTEGRATION,
    NO_TESTS_DEPRECATED,
    PLAYBOOK,
    SCRIPT,
    TEST_PLAYBOOKS_DIR,
    FileType,
)
from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    _get_file_id,
    find_type,
    get_entity_id_by_entity_type,
    get_file,
    get_not_registered_tests,
    get_scripts_and_commands_from_yml_data,
    get_yaml,
    is_uuid,
    listdir_fullpath,
    search_and_delete_from_conf,
)
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic import BaseUpdate


class GenericAgentixFormat(BaseUpdate):
    """GenericAgentixFormat is the base class for all yml updaters.

    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the YML to.
        data (Dict): YML file data arranged in a Dict.
        id_and_version_location (Dict): the object in the yml_data that holds the id and version values.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        assume_answer: Union[bool, None] = None,
        deprecate: bool = False,
        add_tests: bool = True,
        interactive: bool = True,
        clear_cache: bool = False,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            assume_answer=assume_answer,
            interactive=interactive,
            clear_cache=clear_cache,
        )
        self.id_and_version_location = self.get_id_and_version_path_object()
        self.deprecate = deprecate

    def _load_conf_file(self) -> Dict:
        """
        Loads the content of conf.json file from path 'CONF_PATH'
        Returns:
            The content of the json file
        """
        return get_file(CONF_PATH, raise_on_error=True)

    def get_id_and_version_path_object(self):
        """Gets the dict that holds the id and version fields.
        Returns:
            Dict. Holds the id and version fields.
        """
        return self.get_id_and_version_for_data(self.data)

    def get_id_and_version_for_data(self, data):
        try:
            path = "commonfields"
            return data.get(path, data)
        except KeyError:
            # content type is not relevant for checks using this property
            return None

    def save_yml_to_destination_file(self):
        """Safely saves formatted YML data to destination file."""
        if self.source_file != self.output_file:
            logger.debug(f"Saving output YML file to {self.output_file} \n")
        with open(self.output_file, "w") as f:
            yaml.dump(self.data, f)  # ruamel preservers multilines

    def update_yml(
        self, default_from_version: Optional[str] = "", file_type: str = ""
    ) -> None:
        """Manager function for the generic YML updates."""

        self.remove_copy_and_dev_suffixes_from_name()
        self.adds_period_to_description()
        self.remove_unnecessary_keys()
        self.remove_spaces_end_of_id_and_name()
        self.set_fromVersion(
            default_from_version=default_from_version, file_type=file_type
        )
        if self.id_and_version_location:
            self.set_version_to_default(self.id_and_version_location)
        self.sync_data_to_master()

        self.remove_nativeimage_tag_if_exist()

    def remove_from_conf_json(self, file_type, content_item_id) -> None:
        """
        Updates conf.json remove the file's test playbooks.
        Args:
            file_type: The typr of the file, can be integration, playbook or testplaybook.
            content_item_id: The content item id.
        """
        related_test_playbook = self.data.get("tests", [])
        no_test_playbooks_explicitly = any(
            test
            for test in related_test_playbook
            if ("no test" in test.lower()) or ("no tests" in test.lower())
        )
        try:
            conf_json_content = self._load_conf_file()
        except FileNotFoundError:
            logger.debug(
                f"<yellow>Unable to find {CONF_PATH} - skipping update.</yellow>"
            )
            return
        conf_json_test_configuration = conf_json_content["tests"]
        conf_json_content["tests"] = search_and_delete_from_conf(
            conf_json_test_configuration,
            content_item_id,
            file_type,
            related_test_playbook,
            no_test_playbooks_explicitly,
        )
        self._save_to_conf_json(conf_json_content)

    def _save_to_conf_json(self, conf_json_content: Dict) -> None:
        """Save formatted JSON data to destination file."""
        with open(CONF_PATH, "w") as file:
            json.dump(conf_json_content, file, indent=4)

    def remove_spaces_end_of_id_and_name(self):
        """Updates the id and name of the YML to have no spaces on its end"""
        if not self.old_file:
            logger.debug("Updating YML ID and name to be without spaces at the end")
            if name := self.data.get("name"):
                self.data["name"] = name.strip()
            if self.id_and_version_location:
                self.id_and_version_location["id"] = self.id_and_version_location[
                    "id"
                ].strip()

    def remove_nativeimage_tag_if_exist(self):
        if self.data.get("nativeimage"):  # script
            self.data.pop("nativeimage")
        elif script_section := self.data.get("script"):
            if isinstance(script_section, dict) and script_section.get(
                "nativeimage"
            ):  # integration
                script_section.pop("nativeimage")

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the Correlation Rules YML updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def run_format(self) -> int:
        try:
            logger.info(f"\n======= Updating file: {self.source_file} =======")
            self.update_yml(
                default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION.get(
                    self.source_file_type  # type: ignore
                )
            )
            self.save_yml_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            logger.info(
                "".join(
                    traceback.format_exception(
                        type(err), value=err, tb=err.__traceback__
                    )
                )
            )
            logger.debug(
                f"\n<red>Failed to update file {self.source_file}. Error: {err}</red>"
            )
            return ERROR_RETURN_CODE
