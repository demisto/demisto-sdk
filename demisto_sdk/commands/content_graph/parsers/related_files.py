import base64
import re
from abc import ABC
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set, Union

from demisto_sdk.commands.common.constants import (
    AUTHOR_IMAGE_FILE_NAME,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_README_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME,
    RELEASE_NOTES_DIR,
    VERSION_CONFIG_FILE_NAME,
    GitStatuses,
)
from demisto_sdk.commands.common.files import TextFile
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_child_files


class RelatedFileType(Enum):
    YML = "yml"
    JSON = "json"
    README = "readme"
    DESCRIPTION_File = "description_file"
    IMAGE = "image"
    DARK_SVG = "dark_svg"
    LIGHT_SVG = "light_svg"
    CODE_FILE = "code_file"
    TEST_CODE_FILE = "test_code_file"
    SCHEMA = "schema_file"
    XIF = "xif_file"
    PACK_IGNORE = "pack_ignore"
    SECRETS_IGNORE = "secrets_ignore"
    AUTHOR_IMAGE = "author_image_file"
    RELEASE_NOTE = "release_note"
    VERSION_CONFIG = "version_config"


class RelatedFile(ABC):
    file_type: ClassVar[RelatedFileType]

    def __init__(
        self,
        main_file_path: Path,
        git_sha: Optional[str] = None,
        prev_ver: Optional[str] = None,
    ) -> None:
        self.prev_ver = prev_ver
        self.main_file_path: Path = main_file_path
        self.git_sha = git_sha
        self.exist: bool = False
        self.file_path: Path = self.find_the_right_path(self.get_optional_paths())

    @property
    def git_status(self) -> Union[GitStatuses, None]:
        git_util = GitUtil.from_content_path()
        remote, branch = git_util.handle_prev_ver(
            self.prev_ver  # type: ignore[arg-type]
        )
        status = git_util._check_file_status(
            str(self.file_path), remote, branch, feature_branch_or_hash=self.git_sha
        )
        return None if not status else GitStatuses(status)

    def find_the_right_path(self, file_paths: List[Path]) -> Path:
        for path in file_paths:
            if self.is_file_exist(path, self.git_sha):
                self.exist = True
                return path
        return file_paths[-1]

    def get_optional_paths(self) -> List[Path]:
        raise NotImplementedError

    def file_content(self) -> Any:
        raise NotImplementedError

    def is_file_exist(self, file_path: Path, git_sha: Optional[str]) -> bool:
        if git_sha:
            # Checking if file exist in remote branch/sha.
            git_util = GitUtil.from_content_path()
            return git_util.is_file_exist_in_commit_or_branch(
                file_path, git_sha
            ) or git_util.is_file_exist_in_commit_or_branch(file_path, git_sha, False)
        else:
            return file_path.exists()


class TextFiles(RelatedFile):
    def __init__(
        self,
        main_file_path: Path,
        git_sha: Optional[str] = None,
        prev_ver: Optional[str] = None,
    ) -> None:
        self.file_content_str = ""
        super().__init__(main_file_path, git_sha, prev_ver)

    @property
    def file_content(self) -> str:
        if not self.file_content_str:
            try:
                if self.git_sha and not self.prev_ver:
                    self.file_content_str = TextFile.read_from_git_path(
                        path=self.file_path,
                        tag=self.git_sha,
                    )
                else:
                    self.file_content_str = TextFile.read_from_local_path(
                        path=self.file_path
                    )
            except Exception as e:
                logger.debug(f"Failed to get related text file, error: {e}")
        return self.file_content_str

    @file_content.setter
    def file_content(self, content: str):
        """Setter for the file_content property. Updates the file content."""
        self.file_content_str = content
        TextFile.write(content, self.file_path)


class RNRelatedFile(TextFiles):
    file_type = RelatedFileType.RELEASE_NOTE

    def __init__(
        self,
        main_file_path: Path,
        latest_rn: str,
        git_sha: Optional[str] = None,
        prev_ver: Optional[str] = None,
    ) -> None:
        self.latest_rn_version = latest_rn
        self.rns_list: List[str] = []
        super().__init__(main_file_path, git_sha, prev_ver)

    def get_optional_paths(self) -> List[Path]:
        return [
            self.main_file_path
            / RELEASE_NOTES_DIR
            / f"{self.latest_rn_version.replace('.', '_')}.md"
        ]

    @property
    def all_rns(self) -> List[str]:
        if not self.rns_list:
            rns_dir_path = self.main_file_path / RELEASE_NOTES_DIR
            if self.git_sha:
                git_util = GitUtil.from_content_path()
                if not git_util.is_file_exist_in_commit_or_branch(
                    rns_dir_path, self.git_sha
                ):
                    self.rns_list = []
                else:
                    self.rns_list = git_util.list_files_in_dir(
                        rns_dir_path, self.git_sha
                    )
            else:
                self.rns_list = get_child_files(rns_dir_path)
        return self.rns_list


class SecretsIgnoreRelatedFile(RelatedFile):
    file_type = RelatedFileType.SECRETS_IGNORE

    def get_optional_paths(self) -> List[Path]:
        return [self.main_file_path / PACKS_WHITELIST_FILE_NAME]


class PackIgnoreRelatedFile(RelatedFile):
    file_type = RelatedFileType.PACK_IGNORE

    def get_optional_paths(self) -> List[Path]:
        return [self.main_file_path / PACKS_PACK_IGNORE_FILE_NAME]


class XifRelatedFile(TextFiles):
    file_type = RelatedFileType.XIF

    def get_optional_paths(self) -> List[Path]:
        return [Path(str(self.main_file_path).replace(".yml", ".xif"))]

    def get_dataset_from_xif(self) -> Set[str]:
        dataset = re.findall('dataset[ ]?=[ ]?(["a-zA-Z_0-9]+)', self.file_content)
        if dataset:
            return {dataset_name.strip('"') for dataset_name in dataset}
        return set()


class JsonFiles(RelatedFile):
    file_type = RelatedFileType.JSON

    @cached_property
    def file_content(self) -> Optional[Dict[str, Any]]:
        """
        Reads and returns JSON content from the first optional path.
        Returns None if the file cannot be read or parsed.
        """
        paths = self.get_optional_paths()
        if not paths:
            return None  # No paths available
        try:
            with open(paths[0], "r") as file:
                json_data = json5.loads(s=file.read())
            return json_data
        except Exception as e:
            logger.debug(f"Failed to get related text file, error: {e}")
        return None


class VersionConfigRelatedFile(JsonFiles):
    def __init__(
        self,
        main_file_path: Path,
        git_sha: Optional[str] = None,
        prev_ver: Optional[str] = None,
    ) -> None:
        super().__init__(main_file_path, git_sha, prev_ver)

    file_type = RelatedFileType.VERSION_CONFIG

    def get_optional_paths(self) -> List[Path]:
        return [self.main_file_path / VERSION_CONFIG_FILE_NAME]


class SchemaRelatedFile(JsonFiles):
    file_type = RelatedFileType.SCHEMA

    def get_optional_paths(self) -> List[Path]:
        return [Path(str(self.main_file_path).replace(".yml", "_schema.json"))]


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

    def get_optional_paths(self) -> List[Path]:
        return (
            [
                self.main_file_path.parent / PACKS_README_FILE_NAME,
                Path(
                    str(self.main_file_path).replace(
                        ".yml", f"_{PACKS_README_FILE_NAME}"
                    )
                ),
            ]
            if not self.is_pack_readme
            else [self.main_file_path / PACKS_README_FILE_NAME]
        )


class DescriptionRelatedFile(TextFiles):
    file_type = RelatedFileType.DESCRIPTION_File

    def get_optional_paths(self) -> List[Path]:
        return [
            self.main_file_path.parent
            / f"{self.main_file_path.parts[-2]}_description.md"
        ]


class ImageFiles(RelatedFile):
    def get_file_size(self):
        raise NotImplementedError

    def get_file_dimensions(self):
        raise NotImplementedError

    def load_image(self):
        raise NotImplementedError


class PNGFiles(ImageFiles):
    def get_file_size(self):
        return self.file_path.stat()

    def load_image(self) -> Union[str, bytearray, memoryview]:
        encoded_image = ""
        with open(self.file_path, "rb") as image:
            image_data = image.read()
            encoded_image = base64.b64encode(image_data)  # type: ignore
            if isinstance(encoded_image, bytes):
                encoded_image = encoded_image.decode("utf-8")
        return encoded_image


class SVGFiles(ImageFiles):
    def load_image(self) -> bytes:
        encoded_image = b""
        with open(self.file_path, "rb") as image_file:
            encoded_image = image_file.read()  # type: ignore
        return encoded_image


class DarkSVGRelatedFile(RelatedFile):
    file_type = RelatedFileType.DARK_SVG

    def get_optional_paths(self) -> List[Path]:
        return [
            self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_dark.svg"
        ]


class LightSVGRelatedFile(RelatedFile):
    file_type = RelatedFileType.LIGHT_SVG

    def get_optional_paths(self) -> List[Path]:
        return [
            self.main_file_path.parent / f"{self.main_file_path.parts[-2]}_light.svg"
        ]


class ImageRelatedFile(PNGFiles):
    file_type = RelatedFileType.IMAGE

    def get_optional_paths(self) -> List[Path]:
        """
        Generate a list of optional paths for the content item's image.
        The right path will be found later.
        Returns:
            List[Path]: the list of optional paths.
        """
        optional_paths_list = [
            self.main_file_path.parents[1]
            / "doc_files"
            / str(self.main_file_path.parts[-1])
            .replace(".yml", ".png")
            .replace(
                "playbook-", ""
            ),  # In case the playbook's image is located under doc_files folder with the same name as the playbook.
            self.main_file_path.parent
            / f"{self.main_file_path.parts[-2]}_image.png",  # In case of integration image where the image is located in the integration folder with the same name as the integration.
        ]
        if (
            self.main_file_path.suffix == ".json"
        ):  # when editing .yml files, we don't want to end up with the yml file as part of the optional paths.
            optional_paths_list.append(
                Path(str(self.main_file_path).replace(".json", "_image.png"))
            )
        else:  # when editing .json files, we don't want to end up with the json file as part of the optional paths.
            optional_paths_list.append(
                Path(str(self.main_file_path).replace(".yml", ".png")),
            )
        return optional_paths_list


class AuthorImageRelatedFile(PNGFiles):
    file_type = RelatedFileType.AUTHOR_IMAGE

    def get_optional_paths(self) -> List[Path]:
        return [self.main_file_path / AUTHOR_IMAGE_FILE_NAME]


class CodeRelatedFile(TextFiles):
    file_type = RelatedFileType.CODE_FILE

    def __init__(
        self, main_file_path: Path, suffix: str, git_sha: Optional[str] = None
    ) -> None:
        self.suffix = suffix
        super().__init__(main_file_path, git_sha)

    def get_optional_paths(self) -> List[Path]:
        return [
            self.main_file_path.parent
            / f"{self.main_file_path.parts[-2]}{self.suffix}",
            self.main_file_path,
        ]


class TestCodeRelatedFile(CodeRelatedFile):
    file_type = RelatedFileType.TEST_CODE_FILE

    def get_optional_paths(self) -> List[Path]:
        return [
            self.main_file_path.parent
            / f"{self.main_file_path.parts[-2]}_test{self.suffix}"
        ]
