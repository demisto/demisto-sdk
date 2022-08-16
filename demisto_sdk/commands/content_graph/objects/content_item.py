from pathlib import Path
from typing import Any, Dict, Optional, List, Union

from packaging.version import Version, parse
from pathlib import Path
from pydantic import Field

from demisto_sdk.commands.common.tools import (
    get_files_in_dir,
    get_json, get_yaml,
    get_yml_paths_in_dir
)
from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_TO_VERSION, MarketplaceVersions
from demisto_sdk.commands.content_graph.constants import ContentTypes, Rel, UNIFIED_FILES_SUFFIXES, RelationshipData
import demisto_sdk.commands.content_graph.objects.base_content as base_content


class NotAContentItem(Exception):
    pass


class ContentItem(base_content.BaseContent):
    path: Path
    pack_marketplaces: List[MarketplaceVersions] = Field([], exclude=True)
    name: str = ''
    from_version: str = ''
    to_version: str = ''
    relationships: Dict[Rel, List[RelationshipData]] = Field({}, exclude=True)

    @staticmethod
    def is_package(path: Path) -> bool:
        return path.is_dir()

    @staticmethod
    def is_unified_file(path: Path) -> bool:
        return path.suffix in UNIFIED_FILES_SUFFIXES

    @staticmethod
    def is_content_item(path: Path) -> bool:
        return ContentItem.is_package(path) or ContentItem.is_unified_file(path)

    def add_relationship(
        self,
        relationship: Rel,
        target: str,
        **kwargs: Dict[str, Any],
    ) -> None:
        relationship_data: RelationshipData = {
            'source_node_id': self.object_id,
            'source_fromversion': self.from_version,
            'source_marketplaces': self.marketplaces,
            'target': target,
        }
        relationship_data.update(kwargs)
        self.relationships.setdefault(relationship, []).append(relationship_data)

    def add_dependency(
        self,
        dependency_id: str,
        dependency_type: Optional[ContentTypes] = None,
        is_mandatory: bool = True
    ) -> None:
        if dependency_type is None:  # and self.content_type == ContentTypes.SCRIPT:
            relationship = Rel.USES_COMMAND_OR_SCRIPT
            target = dependency_id
        else:
            relationship = Rel.USES
            target = f'{dependency_type}:{dependency_id}'

        self.add_relationship(
            relationship,
            target=target,
            mandatorily=is_mandatory,
        )


class YAMLContentItem(ContentItem):
    yml_data: Dict[str, Any] = Field({}, exclude=True)

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if self.parsing_object:
            self.yml_data = self.get_yaml()
            self.name = self.yml_data.get('name')
            self.deprecated = self.yml_data.get('deprecated', False)
            self.from_version = self.yml_data.get('fromversion')
            self.to_version = self.yml_data.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)
            self.marketplaces = self.yml_data.get('marketplaces', []) or self.pack_marketplaces

            self.connect_to_tests()

    def connect_to_tests(self) -> None:
        tests_playbooks: List[str] =  self.yml_data.get('tests', [])
        for test_playbook_id in tests_playbooks:
            if 'no test' not in test_playbook_id.lower():
                tpb_node_id = f'{ContentTypes.TEST_PLAYBOOK}:{test_playbook_id}'
                self.add_relationship(
                    Rel.TESTED_BY,
                    target=tpb_node_id,
                )

    def get_yaml(self) -> Dict[str, Union[str, List[str]]]:
        if not self.path.is_dir():
            yaml_path = self.path.as_posix()
        else:
            _, yaml_path = get_yml_paths_in_dir(self.path.as_posix())
        if not yaml_path:
            raise NotAContentItem

        self.path = Path(yaml_path)
        return get_yaml(self.path.as_posix())


class JSONContentItem(ContentItem):
    json_data: Dict[str, Any] = Field({}, exclude=True)

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if self.parsing_object:
            self.json_data = self.get_json()
            self.object_id = self.json_data.get('id')
            self.name = self.json_data.get('name')
            self.deprecated = self.json_data.get('deprecated', False)
            self.from_version = self.json_data.get('fromVersion')
            self.to_version = self.json_data.get('toVersion', DEFAULT_CONTENT_ITEM_TO_VERSION)
            self.marketplaces = self.json_data.get('marketplaces', []) or self.pack_marketplaces

    def get_json(self) -> Dict[str, Any]:
        if self.path.is_dir():
            json_files_in_dir = get_files_in_dir(self.path.as_posix(), ['json'], False)
            if len(json_files_in_dir) != 1:
                raise NotAContentItem(f'Directory {self.path} must have a single JSON file.')
            self.path = Path(json_files_in_dir[0])
        return get_json(self.path.as_posix())
