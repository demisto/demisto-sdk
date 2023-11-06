import re
from string import Template

from demisto_sdk.commands.common.logger import logger

CONTENT_TYPES_DICT = {
    "1": {
        "import": "from demisto_sdk.commands.content_graph.objects.integration import Integration",
        "content_type": "Integration"
    },
    "2": {
        "import": "from demisto_sdk.commands.content_graph.objects.script import Script",
        "content_type": "Script"
    },
    "3": {
        "import": "from demisto_sdk.commands.content_graph.objects.playbook import Playbook",
        "content_type": "Playbook"
    },
    "4": {
        "import": "from demisto_sdk.commands.content_graph.objects.pack import Pack",
        "content_type": "Pack"
    },
    "5": {
        "import": "from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard",
        "content_type": "Dashboard"
    },
    "6": {
        "import": "from demisto_sdk.commands.content_graph.objects.classifier import Classifier",
        "content_type": "Classifier"
    },
    "7": {
        "import": "from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType",
        "content_type": "IncidentType"
    },
    "8": {
        "import": "from demisto_sdk.commands.content_graph.objects.layout import Layout",
        "content_type": "Layout"
    },
    "9": {
        "import": "from demisto_sdk.commands.content_graph.objects.mapper import Mapper",
        "content_type": "Mapper"
    },
    "10": {
        "import": "from demisto_sdk.commands.content_graph.objects.wizard import Wizard",
        "content_type": "Wizard"
    },
    "11": {
        "import": "from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule",
        "content_type": "CorrelationRule"
    },
    "12": {
        "import": "from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField",
        "content_type": "IncidentField"
    },
    "13": {
        "import": "from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType",
        "content_type": "IncidentType"
    },
    "14": {
        "import": "from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField",
        "content_type": "IndicatorField"
    },
    "15": {
        "import": "from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType",
        "content_type": "IndicatorType"
    },
    "16": {
        "import": "from demisto_sdk.commands.content_graph.objects.layout_rule import LayoutRule",
        "content_type": "LayoutRule"
    },
    "17": {
        "import": "from demisto_sdk.commands.content_graph.objects.layout import Layout",
        "content_type": "Layout"
    },
    "18": {
        "import": "from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule",
        "content_type": "ModelingRule"
    },
    "19": {
        "import": "from demisto_sdk.commands.content_graph.objects.parsing_Rule import ParsingRule",
        "content_type": "ParsingRule"
    },
    "20": {
        "import": "from demisto_sdk.commands.content_graph.objects.report import Report",
        "content_type": "Report"
    },
    "21": {
        "import": "from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook",
        "content_type": "TestPlaybook"
    },
    "22": {
        "import": "from demisto_sdk.commands.content_graph.objects.trigger import Trigger",
        "content_type": "Trigger"
    },
    "23": {
        "import": "from demisto_sdk.commands.content_graph.objects.widget import Widget",
        "content_type": "Widget"
    },
    "24": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_definition import GenericDefinition",
        "content_type": "GenericDefinition"
    },
    "25": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_field import GenericField",
        "content_type": "GenericField"
    },
    "26": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_module import GenericModule",
        "content_type": "GenericModule"
    },
    "27": {
        "import": "from demisto_sdk.commands.content_graph.objects.generic_type import GenericType",
        "content_type": "GenericType"
    },
    "28": {
        "import": "from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard",
        "content_type": "XSIAMDashboard"
    },
    "29": {
        "import": "from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport",
        "content_type": "XSIAMReport"
    }
}

VALIDATION_TEMPLATE = """
from __future__ import annotations

$imports

$content_types


class IDNameValidator(BaseValidator[ContentTypes]):
    error_code = "$error_code"
    description = "$error_description"
    error_message = "$error_message"
    fixing_message = $fix_message
    related_field = "$related_field"
    $expected_git_statuses

    def is_valid(
        self, content_items: Iterable[ContentTypes], _
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.object_id, content_item.name
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.object_id != content_item.name
        ]

    $fix_method
"""
class ValidationInitializer():
    def init(self):
        self.error_code = None
        self.description = ""
        self.error_message = ""
        self.fix_method = ""
        self.include_old_format_files = False
        self.get_error_details()
        self.get_validation_details()
        # self.get_file_name()
        self.get_fix_info()
        self.process_inputs()
        self.generate_new_py_file()

    def get_error_details(self):
        self.get_error_code()
        self.get_description()
        self.get_error_message()
        self.get_validator_related_field()
        
    def get_error_code(self):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        pattern = r'^[A-Z]{2}\d{3}$'
        self.error_code = str(
            input("Please enter the error code for the new validation: ")
        )
        while not re.match(pattern, self.error_code):
            self.error_code = str(
                input(
                    "The error code should be constructed from two capital letters followed by 3 digits: "
                )
            )
            
    def get_description(self):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        self.description = str(
            input("Please enter the error's description: ")
        )
        while not self.description or self.description.isspace():
            self.description = str(
                input(
                    "The description must be filled, please enter a description again: "
                )
            )
            
    def get_validator_related_field(self):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        self.related_field = str(
            input("Please enter the error's related_field: ")
        )
        while not self.related_field or self.related_field.isspace():
            self.description = str(
                input(
                    "The related_field must be filled, please enter a description again: "
                )
            )
            
    def get_error_message(self):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        self.error_message = str(
            input("Please enter the error's message: ")
        )
        while not self.error_message or self.error_message.isspace():
            self.error_message = str(
                input(
                    "the error's message must be filled, please enter an error message again: "
                )
            )
    
    def generate_new_py_file(self):
        file_name = "new_script.py"
        with open(file_name, "w") as file:
            # Write the content into the file
            new_file_content = Template(VALIDATION_TEMPLATE).safe_substitute(error_code = self.error_code)
            file.write(new_file_content)
        
    def get_validation_details(self):
        self.get_validator_class_name()
        self.get_git_statuses()
        self.get_content_types()
        self.is_based_on_previous_versions()
    
    def get_validator_class_name(self):
        """Makes sure a name is given for the created object
        """
        self.validator_class_name = str(
            input("Please enter the validator's class name in class format (i.e each word with a capital letter): ")
        )
        while not self.validator_class_name or self.validator_class_name.isspace():
            self.validator_class_name = str(
                input(
                    "the error's message must be filled, please enter an error message again: "
                )
            )
        if not self.validator_class_name.endswith("Validator"):
            self.validator_class_name = f"{self.validator_class_name}Validator"
            
    def get_git_statuses(self):
        """Makes sure a name is given for the created object
        """
        git_statuses = str(
            input("Enter a comma separated list of git statuses the validation should run on,\n"
                  "R: renamed files\nA: added files\nD: deleted files\nM: modified files\nor leave empty if you wish that the validation will run on all files.")
        )
        if git_statuses:
            self.git_statuses = git_statuses.split(",")
            if "A" not in self.git_statuses and "D" not in self.git_statuses:
                self.include_old_format_files_is_valid_method  = ", old_content_items: Iterable[Optional[ContentTypes]]"
                self.include_old_format_files_fix_method = ", old_content_item: ContentTypes"
        else:
            self.include_old_format_files_is_valid_method = ", _"
            self.include_old_format_files_fix_method = ", _"
            self.git_statuses = None
    
    def get_content_types(self):
        """Makes sure a name is given for the created object
        """
        supported_content_types = [f"{key}: {value.get("content_type")}" for key, value in CONTENT_TYPES_DICT.items()]
        content_types = str(
            input("Enter a comma separated list of content types to be supported by the validation.\n"
                  f"The supported types are {supported_content_types.split("\n")}")
        )
        while not content_types:
            content_types = str(input("Please enter at least one content type:"))
        self.content_types = content_types.split(",")
        
    def process_inputs(self):
        self.process_content_types()
        
    def process_content_types(self):
        if len (self.content_types) == 1:
            self.supported_content_types = f"ContentTypes = {self.content_types}"
            self.imports = "from typing import Iterable, List\n\n"
        else:
            self.supported_content_types = f"ContentTypes = {','.join(self.content_types)}"
            self.imports = "from typing import Iterable, List, Union\n\n"
        for content_type in self.content_types:
            self.imports += f"{CONTENT_TYPES_DICT.get(content_type, {}).get('import', "")}\n"
            
    def process_fix_result_related_fields(self):
        if self.support_fix:
            self.imports += """from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        FixingResult,
        ValidationResult,
    )"""
            self.fix_method = f"""def fix(self, content_item: ContentTypes{self.include_old_format_files_fix_method}) -> FixResult:
        # Add your fix right here
        pass
            """
        else:
            self.imports += """from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
    )"""

    def get_fix_info(self):
        support_fix = str(
            input("does the validation support fix? (Y/N):")
        )
        while not support_fix and support_fix not in ["Y", "N", "y", "n"]:
            support_fix = str(input("Please enter wether the validation support fix or not? (Y/N):"))
        if support_fix in ["Y", "y"]:
            self.support_fix = True
        else:
            self.support_fix = False
                    
                
def main():
    logger.info("Creating a new validation")
    validation_initializer = ValidationInitializer()
    validation_initializer.init()
                
if __name__ == "__main__":
    main()
