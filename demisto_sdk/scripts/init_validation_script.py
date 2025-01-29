import os
import re
from pathlib import Path
from string import Template

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import pascal_to_snake

GIT_STATUSES_DICT = {
    "A": "GitStatuses.ADDED",
    "R": "GitStatuses.RENAMED",
    "M": "GitStatuses.MODIFIED",
}

RELATED_FILES_DICT = {
    "1": "RelatedFileType.README",
    "2": "RelatedFileType.DESCRIPTION_File",
    "3": "RelatedFileType.IMAGE",
    "4": "RelatedFileType.DARK_SVG",
    "5": "RelatedFileType.LIGHT_SVG",
    "6": "RelatedFileType.CODE_FILE",
    "7": "RelatedFileType.TEST_CODE_FILE",
    "8": "RelatedFileType.SCHEMA",
    "9": "RelatedFileType.XIF",
    "10": "RelatedFileType.PACK_IGNORE",
    "11": "RelatedFileType.SECRETS_IGNORE",
    "12": "RelatedFileType.AUTHOR_IMAGE",
    "13": "RelatedFileType.RELEASE_NOTE",
    "14": "RelatedFileType.VERSION_CONFIG",
}

CONTENT_TYPES_DICT = {
    "1": {
        "import": "from demisto_sdk.commands.content_graph.objects.integration import Integration",
        "content_type": "Integration",
    },
    "2": {
        "import": "from demisto_sdk.commands.content_graph.objects.script import Script",
        "content_type": "Script",
    },
    "3": {
        "import": "from demisto_sdk.commands.content_graph.objects.playbook import Playbook",
        "content_type": "Playbook",
    },
    "4": {
        "import": "from demisto_sdk.commands.content_graph.objects.pack import Pack",
        "content_type": "Pack",
    },
    "5": {
        "import": "from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard",
        "content_type": "Dashboard",
    },
    "6": {
        "import": "from demisto_sdk.commands.content_graph.objects.classifier import Classifier",
        "content_type": "Classifier",
    },
    "7": {
        "import": "from demisto_sdk.commands.content_graph.objects.job import Job",
        "content_type": "Job",
    },
    "8": {
        "import": "from demisto_sdk.commands.content_graph.objects.layout import Layout",
        "content_type": "Layout",
    },
    "9": {
        "import": "from demisto_sdk.commands.content_graph.objects.mapper import Mapper",
        "content_type": "Mapper",
    },
    "10": {
        "import": "from demisto_sdk.commands.content_graph.objects.wizard import Wizard",
        "content_type": "Wizard",
    },
    "11": {
        "import": "from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule",
        "content_type": "CorrelationRule",
    },
    "12": {
        "import": "from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField",
        "content_type": "IncidentField",
    },
    "13": {
        "import": "from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType",
        "content_type": "IncidentType",
    },
    "14": {
        "import": "from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField",
        "content_type": "IndicatorField",
    },
    "15": {
        "import": "from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType",
        "content_type": "IndicatorType",
    },
    "16": {
        "import": "from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule",
        "content_type": "LayoutRule",
    },
    "17": {
        "import": "from demisto_sdk.commands.content_graph.objects.layout import Layout",
        "content_type": "Layout",
    },
    "18": {
        "import": "from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule",
        "content_type": "ModelingRule",
    },
    "19": {
        "import": "from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule",
        "content_type": "ParsingRule",
    },
    "20": {
        "import": "from demisto_sdk.commands.content_graph.objects.report import Report",
        "content_type": "Report",
    },
    "21": {
        "import": "from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook",
        "content_type": "TestPlaybook",
    },
    "22": {
        "import": "from demisto_sdk.commands.content_graph.objects.trigger import Trigger",
        "content_type": "Trigger",
    },
    "23": {
        "import": "from demisto_sdk.commands.content_graph.objects.widget import Widget",
        "content_type": "Widget",
    },
    "24": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_definition import GenericDefinition",
        "content_type": "GenericDefinition",
    },
    "25": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_field import GenericField",
        "content_type": "GenericField",
    },
    "26": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule",
        "content_type": "GenericModule",
    },
    "27": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_type import GenericType",
        "content_type": "GenericType",
    },
    "28": {
        "import": "from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard",
        "content_type": "XSIAMDashboard",
    },
    "29": {
        "import": "from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport",
        "content_type": "XSIAMReport",
    },
    "30": {
        "import": "from demisto_sdk.commands.content_graph.objects.case_field",
        "content_type": "CaseField",
    },
    "31": {
        "import": "from demisto_sdk.commands.content_graph.objects.case_layout",
        "content_type": "CaseLayout",
    },
    "32": {
        "import": "from demisto_sdk.commands.content_graph.objects.case_layout_rule",
        "content_type": "CaseLayoutRule",
    },
}

VALIDATION_TEMPLATE = """
$imports

$supported_content_types


$class_declaration
    error_code = "$error_code"
    description = "$error_description"
    rationale = "$rationale"
    error_message = "$error_message"$fix_message
    related_field = "$related_field"
    is_auto_fixable = $is_auto_fixable$expected_git_statuses$support_deprecated$related_files

    $obtain_invalid_content_items_method

    $fix_method
"""


class ValidationInitializer:
    def __init__(self):
        self.git_statuses = ""
        self.fix_method = ""
        self.fix_message = ""
        self.run_on_deprecated = ""
        self.min_content_type_val = 1
        self.max_content_type_val = int(list(CONTENT_TYPES_DICT.keys())[-1])
        self.using_graph = False

    def run_initializer(self):
        """
        Manage and run the script flow.
        """
        self.run_info_request_functions()
        self.run_generators_function()
        self.create_new_py_file()

    """ Info request functions """

    def run_info_request_functions(self):
        """
        calling all the info requesting functions
        """
        self.initialize_error_details()
        self.initialize_using_graph()
        self.initialize_validation_details()
        self.initialize_file_name()

    def initialize_error_details(self):
        """
        Calls all the methods that are related to error related fields.
        """
        self.initialize_error_code()
        self.initialize_error_description()
        self.initialize_validate_rationale()
        self.initialize_error_message()
        self.initialize_validator_related_field()

    def initialize_error_code(self):
        """
        Request the error_code from the user and validate the input is in the right format (two capital letters followed by 3 digits).
        """
        pattern = r"^[A-Z]{2}\d{3}$"
        self.error_code = str(
            input("Please enter the error code for the new validation: ")
        )
        while not re.match(pattern, self.error_code):
            self.error_code = str(
                input(
                    "The error code should be constructed from two capital letters followed by 3 digits: "
                )
            )

    def initialize_error_description(self):
        """
        Request the error's description from the user.
        """
        self.error_description = str(
            input(
                "Please enter the error's description or press enter to leave blank for now: "
            )
        )

    def initialize_validator_related_field(self):
        """
        Request the related_field from the user.
        """
        self.related_field = str(
            input(
                "Please enter the error's related_field or press enter to leave blank for now: "
            )
        )

    def initialize_validate_rationale(self):
        """
        Request the rationale from the user.
        """
        self.rationale = str(
            input(
                "Please enter the rationale for this validation; *why* do we have this validation? (not what it does)"
            )
        )

    def initialize_error_message(self):
        """
        Request the error_message from the user.
        """
        self.error_message = str(
            input(
                "Please enter the error's message or press enter to leave blank for now: "
            )
        )

    def initialize_validation_details(self):
        """
        Calls all the methods that are related to validation related fields.
        """
        self.initialize_validator_class_name()
        self.initialize_git_statuses()
        self.initialize_content_types()
        self.initialize_related_files()
        self.initialize_fix_info()

    def initialize_validator_class_name(self):
        """
        Request the validator class name and ensure the input is valid.
        """
        pascal_case_pattern = r"^[A-Z][a-z]+(?:[A-Z][a-z]+)*$"
        validator_class_name = str(
            input(
                "Please enter the validator's class name in PascalCase format (i.e each word with a capital letter): "
            )
        )
        while not validator_class_name or not bool(
            re.match(pascal_case_pattern, validator_class_name)
        ):
            validator_class_name = str(
                input(
                    "The class name must be filled, please enter a class name in PascalCase format (i.e each word with a capital letter): "
                )
            )
        if not validator_class_name.endswith("Validator"):
            validator_class_name = f"{validator_class_name}Validator"
        self.class_name = validator_class_name
        if not self.using_graph:
            self.class_declaration = (
                f"class {validator_class_name}(BaseValidator[ContentTypes]):"
            )
        else:
            self.class_declaration = (
                f"class {validator_class_name}(BaseValidator[ContentTypes], ABC):"
            )

    def initialize_git_statuses(self):
        """
        Request the supported git statuses and ensure the input is valid.
        """
        self.git_statuses_str = str(
            input(
                "Enter a comma separated list of git statuses the validation should run on,\n"
                "R: renamed files\nA: added files\nM: modified files\nor leave empty if you wish that the validation will run on all files: "
            )
        )
        while self.git_statuses_str and not set(
            self.git_statuses_str.split(",")
        ).issubset({"A", "R", "M"}):
            self.git_statuses_str = str(
                input(
                    "Please make sure to insert either valid inputs which are:\n"
                    "R: renamed files\nA: added files\nM: modified files\nor leave empty if you wish that the validation will run on all files: "
                )
            )

    def initialize_related_files(self):
        """
        Request the supported related_files and ensure the input is valid.
        """
        related_files = "\n".join(
            [f"{key}: {value}" for key, value in RELATED_FILES_DICT.items()]
        )
        self.related_files = str(
            input(
                f"Enter a comma separated list of related files the validation should run on or leave empty to run on the chosen main content item.\nThe related files are:\n{related_files}\nFill the content types as the numbers they appear as: "
            )
        )
        while self.related_files and not set().issubset(set(RELATED_FILES_DICT.keys())):
            self.related_files = str(
                input(
                    f"Please make sure to insert either valid inputs which are:\n{related_files}\nor leave empty if you wish that the validation will run on all files: "
                )
            )

    def initialize_content_types(self):
        """
        Request the supported content types list and ensure the input is valid.
        """
        supported_content_types = "\n".join(
            [
                f"{key}: {value.get('content_type')}"
                for key, value in CONTENT_TYPES_DICT.items()
            ]
        )
        content_types = str(
            input(
                f"""Enter a comma separated list of content types to be supported by the validation.
The supported types are:
{supported_content_types}
Fill the content types as the numbers they appear as: """
            )
        )
        while not self.is_valid_content_types_input(content_types):
            if not content_types:
                content_types = str(
                    input("Please make sure to enter at least one content type: ")
                )
            else:
                content_types = str(
                    input(
                        f"Please make sure all content types are valid integers between between {self.min_content_type_val} and {self.max_content_type_val}: "
                    )
                )
        self.content_types = content_types.split(",")

    def is_valid_content_types_input(self, content_types: str) -> bool:
        """Validate that the content types input is valid (at least one content type, and all inputs are in the content types range.)

        Args:
            content_types (str): comma separated list of the content_types input.

        Returns:
            bool: True if the input is valid, otherwise return False.
        """
        return bool(content_types) and all(
            [
                content_type.isnumeric()
                and self.min_content_type_val
                <= int(content_type)
                <= self.max_content_type_val
                for content_type in content_types.split(",")
            ]
        )

    def initialize_fix_info(self):
        """
        Request the info wether the validation is fixable or not and ensure the input is valid.
        """
        support_fix = str(input("does the validation support fix? (Y/N): "))
        while not support_fix or support_fix not in ["Y", "N", "y", "n"]:
            support_fix = str(
                input("Please enter wether the validation support fix or not? (Y/N): ")
            )
        if support_fix in ["Y", "y"]:
            self.support_fix = True
            fix_message = str(
                input(
                    "Please enter the fix message or press enter to leave blank for now: "
                )
            )
            self.fix_message = f'\n    fix_message = "{fix_message}"'
        else:
            self.support_fix = False

    def initialize_deprecation_info(self):
        """
        Request the info wether the validation should run on deprecated items or not.
        """
        run_on_deprecated = str(
            input("does the validation should run on deprecated items or not? (Y/N): ")
        )
        while not run_on_deprecated or run_on_deprecated not in ["Y", "N", "y", "n"]:
            run_on_deprecated = str(
                input(
                    "Please enter wether the validation should run on deprecated items or not? (Y/N): "
                )
            )
        if run_on_deprecated in ["Y", "y"]:
            self.run_on_deprecated = "\n    run_on_deprecated = True"

    def initialize_using_graph(self):
        """
        Request the info wether the validation is using graph or not and ensure the input is valid.
        """
        using_graph = str(input("does the validation used the graph object? (Y/N): "))
        while not using_graph or using_graph not in ["Y", "N", "y", "n"]:
            using_graph = str(
                input("Please enter wether the validation using graph or not? (Y/N): ")
            )
        if using_graph in ["Y", "y"]:
            self.using_graph = True

    def initialize_file_name(self):
        """
        Request the file name, ensure the given name is valid.
        """
        self.file_name = str(
            input(
                "Enter a file name in snake_case format or leave empty to generate a formatted name for the class name: "
            )
        )
        while " " in self.file_name:
            self.file_name = str(
                input(
                    "Please enter a valid file name in snake_case format without spaces or leave empty to generate a formatted name for the class name: "
                )
            )

    """ generators functions """

    def run_generators_function(self):
        """
        calling all the generators functions
        """
        self.generate_related_file_section()
        self.generate_git_section()
        self.generate_imports()
        self.generate_supported_content_types_section()
        self.generate_obtain_invalid_content_items_function()
        self.generate_fix_function()
        self.generate_file_info()
        if self.using_graph:
            self.using_graph_all_files_class = (
                self.Generate_files_according_execution_mode("AllFiles")
            )
            self.using_graph_list_files_class = (
                self.Generate_files_according_execution_mode("ListFiles")
            )

    def generate_related_file_section(self):
        """
        Generate the related_file section string.
        """
        if self.related_files:
            related_files_enum_ls = [
                RELATED_FILES_DICT[related_file]
                for related_file in self.related_files.split(",")
            ]
            related_files_enum_str = str(related_files_enum_ls).replace("'", "")
            self.related_files = f"\n    related_file_type = {related_files_enum_str}"

    def generate_git_section(self):
        """
        Generate the expected_git_statuses section string.
        """
        if self.git_statuses_str:
            git_statuses_enum_ls = [
                GIT_STATUSES_DICT[git_status]
                for git_status in self.git_statuses_str.split(",")
            ]
            git_statuses_enum_str = str(git_statuses_enum_ls).replace("'", "")
            self.git_statuses = f"\n    expected_git_statuses = {git_statuses_enum_str}"

    def generate_imports(self):
        """
        Generate the imports section string.
        """
        self.imports = "from __future__ import annotations\n\n"
        if self.using_graph:
            self.imports += "from abc import ABC\n\n"
        if len(self.content_types) == 1:
            self.imports += "from typing import Iterable, List\n\n"
        else:
            self.imports += "from typing import Iterable, List, Union\n\n"

        if self.git_statuses:
            self.imports += (
                "from demisto_sdk.commands.common.constants import GitStatuses\n"
            )
        self.related_files_imports = ""
        if self.related_files:
            self.related_files_imports += "from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType\n"
        for content_type in self.content_types:
            self.related_files_imports += (
                f"{CONTENT_TYPES_DICT.get(content_type, {}).get('import', '')}\n"
            )
        self.imports += self.related_files_imports
        fix_result_import = "FixResult,\n        " if self.support_fix else ""
        self.imports += f"""from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        {fix_result_import}ValidationResult,
)"""

    def generate_supported_content_types_section(self):
        """
        Generate the supported_content_types section string.
        """
        if len(self.content_types) == 1:
            self.supported_content_types = f"ContentTypes = {CONTENT_TYPES_DICT.get(self.content_types[0], {}).get('content_type', '')}"
        else:
            supported_content_types = [
                CONTENT_TYPES_DICT.get(content_type, {}).get("content_type", "")
                for content_type in self.content_types
            ]
            self.supported_content_types = (
                f"ContentTypes = Union{(supported_content_types)}"
            ).replace("'", "")

    def generate_obtain_invalid_content_items_function(self):
        """
        Generate the obtain_invalid_content_items function.
        """
        if not self.using_graph:
            self.obtain_invalid_content_items_method = """
    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
        """

        else:
            self.obtain_invalid_content_items_method = """
    def obtain_invalid_content_items_using_graph(self, content_items: Iterable[ContentTypes], validate_all_files: bool) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
        """

    def generate_fix_function(self):
        """
        Generate the fix function is fix is supported by the validation.
        """
        if self.support_fix:
            self.fix_method = """def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
            """

    def generate_file_info(self):
        """
        Generate the final file name and the dir path for the file, and the file path.
        """
        if not self.file_name:
            self.file_name = pascal_to_snake(self.class_declaration[6:-39])
        if not self.file_name.startswith(self.error_code):
            self.file_name = f"{self.error_code}_{self.file_name}"
        if self.file_name.endswith(".py"):
            self.file_name = f"{self.file_name[0:-3]}"
        dir_path = (
            f"demisto_sdk/commands/validate/validators/{self.error_code[:2]}_validators"
        )
        if not Path(dir_path).exists():
            os.makedirs(dir_path)
        self.file_path = f"{dir_path}/{self.file_name}"

    def Generate_files_according_execution_mode(self, execution_mode):
        """Generate files according to the execution_mode if using graph"""
        if execution_mode == "AllFiles":
            expected_execution_mode = "[ExecutionMode.ALL_FILES]"
            all_files = True
        else:
            expected_execution_mode = (
                "[ExecutionMode.SPECIFIC_FILES, ExecutionMode.USE_GIT]"
            )
            all_files = False
        return f"""
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
{self.related_files_imports}
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult

from demisto_sdk.commands.validate.validators.{self.error_code[:2]}_validators.{self.file_name} import {self.class_name}

{self.supported_content_types}


class {self.class_name}{execution_mode}({self.class_name}):
    expected_execution_mode = {expected_execution_mode}

    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items, {all_files})
        """

    """ Create new py file """

    def create_new_py_file(self):
        """
        insert all the information into the validation template and write the validation into a new py file with the given name under
        demisto_sdk/commands/validate/validators/<error_code_prefix>_validators.
        """
        with open(f"{self.file_path}.py", "w") as file:
            # Write the content into VALIDATION_TEMPLATE
            new_file_content = Template(VALIDATION_TEMPLATE).safe_substitute(
                imports=self.imports,
                supported_content_types=self.supported_content_types,
                class_declaration=self.class_declaration,
                error_code=self.error_code,
                error_description=self.error_description,
                rationale=self.rationale,
                error_message=self.error_message,
                fix_message=self.fix_message,
                related_field=self.related_field,
                is_auto_fixable=self.support_fix,
                expected_git_statuses=self.git_statuses,
                related_files=self.related_files,
                obtain_invalid_content_items_method=self.obtain_invalid_content_items_method,
                fix_method=self.fix_method,
                support_deprecated=self.run_on_deprecated,
            )
            file.write(new_file_content)

        if self.using_graph:
            with open(f"{self.file_path}_all_files.py", "w") as file:
                file.write(self.using_graph_all_files_class)
            with open(f"{self.file_path}_list_files.py", "w") as file:
                file.write(self.using_graph_list_files_class)


def main():
    try:
        logger.info("Creating a new validation")
        validation_initializer = ValidationInitializer()
        validation_initializer.run_initializer()
        logger.info(
            f"The validation was created successfully in {validation_initializer.file_path}"
        )
    except Exception as e:
        logger.error(
            f"Failed to create new validation, encountered the following error: {str(e)}"
        )


if __name__ == "__main__":
    main()
