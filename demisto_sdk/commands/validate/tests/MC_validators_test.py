import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_pack_object,
    create_playbook_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.MC_validators.MC100_source_in_managed_pack import (
    SourceInManagedPackValidator,
)
from demisto_sdk.commands.validate.validators.MC_validators.MC101_managed_pack_has_deployment_json import (
    DEPLOYMENT_JSON_FILENAME,
    ManagedPackHasDeploymentJsonValidator,
)


@pytest.mark.parametrize(
    "content_source, managed, pack_source, expected_result_len",
    [
        # Valid cases - should pass
        ("autonomous", True, "autonomous", 0),  # Managed pack with matching source
        ("partner", True, "partner", 0),  # Managed pack with matching source
        ("", False, "autonomous", 0),  # Non-managed pack, source doesn't matter
        ("wrong", False, "autonomous", 0),  # Non-managed pack, source doesn't matter
        # Invalid cases - should fail
        ("", True, "autonomous", 1),  # Managed pack, missing source on content item
        ("partner", True, "autonomous", 1),  # Managed pack, mismatched source
        ("autonomous", True, "partner", 1),  # Managed pack, mismatched source
    ],
)
def test_SourceInManagedPackValidator_integration(
    content_source, managed, pack_source, expected_result_len
):
    """
    Given:
        - Various combinations of integrations with different source values
          and pack metadata with different managed/source values.

    When:
        - Running SourceInManagedPackValidator.obtain_invalid_content_items.

    Then:
        - Content items in managed packs (managed: true) must have a source field
          that matches the source in pack_metadata.
        - Content items in non-managed packs can have any source value.
    """
    # Create pack with specified metadata
    pack_metadata = {"managed": managed, "source": pack_source}

    pack = create_pack_object(
        paths=list(pack_metadata.keys()), values=list(pack_metadata.values())
    )

    # Create integration with specified source
    integration = create_integration_object(
        paths=["source"],
        values=[content_source],
    )

    # Manually set the pack relationship
    integration.pack = pack

    # Run validation
    invalid_content_items = SourceInManagedPackValidator().obtain_invalid_content_items(
        [integration]
    )

    assert len(invalid_content_items) == expected_result_len


@pytest.mark.parametrize(
    "content_type_factory",
    [
        create_integration_object,
        create_script_object,
        create_playbook_object,
    ],
)
def test_SourceInManagedPackValidator_multiple_content_types(content_type_factory):
    """
    Given:
        - Different content types (Integration, Script, Playbook) in a managed pack
          without the correct source field.

    When:
        - Running SourceInManagedPackValidator.obtain_invalid_content_items.

    Then:
        - All content types should be validated for the source field.
    """
    # Create managed pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "autonomous"],
    )

    # Create content item without source
    content_item = content_type_factory(paths=[], values=[])
    content_item.pack = pack

    # Run validation
    validator = SourceInManagedPackValidator()
    invalid_items = validator.obtain_invalid_content_items([content_item])

    # Should be invalid (missing source)
    assert len(invalid_items) == 1


def test_SourceInManagedPackValidator_fix():
    """
    Given:
        - An integration in a managed pack (managed: true, source: 'autonomous')
          but without the correct source field.

    When:
        - Running the fix method.

    Then:
        - The integration's source should be set to match the pack metadata source.
    """
    # Create managed pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "autonomous"],
    )

    # Create integration without source
    integration = create_integration_object(paths=["source"], values=[""])
    integration.pack = pack

    # Verify it's invalid before fix
    validator = SourceInManagedPackValidator()
    invalid_items = validator.obtain_invalid_content_items([integration])
    assert len(invalid_items) == 1

    # Apply fix
    fix_result = validator.fix(integration)

    # Verify fix was applied
    assert "autonomous" in fix_result.message
    assert integration.source == "autonomous"

    # Verify it's now valid
    invalid_items_after_fix = validator.obtain_invalid_content_items([integration])
    assert len(invalid_items_after_fix) == 0


def test_SourceInManagedPackValidator_fix_mismatched_source():
    """
    Given:
        - A script in a managed pack with a mismatched source field.

    When:
        - Running the fix method.

    Then:
        - The script's source should be updated to match the pack metadata source.
    """
    # Create managed pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "partner"],
    )

    # Create script with wrong source
    script = create_script_object(paths=["source"], values=["autonomous"])
    script.pack = pack

    # Verify it's invalid before fix
    validator = SourceInManagedPackValidator()
    invalid_items = validator.obtain_invalid_content_items([script])
    assert len(invalid_items) == 1

    # Apply fix
    fix_result = validator.fix(script)

    # Verify fix was applied
    assert "partner" in fix_result.message
    assert script.source == "partner"

    # Verify it's now valid
    invalid_items_after_fix = validator.obtain_invalid_content_items([script])
    assert len(invalid_items_after_fix) == 0


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
