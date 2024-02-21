from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import demisto_client

from demisto_sdk.commands.common.tools import write_dict
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseNode,
)

if TYPE_CHECKING:
    # avoid circular imports
    from demisto_sdk.commands.content_graph.objects.script import Script

from pydantic import BaseModel, Field

from demisto_sdk.commands.common.constants import MarketplaceVersions, RelatedFileType
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.integration_script import (
    Argument,
    IntegrationScript,
)


class Parameter(BaseModel):
    name: str
    type: int = 0
    additionalinfo: Optional[str] = None
    defaultvalue: Optional[Any] = None
    required: Optional[bool] = None
    display: Optional[str] = None
    section: Optional[str] = None
    advanced: Optional[bool] = None
    hidden: Optional[Any] = None
    options: Optional[List[str]] = None
    displaypassword: Optional[str] = None
    hiddenusername: Optional[bool] = None
    hiddenpassword: Optional[bool] = None
    fromlicense: Optional[str] = None


class Output(BaseModel):
    description: str = ""
    contentPath: Optional[str] = None
    contextPath: Optional[str] = None
    important: Optional[bool] = False
    importantDescription: Optional[str] = None
    type: Optional[str] = None


class Command(BaseNode, content_type=ContentType.COMMAND):  # type: ignore[call-arg]
    name: str

    # From HAS_COMMAND relationship
    args: List[Argument] = Field([], exclude=True)
    outputs: List[Output] = Field([], exclude=True)

    deprecated: bool = Field(False)
    description: Optional[str] = Field("")

    # missing attributes in DB
    node_id: str = Field("", exclude=True)
    object_id: str = Field("", alias="id", exclude=True)
    marketplaces: List[MarketplaceVersions] = Field([], exclude=True)

    @property
    def integrations(self) -> List["Integration"]:
        return [
            r.content_item_to  # type: ignore[misc]
            for r in self.relationships_data[RelationshipType.HAS_COMMAND]
            if r.content_item_to.database_id == r.source_id
        ]

    def dump(self, *args) -> None:
        raise NotImplementedError()


class Integration(IntegrationScript, content_type=ContentType.INTEGRATION):  # type: ignore[call-arg]
    is_fetch: bool = Field(False, alias="isfetch")
    is_fetch_events: bool = Field(False, alias="isfetchevents")
    is_fetch_assets: bool = False
    is_fetch_events_and_assets: bool = False
    is_feed: bool = False
    is_beta: bool = False
    is_mappable: bool = False
    long_running: bool = False
    category: str
    commands: List[Command] = []
    params: List[Parameter] = Field([], exclude=True)

    @property
    def imports(self) -> List["Script"]:
        return [
            r.content_item_to  # type: ignore[misc]
            for r in self.relationships_data[RelationshipType.IMPORTS]
            if r.content_item_to.database_id == r.target_id
        ]

    def set_commands(self):
        commands = [
            Command(
                # the related to has to be a command
                name=r.content_item_to.name,  # type: ignore[union-attr,attr-defined]
                marketplaces=self.marketplaces,
                deprecated=r.deprecated,
                description=r.description,
            )
            for r in self.relationships_data[RelationshipType.HAS_COMMAND]
        ]
        self.commands = commands

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        if self.unified_data:
            summary["name"] = self.unified_data.get("display")
        return summary

    def metadata_fields(self):
        return (
            super()
            .metadata_fields()
            .union(
                {
                    "category": True,
                    "commands": {
                        "__all__": {"name": True, "description": True}
                    },  # for all commands, keep the name and description
                    "is_fetch": True,
                    "is_fetch_events": True,
                }
            )
        )

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ) -> dict:
        data = super().prepare_for_upload(current_marketplace, **kwargs)

        if supported_native_images := self.get_supported_native_images(
            ignore_native_image=kwargs.get("ignore_native_image") or False,
        ):
            logger.debug(
                f"Adding the following native images {supported_native_images} to integration {self.object_id}"
            )
            data["script"]["nativeimage"] = supported_native_images

        return data

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.integration_upload

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        if "category" in _dict and path.suffix == ".yml":
            return True
        return False

    def save(self):
        super().save()
        data = self.data
        data["script"]["commands"] = self.get_yml_commands()
        data["configuration"] = self.get_yml_configurations(self.params)
        write_dict(self.path, data, indent=4)

    def get_yml_commands(self) -> List[Dict]:
        yml_commands = []
        for command in self.commands:
            yml_commands.append(
                {
                    "name": command.name,
                    "deprecated": command.deprecated,
                    "description": command.description,
                    "arguments": self.get_yml_args(command.args),
                    "outputs": self.get_yml_outputs(command.outputs),
                }
            )
        return yml_commands

    def get_yml_outputs(self, outputs: List[Output]) -> List[Dict]:
        """Generate a list of Output dict objects.

        Args:
            outputs (List[Output]): The list of Output objects to turn to dict.

        Returns:
            List[Dict]: The List of the Output objects as dict objects.
        """
        yml_outputs = []
        optional_output_fields = [
            "contentPath",
            "contextPath",
            "importantDescription",
            "type",
            "important",
        ]
        for output in outputs:
            yml_output: Dict[str, Any] = {"description": output.description}
            dictified_output = output.dict()
            for optional_output_field in optional_output_fields:
                if (
                    optional_output_field in dictified_output
                    and dictified_output[optional_output_field] is not None
                ):
                    yml_output[optional_output_field] = dictified_output[
                        optional_output_field
                    ]
            yml_outputs.append(yml_output)
        return yml_outputs

    def get_yml_configurations(self, params: List[Parameter]) -> List[Dict]:
        """Generate a list of Parameter dict objects.

        Args:
            params (List[Parameter]): The list of Parameter objects to turn to dict.

        Returns:
            List[Dict]: The List of the Parameter objects as dict objects.
        """
        optional_param_fields: List[str] = [
            "additionalinfo",
            "defaultvalue",
            "required",
            "display",
            "section",
            "advanced",
            "hidden",
            "options",
            "displaypassword",
            "hiddenusername",
            "hiddenpassword",
            "fromlicense",
        ]
        yml_params: List[Dict] = []
        for param in params:
            yml_param: Dict[str, Any] = {
                "name": param.name,
                "type": param.type,
            }
            dict_param = param.dict()
            for optional_param_field in optional_param_fields:
                if (
                    optional_param_field in dict_param
                    and dict_param[optional_param_field] is not None
                ):
                    yml_param[optional_param_field] = dict_param[optional_param_field]
            yml_params.append(yml_param)
        return yml_params

    def get_related_content(self) -> Dict[RelatedFileType, Dict]:
        related_content_files = super().get_related_content()
        related_content_files.update(
            {
                RelatedFileType.IMAGE: {
                    "path": [
                        str(self.path.parent / f"{self.path.parts[-2]}_image.png")
                    ],
                    "git_status": None,
                },
                RelatedFileType.DARK_SVG: {
                    "path": [
                        str(self.path.parent / f"{self.path.parts[-2]}_description.md")
                    ],
                    "git_status": None,
                },
                RelatedFileType.LIGHT_SVG: {
                    "path": [
                        str(self.path.parent / f"{self.path.parts[-2]}_light.svg")
                    ],
                    "git_status": None,
                },
                RelatedFileType.DESCRIPTION: {
                    "path": [str(self.path.parent / f"{self.path.parts[-2]}_dark.svg")],
                    "git_status": None,
                },
            }
        )
        return related_content_files

    @property
    def description_file(self) -> str:
        return self.get_related_text_file(RelatedFileType.DESCRIPTION)
