import re
from enum import Enum, IntEnum
from typing import Union

from demisto_sdk.commands.common.constants import (DEFAULT_VERSION,
                                                   FEATURE_BRANCHES,
                                                   INCIDENT_FIELD,
                                                   INDICATOR_FIELD,
                                                   OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import get_remote_file
from packaging.version import Version
from wcmatch.pathlib import Path


class TypeFields(Enum):
    IndicatorFieldTypeShortText = "shortText"
    IndicatorFieldTypeLongText = "longText"
    IndicatorFieldTypeBoolean = "boolean"
    IndicatorFieldTypeSingleSelect = "singleSelect"
    IndicatorFieldTypeMultiSelect = "multiSelect"
    IndicatorFieldTypeDate = "date"
    IndicatorFieldTypeUser = "user"
    IndicatorFieldTypeRole = "role"
    IndicatorFieldTypeNumeric = "number"
    IndicatorFieldTypeAttachments = "attachments"
    IndicatorFieldTypeTags = "tagsSelect"
    IndicatorFieldTypeInternal = "internal"
    IndicatorFieldTypeURL = "url"
    IndicatorFieldTypeMD = "markdown"
    IndicatorFieldTypeGrid = "grid"
    IndicatorFieldTypeTimer = "timer"
    IndicatorFieldTypeHTML = "html"

    @classmethod
    def is_valid_indicator_field(cls, _type):
        return _type in [field.value for field in cls]


class GroupFieldTypes(IntEnum):
    INCIDENT_FIELD = 0
    EVIDENCE_FIELD = 1
    INDICATOR_FIELD = 2

    @classmethod
    def is_valid_group(cls, group):
        return group in [group.value for group in cls]


# Demisto is using a Bleve DB, those keys cannot be the cliName
BleveMapping = {
    0: [
        "id",
        "shardid",
        "modified",
        "autime",
        "account",
        "type",
        "rawtype",
        "phase",
        "rawphase",
        "name",
        "rawname",
        "status",
        "reason",
        "created",
        "parent",
        "occurred",
        "duedate",
        "reminder",
        "closed",
        "sla",
        "level",
        "investigationid",
        "details",
        "openduration",
        "droppedcount",
        "linkedcount",
        "closinguserId",
        "activatinguserId",
        "owner",
        "roles",
        "previousroles",
        "hasrole",
        "dbotcreatedBy",
        "activated",
        "closereason",
        "rawClosereason",
        "playbookid",
        "isplayground",
        "category",
        "rawcategory",
        "runstatus",
        "rawjson",
        "sourcebrand",
        "sourceinstance",
        "Lastopen",
        "canvases",
        "notifytime",
        "todotaskids",
        "scheduled",
        "labels",
    ],
    1: [
        "id",
        "shardid",
        "modified",
        "incidentid",
        "entryid",
        "description",
        "tags",
        "tagsraw",
        "occurred",
        "markeddate",
        "fetched",
        "taskid",
        "markedby",
        "roles",
        "previousroles",
        "hasrole",
        "dbotcreatedBy",
    ],
    2: [
        "id",
        "modified",
        "type",
        "rawname",
        "name",
        "createdtime",
        "name",
        "createdtime",
        "investigationids",
        "investigationscount",
        "isioc",
        "score",
        "lastseen",
        "lastreputationRun",
        "firstseen",
        "calculatedtime",
        "source",
        "rawsource",
        "manualscore",
        "setby",
        "manualsetTime",
        "comment",
        "modifiedtime",
        "sourceinstances",
        "sourcebrands",
        "context",
        "expiration",
        "expirationstatus",
        "manuallyeditedfields",
        "moduletofeedmap",
        "isshared",
    ],
}

INDICATOR_FIELD_CLINAME_VALIDATION_REGEX = r"[0-9a-z]+$"


class IndicatorField(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, INDICATOR_FIELD)
        self.base = base if base else BaseValidator()

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "incidentfield-indicatorfield-hello-world.yml"
            2. "indicatorfield-hello-world.yml" -> "incidentfield-indicatorfield-hello-world.yml"

        Returns:
            str: Normalize file name.
        """
        normalize_file_name = self._path.name
        # Handle case where "incidentfield-*hello-world.yml"
        if normalize_file_name.startswith(f'{INCIDENT_FIELD}-') and \
                not normalize_file_name.startswith(f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-'):
            normalize_file_name = normalize_file_name.replace(f'{INCIDENT_FIELD}-',
                                                              f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-')
        else:
            # Handle case where "indicatorfield-*hello-world.yml"
            if normalize_file_name.startswith(f'{INDICATOR_FIELD}-'):
                normalize_file_name = normalize_file_name.replace(f'{INDICATOR_FIELD}-',
                                                                  f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-')
            # Handle case where "*hello-world.yml"
            else:
                normalize_file_name = f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-{normalize_file_name}'

        return normalize_file_name

    def validate(self):
        if self.base.check_bc:
            return self.is_valid_file() and \
                self.is_backward_compatible(old_file=get_remote_file(self.path, tag=self.base.prev_ver))
        else:
            return self.is_valid_file()

    def is_backward_compatible(self, old_file):
        """Check whether the Indicator Field is backward compatible or not
        """
        if not old_file:
            return True

        is_bc_broke = any(
            [
                self.is_changed_type(old_file),
                self.is_changed_from_version(old_file),
            ]
        )

        return not is_bc_broke

    def is_valid_file(self):
        """Check whether the Indicator Field is valid or not
        """
        return all(
            [
                self.is_valid_version(),
                self.is_valid_name(),
                self.is_valid_type(),
                self.is_valid_group(),
                self.is_valid_content_flag(),
                self.is_valid_system_flag(),
                self.is_valid_cliname(),
                self.is_valid_version(),
                self.is_valid_required(),
                self.is_valid_fromversion()
            ]
        )

    def is_valid_name(self):
        """Validate that the name and cliName does not contain any potential incident synonyms."""
        name = self.get('name', '')
        bad_words = {
            "incident",
            "case",
            "alert",
            "event",
            "playbook",
            "ticket",
            "issue",
            "incidents",
            "cases",
            "alerts",
            "events",
            "playbooks",
            "tickets",
            "issues",
        }
        # TODO remove when demisto/etc#24232 is resolved
        whitelisted_field_names = {
            "XDR Alert Count",
            "XDR High Severity Alert Count",
            "XDR Medium Severity Alert Count",
            "XDR Low Severity Alert Count",
            "XDR Incident ID",
            "Detection Ticketed",
            "Claroty Alert Resolved",  # Needed for incidentfield-Claroty_Alert_Resolved.json
            "Claroty Alert Type",  # Needed for incidentfield-Claroty_Alert_Type.json
            "Code42 Alert Type",  # Needed for incidentfield-Code42_Alert_Type.json
            "Code42 File Events",  # Needed for incidentfield-Code42_File_Events.json
            "XDR Alerts",  # Needed for XDR_Alerts.json
            "Indeni Issue ID",  # Needed for incidentfield-Indeni_Device_ID.json
        }
        if name not in whitelisted_field_names:
            for word in name.split():
                if word.lower() in bad_words:
                    error_message, error_code = Errors.invalid_incident_field_name(word)
                    self.base.handle_error(error_message, error_code,
                                           file_path=self.path, warning=True)

        return True

    def is_valid_content_flag(self, content_value=True):
        """Validate that field is marked as content."""
        is_valid_flag = self.get("content") is content_value
        if not is_valid_flag:
            error_message, error_code = Errors.invalid_incident_field_content_key_value(content_value)
            if not self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid_flag = True

        return is_valid_flag

    def is_valid_system_flag(self, system_value=False):
        """Validate that field is not marked as system."""
        is_valid_flag = self.get("system", False) is system_value
        if not is_valid_flag:
            error_message, error_code = Errors.invalid_incident_field_system_key_value(system_value)
            if not self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid_flag = True

        return is_valid_flag

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(str(self.path))):
                return False
        return True

    def is_valid_type(self):
        # type: () -> bool
        is_valid = TypeFields.is_valid_indicator_field(self.get("type"))
        if is_valid:
            return True
        error_message, error_code = Errors.invalid_incident_field_type(self.get('type'),
                                                                       TypeFields)
        if self.base.handle_error(error_message, error_code, file_path=self.path):
            return False
        return True

    def is_valid_group(self):
        # type: () -> bool
        group = self.get("group")
        if GroupFieldTypes.is_valid_group(group):
            return True
        error_message, error_code = Errors.invalid_incident_field_group_value(group)
        if self.base.handle_error(error_message, error_code, file_path=self.path):
            return False
        return True

    def is_valid_cliname(self):
        # type: () -> bool
        return self.is_cliname_is_builtin_key() and self.is_matching_cliname_regex()

    def is_matching_cliname_regex(self):
        # type: () -> bool
        cliname = self.get("cliName")
        if re.fullmatch(INDICATOR_FIELD_CLINAME_VALIDATION_REGEX, cliname):  # type: ignore
            return True
        error_message, error_code = Errors.invalid_incident_field_cli_name_regex(
            INDICATOR_FIELD_CLINAME_VALIDATION_REGEX)
        if self.base.handle_error(error_message, error_code, file_path=self.path):
            return False
        return True

    def is_cliname_is_builtin_key(self):
        # type: () -> bool
        cliname = self.get("cliName")
        group = self.get("group")
        is_valid = True
        if group == GroupFieldTypes.INDICATOR_FIELD:
            is_valid = cliname not in BleveMapping[GroupFieldTypes.INDICATOR_FIELD]
        elif group == GroupFieldTypes.EVIDENCE_FIELD:
            is_valid = cliname not in BleveMapping[GroupFieldTypes.EVIDENCE_FIELD]
        elif group == GroupFieldTypes.INCIDENT_FIELD:
            is_valid = cliname not in BleveMapping[GroupFieldTypes.INCIDENT_FIELD]
        if not is_valid:
            error_message, error_code = Errors.invalid_incident_field_cli_name_value(cliname)
            if not self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid = True
        return is_valid

    def is_valid_required(self):
        # type: () -> bool
        """Validate that the indicator field is not required."""
        is_valid = True

        # due to a current platform limitation, indicator fields can not be set to required
        # after it will be fixed, need to validate that required field are not associated to all indicator types
        # as can be seen in this pr: https://github.com/demisto/content/pull/5682
        required = self.get('required', False)
        if required:
            error_message, error_code = Errors.new_incident_field_required()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False

        return is_valid

    def is_changed_from_version(self, old_file):
        # type: (dict) -> bool
        """Check if fromversion has been changed.

       Returns:
           bool. Whether fromversion has been changed.
       """
        is_fromversion_changed = False
        old_from_version = old_file.get('fromVersion', None)
        if old_from_version:
            current_from_version = str(self.from_version)
            if old_from_version != current_from_version:
                error_message, error_code = Errors.from_version_modified_after_rename()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_fromversion_changed = True

        return is_fromversion_changed

    def is_changed_type(self, old_file):
        # type: (dict) -> bool
        """Validate that the type was not changed."""
        is_type_changed = False
        current_type = self.get('type', "")
        if old_file:
            old_type = old_file.get('type', {})
            if old_type and old_type != current_type:
                error_message, error_code = Errors.incident_field_type_change()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_type_changed = True

        return is_type_changed

    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromVersion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.base.prev_ver or feature_branch_name in self.base.branch_name)
               for feature_branch_name in FEATURE_BRANCHES) or str(self.path).endswith('reputations.json'):
            return False

        return True
