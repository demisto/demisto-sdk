"""
This module is designed to validate the existence and structure of content pack essential files in content.
"""

import os
import re
from pathlib import Path
from typing import Dict, Tuple

from dateutil import parser
from git import GitCommandError
from packaging.version import Version, parse

from demisto_sdk.commands.common.constants import (  # PACK_METADATA_PRICE,
    API_MODULES_PACK,
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    EXCLUDED_DISPLAY_NAME_WORDS,
    INCORRECT_PACK_NAME_PATTERN,
    INTEGRATIONS_DIR,
    MANDATORY_PACK_METADATA_FIELDS,
    MARKETPLACE_KEY_PACK_METADATA,
    MODULES,
    PACK_METADATA_CATEGORIES,
    PACK_METADATA_CERTIFICATION,
    PACK_METADATA_CREATED,
    PACK_METADATA_CURR_VERSION,
    PACK_METADATA_DEPENDENCIES,
    PACK_METADATA_DESC,
    PACK_METADATA_EMAIL,
    PACK_METADATA_MANDATORY_FILLED_FIELDS,
    PACK_METADATA_MODULES,
    PACK_METADATA_NAME,
    PACK_METADATA_SUPPORT,
    PACK_METADATA_URL,
    PACK_METADATA_USE_CASES,
    PACK_SUPPORT_OPTIONS,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME,
    PACKS_README_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME,
    PARTNER_SUPPORT,
    SUPPORTED_CONTRIBUTORS_LIST,
    VERSION_REGEX,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.errors import ALLOWED_IGNORE_ERRORS, Errors
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    check_timestamp_format,
    extract_error_codes_from_file,
    get_core_pack_list,
    get_current_usecases,
    get_json,
    get_local_remote_file,
    get_pack_latest_rn_version,
    get_remote_file,
    is_external_repository,
    pack_name_to_path,
)
from demisto_sdk.commands.find_dependencies.find_dependencies import PackDependencies
from demisto_sdk.commands.validate.tools import (
    extract_non_approved_tags,
    filter_by_marketplace,
)

ALLOWED_CERTIFICATION_VALUES = ["certified", "verified"]
MAXIMUM_DESCRIPTION_FIELD_LENGTH = 130


class BlockingValidationFailureException(BaseException):
    """
    Used for blocking other validations from being run, force-stopping the validation process.
    For example, when a required file is missing. Raise it after adding a suitable error to self._errors.
    """

    pass


class PackUniqueFilesValidator(BaseValidator):
    """PackUniqueFilesValidator is designed to validate the correctness of content pack's files structure.
    Existence and validity of this files is essential."""

    def __init__(
        self,
        pack,
        pack_path=None,
        validate_dependencies=False,
        ignored_errors=None,
        should_version_raise=False,
        id_set_path=None,
        private_repo=False,
        skip_id_set_creation=False,
        prev_ver=None,
        json_file_path=None,
        support=None,
        specific_validations=None,
    ):
        """Inits the content pack validator with pack's name, pack's path, and unique files to content packs such as:
        secrets whitelist file, pack-ignore file, pack-meta file and readme file
        :param pack: content package name, which is the directory name of the pack
        """
        super().__init__(
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )
        self.pack = pack
        self.pack_path = pack_name_to_path(self.pack) if not pack_path else pack_path
        self.secrets_file = PACKS_WHITELIST_FILE_NAME
        self.pack_ignore_file = PACKS_PACK_IGNORE_FILE_NAME
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        self.readme_file = PACKS_README_FILE_NAME
        self.validate_dependencies = validate_dependencies
        self._errors = []
        self.should_version_raise = should_version_raise
        self.id_set_path = id_set_path
        self.private_repo = private_repo
        self.skip_id_set_creation = skip_id_set_creation
        self.support = support
        self.metadata_content: Dict = dict()

        if not prev_ver:
            git_util = Content.git_util()
            main_branch = git_util.handle_prev_ver()[1]
            self.prev_ver = (
                f"{DEMISTO_GIT_UPSTREAM}/{main_branch}"
                if not main_branch.startswith(DEMISTO_GIT_UPSTREAM)
                else main_branch
            )
        else:
            self.prev_ver = prev_ver

    # error handling

    def _add_error(
        self,
        error: Tuple[str, str],
        file_path: str,
        warning=False,
        suggested_fix=None,
    ):
        """Adds error entry to a list under pack's name
        Returns True if added and false otherwise"""
        error_message, error_code = error

        if self.pack_path not in file_path:
            file_path = os.path.join(self.pack_path, file_path)

        formatted_error = self.handle_error(
            error_message,
            error_code,
            file_path=file_path,
            warning=warning,
            suggested_fix=suggested_fix,
        )
        if formatted_error:
            self._errors.append(formatted_error)
            return True

        return False

    def get_errors(self, raw=False) -> str:
        """Get the dict version or string version for print"""
        errors = ""
        if raw:
            errors = "\n  ".join(self._errors)
        elif self._errors:
            errors = " - Issues with unique files in pack: {}\n  {}".format(
                self.pack, "\n  ".join(self._errors)
            )

        return errors

    # file utils
    def _get_pack_file_path(self, file_name=""):
        """Returns the full file path to pack's file"""
        return os.path.join(self.pack_path, file_name)

    @error_codes("PA128,PA100")
    def _is_pack_file_exists(self, file_name: str, is_required: bool = False):
        """
        Check if a file with given name exists in pack root.
        is_required is True means that absence of the file should block other tests from running
            (see BlockingValidationFailureException).
        """
        if not Path(self._get_pack_file_path(file_name)).is_file():
            error_function = (
                Errors.required_pack_file_does_not_exist
                if is_required
                else Errors.pack_file_does_not_exist
            )
            if self._add_error(error_function(file_name), file_name):
                if is_required:
                    raise BlockingValidationFailureException()
                return False
        return True

    def _read_file_content(self, file_name):
        """Open & Read a file object's content throw exception if can't"""
        try:
            with open(self._get_pack_file_path(file_name), encoding="utf-8") as file:
                return file.read()
        except OSError:
            if not self._add_error(Errors.cant_open_pack_file(file_name), file_name):
                return "No-Text-Required"
        except ValueError:
            if not self._add_error(Errors.cant_read_pack_file(file_name), file_name):
                return "No-Text-Required"

        return False

    def _read_metadata_content(self) -> Dict:
        """
        Reads metadata content. Avoids the duplication of file opening in case metadata was already opened once.
        Returns:
            (Dict): Metadata JSON pack file content.
        """
        if not self.metadata_content:
            pack_meta_file_content = self._read_file_content(self.pack_meta_file)
            self.metadata_content = json.loads(pack_meta_file_content)
        return self.metadata_content

    def _parse_file_into_list(self, file_name, delimiter="\n"):
        """Parse file's content to list, throw exception if can't"""
        file_content = self._read_file_content(file_name)
        try:
            if file_content:
                return file_content.split(delimiter)
        except ValueError:
            if not self._add_error(
                Errors.cant_parse_pack_file_to_list(file_name), file_name
            ):
                return True

        return False

    def check_metadata_for_marketplace_change(self):
        """Return True if pack_metadata's marketplaces field was changed."""
        metadata_file_path = self._get_pack_file_path(self.pack_meta_file)
        if not Path(metadata_file_path).is_file():
            # No metadata file, No marketplace change.
            return False

        old_meta_file_content = get_remote_file(metadata_file_path, tag=self.prev_ver)
        current_meta_file_content = self._read_metadata_content()
        old_marketplaces = old_meta_file_content.get("marketplaces", [])
        current_marketplaces = current_meta_file_content.get("marketplaces", [])
        return set(old_marketplaces) != set(current_marketplaces)

    # secrets validation
    def validate_secrets_file(self):
        """Validate everything related to .secrets-ignore file"""
        if self._is_pack_file_exists(self.secrets_file) and all(
            [self._is_secrets_file_structure_valid()]
        ):
            return True

        return False

    def _check_if_file_is_empty(self, file_name: str) -> bool:
        """
        Check if file exists and contains info other than space characters.
        Returns false if the file does not exists or not empty
        """
        if self._is_pack_file_exists(file_name):
            content = self._read_file_content(file_name)
            if not content or content.isspace():
                return True

        return False

    @error_codes("IM109")
    def validate_author_image_exists(self):
        if self.metadata_content.get(PACK_METADATA_SUPPORT) == PARTNER_SUPPORT:
            author_image_path = os.path.join(self.pack_path, "Author_image.png")
            if not Path(author_image_path).exists():
                if self._add_error(
                    Errors.author_image_is_missing(author_image_path),
                    file_path=author_image_path,
                ):
                    return False

        return True

    @error_codes("RM104")
    def validate_pack_readme_file_is_not_empty(self):
        """
        Validates that README.md file is not empty for partner packs and packs with playbooks
        """
        playbooks_path = os.path.join(self.pack_path, "Playbooks")
        contains_playbooks = (
            Path(playbooks_path).exists() and len(os.listdir(playbooks_path)) != 0
        )
        if (
            self.support == PARTNER_SUPPORT or contains_playbooks
        ) and self._check_if_file_is_empty(self.readme_file):
            if self._add_error(Errors.empty_readme_error(), self.readme_file):
                return False

        return True

    @error_codes("RM105")
    def validate_pack_readme_and_pack_description(self):
        """
        Validates that README.md file is not the same as the pack description.
        Returns False if the pack readme is different than the pack description.
        """
        metadata = self._read_metadata_content()
        metadata_description = metadata.get(PACK_METADATA_DESC, "").lower().strip()
        if self._is_pack_file_exists(
            self.readme_file
        ) and not self._check_if_file_is_empty(self.readme_file):
            pack_readme = self._read_file_content(self.readme_file)
            readme_content = pack_readme.lower().strip()
            if metadata_description == readme_content:
                if self._add_error(
                    Errors.readme_equal_description_error(), self.readme_file
                ):
                    return False

        return True

    def _is_secrets_file_structure_valid(self):
        """Check if .secrets-ignore structure is parse-able"""
        if self._parse_file_into_list(self.secrets_file):
            return True

        return False

    # pack ignore validation
    def validate_pack_ignore_file(self):
        """Validate everything related to .pack-ignore file"""
        if self._is_pack_file_exists(self.pack_ignore_file) and all(
            [self._is_pack_ignore_file_structure_valid()]
        ):
            if self.validate_non_ignorable_error():
                return True

        return False

    @error_codes("PA104")
    def _is_pack_ignore_file_structure_valid(self):
        """Check if .pack-ignore structure is parse-able"""
        try:
            if self._parse_file_into_list(self.pack_ignore_file):
                return True
        except re.error:
            if not self._add_error(
                Errors.pack_file_bad_format(self.pack_ignore_file),
                self.pack_ignore_file,
            ):
                return True

        return False

    @error_codes("PA137")
    def validate_non_ignorable_error(self):
        """
        Check if .pack-ignore includes error codes that cannot be ignored.
        Returns False if an non-ignorable error code is found,
        or True if all ignored errors are indeed ignorable.
        """
        error_codes = extract_error_codes_from_file(self.pack)
        if error_codes:
            nonignoable_errors = error_codes.difference(ALLOWED_IGNORE_ERRORS)
            if nonignoable_errors and self._add_error(
                Errors.pack_have_nonignorable_error(nonignoable_errors),
                self.pack_ignore_file,
            ):
                return False
        return True

    # pack metadata validation
    def validate_pack_meta_file(self):
        """Validate everything related to pack_metadata.json file"""
        if self._is_pack_file_exists(self.pack_meta_file, is_required=True) and all(
            [
                self._is_pack_meta_file_structure_valid(),
                self._is_valid_contributor_pack_support_details(),
                self._is_approved_usecases(),
                self._is_right_version(),
                self._is_approved_tag_prefixes(),
                self._is_approved_tags(),
                self._is_price_changed(),
                self._is_valid_support_type(),
                self.is_right_usage_of_usecase_tag(),
                not self.should_pack_be_deprecated(),
            ]
        ):
            if self.should_version_raise:
                return self.validate_version_bump()
            else:
                return True

        return False

    @error_codes("PA114")
    def validate_version_bump(self):
        metadata_file_path = self._get_pack_file_path(self.pack_meta_file)
        old_meta_file_content = get_remote_file(metadata_file_path, tag=self.prev_ver)
        current_meta_file_content = get_json(metadata_file_path)
        old_version = old_meta_file_content.get("currentVersion", "0.0.0")
        current_version = current_meta_file_content.get("currentVersion", "0.0.0")
        if Version(old_version) < Version(current_version):
            return True
        elif self._add_error(
            Errors.pack_metadata_version_should_be_raised(self.pack, old_version),
            metadata_file_path,
        ):
            return False
        return True

    @error_codes("PA108,PA125")
    def validate_pack_name(self, metadata_file_content: Dict) -> bool:
        # check validity of pack metadata mandatory fields
        pack_name: str = metadata_file_content.get(PACK_METADATA_NAME, "")
        if not pack_name or "fill mandatory field" in pack_name:
            if self._add_error(
                Errors.pack_metadata_name_not_valid(), self.pack_meta_file
            ):
                return False
        if len(pack_name) < 3:
            if self._add_error(
                Errors.pack_name_is_not_in_xsoar_standards("short"), self.pack_meta_file
            ):
                return False
        if pack_name[0].islower():
            if self._add_error(
                Errors.pack_name_is_not_in_xsoar_standards("capital"),
                self.pack_meta_file,
            ):
                return False
        if re.findall(INCORRECT_PACK_NAME_PATTERN, pack_name):
            if self._add_error(
                Errors.pack_name_is_not_in_xsoar_standards("wrong_word"),
                self.pack_meta_file,
            ):
                return False
        if not self.name_does_not_contain_excluded_word(pack_name):
            if self._add_error(
                Errors.pack_name_is_not_in_xsoar_standards(
                    "excluded_word", EXCLUDED_DISPLAY_NAME_WORDS
                ),
                self.pack_meta_file,
            ):
                return False
        return True

    def name_does_not_contain_excluded_word(self, pack_name: str) -> bool:
        """
        Checks whether given object has excluded name.
        Args:
            pack_name (str): Name of the pack.
        Returns:
            (bool) False if name corresponding pack name contains excluded name, true otherwise.
        """
        lowercase_name = pack_name.lower()
        return not any(
            excluded_word in lowercase_name
            for excluded_word in EXCLUDED_DISPLAY_NAME_WORDS
        )

    def _is_empty_dir(self, dir_path: Path) -> bool:
        return dir_path.stat().st_size == 0

    def _is_integration_pack(self):
        integration_dir: Path = Path(self.pack_path) / INTEGRATIONS_DIR
        return integration_dir.exists() and not self._is_empty_dir(
            dir_path=integration_dir
        )

    @error_codes("PA105,PA106,PA107,PA109,PA110,PA115,PA111,PA129,PA118,PA112")
    def _is_pack_meta_file_structure_valid(self):
        """Check if pack_metadata.json structure is json parse-able and valid"""
        try:
            metadata = self._read_metadata_content()
            if not metadata:
                if self._add_error(Errors.pack_metadata_empty(), self.pack_meta_file):
                    raise BlockingValidationFailureException()

            if not isinstance(metadata, dict):
                if self._add_error(
                    Errors.pack_metadata_should_be_dict(self.pack_meta_file),
                    self.pack_meta_file,
                ):
                    raise BlockingValidationFailureException()

            missing_fields = [
                field
                for field in MANDATORY_PACK_METADATA_FIELDS
                if field not in metadata.keys()
            ]
            if missing_fields:
                if self._add_error(
                    Errors.missing_field_iin_pack_metadata(
                        self.pack_meta_file, missing_fields
                    ),
                    self.pack_meta_file,
                ):
                    raise BlockingValidationFailureException()

            elif not self.validate_pack_name(metadata):
                raise BlockingValidationFailureException()

            description_name = metadata.get(PACK_METADATA_DESC, "").lower()
            if not description_name or "fill mandatory field" in description_name:
                if self._add_error(
                    Errors.pack_metadata_field_invalid(), self.pack_meta_file
                ):
                    raise BlockingValidationFailureException()

            if not self.is_pack_metadata_desc_too_long(description_name):
                return False

            # check non mandatory dependency field
            dependencies_field = metadata.get(PACK_METADATA_DEPENDENCIES, {})
            if not isinstance(dependencies_field, dict):
                if self._add_error(
                    Errors.dependencies_field_should_be_dict(self.pack_meta_file),
                    self.pack_meta_file,
                ):
                    return False

            # check created field in iso format
            created_field = metadata.get(PACK_METADATA_CREATED, "")
            if created_field:
                if not check_timestamp_format(created_field):
                    suggested_value = parser.parse(created_field).isoformat() + "Z"
                    if self._add_error(
                        Errors.pack_timestamp_field_not_in_iso_format(
                            PACK_METADATA_CREATED, created_field, suggested_value
                        ),
                        self.pack_meta_file,
                    ):
                        return False

            # check metadata list fields and validate that no empty values are contained in this fields
            for list_field in PACK_METADATA_MANDATORY_FILLED_FIELDS:
                field = metadata[list_field]
                if field and len(field) == 1:
                    value = field[0]
                    if not value:
                        if self._add_error(
                            Errors.empty_field_in_pack_metadata(
                                self.pack_meta_file, list_field
                            ),
                            self.pack_meta_file,
                        ):
                            return False

            # check metadata categories isn't an empty list, only if it is an integration.
            if self._is_integration_pack():
                if not metadata[PACK_METADATA_CATEGORIES]:
                    if self._add_error(
                        Errors.pack_metadata_missing_categories(self.pack_meta_file),
                        self.pack_meta_file,
                    ):
                        return False

            # check modules field is used only for XSIAM and contains valid values
            if not self.is_modules_field_valid(metadata):
                return False

            # if the field 'certification' exists, check that its value is set to 'certified' or 'verified'
            certification = metadata.get(PACK_METADATA_CERTIFICATION)
            if certification and certification not in ALLOWED_CERTIFICATION_VALUES:
                if self._add_error(
                    Errors.pack_metadata_certification_is_invalid(self.pack_meta_file),
                    self.pack_meta_file,
                ):
                    return False

            # check format of metadata version
            version = metadata.get(PACK_METADATA_CURR_VERSION, "0.0.0")
            if not self._is_version_format_valid(version):
                return False

        except (ValueError, TypeError):
            if self._add_error(
                Errors.pack_metadata_isnt_json(self.pack_meta_file), self.pack_meta_file
            ):
                raise BlockingValidationFailureException()

        return True

    @error_codes("PA135,PA136")
    def is_modules_field_valid(self, metadata: Dict):
        if modules := metadata.get(PACK_METADATA_MODULES, []):
            # used only for XSIAM
            if MarketplaceVersions.MarketplaceV2 not in metadata.get(
                MARKETPLACE_KEY_PACK_METADATA, []
            ):
                if self._add_error(
                    Errors.pack_metadata_modules_for_non_xsiam(),
                    self.pack_meta_file,
                ):
                    return False

            # contains valid values
            if not set(modules).issubset(MODULES):
                if self._add_error(
                    Errors.pack_metadata_invalid_modules(),
                    self.pack_meta_file,
                ):
                    return False
        return True

    @error_codes("PA126")
    def is_pack_metadata_desc_too_long(self, description_name):
        if len(description_name) > MAXIMUM_DESCRIPTION_FIELD_LENGTH:
            if self._add_error(
                Errors.pack_metadata_long_description(),
                self.pack_meta_file,
                warning=True,
            ):
                return False
        return True

    @error_codes("PA113")
    def validate_support_details_exist(self, pack_meta_file_content):
        """Validate either email or url exist in contributed pack details."""
        if (
            not pack_meta_file_content[PACK_METADATA_URL]
            and not pack_meta_file_content[PACK_METADATA_EMAIL]
        ):
            if self._add_error(
                Errors.pack_metadata_missing_url_and_email(), self.pack_meta_file
            ):
                return False

        return True

    @error_codes("PA127")
    def validate_metadata_url(self, pack_meta_file_content):
        """Validate the url in the pack metadata doesn't lead to a github repository."""
        metadata_url = pack_meta_file_content[PACK_METADATA_URL]
        metadata_url = metadata_url.lower().strip()
        if len(re.findall("github.com", metadata_url)) > 0:
            # GitHub URLs that lead to a /issues page are also acceptable as a support URL.
            if not metadata_url.endswith("/issues"):
                self._add_error(Errors.metadata_url_invalid(), self.pack_meta_file)
                return False

        return True

    @error_codes("PA112")
    def _is_valid_contributor_pack_support_details(self):
        """Check email and url in contributed pack metadata details."""
        try:
            pack_meta_file_content = self._read_metadata_content()
            if (
                pack_meta_file_content[PACK_METADATA_SUPPORT]
                in SUPPORTED_CONTRIBUTORS_LIST
            ):
                return all(
                    [
                        self.validate_support_details_exist(pack_meta_file_content),
                        self.validate_metadata_url(pack_meta_file_content),
                    ]
                )

        except (ValueError, TypeError):
            if self._add_error(
                Errors.pack_metadata_isnt_json(self.pack_meta_file), self.pack_meta_file
            ):
                return False

        return True

    @error_codes("PA117,PA112")
    def _is_valid_support_type(self) -> bool:
        """Checks whether the support type is valid in the pack metadata.

        Returns:
            bool: True if the support type is valid, otherwise False

        """
        try:
            pack_meta_file_content = self._read_metadata_content()
            if (
                pack_meta_file_content[PACK_METADATA_SUPPORT]
                not in PACK_SUPPORT_OPTIONS
            ):
                self._add_error(
                    Errors.pack_metadata_invalid_support_type(), self.pack_meta_file
                )
                return False
            self.support = pack_meta_file_content[PACK_METADATA_SUPPORT]
        except (ValueError, TypeError):
            if self._add_error(
                Errors.pack_metadata_isnt_json(self.pack_meta_file), self.pack_meta_file
            ):
                return False

        return True

    @error_codes("PA119")
    def _is_approved_usecases(self) -> bool:
        """Checks whether the usecases in the pack metadata are approved

        Return:
             bool: True if the usecases are approved, otherwise False
        """
        if is_external_repository():
            return True

        non_approved_usecases = set()
        try:
            pack_meta_file_content = self._read_metadata_content()
            current_usecases = get_current_usecases()
            non_approved_usecases = set(
                pack_meta_file_content[PACK_METADATA_USE_CASES]
            ) - set(current_usecases)
            if non_approved_usecases:
                if self._add_error(
                    Errors.pack_metadata_non_approved_usecases(non_approved_usecases),
                    self.pack_meta_file,
                ):
                    return False
        except (ValueError, TypeError):
            if self._add_error(
                Errors.pack_metadata_non_approved_usecases(non_approved_usecases),
                self.pack_meta_file,
            ):
                return False
        return True

    @error_codes("PA130")
    def _is_version_format_valid(self, version: str) -> bool:
        """
        checks if the meta-data version is in the correct format
        Args:
            version (str): The version to check the foramt on

        Returns:
            bool: True if the version is in the correct format, otherwise false.
        """
        match_obj = re.match(VERSION_REGEX, version)
        if not match_obj:
            self._add_error(Errors.wrong_version_format(), self.pack_meta_file)
            return False
        return True

    @error_codes("PA133")
    def _is_approved_tag_prefixes(self) -> bool:
        """Checks whether the tags in the pack metadata are approved

        Return:
            bool: True if the tags are approved, otherwise False
        """
        if is_external_repository():
            return True

        is_valid = True
        approved_prefixes = {x.value for x in list(MarketplaceVersions)}
        pack_meta_file_content = self._read_metadata_content()
        for tag in pack_meta_file_content.get("tags", []):
            if ":" in tag:
                tag_data = tag.split(":")
                marketplaces = tag_data[0].split(",")
                for marketplace in marketplaces:
                    if marketplace not in approved_prefixes:
                        if self._add_error(
                            Errors.pack_metadata_non_approved_tag_prefix(
                                tag, approved_prefixes
                            ),
                            self.pack_meta_file,
                        ):
                            is_valid = False

        return is_valid

    @error_codes("PA120")
    def _is_approved_tags(self) -> bool:
        """Checks whether the tags in the pack metadata are approved
        Return:
             bool: True if the tags are approved, otherwise False
        """
        if is_external_repository():
            return True

        is_valid_tag_prefixes = True
        non_approved_tags = set()
        marketplaces = [x.value for x in list(MarketplaceVersions)]
        try:
            pack_tags, is_valid_tag_prefixes = filter_by_marketplace(
                marketplaces, self._read_metadata_content()
            )
            non_approved_tags = extract_non_approved_tags(pack_tags, marketplaces)
            if non_approved_tags:
                if self._add_error(
                    Errors.pack_metadata_non_approved_tags(non_approved_tags),
                    self.pack_meta_file,
                ):
                    return False
        except (ValueError, TypeError):
            if self._add_error(
                Errors.pack_metadata_non_approved_tags(non_approved_tags),
                self.pack_meta_file,
            ):
                return False

        return is_valid_tag_prefixes

    @error_codes("RN106,PA131")
    def _is_right_version(self):
        """Checks whether the currentVersion field in the pack metadata matches the version of the latest release note.

        Return:
             bool: True if the versions are match, otherwise False
        """
        metadata_file_path = self._get_pack_file_path(self.pack_meta_file)
        current_version = self.metadata_content.get("currentVersion", "0.0.0")
        rn_version = get_pack_latest_rn_version(self.pack_path)
        if not rn_version and current_version == "1.0.0":
            return True
        if not rn_version:
            self._add_error(Errors.missing_release_notes_for_pack(self.pack), self.pack)
            return False
        if parse(rn_version) != parse(current_version):
            self._add_error(
                Errors.pack_metadata_version_diff_from_rn(
                    self.pack, rn_version, current_version
                ),
                metadata_file_path,
            )
            return False
        return True

    def _contains_use_case(self):
        """
        Return:
            True if the Pack contains at least one PB, Incident Type or Layout, otherwise False
        """
        playbooks_path = os.path.join(self.pack_path, "Playbooks")
        incidents_path = os.path.join(self.pack_path, "IncidentTypes")
        layouts_path = os.path.join(self.pack_path, "Layouts")

        answers = [
            Path(playbooks_path).exists() and len(os.listdir(playbooks_path)) != 0,
            Path(incidents_path).exists() and len(os.listdir(incidents_path)) != 0,
            Path(layouts_path).exists() and len(os.listdir(layouts_path)) != 0,
        ]
        return any(answers)

    @error_codes("PA123")
    def is_right_usage_of_usecase_tag(self):
        """Checks whether Use Case tag in pack_metadata is used properly

        Return:
             bool: True if the Pack contains at least one PB, Incident Type or Layout, otherwise False
        """
        try:
            pack_meta_file_content = self._read_metadata_content()

            if "Use Case" in pack_meta_file_content["tags"]:
                if not self._contains_use_case():
                    if self._add_error(
                        Errors.is_wrong_usage_of_usecase_tag(), self.pack_meta_file
                    ):
                        return False
        except (ValueError, TypeError):
            if self._add_error(
                Errors.is_wrong_usage_of_usecase_tag(), self.pack_meta_file
            ):
                return False
        return True

    def get_master_private_repo_meta_file(self, metadata_file_path: str):
        current_repo = GitUtil()

        # if running on master branch in private repo - do not run the test
        if current_repo.get_current_git_branch_or_hash() == DEMISTO_GIT_PRIMARY_BRANCH:
            logger.debug(
                "<yellow>Running on master branch - skipping price change validation</yellow>"
            )
            return None
        try:
            tag = self.prev_ver
            tag = tag.replace(f"{DEMISTO_GIT_UPSTREAM}/", "").replace("demisto/", "")
            old_meta_file_content = get_local_remote_file(
                full_file_path=metadata_file_path, tag=tag, return_content=True
            )

        except GitCommandError as e:
            logger.debug(
                f"Got an error while trying to connect to git - {str(e)}\n"
                f"Skipping price change validation"
            )
            return None

        # if there was no past version
        if not old_meta_file_content:
            logger.debug(
                "<yellow>Unable to find previous pack_metadata.json file - skipping price change validation</yellow>"
            )
            return None

        return json.loads(old_meta_file_content)

    @error_codes("PA121")
    def _is_price_changed(self) -> bool:
        # only check on private repo
        if not self.private_repo:
            return True

        metadata_file_path = self._get_pack_file_path(self.pack_meta_file)
        old_meta_file_content = self.get_master_private_repo_meta_file(
            metadata_file_path
        )

        # if there was no past version or running on master branch
        if not old_meta_file_content:
            return True

        current_meta_file_content = get_json(metadata_file_path)
        current_price = current_meta_file_content.get("price")
        old_price = old_meta_file_content.get("price")

        # if a price was added, removed or changed compared to the master version - return an error
        if (
            (old_price and not current_price)
            or (current_price and not old_price)
            or (old_price != current_price)
        ):
            if self._add_error(
                Errors.pack_metadata_price_change(old_price, current_price),
                self.pack_meta_file,
            ):
                return False

        return True

    def are_valid_files(self, id_set_validations) -> str:
        """Main Execution Method"""
        try:
            self.validate_secrets_file()
            self.validate_pack_ignore_file()
            # metadata file is not validated for API_MODULES_PACK
            if API_MODULES_PACK not in self.pack:
                self.validate_pack_meta_file()

            self.validate_pack_readme_file_is_not_empty()
            self.validate_pack_readme_and_pack_description()
            self.validate_author_image_exists()

            # We only check pack dependencies for -g flag
            if self.validate_dependencies:
                self.validate_pack_dependencies()

            # Check if unique files are valid against the rest of the files, using the ID set.
            if id_set_validations:
                is_valid, error = id_set_validations.is_unique_file_valid_in_set(
                    self.pack_path, self.ignored_errors
                )
                if not is_valid:
                    self._add_error(error, self.pack_path)
        except BlockingValidationFailureException:
            # note that raising this should happen after adding the error to self._errors,
            # so no special handling is required on this `except` block
            pass

        return self.get_errors()

    # pack dependencies validation
    def validate_pack_dependencies(self):
        try:
            logger.info(
                f"\n<cyan>Running pack dependencies validation on {self.pack}</cyan>\n"
            )
            core_pack_list = get_core_pack_list()

            first_level_dependencies = PackDependencies.find_dependencies(
                self.pack,
                id_set_path=self.id_set_path,
                silent_mode=True,
                exclude_ignored_dependencies=False,
                update_pack_metadata=False,
                skip_id_set_creation=self.skip_id_set_creation,
                use_pack_metadata=True,
            )

            if not first_level_dependencies:
                logger.debug("<yellow>No first level dependencies found</yellow>")
                return True

            for core_pack in core_pack_list:
                first_level_dependencies.pop(core_pack, None)
            if not first_level_dependencies:
                logger.debug(
                    "<yellow>Found first level dependencies only on core packs</yellow>"
                )
                return True

            dependency_result = json.dumps(first_level_dependencies, indent=4)
            logger.info(f"<bold>Found dependencies result for {self.pack} pack:</bold>")
            logger.info(f"<bold>{dependency_result}</bold>")

            if self.pack in core_pack_list:
                if not self.validate_core_pack_dependencies(first_level_dependencies):
                    return False

            non_supported_pack = first_level_dependencies.get("NonSupported", {})
            deprecated_pack = first_level_dependencies.get("DeprecatedContent", {})

            if not self.is_invalid_package_dependencies(
                non_supported_pack, deprecated_pack
            ):
                return False

            return True

        except ValueError as e:
            if "Couldn't find any items for pack" in str(e):
                error_message, error_code = Errors.invalid_id_set()
                if self._add_error(
                    (error_message, error_code), file_path=self.pack_path
                ):
                    return False
                return True
            else:
                raise

    @error_codes("PA116")
    def is_invalid_package_dependencies(self, non_supported_pack, deprecated_pack):
        if (non_supported_pack.get("mandatory")) or (deprecated_pack.get("mandatory")):
            error_message, error_code = Errors.invalid_package_dependencies(self.pack)
            if self._add_error((error_message, error_code), file_path=self.pack_path):
                return False
        return True

    @error_codes("PA124")
    def validate_core_pack_dependencies(self, dependencies_packs):
        found_dependencies = []
        for dependency_pack in dependencies_packs:
            if dependencies_packs.get(dependency_pack, {}).get("mandatory"):
                found_dependencies.append(dependency_pack)

        if found_dependencies:
            error_message, error_code = Errors.invalid_core_pack_dependencies(
                self.pack, str(found_dependencies)
            )
            if self._add_error((error_message, error_code), file_path=self.pack_path):
                return False
        return True

    @error_codes("PA132")
    def should_pack_be_deprecated(self) -> bool:
        """
        Validates whether a pack should be deprecated
        if all its content items (playbooks/scripts/integrations/modeling_rules) are deprecated.

        Returns:
            bool: True if pack should be deprecated, False if it shouldn't.
        """
        pack = Pack(self.pack_path)
        if pack.should_be_deprecated():
            error_message, error_code = Errors.pack_should_be_deprecated(self.pack)
            return self._add_error(
                (error_message, error_code),
                file_path=self.pack_meta_file,
                suggested_fix=Errors.suggest_fix(
                    file_path=self._get_pack_file_path(self.pack_meta_file)
                ),
            )
        return False
