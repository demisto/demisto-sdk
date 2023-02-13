import base64
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from ruamel.yaml.scalarstring import PlainScalarString, SingleQuotedScalarString

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    TYPE_PWSH,
    TYPE_PYTHON,
    TYPE_TO_EXTENSION,
)
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.tools import (
    LOG_COLORS,
    get_yaml,
    pascal_case,
    print_color,
    print_error,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)

yaml = YAML_Handler()

REGEX_MODULE = r"### GENERATED CODE ###((.|\s)+?)### END GENERATED CODE ###"
INTEGRATIONS_DOCS_REFERENCE = "https://xsoar.pan.dev/docs/reference/integrations/"


class YmlSplitter:
    """YmlSplitter is a class that's designed to split a yml file to it's components.

    Attributes:
        input (str): input yml file path
        output (str): output path
        no_demisto_mock (bool): whether to add an import for demistomock
        no_common_server (bool): whether to add an import for common server
        no_auto_create_dir (bool): whether to create a dir
        base_name (str): the base name of all extracted files
        no_readme (bool): whether to extract readme
        file_type (str): yml file type (integration/script/modeling or parsing rule)
        configuration (Configuration): Configuration object
        lines_inserted_at_code_start (int): the amount of lines inserted at the beginning of the code file
    """

    def __init__(
        self,
        input: str,
        output: str = "",
        file_type: str = "",
        no_demisto_mock: bool = False,
        no_common_server: bool = False,
        no_auto_create_dir: bool = False,
        configuration: Configuration = None,
        base_name: str = "",
        no_readme: bool = False,
        no_logging: bool = False,
        **_,  # ignoring unexpected kwargs
    ):
        self.input = Path(input).resolve()
        self.output = (Path(output) if output else Path(self.input.parent)).resolve()
        self.demisto_mock = not no_demisto_mock
        self.common_server = not no_common_server
        self.file_type = file_type
        self.base_name = base_name
        self.readme = not no_readme
        self.logging = not no_logging
        self.lines_inserted_at_code_start = 0
        self.config = configuration or Configuration()
        self.auto_create_dir = not no_auto_create_dir
        self.yml_data = get_yaml(self.input)
        self.api_module_path: Optional[str] = None

    def get_output_path(self):
        """Get processed output path"""
        output_path = Path(self.output)
        if self.auto_create_dir and output_path.name in {
            "Integrations",
            "Scripts",
            "ModelingRules",
            "ParsingRules",
        }:
            code_name = self.yml_data.get("name")
            if not code_name:
                raise ValueError(
                    f"Failed determining Integration/Script/ModelingRule/ParsingRule name "
                    f"when trying to auto create sub dir at: {self.output}"
                    f"\nRun with option --no-auto-create-dir to skip auto creation of target dir."
                )
            output_path = output_path / pascal_case(code_name)
        return output_path

    def extract_to_package_format(
        self, executed_from_contrib_converter: bool = False
    ) -> int:
        """Extracts the self.input yml file into several files according to the XSOAR standard of the package format.

        Returns:
             int. status code for the operation.
        """
        try:
            output_path = self.get_output_path()
        except ValueError as ex:
            print_error(str(ex))
            return 1
        self.print_logs(
            f"Starting migration of: {self.input} to dir: {output_path}",
            log_color=LOG_COLORS.NATIVE,
        )
        output_path.mkdir(parents=True, exist_ok=True)
        base_name = output_path.name if not self.base_name else self.base_name
        code_file = output_path / base_name
        self.extract_code(code_file, executed_from_contrib_converter)
        script = self.yml_data.get("script", {})
        lang_type: str = (
            script.get("type", "")
            if self.file_type == "integration"
            else self.yml_data.get("type")
        )
        self.extract_image(f"{output_path}/{base_name}_image.png")
        self.extract_long_description(f"{output_path}/{base_name}_description.md")
        yaml_out = f"{output_path}/{base_name}.yml"
        self.print_logs(
            f"Creating yml file: {yaml_out} ...", log_color=LOG_COLORS.NATIVE
        )
        with open(self.input) as yf:
            yaml_obj = yaml.load(yf)
        script_obj = yaml_obj

        if self.file_type in ("modelingrule", "parsingrule"):
            self.extract_rules(f"{output_path}/{base_name}.xif")
            if "rules" in yaml_obj:
                yaml_obj["rules"] = PlainScalarString("")
            if "schema" in yaml_obj:
                self.extract_rule_schema_and_samples(
                    f"{output_path}/{base_name}_schema.json"
                )
                yaml_obj["schema"] = PlainScalarString("")
            if "samples" in yaml_obj:
                self.extract_rule_schema_and_samples(f"{output_path}/{base_name}.json")
                del yaml_obj["samples"]
            with open(yaml_out, "w") as yf:
                yaml.dump(yaml_obj, yf)
        else:
            code_file = f"{code_file}{TYPE_TO_EXTENSION[lang_type]}"
            if self.file_type == "integration":
                script_obj = yaml_obj["script"]
                if "image" in yaml_obj:
                    del yaml_obj["image"]
                if "detaileddescription" in yaml_obj:
                    del yaml_obj["detaileddescription"]
            script_obj["script"] = SingleQuotedScalarString("")
            code_type = script_obj["type"]
            if code_type == TYPE_PWSH and not yaml_obj.get("fromversion"):
                self.print_logs(
                    "Setting fromversion for PowerShell to: 5.5.0",
                    log_color=LOG_COLORS.NATIVE,
                )
                yaml_obj["fromversion"] = "5.5.0"
            with open(yaml_out, "w") as yf:
                yaml.dump(yaml_obj, yf)
            # check if there is a README and if found, set found_readme to True
            if self.readme:
                yml_readme = self.input.parent / f"{self.input.stem}_README.md"
                readme = output_path / "README.md"
                if yml_readme.exists():
                    self.print_logs(
                        f"Copying {readme} to {readme}", log_color=LOG_COLORS.NATIVE
                    )
                    shutil.copy(yml_readme, readme)
                else:
                    # open an empty file
                    with open(readme, "w"):
                        pass
        self.print_logs(
            f"Finished splitting the yml file - you can find the split results here: {output_path}",
            log_color=LOG_COLORS.GREEN,
        )
        return 0

    def extract_code(
        self, code_file_path, executed_from_contrib_converter: bool = False
    ) -> int:
        """Extracts the code from the yml_file.
        If code_file_path doesn't contain the proper extension will add it.

        Returns:
             int. status code for the operation.
        """
        common_server = self.common_server
        if common_server:
            common_server = "CommonServerPython" not in str(
                self.input
            ) and "CommonServerPowerShell" not in str(self.input)
        if self.file_type == "modelingrule" or self.file_type == "parsingrule":
            # no need to extract code
            return 0

        script = self.yml_data["script"]
        if (
            self.file_type == "integration"
        ):  # in integration the script is stored at a second level
            lang_type = script["type"]
            script = script["script"]
        else:
            lang_type = self.yml_data["type"]
        ext = TYPE_TO_EXTENSION[lang_type]
        code_file_path = code_file_path.with_suffix(ext)
        self.print_logs(
            f"Extracting code to: {code_file_path} ...", log_color=LOG_COLORS.NATIVE
        )
        with open(code_file_path, "w") as code_file:
            if lang_type == TYPE_PYTHON and self.demisto_mock:
                code_file.write("import demistomock as demisto  # noqa: F401\n")
                self.lines_inserted_at_code_start += 1
            if common_server:
                if lang_type == TYPE_PYTHON:
                    code_file.write("from CommonServerPython import *  # noqa: F401\n")
                    self.lines_inserted_at_code_start += 1
                if lang_type == TYPE_PWSH:
                    code_file.write(". $PSScriptRoot\\CommonServerPowerShell.ps1\n")
                    self.lines_inserted_at_code_start += 1
            script = self.replace_imported_code(script, executed_from_contrib_converter)
            script = self.replace_section_headers_code(script)
            code_file.write(script)
            if script and script[-1] != "\n":
                # make sure files end with a new line (pyml seems to strip the last newline)
                code_file.write("\n")
        return 0

    def extract_image(self, output_path) -> int:
        """Extracts the image from the yml_file.

        Returns:
             int. status code for the operation.
        """
        if self.file_type == "script":
            return 0  # no image in script type
        self.print_logs(
            f"Extracting image to: {output_path} ...", log_color=LOG_COLORS.NATIVE
        )
        im_field = self.yml_data.get("image")
        if im_field and len(im_field.split(",")) >= 2:
            image_b64 = self.yml_data["image"].split(",")[1]
            with open(output_path, "wb") as image_file:
                image_file.write(base64.decodebytes(image_b64.encode("utf-8")))
        return 0

    def remove_integration_documentation(self, detailed_description):
        if "[View Integration Documentation]" in detailed_description:
            normalized_integration_id = (
                IntegrationScriptUnifier.normalize_integration_id(
                    self.yml_data["commonfields"]["id"]
                )
            )
            integration_doc_link = (
                INTEGRATIONS_DOCS_REFERENCE + normalized_integration_id
            )
            documentation = f"[View Integration Documentation]({integration_doc_link})"
            if "\n\n---\n" + documentation in detailed_description:
                detailed_description = detailed_description.replace(
                    "\n\n---\n" + documentation, ""
                )
            elif documentation in detailed_description:
                detailed_description = detailed_description.replace(documentation, "")

        return detailed_description

    def extract_long_description(self, output_path) -> int:
        """Extracts the detailed description from the yml_file.

        Returns:
             int. status code for the operation.
        """
        if self.file_type == "script":
            return 0  # no long description in script type
        long_description = self.yml_data.get("detaileddescription")
        if long_description:
            long_description = self.remove_integration_documentation(long_description)
            self.print_logs(
                f"Extracting long description to: {output_path} ...",
                log_color=LOG_COLORS.NATIVE,
            )
            with open(output_path, "w", encoding="utf-8") as desc_file:
                desc_file.write(long_description)
        return 0

    def extract_rules(self, output_path) -> int:
        """Extracts the parsing and modeling rules from the yml_file.

        Returns:
             int. status code for the operation.
        """
        rules = self.yml_data.get("rules")
        if rules:
            self.print_logs(
                f"Extracting rules to: {output_path} ...", log_color=LOG_COLORS.NATIVE
            )
            with open(output_path, "w", encoding="utf-8") as rules_file:
                rules_file.write(rules)
        return 0

    def extract_rule_schema_and_samples(self, output_path) -> int:
        """
        Extracts the schema of the modeling rules from the yml_file.
        Extracts the samples of the parsing rules from the yml_file.
        Returns:
             int. status code for the operation.
        """
        # Modeling rules
        schema = self.yml_data.get("schema")
        if schema:
            self.print_logs(
                f"Extracting rules schema to: {output_path} ...",
                log_color=LOG_COLORS.NATIVE,
            )
            with open(output_path, "w", encoding="utf-8") as rules_file:
                rules_file.write(schema)

        # Parsing rules
        samples = self.yml_data.get("samples")
        if samples:
            self.print_logs(
                f"Extracting rules samples to: {output_path} ...",
                log_color=LOG_COLORS.NATIVE,
            )
            with open(output_path, "w", encoding="utf-8") as rules_file:
                rules_file.write(samples)
        return 0

    def print_logs(self, log_msg: str, log_color: str) -> None:
        """
        Prints the logging message if logging is enabled
        :param log_msg: The logging message
        :param log_color: The printing color
        :return: None
        """
        if self.logging:
            print_color(log_msg, log_color)

    def update_api_module_contribution(self, lines: list, imported_line: str):
        """
        save the api module changes done by the contributor to the api module file before it is replaced in the
        integration code.
        :param lines: the integration lines.
        :param imported_line: the imported line in the code, represents the Api Module used.
        :return: None
        """
        imported_line_arr = imported_line.split(
            " "
        )  # example: imported_line = from CorIRApiModule import *
        updated_lines = lines[4:-3]  # ignore first 4 lines and last 3 line.
        if (
            len(imported_line_arr) >= 3
            and imported_line_arr[0] == "from"
            and imported_line_arr[2] == "import"
        ):
            module_name = imported_line_arr[1]
            self.api_module_path = os.path.join(
                "./Packs", "ApiModules", "Scripts", module_name, module_name + ".py"
            )
            with open(self.api_module_path, "w") as f:
                f.write("from CommonServerPython import *  # noqa: F401\n")
                f.write("import demistomock as demisto  # noqa: F401\n")
                f.write("\n".join(updated_lines))

    def replace_imported_code(
        self, script, executed_from_contrib_converter: bool = False
    ):
        # this is how we check that generated code exists, and the syntax of the generated code is up to date
        if (
            "### GENERATED CODE ###:" in script
            and "### END GENERATED CODE ###" in script
        ):
            matches = re.finditer(REGEX_MODULE, script)
            for match in matches:
                code = match.group(1)
                lines = code.split("\n")
                imported_line = lines[0][
                    2:
                ]  # the first two chars are not part of the code
                if executed_from_contrib_converter:
                    self.update_api_module_contribution(lines, imported_line)
                self.print_logs(
                    f"Replacing code block with `{imported_line}`", LOG_COLORS.NATIVE
                )
                script = script.replace(match.group(), imported_line)
        return script

    def replace_section_headers_code(self, script):
        """
        remove the auto-generated section headers if they exist.
        """
        return re.sub(
            r"register_module_line\('.+', '(?:start|end)', __line__\(\)\)\n", "", script
        )
