
import enum
from pathlib import Path


PACKS_FOLDER = 'Packs'
PACK = 'Pack'
COMMAND = 'Command'


class Marketplaces(enum.Enum):
    XSOAR = 'xsoar'
    XSIAM = 'marketplacev2'

    @staticmethod
    def to_dict():
        return {i.value: i.name for i in Marketplaces}


class ScriptTypes(enum.Enum):
    PYTHON2 = 'python2'
    PYTHON3 = 'python3'
    JAVASCRIPT = 'javascript'
    POWERSHELL = 'powershell'

    @staticmethod
    def to_dict():
        return {i.value: i.value for i in ScriptTypes}


class Rel(enum.Enum):
    DEPENDS_ON = 'DEPENDS_ON'
    TESTED_BY = 'TESTED_BY'
    IN_PACK = 'IN_PACK'
    IN_INTEGRATION = 'IN_INTEGRATION'

    def __str__(self):
        return self.value


class PackFolder(enum.Enum):
    SCRIPTS = 'Scripts'
    PLAYBOOKS = 'Playbooks'
    INTEGRATIONS = 'Integrations'
    TEST_PLAYBOOKS = 'TestPlaybooks'
    REPORTS = 'Reports'
    DASHBOARDS = 'Dashboards'
    WIDGETS = 'Widgets'
    INCIDENT_FIELDS = 'IncidentFields'
    INCIDENT_TYPES = 'IncidentTypes'
    INDICATOR_FIELDS = 'IndicatorFields'
    LAYOUTS = 'Layouts'
    CLASSIFIERS = 'Classifiers'
    INDICATOR_TYPES = 'IndicatorTypes'
    CONNECTIONS = 'Connections'
    GENERIC_DEFINITIONS = 'GenericDefinitions'
    GENERIC_FIELDS = 'GenericFields'
    GENERIC_MODULES = 'GenericModules'
    GENERIC_TYPES = 'GenericTypes'
    LISTS = 'Lists'
    PREPROCESS_RULES = 'PreProcessRules'
    JOBS = 'Jobs'
    PARSING_RULES = 'ParsingRules'
    MODELING_RULES = 'ModelingRules'
    CORRELATION_RULES = 'CorrelationRules'
    XSIAM_DASHBOARDS = 'XSIAMDashboards'
    XSIAM_REPORTS = 'XSIAMReports'
    TRIGGERS = 'Triggers'
    WIZARDS = 'Wizards'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @classmethod
    def is_content_item_folder(cls, path: Path):
        return path.is_dir() and cls.has_value(path.parts[-2])

    @classmethod
    def is_pack_folder(cls, path: Path):
        return path.is_dir() and cls.has_value(path.parts[-1])
    
    @property
    def type(self) -> str:
        return self.value[:-1]  # remove the `s`
