import traceback
from distutils.version import LooseVersion
from typing import Optional, Tuple

import click

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    FILETYPE_TO_DEFAULT_FROMVERSION,
)
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.tools import is_uuid, print_error
from demisto_sdk.commands.format.format_constants import (
    ARGUMENTS_DEFAULT_VALUES,
    ERROR_RETURN_CODE,
    SKIP_RETURN_CODE,
    SUCCESS_RETURN_CODE,
    TO_VERSION_5_9_9,
)
from demisto_sdk.commands.format.update_generic import BaseUpdate

yaml = YAML_Handler()
json = JSON_Handler()


class BaseUpdateJSON(BaseUpdate):
    """BaseUpdateJSON is the base class for all json updaters.
    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the YML to.
        data (dict): JSON file data arranged in a Dict.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        verbose: bool = False,
        clear_cache: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            verbose=verbose,
            clear_cache=clear_cache,
            **kwargs,
        )

    def set_default_values_as_needed(self):
        """Sets basic arguments of reputation commands to be default, isArray and required."""
        if self.verbose:
            click.echo("Updating required default values")
        for field in ARGUMENTS_DEFAULT_VALUES:
            if self.__class__.__name__ in ARGUMENTS_DEFAULT_VALUES[field][1]:
                self.data[field] = ARGUMENTS_DEFAULT_VALUES[field][0]

    def save_json_to_destination_file(
        self,
        encode_html_chars: bool = True,
        escape_forward_slashes: bool = False,
        ensure_ascii: bool = False,
        indent: int = 4,
    ):
        """Save formatted JSON data to destination file."""
        if self.source_file != self.output_file:
            click.secho(f"Saving output JSON file to {self.output_file}", fg="white")
        with open(self.output_file, "w") as file:
            json.dump(
                self.data,
                file,
                indent=indent,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
                ensure_ascii=ensure_ascii,
            )

    def update_json(
        self, default_from_version: Optional[str] = "", file_type: str = ""
    ):
        """Manager function for the generic JSON updates."""
        self.remove_null_fields()
        self.check_server_version()
        self.remove_spaces_end_of_id_and_name()
        self.remove_unnecessary_keys()
        self.set_version_to_default()
        self.set_fromVersion(
            default_from_version=default_from_version, file_type=file_type
        )
        self.sync_data_to_master()

    def set_toVersion(self):
        """
        Sets toVersion key in file
        Relevant for old entities such as layouts and classifiers.
        """
        if (
            not self.data.get("toVersion")
            or LooseVersion(self.data.get("toVersion", DEFAULT_CONTENT_ITEM_TO_VERSION))
            >= TO_VERSION_5_9_9
        ):
            if self.verbose:
                click.echo("Setting toVersion field")
            self.data["toVersion"] = TO_VERSION_5_9_9

    def set_description(self):
        """Add an empty description to file root."""
        if "description" not in self.data:
            if self.verbose:
                click.echo("Adding empty descriptions to root")
            self.data["description"] = ""

    def remove_null_fields(self):
        """Remove empty fields from file root."""
        schema_fields = self.schema.get("mapping", {}).keys()
        for field in schema_fields:
            # We want to keep 'false' and 0 values, and avoid removing fields that are required in the schema.
            if (
                field in self.data
                and self.data[field] in (None, "", [], {})
                and not self.schema.get("mapping", {}).get(field, {}).get("required")
            ):
                # We don't want to remove the defaultRows key in grid, even if it is empty
                if not (field == "defaultRows" and self.data.get("type", "") == "grid"):
                    self.data.pop(field)

    def update_id(self, field="name") -> None:
        """Updates the id to be the same as the provided field ."""
        updated_integration_id_dict = {}
        if self.old_file:
            current_id = self.data.get("id")
            old_id = self.old_file.get("id")
            if current_id != old_id:
                click.secho(
                    f"The modified JSON file corresponding to the path: {self.relative_content_path} contains an "
                    f"ID which does not match the ID in remote file. Changing the ID from {current_id} back "
                    f"to {old_id}.",
                    fg="yellow",
                )
                self.data["id"] = old_id
        else:
            if self.verbose:
                click.echo("Updating ID to be the same as JSON name")
            if field not in self.data:
                print_error(
                    f"Missing {field} field in file {self.source_file} - add this field manually"
                )
                return None
            if "id" in self.data and is_uuid(
                self.data["id"]
            ):  # only happens if id had been defined
                updated_integration_id_dict[self.data["id"]] = self.data[field]
            self.data["id"] = self.data[field]
            if updated_integration_id_dict:
                self.updated_ids.update(updated_integration_id_dict)

    def remove_spaces_end_of_id_and_name(self):
        """Updates the id and name of the json to have no spaces on its end"""
        if not self.old_file:
            if self.verbose:
                click.echo("Updating json ID and name to be without spaces at the end")
            if "name" in self.data:
                self.data["name"] = self.data["name"].strip()
            if "id" in self.data:
                self.data["id"] = self.data["id"].strip()

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def run_format(self) -> int:
        try:
            click.secho(
                f"\n======= Updating file: {self.source_file} =======", fg="white"
            )
            self.update_json(
                default_from_version=FILETYPE_TO_DEFAULT_FROMVERSION.get(
                    self.source_file_type  # type: ignore
                )
            )
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            print(
                "".join(
                    traceback.format_exception(
                        type(err), value=err, tb=err.__traceback__
                    )
                )
            )
            if self.verbose:
                click.secho(
                    f"\nFailed to update file {self.source_file}. Error: {err}",
                    fg="red",
                )
            return ERROR_RETURN_CODE
