from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.AG_validators.AG100_is_forbidden_content_item import (
    IsForbiddenContentItemValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG101_is_correct_mp import (
    IsCorrectMPValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG104_is_correct_sm import (
    IsCorrectSMValidator,
)


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
            display="",
            path=Path("test.yml"),
            marketplaces=["xsoar"],
            name="test",
            fromversion="",
            toversion="",
            display_name="",
            deprecated=False,
            id="",
            node_id="",
        )
    ]
    expected_msg = (
        f"The items {ContentType.AGENTIX_AGENT} and {ContentType.AGENTIX_ACTION} and {ContentType.SCRIPT} with is_llm=True "
        f"should be stored in content-test-conf, not in Content"
    )
    results = IsForbiddenContentItemValidator().obtain_invalid_content_items(
        content_items
    )

    assert len(results) == 1
    assert results[0].message == expected_msg


def test_is_correct_marketplace():
    """
    Given
    - One valid and one invalid AgentixAgent items.
    - One valid and one invalid AgentixAction items.
    - Four valid and one invalid Script items.

    When
    - Calling the IsCorrectMPValidator obtain_invalid_content_items function.

    Then
    - Make sure 3 failures are returned and the error message contains the informative message.
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
            display_name="",
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
            display_name="",
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
            display_name="",
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
            display_name="",
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
        "The items AgentixAgent, AgentixAction and Script with isllm=true"
        " should be uploaded to platform only. Please specify only platform"
        " under marketplaces."
    )

def test_is_correct_supportedModules():
    """
    Given
    - Two invalid AgentixAgent items.
    - One valid and one invalid AgentixAction items.
    - Two valid and one invalid Script items.

    When
    - Calling the IsMarketplaceExistsValidator obtain_invalid_content_items function.

    Then
    - Make sure 4 failures are returned and the error message contains the informative message.
    """
    content_items = [
        AgentixAgent(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["platform"],
            name="test",
            fromversion="",
            toversion="",
            display_name="",
            deprecated=False,
            id="",
            node_id="",
            supportedModules=["X1"]
        ),
        AgentixAgent(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["platform"],
            name="test",
            fromversion="",
            toversion="",
            display_name="",
            deprecated=False,
            id="",
            node_id=""
        ),
        AgentixAction(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["platform"],
            name="test",
            fromversion="",
            toversion="",
            display_name="",
            deprecated=False,
            id="",
            node_id="",
            underlying_content_item_id="test",
            underlying_content_item_name="test",
            underlying_content_item_type="script",
            underlying_content_item_version=-1,
            agent_id="test",
            supportedModules=["X1", "agentix"]
        ),
        AgentixAction(
            color="red",
            description="",
            display="",
            path=Path("test.yml"),
            marketplaces=["platform"],
            name="test",
            fromversion="",
            toversion="",
            display_name="",
            deprecated=False,
            id="",
            node_id="",
            underlying_content_item_id="test",
            underlying_content_item_name="test",
            underlying_content_item_type="script",
            underlying_content_item_version=-1,
            agent_id="test",
            supportedModules=["agentix"]
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
            supportedModules=["agentix"]
        ),
        Script(
            is_llm=False,
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
            supportedModules=["X1", "agentix"]
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
            supportedModules=["X1", "agentix"]
        ),
    ]
    results = IsCorrectSMValidator().obtain_invalid_content_items(content_items)

    assert len(results) == 4
    assert results[0].message == (
        "The items AgentixAgent, AgentixAction and Script with isllm=true"
        " should be uploaded to agentix supported module only. "
        "Please specify only agentix under supportedModules."
    )
