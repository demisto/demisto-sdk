from abc import ABC
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Union

from pydantic import BaseModel

from demisto_sdk.commands.common.constants import (
    AUTHOR_IMAGE_FILE_NAME,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_README_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME,
    GitStatuses,
    RelatedFileType,
)
from demisto_sdk.commands.common.files import TextFile
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.parsers.content_item import (
    NotAContentItemException,
)


class RelatedFile(ABC, BaseModel):
    file_type: ClassVar[RelatedFileType]

    def __init__(self, main_file_path: Path, git_sha: Optional[str] = None) -> None:
        self.main_file_path: Path = main_file_path
        self.git_sha = git_sha
        self.file_paths: List[str] = self.get_optional_paths()
        self.exist: bool = False
        self.file_path: Path = self.find_the_right_path()
        self.git_status: Union[GitStatuses, None] = self.get_git_status()

    def get_git_status(self) -> Union[GitStatuses, None]:
        status = None
        if self.git_sha:
            git_util = GitUtil()
            remote, branch = git_util.handle_prev_ver(
                self.git_sha  # type: ignore[arg-type]
            )
            status = git_util._check_file_status(str(self.file_path), remote, branch)
        return None if not status else GitStatuses(status)

    def find_the_right_path(self) -> Path:
        for path in self.file_paths:
            if self.is_file_exist(Path(path), self.git_sha):
                self.exist = True
                return Path(path)
        return Path(self.file_paths[-1])

    def get_optional_paths(self) -> List[str]:
        raise NotImplementedError

    def get_file_content(self) -> Any:
        raise NotImplementedError

    def is_file_exist(self, file_path: Path, git_sha: Optional[str]) -> bool:
        if git_sha:
            # implement is_exist with git_sha logic
            return file_path.exists()
        else:
            return file_path.exists()


class TextFiles(RelatedFile):
    def __init__(self, main_file_path: Path, git_sha: Optional[str] = None) -> None:
        super().__init__(main_file_path, git_sha)

    def get_file_content(self) -> str:
        for file_path in self.file_paths:
            try:
                if self.git_sha:
                    file = TextFile.read_from_git_path(
                        path=file_path,
                        tag=self.git_sha,
                    )
                else:
                    file = TextFile.read_from_local_path(path=file_path)
                self.file_paths = [file_path]
                return file
            except Exception as e:
                logger.error(f"Failed to get related text file, error: {e}")
                continue
        raise NotAContentItemException(
            f"The {self.file_type.value} file could not be found in the following paths: {', '.join(self.file_paths)}"
        )


class YmlRelatedFile(RelatedFile):
    file_type = RelatedFileType.YML


class JsonRelatedFile(RelatedFile):
    file_type = RelatedFileType.JSON


class RNRelatedFile(TextFiles):
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


class ReadmeRelatedFile(TextFiles):
    file_type = RelatedFileType.README

    def __init__(
        self,
        main_file_path: Path,
        is_pack_readme: bool = False,
        git_sha: Optional[str] = None,
    ) -> None:
        self.is_pack_readme = is_pack_readme
        super().__init__(main_file_path, git_sha)

    def get_optional_paths(self) -> List[str]:
        return (
            [
                str(self.main_file_path.parent / PACKS_README_FILE_NAME),
                str(self.main_file_path).replace(".yml", f"_{PACKS_README_FILE_NAME}"),
            ]
            if not self.is_pack_readme
            else [str(self.main_file_path / PACKS_README_FILE_NAME)]
        )


class DescriptionRelatedFile(TextFiles):
    file_type = RelatedFileType.DESCRIPTION

    def get_optional_paths(self) -> List[str]:
        return [
            str(
                self.main_file_path.parent
                / f"{self.main_file_path.parts[-2]}_description.md"
            )
        ]


class DarkSVGRelatedFile(RelatedFile):
    file_type = RelatedFileType.DARK_SVG

    def get_optional_paths(self) -> List[str]:
        return [
            str(
                self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_dark.svg"
            )
        ]


class LightSVGRelatedFile(RelatedFile):
    file_type = RelatedFileType.LIGHT_SVG

    def get_optional_paths(self) -> List[str]:
        return [
            str(
                self.main_file_path.parent
                / f"{self.main_file_path.parts[-2]}_light.svg"
            )
        ]


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
            str(
                self.main_file_path.parent
                / f"{self.main_file_path.parts[-2]}_image.png"
            ),
        ]


class CodeRelatedFile(TextFiles):
    file_type = RelatedFileType.CODE

    def __init__(
        self, main_file_path: Path, suffix: str, git_sha: Optional[str] = None
    ) -> None:
        self.suffix = suffix
        super().__init__(main_file_path, git_sha)

    def get_optional_paths(self) -> List[str]:
        return [
            str(
                self.main_file_path.parent
                / f"{self.main_file_path.parts[-2]}{self.suffix}"
            ),
            str(self.main_file_path),
        ]


class TestCodeRelatedFile(CodeRelatedFile):
    file_type = RelatedFileType.TEST_CODE

    def get_optional_paths(self) -> List[str]:
        return [
            str(
                self.main_file_path.parent
                / f"{self.main_file_path.parts[-2]}_test{self.suffix}"
            )
        ]
