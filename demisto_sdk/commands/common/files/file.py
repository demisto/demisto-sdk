import shutil
import urllib.parse
from abc import ABC, abstractmethod
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Set, Type, Union

import requests
from bs4.dammit import UnicodeDammit
from pydantic import BaseModel, validator
from requests.exceptions import RequestException

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    urljoin,
)
from demisto_sdk.commands.common.files.errors import (
    FileContentReadError,
    FileReadError,
    GitFileReadError,
    HttpFileReadError,
    LocalFileReadError,
    UnknownFileError,
)
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler
from demisto_sdk.commands.common.logger import logger


class File(ABC, BaseModel):
    git_util: GitUtil
    input_path: Path
    default_encoding: str = "utf-8"  # default encoding is utf-8

    class Config:
        arbitrary_types_allowed = (
            True  # allows having custom classes for properties in model
        )

    @property
    def input_file_content(self) -> bytes:
        return self.input_path.read_bytes()

    @property
    def normalized_suffix(self) -> str:
        if suffix := self.input_path.suffix.lower():
            return suffix[1:]
        return suffix

    @property
    def input_path_original_encoding(self) -> Optional[str]:
        return UnicodeDammit(self.input_file_content).original_encoding

    @property
    def input_file_size(self) -> int:
        return self.input_path.stat().st_size

    @classmethod
    def is_class_type(cls, path: Path) -> bool:
        return (
            path.name in cls.known_files()
            or path.suffix.lower() in cls.known_extensions()
        )

    @classmethod
    def known_files(cls) -> Set[str]:
        return set()

    @classmethod
    def known_extensions(cls) -> Set[str]:
        return set()

    @validator("git_util", always=True, pre=True)
    def validate_git_util(cls, v: Optional[GitUtil]) -> GitUtil:
        return v or GitUtil.from_content_path()

    def copy_file(self, destination_path: Union[Path, str]):
        shutil.copyfile(self.input_path, destination_path)

    @validator("input_path", always=True)
    def validate_input_path(cls, v: Optional[Path], values) -> Optional[Path]:
        if not v:
            return None
        if v.is_absolute():
            return v
        else:
            logger.debug(f"File {v} does not exist, getting full relative path")

        git_util: GitUtil = values["git_util"]

        path = git_util.repo.working_dir / v
        if path.exists():
            return path

        raise FileNotFoundError(f"File {path} does not exist")

    @classmethod
    def __file_factory(cls, path: Path) -> Type["File"]:
        def _file_factory(_cls):
            for subclass in _cls.__subclasses__():
                if subclass.is_class_type(path):
                    return subclass
                if _subclass := _file_factory(subclass):
                    return _subclass

            return None

        if file_object := _file_factory(cls):
            return file_object

        raise UnknownFileError(path)

    @abstractmethod
    def load(self, file_content: bytes):
        raise NotImplementedError(
            "load must be implemented for each File concrete object"
        )

    @classmethod
    @lru_cache
    def from_path(
        cls,
        input_path: Optional[Union[Path, str]] = None,
        git_util: Optional[GitUtil] = None,
        **kwargs,
    ) -> "File":

        if input_path:
            input_path = Path(input_path)

        model_attributes: Dict[str, Any] = {
            "input_path": input_path,
            "git_util": git_util,
        }

        model_attributes.update(kwargs)

        if cls is File and input_path:
            model = cls.__file_factory(input_path).parse_obj(  # type: ignore[arg-type]
                model_attributes
            )
        else:
            model = cls.parse_obj(model_attributes)
        logger.debug(f"Using model {model} for file {input_path}")
        return model

    @classmethod
    @lru_cache
    def read_from_file_content(
        cls,
        file_content: Union[bytes, BytesIO],
        handler: Optional[XSOAR_Handler] = None,
    ):
        if cls is File:
            raise ValueError(
                "when reading from file content please specify concrete class"
            )

        model_attributes: Dict[str, Any] = {}
        if handler:
            model_attributes["handler"] = handler

        # builds up the object without validations, when loading from file content, no need to init path and git_util
        model = cls.construct(**model_attributes)

        if isinstance(file_content, BytesIO):
            file_content = file_content.read()

        try:
            return model.load(file_content)
        except LocalFileReadError as e:
            logger.error(f"Could not read file content as {cls.__name__} file")
            raise FileContentReadError(file_content, exc=e.original_exc)

    @classmethod
    @lru_cache
    def read_from_local_path(
        cls,
        path: Union[Path, str],
        git_util: Optional[GitUtil] = None,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ) -> Any:
        if clear_cache:
            cls.read_from_local_path.clear_cache()
        model = cls.from_path(input_path=path, git_util=git_util, handler=handler)
        return model.read_local_file()

    def read_local_file(self) -> Any:
        try:
            return self.load(self.input_file_content)
        except FileReadError:
            logger.exception(
                f"Could not read file {self.input_path} as {self.__class__.__name__} file"
            )
            raise

    @classmethod
    @lru_cache
    def read_from_git_path(
        cls,
        path: Union[str, Path],
        tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
        git_util: Optional[GitUtil] = None,
        from_remote: bool = True,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ) -> Any:
        if clear_cache:
            cls.read_from_git_path.clear_cache()
        model = cls.from_path(input_path=path, git_util=git_util, handler=handler)
        return model.read_git_file(tag, from_remote=from_remote)

    def read_git_file(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH, from_remote: bool = True
    ):
        try:
            return self.load(
                self.git_util.read_file_content(
                    self.input_path, commit_or_branch=tag, from_remote=from_remote
                )
            )
        except Exception as e:
            if from_remote:
                tag = f"{DEMISTO_GIT_UPSTREAM}:{tag}"
            logger.exception(
                f"Could not read git file {self.input_path} from {tag} as {self.__class__.__name__} file"
            )
            raise GitFileReadError(
                self.input_path,
                tag=tag,
                exc=e,
            )

    @classmethod
    def read_from_github_api(
        cls,
        path: str,
        git_content_config: Optional[GitContentConfig] = None,
        tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ):
        if not git_content_config:
            git_content_config = GitContentConfig()

        git_path_url = urljoin(git_content_config.base_api, tag, path)
        github_token = git_content_config.CREDENTIALS.github_token

        timeout = 10

        cls.__file_factory(Path(path)) if cls is File else cls

        try:
            return cls.read_from_http_request(
                git_path_url,
                headers={
                    "Authorization": f"Bearer {github_token}" if github_token else "",
                    "Accept": "application/vnd.github.VERSION.raw",
                },
                timeout=timeout,
                handler=handler,
                clear_cache=clear_cache,
            )
        except FileReadError as e:
            logger.warning(
                f"Received error {e} when trying to retrieve {git_path_url} content from Github, retrying"
            )
            return cls.read_from_http_request(
                git_path_url, params={"token": github_token}, timeout=timeout
            )

    @classmethod
    def read_from_gitlab_api(
        cls,
        path: str,
        git_content_config: Optional[GitContentConfig] = None,
        tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ):
        if not git_content_config:
            git_content_config = GitContentConfig()

        git_path_url = urljoin(
            git_content_config.base_api, "files", urllib.parse.quote_plus(path), "raw"
        )
        gitlab_token = git_content_config.CREDENTIALS.gitlab_token

        model = cls.__file_factory(Path(path)) if cls is File else cls
        return model.read_from_http_request(
            git_path_url,
            headers={"PRIVATE-TOKEN": gitlab_token},
            params={"ref": tag},
            handler=handler,
            clear_cache=clear_cache,
        )

    @classmethod
    def read_from_http_request(
        cls,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        verify: bool = True,
        timeout: Optional[int] = None,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ):
        # if clear_cache:
        #     cls.read_from_http_request.clear_cache()
        try:
            response = requests.get(
                url,
                params=params,
                verify=verify,
                timeout=timeout,
                headers=headers,
            )
            response.raise_for_status()
        except RequestException as e:
            logger.exception(f"Could not retrieve file from {url}")
            raise HttpFileReadError(url, exc=e)

        try:
            return cls.read_from_file_content(response.content, handler=handler)
        except FileContentReadError as e:
            logger.exception(f"Could not read file from {url} as {cls.__name__} file")
            raise HttpFileReadError(url=url, exc=e)

    @classmethod
    def write_file(
        cls, data: Any, output_path: Union[Path, str], encoding: Optional[str] = None
    ):
        model = cls.from_path()
        model.write(data, path=Path(output_path), encoding=encoding)

    @abstractmethod
    def _write(self, data: Any, path: Path, encoding: Optional[str] = None) -> None:
        raise NotImplementedError(
            "write must be implemented for each File concrete object"
        )

    def write(
        self, data: Any, path: Union[str, Path], encoding: Optional[str] = None
    ) -> None:
        def _write_safe_unicode():
            self._write(data, path=path)

        if encoding:
            self._write(data, path=path, encoding=encoding)
        else:
            try:
                _write_safe_unicode()
            except UnicodeDecodeError:
                original_file_encoding = UnicodeDammit(
                    path.read_bytes()
                ).original_encoding
                if original_file_encoding == self.default_encoding:
                    logger.error(
                        f"{path} is encoded as unicode, cannot handle the error, raising it"
                    )
                    raise

                logger.debug(
                    f"deleting {path} - it will be rewritten as unicode (was {original_file_encoding})"
                )
                path.unlink()  # deletes the file
                logger.debug(f"rewriting {path} as unicode file")
                _write_safe_unicode()  # recreates the file
