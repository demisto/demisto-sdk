import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
)
from demisto_sdk.commands.validate.validators.MC_validators.MC101_managed_pack_has_deployment_json import (
    DEPLOYMENT_JSON_FILENAME,
    ManagedPackHasDeploymentJsonValidator,
)


@pytest.mark.parametrize(
    "managed, has_deployment_json, expected_result_len",
    [
        # Valid cases - should pass
        (False, False, 0),  # Non-managed pack, no deployment.json required
        (False, True, 0),  # Non-managed pack, deployment.json present (irrelevant)
        (True, True, 0),  # Managed pack with deployment.json present
        # Invalid cases - should fail
        (True, False, 1),  # Managed pack missing deployment.json
    ],
)
def test_ManagedPackHasDeploymentJsonValidator(
    managed, has_deployment_json, expected_result_len
):
    """
    Given:
        - Various combinations of packs with different managed values
          and presence/absence of deployment.json.

    When:
        - Running ManagedPackHasDeploymentJsonValidator.obtain_invalid_content_items.

    Then:
        - Managed packs (managed: true) must have a deployment.json file.
        - Non-managed packs are always valid regardless of deployment.json presence.
    """
    pack = create_pack_object(
        paths=["managed"],
        values=[managed],
    )

    if has_deployment_json:
        (pack.path / DEPLOYMENT_JSON_FILENAME).write_text("{}")

    invalid_content_items = (
        ManagedPackHasDeploymentJsonValidator().obtain_invalid_content_items([pack])
    )

    assert len(invalid_content_items) == expected_result_len


def test_ManagedPackHasDeploymentJsonValidator_error_message():
    """
    Given:
        - A managed pack (managed: true) without a deployment.json file.

    When:
        - Running ManagedPackHasDeploymentJsonValidator.obtain_invalid_content_items.

    Then:
        - The validation result message should mention the missing deployment.json.
    """
    pack = create_pack_object(
        paths=["managed"],
        values=[True],
    )

    invalid_content_items = (
        ManagedPackHasDeploymentJsonValidator().obtain_invalid_content_items([pack])
    )

    assert len(invalid_content_items) == 1
    assert "deployment.json" in invalid_content_items[0].message
    assert "managed" in invalid_content_items[0].message
