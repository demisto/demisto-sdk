from pathlib import Path

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
from demisto_sdk.commands.validate.validators.AG_validators.AG105_is_valid_types import (
    IsTypeValid,
)
from demisto_sdk.commands.content_graph.objects.agentix_action import (
    AgentixActionArgument,
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
            display_name="test",
            deprecated=False,
            id="",
            node_id="",
            supportedModules=["X1"],
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
            marketplaces=["platform"],
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
            supportedModules=["X1", "agentix"],
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
            display_name="test",
            deprecated=False,
            id="",
            node_id="",
            underlying_content_item_id="test",
            underlying_content_item_name="test",
            underlying_content_item_type="script",
            underlying_content_item_version=-1,
            agent_id="test",
            supportedModules=["agentix"],
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
            supportedModules=["agentix"],
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
            supportedModules=["X1", "agentix"],
        ),
        Script(
            is_llm=True,
            marketplaces=["xsoar", "platform"],
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
            supportedModules=["X1", "agentix"],
        ),
    ]
    results = IsCorrectSMValidator().obtain_invalid_content_items(content_items)

    assert len(results) == 4
    assert (
        "The following Agentix related content item 'test' should have only 'agentix' type supportedModules. Valid modules"
    ) in results[0].message


def test_is_type_valid():
    """
    Given
    - One AgentixAction with valid argument and output types.
    - One AgentixAction with invalid argument and output types.
    - One AgentixAction with mixed valid and invalid types.

    When
    - Calling the IsTypeValid obtain_invalid_content_items function.

    Then
    - Ensure that 2 validation failures are returned.
    - Make sure the error messages include the invalid argument and output names,
      and list the valid type options.
    """
    # Valid content item
    valid_action = AgentixAction(
        color="red",
        description="",
        display="",
        path=Path("test_valid.yml"),
        marketplaces=["platform"],
        name="valid_action",
        fromversion="",
        toversion="",
        display_name="ValidAction",
        deprecated=False,
        id="",
        node_id="",
        underlying_content_item_id="test",
        underlying_content_item_name="test",
        underlying_content_item_type="script",
        underlying_content_item_version=-1,
        agent_id="test",
        args=[
            AgentixActionArgument(name="arg1", type="string"),
            AgentixActionArgument(name="arg2", type="boolean"),
        ],
        outputs=[
            AgentixActionArgument(name="output1", type="json"),
            AgentixActionArgument(name="output2", type="number"),
        ],
    )

    # Invalid types for both args and outputs
    invalid_action = AgentixAction(
        color="red",
        description="",
        display="",
        path=Path("test_invalid.yml"),
        marketplaces=["platform"],
        name="invalid_action",
        fromversion="",
        toversion="",
        display_name="InvalidAction",
        deprecated=False,
        id="",
        node_id="",
        underlying_content_item_id="test",
        underlying_content_item_name="test",
        underlying_content_item_type="script",
        underlying_content_item_version=-1,
        agent_id="test",
        args=[
            AgentixActionArgument(name="arg_invalid", type="InvalidType"),
        ],
        outputs=[
            AgentixActionArgument(name="output_invalid", type="Object"),
        ],
    )

    # Mixed valid and invalid
    mixed_action = AgentixAction(
        color="red",
        description="",
        display="",
        path=Path("test_mixed.yml"),
        marketplaces=["platform"],
        name="mixed_action",
        fromversion="",
        toversion="",
        display_name="MixedAction",
        deprecated=False,
        id="",
        node_id="",
        underlying_content_item_id="test",
        underlying_content_item_name="test",
        underlying_content_item_type="script",
        underlying_content_item_version=-1,
        agent_id="test",
        args=[
            AgentixActionArgument(name="arg_ok", type="number"),
            AgentixActionArgument(name="arg_bad", type="Blob"),
        ],
        outputs=[
            AgentixActionArgument(name="output_ok", type="string"),
            AgentixActionArgument(name="output_bad", type="Array"),
        ],
    )

    content_items = [valid_action, invalid_action, mixed_action]

    results = IsTypeValid().obtain_invalid_content_items(content_items)

    # We expect 2 invalid results: invalid_action and mixed_action
    assert len(results) == 2

    # Validate first message content
    assert "invalid_action" in results[0].message
    assert "arg_invalid" in results[0].message
    assert "output_invalid" in results[0].message
    assert "Possible argument types" in results[0].message
    assert "Possible output types" in results[0].message

    # Validate second message content
    assert "mixed_action" in results[1].message
    assert "arg_bad" in results[1].message
    assert "output_bad" in results[1].message
