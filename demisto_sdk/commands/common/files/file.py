import inspect
import shutil
import urllib.parse
from abc import ABC, abstractmethod
from functools import cached_property, lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Type, Union

import requests
from bs4.dammit import UnicodeDammit
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


class File(ABC):

    git_util = GitUtil.from_content_path()

    @property
    def path(self) -> Path:
        return getattr(self, "_path")

    @cached_property
    def file_content(self) -> bytes:
        return self.path.read_bytes()

    @property
    def normalized_suffix(self) -> str:
        if suffix := self.path.suffix.lower():
            return suffix[1:]
        return suffix

    @property
    def original_encoding(self) -> Optional[str]:
        return UnicodeDammit(self.file_content).original_encoding

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    def copy_file(self, destination_path: Union[Path, str]):
        shutil.copyfile(self.path, destination_path)

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
        path: Union[Path, str],
    ) -> Type["File"]:
        """
        Returns the correct file model

        Args:
            path: the file input path

        Returns:
            File: any subclass of the File model.
        """
        path = Path(path)

        if cls is File:
            file_class = cls.__file_factory(path)
        else:
            file_class = cls
        logger.debug(f"Using class {file_class} for file {path}")
        return file_class

    @classmethod
    def as_default(cls, **kwargs):
        return super().__new__(cls)

    @classmethod
    @lru_cache
    def read_from_file_content(
        cls,
        file_content: Union[bytes, BytesIO],
        encoding: Optional[str] = None,
        handler: Optional[XSOAR_Handler] = None,
    ) -> Any:
        """
        Read a file from its representation in bytes.

        Args:
            file_content: the file content in bytes / bytesIo
            encoding: any custom encoding if needed, relevant only for Text based files
            handler: whether a custom handler is required, if not takes the default, relevant only for json/yaml files


        Returns:
            Any: the file content in the desired format
        """
        instance = cls.as_default(encoding=encoding, handler=handler)

        try:
            instance.load(file_content)
        except LocalFileReadError as e:
            logger.error(f"Could not read file content as {cls.__name__} file")
            raise FileContentReadError(exc=e.original_exc)

    @classmethod
    def with_local_path(cls, path: Path, **kwargs):
        instance = cls.as_default()
        instance._path = path
        return instance

    @classmethod
    @lru_cache
    def read_from_local_path(
        cls,
        path: Union[Path, str],
        encoding: Optional[str] = None,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ) -> Any:
        """
        Reads a file from a local path in the file system.

        Args:
            path: the path of the file
            encoding: any custom encoding if needed
            handler: whether a custom handler is required, if not takes the default.
            clear_cache: whether to clear cache

        Returns:
            Any: the file content in the desired format
        """
        path = Path(path)

        if clear_cache:
            cls.read_from_local_path.cache_clear()

        if not path.is_absolute():
            logger.debug(
                f"path {path} is not absolute, trying to get full relative path from {cls.git_util.repo.working_dir}"
            )
            path = cls.git_util.repo.working_dir / path
            if not path.exists():
                raise FileNotFoundError(f"File {path} does not exist")

        return (
            cls._from_path(path)
            .with_local_path(path, encoding=encoding, handler=handler)
            .__read_local_file()
        )

    def __read_local_file(self):
        try:
            return self.load(self.file_content)
        except FileReadError:
            logger.error(
                f"Could not read file {self.path} as {self.__class__.__name__} file"
            )
            raise

    @classmethod
    @lru_cache
    def read_from_git_path(
        cls,
        path: Union[str, Path],
        tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
        encoding: Optional[str] = None,
        from_remote: bool = True,
        handler: Optional[XSOAR_Handler] = None,
        clear_cache: bool = False,
    ) -> Any:
        """
        Reads a file from a specific git sha/branch.

        Args:
            path: the path to the file
            tag: branch / sha of the desired commit
            encoding: any custom encoding if needed
            from_remote: whether it should be taken from remote branch/sha or local branch/sha
            handler: whether a custom handler is required, if not takes the default.
            clear_cache: whether to clear cache

        Returns:
            Any: the file content in the desired format
        """
        path = Path(path)

        if clear_cache:
            cls.read_from_git_path.cache_clear()

        if cls.git_util.is_file_exist_in_commit_or_branch(
            path, commit_or_branch=tag, from_remote=from_remote
        ):
            # when reading from git we need relative path from the repo root
            path = cls.git_util.path_from_git_root(path)
        else:
            raise FileNotFoundError(
                f"File {path} does not exist in commit/branch {tag}"
            )

        return (
            cls._from_path(path)
            .with_local_path(path, encoding=encoding, handler=handler)
            .__read_git_file(tag, from_remote)
        )

    def __read_git_file(self, tag: str, from_remote: bool = True) -> Any:
        try:
            return self.load(
                self.git_util.read_file_content(
                    self.path, commit_or_branch=tag, from_remote=from_remote
                )
            )
        except Exception as e:
            if from_remote:
                tag = f"{DEMISTO_GIT_UPSTREAM}:{tag}"
            logger.error(
                f"Could not read git file {self.path} from {tag} as {self.__class__.__name__} file"
            )
            raise GitFileReadError(
                self.path,
                tag=tag,
                exc=e,
            )

    @classmethod
    def read_from_github_api(
        cls,
        path: str,
        git_content_config: Optional[GitContentConfig] = None,
        encoding: Optional[str] = None,
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
            encoding: any custom encoding if needed
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
                encoding=encoding,
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
                logger.error(
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
        encoding: Optional[str] = None,
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
            encoding: any custom encoding if needed

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
            encoding=encoding,
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
        encoding: Optional[str] = None,
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
            encoding: any custom encoding if needed
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
            return cls.read_from_file_content(
                response.content, encoding=encoding, handler=handler
            )
        except FileContentReadError as e:
            logger.error(f"Could not read file from {url} as {cls.__name__} file")
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
            raise ValueError("when writing file specify concrete class")

        file_instance = cls.as_default(encoding=encoding, handler=handler)
        try:
            file_instance.__write(data, path=output_path, encoding=encoding, **kwargs)
        except Exception as e:
            logger.error(f"Could not write {output_path} as {cls.__name__} file")
            raise FileWriteError(output_path, exc=e)

    @abstractmethod
    def __write(self, data: Any, path: Path, **kwargs) -> None:
        raise NotImplementedError
