"""
NOTE: This is not a standard Content item. There's no model for it.
I's only used (at least at the time of writing these lines) in the validate_conf_json.py script
"""
import itertools
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Set, Union

from more_itertools import always_iterable
from packaging.version import Version
from pydantic import BaseModel, Extra, Field, validator

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.common import ContentType


class StrictBaseModel(BaseModel):
    class Config:
        extra = Extra.forbid


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
    marketplaces: Optional[MarketplaceVersions] = None

    @validator("fromversion", "toversion")
    def validate_version(cls, v):
        Version(v)


class ImageConfig(StrictBaseModel):
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

    @staticmethod
    def from_path(path: Path = CONF_PATH) -> "ConfJSON":
        return ConfJSON(**get_json(path))  # type:ignore[assignment]

    @property
    def linked_content_items(self) -> Dict[ContentType, Set[str]]:
        result: DefaultDict[ContentType, Set[str]] = defaultdict(set)

        for content_type, id_sources in (
            (
                ContentType.INTEGRATION,
                (
                    itertools.chain.from_iterable(
                        always_iterable(test.integrations) for test in self.tests
                    ),
                    self.unmockable_integrations.keys(),
                    self.parallel_integrations,
                    (
                        v
                        for v in self.skipped_integrations.keys()
                        if not v.startswith("_comment")
                    ),
                ),
            ),
            (
                ContentType.TEST_PLAYBOOK,
                (
                    (test.playbookID for test in self.tests),
                    # self.skipped_tests.keys(), # not collecting skipped tests as this section preserves for skip reasons.
                    self.private_tests,
                    self.reputation_tests,
                    self.test_marketplacev2,
                ),
            ),
            (
                ContentType.SCRIPT,
                (test.scripts for test in self.tests),
            ),
            (
                ContentType.PACK,
                (self.nightly_packs,),
            ),
        ):
            for id_source in id_sources:
                result[content_type].update(filter(None, (always_iterable(id_source))))
        return dict(result)
