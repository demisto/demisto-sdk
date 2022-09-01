
import enum
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set
from demisto_sdk.commands.common.tools import get_content_path

REPO_PATH = Path(get_content_path())

NEO4J_ADMIN_DOCKER = ''

NEO4J_DATABASE_URL = os.getenv('DEMISTO_SDK_NEO4J_DATABASE_URL', 'bolt://localhost:7687')
NEO4J_USERNAME = os.getenv('DEMISTO_SDK_NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('DEMISTO_SDK_NEO4J_PASSWORD', 'test')


PACKS_FOLDER = 'Packs'
PACK_METADATA_FILENAME = 'pack_metadata.json'
PACK_CONTRIBUTORS_FILENAME = 'contributors.json'
UNIFIED_FILES_SUFFIXES = ['.yml', '.json']


class Relationship(enum.Enum):
    DEPENDS_ON = 'DEPENDS_ON'
    HAS_COMMAND = 'HAS_COMMAND'
    IMPORTS = 'IMPORTS'
    IN_PACK = 'IN_PACK'
    TESTED_BY = 'TESTED_BY'
    USES = 'USES'
    USES_COMMAND_OR_SCRIPT = 'USES_COMMAND_OR_SCRIPT'

    def __str__(self):
        return self.value


class ContentType(str, enum.Enum):
    BASE_CONTENT = 'BaseContent'
    CLASSIFIER = 'Classifier'
    COMMAND = 'Command'
    COMMAND_OR_SCRIPT = 'CommandOrScript'
    CONNECTION = 'Connection'
    CORRELATION_RULE = 'CorrelationRule'
    DASHBOARD = 'Dashboard'
    GENERIC_DEFINITION = 'GenericDefinition'
    GENERIC_FIELD = 'GenericField'
    GENERIC_MODULE = 'GenericModule'
    GENERIC_TYPE = 'GenericType'
    INCIDENT_FIELD = 'IncidentField'
    INCIDENT_TYPE = 'IncidentType'
    INDICATOR_FIELD = 'IndicatorField'
    INDICATOR_TYPE = 'IndicatorType'
    INTEGRATION = 'Integration'
    JOB = 'Job'
    LAYOUT = 'Layouts'
    LIST = 'List'
    MAPPER = 'Mapper'
    MODELING_RULE = 'ModelingRule'
    PACK = 'Pack'
    PARSING_RULE = 'ParsingRule'
    PLAYBOOK = 'Playbook'
    PREPROCESS_RULE = 'PreProcessRule'
    REPORT = 'Report'
    SCRIPT = 'Script'
    TEST_PLAYBOOK = 'TestPlaybook'
    TRIGGER = 'Trigger'
    WIDGET = 'Widget'
    XSIAM_DASHBOARD = 'XSIAMDashboard'
    XSIAM_REPORT = 'XSIAMReport'
    WIZARD = 'Wizard'

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
        if self == ContentType.SCRIPT:
            return 'automation'
        elif self == ContentType.INDICATOR_TYPE:
            return 'reputation'
        elif self == ContentType.INDICATOR_FIELD:
            return 'incidentfield-indicatorfield'
        elif self == ContentType.LAYOUT:
            return 'layoutscontainer'
        elif self == ContentType.PREPROCESS_RULE:
            return 'pre-process-rule'
        return self.lower()

    @staticmethod
    def prefixes() -> List[str]:
        return [c.server_name for c in ContentType] + ['indicatorfield']

    @classmethod
    def by_folder(cls, folder: str) -> 'ContentType':
        return cls(folder[:-1])  # remove the `s`

    @property
    def as_folder(self) -> str:
        if self == ContentType.MAPPER:
            return f'{ContentType.CLASSIFIER}s'
        return f'{self.value}s'

    @staticmethod
    def abstract_types() -> List['ContentType']:
        return [ContentType.BASE_CONTENT, ContentType.COMMAND_OR_SCRIPT]

    @staticmethod
    def non_content_items() -> List['ContentType']:
        return [ContentType.PACK, ContentType.COMMAND]

    @staticmethod
    def non_abstracts(include_non_content_items: bool = True) -> Iterator['ContentType']:
        for content_type in ContentType:
            if content_type in ContentType.abstract_types():
                continue
            if not include_non_content_items and content_type in ContentType.non_content_items():
                continue
            yield content_type

    @staticmethod
    def content_items() -> Iterator['ContentType']:
        return ContentType.non_abstracts(include_non_content_items=False)

    @staticmethod
    def pack_folders(pack_path: Path) -> Iterator[Path]:
        for content_type in ContentType.content_items():
            if content_type == ContentType.MAPPER:
                continue
            pack_folder = pack_path / content_type.as_folder
            if pack_folder.is_dir() and not pack_folder.name.startswith('.'):
                yield pack_folder


class Relationships(dict):
    def add(self, relationship: Relationship, **kwargs):
        if relationship not in self.keys():
            self.__setitem__(relationship, [])
        self.__getitem__(relationship).append(kwargs)

    def add_batch(self, relationship: Relationship, data: List[Dict[str, Any]]):
        if relationship not in self.keys():
            self.__setitem__(relationship, [])
        self.__getitem__(relationship).extend(data)

    def update(self, other: 'Relationships') -> None:
        for relationship, parsed_data in other.items():
            if relationship not in Relationship or not isinstance(parsed_data, list):
                raise TypeError
            self.add_batch(relationship, parsed_data)


class Nodes(dict):
    def __init__(self, *args) -> None:
        super().__init__(self)
        for arg in args:
            if not isinstance(arg, dict):
                raise ValueError(f'Expected a dict: {arg}')
        self.add_batch(args)

    def add(self, **kwargs):
        content_type: ContentType = ContentType(kwargs.get('content_type'))
        if content_type not in self.keys():
            self.__setitem__(content_type, [])
        self.__getitem__(content_type).append(kwargs)

    def add_batch(self, data: Iterator[Dict[str, Any]]):
        for obj in data:
            self.add(**obj)

    def update(self, other: 'Nodes', **kwargs) -> None:
        for content_type, data in other.items():
            if content_type not in ContentType or not isinstance(data, list):
                raise TypeError
            self.add_batch(data)
