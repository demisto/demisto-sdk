
import enum
from pathlib import Path
from typing import Iterator, Dict, List


PACKS_FOLDER = 'Packs'
PACK_METADATA_FILENAME = 'pack_metadata.json'


class Rel(enum.Enum):
    DEPENDS_ON = 'DEPENDS_ON'
    TESTED_BY = 'TESTED_BY'
    IN_PACK = 'IN_PACK'
    HAS_COMMAND = 'HAS_COMMAND'

    def __str__(self):
        return self.value
    
    @staticmethod
    def props_existence_constraints() -> Dict['Rel', List[str]]:
        constraints = {
            Rel.DEPENDS_ON: ['mandatorily'],
        }
        assert all(len(props) == 1 for props in constraints.values())  # constraints query limitation
        return constraints



class ContentTypes(enum.Enum):
    BASE_CONTENT = 'BaseContent'
    PACK = 'Pack'
    COMMAND = 'Command'
    CONTENT_ITEM = 'ContentItem'
    SCRIPT = 'Script'
    PLAYBOOK = 'Playbook'
    INTEGRATION = 'Integration'
    TEST_PLAYBOOK = 'TestPlaybook'
    REPORT = 'Report'
    DASHBOARD = 'Dashboard'
    WIDGET = 'Widget'
    INCIDENT_FIELD = 'IncidentField'
    INCIDENT_TYPE = 'IncidentType'
    INDICATOR_FIELD = 'IndicatorField'
    LAYOUT = 'Layout'
    CLASSIFIER = 'Classifier'
    INDICATOR_TYPE = 'IndicatorType'
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

    def __str__(self) -> str:
        return self.value

    @property
    def labels(self) -> List[str]:
        labels: List[str] = [ContentTypes.BASE_CONTENT.value, self.value]

        if self.value not in [ContentTypes.PACK.value, ContentTypes.COMMAND.value]:
            labels.append(ContentTypes.CONTENT_ITEM.value)

        if self.value == ContentTypes.SCRIPT.value:
            labels.append(ContentTypes.COMMAND.value)

        if self.value == ContentTypes.TEST_PLAYBOOK.value:
            labels.append(ContentTypes.PLAYBOOK.value)

        return labels

    @classmethod
    def by_folder(cls, folder: str) -> 'ContentTypes':
        return cls(folder[:-1])  # remove the `s`

    @property
    def as_folder(self) -> str:
        return f'{self.value}s'

    @staticmethod
    def pack_folders(pack_path: Path) -> Iterator[Path]:
        for content_type in ContentTypes:
            pack_folder = pack_path / content_type.as_folder
            if pack_folder.is_dir():
                yield pack_folder

    @staticmethod
    def props_uniqueness_constraints() -> Dict['ContentTypes', List[str]]:
        return {
            ContentTypes.BASE_CONTENT: ['node_id'],
        }

    @staticmethod
    def props_existence_constraints() -> Dict['ContentTypes', List[str]]:
        return {
            ContentTypes.PACK: ['name', 'deprecated', 'marketplaces', 'author', 'certification', 'current_version', 'categories'],
            ContentTypes.CONTENT_ITEM: ['name', 'deprecated', 'marketplaces', 'fromversion'],
            ContentTypes.INTEGRATION: ['display_name', 'type'],
            ContentTypes.SCRIPT: ['type'],
        }
