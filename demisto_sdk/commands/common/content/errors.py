from abc import abstractmethod
from typing import Optional

from wcmatch.pathlib import Path


class ContentError(Exception):
    def __init__(
        self, obj: object, obj_path: Path, additional_info: Optional[str] = ""
    ):
        """Base class for exceptions in this module.

        Args:
            obj: Object reference.
            obj_path: Object path.
            additional_info: explanation of the error.
        """
        self.obj_type = obj.__class__
        self.obj_path = obj_path
        self.additional_info = additional_info

    @property
    @abstractmethod
    def msg(self) -> str:
        pass


class ContentInitializeError(ContentError):
    def __init__(
        self, obj: object, obj_path: Path, additional_info: Optional[str] = ""
    ):
        """Exception raised when an error occurred in object initialization"""
        super().__init__(obj, obj_path, additional_info)

    @property
    def msg(self) -> str:
        msg = f"Content object init error:\n\t- Object: {self.obj_type}\n\t- {self.obj_path}"
        if self.additional_info:
            msg += f"\n\t - Info: {self.additional_info}"

        return msg


class ContentDumpError(ContentError):
    def __init__(
        self, obj: object, obj_path: Path, additional_info: Optional[str] = ""
    ):
        """Exception raised when an error occurred in object dump"""
        super().__init__(obj, obj_path, additional_info)

    @property
    def msg(self) -> str:
        msg = f"Content object dump error:\n\t- Object: {self.obj_type}\n\t- {self.obj_path}"
        if self.additional_info:
            msg += f"\n\t - Info: {self.additional_info}"

        return msg


class ContentKeyError(ContentError):
    def __init__(
        self, obj: object, obj_path: Path, key: str, additional_info: Optional[str] = ""
    ):
        """Exception raised when an error occurred in accessing key of the object (YAML/JSON)"""
        super().__init__(obj, obj_path, additional_info)
        self.key = key

    @property
    def msg(self) -> str:
        msg = f"Content object key error:\n\t- Object: {self.obj_type}\n\t-{self.obj_path}\n\t- Key: {self.key}"
        if self.additional_info:
            msg += f"\n\t - Info: {self.additional_info}"

        return msg


class ContentSerializeError(ContentError):
    def __init__(
        self, obj: object, obj_path: Path, additional_info: Optional[str] = ""
    ):
        """Exception raised when an error occurred in object serialization"""
        super().__init__(obj, obj_path, additional_info)

    @property
    def msg(self) -> str:
        msg = f"Content object serialize error:\n\t- Object: {self.obj_type}\n\t- {self.obj_path}\n\t"
        if self.additional_info:
            msg += f"\n\t - Info: {self.additional_info}"

        return msg


class ContentFactoryError(ContentError):
    def __init__(
        self, obj: object, obj_path: Path, additional_info: Optional[str] = ""
    ):
        """Exception raised when an error occurred in content object factory"""
        super().__init__(obj, obj_path, additional_info)

    @property
    def msg(self) -> str:
        msg = f"Content Factory error:\n\t- Object: {self.obj_type}\n\t- {self.obj_path}\n\t"
        if self.additional_info:
            msg += f"\n\t - Info: {self.additional_info}"

        return msg
