import os.path
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from git import InvalidGitRepositoryError
from requests.structures import CaseInsensitiveDict

from demisto_sdk.commands.common import git_util
from demisto_sdk.commands.common.constants import (
    CONTENT_FILE_ENDINGS,
    CONTEXT_OUTPUT_README_TABLE_HEADER,
    DOCS_COMMAND_SECTION_REGEX,
    INTEGRATIONS_DIR,
    INTEGRATIONS_README_FILE_NAME,
)
from demisto_sdk.commands.common.default_additional_info_loader import (
    load_default_additional_info_dict,
)
from demisto_sdk.commands.common.files.errors import GitFileReadError
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_content_path,
    get_yaml,
)
from demisto_sdk.commands.generate_docs.common import (
    CONFIGURATION_SECTION_STEPS,
    add_lines,
    build_example_dict,
    generate_numbered_section,
    generate_section,
    generate_table_section,
    save_output,
    string_escape_md,
)
from demisto_sdk.commands.integration_diff.integration_diff_detector import (
    IntegrationDiffDetector,
)

CREDENTIALS = 9


class IntegrationDocUpdateManager:
    """
    A class to abstract away and manage the Integration documentation update.

    The process is as follows:
    1) Compare the integration YAMLs from input and master to check for differences in configuration and commands.
    2) If any changes are detected in the configuration, replace the configuration section.
    3) If any modifications are detected in the existing commands, replace the modified command'(s') section(s).
    4) If new commands are detected, we append them to the end of the commands section (EOF).
    """

    def __init__(
        self,
        input_path: str,
        is_contribution: bool,
        example_dict: dict,
        command_permissions_dict: dict,
    ) -> None:
        self.new_yaml_path = Path(input_path)
        self.new_readme_path = self.new_yaml_path.parent / INTEGRATIONS_README_FILE_NAME
        self.update_errors: List[str] = []
        self.output_doc: str = ""

        self.is_ui_contribution: bool = is_contribution
        self.integration_name: str = self.new_yaml_path.stem

        # We attempt to get the integration YAML from version control
        # first from remote (`demisto/content` `origin/master`).
        # If we can't get it from remote, we get it from local `master`
        # branch.
        self.old_yaml_path = self._get_resource_path_from_source_control(
            remote=True, type=CONTENT_FILE_ENDINGS[1]
        ) or self._get_resource_path_from_source_control(
            remote=False, type=CONTENT_FILE_ENDINGS[1]
        )

        if self.old_yaml_path:
            self.integration_diff = IntegrationDiffDetector(
                new=str(self.new_yaml_path), old=str(self.old_yaml_path)
            )
            self.old_readme_path = self._get_resource_path_from_source_control(
                remote=True, type=CONTENT_FILE_ENDINGS[4]
            ) or self._get_resource_path_from_source_control(
                remote=False, type=CONTENT_FILE_ENDINGS[4]
            )
            self.output_doc = (
                self.old_readme_path.read_text() if self.old_readme_path else ""
            )

        self.example_dict = example_dict
        self.command_permissions_dict = command_permissions_dict

    def _get_resource_path_from_source_control(
        self, remote: bool, type: str
    ) -> Optional[Path]:
        """
        Retrieve the resource (integration YML or integration README)
        from source control (remote or local).

        Args:
        - `remote` (``bool``): Indicating whether we should download the
        file from remote or get it locally.
        - `type` (``type``): The type of file to retrieve. Possible values are 'yml' and 'md'.

        Returns:
        - `Path` if the YAML was found, `None` otherwise.
        """

        # Validate file types
        if type not in {CONTENT_FILE_ENDINGS[1], CONTENT_FILE_ENDINGS[4]}:
            raise ValueError("'type' argument must be either 'md' or 'yml'.")

        path = None

        # Check if we're retrieving the YML or README
        if type == CONTENT_FILE_ENDINGS[1]:
            logger.debug(
                f"Reading {self.integration_name} YAML from {'remote' if remote else 'local'} git path..."
            )
            resource_path = self.new_yaml_path

        else:
            logger.debug(
                f"Reading {self.integration_name} README from {'remote' if remote else 'local'} git path..."
            )
            resource_path = self.new_readme_path

        try:
            # In case we're attempting to get the yml/md in a contrib flow
            # we already have the content repo fork cloned and synced with upstream
            # so there's no need to get the file from remote.
            # We therefore set the output path to the relative path from
            # the content path of the resource.
            if self.is_ui_contribution or not remote:
                relative_resource_path = os.path.join(
                    INTEGRATIONS_DIR, self.integration_name, resource_path.name
                )
                path = list(get_content_path().glob(f"**/{relative_resource_path}"))[0]
            elif remote:

                if not resource_path.is_absolute():
                    resource_path = resource_path.absolute()

                remote_file_content = TextFile.read_from_git_path(
                    resource_path, from_remote=remote
                )

                path = self._write_resource_to_tmp(resource_path, remote_file_content)
        except (
            FileNotFoundError,
            git_util.GitFileNotFoundError,
            GitFileReadError,
            KeyError,
            IndexError,
        ) as e:
            msg = f"{e.__class__.__name__}: Could not find file '{str(resource_path)}' in {'remote' if remote else 'local'}. Please specify the full path to the integration YAML file, e.g. `demisto-sdk generate-docs -i $(realpath {resource_path})`"
            logger.error(msg)
            self.update_errors.append(msg)
            path = None
        except InvalidGitRepositoryError as err:
            msg = f"Failed to open git repository: {str(err)}"
            logger.error(msg)
            self.update_errors.append(msg)
            path = None
        finally:
            logger.debug(f"Path returned: '{path}'")
            return path if path and path.exists() else None

    def can_update_docs(self) -> bool:
        """
        Before generating a new README, we check whether it's possible to update the interation docs.
        We check whether:

        - There's an integration diff. In case when we can't pull an integration YAML from `origin/master`,
        we won't have an integration diff instance.
        - There's an integration README from `origin/master`.
        If it's not new, we retrieve the integration YAML from `demisto/content` `origin/master``,
        and regenerate the changed sections.
        """

        can_update = False
        try:

            if not self.integration_diff:
                msg = "Unable to update docs because the integration YAML doesn't exist in remote."
                logger.error(msg)
                self.update_errors.append(msg)
            elif not self.old_readme_path:
                msg = "Unable to update docs because integration README doesn't exist in remote."
                logger.error(msg)
                self.update_errors.append(msg)
            else:
                can_update = True
        except (TypeError, FileNotFoundError) as err:
            msg = f"Could not create an compare integration '{self.new_yaml_path}' with origin ': {str(err)}"
            logger.error(msg)
            self.update_errors.append(msg)
        finally:
            return can_update

    def _update_conf_section(self):
        """
        Helper function that replaces an integration configuration section in the
        README.
        """

        try:
            new_configuration_section = generate_setup_section(
                self.integration_diff.new_yaml_data
            )

            doc_text_lines = self.output_doc.splitlines()

            # We take the first and the second-to-last index of the old section
            # and use the section range to replace it with the new section.
            # Second-to-last index because the last element is an empty string
            old_config_start_line = doc_text_lines.index(
                CONFIGURATION_SECTION_STEPS.STEP_1.value
            )
            old_config_end_line = doc_text_lines.index(
                CONFIGURATION_SECTION_STEPS.STEP_4.value
            )

            doc_text_lines[
                old_config_start_line : old_config_end_line + 1
            ] = new_configuration_section

            self.output_doc = "\n".join(doc_text_lines)
        except ValueError as e:
            error = f"Unable to find configuration section line in README: {str(e)}"
            self.update_errors.append(error)
        except Exception as e:
            error = f"Failed replacing the integration section: {e.__class__.__name__} {str(e)}"
            self.update_errors.append(error)

    def _update_commands_section(self):
        """
        Helper function that replaces an integration commands section in the
        README.
        """

        for i, modified_command in enumerate(
            self.integration_diff.get_modified_commands()
        ):
            try:
                old_command_section, _ = generate_commands_section(
                    self.integration_diff.old_yaml_data,
                    {},
                    {},
                    modified_command,
                )

                (
                    new_command_section,
                    generate_command_section_errors,
                ) = generate_commands_section(
                    self.integration_diff.new_yaml_data,
                    self.example_dict,
                    self.command_permissions_dict,
                    modified_command,
                )

                # UI contributions cannot generate human readable/example output
                # of the command so there's no need to add certain error types
                # to the list of errors
                if generate_command_section_errors:
                    for error in generate_command_section_errors:
                        if (
                            self.is_ui_contribution
                            and "Did not get any example for" in error
                        ):
                            continue
                        else:
                            self.update_errors.extend(generate_command_section_errors)

                doc_text_lines = self.output_doc.splitlines()

                # We take the first and the second-to-last index of the old section
                # and use the section range to replace it with the new section.
                # Second-to-last index because the last element is an empty string
                old_cmd_start_line = doc_text_lines.index(old_command_section[0])

                # In cases when there are multiple identical context outputs
                # in the second-to-last line, we need to find the relevant
                # second-to-last line for the specific command we're replacing.
                indices = [
                    i
                    for i, doc_line in enumerate(doc_text_lines)
                    if doc_line == old_command_section[-2]
                ]

                if indices and len(indices) > 1:
                    old_cmd_end_line = doc_text_lines.index(
                        old_command_section[-2], indices[i]
                    )
                else:
                    old_cmd_end_line = doc_text_lines.index(old_command_section[-2])

                doc_text_lines[
                    old_cmd_start_line : old_cmd_end_line + 1
                ] = new_command_section

                self.output_doc = "\n".join(doc_text_lines)
            except (ValueError, IndexError) as e:
                error = f"Unable to replace '{modified_command}' section in README: {str(e)}"
                self.update_errors.append(error)

    def _get_sections_to_update(self) -> Tuple[bool, List[str], List[str]]:

        return (
            self.integration_diff.is_configuration_different(),
            self.integration_diff.get_modified_commands(),
            self.integration_diff.get_added_commands(),
        )

    def _get_resource_path(self) -> str:
        """
        Helper function to resolve the resource path.
        """

    def _write_resource_to_tmp(self, resource_path: Path, content: str) -> Path:
        """
        Helper function to write
        """

        tmp_file = tempfile.NamedTemporaryFile(
            "w", suffix=resource_path.name, delete=False
        )
        logger.debug(f"Writing {len(content)}B into temp file '{tmp_file.name}'...")
        tmp_file.write(content)
        logger.debug(f"Finished writing to temp file '{tmp_file.name}'")

        return Path(tmp_file.name)

    def update_docs(self) -> Tuple[str, List[str]]:
        """
        Helper function that updates the integration documentation and returns the
        raw README text.
        """

        (
            update_configuration,
            modified_commands,
            added_commands,
        ) = self._get_sections_to_update()

        # In case the configuration section has changed
        # we want to replace the section with the new
        if update_configuration:
            logger.info("\t\u2699 Integration configuration has changed, updating...")

            self._update_conf_section()

        # Handle changed command arguments
        # We iterate over every modified command and subtitute
        # the section with the new one
        if modified_commands:
            logger.info(
                f"\t\u2699 Integration commands {','.join(modified_commands)} have changed, replacing the old section with the new one..."
            )

            self._update_commands_section()

        # Handle new commands
        # we append them to the README.
        if added_commands:
            self.output_doc += "\n"

            for cmd in added_commands:
                logger.info(f"\t\u2699 Generating docs for command `{cmd}`...")
                (
                    command_section,
                    generate_command_section_errors,
                ) = generate_commands_section(
                    yaml_data=self.integration_diff.new_yaml_data,
                    example_dict=self.example_dict,
                    command_permissions_dict=self.command_permissions_dict,
                    command=cmd,
                )

                if generate_command_section_errors:
                    logger.error(
                        f"\t\u26A0 Generating section for command '{cmd}' resulted in {len(generate_command_section_errors)} error(s)"
                    )
                    self.update_errors.extend(generate_command_section_errors)

                command_section_str = "\n".join(command_section)
                self.output_doc, append_cmd_errs = append_or_replace_command_in_docs(
                    self.output_doc, command_section_str, cmd
                )
                self.output_doc += "\n"

                if append_cmd_errs:
                    logger.error(
                        f"\t\u26A0 Appending section for command '{cmd}' to README.md resulted in {len(append_cmd_errs)} error(s)"
                    )
                    self.update_errors.extend(append_cmd_errs)
                else:
                    logger.info(
                        f"\t\u2713 New command `{cmd}` section added to the README.md."
                    )

        return self.output_doc, self.update_errors


def append_or_replace_command_in_docs(
    old_docs: str, new_doc_section: str, command_name: str
) -> Tuple[str, list]:
    """Replacing a command in a README.md file with a new string.

    Args:
        old_docs: the old docs string
        new_doc_section: the new string to replace
        command_name: the command name itself

    Returns:
        str: The whole documentation.
    """
    regexp = DOCS_COMMAND_SECTION_REGEX.format(command_name + "\n")
    # Read doc content
    errs = list()
    if re.findall(regexp, old_docs, flags=re.DOTALL):
        new_docs = re.sub(regexp, new_doc_section, old_docs, flags=re.DOTALL)
        logger.info("[green]New command docs has been replaced in README.md.[/green]")
    else:
        if command_name in old_docs:
            errs.append(
                f"Could not replace the command `{command_name}` in the file although it"
                f" is presented in the file."
                "Copy and paste it in the appropriate spot."
            )
        if old_docs.endswith("\n"):
            # Remove trailing '\n'
            old_docs = old_docs[:-1]
        new_docs = f"{old_docs}\n{new_doc_section}"
        logger.info("[green]New command docs has been added to the README.md.[/green]")
    return new_docs, errs


def generate_integration_doc(
    input_path: str,
    examples: Optional[str] = None,
    output: Optional[str] = None,
    use_cases: Optional[str] = None,
    permissions: Optional[str] = None,
    command_permissions: Optional[str] = None,
    limitations: Optional[str] = None,
    insecure: bool = False,
    command: Optional[str] = None,
    old_version: str = "",
    skip_breaking_changes: bool = False,
    is_contribution: bool = False,
):
    """
    Generate integration documentation.
    If the `command` argument is supplied, a new command section is appended to the existing README.
    If the integration exists in version control, an update is run on the modified sections of the existing README.
    Otherwise, create a new README.

    Args:
        input_path: path to the yaml integration
        examples: path to the command examples
        output: path to the output documentation
        use_cases: use cases string
        permissions: global permissions for the docs
        command_permissions: permissions per command
        limitations: limitations description
        insecure: should use insecure
        command: specific command to generate docs for
        is_contribution: Check if the content item is a new integration contribution or not.

    """
    try:
        yml_data = get_yaml(input_path)
        if not output:  # default output dir will be the dir of the input file
            output = os.path.dirname(os.path.realpath(input_path))
        errors: list = []
        example_dict: dict = {}
        if examples:
            specific_commands = command.split(",") if command else None
            command_examples = get_command_examples(examples, specific_commands)
            example_dict, build_errors = build_example_dict(command_examples, insecure)
            errors.extend(build_errors)
        else:
            errors.append("Command examples were not supplied.")

        if permissions == "per-command":
            command_permissions_dict: Any = {}
            if command_permissions and Path(command_permissions).is_file():
                permission_list = get_command_permissions(command_permissions)
                for command_permission in permission_list:
                    # get all the permissions after the command name
                    key, value = command_permission.split(" ", 1)
                    command_permissions_dict.update({key: value})
            else:
                errors.append(
                    f"Command permissions was not found {command_permissions}."
                )
        else:  # permissions in ['none', 'general']
            command_permissions_dict = None

        update_mgr = IntegrationDocUpdateManager(
            input_path, is_contribution, example_dict, command_permissions_dict
        )

        if command:
            specific_commands = command.split(",")
            readme_path = os.path.join(output, "README.md")
            with open(readme_path) as f:
                doc_text = f.read()
            for specific_command in specific_commands:
                logger.info(f"Generating docs for command `{specific_command}`")
                command_section, command_errors = generate_commands_section(
                    yml_data,
                    example_dict,
                    command_permissions_dict,
                    command=specific_command,
                )
                command_section_str = "\n".join(command_section)
                doc_text, append_errors = append_or_replace_command_in_docs(
                    doc_text, command_section_str, specific_command
                )

                if command_errors:
                    errors.extend(command_errors)
                if append_errors:
                    errors.extend(append_errors)

        # We check whether the docs can be updated.
        # We can update the docs when we have the following
        # in source control:
        # - An integration YAML.
        # - An integration README.
        elif update_mgr.can_update_docs():
            logger.info("Found existing integration, updating documentation...")
            doc_text, update_errors = update_mgr.update_docs()

            if update_errors:
                errors.extend(update_errors)
        else:
            docs: list = []
            docs.extend(add_lines(yml_data.get("description")))
            if not is_contribution:
                docs.extend(
                    [
                        f"This integration was integrated and tested with version xx of {yml_data['name']}.",
                        "",
                    ]
                )
            # Checks if the integration is a new version
            integration_version = re.findall("[vV][2-9]$", yml_data.get("display", ""))
            if integration_version and not skip_breaking_changes:
                docs.extend(
                    [
                        "Some changes have been made that might affect your existing content. "
                        "\nIf you are upgrading from a previous version of this integration, see [Breaking Changes]"
                        "(#breaking-changes-from-the-previous-version-of-this-integration-"
                        f'{yml_data.get("display", "").replace(" ", "-").lower()}).',
                        "",
                    ]
                )
            # Integration use cases
            if use_cases:
                docs.extend(generate_numbered_section("Use Cases", use_cases))
            # Integration general permissions
            if permissions == "general":
                docs.extend(generate_section("Permissions", ""))
            # Setup integration to work with Demisto
            docs.extend(
                generate_section(
                    "Configure {} on Cortex XSOAR".format(yml_data["display"]), ""
                )
            )
            # Setup integration on Demisto
            docs.extend(generate_setup_section(yml_data))
            # Commands
            (
                command_section,
                generate_command_section_errors,
            ) = generate_commands_section(
                yml_data, example_dict, command_permissions_dict, command=command
            )
            docs.extend(command_section)
            # Mirroring Incident
            if trigger_generate_mirroring_section(yml_data):
                docs.extend(generate_mirroring_section(yml_data))
            # breaking changes
            if integration_version and not skip_breaking_changes:
                docs.extend(
                    generate_versions_differences_section(
                        input_path, old_version, yml_data.get("display", "")
                    )
                )

            errors.extend(generate_command_section_errors)
            # Known limitations
            if limitations:
                docs.extend(generate_numbered_section("Known Limitations", limitations))

            doc_text = "\n".join(docs)
            if not doc_text.endswith("\n"):
                doc_text += "\n"

        save_output(output, INTEGRATIONS_README_FILE_NAME, doc_text)

        if errors:
            logger.info(f"[yellow]Found {len(errors)} possible errors:[/yellow]")
            for error in errors:
                logger.info(f"\t- {error}")

    except Exception as ex:
        logger.info(f"[red]Error: {str(ex)}[/red]")
        raise


# Setup integration on Demisto

with (Path(__file__).parent / "default_additional_information.json").open() as f:
    # Case insensitive to catch both `API key` and `API Key`, giving both the same value.
    default_additional_information: CaseInsensitiveDict = CaseInsensitiveDict(
        json.load(f)
    )


def generate_setup_section(yaml_data: dict) -> List[str]:

    """
    Generate the configuration section of the README.
    This section includes:
    - The steps to set up the integration instance.
    - The configuration options table.

    Arguments:
    - `yaml_data` (``dict``): The integration YAML in dictionary format.

    Returns:
    - `List[str]` of the section lines.

    """

    default_additional_info: CaseInsensitiveDict = load_default_additional_info_dict()

    section = [
        CONFIGURATION_SECTION_STEPS.STEP_1.value,
        CONFIGURATION_SECTION_STEPS.STEP_2_TEMPLATE.value.format(yaml_data["display"]),
        CONFIGURATION_SECTION_STEPS.STEP_3.value,
    ]
    access_data: List[Dict] = []

    for conf in yaml_data["configuration"]:
        if conf["type"] == CREDENTIALS:
            add_access_data_of_type_credentials(access_data, conf)
        else:
            access_data.append(
                {
                    "Parameter": conf.get("display"),
                    "Description": string_escape_md(
                        conf.get("additionalinfo", "")
                        or default_additional_info.get(conf.get("name", ""), ""),
                        escape_html=False,
                    ),
                    "Required": conf.get("required", ""),
                }
            )

    # Check if at least one parameter has additional info field.
    # If not, remove the description column from the access data table section.
    access_data_with_description = list(
        filter(lambda x: x.get("Description", "") != "", access_data)
    )
    if len(access_data_with_description) == 0:
        list(map(lambda x: x.pop("Description"), access_data))

    section.extend(
        generate_table_section(
            access_data, "", horizontal_rule=False, numbered_section=True
        )
    )
    section.append(CONFIGURATION_SECTION_STEPS.STEP_4.value)
    section.append("")

    return section


# Incident Mirroring


def trigger_generate_mirroring_section(yml_data: dict) -> bool:
    """

    Args:
        yml_data: yml data of the integration.

    Returns:
        true if mirroring section should be generated.

    """
    script_data = yml_data.get("script", {})
    sync_in = script_data.get("isremotesyncout", False)
    sync_out = script_data.get("isremotesyncin", False)
    return sync_out or sync_in


def is_configuration_exists(yml_data: dict, names: list):
    """
    Args:
        yml_data: yml data of the integration
        names: list of configuration params to search for

    Returns:
        list of all configurations found.

    """
    confs = []
    for conf in yml_data.get("configuration", []):
        if conf.get("name", "") in names:
            confs.append(conf)
    return confs


def generate_mirroring_section(yaml_data: dict) -> List[str]:
    """

    Args:
        yaml_data: dict representing the yml file of the integration.

    Returns: markdown section of Incident Mirroring.

    """
    integration_name = format(yaml_data["display"])
    directions = {
        "None": "Turns off incident mirroring.",
        "Incoming": f"Any changes in {integration_name} events (mirroring incoming fields) will be reflected in Cortex XSOAR incidents.",
        "Outgoing": f"Any changes in Cortex XSOAR incidents will be reflected in {integration_name} events (outgoing mirrored fields).",
        "Incoming And Outgoing": f"Changes in Cortex XSOAR incidents and {integration_name} events will be reflected in both directions.",
    }

    section = [
        "## Incident Mirroring",
        "",
        f"You can enable incident mirroring between Cortex XSOAR incidents and {integration_name} corresponding "
        f"events (available from Cortex XSOAR version 6.0.0).",
        "To set up the mirroring:",
        "1. Enable *Fetching incidents* in your instance configuration.",
    ]

    index = 2

    # Mirroring direction

    direction_conf = is_configuration_exists(yaml_data, ["mirror_direction"])
    if direction_conf:
        options = []
        for option in direction_conf[0].get("options", []):
            options.append(
                {"Option": option, "Description": directions.get(option, "")}
            )
        dir_text = (
            f"{index}. In the *Mirroring Direction* integration parameter, select in which direction the "
            f"incidents should be mirrored:"
        )
        index = index + 1
        section.append(dir_text)
        section.extend(
            generate_table_section(
                title="", data=options, horizontal_rule=False, numbered_section=True
            )
        )

    # mirroring tags

    tags = is_configuration_exists(
        yaml_data, ["comment_tag", "work_notes_tag", "file_tag"]
    )
    tags = [tag.get("display", "") for tag in tags]
    if tags:
        section.append(
            f"{index}. Optional: You can go to the mirroring tags parameter and select the tags used to "
            f'mark incident entries to be mirrored. Available tags are: {", ".join(tags)}.'
        )
        index = index + 1

    # Close Mirrored XSOAR Incident param

    if is_configuration_exists(yaml_data, ["close_incident"]):
        section.append(
            f"{index}. Optional: Check the *Close Mirrored XSOAR Incident* integration parameter to close the Cortex"
            f" XSOAR incident when the corresponding event is closed in {integration_name}."
        )
        index = index + 1
    if is_configuration_exists(yaml_data, ["close_out"]):
        section.append(
            f"{index}. Optional: Check the *Close Mirrored {integration_name} event* integration"
            f" parameter to close them when the corresponding Cortex XSOAR incident is closed."
        )

    section.extend(
        [
            "",
            "Newly fetched incidents will be mirrored in the chosen direction. However, this selection does "
            "not affect existing incidents.",
            f"**Important Note:** To ensure the mirroring works as expected, mappers are required,"
            f" both for incoming and outgoing, to map the expected fields in Cortex XSOAR and {integration_name}.",
            "",
        ]
    )

    return section


# Commands
def generate_commands_section(
    yaml_data: dict,
    example_dict: dict,
    command_permissions_dict: Optional[dict],
    command: Optional[str] = None,
) -> Tuple[list, list]:
    """Generate the commands section the the README.md file.

    Arguments:
        yaml_data (dict): The data of the .yml file (integration or script)
        example_dict (dict): Examples of running commands.
        command_permissions_dict (dict): Permission needed per command
        command (Optional[str]): A specific command to run on. will return the command itself without the section header.

    Returns:
        [str, str] -- [commands section, errors]
    """
    errors: list = []
    section = [
        "## Commands",
        "",
        "You can execute these commands from the Cortex XSOAR CLI, as part of an automation, or in a playbook.",
        "After you successfully execute a command, a DBot message appears in the War Room with the command details.",
        "",
    ]
    commands = filter(
        lambda cmd: not cmd.get("deprecated", False), yaml_data["script"]["commands"]
    )
    command_sections: list = []
    if command:
        # for specific command, return it only.
        try:
            command_dict = list(filter(lambda cmd: cmd["name"] == command, commands))[0]
        except IndexError:
            err = f"Could not find the command `{command}` in the .yml file."
            logger.info("[red]{err}[/red]")
            raise IndexError(err)
        return generate_single_command_section(
            command_dict, example_dict, command_permissions_dict
        )
    for cmd in commands:
        cmd_section, cmd_errors = generate_single_command_section(
            cmd, example_dict, command_permissions_dict
        )
        command_sections.extend(cmd_section)
        errors.extend(cmd_errors)

    section.extend(command_sections)
    return section, errors


def generate_single_command_section(
    cmd: dict, example_dict: dict, command_permissions_dict
):
    errors = []
    cmd_example = example_dict.get(cmd["name"])
    if command_permissions_dict:
        if command_permissions_dict.get(cmd["name"]):
            cmd_permission_example = [
                "#### Required Permissions",
                "",
                command_permissions_dict.get(cmd["name"]),
                "",
            ]
        else:
            errors.append(
                f"Error! Command Permissions were not found for command {cmd['name']}"
            )
            cmd_permission_example = ["#### Required Permissions", ""]
    elif isinstance(command_permissions_dict, dict) and not command_permissions_dict:
        cmd_permission_example = [
            "#### Required Permissions",
            "",
            "**FILL IN REQUIRED PERMISSIONS HERE**",
            "",
        ]
    else:  # no permissions for this command
        cmd_permission_example = []

    section = [
        "### {}".format(cmd["name"]),
        "",
        "***",
    ]
    if desc := cmd.get("description"):
        section.append(desc)
    section.extend(
        [
            "",
            *cmd_permission_example,
            "#### Base Command",
            "",
            "`{}`".format(cmd["name"]),
            "",
            "#### Input",
            "",
        ]
    )

    # Inputs
    arguments = cmd.get("arguments")
    if arguments is None:
        section.append("There are no input arguments for this command.")
    else:
        section.extend(
            [
                "| **Argument Name** | **Description** | **Required** |",
                "| --- | --- | --- |",
            ]
        )
        for arg in arguments:
            description = arg.get("description")
            if not description:
                errors.append(
                    "Error! You are missing description in input {} of command {}".format(
                        arg["name"], cmd["name"]
                    )
                )
            if description and not description.endswith("."):
                description = f"{description}."

            argument_description = (
                f'{description} Possible values are: {", ".join(arg.get("predefined"))}.'
                if arg.get("predefined")
                else description
            )
            if arg.get("defaultValue"):
                argument_description = (
                    f'{argument_description} Default is {arg.get("defaultValue")}.'
                )

            required_status = "Required" if arg.get("required") else "Optional"
            section.append(
                "| {} | {} | {} | ".format(
                    arg["name"],
                    string_escape_md(argument_description, True, True),
                    required_status,
                )
            )
    section.append("")

    # Context output
    section.extend(
        [
            "#### Context Output",
            "",
        ]
    )
    outputs = cmd.get("outputs")
    if outputs is None or len(outputs) == 0:
        section.append("There is no context output for this command.")
    else:
        section.extend([CONTEXT_OUTPUT_README_TABLE_HEADER, "| --- | --- | --- |"])
        for output in outputs:
            if not output.get("description"):
                errors.append(
                    "Error! You are missing description in output {} of command {}".format(
                        output["contextPath"], cmd["name"]
                    )
                )
            section.append(
                "| {} | {} | {} | ".format(
                    output["contextPath"],
                    output.get("type", "unknown"),
                    string_escape_md(output.get("description", "")),
                )
            )
        section.append("")

    # Raw output:
    example_section, example_errors = generate_command_example(cmd, cmd_example)
    section.extend(example_section)
    errors.extend(example_errors)

    return section, errors


def generate_versions_differences_section(
    input_path, old_version, display_name
) -> list:
    """
    Generate the version differences section to the README.md file.

    Arguments:
        input_path : The integration file path.

    Returns:
        List of the section lines.
    """

    differences_section = [
        f"## Breaking changes from the previous version of this integration - {display_name}",
        "%%FILL HERE%%",
        "The following sections list the changes in this version.",
        "",
    ]

    if not old_version:
        user_response = str(
            input(
                "Enter the path of the previous integration version file if any. Press Enter to skip.\n"
            )
        )

        if user_response:
            old_version = user_response

    if old_version:
        differences = get_previous_version_differences(input_path, old_version)

        if differences[0] != "":
            differences_section.extend(differences)

        else:
            # If there are no differences, remove the headers.
            differences_section = []

    else:

        differences_section.extend(
            [
                "### Commands",
                "#### The following commands were removed in this version:",
                "* *commandName* - this command was replaced by XXX.",
                "* *commandName* - this command was replaced by XXX.",
                "",
                "### Arguments",
                "#### The following arguments were removed in this version:",
                "",
                "In the *commandName* command:",
                "* *argumentName* - this argument was replaced by XXX.",
                "* *argumentName* - this argument was replaced by XXX.",
                "",
                "#### The behavior of the following arguments was changed:",
                "",
                "In the *commandName* command:",
                "* *argumentName* - is now required.",
                "* *argumentName* - supports now comma separated values.",
                "",
                "### Outputs",
                "#### The following outputs were removed in this version:",
                "",
                "In the *commandName* command:",
                "* *outputPath* - this output was replaced by XXX.",
                "* *outputPath* - this output was replaced by XXX.",
                "",
                "In the *commandName* command:",
                "* *outputPath* - this output was replaced by XXX.",
                "* *outputPath* - this output was replaced by XXX.",
                "",
            ]
        )

    differences_section.extend(
        [
            "## Additional Considerations for this version",
            "%%FILL HERE%%",
            "* Insert any API changes, any behavioral changes, limitations, or restrictions "
            "that would be new to this version.",
            "",
        ]
    )

    return differences_section


def get_previous_version_differences(
    new_integration_path, previous_integration_path
) -> list:
    """
    Gets the section of the previous integration version differences.

    Args:
        new_integration_path: The new integration path.
        previous_integration_path: The old integration path.

    Return:
        List of the differences section lines.
    """

    differences_detector = IntegrationDiffDetector(
        new=new_integration_path, old=previous_integration_path
    )
    differences_detector.missing_items_report = differences_detector.get_differences()

    differences_section = [
        differences_detector.print_items_in_docs_format(secho_result=False)
    ]

    return differences_section


def disable_md_autolinks(markdown: str) -> str:
    """Disable auto links that markdown clients (such as xosar.pan.dev) auto create. This behaviour is more
    consistent with how the Server works were links are only created for explicitly defined links.
    We take: https//lgtm.com/rules/9980089 and change to: https:<span>//</span>lgtm.com/rules/9980089
    Note that we don't want to change legitimate md links of the form: (link)[http://test.com]. We avoid
    legitimate md links by using a negative lookbehind in the regex to make sure before the http match
    we don't have ")[".

    Args:
        markdown (str): markdown to process

    Returns:
        str: processed markdown
    """
    if not markdown:
        return markdown
    return re.sub(
        r"\b(?<!\)\[)(https?)://([\w\d]+?\.[\w\d]+?)\b",
        r"\1:<span>//</span>\2",
        markdown,
        flags=re.IGNORECASE,
    )


def generate_command_example(cmd_from_yaml, cmd_example=None):
    example = []
    errors = []
    if not cmd_example:
        errors.append(
            f'Did not get any example for {cmd_from_yaml["name"]}. Please add it manually.'
        )

    else:
        for script_example, md_example, context_example in cmd_example:
            example.extend(["#### Command example", f"```{script_example}```"])
            if context_example and context_example != "{}":
                example.extend(
                    [
                        "#### Context Example",
                        "```json",
                        f"{context_example}",
                        "```",
                        "",
                    ]
                )
            example.extend(
                [
                    "#### Human Readable Output",
                    "{}".format(
                        ">".join(
                            f"\n{disable_md_autolinks(md_example)}".splitlines(True)
                        )
                    ),
                    # prefix human readable with quote
                    "",
                ]
            )

    return example, errors


def get_command_examples(commands_examples_input, specific_commands):
    """
    get command examples from command file

    @param commands_examples_input: commands examples file or a comma separeted list of com
    @param specific_commands: commands specified by the user

    @return: a list of command examples
    """

    if not commands_examples_input:
        return []

    if Path(commands_examples_input).is_file():
        with open(commands_examples_input) as examples_file:
            command_examples = examples_file.read().splitlines()
    else:
        logger.info(
            "[yellow]failed to open commands file, using commands as comma seperated list[/yellow]"
        )
        command_examples = commands_examples_input.split(",")

    # Filter from the examples only the commands specified by the user
    if specific_commands:
        command_examples = [
            command_ex
            for command_ex in command_examples
            if command_ex.split(" ")[0].strip("!") in specific_commands
        ]

    command_examples = (
        list(filter(None, map(command_example_filter, command_examples))) or []
    )

    logger.info("found the following commands:\n{}".format("\n".join(command_examples)))
    return command_examples


def command_example_filter(command):
    if not command:
        return
    elif command.startswith("#"):
        return
    elif not command.startswith("!"):
        return f"!{command}"
    return command


def get_command_permissions(commands_permissions_file_path) -> list:
    """
    get command permissions from file

    @param commands_permissions_file_path: command permissions file or the content of such file

    @return: a list of command permissions
    """
    commands_permissions: list = []

    if commands_permissions_file_path is None:
        return commands_permissions

    if Path(commands_permissions_file_path).is_file():
        with open(commands_permissions_file_path) as permissions_file:
            permissions = permissions_file.read().splitlines()
    else:
        logger.info("failed to open permissions file")
        permissions = commands_permissions_file_path.split("\n")

    permissions_map = map(command_permissions_filter, permissions)
    permissions_list: List = list(filter(None, permissions_map))

    logger.info(
        "found the following commands permissions:\n{}".format(
            "\n ".join(permissions_list)
        )
    )
    return permissions_list


def command_permissions_filter(permission):
    if permission.startswith("#"):
        return
    elif permission.startswith("!"):
        return f"{permission}"
    return permission


def add_access_data_of_type_credentials(
    access_data: List[Dict], credentials_conf: Dict
) -> None:
    """
    Adds to 'access_data' the parameter data of credentials configuration parameter.
    Args:
        access_data (List[Dict]): Access data to add the credentials conf data to.
        credentials_conf (Dict): Credentials conf data.

    Returns:
        (None): Adds the data to 'access_data'.
    """
    display_name = credentials_conf.get("display")
    if display_name:
        access_data.append(
            {
                "Parameter": display_name,
                "Description": string_escape_md(
                    credentials_conf.get("additionalinfo", "")
                ),
                "Required": credentials_conf.get("required", ""),
            }
        )
    access_data.append(
        {
            "Parameter": credentials_conf.get("displaypassword", "Password"),
            "Description": ""
            if display_name
            else string_escape_md(credentials_conf.get("additionalinfo", "")),
            "Required": credentials_conf.get("required", ""),
        }
    )
