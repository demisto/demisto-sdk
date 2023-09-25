from abc import abstractmethod
from io import StringIO
from typing import Any, Dict, List, Type, Union

from pydantic import Field, validator

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
)
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class HandlerFile(File):

    handler: XSOAR_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    @abstractmethod
    def validate_handler(cls, v: Type[XSOAR_Handler]) -> Type[XSOAR_Handler]:
        raise NotImplementedError("validate_handler must be implemented")

    def read_local_file(self) -> Union[List, Dict]:
        return self.load(super().read_local_file())

    def read_local_file_git(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH
    ) -> Union[List, Dict]:
        return self.load(super().read_local_file_git(tag=tag))

    def read_origin_file_git(
        self, branch: str = DEMISTO_GIT_PRIMARY_BRANCH
    ) -> Union[List, Dict]:
        return self.load(super().read_origin_file_git(branch=branch))

    def load(self, file_content: Union[StringIO, str]) -> Union[List, Dict]:
        if not isinstance(file_content, StringIO):
            file_content = StringIO(file_content)
        return self.handler.load(file_content)

    def write(self, data: Any) -> None:
        with self.output_path.open("w", encoding=self.default_encoding) as output_file:
            self.handler.dump(data, output_file)
