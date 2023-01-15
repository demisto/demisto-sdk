from unittest.mock import patch

import pytest

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.hook_validations.wizard import WizardValidator

json = JSON_Handler()


def get_validator(current_file=None, old_file=None, file_path="Packs/exists"):
    with patch.object(StructureValidator, "__init__", lambda a, b: None):
        structure = StructureValidator("")
        structure.current_file = current_file
        structure.old_file = old_file
        structure.file_path = file_path
        structure.is_valid = True
        structure.prev_ver = "master"
        structure.branch_name = ""
        structure.quiet_bc = False
        structure.specific_validations = None
        validator = WizardValidator(structure)
        validator.current_file = current_file
    return validator


class TestWizardValidator:
    @pytest.mark.parametrize(
        "current_file,id_set,answer",
        [
            ({}, None, True),
            (
                {"dependency_packs": [{"packs": [{"name": "not_exists"}]}]},
                {"Packs": {"exists": {}}},
                False,
            ),
            (
                {"dependency_packs": [{"packs": [{"name": "exists"}]}]},
                {"Packs": {"exists": {}}},
                True,
            ),
            (
                {
                    "dependency_packs": [
                        {"packs": [{"name": "exists"}, {"name": "not_exists"}]}
                    ]
                },
                {"Packs": {"exists": {}}},
                False,
            ),
        ],
    )
    def test_are_dependency_packs_valid(self, current_file, id_set, answer):
        """
        Given
        - a valid wizard
        - an id_set describing packs
        When
        - Validating a wizard are_dependency_packs_valid
        Then
        - Return whether the wizard is valid
        """
        validator = get_validator(current_file)
        assert validator.are_dependency_packs_valid(id_set) is answer

    @pytest.mark.parametrize(
        "current_file,id_set,answer",
        [
            ({}, None, True),
            (
                {
                    "dependency_packs": [{"packs": [{"name": "not_exists"}]}],
                    "wizard": {"fetching_integrations": [{"name": "not_exists"}]},
                },
                {"integrations": [{"exists": {"pack": "exists"}}]},
                False,
            ),  # False - missing from id_set
            (
                {"wizard": {"fetching_integrations": [{"name": "not_exists"}]}},
                {
                    "integrations": [
                        {"exists": {"pack": "exists"}},
                        {"not_exists": {"pack": "not_exists"}},
                    ]
                },
                False,
            ),
            # False - missing from dependency_packs
            (
                {"wizard": {"fetching_integrations": [{"name": "exists"}]}},
                {"integrations": [{"exists": {"pack": "exists"}}]},
                True,
            ),
        ],
    )
    def test_are_integrations_in_dependency_packs(self, current_file, id_set, answer):
        """
        Given
        - a valid wizard
        - an id_set describing packs
        When
        - Validating a wizard are_dependency_packs_valid
        Then
        - Return whether the wizard is valid
        """
        validator = get_validator(current_file)
        assert validator.are_integrations_in_dependency_packs(id_set) is answer

    @pytest.mark.parametrize(
        "current_file,id_set,answer",
        [
            ({}, None, True),
            (
                {
                    "dependency_packs": [{"packs": [{"name": "not_exists"}]}],
                    "wizard": {"set_playbook": [{"name": "not_exists"}]},
                },
                {"playbooks": [{"exists": {"pack": "exists"}}]},
                False,
            ),  # False - missing from id_set
            (
                {"wizard": {"set_playbook": [{"name": "not_exists"}]}},
                {
                    "playbooks": [
                        {"exists": {"pack": "exists"}},
                        {"not_exists": {"pack": "not_exists"}},
                    ]
                },
                False,
            ),
            # False - missing from dependency_packs
            (
                {"wizard": {"set_playbook": [{"name": "exists"}]}},
                {"playbooks": [{"exists": {"pack": "exists"}}]},
                True,
            ),
        ],
    )
    def test_are_playbooks_in_dependency_packs(self, current_file, id_set, answer):
        validator = get_validator(current_file)
        assert validator.are_playbooks_in_dependency_packs(id_set) is answer

    @pytest.mark.parametrize(
        "current_file,answer",
        [
            ({}, True),
            (
                {
                    "wizard": {
                        "set_playbook": [
                            {"name": "exists", "link_to_integration": "exists"}
                        ],
                        "fetching_integrations": [
                            {"name": "exists"},
                            {"name": "exists2"},
                        ],
                    }
                },
                False,
            ),
            (
                {
                    "wizard": {
                        "set_playbook": [
                            {"name": "exists", "link_to_integration": "not_exists"}
                        ],
                        "fetching_integrations": [{"name": "exists"}],
                    }
                },
                False,
            ),
            (
                {
                    "wizard": {
                        "set_playbook": [
                            {"name": "exists", "link_to_integration": "exists"}
                        ],
                        "fetching_integrations": [{"name": "exists"}],
                    }
                },
                True,
            ),
            (
                {
                    "wizard": {
                        "set_playbook": [
                            {"name": "exists", "link_to_integration": None}
                        ],
                        "fetching_integrations": [{"name": "exists"}],
                    }
                },
                True,
            ),
        ],
    )
    def test_do_all_fetch_integrations_have_playbook(self, current_file, answer):
        validator = get_validator(current_file)
        assert validator.do_all_fetch_integrations_have_playbook() is answer
