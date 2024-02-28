from abc import ABC
from pathlib import Path
from typing import ClassVar, List, Union

from pydantic import BaseModel

from demisto_sdk.commands.common.constants import (
    AUTHOR_IMAGE_FILE_NAME,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_README_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME,
    GitStatuses,
    RelatedFileType,
)


class RelatedFile(ABC, BaseModel):
    git_status: ClassVar[Union[GitStatuses, None]] = None
    file_type: ClassVar[RelatedFileType]
    
    def __init__(self, main_file_path: Path) -> None:
        self.main_file_path: Path = main_file_path
        self.file_paths: List[str] = self.get_optional_paths()

    def get_optional_paths(self) -> List[str]:
        raise NotImplementedError
      
class YmlRelatedFile(RelatedFile):
    file_type = RelatedFileType.YML
        
    def get_optional_paths(self) -> List[str]:
        raise NotImplementedError

class JsonRelatedFile(RelatedFile):
    file_type = RelatedFileType.JSON
        
    def get_optional_paths(self) -> List[str]:
        raise NotImplementedError

class RNRelatedFile(RelatedFile):
    file_type = RelatedFileType.RELEASE_NOTES
        
    def get_optional_paths(self) -> List[str]:
        raise NotImplementedError

class AuthorImageRelatedFile(RelatedFile):
    file_type = RelatedFileType.AUTHOR_IMAGE
        
    def get_optional_paths(self) -> List[str]:
        return [str(self.main_file_path / AUTHOR_IMAGE_FILE_NAME)]

class SecretsIgnoreRelatedFile(RelatedFile):
    file_type = RelatedFileType.SECRETS_IGNORE
        
    def get_optional_paths(self) -> List[str]:
        return [str(self.main_file_path / PACKS_WHITELIST_FILE_NAME)]

class PackIgnoreRelatedFile(RelatedFile):
    file_type = RelatedFileType.PACK_IGNORE
        
    def get_optional_paths(self) -> List[str]:
        return [str(self.main_file_path / PACKS_PACK_IGNORE_FILE_NAME)]

class XifRelatedFile(RelatedFile):
    file_type = RelatedFileType.XIF
        
    def get_optional_paths(self) -> List[str]:
        return [str(self.main_file_path).replace(".yml", ".xif")]

class SchemaRelatedFile(RelatedFile):
    file_type = RelatedFileType.SCHEMA
        
    def get_optional_paths(self) -> List[str]:
        return [str(self.main_file_path).replace(".yml", "_Schema.json")]

class ReadmeRelatedFile(RelatedFile):
    file_type = RelatedFileType.README
    
    def __init__(self, main_file_path: Path, is_pack_readme: bool = False) -> None:
        self.is_pack_readme = is_pack_readme
        super().__init__(main_file_path)
        
    def get_optional_paths(self) -> List[str]:
        return [
                        str(self.main_file_path.parent / PACKS_README_FILE_NAME),
                        str(self.main_file_path).replace(".yml", f"_{PACKS_README_FILE_NAME}")
                    ] if not self.is_pack_readme else [str(self.main_file_path / PACKS_README_FILE_NAME)]

class DescriptionRelatedFile(RelatedFile):
    file_type = RelatedFileType.DESCRIPTION
        
    def get_optional_paths(self) -> List[str]:
        return [
                        str(self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_description.md")
                    ]

class DarkSVGRelatedFile(RelatedFile):
    file_type = RelatedFileType.DARK_SVG
        
    def get_optional_paths(self) -> List[str]:
        return [str(self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_dark.svg")]

class LightSVGRelatedFile(RelatedFile):
    file_type = RelatedFileType.LIGHT_SVG
        
    def get_optional_paths(self) -> List[str]:
        return [str(self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_light.svg")]

class ImageRelatedFile(RelatedFile):
    file_type = RelatedFileType.IMAGE
        
    def get_optional_paths(self) -> List[str]:
        return [
                        str(
                            self.main_file_path.parents[1]
                            / "doc_files"
                            / str(self.main_file_path.parts[-1])
                            .replace(".yml", ".png")
                            .replace("playbook-", "")
                        ),
                        str(self.main_file_path).replace(".yml", ".png"),
                        str(self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_image.png")
                    ]

class CodeRelatedFile(RelatedFile):
    file_type = RelatedFileType.CODE
        
    def __init__(self, main_file_path: Path, suffix: str) -> None:
        self.suffix = suffix
        super().__init__(main_file_path)
        
    def get_optional_paths(self) -> List[str]:
        return [
                        str(self.main_file_path.parent / f"{self.main_file_path.parts[-2]}{self.suffix}"),
                        str(self.main_file_path),
                    ]

class TestCodeRelatedFile(CodeRelatedFile, RelatedFile):
    file_type = RelatedFileType.TEST_CODE
        
    def get_optional_paths(self) -> List[str]:
        return [
                        str(self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_test{self.suffix}")
                    ]
