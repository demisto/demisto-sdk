from pathlib import Path

import pytest

from demisto_sdk.commands.prepare_content.agentix_markdown_unifier import (
    AGENTIX_SKILL_FILE_SUFFIX,
    AGENTIX_SKILL_TARGET_FIELD,
    AgentixMarkdownUnifier,
)


def test_unify_populates_target_field_from_markdown_file(tmp_path: Path):
    """
    Given
    - A package directory containing a '<SkillName>_skill.md' markdown file and a
      data dict.

    When
    - Calling AgentixMarkdownUnifier.unify with a target_field.

    Then
    - The data dict is returned with the target_field populated from the file
      content (stripped), and the original dict is not mutated.
    """
    package_path = tmp_path / "MySkill"
    package_path.mkdir()
    (package_path / f"{package_path.name}{AGENTIX_SKILL_FILE_SUFFIX}").write_text(
        "  skill body content\n", encoding="utf-8"
    )
    main_file = package_path / "MySkill.yml"
    data = {"id": "MySkill"}

    unified = AgentixMarkdownUnifier.unify(
        main_file,
        data,
        target_field=AGENTIX_SKILL_TARGET_FIELD,
        file_suffix=AGENTIX_SKILL_FILE_SUFFIX,
    )

    assert unified[AGENTIX_SKILL_TARGET_FIELD] == "skill body content"
    # Ensure the input dict was deep-copied, not mutated.
    assert AGENTIX_SKILL_TARGET_FIELD not in data


def test_unify_missing_markdown_file_leaves_target_field_unset(tmp_path: Path):
    """
    Given
    - A package directory without the expected markdown file.

    When
    - Calling AgentixMarkdownUnifier.unify with a target_field.

    Then
    - The returned dict equals the input data (target_field is not added).
    """
    package_path = tmp_path / "MySkill"
    package_path.mkdir()
    main_file = package_path / "MySkill.yml"
    data = {"id": "MySkill"}

    unified = AgentixMarkdownUnifier.unify(
        main_file,
        data,
        target_field=AGENTIX_SKILL_TARGET_FIELD,
        file_suffix=AGENTIX_SKILL_FILE_SUFFIX,
    )

    assert unified == data
    assert AGENTIX_SKILL_TARGET_FIELD not in unified


def test_unify_without_target_field_raises(tmp_path: Path):
    """
    Given
    - A valid package and data dict.

    When
    - Calling AgentixMarkdownUnifier.unify without providing target_field
      (now allowed by the signature for LSP compatibility with the base Unifier).

    Then
    - A ValueError is raised by the runtime guard.
    """
    main_file = tmp_path / "MySkill.yml"

    with pytest.raises(ValueError, match="target_field"):
        AgentixMarkdownUnifier.unify(
            main_file,
            {"id": "MySkill"},
            file_suffix=AGENTIX_SKILL_FILE_SUFFIX,
        )
