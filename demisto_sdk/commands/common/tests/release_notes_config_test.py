from typing import Optional

import pytest

from demisto_sdk.commands.common.hook_validations.release_notes_config import (
    ReleaseNotesConfigValidator,
)


class TestReleaseNotesConfigValidator:
    HAS_CORRESPONDING_RN_FILE_INPUTS = [("Some RN text", True), (None, False)]

    @pytest.mark.parametrize("rn_text, expected", HAS_CORRESPONDING_RN_FILE_INPUTS)
    def test_has_corresponding_rn_file(
        self, pack, rn_text: Optional[str], expected: bool
    ):
        """
        Given:
        - Config file for RN.

        When:
        - Checking if config file is valid:
        Case a: Config file has corresponding RN file.
        Case b: Config file does not have corresponding RN file.

        Then: Ensure expected bool is returned:
        Case a: Ensure true is returned.
        Case b: Ensure false is returned.
        """
        if rn_text:
            with open(f"{pack.path}/ReleaseNotes/1_0_1.md", "w") as f:
                f.write(rn_text)
        rn_config_validator = ReleaseNotesConfigValidator(
            f"{pack.path}/ReleaseNotes/1_0_1.json"
        )
        assert rn_config_validator.has_corresponding_rn_file() == expected

    @pytest.mark.parametrize("rn_text, expected", HAS_CORRESPONDING_RN_FILE_INPUTS)
    def test_is_valid_file(self, pack, rn_text: Optional[str], expected: bool):
        """
        Given:
        - Config file for RN.

        When:
        - Checking if config file is valid:
        Case a: Config file has corresponding RN file.
        Case b: Config file does not have corresponding RN file.

        Then: Ensure expected bool is returned:
        Case a: Ensure true is returned.
        Case b: Ensure false is returned.
        """
        if rn_text:
            with open(f"{pack.path}/ReleaseNotes/1_0_1.md", "w") as f:
                f.write(rn_text)
        rn_config_validator = ReleaseNotesConfigValidator(
            f"{pack.path}/ReleaseNotes/1_0_1.json"
        )
        assert rn_config_validator.is_file_valid() == expected
