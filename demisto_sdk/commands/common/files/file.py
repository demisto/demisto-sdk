import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Set, Type, Union

from bs4.dammit import UnicodeDammit
from pydantic import BaseModel, validator

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
)
from demisto_sdk.commands.common.files.errors import (
    FileReadError,
    UnknownFileError,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler
from demisto_sdk.commands.common.logger import logger


class File(ABC, BaseModel):
    git_util: GitUtil
    input_path: Path
    output_path: Path
    default_encoding: str = "utf-8"  # default encoding is utf-8

    class Config:
        arbitrary_types_allowed = (
            True  # allows having custom classes for properties in model
        )

    @property
    def input_path_original_encoding(self) -> Optional[str]:
        return UnicodeDammit(self.input_path.read_bytes()).original_encoding

    @property
    def output_path_original_encoding(self) -> Optional[str]:
        return UnicodeDammit(self.output_path.read_bytes()).original_encoding

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

    def move_file(self, destination_path: Union[Path, str]):
        shutil.move(self.input_path, destination_path)
        self.__dict__[self.input_path] = destination_path

    @validator("input_path", always=True)
    def validate_input_path(cls, v: Path, values) -> Path:
        if v.is_absolute():
            return v
        else:
            logger.debug(f"File {v} does not exist, getting full relative path")

        git_util: GitUtil = values["git_util"]

        path = git_util.repo.working_dir / v
        if path.exists():
            return path

        raise FileNotFoundError(f"File {path} does not exist")

    @validator("output_path", always=True)
    def validate_output_path(cls, v: Path) -> Path:
        if v.suffix.lower() or v.name in cls.known_files():
            return v
        raise ValueError(
            f"output file {v} does not contain suffix, make sure to add file suffix"
        )

    @classmethod
    def file_factory(cls, path: Path) -> Type["File"]:
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
    def load(self, file_content: str) -> Any:
        raise NotImplementedError(
            "load must be implemented for each File concrete object"
        )

    @classmethod
    @lru_cache
    def from_path(
        cls,
        input_path: Optional[Union[Path, str]] = None,
        output_path: Optional[Union[Path, str]] = None,
        git_util: Optional[GitUtil] = None,
        **kwargs,
    ) -> "File":
        if input_path and output_path:
            input_path = Path(input_path)
            output_path = Path(output_path)
        elif input_path and not output_path:
            input_path = Path(input_path)
            output_path = Path(input_path)
        elif output_path and not input_path:
            input_path = Path(output_path)
            output_path = Path(output_path)
        else:
            raise ValueError("Either input_path or output_path must be provided")

        model_attributes: Dict[str, Any] = {
            "input_path": input_path,
            "output_path": output_path,
            "git_util": git_util,
        }

        model_attributes.update(kwargs)

        if cls is File:
            model = cls.file_factory(input_path or output_path).parse_obj(  # type: ignore[arg-type]
                model_attributes
            )
        else:
            model = cls.parse_obj(model_attributes)
        return model

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
        return self.input_path.read_bytes()

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
            return self.git_util.read_file_content(
                self.input_path, commit_or_branch=tag, from_remote=from_remote
            )
        except Exception as e:
            raise FileReadError(self.input_path, exc=e)

    @abstractmethod
    def _write(self, data: Any, encoding: Optional[str] = None) -> None:
        raise NotImplementedError(
            "write must be implemented for each File concrete object"
        )

    def write(self, data: Any, encoding: Optional[str] = None) -> None:
        def _write_safe_unicode():
            self._write(data)

        if encoding:
            self._write(data, encoding=encoding)
        else:
            try:
                _write_safe_unicode()
            except UnicodeDecodeError:
                if self.output_path_original_encoding == self.default_encoding:
                    logger.error(
                        f"{self.output_path} is encoded as unicode, cannot handle the error, raising it"
                    )
                    raise

                logger.debug(
                    f"deleting {self.output_path} - it will be rewritten as unicode (was {self.output_path_original_encoding})"
                )
                self.output_path.unlink()  # deletes the file
                logger.debug(f"rewriting {self.output_path} as unicode file")
                _write_safe_unicode()  # recreates the file
