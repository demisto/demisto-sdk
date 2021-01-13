"""
This module is designed to validate the correctness of incident field entities in content.
"""
import re
from distutils.version import LooseVersion
from enum import Enum, IntEnum

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class TypeFields(Enum):
    IncidentFieldTypeShortText = "shortText"
    IncidentFieldTypeLongText = "longText"
    IncidentFieldTypeBoolean = "boolean"
    IncidentFieldTypeSingleSelect = "singleSelect"
    IncidentFieldTypeMultiSelect = "multiSelect"
    IncidentFieldTypeDate = "date"
    IncidentFieldTypeUser = "user"
    IncidentFieldTypeRole = "role"
    IncidentFieldTypeNumeric = "number"
    IncidentFieldTypeAttachments = "attachments"
    IncidentFieldTypeTags = "tagsSelect"
    IncidentFieldTypeInternal = "internal"
    IncidentFieldTypeURL = "url"
    IncidentFieldTypeMD = "markdown"
    IncidentFieldTypeGrid = "grid"
    IncidentFieldTypeTimer = "timer"
    IncidentFieldTypeHTML = "html"

    @classmethod
    def is_valid_incident_field(cls, _type):
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

INCIDENT_FIELD_CLINAME_VALIDATION_REGEX = r"[0-9a-z]+$"


class IncidentFieldValidator(ContentEntityValidator):
    """IncidentFieldValidator is designed to validate the correctness of the file structure we enter to content repo.
    And also try to catch possible Backward compatibility breaks due to the performed changes.
    """

    def is_backward_compatible(self):
        """Check whether the Incident Field is backward compatible or not
        """
        if not self.old_file:
            return True

        is_bc_broke = any(
            [
                self.is_changed_type(),
                self.is_changed_from_version(),
            ]
        )

        return not is_bc_broke

    def is_valid_file(self, validate_rn=True):
        """Check whether the Incident Field is valid or not
        """
        return all(
            [
                super().is_valid_file(validate_rn),
                self.is_valid_name(),
                self.is_valid_type(),
                self.is_valid_group(),
                self.is_valid_content_flag(),
                self.is_valid_system_flag(),
                self.is_valid_cliname(),
                self.is_valid_version(),
                self.is_valid_required(),
                self.is_valid_indicator_grid_fromversion()
            ]
        )

    def is_valid_name(self):
        """Validate that the name and cliName does not contain any potential incident synonyms."""
        name = self.current_file.get("name", "")
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
                    self.handle_error(error_message, error_code, file_path=self.file_path, warning=True)

        return True

    def is_valid_content_flag(self, content_value=True):
        """Validate that field is marked as content."""
        is_valid_flag = self.current_file.get("content") is content_value
        if not is_valid_flag:
            error_message, error_code = Errors.invalid_incident_field_content_key_value(content_value)
            if not self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid_flag = True

        return is_valid_flag

    def is_valid_system_flag(self, system_value=False):
        """Validate that field is not marked as system."""
        is_valid_flag = self.current_file.get("system", False) is system_value
        if not is_valid_flag:
            error_message, error_code = Errors.invalid_incident_field_system_key_value(system_value)
            if not self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid_flag = True

        return is_valid_flag

    def is_valid_version(self):
        # type: () -> bool
        return super(IncidentFieldValidator, self)._is_valid_version()

    def is_valid_type(self):
        # type: () -> bool
        is_valid = TypeFields.is_valid_incident_field(self.current_file.get("type"))
        if is_valid:
            return True
        error_message, error_code = Errors.invalid_incident_field_type(self.current_file.get('type'), TypeFields)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False
        return True

    def is_valid_group(self):
        # type: () -> bool
        group = self.current_file.get("group")
        if GroupFieldTypes.is_valid_group(group):
            return True
        error_message, error_code = Errors.invalid_incident_field_group_value(group)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False
        return True

    def is_valid_cliname(self):
        # type: () -> bool
        return self.is_cliname_is_builtin_key() and self.is_matching_cliname_regex()

    def is_matching_cliname_regex(self):
        # type: () -> bool
        cliname = self.current_file.get("cliName")
        if re.fullmatch(INCIDENT_FIELD_CLINAME_VALIDATION_REGEX, cliname):  # type: ignore
            return True
        error_message, error_code = Errors.invalid_incident_field_cli_name_regex(
            INCIDENT_FIELD_CLINAME_VALIDATION_REGEX)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False
        return True

    def is_cliname_is_builtin_key(self):
        # type: () -> bool
        cliname = self.current_file.get("cliName")
        group = self.current_file.get("group")
        is_valid = True
        if group == GroupFieldTypes.INDICATOR_FIELD:
            is_valid = cliname not in BleveMapping[GroupFieldTypes.INDICATOR_FIELD]
        elif group == GroupFieldTypes.EVIDENCE_FIELD:
            is_valid = cliname not in BleveMapping[GroupFieldTypes.EVIDENCE_FIELD]
        elif group == GroupFieldTypes.INCIDENT_FIELD:
            is_valid = cliname not in BleveMapping[GroupFieldTypes.INCIDENT_FIELD]
        if not is_valid:
            error_message, error_code = Errors.invalid_incident_field_cli_name_value(cliname)
            if not self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = True
        return is_valid

    def is_valid_required(self):
        # type: () -> bool
        """Validate that the incident field is not required."""
        is_valid = True

        # due to a current platform limitation, incident fields can not be set to required
        # after it will be fixed, need to validate that required field are not associated to all incident types
        # as can be seen in this pr: https://github.com/demisto/content/pull/5682
        required = self.current_file.get('required', False)
        if required:
            error_message, error_code = Errors.new_incident_field_required()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    def is_changed_from_version(self):
        # type: () -> bool
        """Check if fromversion has been changed.

       Returns:
           bool. Whether fromversion has been changed.
       """
        is_fromversion_changed = False
        old_from_version = self.old_file.get('fromVersion', None)
        if old_from_version:
            current_from_version = self.current_file.get('fromVersion', None)
            if old_from_version != current_from_version:
                error_message, error_code = Errors.from_version_modified_after_rename()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_fromversion_changed = True

        return is_fromversion_changed

    def is_changed_type(self):
        # type: () -> bool
        """Validate that the type was not changed."""
        is_type_changed = False
        current_type = self.current_file.get('type', "")
        if self.old_file:
            old_type = self.old_file.get('type', {})
            if old_type and old_type != current_type:
                error_message, error_code = Errors.incident_field_type_change()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_type_changed = True

        return is_type_changed

    def is_valid_indicator_grid_fromversion(self):
        # type: () -> bool
        """Validate that a indicator field with type grid is from version >= 5.5.0"""
        if self.structure_validator.file_type != FileType.INDICATOR_FIELD.value:
            return True

        if self.current_file.get('type') != 'grid':
            return True

        current_version = LooseVersion(self.current_file.get('fromVersion', '0.0.0'))
        if current_version < LooseVersion('5.5.0'):
            error_message, error_code = Errors.indicator_field_type_grid_minimal_version(current_version)

            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True
