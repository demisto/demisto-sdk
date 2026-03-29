from pathlib import Path

import pytest

from demisto_sdk.scripts.validate_content_path import (
    InvalidAgentixActionFileName,
    InvalidDepthOneFile,
    _validate,
)


class TestAgentixActionsPathValidation:
    """Tests for the AgentixActions path hierarchy validation.

    The new (valid) hierarchy is:
        Packs/<Pack>/AgentixActions/<ActionName>/<ActionName>.yml
        Packs/<Pack>/AgentixActions/<ActionName>/<ActionName>_test.yml

    The old (invalid) hierarchy is:
        Packs/<Pack>/AgentixActions/<ActionName>.yml
    """

    def test_old_hierarchy_depth_one_file_fails(self, tmp_path: Path):
        """
        Given:
            - A file directly under AgentixActions (old hierarchy).
        When:
            - Running _validate on the path.
        Then:
            - InvalidDepthOneFile is raised.
        """
        path = tmp_path / "Packs" / "Core" / "AgentixActions" / "CortexDummyAction.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

        with pytest.raises(InvalidDepthOneFile):
            _validate(path)

    def test_new_hierarchy_valid_action_file(self, tmp_path: Path):
        """
        Given:
            - A file in the new hierarchy: AgentixActions/<ActionName>/<ActionName>.yml
        When:
            - Running _validate on the path.
        Then:
            - No exception is raised (path is valid).
        """
        path = (
            tmp_path
            / "Packs"
            / "CommonScripts"
            / "AgentixActions"
            / "GetCaseExtraData"
            / "GetCaseExtraData.yml"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

        # Should not raise any exception
        _validate(path)

    def test_new_hierarchy_valid_test_file(self, tmp_path: Path):
        """
        Given:
            - A test file in the new hierarchy: AgentixActions/<ActionName>/<ActionName>_test.yml
        When:
            - Running _validate on the path.
        Then:
            - No exception is raised (path is valid).
        """
        path = (
            tmp_path
            / "Packs"
            / "CommonScripts"
            / "AgentixActions"
            / "GetCaseExtraData"
            / "GetCaseExtraData_test.yml"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

        # Should not raise any exception
        _validate(path)

    def test_new_hierarchy_mismatched_file_name_fails(self, tmp_path: Path):
        """
        Given:
            - A file in a subfolder under AgentixActions but with a name that doesn't match the parent folder.
        When:
            - Running _validate on the path.
        Then:
            - InvalidAgentixActionFileName is raised.
        """
        path = (
            tmp_path
            / "Packs"
            / "CommonScripts"
            / "AgentixActions"
            / "GetCaseExtraData"
            / "WrongName.yml"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

        with pytest.raises(InvalidAgentixActionFileName):
            _validate(path)

    def test_new_hierarchy_wrong_suffix_fails(self, tmp_path: Path):
        """
        Given:
            - A file in the new hierarchy with a .json suffix instead of .yml.
        When:
            - Running _validate on the path.
        Then:
            - InvalidAgentixActionFileName is raised.
        """
        path = (
            tmp_path
            / "Packs"
            / "CommonScripts"
            / "AgentixActions"
            / "GetCaseExtraData"
            / "GetCaseExtraData.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

        with pytest.raises(InvalidAgentixActionFileName):
            _validate(path)
