import inspect
import shutil
import urllib.parse
from abc import ABC, abstractmethod
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union

import requests
from bs4.dammit import UnicodeDammit
from pydantic import BaseModel, PrivateAttr, validator
from requests.exceptions import ConnectionError, RequestException, Timeout

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    urljoin,
)
from demisto_sdk.commands.common.files.errors import (
    FileContentReadError,
    FileReadError,
    FileWriteError,
    GitFileReadError,
    HttpFileReadError,
    LocalFileReadError,
    UnknownFileError,
)
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import retry


class File(ABC, BaseModel):
    git_util: GitUtil
    input_path: Path
    _input_path_content: bytes = PrivateAttr(None)
    default_encoding: str = "utf-8"  # default encoding is utf-8

    class Config:
        arbitrary_types_allowed = (
            True  # allows having custom classes for properties in model
        )

    @validator("git_util", pre=True, always=True)
    def get_git_util(cls, v: Optional[GitUtil]) -> GitUtil:
        return v or GitUtil.from_content_path()

    @validator("input_path", always=True)
    def get_input_path(cls, v: Path, values: Dict) -> Path:
        input_path = v
        git_util = values["git_util"]

        if input_path.is_absolute():
            return input_path
        else:
            logger.debug(
                f"path {input_path} is not absolute, trying to get full relative path from {git_util.repo.working_dir}"
            )

        input_path = git_util.repo.working_dir / input_path
        if not input_path.exists():
            raise FileNotFoundError(f"File {input_path} does not exist")

        return input_path

    @property
    def content(self) -> bytes:
        if self._input_path_content is None:
            self._input_path_content = self.input_path.read_bytes()
        return self._input_path_content

    @property
    def normalized_suffix(self) -> str:
        if suffix := self.input_path.suffix.lower():
            return suffix[1:]
        return suffix

    @property
    def input_path_original_encoding(self) -> Optional[str]:
        return UnicodeDammit(self.content).original_encoding

    @property
    def size(self) -> int:
        return self.input_path.stat().st_size

    def copy_file(self, destination_path: Union[Path, str]):
        shutil.copyfile(self.input_path, destination_path)

    @abstractmethod
    def load(self, file_content: bytes) -> Any:
        """
        Loads the file as the requested file type.

        Args:
            file_content: the file content in bytes

        Returns:
            Any: the file content in the desired format
        """
        raise NotImplementedError(
            "load must be implemented for each File concrete object"
        )

    @classmethod
    @abstractmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        raise NotImplementedError

    @classmethod
    def __file_factory(cls, path: Path) -> Type["File"]:
        def _file_factory(_cls):
            for subclass in _cls.__subclasses__():
                if not inspect.isabstract(subclass) and subclass.is_model_type_by_path(
                    path
                ):
                    return subclass
                if _subclass := _file_factory(subclass):
                    return _subclass
            return None

        if file_object := _file_factory(cls):
            return file_object

        raise UnknownFileError(f"Could not identify file {path}")

    @classmethod
    @lru_cache
    def _from_path(
        cls,
        input_path: Union[Path, str],
        git_util: Optional[GitUtil] = None,
        **kwargs,
    ) -> "File":
        """
        Returns the correct file model

        Args:
            input_path: the file input path
            git_util: whether there should be any customized git util
            **kwargs: any additional arguments to initialize the model

        Returns:
            File: any subclass of the File model.
        """
        input_path = Path(input_path)

        model_attributes: Dict[str, Any] = {
            "input_path": input_path,
            "git_util": git_util,
        }

        model_attributes.update(kwargs)

        if cls is File:
            model = cls.__file_factory(input_path)
        else:
            model = cls
        logger.debug(f"Using model {model} for file {input_path}")
        return model.parse_obj(model_attributes)

    @classmethod
    @lru_cache
    def read_from_file_content(
        cls,
        file_content: Union[bytes, BytesIO],
        handler: Optional[XSOAR_Handler] = None,
    ) -> Any:
        """
        Read a file from its representation in bytes.

        Args:
            file_content: the file content in bytes / bytesIo
            handler: whether a custom handler is required, if not takes the default.

        Returns:
            Any: the file content in the desired format
        """
        if cls is File:
            raise ValueError(
                "when reading from file content please specify concrete class"
            )

        model_attributes: Dict[str, Any] = {"_input_path_content": file_content}
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
            raise FileContentReadError(exc=e.original_exc)

    @classmethod
    @lru_cache
    def read_from_local_path(
        cls,
        path: Union[Path, str],
        git_util: Optional[GitUtil] = None,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ) -> Any:
        """
        Reads a file from a local path in the file system.

        Args:
            path: the path of the file
            git_util: whether custom git-util is required
            handler: whether a custom handler is required, if not takes the default.
            clear_cache: whether to clear cache

        Returns:
            Any: the file content in the desired format
        """
        if clear_cache:
            cls.read_from_local_path.cache_clear()
        model = cls._from_path(input_path=path, git_util=git_util, handler=handler)
        return model.__read_local_file()

    def __read_local_file(self) -> Any:
        try:
            return self.load(self.content)
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
        """
        Reads a file from a specific git sha/branch.

        Args:
            path: the path to the file
            tag: branch / sha of the desired commit
            git_util: whether custom git-util is required
            from_remote: whether it should be taken from remote branch/sha or local branch/sha
            handler: whether a custom handler is required, if not takes the default.
            clear_cache: whether to clear cache

        Returns:
            Any: the file content in the desired format
        """
        if clear_cache:
            cls.read_from_git_path.cache_clear()
        model = cls._from_path(input_path=path, git_util=git_util, handler=handler)
        return model.__read_git_file(tag, from_remote=from_remote)

    def __read_git_file(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH, from_remote: bool = True
    ) -> Any:
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
        verify_ssl: bool = True,
    ) -> Any:
        """
        Reads a file from Github api.

        Args:
            path: the path to the file in github
            git_content_config: git content config object
            tag: the branch/sha to take the file from within Github
            handler: whether a custom handler is required, if not takes the default.
            clear_cache: whether to clear cache
            verify_ssl: whether SSL should be verified

        Returns:
            Any: the file content in the desired format
        """
        if not git_content_config:
            git_content_config = GitContentConfig()

        git_path_url = urljoin(git_content_config.base_api, tag, path)
        github_token = git_content_config.CREDENTIALS.github_token

        timeout = 10

        try:
            return cls.read_from_http_request(
                git_path_url,
                headers=frozenset(
                    {
                        "Authorization": f"Bearer {github_token}"
                        if github_token
                        else "",
                        "Accept": "application/vnd.github.VERSION.raw",
                    }.items()
                ),
                timeout=timeout,
                handler=handler,
                clear_cache=clear_cache,
                verify=verify_ssl,
            )
        except FileReadError as e:
            logger.warning(
                f"Received error {e} when trying to retrieve {git_path_url} content from Github, retrying"
            )
            try:
                return cls.read_from_http_request(
                    git_path_url,
                    params=frozenset({"token": github_token}.items()),
                    timeout=timeout,
                )
            except FileReadError:
                logger.exception(
                    f"Could not retrieve the content of {git_path_url} file from Github"
                )
                raise

    @classmethod
    def read_from_gitlab_api(
        cls,
        path: str,
        git_content_config: Optional[GitContentConfig] = None,
        tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
        verify_ssl: bool = True,
    ) -> Any:
        """
        Reads a file from Gitlab api.

        Args:
            path: the path to the file in gitlab
            git_content_config: git content config object
            tag: the branch/sha to take the file from within Gitlab
            handler: whether a custom handler is required, if not takes the default.
            clear_cache: whether to clear cache
            verify_ssl: whether SSL should be verified

        Returns:
            Any: the file content in the desired format
        """
        if not git_content_config:
            git_content_config = GitContentConfig()

        git_path_url = urljoin(
            git_content_config.base_api, "files", urllib.parse.quote_plus(path), "raw"
        )
        gitlab_token = git_content_config.CREDENTIALS.gitlab_token

        return cls.read_from_http_request(
            git_path_url,
            headers=frozenset({"PRIVATE-TOKEN": gitlab_token}.items()),
            params=frozenset({"ref": tag}.items()),
            handler=handler,
            clear_cache=clear_cache,
            verify=verify_ssl,
        )

    @classmethod
    @retry(times=5, exceptions=(Timeout, ConnectionError))
    @lru_cache
    def read_from_http_request(
        cls,
        url: str,
        headers: Optional[frozenset] = None,
        params: Optional[frozenset] = None,
        verify: bool = True,
        timeout: Optional[int] = None,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ) -> Any:
        """
        Reads a file from any api via http request.

        Args:
            url: the utl to the file
            headers: request headers
            params: request params
            verify: whether SSL should be verified
            timeout: timeout for the request
            handler: whether a custom handler is required, if not takes the default.
            clear_cache: whether to clear cache

        Returns:
            Any: the file content in the desired format

        """
        if cls is File:
            raise ValueError(
                "when reading from file content please specify concrete class"
            )
        if clear_cache:
            cls.read_from_http_request.cache_clear()
        try:
            response = requests.get(
                url,
                params={key: value for key, value in params} if params else None,
                verify=verify,
                timeout=timeout,
                headers={key: value for key, value in headers} if headers else None,
            )
            response.raise_for_status()
        except RequestException as e:
            logger.exception(f"Could not retrieve file from {url}")
            raise HttpFileReadError(url, exc=e)

        try:
            return cls.read_from_file_content(response.content, handler=handler)
        except FileContentReadError as e:
            logger.exception(f"Could not read file from {url} as {cls.__name__} file")
            raise HttpFileReadError(url, exc=e)

    @classmethod
    def write_file(
        cls,
        data: Any,
        output_path: Union[Path, str],
        encoding: Optional[str] = None,
        handler: Optional[XSOAR_Handler] = None,
        **kwargs,
    ):
        """
        Writes a file into to the local file system.

        Args:
            data: the data to write
            output_path: the output path to write to
            encoding: any custom encoding if needed
            handler: whether a custom handler is required, if not takes the default.

        """
        output_path = Path(output_path)

        if cls is File:
            raise ValueError("when writing file please specify concrete class")

        model_attributes: Dict[str, Any] = {}
        if handler:
            model_attributes["handler"] = handler

        # builds up the object without validations, when writing file, no need to init path and git_util
        model = cls.construct(**model_attributes)
        try:
            model.write(data, path=output_path, encoding=encoding, **kwargs)
        except Exception as e:
            logger.exception(f"Could not write {output_path} as {cls.__name__} file")
            raise FileWriteError(output_path, exc=e)

    @abstractmethod
    def _write(
        self, data: Any, path: Path, encoding: Optional[str] = None, **kwargs
    ) -> None:
        raise NotImplementedError(
            "__write must be implemented for each File concrete object"
        )

    def write(
        self, data: Any, path: Path, encoding: Optional[str] = None, **kwargs
    ) -> None:
        def _write_safe_unicode():
            self._write(data, path=path, **kwargs)

        if encoding:
            self._write(data, path=path, encoding=encoding, **kwargs)
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
