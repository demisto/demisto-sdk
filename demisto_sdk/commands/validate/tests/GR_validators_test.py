import pytest
import logging
from pathlib import Path
from TestSuite.repo import Repo
from demisto_sdk.commands.common.legacy_git_tools import git_path
import demisto_sdk.commands.content_graph.neo4j_service as neo4j_service
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.validate.validators.GR_validators import GR100_uses_items_not_in_market_place

from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place import \
    MarketplaceFieldsValidator

from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_relationship,
    mock_test_playbook,
)

from demisto_sdk.commands.common.constants import (
    GENERAL_DEFAULT_FROMVERSION,
    SKIP_PREPARE_SCRIPT_NAME,
    MarketplaceVersions,
)

from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)

MP_XSOAR = [MarketplaceVersions.XSOAR.value]
MP_V2 = [MarketplaceVersions.MarketplaceV2.value]
MP_XSOAR_AND_V2 = [
    MarketplaceVersions.XSOAR.value,
    MarketplaceVersions.MarketplaceV2.value,
]


def test_MarketplaceFieldsValidator_is_valid(mocker, graph_repo: Repo):
    """
    Given
    - A content repo
    When
    - running MarketplaceFieldsValidator is_valid function.
    Then
    - Validate the existence of invalid marketplaces usages.
    """

    # pack2 = graph_repo.create_pack()
    # pack2.set_data(marketplaces=MP_XSOAR)

    pack = graph_repo.create_pack()
    pack.set_data(marketplaces=MP_V2)

    test_integration_0 = pack.create_integration("test_integration_0")
    test_integration_0.set_data(marketplaces=MP_XSOAR)
    test_integration_0.set_commands(["command_1"])

    test_integration_1 = pack.create_integration("test_integration_1")
    test_integration_1.set_data(marketplaces=MP_V2)
    test_integration_1.set_commands(["command_2", "command_3"])
    pass
    net4j_content_graph_interface = graph_repo.create_graph()
    # create_content_graph(net4j_content_graph_interface)
    # pack_graph_object = pack.get_graph_object(interface=net4j_content_graph_interface)
    # integrations = pack_graph_object.content_items.integration
    # MarketplaceFieldsValidator.graph_interface = net4j_content_graph_interface
    # validator = MarketplaceFieldsValidator()
    # validator.is_valid([pack_graph_object] + pack_graph_object.content_items.integration)
    pass
    # results = MarketplaceFieldsValidator().is_valid([pack_graph_object])

    # command_1 = test_integration
    # command_1.set_data(marketplaces=MP_V2)

    # MarketplaceFieldsValidator.graph_interface = graph_repo.create_graph()
    # pack.create_script("script_1").
    # pack.create_integration("test_integration_1").set_data(marketplaces=MP_V2)
    # pack.create_integration("test_integration_2/").set_data(marketplaces=MP_XSOAR_AND_V2)


    # graph.create_relationships()
    pass
    # pack.set_data()
    # logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    #
    # validator = MarketplaceFieldsValidator()
    # create_content_graph(validator.graph)
    # pass
    # # MarketplaceFieldsValidator().is_valid()
    # #
    # # with GraphValidator(update_graph=False) as graph_validator:
    # #     create_content_graph(graph_validator.graph)
    # #     is_valid = graph_validator.validate_marketplaces_fields()
    # #ss
    # # assert not is_valid
    # # assert str_in_call_args_list(
    # #     logger_error.call_args_list,
    # #     "Content item 'SamplePlaybook' can be used in the 'xsoar, xpanse' marketplaces"
    # #     ", however it uses content items: 'SamplePlaybook2' which are not supported in"
    # #     " all of the marketplaces of 'SamplePlaybook'",
    # # )
