from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import (
    NATIVE_IMAGE_FILE_NAME,
    PACKS_README_FILE_NAME,
    Auto,
    MarketplaceVersions,
    RelatedFileType,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.common.docker_helper import (
    get_python_version,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
)
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.common import lazy_property
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)


class Argument(BaseModel):
    name: str
    description: str
    required: Optional[bool] = False
    default: Optional[bool] = None
    predefined: Optional[List[str]] = None
    isArray: Optional[bool] = False
    defaultvalue: Optional[Any] = None
    secret: Optional[bool] = False
    deprecated: Optional[bool] = False
    type: Optional[str] = None
    hidden: Optional[bool] = False
    auto: Optional[Auto] = None


class IntegrationScript(ContentItem):
    type: str
    subtype: Optional[str]
    docker_image: DockerImage = DockerImage("")
    alt_docker_images: List[str] = []
    description: Optional[str] = Field("")
    is_unified: bool = Field(False, exclude=True)
    code: Optional[str] = Field(None, exclude=True)
    unified_data: dict = Field(None, exclude=True)
    file_type: RelatedFileType = RelatedFileType.YML

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

    @property
    def readme(self) -> str:
        return get_file(
            str(self.path.parent / PACKS_README_FILE_NAME),
            return_content=True,
            git_sha=self.git_sha,
        )

    def get_related_content(self) -> Dict[RelatedFileType, dict]:
        related_content_ls = super().get_related_content()
        suffix = (
            ".ps1" if self.is_powershell else ".js" if self.is_javascript else ".py"
        )
        related_content_ls.update(
            {
                RelatedFileType.README: {
                    "path": (
                        (self.path.parent / PACKS_README_FILE_NAME).relative_to(
                            CONTENT_PATH
                        ),
                        (
                            Path(
                                str(self.path).replace(
                                    ".yml", f"_{PACKS_README_FILE_NAME}"
                                )
                            )
                        ).relative_to(CONTENT_PATH),
                    ),
                    "git_status": None,
                },
                RelatedFileType.TEST_CODE: {
                    "path": (
                        self.path.parent / f"{self.path.parts[-2]}_test{suffix}"
                    ).relative_to(CONTENT_PATH),
                    "git_status": None,
                },
                RelatedFileType.CODE: {
                    "path": (
                        (
                            self.path.parent / f"{self.path.parts[-2]}{suffix}"
                        ).relative_to(CONTENT_PATH),
                        (self.path).relative_to(CONTENT_PATH),
                    ),
                    "git_status": None,
                },
            }
        )
        return related_content_ls
