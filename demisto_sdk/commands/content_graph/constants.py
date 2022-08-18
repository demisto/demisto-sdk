
from dataclasses import dataclass
import enum
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set
from demisto_sdk.commands.common.tools import get_content_path


REPO_PATH = Path(get_content_path())

NEO4J_ADMIN_DOCKER = ''

NEO4J_DATABASE_URL = os.getenv('DEMISTO_SDK_NEO4J_DATABASE_URL', 'bolt://localhost:7687')
NEO4J_USERNAME = os.getenv('DEMISTO_SDK_NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('DEMISTO_SDK_NEO4J_USERNAME', 'test')


PACKS_FOLDER = 'Packs'
PACK_METADATA_FILENAME = 'pack_metadata.json'
UNIFIED_FILES_SUFFIXES = ['.yml', '.json']


class Rel(enum.Enum):
    USES = 'USES'
    USES_COMMAND_OR_SCRIPT = 'USES_COMMAND_OR_SCRIPT'
    DEPENDS_ON = 'DEPENDS_ON'
    TESTED_BY = 'TESTED_BY'
    IN_PACK = 'IN_PACK'
    HAS_COMMAND = 'HAS_COMMAND'
    IMPORTS = 'IMPORTS'

    def __str__(self):
        return self.value

    @staticmethod
    def props_existence_constraints() -> Dict['Rel', List[str]]:
        constraints = {
            Rel.DEPENDS_ON: ['mandatorily'],
        }
        assert all(len(props) == 1 for props in constraints.values())  # constraints query limitation
        return constraints


class ContentTypes(str, enum.Enum):
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
        labels: Set[str] = {ContentTypes.BASE_CONTENT.value, self.value}

        if self.value == ContentTypes.TEST_PLAYBOOK.value:
            labels.add(ContentTypes.PLAYBOOK.value)

        if self in [ContentTypes.SCRIPT, ContentTypes.COMMAND]:
            labels.add(ContentTypes.COMMAND_OR_SCRIPT.value)

        return list(labels)

    @classmethod
    def by_folder(cls, folder: str) -> 'ContentTypes':
        return cls(folder[:-1])  # remove the `s`

    @property
    def as_folder(self) -> str:
        return f'{self.value}s'

    @staticmethod
    def abstract_types() -> List['ContentTypes']:
        return [ContentTypes.BASE_CONTENT, ContentTypes.COMMAND_OR_SCRIPT]

    @staticmethod
    def non_content_items() -> List['ContentTypes']:
        return [ContentTypes.PACK, ContentTypes.COMMAND]

    @staticmethod
    def non_abstracts(include_non_content_items: bool = True) -> Iterator['ContentTypes']:
        for content_type in ContentTypes:
            if content_type in ContentTypes.abstract_types():
                continue
            if not include_non_content_items and content_type in ContentTypes.non_content_items():
                continue
            yield content_type

    @staticmethod
    def content_items() -> Iterator['ContentTypes']:
        return ContentTypes.non_abstracts(include_non_content_items=False)

    @staticmethod
    def pack_folders(pack_path: Path) -> Iterator[Path]:
        for content_type in ContentTypes.content_items():
            pack_folder = pack_path / content_type.as_folder
            if pack_folder.is_dir() and not pack_folder.name.startswith('.'):
                yield pack_folder


RelationshipData = Dict[str, Any]
NodeData = Dict[str, Any]
