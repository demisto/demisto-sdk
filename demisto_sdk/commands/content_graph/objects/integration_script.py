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


class Output(BaseModel):
    description: str = ""
    contentPath: Optional[str] = None
    contextPath: Optional[str] = None
    important: Optional[bool] = None
    importantDescription: Optional[str] = None
    type: Optional[str] = None


class IntegrationScript(ContentItem):
    type: str
    subtype: Optional[str]
    docker_image: DockerImage = DockerImage("")
    alt_docker_images: List[str] = []
    description: Optional[str] = Field("")
    is_unified: bool = Field(False, exclude=True)
    code: Optional[str] = Field(None, exclude=True)
    unified_data: dict = Field(None, exclude=True)
    version: Optional[int] = Field(0)

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

    def get_related_content(self) -> Dict[RelatedFileType, Dict]:
        related_content_files = super().get_related_content()
        suffix = (
            ".ps1" if self.is_powershell else ".js" if self.is_javascript else ".py"
        )
        related_content_files.update(
            {
                RelatedFileType.README: {
                    "path": [
                        str(self.path.parent / PACKS_README_FILE_NAME),
                        str(self.path).replace(".yml", f"_{PACKS_README_FILE_NAME}"),
                    ],
                    "git_status": None,
                },
                RelatedFileType.TEST_CODE: {
                    "path": [
                        str(self.path.parent / f"{self.path.parts[-2]}_test{suffix}")
                    ],
                    "git_status": None,
                },
                RelatedFileType.CODE: {
                    "path": [
                        str(self.path.parent / f"{self.path.parts[-2]}{suffix}"),
                        str(self.path),
                    ],
                    "git_status": None,
                },
            }
        )
        return related_content_files

    @property
    def readme(self) -> str:
        return self.get_related_text_file(RelatedFileType.README)

    def get_yml_args(self, args: List[Argument]) -> List[Dict]:
        yml_args = []
        for arg in args:
            yml_arg: Dict[str, Any] = {
                "description": arg.description or "",
                "name": arg.name,
            }
            if arg.default is not None:
                yml_arg["default"] = arg.default
            if arg.predefined is not None:
                yml_arg["predefined"] = arg.predefined
            if arg.defaultvalue is not None:
                yml_arg["defaultvalue"] = arg.defaultvalue
            if arg.hidden is not None:
                yml_arg["hidden"] = arg.hidden
            if arg.auto is not None:
                yml_arg["auto"] = arg.auto
            if arg.type is not None:
                yml_arg["type"] = arg.type
            if arg.isArray is not None:
                yml_arg["isArray"] = arg.isArray
            if arg.deprecated:
                yml_arg["deprecated"] = arg.deprecated
            if arg.secret is not None:
                yml_arg["secret"] = arg.secret
            if arg.required is not None:
                yml_arg["required"] = arg.required
            yml_args.append(yml_arg)
        return yml_args

    def get_yml_outputs(self, outputs: List[Output]) -> List[Dict]:
        yml_outputs = []
        for output in outputs:
            yml_output: Dict[str, Any] = {"description": output.description}
            if output.contentPath is not None:
                yml_output["contentPath"] = output.contentPath
            if output.contextPath is not None:
                yml_output["contextPath"] = output.contextPath
            if output.importantDescription is not None:
                yml_output["importantDescription"] = output.importantDescription
            if output.type is not None:
                yml_output["type"] = output.type
            if output.important is not None:
                yml_output["important"] = output.important
            yml_outputs.append(yml_output)
        return yml_outputs
