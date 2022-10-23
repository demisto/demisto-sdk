import logging
import shutil
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import (
    CONTRIBUTORS_README_TEMPLATE, MarketplaceVersions)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import get_mp_tag_parser
from demisto_sdk.commands.content_graph.common import (PACK_METADATA_FILENAME,
                                                       ContentType, Nodes, RelationshipType,
                                                       Relationships)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Integration

json = JSON_Handler()

logger = logging.getLogger('demisto-sdk')


class PackMetadata(BaseModel):
    name: str
    description: str
    created: str
    updated: str
    support: str
    email: str
    url: str
    author: str
    certification: str
    hidden: bool
    server_min_version: str = Field(alias='serverMinVersion')
    current_version: str = Field(alias='currentVersion')
    tags: List[str]
    categories: List[str]
    use_cases: List[str] = Field(alias='useCases')
    keywords: List[str]
    price: Optional[int] = None
    premium: Optional[bool] = None
    vendor_id: Optional[str] = Field(None, alias='vendorId')
    vendor_name: Optional[str] = Field(None, alias='vendorName')
    preview_only: Optional[bool] = Field(None, alias='previewOnly')


class Pack(BaseContent, PackMetadata, content_type=ContentType.PACK):
    path: Path
    contributors: Optional[List[str]] = None
    relationships: Relationships = Field(Relationships(), exclude=True)

    @property
    def content_items(self) -> List[ContentItem]:
        return [r.related_to for r in self.relationshipss if not r.is_nested and r.relationship_type == RelationshipType.IN_PACK]
    
    @property
    def integrations(self) -> List[Integration]:
        return [content_item for content_item in self.content_items if isinstance(content_item, Integration)] 
    
    @property
    def depends_on(self) -> List["Pack"]:
        return [r.related_to for r in self.relationshipss if r.relationship_type == RelationshipType.DEPENDS_ON]
    
    def dump_metadata(self, path: Path) -> None:
        metadata = self.dict(exclude={'path', 'node_id', 'content_type'})
        metadata['contentItems'] = {}
        for content_item in self.content_items:
            if content_item.content_type == ContentType.TEST_PLAYBOOK:
                continue
            try:
                metadata['contentItems'].setdefault(content_item.content_type.server_name, []).append(content_item.summary())
            except NotImplementedError as e:
                logger.debug(f'Could not add {content_item.name} to pack metadata: {e}')
        with open(path, 'w') as f:
            json.dump(metadata, f, indent=4)

    def dump_readme(self, path: Path, marketplace: MarketplaceVersions) -> None:
        shutil.copyfile(self.path / 'README.md', path)
        if self.contributors:
            fixed_contributor_names = [f' - {contrib_name}\n' for contrib_name in self.contributors]
            contribution_data = CONTRIBUTORS_README_TEMPLATE.format(contributors_names=''.join(fixed_contributor_names))
            with open(path, 'a+') as f:
                f.write(contribution_data)
        with open(path, 'r+') as f:
            try:
                text = f.read()
                parsed_text = get_mp_tag_parser(marketplace).parse_text(text)
                if len(text) != len(parsed_text):
                    f.seek(0)
                    f.write(parsed_text)
                    f.truncate()
            except Exception as e:
                logger.error(f'Failed dumping readme: {e}')

    def dump(self, path: Path, marketplace: MarketplaceVersions):
        try:
            path.mkdir(exist_ok=True, parents=True)
            for content_item in self.content_items:
                content_item.dump(path / content_item.content_type.as_folder, marketplace)
            self.dump_metadata(path / 'metadata.json')
            self.dump_readme(path / 'README.md', marketplace)
            shutil.copy(self.path / PACK_METADATA_FILENAME, path / PACK_METADATA_FILENAME)
            try:
                shutil.copytree(self.path / 'ReleaseNotes', path / 'ReleaseNotes')
            except FileNotFoundError:
                logger.info(f'No such file {self.path / "ReleaseNotes"}')
            try:
                shutil.copy(self.path / 'Author_image.png', path / 'Author_image.png')
            except FileNotFoundError:
                logger.info(f'No such file {self.path / "Author_image.png"}')
            logger.info(f'Dumped pack {self.name}. Files: {list(path.iterdir())}')
        except Exception as e:
            logger.error(f'Failed dumping pack {self.name}: {e}')
            raise

    def to_nodes(self) -> Nodes:
        return Nodes(self.to_dict(), *[content_item.to_dict() for content_item in self.content_items])
