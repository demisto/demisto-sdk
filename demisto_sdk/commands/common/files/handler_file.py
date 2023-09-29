from abc import abstractmethod
from io import StringIO
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import Field, validator

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
)
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class HandlerFile(TextFile):

    handler: XSOAR_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    @abstractmethod
    def validate_handler(cls, v: Type[XSOAR_Handler]) -> Type[XSOAR_Handler]:
        raise NotImplementedError("validate_handler must be implemented")

    def read_local_file(self) -> Union[List, Dict]:
        return self.load(super().read_local_file())

    def read_git_file(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH, from_remote: bool = True
    ):
        return self.load(super().read_git_file(tag, from_remote=from_remote))

    def load(self, file_content: Union[StringIO, str]) -> Union[List, Dict]:
        if not isinstance(file_content, StringIO):
            file_content = StringIO(file_content)
        return self.handler.load(file_content)

    def write(self, data: Any, encoding: Optional[str] = None) -> None:
        with self.output_path.open(
            "w", encoding=encoding or self.default_encoding
        ) as output_file:
            self.handler.dump(data, output_file)
