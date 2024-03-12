from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import (
    NATIVE_IMAGE_FILE_NAME,
    Auto,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.common.docker_helper import (
    get_python_version,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
)
from demisto_sdk.commands.content_graph.common import lazy_property
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.parsers.related_files import (
    CodeRelatedFile,
    ReadmeRelatedFile,
    TestCodeRelatedFile,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


class Argument(BaseModel):
    name: str
    description: str = ""
    required: Optional[bool] = None
    default: Optional[bool] = None
    predefined: Optional[List[str]] = None
    isArray: Optional[bool] = None
    defaultvalue: Optional[Any] = None
    secret: Optional[bool] = None
    deprecated: Optional[bool] = False
    type: Optional[str] = None
    hidden: Optional[bool] = False
    auto: Optional[Auto] = None

    @property
    def to_raw_dict(self) -> Dict:
        """Generate a Dict representation of the Argument object.

        Returns:
            Dict: The Dict representation of the Argument object.
        """
        dictified_arg = self.dict(exclude_none=True)
        if "auto" in dictified_arg:
            dictified_arg["auto"] = str(dictified_arg["auto"])
        return dictified_arg


class IntegrationScript(ContentItem):
    type: str
    subtype: Optional[str]
    docker_image: DockerImage = DockerImage("")
    alt_docker_images: List[str] = []
    description: Optional[str] = Field("")
    is_unified: bool = Field(False, exclude=True)
    code: Optional[str] = Field(None, exclude=True)
    unified_data: dict = Field(None, exclude=True)
    version: Optional[int] = 0

    @lazy_property
    def python_version(self) -> Optional[str]:
        """
        Get the python version from the script/integration docker-image in case it's a python image
        """
        if self.type == "python" and (
            python_version := get_python_version(self.docker_image)
        ):
            return str(python_version)

        return None

    @property
    def docker_images(self) -> List[str]:
        return [self.docker_image] + self.alt_docker_images if self.docker_image else []

    @property
    def is_powershell(self) -> bool:
        return self.type == "powershell"

    @property
    def is_javascript(self) -> bool:
        return self.type == "javascript"

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        data = (
            self.data
            if kwargs.get("unify_only")
            else super().prepare_for_upload(current_marketplace)
        )
        data = IntegrationScriptUnifier.unify(
            self.path, data, current_marketplace, **kwargs
        )
        self.unified_data = data
        return data

    def get_supported_native_images(
        self, ignore_native_image: bool = False
    ) -> List[str]:
        if not ignore_native_image:
            if not Path(f"Tests/{NATIVE_IMAGE_FILE_NAME}").exists():
                logger.debug(f"The {NATIVE_IMAGE_FILE_NAME} file could not be found.")
                return []
            return ScriptIntegrationSupportedNativeImages(
                _id=self.object_id,
                docker_image=self.docker_image,
                native_image_config=NativeImageConfig.get_instance(),
            ).get_supported_native_image_versions(get_raw_version=True)
        return []

    @cached_property
    def code_file(self) -> CodeRelatedFile:
        suffix = (
            ".ps1" if self.is_powershell else ".js" if self.is_javascript else ".py"
        )
        return CodeRelatedFile(self.path, suffix=suffix, git_sha=self.git_sha)

    @cached_property
    def test_code_file(self) -> TestCodeRelatedFile:
        suffix = (
            ".ps1" if self.is_powershell else ".js" if self.is_javascript else ".py"
        )
        return TestCodeRelatedFile(self.path, suffix=suffix, git_sha=self.git_sha)

    @cached_property
    def readme(self) -> ReadmeRelatedFile:
        return ReadmeRelatedFile(self.path, is_pack_readme=False, git_sha=self.git_sha)
