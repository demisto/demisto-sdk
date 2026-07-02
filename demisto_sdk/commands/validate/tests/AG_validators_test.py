from pathlib import Path

import pytest

from demisto_sdk.commands.content_graph.objects.agentix_action import (
    AgentixAction,
)
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.tests.test_tools import (
    create_agentix_action_object,
    create_agentix_agent_object,
    create_agentix_skill_object,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG100_is_forbidden_content_item import (
    IsForbiddenContentItemValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG101_is_correct_mp import (
    IsCorrectMPValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG105_is_valid_types import (
    IsTypeValid,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG106_is_action_name_valid import (
    IsActionNameValidValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG107_is_display_name_valid import (
    IsDisplayNameValidValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG108_is_valid_rgb_color import (
    IsValidColorValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG109_is_system_instructions_valid import (
    IsSystemInstructionsValidValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG111_is_skill_content_file_exists import (
    IsSkillContentFileExistsValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG112_is_skill_total_token_budget import (
    SKILL_TOKEN_LIMIT,
    IsSkillTotalTokenBudgetValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG114_is_skill_char_cleanliness import (
    IsSkillCharCleanlinessValidator,
)
from demisto_sdk.commands.validate.validators.AG_validators.AG115_is_skill_description_length import (
    DESCRIPTION_MAX_WORDS,
    DESCRIPTION_MIN_WORDS,
    IsSkillDescriptionLengthValidator,
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
            visibility="public",
            actionids=["test_action"],
            systeminstructions="Test system instructions",
            conversationstarters=["Test conversation starter"],
            autoenablenewactions=False,
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
            visibility="public",
            actionids=[""],
            systeminstructions="",
            conversationstarters=[""],
            autoenablenewactions=False,
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
            visibility="public",
            actionids=[""],
            systeminstructions="",
            conversationstarters=[""],
            autoenablenewactions=False,
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


def test_is_valid_color():
    """
    Given:
    - Two AgentixAgent items, one with a valid color and one with an invalid color.

    When:
    - Calling the IsValidColorValidator obtain_invalid_content_items function.

    Then:
    - Make sure one failure is returned for the invalid color and the error message is correct.
    """
    content_items = [
        create_agentix_agent_object(
            paths=["color", "name"],
            values=["#FF0000", "Valid Color Agent"],
        ),
        create_agentix_agent_object(
            paths=["color", "name"],
            values=["invalid_color", "Invalid Color Agent"],
        ),
        create_agentix_agent_object(
            paths=["color", "name"],
            values=["#12345G", "Invalid Hex Agent"],
        ),
        create_agentix_agent_object(
            paths=["color", "name"],
            values=["#FFF", "Short Hex Agent"],
        ),
    ]

    results = IsValidColorValidator().obtain_invalid_content_items(content_items)

    assert len(results) == 3
    error_messages = [result.message for result in results]
    assert (
        "The Agentix-agent 'Invalid Color Agent' color 'invalid_color' is not a valid RGB hex color.\n"
        "Please make sure that the color is a valid 6-digit hex color string, starting with '#'. For example: '#FFFFFF'."
    ) in error_messages
    assert (
        "The Agentix-agent 'Invalid Hex Agent' color '#12345G' is not a valid RGB hex color.\n"
        "Please make sure that the color is a valid 6-digit hex color string, starting with '#'. For example: '#FFFFFF'."
    ) in error_messages
    assert (
        "The Agentix-agent 'Short Hex Agent' color '#FFF' is not a valid RGB hex color.\n"
        "Please make sure that the color is a valid 6-digit hex color string, starting with '#'. For example: '#FFFFFF'."
    ) in error_messages


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
    valid_action = create_agentix_action_object(
        paths=["display", "args", "outputs"],
        values=[
            "ValidAction",
            [
                {
                    "name": "arg1",
                    "description": "arg1",
                    "type": "string",
                    "underlyingargname": "arg1",
                },
                {
                    "name": "arg2",
                    "description": "arg2",
                    "type": "boolean",
                    "underlyingargname": "arg2",
                },
            ],
            [
                {
                    "name": "output1",
                    "type": "json",
                    "description": "output1",
                    "underlyingoutputcontextpath": "output1",
                },
                {
                    "name": "output2",
                    "type": "number",
                    "description": "output2",
                    "underlyingoutputcontextpath": "output2",
                },
            ],
        ],
        action_name="valid_action",
    )

    # Invalid types for both args and outputs
    invalid_action = create_agentix_action_object(
        paths=["display", "args", "outputs"],
        values=[
            "InvalidAction",
            [
                {
                    "name": "arg_invalid",
                    "type": "InvalidType",
                    "description": "arg_invalid",
                    "underlyingargname": "arg_invalid",
                }
            ],
            [
                {
                    "name": "output_invalid",
                    "type": "Object",
                    "description": "output_invalid",
                    "underlyingoutputcontextpath": "output_invalid",
                }
            ],
        ],
        action_name="invalid_action",
    )

    # Mixed valid and invalid
    mixed_action = create_agentix_action_object(
        paths=["display", "args", "outputs"],
        values=[
            "MixedAction",
            [
                {
                    "name": "arg_ok",
                    "type": "number",
                    "description": "arg_ok",
                    "underlyingargname": "arg_ok",
                },
                {
                    "name": "arg_bad",
                    "type": "Blob",
                    "description": "arg_bad",
                    "underlyingargname": "arg_bad",
                },
            ],
            [
                {
                    "name": "output_ok",
                    "type": "string",
                    "description": "output_ok",
                    "underlyingoutputcontextpath": "output_ok",
                },
                {
                    "name": "output_bad",
                    "type": "Array",
                    "description": "output_bad",
                    "underlyingoutputcontextpath": "output_bad",
                },
            ],
        ],
        action_name="mixed_action",
    )

    content_items = [valid_action, invalid_action, mixed_action]

    results = IsTypeValid().obtain_invalid_content_items(content_items)

    # We expect 2 invalid results: invalid_action and mixed_action
    assert len(results) == 2
    # Validate first message content
    assert (
        "The following Agentix action 'InvalidAction' contains invalid types:\n"
        "Arguments with invalid types: arg_invalid. Possible argument types: unknown, keyValue, textArea, string, number, date, boolean.\nOutputs with invalid types: output_invalid. "
        "Possible output types: unknown, string, number, date, boolean, json."
    ) in results[0].message

    # Validate second message content
    assert (
        "The following Agentix action 'MixedAction' contains invalid types:\n"
        "Arguments with invalid types: arg_bad. Possible argument types: unknown, keyValue, textArea, string, number, date, boolean.\n"
        "Outputs with invalid types: output_bad. Possible output types: unknown, string, number, date, boolean, json."
    ) in results[1].message


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        # Case 1: All valid AgentixAction displays
        (
            [
                create_agentix_action_object(paths=["display"], values=["ValidName"]),
                create_agentix_action_object(paths=["display"], values=["Valid_Name"]),
                create_agentix_action_object(paths=["display"], values=["Valid-Name"]),
                create_agentix_action_object(paths=["display"], values=["Valid Name"]),
                create_agentix_action_object(paths=["display"], values=["A123"]),
                create_agentix_action_object(paths=["display"], values=["A_1-2 3"]),
            ],
            0,
        ),
        # Case 2: One invalid (starts with digit), one valid
        (
            [
                create_agentix_action_object(paths=["display"], values=["1Invalid"]),
                create_agentix_action_object(paths=["display"], values=["ValidName"]),
            ],
            1,
        ),
        # Case 3: Invalid (contains forbidden character)
        ([create_agentix_action_object(paths=["display"], values=["Invalid!"])], 1),
        # Case 4: Multiple invalid
        (
            [
                create_agentix_action_object(paths=["display"], values=["1Invalid"]),
                create_agentix_action_object(paths=["display"], values=["Invalid!"]),
                create_agentix_action_object(paths=["display"], values=["ValidName"]),
            ],
            2,
        ),
    ],
)
def test_IsDisplayNameValid_obtain_invalid_content_items(
    content_items, expected_number_of_failures
):
    """
    Given
    - AgentixAction content_items with various display values.
    When
    - Calling the IsDisplayNameValid.obtain_invalid_content_items function.
    Then
    - Make sure the right amount of failure return.
    """
    results = IsDisplayNameValidValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        # Case 1: All valid AgentixAction names
        (
            [
                create_agentix_action_object(paths=["name"], values=["ValidName"]),
                create_agentix_action_object(paths=["name"], values=["Valid_Name"]),
                create_agentix_action_object(paths=["name"], values=["A123"]),
            ],
            0,
        ),
        # Case 2: One invalid (contains space), one valid
        (
            [
                create_agentix_action_object(paths=["name"], values=["Invalid Name"]),
                create_agentix_action_object(paths=["name"], values=["ValidName"]),
            ],
            1,
        ),
        # Case 3: Invalid (contains forbidden character)
        ([create_agentix_action_object(paths=["name"], values=["Invalid!"])], 1),
    ],
)
def test_IsActionNameValid_obtain_invalid_content_items(
    content_items, expected_number_of_failures
):
    """
    Given
    - AgentixAction content_items with various name values.
    When
    - Calling the IsActionNameValidValidator.obtain_invalid_content_items function.
    Then
    - Make sure the right amount of failure return.
    """
    results = IsActionNameValidValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures


def test_is_valid_agent_visibility():
    """
    Given
    - Three AgentixAgent items with different visibility values.

    When
    - Calling the IsValidAgentVisibilityValidator obtain_invalid_content_items function.

    Then
    - Make sure only invalid visibility values are flagged.
    """
    from demisto_sdk.commands.validate.tests.test_tools import (
        create_agentix_agent_object,
    )
    from demisto_sdk.commands.validate.validators.AG_validators.AG104_is_valid_agent_visibility import (
        IsValidAgentVisibilityValidator,
    )

    # Valid visibility values
    valid_public_agent = create_agentix_agent_object(
        paths=["visibility"], values=["public"]
    )
    valid_private_agent = create_agentix_agent_object(
        paths=["visibility"], values=["private"]
    )

    # Invalid visibility value
    invalid_agent = create_agentix_agent_object(
        paths=["visibility"], values=["internal"]
    )

    content_items = [valid_public_agent, valid_private_agent, invalid_agent]

    results = IsValidAgentVisibilityValidator().obtain_invalid_content_items(
        content_items
    )

    assert len(results) == 1
    assert "internal" in results[0].message
    assert "public, private" in results[0].message


def test_is_system_instructions_valid():
    """
    Given
    - AgentixAgent items with various system instructions lengths and pack names.

    When
    - Calling the IsSystemInstructionsValidValidator obtain_invalid_content_items function.

    Then
    - Ensure that only the item with system instructions exceeding the limit and in 'AI Agents' pack is flagged.
    """
    limit = 65535
    long_instructions = "a" * (limit + 1)
    valid_instructions = "valid instructions"

    # Valid: Short instructions, correct pack
    valid_agent = create_agentix_agent_object(
        paths=["systeminstructions", "name"],
        values=[valid_instructions, "valid_agent"],
        pack_info={"name": "AI Agents"},
        agent_name="valid_agent",
    )

    # Invalid: Long instructions, correct pack
    invalid_agent = create_agentix_agent_object(
        paths=["systeminstructions", "name"],
        values=[long_instructions, "invalid_agent"],
        pack_info={"name": "AI Agents"},
        agent_name="invalid_agent",
    )

    # Ignored: No instructions
    ignored_agent_no_instructions = create_agentix_agent_object(
        paths=["systeminstructions", "name"],
        values=["", "ignored_agent_no_instructions"],
        pack_info={"name": "AI Agents"},
        agent_name="ignored_agent_no_instructions",
    )

    content_items = [
        valid_agent,
        invalid_agent,
        ignored_agent_no_instructions,
    ]

    results = IsSystemInstructionsValidValidator().obtain_invalid_content_items(
        content_items
    )

    assert len(results) == 1
    assert results[0].content_object.name == "invalid_agent"
    assert (
        f"The system instructions for Agentix Agent 'invalid_agent' exceed the maximum allowed size of {limit} bytes"
        in results[0].message
    )


# ---------------------------------------------------------------------------
# AgentixSkill validators (AG111, AG112, AG114, AG115) — edge cases.
#
# These exercise the new skill package layout where the body lives in
# ``<SkillName>_skill.md`` next to ``<SkillName>.yml``.
# ---------------------------------------------------------------------------


def test_AG111_skill_content_file_exists():
    """
    Given
    - One skill whose body file (<SkillName>_skill.md) exists.
    - One skill whose body file is missing.

    When
    - Calling IsSkillContentFileExistsValidator.obtain_invalid_content_items.

    Then
    - Only the skill with the missing body file is reported.
    """
    valid_skill = create_agentix_skill_object(
        skill_name="valid_skill", skill_content="Some skill body."
    )
    missing_body_skill = create_agentix_skill_object(skill_name="missing_body_skill")
    # Remove the body file *before* the validator accesses the cached
    # ``skill_content_file`` related-file (whose ``exist`` is computed lazily),
    # so the validator sees the file as missing. The body lives in
    # ``<SkillName>_skill.md`` next to the schema yml.
    skill_dir = missing_body_skill.path.parent
    (skill_dir / f"{skill_dir.name}_skill.md").unlink()

    results = IsSkillContentFileExistsValidator().obtain_invalid_content_items(
        [valid_skill, missing_body_skill]
    )

    assert len(results) == 1
    assert "missing its content file" in results[0].message
    assert "missing_body_skill_skill.md" in results[0].message


def test_AG112_skill_within_token_budget():
    """
    Given
    - A skill whose body is comfortably within the token budget.

    When
    - Calling IsSkillTotalTokenBudgetValidator.obtain_invalid_content_items.

    Then
    - No failures are returned.
    """
    skill = create_agentix_skill_object(
        skill_name="small_skill", skill_content="A short body."
    )

    results = IsSkillTotalTokenBudgetValidator().obtain_invalid_content_items([skill])

    assert results == []


def test_AG112_skill_exceeds_token_budget():
    """
    Given
    - A skill whose body exceeds the estimated token budget
      (~4 chars per token, so the body must exceed SKILL_TOKEN_LIMIT * 4 chars).

    When
    - Calling IsSkillTotalTokenBudgetValidator.obtain_invalid_content_items.

    Then
    - The oversized skill is reported.
    """
    oversized_body = "a" * (SKILL_TOKEN_LIMIT * 4 + 4)
    skill = create_agentix_skill_object(
        skill_name="big_skill", skill_content=oversized_body
    )

    results = IsSkillTotalTokenBudgetValidator().obtain_invalid_content_items([skill])

    assert len(results) == 1
    assert "is too large" in results[0].message


@pytest.mark.parametrize(
    "skill_content, description, expect_failure",
    [
        pytest.param(
            "Plain ASCII body with code `let x = 1;`.",
            "Plain ASCII description.",
            False,
            id="clean-ascii-passes",
        ),
        pytest.param(
            "This body has an emoji 🚀 in the prose.",
            "Plain ASCII description.",
            True,
            id="emoji-in-body-fails",
        ),
        pytest.param(
            "Plain ASCII body.",
            "Description with curly quote \u201cword\u201d.",
            True,
            id="non-ascii-in-description-fails",
        ),
        pytest.param(
            "Body with non-ascii only inside code: ```py\nx = '\u00e9'\n```",
            "Plain ASCII description.",
            False,
            id="non-ascii-inside-code-block-ignored",
        ),
    ],
)
def test_AG114_skill_char_cleanliness(
    skill_content: str, description: str, expect_failure: bool
):
    """
    Given
    - Skills with various ASCII / non-ASCII content in prose and code blocks.

    When
    - Calling IsSkillCharCleanlinessValidator.obtain_invalid_content_items.

    Then
    - Non-ASCII characters in prose are flagged, while those inside code blocks
      are ignored.
    """
    skill = create_agentix_skill_object(
        paths=["description"],
        values=[description],
        skill_name="cleanliness_skill",
        skill_content=skill_content,
    )

    results = IsSkillCharCleanlinessValidator().obtain_invalid_content_items([skill])

    assert bool(results) is expect_failure


@pytest.mark.parametrize(
    "description, expect_failure",
    [
        pytest.param(
            " ".join(["word"] * DESCRIPTION_MIN_WORDS),
            False,
            id="exactly-min-words-passes",
        ),
        pytest.param(
            " ".join(["word"] * DESCRIPTION_MAX_WORDS),
            False,
            id="exactly-max-words-passes",
        ),
        pytest.param(
            " ".join(["word"] * (DESCRIPTION_MIN_WORDS - 1)),
            True,
            id="below-min-words-fails",
        ),
        pytest.param(
            " ".join(["word"] * (DESCRIPTION_MAX_WORDS + 1)),
            True,
            id="above-max-words-fails",
        ),
        pytest.param("", True, id="empty-description-fails"),
    ],
)
def test_AG115_skill_description_length(description: str, expect_failure: bool):
    """
    Given
    - Skills with descriptions at the boundaries of the allowed word range.

    When
    - Calling IsSkillDescriptionLengthValidator.obtain_invalid_content_items.

    Then
    - Descriptions outside the [MIN, MAX] word range are flagged; boundaries pass.
    """
    skill = create_agentix_skill_object(
        paths=["description"],
        values=[description],
        skill_name="description_skill",
        skill_content="Body.",
    )

    results = IsSkillDescriptionLengthValidator().obtain_invalid_content_items([skill])

    assert bool(results) is expect_failure


def _ag116_build_action(pack, folder_name: str, action_id: str):
    action = pack.create_agentix_action(folder_name)
    action.create_default_agentix_action()
    action.set_data(**{"commonfields.id": action_id})
    return action


def _ag116_build_skill(pack, folder_name: str, skill_id: str, action_ids):
    body = " ".join(f"<action={action_id}>" for action_id in action_ids)
    skill = pack.create_agentix_skill(folder_name)
    skill.create_default_agentix_skill(
        name=folder_name,
        skill_id=skill_id,
        skill_content=f"Skill body. {body}",
    )
    return skill


def _ag116_build_agent(pack, folder_name: str, agent_id: str, skill_ids, action_ids):
    agent = pack.create_agentix_agent(folder_name)
    agent.create_default_agentix_agent(name=folder_name, agent_id=agent_id)
    agent.update({"skillids": list(skill_ids), "actionids": list(action_ids)})
    return agent


def test_AG116_agent_missing_skill_action_is_invalid(graph_repo):
    """
    Given
    - An agent registering a skill that depends on two actions, but the agent's
      'actionids' includes only one of them.

    When
    - Running the AG116 validation across the entire repository.

    Then
    - AG116 reports the agent as missing the second action dependency.
    """
    from demisto_sdk.commands.validate.validators.AG_validators.AG116_agent_includes_skill_action_dependencies_all_files import (
        IsAgentIncludesSkillActionDependenciesValidatorAllFiles,
    )
    from demisto_sdk.commands.validate.validators.base_validator import BaseValidator

    pack = graph_repo.create_pack("AgentPack")
    _ag116_build_action(pack, "ActionA", "action-a")
    _ag116_build_action(pack, "ActionB", "action-b")
    _ag116_build_skill(pack, "MySkill", "my-skill-id", ["action-a", "action-b"])
    _ag116_build_agent(
        pack,
        "MyAgent",
        "my-agent-id",
        skill_ids=["my-skill-id"],
        action_ids=["action-a"],  # missing 'action-b'
    )

    graph_interface = graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsAgentIncludesSkillActionDependenciesValidatorAllFiles().obtain_invalid_content_items(
        []
    )

    assert len(results) == 1
    assert "action-b" in results[0].message
    assert "action-a" not in results[0].message


def test_AG116_agent_includes_all_skill_actions_is_valid(graph_repo):
    """
    Given
    - An agent registering a skill that depends on two actions, and the agent's
      'actionids' includes both of them.

    When
    - Running the AG116 validation across the entire repository.

    Then
    - AG116 reports no problem for the agent.
    """
    from demisto_sdk.commands.validate.validators.AG_validators.AG116_agent_includes_skill_action_dependencies_all_files import (
        IsAgentIncludesSkillActionDependenciesValidatorAllFiles,
    )
    from demisto_sdk.commands.validate.validators.base_validator import BaseValidator

    pack = graph_repo.create_pack("AgentPack")
    _ag116_build_action(pack, "ActionA", "action-a")
    _ag116_build_action(pack, "ActionB", "action-b")
    _ag116_build_skill(pack, "MySkill", "my-skill-id", ["action-a", "action-b"])
    _ag116_build_agent(
        pack,
        "MyAgent",
        "my-agent-id",
        skill_ids=["my-skill-id"],
        action_ids=["action-a", "action-b"],
    )

    graph_interface = graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsAgentIncludesSkillActionDependenciesValidatorAllFiles().obtain_invalid_content_items(
        []
    )

    assert not results


def test_AG116_list_files_fetches_only_required_skills(graph_repo, mocker):
    """
    Given
    - Two agents each registering a different skill, but only one agent is passed
      to the (git/specific-files) list-files validation.

    When
    - Running the AG116 list-files validation on the single changed agent.

    Then
    - Only the skill registered by the validated agent is fetched from the graph
      (the other skill is not queried), and the missing action is reported.
    """
    from demisto_sdk.commands.content_graph.common import ContentType
    from demisto_sdk.commands.validate.validators.AG_validators.AG116_agent_includes_skill_action_dependencies_list_files import (
        IsAgentIncludesSkillActionDependenciesValidatorListFiles,
    )
    from demisto_sdk.commands.validate.validators.base_validator import BaseValidator

    pack = graph_repo.create_pack("AgentPack")
    _ag116_build_action(pack, "ActionA", "action-a")
    _ag116_build_action(pack, "ActionB", "action-b")
    _ag116_build_skill(pack, "SkillOne", "skill-one", ["action-a"])
    _ag116_build_skill(pack, "SkillTwo", "skill-two", ["action-b"])
    changed_agent = _ag116_build_agent(
        pack,
        "ChangedAgent",
        "changed-agent-id",
        skill_ids=["skill-one"],
        action_ids=[],  # missing 'action-a'
    )
    _ag116_build_agent(
        pack,
        "OtherAgent",
        "other-agent-id",
        skill_ids=["skill-two"],
        action_ids=["action-b"],
    )

    graph_interface = graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    search_spy = mocker.spy(graph_interface, "search")
    agent_object = changed_agent.get_graph_object(graph_interface)

    results = IsAgentIncludesSkillActionDependenciesValidatorListFiles().obtain_invalid_content_items(
        [agent_object]
    )

    assert len(results) == 1
    assert "action-a" in results[0].message

    skill_search_calls = [
        call
        for call in search_spy.call_args_list
        if call.kwargs.get("content_type") == ContentType.AGENTIX_SKILL
    ]
    assert skill_search_calls, "expected the validator to query the graph for skills"
    assert all(
        call.kwargs.get("object_id") == ["skill-one"] for call in skill_search_calls
    ), "expected only the validated agent's skill to be fetched"
