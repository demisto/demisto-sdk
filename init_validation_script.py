import re
from string import Template

from demisto_sdk.commands.common.logger import logger

validation_template = f"""
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.wizard import Wizard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixingResult,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Dashboard,
    IncidentType,
    Layout,
    Mapper,
    Playbook,
    Script,
    Wizard,
    Classifier,
]


class IDNameValidator(BaseValidator[ContentTypes]):
    error_code = "$error_code"
    description = "$error_description"
    error_message = "$error_message"
    fixing_message = "Changing name to be equal to id ({0})."
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

    def fix(self, content_item: ContentTypes, _) -> FixingResult:
        content_item.name = content_item.object_id
        return FixingResult(
            validator=self,
            message=self.fixing_message.format(content_item.object_id),
            content_object=content_item,
        )
"""
class ValidationInitializer():
    def init(self):
        self.error_code = None
        self.description = ""
        self.error_message = ""
        self.get_error_details()
        self.get_validation_details()
        # self.get_file_name()
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
            new_file_content = Template(validation_template).safe_substitute(error_code = self.error_code)
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
            if not "A" in self.git_statuses and not "D" in self.git_statuses:
                self.include_old_format_files = True
            else:
                self.git_statuses = 
                
def main():
    logger.info("Creating a new validation")
    validation_initializer = ValidationInitializer()
    validation_initializer.init()
                
if __name__ == "__main__":
    main()
