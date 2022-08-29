
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
    USES = 'USES'
    USES_COMMAND_OR_SCRIPT = 'USES_COMMAND_OR_SCRIPT'
    DEPENDS_ON = 'DEPENDS_ON'
    TESTED_BY = 'TESTED_BY'
    IN_PACK = 'IN_PACK'
    HAS_COMMAND = 'HAS_COMMAND'
    IMPORTS = 'IMPORTS'

    def __str__(self):
        return self.value


class ContentType(str, enum.Enum):
    BASE_CONTENT = 'BaseContent'
    PACK = 'Pack'
    COMMAND_OR_SCRIPT = 'CommandOrScript'
    COMMAND = 'Command'
    SCRIPT = 'Script'
    PLAYBOOK = 'Playbook'
    INTEGRATION = 'Integration'
    TEST_PLAYBOOK = 'TestPlaybook'
    INCIDENT_FIELD = 'IncidentField'
    INCIDENT_TYPE = 'IncidentType'
    INDICATOR_TYPE = 'IndicatorType'
    INDICATOR_FIELD = 'IndicatorField'
    CLASSIFIER = 'Classifier'
    MAPPER = 'Mapper'
    LAYOUT = 'Layout'
    WIDGET = 'Widget'
    DASHBOARD = 'Dashboard'
    REPORT = 'Report'
    CONNECTION = 'Connection'
    GENERIC_DEFINITION = 'GenericDefinition'
    GENERIC_FIELD = 'GenericField'
    GENERIC_MODULE = 'GenericModule'
    GENERIC_TYPE = 'GenericType'
    LIST = 'List'
    PREPROCESS_RULE = 'PreProcessRule'
    JOB = 'Job'
    PARSING_RULE = 'ParsingRule'
    MODELING_RULE = 'ModelingRule'
    CORRELATION_RULE = 'CorrelationRule'
    XSIAM_DASHBOARD = 'XSIAMDashboard'
    XSIAM_REPORT = 'XSIAMReport'
    TRIGGER = 'Trigger'
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
        return self.lower()

    @staticmethod
    def prefixes() -> List[str]:
        return [c.server_name for c in ContentType]

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
