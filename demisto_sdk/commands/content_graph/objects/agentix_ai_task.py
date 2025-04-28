from pathlib import Path
from typing import Set, List, Union

from pydantic import Field, DirectoryPath

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import write_dict
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_scripts_prepare import \
    MarketplaceIncidentToAlertScriptsPreparer


class AgentixAITask(IntegrationScript, content_type=ContentType.AGENTIX_AI_TASK):
    is_llm: bool = Field(..., alias="isLLM")
    pre_script: str = Field('', alias="preScript")
    post_script: str = Field('', alias="postScript")
    prompt: str = ''
    few_shots: str = Field('', alias="fewShots")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        pass

    def metadata_fields(self) -> Set[str]:
        return (
            super()
            .metadata_fields()
            .union(
                {
                    "tags",
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
                f"Adding the following native images {supported_native_images} to script {self.object_id}"
            )
            data["nativeimage"] = supported_native_images

        return data

    def dump(self, dir: DirectoryPath, marketplace: MarketplaceVersions) -> None:
        dir.mkdir(exist_ok=True, parents=True)
        data = self.prepare_for_upload(current_marketplace=marketplace)

        for data in MarketplaceIncidentToAlertScriptsPreparer.prepare(
            data, marketplace, self.is_incident_to_alert(marketplace)
        ):
            # Two scripts return from the preparation, one the original, and other the new script,
            # in order to normalize the name of the new script, make a copy of the original object
            # in case it is a new script with an update of the name and path.
            script_name = data.get("name")

            if script_name == self.name:  # the original script
                obj = self

            else:  # a modified script, replaced incidents->alerts
                obj = self.copy(
                    update={
                        "name": script_name,
                        "path": self.path.with_name(f"{script_name}.yml"),
                    }
                )
            try:
                write_dict(dir / obj.normalize_name, data=data, handler=obj.handler)

            except FileNotFoundError as e:
                logger.warning(f"Failed to dump {obj.path} to {dir}: {e}")
    #
    #
    # @classmethod
    # def _client_upload_method(cls, client: demisto_client) -> Callable:
    #     return client.import_script