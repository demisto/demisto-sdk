from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.AG_validators.AG100_is_forbidden_content_item import (
    IsForbiddenContentItemValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG101_is_correct_mp import (
    IsMarketplaceExistsValidator,
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

    content_items = [AgentixAgent(color="red", description="", display="", path=Path("test.yml"),
                                  marketplaces=["xsoar"], name="test", fromversion="", toversion="",
                                  display_name="", deprecated=False, id="", node_id="")]
    expected_msg = (
        f"The items {ContentType.AGENTIX_AGENT} and {ContentType.AGENTIX_ACTION} "
        f"should be stored in content-test-conf, not in Content"
    )
    results = (
        IsForbiddenContentItemValidator().obtain_invalid_content_items(
            content_items
        )
    )

    assert len(results) == 1
    assert results[0].message == expected_msg


def test_is_marketplace_exists():
    """
    Given
    - One valid and one invalid AgentixAgent items.
    - One valid and one invalid AgentixAction items.
    - Two valid and one invalid Script items.

    When
    - Calling the IsMarketplaceExistsValidator obtain_invalid_content_items function.

    Then
    - Make sure 3 failures are returned and the error message contains the informative message.
    """
    content_items = [AgentixAgent(color="red", description="", display="", path=Path("test.yml"),
                                marketplaces=["xsoar"], name="test", fromversion="", toversion="",
                                display_name="", deprecated=False, id="", node_id=""),
                    AgentixAgent(color="red", description="", display="", path=Path("test.yml"),
                                marketplaces=["xsoar_saas"], name="test", fromversion="", toversion="",
                                display_name="", deprecated=False, id="", node_id=""),
                    AgentixAction(color="red", description="", display="", path=Path("test.yml"),
                                marketplaces=["xsoar"], name="test", fromversion="", toversion="",
                                display_name="", deprecated=False, id="", node_id="",
                                underlyingContentItemId="test", underlyingContentItemName="test",
                                underlyingcontentitemtype=1, underlyingContentItemVersion=-1, agent_id="test"),
                    AgentixAction(color="red", description="", display="", path=Path("test.yml"),
                                marketplaces=["xsoar_saas"], name="test", fromversion="", toversion="",
                                display_name="", deprecated=False, id="", node_id="",
                                underlyingContentItemId="test", underlyingContentItemName="test",
                                underlyingcontentitemtype=1, underlyingContentItemVersion=-1, agent_id="test"),
                    Script(is_llm=True, marketplaces=["xsoar_saas"], id="", script='print("hello world")',
                           node_id="", path=Path("test.yml"), name="test1", fromversion="6.0.0",
                           toversion="8.0.0", display_name="test", deprecated=False, type='python',
                           tags=['test'], skip_prepare=[]),
                    Script(is_llm=False, marketplaces=["xsoar"], id="", script='print("hello world")',
                           node_id="", path=Path("test.yml"), name="test1", fromversion="6.0.0",
                           toversion="8.0.0", display_name="test", deprecated=False, type='python',
                           tags=['test'], skip_prepare=[]),
                    Script(is_llm=True, marketplaces=["xsoar"], id="", script='print("hello world")',
                           node_id="", path=Path("test.yml"), name="test1", fromversion="6.0.0",
                           toversion="8.0.0", display_name="test", deprecated=False, type='python',
                           tags=['test'], skip_prepare=[])
                    ]
    results = (
        IsMarketplaceExistsValidator().obtain_invalid_content_items(
            content_items
        )
    )

    assert len(results) == 3
    assert results[0].message == ("The items AgentixAgent, AgentixAction and Script with isllm=true"
                                  " should be uploaded to xsoar_saas only. Please specify only xsoar_saas"
                                  " under marketplaces.")
