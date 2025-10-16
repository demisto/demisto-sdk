from pathlib import Path

import pytest

from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.tests.test_tools import create_agentix_action_object
from demisto_sdk.commands.validate.validators.AG_validators.AG100_is_forbidden_content_item import (
    IsForbiddenContentItemValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG101_is_correct_mp import (
    IsCorrectMPValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG106_is_action_name_valid import IsActionNameValidValidator


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

@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        # Case 1: All valid AgentixAction names
        (
            [
                create_agentix_action_object(paths=["name"], values=["ValidName"]),
                create_agentix_action_object(paths=["name"], values=["Valid_Name"]),
                create_agentix_action_object(paths=["name"], values=["A123"]),
            ],
            0,
            [],
        ),
        # Case 2: One invalid (contains space), one valid
        (
            [
                create_agentix_action_object(paths=["name"], values=["Invalid Name"]),
                create_agentix_action_object(paths=["name"], values=["ValidName"]),
            ],
            1,
            [
                        "The following AgentixAction name value is invalid: Invalid Name.\n"
        "AgentixAction name value may contain only letters (uppercase or lowercase), digits, or underscores. "
        "Spaces and special characters are not allowed.",
            ],
        ),
        # Case 3: Invalid (contains forbidden character)
        (
            [create_agentix_action_object(paths=["name"], values=["Invalid!"])],
            1,
            [
                "The following AgentixAction name value is invalid: Invalid!.\n"
                "AgentixAction name value may contain only letters (uppercase or lowercase), digits, or underscores. "
                "Spaces and special characters are not allowed."
                ,
            ],
        ),
    ],
)
def test_IsDisplayNameValid_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    - AgentixAction content_items with various display values.
    When
    - Calling the IsDisplayNameValid.obtain_invalid_content_items function.
    Then
    - Make sure the right amount of failure return and that the error msg is correct.
    """
    results = IsActionNameValidValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )