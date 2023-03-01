import enum
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, NamedTuple, Set

from neo4j import graph

NEO4J_ADMIN_DOCKER = ""

NEO4J_DATABASE_HTTP = os.getenv(
    "DEMISTO_SDK_NEO4J_DATABASE_HTTP", "http://127.0.0.1:7474"
)
NEO4J_DATABASE_URL = os.getenv(
    "DEMISTO_SDK_NEO4J_DATABASE_URL", "bolt://127.0.0.1:7687"
)
NEO4J_USERNAME = os.getenv("DEMISTO_SDK_NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("DEMISTO_SDK_NEO4J_PASSWORD", "test")

NEO4J_FOLDER = "neo4j-data"

PACKS_FOLDER = "Packs"
PACK_METADATA_FILENAME = "pack_metadata.json"
PACK_CONTRIBUTORS_FILENAME = "CONTRIBUTORS.json"
UNIFIED_FILES_SUFFIXES = [".yml", ".json"]


class Neo4jRelationshipResult(NamedTuple):
    node_from: graph.Node
    relationships: List[graph.Relationship]
    nodes_to: List[graph.Node]


class RelationshipType(str, enum.Enum):
    DEPENDS_ON = "DEPENDS_ON"
    HAS_COMMAND = "HAS_COMMAND"
    IMPORTS = "IMPORTS"
    IN_PACK = "IN_PACK"
    TESTED_BY = "TESTED_BY"
    USES = "USES"
    USES_BY_ID = "USES_BY_ID"
    USES_BY_NAME = "USES_BY_NAME"
    USES_COMMAND_OR_SCRIPT = "USES_COMMAND_OR_SCRIPT"
    USES_PLAYBOOK = "USES_PLAYBOOK"


class ContentType(str, enum.Enum):
    BASE_CONTENT = "BaseContent"
    CLASSIFIER = "Classifier"
    COMMAND = "Command"
    COMMAND_OR_SCRIPT = "CommandOrScript"
    CONNECTION = "Connection"
    CORRELATION_RULE = "CorrelationRule"
    DASHBOARD = "Dashboard"
    GENERIC_DEFINITION = "GenericDefinition"
    GENERIC_FIELD = "GenericField"
    GENERIC_MODULE = "GenericModule"
    GENERIC_TYPE = "GenericType"
    INCIDENT_FIELD = "IncidentField"
    INCIDENT_TYPE = "IncidentType"
    INDICATOR_FIELD = "IndicatorField"
    INDICATOR_TYPE = "IndicatorType"
    INTEGRATION = "Integration"
    JOB = "Job"
    LAYOUT = "Layout"
    LIST = "List"
    MAPPER = "Mapper"
    MODELING_RULE = "ModelingRule"
    PACK = "Pack"
    PARSING_RULE = "ParsingRule"
    PLAYBOOK = "Playbook"
    PREPROCESS_RULE = "PreProcessRule"
    REPORT = "Report"
    SCRIPT = "Script"
    TEST_PLAYBOOK = "TestPlaybook"
    TRIGGER = "Trigger"
    WIDGET = "Widget"
    XSIAM_DASHBOARD = "XSIAMDashboard"
    XSIAM_REPORT = "XSIAMReport"
    WIZARD = "Wizard"
    XDRC_TEMPLATE = "XDRCTemplate"
    LAYOUT_RULE = "LayoutRule"

    @property
    def labels(self) -> List[str]:
        labels: Set[str] = {ContentType.BASE_CONTENT.value, self.value}

        if self.value == ContentType.TEST_PLAYBOOK.value:
            labels.add(ContentType.PLAYBOOK.value)

        if self in [ContentType.SCRIPT, ContentType.COMMAND]:
            labels.add(ContentType.COMMAND_OR_SCRIPT.value)

        return list(labels)

    @property
    def server_name(self) -> str:
        if self == ContentType.INDICATOR_TYPE:
            return "reputation"
        elif self == ContentType.INDICATOR_FIELD:
            return "incidentfield-indicatorfield"
        elif self == ContentType.LAYOUT:
            return "layoutscontainer"
        elif self == ContentType.PREPROCESS_RULE:
            return "pre-process-rule"
        elif self == ContentType.TEST_PLAYBOOK:
            return ContentType.PLAYBOOK.server_name
        elif self == ContentType.MAPPER:
            return "classifier-mapper"
        return self.lower()

    @staticmethod
    def server_names() -> List[str]:
        return [c.server_name for c in ContentType] + ["indicatorfield", "mapper"]

    @staticmethod
    def values() -> Iterator[str]:
        return (c.value for c in ContentType)

    @classmethod
    def by_path(cls, path: Path) -> "ContentType":
        for idx, folder in enumerate(path.parts):
            if folder == PACKS_FOLDER:
                content_type_dir = path.parts[idx + 2]
                break
        else:
            # less safe option - will raise an exception if the path
            # is not to the content item directory or file
            if path.parts[-2][:-1] in ContentType.values():
                content_type_dir = path.parts[-2]
            elif path.parts[-3][:-1] in ContentType.values():
                content_type_dir = path.parts[-3]
            else:
                raise ValueError(f"Could not find content type in path {path}")
        return cls(content_type_dir[:-1])  # remove the `s`

    @staticmethod
    def folders() -> List[str]:
        return [c.as_folder for c in ContentType]

    @property
    def as_folder(self) -> str:
        if self == ContentType.MAPPER:
            return f"{ContentType.CLASSIFIER}s"
        return f"{self.value}s"

    @staticmethod
    def abstract_types() -> List["ContentType"]:
        return [ContentType.BASE_CONTENT, ContentType.COMMAND_OR_SCRIPT]

    @staticmethod
    def non_content_items() -> List["ContentType"]:
        return [ContentType.PACK, ContentType.COMMAND]

    @staticmethod
    def non_abstracts(
        include_non_content_items: bool = True,
    ) -> Iterator["ContentType"]:
        for content_type in ContentType:
            if content_type in ContentType.abstract_types():
                continue
            if (
                not include_non_content_items
                and content_type in ContentType.non_content_items()
            ):
                continue
            yield content_type

    @staticmethod
    def content_items() -> Iterator["ContentType"]:
        return ContentType.non_abstracts(include_non_content_items=False)

    @staticmethod
    def threat_intel_report_types() -> List["ContentType"]:
        return [ContentType.GENERIC_FIELD, ContentType.GENERIC_TYPE]

    @staticmethod
    def pack_folders(pack_path: Path) -> Iterator[Path]:
        for content_type in ContentType.content_items():
            if content_type == ContentType.MAPPER:
                continue
            pack_folder = pack_path / content_type.as_folder
            if pack_folder.is_dir() and not pack_folder.name.startswith("."):
                if content_type not in ContentType.threat_intel_report_types():
                    yield pack_folder
                else:
                    for tir_folder in pack_folder.iterdir():
                        if tir_folder.is_dir() and not tir_folder.name.startswith("."):
                            yield tir_folder


class Relationships(dict):
    def add(self, relationship: RelationshipType, **kwargs):
        if relationship not in self.keys():
            self.__setitem__(relationship, [])
        self.__getitem__(relationship).append(kwargs)

    def add_batch(self, relationship: RelationshipType, data: List[Dict[str, Any]]):
        if relationship not in self.keys():
            self.__setitem__(relationship, [])
        self.__getitem__(relationship).extend(data)

    def update(self, other: "Relationships") -> None:  # type: ignore
        for relationship, parsed_data in other.items():
            if relationship not in RelationshipType or not isinstance(
                parsed_data, list
            ):
                raise TypeError
            self.add_batch(relationship, parsed_data)


class Nodes(dict):
    def __init__(self, *args) -> None:
        super().__init__(self)
        for arg in args:
            if not isinstance(arg, dict):
                raise ValueError(f"Expected a dict: {arg}")
        self.add_batch(args)  # type: ignore[arg-type]

    def add(self, **kwargs):
        content_type: ContentType = ContentType(kwargs.get("content_type"))
        if content_type not in self.keys():
            self.__setitem__(content_type, [])
        self.__getitem__(content_type).append(kwargs)

    def add_batch(self, data: Iterator[Dict[str, Any]]):
        for obj in data:
            self.add(**obj)

    def update(self, other: "Nodes") -> None:  # type: ignore[override]
        data: Iterator[Dict[str, Any]]
        for content_type, data in other.items():
            if content_type not in ContentType or not isinstance(data, list):
                raise TypeError
            self.add_batch(data)


SERVER_CONTENT_ITEMS = {
    ContentType.INCIDENT_FIELD: [
        "name",
        "details",
        "severity",
        "owner",
        "created",
        "modified",
        "dbotCreatedBy",
        "type",
        "dbotSource",
        "category",
        "dbotStatus",
        "playbookId",
        "dbotCreated",
        "dbotClosed",
        "closed",
        "occurred",
        "activated",
        "openDuration",
        "lastOpen",
        "dbotDueDate",
        "dueDate",
        "dbotModified",
        "dbotTotalTime",
        "reason",
        "closeReason",
        "closeNotes",
        "closingUserId",
        "activatingingUserId",
        "reminder",
        "notifyTime",
        "lastJobRunTime",
        "sla",
        "phase",
        "rawPhase",
        "rawName",
        "rawType",
        "parent",
        "roles",
        "xsoarReadOnlyRoles",
        "labels",
        "attachment",
        "runStatus",
        "sourceBrand",
        "sourceInstance",
        "CustomFields",
        "droppedCount",
        "linkedCount",
        "linkedIncidents",
        "feedBased",
        "isDebug",
        "dbotMirrorId",
        "dbotMirrorInstance",
        "dbotMirrorDirection",
        "dbotDirtyFields",
        "dbotCurrentDirtyFields",
        "dbotMirrorTags",
        "dbotMirrorLastSync",
        "timestamp",
    ],
    ContentType.INDICATOR_FIELD: [
        "name",
        "relatedIncCount",
        "timestamp",
        "indicator_type",
        "value",
        "source",
        "investigationIDs",
        "lastSeen",
        "calculatedTime",
        "firstSeen",
        "score",
        "md5",
        "sha1",
        "sha256",
        "sha512",
        "ssdeep",
        "imphash",
        "size",
        "filetype",
        "comment",
        "expiration",
        "manualExpirationTime",
        "expirationStatus",
        "expirationdate",
        "sourceInstances",
        "sourceBrands",
        "modifiedTime",
        "comments",
        "modified",
        "isShared",
        "registrarname",
        "indicatortype",
        "aggregatedReliability",
        "starttime",
    ],
    ContentType.SCRIPT: [
        "getAPIKeyFromLicense",
        "handleIndicatorFormatterCache",
        "dockerImageUpdate",
        "addSystem",
        "getEntries",
        "getContext",
        "getFindings",
        "delContext",
        "getEntry",
        "closeInvestigation",
        "reopenInvestigation",
        "setSeverity",
        "setOwner",
        "setPhase",
        "taskReopen",
        "taskComplete",
        "taskAssign",
        "setTaskDueDate",
        "todoRemove",
        "todoAdd",
        "todoReopen",
        "todoComplete",
        "todoAssign",
        "todoDueDate",
        "addOneTimeEntitlement",
        "addEntitlement",
        "setPlaybook",
        "setIncident",
        "resetDirtyFields",
        "investigate",
        "setIncidentReminder",
        "createEntry",
        "addEntries",
        "createNewIncident",
        "setPlaybookAccordingToType",
        "getUserByEmail",
        "getUserByUsername",
        "getFilePath",
        "getIncidents",
        "addTask",
        "scheduleEntry",
        "cancelScheduledEntry",
        "markAsEvidence",
        "markAsNote",
        "setYourselfAs",
        "appendIndicatorField",
        "removeIndicatorField",
        "enrichIndicators",
        "getList",
        "setList",
        "createList",
        "addToList",
        "removeFromList",
        "setEntriesTags",
        "resetEntriesTags",
        "findIndicators",
        "getIndicator",
        "deleteIndicators",
        "executeCommandAt",
        "getUsers",
        "getRoles",
        "setRoleShifts",
        "setIndicator",
        "setIndicators",
        "createNewIndicator",
        "associateIndicatorToIncident",
        "associateIndicatorsToIncident",
        "unAssociateIndicatorToIncident",
        "unAssociateIndicatorsFromIncident",
        "addChildInvestigation",
        "pauseInvestigation",
        "generateSummaryReport",
        "generateGeneralReport",
        "resumeInvestigation",
        "getOwnerSuggestion",
        "getIndicatorScoreCache",
        "restrictInvestigation",
        "linkIncidents",
        "mdToHtml",
        "relatedIncidents",
        "maliciousRatio",
        "similarSsdeep",
        "extractIndicators",
        "isWhitelisted",
        "invite",
        "startTimer",
        "resetTimer",
        "stopTimer",
        "pauseTimer",
        "createMLModel",
        "deleteMLModel",
        "evaluateMLModel",
        "getMLModel",
        "reevaluateMLModel",
        "shareIndicators",
        "expireIndicators",
        "getWorkersStatistics",
        "excludeIndicators",
        "getMirrorStatistics",
        "getSyncMirrorRecords",
        "purgeClosedSyncMirrorRecords",
        "getInvPlaybookMetaData",
        "getDBStatistics",
        "getInternalData",
        "drawCanvas",
        "deleteRelationships",
        "searchRelationships",
        "getSystemDiagnostics",
        "triggerDebugMirroringRun",
        # Filters
        "isEqual",
        "isNotEqual",
        "isEqualCase",
        "isNotEqualCase",
        "isEqualNumber",
        "isNotEqualNumber",
        "isEqualString",
        "isNotEqualString",
        "contains",
        "notContains",
        "containsString",
        "notContainsString",
        "startWith",
        "notStartWith",
        "endWith",
        "notEndWith",
        "inList",
        "notInList",
        "match",
        "stringHasLength",
        "isEqual",
        "isNotEqual",
        "greaterThan",
        "greaterThanOrEqual",
        "lessThan",
        "lessThanOrEqual",
        "isSame",
        "isBefore",
        "isAfter",
        "isTrue",
        "isFalse",
        "isExists",
        "isNotExists",
        "isEmpty",
        "isNotEmpty",
        "contains",
        "notContains",
        "in",
        "notIn",
        "hasLength",
        "isIdenticalIncident",
        "isNotIdenticalIncident",
        "containsGeneral",
        "notContainsGeneral",
        # Transformers
        "toUpperCase",
        "toLowerCase",
        "substringFrom",
        "substringTo",
        "substring",
        "split",
        "splitAndTrim",
        "trim",
        "replace",
        "replaceMatch",
        "concat",
        "strLength",
        "round",
        "floor",
        "ceil",
        "addition",
        "subtraction",
        "multiply",
        "division",
        "modulo",
        "toPercent",
        "abs",
        "precision",
        "quadraticEquation",
        "toString",
        "toUnix",
        "getField",
        "sort",
        "count",
        "atIndex",
        "join",
        "uniq",
        "indexOf",
        "slice",
        "sliceByItem",
        "splice",
        "Stringify",
        "append",
        "ConvertKeysToTableFieldFormat",
    ],
    ContentType.COMMAND: [
        # activedir-login integration commands
        "ad-default-domain",
        "ad-authenticate",
        "ad-authentication-roles",
        "ad-authenticate-and-roles",
        "ad-groups",
        # activedir integration commands
        "ad-search",
        "ad-expire-password",
        "ad-set-new-password",
        "ad-unlock-account",
        "ad-disable-account",
        "ad-enable-account",
        "ad-remove-from-group",
        "ad-add-to-group",
        "ad-create-user",
        "ad-update-user",
        "ad-delete-user",
        "ad-modify-computer-ou",
        "ad-create-contact",
        "ad-update-contact",
        # carbonblackprotection integration commands
        "cbp-fileCatalog-search",
        "cbp-fileInstance-search",
        "cbp-fileRule-search",
        "cbp-fileRule-get",
        "cbp-fileRule-delete",
        "cbp-fileRule-update",
        "cbp-fileAnalysis-get",
        "cbp-fileAnalysis-createOrUpdate",
        "cbp-fileAnalysis-search",
        "cbp-fileUpload-get",
        "cbp-fileUpload-download",
        "cbp-fileUpload-createOrUpdate",
        "cbp-fileUpload-search",
        "cbp-connector-get",
        "cbp-connector-search",
        "cbp-computer-search",
        "cbp-computer-get",
        "cbp-computer-update",
        "cbp-notification-search",
        "cbp-publisher-search",
        "cbp-event-search",
        "cbp-approvalRequest-search",
        "cbp-serverConfig-search",
        "cbp-policy-search",
        # carbonblack integration commands
        "cb-version",
        "cb-process",
        "cb-process-events",
        "cb-binary",
        "cb-binary-get",
        "cb-alert",
        "cb-list-sensors",
        "cb-list-sessions",
        "cb-sensor-info",
        "cb-session-create",
        "cb-session-close",
        "cb-keepalive",
        "cb-session-info",
        "cb-archive",
        "cb-command-create",
        "cb-list-commands",
        "cb-command-info",
        "cb-command-cancel",
        "cb-list-files",
        "cb-file-info",
        "cb-file-delete",
        "cb-file-get",
        "cb-watchlist-get",
        "cb-watchlist-new",
        "cb-watchlist-set",
        "cb-watchlist-del",
        "cb-terminate-process",
        "cb-quarantine-device",
        "cb-unquarantine-device",
        "cb-block-hash",
        "cb-unblock-hash",
        "cb-get-hash-blacklist",
        "cb-get-process",
        "cb-get-processes",
        # cylance integration commands
        "file",
        "cy-upload",
        # duo integration commands
        "duo-authenticate",
        "duo-authenticate-status",
        "duo-check",
        "duo-preauth",
        # elasticsearch integration commands
        "search",
        # fcm integration commands
        "fcm-push",
        # google integration commands
        "googleapps-list-users",
        "googleapps-get-user",
        "googleapps-delete-user",
        "googleapps-get-user-roles",
        "googleapps-revoke-user-role",
        "googleapps-gmail-search",
        "googleapps-gmail-get-mail",
        "googleapps-device-action",
        "googleapps-get-devices-for-user",
        "googleapps-get-tokens-for-user",
        "googleapps-chrome-device-action",
        "googleapps-get-chrome-devices-for-user",
        "googleapps-gmail-get-attachment",
        # kafka integration commands
        "kafka-publish-msg",
        "kafka-print-topics",
        "kafka-consume-msg",
        "kafka-fetch-partitions",
        # mail-sender integration commands
        "send-mail",
        # mattermost integration commands
        "send-notification",
        "mattermost-send",
        "mattermost-send-file",
        "mattermost-close-channel",
        "close-channel",
        "mattermost-mirror-investigation",
        "mirror-investigation",
        # esm integration commands
        "search",
        "esmFetchAllFields",
        # mysql integration commands
        "query",
        # nexpose integration commands
        "vulnerability-list",
        "vulnerability-details",
        "generate-adhoc-report",
        "send-xml",
        # pagerduty integration commands
        "PagerDutyGetUsersOnCall",
        "PagerDutyGetAllSchedules",
        "PagerDutyGetUsersOnCallNow",
        "PagerDutyIncidents",
        "pagerDutySubmitEvent",
        # remoteaccess integration commands
        "ssh",
        "copy-to",
        "copy-from",
        # sharedagent integration commands
        "sharedagent_create",
        "execute",
        "sharedagent_remove",
        "sharedagent_status",
        # slack integration commands
        "send-notification",
        "slack-send",
        "mirror-investigation",
        "slack-mirror-investigation",
        "close-channel",
        "slack-close-channel",
        "slack-send-file",
        # mssql integration commands
        "query",
        # threatcentral integration commands
        "Threat-Central",
    ],
    ContentType.INTEGRATION: [
        "mail-listener",
        "osxcollector",
        "volatility",
        "threatcentral",
        "mattermost",
        "indicators-share",
        "sharedagent",
        "activedir",
        "activedir-login",
        "esm",
        "saml",
        "pagerduty",
        "mail-sender",
        "carbonblack",
        "carbonblackprotection",
        "slack",
        "nexpose",
        "duo",
        "cylance",
        "remoteaccess",
        "elasticsearch",
        "mysql",
        "mssql",
        "google",
        "crowdstrike-streaming-api",
        "kafka",
        "syslog",
        "fcm",
    ],
}
