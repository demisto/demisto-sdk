import glob
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.common.constants import (
    BETA_INTEGRATION_DISCLAIMER,
    PACKS_INTEGRATION_YML_REGEX,
    FileType,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.hook_validations.readme import mdx_server_is_up
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.markdown_lint import run_markdownlint
from demisto_sdk.commands.common.tools import find_type, get_yaml, os, re

CONTRIBUTOR_DETAILED_DESC = "Contributed Integration"


class DescriptionValidator(BaseValidator):
    """DescriptionValidator was designed to make sure we provide a detailed description properly.

    Attributes:
        file_path (string): Path to the checked file.
        _is_valid (bool): the attribute which saves the valid/in-valid status of the current file.
    """

    def __init__(
        self,
        file_path: str,
        ignored_errors=None,
        json_file_path: Optional[str] = None,
        specific_validations: Optional[List[str]] = None,
    ):
        super().__init__(
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )
        self._is_valid = True
        # Handling a case where the init function initiated with file path instead of structure validator
        self.file_path = (
            file_path.file_path
            if isinstance(file_path, StructureValidator)
            else file_path
        )
        self.data_dictionary = (
            get_yaml(self.file_path)
            if find_type(self.file_path)
            in [FileType.INTEGRATION, FileType.BETA_INTEGRATION]
            else {}
        )

    def is_valid_file(self):
        self.is_duplicate_description()

        # Validations that will run only on Markdown file
        if (
            not self.data_dictionary.get("detaileddescription")
            and ".md" in self.file_path
        ):
            with open(self.file_path) as f:
                file_content = f.read()

            self.is_valid_description_name()
            # self.has_markdown_lint_errors(file_content=file_content)
            self.contains_contrib_details(file_content=file_content)
            if not self.validate_no_disallowed_terms_in_customer_facing_docs(
                file_content=file_content, file_path=self.file_path
            ):
                self._is_valid = False

        return self._is_valid

    @error_codes("DS105")
    def contains_contrib_details(self, file_content: str):
        """check if DESCRIPTION file contains contribution details"""
        contrib_details = re.findall(
            rf"### .* {CONTRIBUTOR_DETAILED_DESC}", file_content
        )
        if contrib_details:
            error_message, error_code = Errors.description_contains_contrib_details()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                self._is_valid = False
                return False
        return True

    @error_codes("DS100,DS101,DS102")
    def is_valid_beta_description(self):
        """Check if beta disclaimer exists in detailed description"""
        description_in_yml = (
            self.data_dictionary.get("detaileddescription", "")
            if self.data_dictionary
            else ""
        )
        is_unified_integration = self.data_dictionary.get("script", {}).get(
            "script", ""
        ) not in {"-", ""}

        if not is_unified_integration:
            try:
                md_file_path = glob.glob(
                    os.path.join(os.path.dirname(self.file_path), "*_description.md")
                )[0]
            except IndexError:
                (
                    error_message,
                    error_code,
                ) = Errors.description_missing_in_beta_integration()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self._is_valid = False
                    return False

            with open(md_file_path) as description_file:
                description = description_file.read()
            if BETA_INTEGRATION_DISCLAIMER not in description:
                error_message, error_code = Errors.no_beta_disclaimer_in_description()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self._is_valid = False
                    return False
            else:
                return True

        # unified integration case
        elif BETA_INTEGRATION_DISCLAIMER not in description_in_yml:
            error_message, error_code = Errors.no_beta_disclaimer_in_yml()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False

        return True

    @error_codes("DS104,DS103")
    def is_duplicate_description(self):
        """Check if the integration has a non-duplicate description ."""
        is_description_in_yml = False
        is_description_in_package = False
        package_path = None
        md_file_path = None

        file_path = Path(self.file_path)

        if not re.match(PACKS_INTEGRATION_YML_REGEX, self.file_path, re.IGNORECASE):
            package_path = str(file_path.parent)
            try:
                base_name_without_extension: str = file_path.stem.replace(
                    "_description", ""
                )

                expected_description_name: str = str(
                    Path(
                        str(file_path.parent),
                        f"{base_name_without_extension}_description.md",
                    )
                )
                md_file_path = glob.glob(expected_description_name)[0]
            except IndexError:
                is_unified_integration = self.data_dictionary.get("script", {}).get(
                    "script", ""
                ) not in {"-", ""}
                if not (
                    self.data_dictionary.get("deprecated") or is_unified_integration
                ):
                    error_message, error_code = Errors.no_description_file_warning()
                    self.handle_error(
                        error_message,
                        error_code,
                        file_path=self.file_path,
                        warning=True,
                    )

            if md_file_path:
                is_description_in_package = True

        if not self.data_dictionary:
            return is_description_in_package

        if self.data_dictionary.get("detaileddescription"):
            is_description_in_yml = True

        if is_description_in_package and is_description_in_yml:
            error_message, error_code = Errors.description_in_package_and_yml()
            if self.handle_error(error_message, error_code, file_path=package_path):
                self._is_valid = False
                return False

        return True

    @error_codes("DS106")
    def is_valid_description_name(self):
        """Check if the description name is valid"""
        description_path = glob.glob(
            os.path.join(os.path.dirname(self.file_path), "*_description.md")
        )
        md_paths = glob.glob(os.path.join(os.path.dirname(self.file_path), "*.md"))

        description_file_path = self.file_path
        integrations_folder = Path(description_file_path).parent.name
        description_file = Path(description_file_path).name

        # drop file extension
        description_file_base_name = description_file.rsplit("_", 1)[0]

        # checking if there are any .md files only for description with a wrong name
        for path in md_paths:
            if path.endswith("README.md") or path.endswith("CHANGELOG.md"):
                md_paths.remove(path)

        if (
            not description_path
            and md_paths
            or integrations_folder != description_file_base_name
        ):
            error_message, error_code = Errors.invalid_description_name()

            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False

        return True

    def has_markdown_lint_errors(self, file_content: str):
        if mdx_server_is_up():
            markdown_response = run_markdownlint(file_content)
            if markdown_response.has_errors:
                error_message, error_code = Errors.description_lint_errors(
                    self.file_path, markdown_response.validations
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    self._is_valid = False
                    return False
        return True
