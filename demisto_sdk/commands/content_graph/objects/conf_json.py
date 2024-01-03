from typing import Dict, List, Optional, Set, Union

from more_itertools import always_iterable
from packaging.version import Version
from pydantic import BaseModel, Extra, Field, validator

from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Nodes,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
)


class StrictBaseModel(BaseModel):
    class Config:
        extra = Extra.forbid


class ConfJson(BaseContent, content_type=ContentType.CONF_JSON):
    fromversion: str

    def to_node(self):
        return Nodes(self.to_dict())

    @property
    def body(self) -> "ConfJSON":
        return ConfJSON.parse_file(self.path)  # TODO consider loading just once

    @property
    def relationships(self) -> Relationships:
        relationships = Relationships()

        class RelationshipDatum(BaseModel, frozen=True):
            content_type: ContentType
            content_id: str
            relationship_type: RelationshipType

        relationship_data: Set[RelationshipDatum] = set()  # prevents duplicates

        for content_type, ids, relationship_type in (
            (
                ContentType.INTEGRATION,
                (test.integrations for test in self.body.tests),
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.PLAYBOOK,
                (test.playbookID for test in self.body.tests),
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.SCRIPT,
                (test.scripts for test in self.body.tests),
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.INTEGRATION,
                filter(
                    lambda s: not s.startswith("_comment"),
                    self.body.skipped_integrations,
                ),
                RelationshipType.CONF_JSON_SKIPPED,
            ),
            (
                ContentType.TEST_PLAYBOOK,
                self.body.skipped_tests.keys(),
                RelationshipType.CONF_JSON_SKIPPED,
            ),
            (
                ContentType.PACK,
                self.body.nightly_packs,
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.INTEGRATION,
                self.body.unmockable_integrations,
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.INTEGRATION,
                self.body.parallel_integrations,
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.TEST_PLAYBOOK,
                self.body.private_tests,
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.TEST_PLAYBOOK,
                self.body.reputation_tests,
                RelationshipType.CONF_JSON_USES,
            ),
            (
                ContentType.TEST_PLAYBOOK,
                self.body.test_marketplacev2,
                RelationshipType.CONF_JSON_USES,
            ),
        ):
            for one_or_many_ids in filter(None, ids):
                for content_id in filter(  # type:ignore[var-annotated]
                    None, always_iterable(one_or_many_ids)
                ):
                    relationship_data.add(
                        RelationshipDatum(
                            content_type=content_type,
                            content_id=content_id,
                            relationship_type=relationship_type,
                        )
                    )

        for relationship_datum in relationship_data:
            relationships.add(
                relationship_datum.relationship_type,
                source_id=self.object_id,
                source_type=self.content_type,
                source_fromversion=self.fromversion,
                source_marketplaces=self.marketplaces,
                target=relationship_datum.content_id,
                target_type=relationship_datum.content_type,
                target_fromversion=self.fromversion,
            )
        return relationships


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
