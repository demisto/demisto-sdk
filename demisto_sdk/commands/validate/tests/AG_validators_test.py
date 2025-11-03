from pathlib import Path

from TestSuite.repo import Repo
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.AG_validators import AG110_is_agentix_action_name_already_exists_valid
from demisto_sdk.commands.validate.validators.AG_validators.AG100_is_forbidden_content_item import (
    IsForbiddenContentItemValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG101_is_correct_mp import (
    IsCorrectMPValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG110_is_agentix_action_name_already_exists_valid import \
    IsAgentixActionNameAlreadyExistsValidator


def test_is_forbidden_content_item():
    """
    Given
    - One valid AgentixAgent item.

    When
    - Calling the IsForbiddenContentItemValidator obtain_invalid_content_items function.

    Then
    - Make sure one failure is returned and the error message contains the informative message.
    """

    content_items = [
        AgentixAgent(
            color="red",
            description="",
            display="display Name",
            path=Path("test.yml"),
            marketplaces=["platform"],
            name="test",
            fromversion="",
            toversion="",
            display_name="display Name",
            deprecated=False,
            id="",
            node_id="",
        )
    ]
    expected_msg = "The following Agentix related content item 'display Name' should not be uploaded through content repo, please move it to content-test-conf repo."
    results = IsForbiddenContentItemValidator().obtain_invalid_content_items(
        content_items
    )

    assert len(results) == 1
    assert results[0].message == expected_msg


def test_is_correct_marketplace():
    """
    Given
    - Two invalid AgentixAgent items.
    - Two invalid AgentixAction items.
    - Four valid and two invalid Script items.

    When
    - Calling the IsCorrectMPValidator obtain_invalid_content_items function.

    Then
    - Make sure 6 failures are returned and the error message contains the informative message.
    """
    content_items = [
        AgentixAgent(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["xsoar"],
            name="test",
            fromversion="",
            toversion="",
            display_name="test",
            deprecated=False,
            id="",
            node_id="",
        ),
        AgentixAgent(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["xsoar_saas"],
            name="test",
            fromversion="",
            toversion="",
            display_name="test",
            deprecated=False,
            id="",
            node_id="",
        ),
        AgentixAction(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["xsoar"],
            name="test",
            fromversion="",
            toversion="",
            display_name="test",
            deprecated=False,
            id="",
            node_id="",
            underlying_content_item_id="test",
            underlying_content_item_name="test",
            underlying_content_item_type="script",
            underlying_content_item_version=-1,
            agent_id="test",
        ),
        AgentixAction(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["xsoar_saas"],
            name="test",
            fromversion="",
            toversion="",
            display_name="test",
            deprecated=False,
            id="",
            node_id="",
            underlying_content_item_id="test",
            underlying_content_item_name="test",
            underlying_content_item_type="script",
            underlying_content_item_version=-1,
            agent_id="test",
        ),
        Script(
            is_llm=True,
            marketplaces=["xsoar_saas"],
            id="",
            script='print("hello world")',
            node_id="",
            path=Path("test.yml"),
            name="test1",
            fromversion="6.0.0",
            toversion="8.0.0",
            display_name="test",
            deprecated=False,
            type="python",
            tags=["test"],
            skip_prepare=[],
        ),
        Script(
            is_llm=False,
            marketplaces=["xsoar"],
            id="",
            script='print("hello world")',
            node_id="",
            path=Path("test.yml"),
            name="test1",
            fromversion="6.0.0",
            toversion="8.0.0",
            display_name="test",
            deprecated=False,
            type="python",
            tags=["test"],
            skip_prepare=[],
        ),
        Script(
            is_llm=True,
            marketplaces=["xsoar"],
            id="",
            script='print("hello world")',
            node_id="",
            path=Path("test.yml"),
            name="test1",
            fromversion="6.0.0",
            toversion="8.0.0",
            display_name="test",
            deprecated=False,
            type="python",
            tags=["test"],
            skip_prepare=[],
        ),
        Script(
            is_llm=True,
            marketplaces=["platform"],
            id="",
            script='print("hello world")',
            node_id="",
            path=Path("test.yml"),
            name="test1",
            fromversion="6.0.0",
            toversion="8.0.0",
            display_name="test",
            deprecated=False,
            type="python",
            tags=["test"],
            skip_prepare=[],
        ),
        Script(
            is_llm=False,
            marketplaces=["xsoar"],
            id="",
            script='print("hello world")',
            node_id="",
            path=Path("test.yml"),
            name="test1",
            fromversion="6.0.0",
            toversion="8.0.0",
            display_name="test",
            deprecated=False,
            type="python",
            tags=["test"],
            skip_prepare=[],
        ),
    ]
    results = IsCorrectMPValidator().obtain_invalid_content_items(content_items)

    assert len(results) == 6
    assert results[0].message == (
        "The following Agentix related content item 'test' should have only marketplace 'platform'."
    )


def test_IsAgentixActionNameAlreadyExistsValidator_obtain_invalid_content_items(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, with 1 agentix action in each, and 2 of them are with the same name
    When
        - running IsAgentixActionNameAlreadyExistsValidator obtain_invalid_content_items function, on one of the packs with the duplicate agentix action name.
    Then
        - Validate that we got the error messages for the duplicate name.
    """
    mocker.patch.object(
        AG110_is_agentix_action_name_already_exists_valid
        ,
        "CONTENT_PATH",
        new=graph_repo.path,
    )
    graph_repo.create_pack(name="pack1")
    graph_repo.create_pack(name="pack2")
    graph_repo.create_pack(name="pack3")
    graph_repo.packs[1].agentix_actions[0].set_agentix_action_name("test")
    graph_repo.packs[2].agentix_actions[0].set_agentix_action_name("test")

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = (
        IsAgentixActionNameAlreadyExistsValidator().obtain_invalid_content_items(
            [graph_repo.packs[0], graph_repo.packs[2]]
        )
    )

    assert len(results) == 1