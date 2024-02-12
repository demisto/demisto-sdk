import os
from pathlib import Path
from typing import Optional

from demisto_sdk.commands.common.constants import (
    PACK_METADATA_SUPPORT,
    PACKS_DIR,
    PACKS_PACK_META_FILE_NAME,
    FileType,
)
from demisto_sdk.commands.common.errors import (
    ALLOWED_IGNORE_ERRORS,
    FOUND_FILES_AND_ERRORS,
    FOUND_FILES_AND_IGNORED_ERRORS,
    PRESET_ERROR_TO_CHECK,
    PRESET_ERROR_TO_IGNORE,
    Errors,
    get_all_error_codes,
    get_error_object,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_file_displayed_name,
    get_json,
    get_pack_name,
    get_relative_path_from_packs_dir,
    get_yaml,
    str2bool,
)


def error_codes(error_codes_str: str):
    def error_codes_decorator(func):
        def wrapper(self, *args, **kwargs):
            if self.specific_validations:
                error_codes = error_codes_str.split(",")
                for error_code in error_codes:
                    if self.should_run_validation(error_code):
                        return func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)

            return True

        return wrapper

    return error_codes_decorator


class BaseValidator:
    def __init__(
        self,
        ignored_errors=None,
        print_as_warnings=False,
        json_file_path: Optional[str] = None,
        specific_validations: Optional[list] = None,
    ):
        # these are the ignored errors from the .pack-ignore including un-allowed error codes
        self.ignored_errors = ignored_errors or {}
        # these are the predefined ignored errors from packs which are partner/community support based.
        # represented by PRESET_ERROR_TO_IGNORE
        self.predefined_by_support_ignored_errors = {}  # type: ignore[var-annotated]
        # these are the predefined ignored errors from packs which are deprecated.
        # represented by PRESET_ERROR_TO_CHECK
        self.predefined_deprecated_ignored_errors = {}  # type: ignore[var-annotated]
        self.print_as_warnings = print_as_warnings
        self.checked_files = set()  # type: ignore
        self.json_file_path = json_file_path
        self.specific_validations = specific_validations

    @staticmethod
    def should_ignore_error(
        error_code,
        ignored_errors_pack_ignore,
        predefined_deprecated_ignored_errors,
        predefined_by_support_ignored_errors,
    ):
        """
        Determine if an error should be ignored or not. That includes all types of ignored errors,
        errors which come from .pack-ignore, pre-defined errors of partner/community packs and pre-defined errors
        of deprecated packs.

        Args:
            error_code (str): the error code of the validation.
            ignored_errors_pack_ignore (list[str]): a list of ignored errors which is
                part of the .pack-ignore that belongs to a specific file.
            predefined_deprecated_ignored_errors (list[str]): a list of ignored errors which are part of a deprecated
                content entity.
            predefined_by_support_ignored_errors (list[str)): a list of ignored errors which are part of the support
                level of a pack.

        Returns:
            True if error should be ignored, False if not.
        """
        error_type = error_code[:2]

        if (
            error_code in predefined_deprecated_ignored_errors
            or error_type in predefined_deprecated_ignored_errors
        ):
            return True

        if (
            error_code in predefined_by_support_ignored_errors
            or error_type in predefined_by_support_ignored_errors
        ):
            return True

        return (
            error_code in ignored_errors_pack_ignore
            or error_type in ignored_errors_pack_ignore
        ) and (error_code in ALLOWED_IGNORE_ERRORS)

    @staticmethod
    def is_error_not_allowed_in_pack_ignore(error_code, ignored_errors_pack_ignore):
        """
        Determine whether an error code that is in the .pack-ignore should not be ignored.

         Args:
            error_code (str): the error code of the validation.
            ignored_errors_pack_ignore (list[str]): a list of ignored errors which
                should be ignored in the file (a single row).

        Returns:
            True if error code can not be ignored, False otherwise.
        """
        error_type = error_code[:2]
        return (
            error_code in ignored_errors_pack_ignore
            or error_type in ignored_errors_pack_ignore
        ) and (error_code not in ALLOWED_IGNORE_ERRORS)

    def should_run_validation(self, error_code: str):
        if not self.specific_validations:
            return True
        return (
            error_code in self.specific_validations
            or error_code[:2] in self.specific_validations
        )

    def handle_error(
        self,
        error_message,
        error_code,
        file_path,
        suggested_fix=None,
        warning=False,
        drop_line=False,
        ignored_errors=None,
    ):
        """
        Handle an error that occurred during validation.

        Args:
            drop_line (bool): Whether to drop a line at the beginning of the error message
            warning (bool): Print the error as a warning
            suggested_fix (str): A suggested fix
            error_message (str): The error message
            file_path (str): The file from which the error occurred
            error_code (str): The error code
            ignored_errors (dict): if there are any ignored_errors, will override the ignored_errors attribute.

        Returns:
            str: formatted error message, None in case validation should be skipped or can be ignored.
        """
        if ignored_errors:
            self.ignored_errors = ignored_errors

        if self.specific_validations:
            if not self.should_run_validation(error_code):
                # if the error code is not specified in the
                # specific_validations list, we exit the function and return None
                return None

        def formatted_error_str():
            formatted_error_message_prefix = f"{file_path}: [{error_code}]"
            if is_error_not_allowed_in_pack_ignore:
                formatted = f"{formatted_error_message_prefix} can not be ignored in .pack-ignore\n"
            else:
                formatted = (
                    f"{formatted_error_message_prefix} - {error_message}".rstrip("\n")
                    + "\n"
                )
            if drop_line:
                formatted = "\n" + formatted
            return formatted

        if file_path:
            if not isinstance(file_path, str):
                file_path = str(file_path)

            file_name = Path(file_path).name
            try:
                self.check_file_flags(file_name, file_path)
            except FileNotFoundError:
                logger.info(
                    f"[yellow]File {file_path} not found, cannot check its flags (deprecated, etc)[/yellow]"
                )

            rel_file_path = get_relative_path_from_packs_dir(file_path)

        else:
            file_name = "No-Name"
            rel_file_path = "No-Name"

        ignored_errors_pack_ignore = (
            self.ignored_errors.get(file_name)
            or self.ignored_errors.get(rel_file_path)
            or []
        )
        predefined_deprecated_ignored_errors = (
            self.predefined_deprecated_ignored_errors.get(file_name)
            or self.predefined_deprecated_ignored_errors.get(rel_file_path)
            or []
        )
        predefined_by_support_ignored_errors = (
            self.predefined_by_support_ignored_errors.get(file_path)
            or self.predefined_by_support_ignored_errors.get(rel_file_path)
            or []
        )

        is_error_not_allowed_in_pack_ignore = self.is_error_not_allowed_in_pack_ignore(
            error_code=error_code, ignored_errors_pack_ignore=ignored_errors_pack_ignore
        )

        if (
            self.should_ignore_error(
                error_code,
                ignored_errors_pack_ignore,
                predefined_deprecated_ignored_errors,
                predefined_by_support_ignored_errors,
            )
            or warning
        ):
            if self.print_as_warnings or warning:
                logger.warning(f"[yellow]{formatted_error_str()}[/yellow]")
                self.json_output(file_path, error_code, error_message, warning)
                self.add_to_report_error_list(
                    error_code, file_path, FOUND_FILES_AND_IGNORED_ERRORS
                )
            return None

        formatted_error = formatted_error_str()
        if suggested_fix and not is_error_not_allowed_in_pack_ignore:
            logger.error(f"[red]{formatted_error[:-1]}[/red]")
            if error_code == "ST109":
                logger.info("[red]Please add to the root of the yml.[/red]\n")
            elif error_code == "ST107":
                missing_field = error_message.split(" ")[3]
                path_to_add = error_message.split(":")[1]
                logger.info(
                    f"[red]Please add the field {missing_field} to the path: {path_to_add} in the yml.[/red]\n"
                )
            else:
                logger.info(f"[red]{suggested_fix}[/red]\n")

        else:
            logger.error(f"[red]{formatted_error}[/red]")

        self.json_output(file_path, error_code, error_message, warning)
        self.add_to_report_error_list(error_code, file_path, FOUND_FILES_AND_ERRORS)
        if (not warning) and str2bool(
            os.getenv("GITHUB_ACTIONS")
        ):  # warnings are not printed
            github_annotation_message = (
                f"{error_message}\n{suggested_fix}" if suggested_fix else error_message
            ).replace(
                "\n", "%0A"
            )  # GitHub action syntax
            print(  # noqa: T201
                f"::error file={file_path},line=1,endLine=1,title=Validation Error {error_code}::{github_annotation_message}"
            )
        return formatted_error

    def check_file_flags(self, file_name, file_path):
        if file_name not in self.checked_files:
            self.check_deprecated(file_path)
            self.update_checked_flags_by_support_level(file_path)
            self.checked_files.add(file_name)

    def check_deprecated(self, file_path):
        if file_path.endswith(".yml"):
            yml_dict = get_yaml(file_path, keep_order=False)
            if not isinstance(yml_dict, list) and yml_dict.get("deprecated"):
                # yml files may be list or dict-like
                self.add_flag_to_ignore_list(file_path, "deprecated")

    @staticmethod
    def get_metadata_file_content(meta_file_path):
        if not Path(meta_file_path).exists():
            return {}
        return get_json(meta_file_path)

    def update_checked_flags_by_support_level(self, file_path):
        pack_name = get_pack_name(file_path)
        if pack_name:
            metadata_path = os.path.join(
                PACKS_DIR, pack_name, PACKS_PACK_META_FILE_NAME
            )
            metadata_json = self.get_metadata_file_content(metadata_path)
            support = metadata_json.get(PACK_METADATA_SUPPORT)

            if support in ("partner", "community"):
                self.add_flag_to_ignore_list(file_path, support)

    @staticmethod
    def create_reverse_ignored_errors_list(errors_to_check):
        ignored_error_list = []
        all_errors = get_all_error_codes()
        for error_code in all_errors:
            error_type = error_code[:2]
            if error_code not in errors_to_check and error_type not in errors_to_check:
                ignored_error_list.append(error_code)

        return ignored_error_list

    def add_flag_to_ignore_list(self, file_path, flag):
        if flag in PRESET_ERROR_TO_IGNORE:
            for predefined_error_code in PRESET_ERROR_TO_IGNORE[flag]:
                if file_path not in self.predefined_by_support_ignored_errors:
                    self.predefined_by_support_ignored_errors[file_path] = []
                self.predefined_by_support_ignored_errors[file_path].append(
                    predefined_error_code
                )

        elif flag in PRESET_ERROR_TO_CHECK:
            deprecated_ignored_errors = self.create_reverse_ignored_errors_list(
                PRESET_ERROR_TO_CHECK[flag]
            )
            for ignored_error in deprecated_ignored_errors:
                if file_path not in self.predefined_deprecated_ignored_errors:
                    self.predefined_deprecated_ignored_errors[file_path] = []
                self.predefined_deprecated_ignored_errors[file_path].append(
                    ignored_error
                )

    @staticmethod
    def add_to_report_error_list(error_code, file_path, error_list) -> bool:
        formatted_file_and_error = f"{file_path} - [{error_code}]"
        if formatted_file_and_error not in error_list:
            error_list.append(formatted_file_and_error)
            return True
        return False

    def json_output(
        self, file_path: str, error_code: str, error_message: str, warning: bool
    ) -> None:
        """Adds an error's info to the output JSON file

        Args:
            file_path (str): The file path where the error ocurred.
            error_code (str): The error code
            error_message (str): The error message
            warning (bool): Whether the error is defined as a warning
        """
        if not self.json_file_path:
            return

        error_data = get_error_object(error_code)

        output = {
            "severity": "warning" if warning else "error",
            "errorCode": error_code,
            "message": error_message,
            "relatedField": error_data.get("related_field"),
            "linter": "validate",
        }

        json_contents = []
        existing_json = ""
        if Path(self.json_file_path).exists():
            try:
                existing_json = get_json(self.json_file_path)
            except ValueError:
                pass
            if isinstance(existing_json, list):
                json_contents = existing_json

        file_type = find_type(file_path)
        entity_type = file_type.value if file_type else "pack"

        # handling unified yml image errors
        if entity_type == FileType.INTEGRATION.value and error_code.startswith("IM"):
            entity_type = FileType.IMAGE.value

        formatted_error_output = {
            "filePath": file_path,
            "fileType": os.path.splitext(file_path)[1].replace(".", ""),
            "entityType": entity_type,
            "errorType": "Settings",
            "name": get_file_displayed_name(file_path),
            "linter": "validate",
            **output,
        }
        json_contents.append(formatted_error_output)
        with open(self.json_file_path, "w") as f:
            json.dump(json_contents, f, indent=4)

    @staticmethod
    def validate_xsiam_content_item_title(file_path):
        file_path_object = Path(file_path)
        file_type = find_type(file_path)
        file_name = str(file_path_object.stem)
        dir_name = str(file_path_object.parent.stem)
        pack_name = get_pack_name(file_path)
        if file_type in {
            FileType.XDRC_TEMPLATE,
            FileType.XDRC_TEMPLATE_YML,
            FileType.MODELING_RULE,
            FileType.PARSING_RULE,
            FileType.XIF_FILE,
            FileType.MODELING_RULE_XIF,
            FileType.PARSING_RULE_XIF,
        }:
            if file_name != dir_name:
                return False
        elif file_type in {
            FileType.CORRELATION_RULE,
            FileType.XSIAM_DASHBOARD,
            FileType.XSIAM_REPORT,
            FileType.XSIAM_REPORT_IMAGE,
            FileType.XSIAM_DASHBOARD_IMAGE,
        }:
            if not file_name.startswith(f"{pack_name}_"):
                return False
        elif file_type == FileType.MODELING_RULE_SCHEMA:
            schema_expected_name = f"{dir_name}_schema"
            if file_name != schema_expected_name:
                return False
        return True

    @error_codes("BA125")
    def validate_no_disallowed_terms_in_customer_facing_docs(
        self, file_content: str, file_path: str
    ) -> bool:
        """
        Validate that customer facing docs and fields don't contain any internal terms that aren't clear for customers.

        Args:
            file_content (str): The content of the file to check.
            file_path (str): The path of the file the content belongs to.

        Returns:
            bool: True if no such terms were found, False otherwise.
        """
        disallowed_terms = (
            [  # These terms are checked regardless for case (case-insensitive)
                "test-module",
                "test module",
                "long-running-execution",
            ]
        )

        found_terms = []

        # Search for terms
        for term in disallowed_terms:
            if term.casefold() in file_content.casefold():
                found_terms.append(term)

        # Raise error if disallowed terms found
        if found_terms:
            error_message, error_code = Errors.customer_facing_docs_disallowed_terms(
                found_terms=found_terms
            )

            if self.handle_error(
                error_message,
                error_code,
                file_path=file_path,
            ):
                return False
        return True
