from pathlib import Path
from typing import Dict, List, Optional, Union

from packaging.version import Version
from pydantic import BaseModel, Extra, Field, validator

from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Nodes,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseNode


class StrictBaseModel(BaseModel):
    class Config:
        extra = Extra.forbid


class ConfJsonNode(BaseNode, content_type=ContentType.CONF_JSON):
    path: Path
    fromversion: str

    def to_node(self):
        return Nodes(self.to_dict())

    @property
    def body(self) -> "ConfJSON":
        return ConfJSON.parse_file(self.path)  # TODO consider loading just once

    @property
    def relationships(self) -> Relationships:
        result = Relationships()
        for skipped_integration in self.body.skipped_integrations:
            result.add(
                RelationshipType.USES_BY_ID,
                source_id=self.object_id,
                source_type=self.content_type,
                target=skipped_integration,
                target_type=ContentType.INTEGRATION,
            )
        return result


class DictWithSingleSimpleString(StrictBaseModel):
    simple: str


class ExternalPlaybookConfig(StrictBaseModel):
    playbookID: str
    input_parameters: Dict[str, DictWithSingleSimpleString]


class InstanceConfiguration(StrictBaseModel):
    classifier_id: str
    incoming_mapper_id: str


class Test(StrictBaseModel):
    playbookID: str
    integrations: Optional[Union[str, List[str]]] = None
    instance_names: Optional[Union[str, List[str]]] = None
    timeout: Optional[int] = None
    is_mockable: Optional[bool] = None
    memory_threshold: Optional[int] = None
    pid_threshold: Optional[int] = None
    has_api: Optional[bool] = None
    fromversion: Optional[str] = None
    toversion: Optional[str] = None
    nightly: Optional[bool] = None
    context_print_dt: Optional[str] = None
    scripts: Optional[Union[str, List[str]]]
    runnable_on_docker_only: Optional[bool] = None
    external_playbook_config: Optional[ExternalPlaybookConfig] = None
    instance_configuration: Optional[InstanceConfiguration] = None

    @validator("fromversion", "toversion")
    def validate_version(cls, v):
        Version(v)


class ImageConfig(StrictBaseModel):  # TODO use?
    memory_threshold: Optional[int] = None
    pid_threshold: Optional[int] = None


class DockerThresholds(StrictBaseModel):
    field_comment: str = Field(..., alias="_comment")
    images: Dict[str, ImageConfig]


class ConfJSON(StrictBaseModel):
    available_tests_fields: Dict[str, str]
    testTimeout: int
    testInterval: int
    tests: List[Test]
    skipped_tests: Dict[str, str]
    skipped_integrations: Dict[str, str]
    nightly_packs: List[str]
    unmockable_integrations: Dict[str, str]
    parallel_integrations: List[str]
    private_tests: List[str]
    docker_thresholds: DockerThresholds
    test_marketplacev2: List[str]
    reputation_tests: List[str]
    # self.relationships: Relationships = Relationships()
