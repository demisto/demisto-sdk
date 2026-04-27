"""Tests for CO (Connector) validators — CO100, CO112, and CO113."""

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectorField,
    FieldGroup,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_connector_object,
    create_integration_object,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO100_is_matching_integration_exist import (
    IsMatchingIntegrationExistValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO112_is_matching_license import (
    IsMatchingLicenseValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO113_is_mirroring_omitted import (
    IsMirroringOmittedValidator,
)

# ============================================================
# CO100 — IsMatchingIntegrationExistValidator
# ============================================================


class TestCO100IsMatchingIntegrationExist:
    """Tests for CO100 validator: every XSOAR handler must have a resolved integration."""

    def test_valid_handler_with_matched_integration(self):
        """
        Given: A connector whose XSOAR handler has related_integration set.
        When: CO100 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object()
        integration = create_integration_object()
        connector.handlers[0].related_integration = integration

        validator = IsMatchingIntegrationExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_with_unresolved_integration_id(self):
        """
        Given: A connector whose XSOAR handler has xsoar_integration_id but
               related_integration is None (integration not found in repo).
        When: CO100 runs.
        Then: A validation error is returned mentioning the integration ID.
        """
        connector = create_connector_object()
        assert connector.handlers[0].xsoar_integration_id == "TestIntegration"
        assert connector.handlers[0].related_integration is None

        validator = IsMatchingIntegrationExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "TestIntegration" in results[0].message
        assert "not found" in results[0].message

    def test_both_failure_cases_combined(self):
        """
        Given: A connector with two XSOAR handlers — one with an unresolved
               integration ID and one missing the ID entirely.
        When: CO100 runs.
        Then: A single ValidationResult is returned containing both issues.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-unresolved",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "NonExistent",
                        },
                    },
                },
                {
                    "id": "xsoar-no-label",
                    "triggering": {
                        "labels": None,
                    },
                },
            ]
        )

        validator = IsMatchingIntegrationExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "NonExistent" in msg
        assert "not found" in msg
        assert "missing xsoar-integration-id" in msg
        assert "xsoar-no-label" in msg

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A connector with a non-XSOAR handler (module != 'xsoar').
        When: CO100 runs.
        Then: No validation errors — non-XSOAR handlers are not checked.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "other-handler",
                    "metadata": {
                        "module": "other",
                        "ownership": {"team": "other-team"},
                    },
                    "triggering": {
                        "labels": None,
                    },
                },
            ]
        )
        assert len(connector.xsoar_handlers) == 0

        validator = IsMatchingIntegrationExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_multiple_connectors_independent_results(self):
        """
        Given: Two connectors — one valid (handler linked), one invalid (unresolved).
        When: CO100 runs on both.
        Then: Only the invalid connector produces a validation error.
        """
        valid_connector = create_connector_object(connector_id="valid-conn")
        integration = create_integration_object()
        valid_connector.handlers[0].related_integration = integration

        invalid_connector = create_connector_object(connector_id="invalid-conn")
        # related_integration is None by default

        validator = IsMatchingIntegrationExistValidator()
        results = validator.obtain_invalid_content_items(
            [valid_connector, invalid_connector]
        )

        assert len(results) == 1
        assert "invalid-conn" in results[0].message


# ============================================================
# CO112 — IsMatchingLicenseValidator
# ============================================================


class TestCO112IsMatchingLicense:
    """Tests for CO112 validator: capability license union must cover supportedModules."""

    def test_valid_license_coverage(self):
        """
        Given: Integration supportedModules=["xsiam"], capability required_license=["xsiam"].
        When: CO112 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam"]]
        )
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_missing_module_in_license(self):
        """
        Given: Integration supportedModules=["xsiam", "xsoar"],
               capability required_license=["xsiam"] only.
        When: CO112 runs.
        Then: Validation error — "xsoar" is not covered.
        """
        connector = create_connector_object()
        integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam", "xsoar"]]
        )
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "xsoar" in results[0].message

    def test_no_related_integration_skipped(self):
        """
        Given: Handler with related_integration=None.
        When: CO112 runs.
        Then: No errors — CO100 handles missing integrations.
        """
        connector = create_connector_object()
        assert connector.handlers[0].related_integration is None

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_empty_supported_modules_skipped(self):
        """
        Given: Integration with supportedModules=[] (empty).
        When: CO112 runs.
        Then: No errors — nothing to check.
        """
        connector = create_connector_object()
        integration = create_integration_object(paths=["supportedModules"], values=[[]])
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_no_capability_licenses_skipped(self):
        """
        Given: Capability with config=None (no required_license).
        When: CO112 runs.
        Then: No errors — empty handler_licenses triggers continue.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "test-capability",
                        "title": "Test",
                        "description": "No license",
                        "config": None,
                    }
                ]
            }
        )
        integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam"]]
        )
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_sub_capability_license_contributes(self):
        """
        Given: Capability has no required_license, but sub-capability has
               required_license=["xsiam"]. Integration supportedModules=["xsiam"].
        When: CO112 runs.
        Then: No errors — sub-capability license covers the module.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "test-capability",
                        "title": "Test",
                        "description": "Sub-cap test",
                        "config": None,
                        "sub_capabilities": [
                            {
                                "id": "sub-1",
                                "title": "Sub One",
                                "config": {"required_license": ["xsiam"]},
                            }
                        ],
                    }
                ]
            }
        )
        integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam"]]
        )
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_sub_capability_license_insufficient(self):
        """
        Given: Sub-capability required_license=["xsiam"],
               integration supportedModules=["xsiam", "xsoar"].
        When: CO112 runs.
        Then: Validation error — "xsoar" is not covered.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "test-capability",
                        "title": "Test",
                        "description": "Sub-cap insufficient",
                        "config": None,
                        "sub_capabilities": [
                            {
                                "id": "sub-1",
                                "title": "Sub One",
                                "config": {"required_license": ["xsiam"]},
                            }
                        ],
                    }
                ]
            }
        )
        integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam", "xsoar"]]
        )
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "xsoar" in results[0].message

    def test_capability_not_found_in_connector(self):
        """
        Given: Handler references capability "nonexistent" that doesn't exist
               in connector.capability_by_id.
        When: CO112 runs.
        Then: No errors — gracefully skipped.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "capabilities": [
                        {
                            "id": "nonexistent",
                            "auth_options": [{"id": "auth-1", "workloads": ["w1"]}],
                        }
                    ],
                }
            ]
        )
        integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam"]]
        )
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_multiple_handlers_independent_checks(self):
        """
        Given: Two XSOAR handlers — one with matching licenses, one with mismatch.
        When: CO112 runs.
        Then: Only the mismatched handler produces a validation error.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-good",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "GoodIntegration",
                        },
                    },
                },
                {
                    "id": "xsoar-bad",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "BadIntegration",
                        },
                    },
                },
            ]
        )
        good_integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam"]]
        )
        bad_integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam", "xsoar"]]
        )
        # Match by handler ID since directory order is non-deterministic
        for h in connector.handlers:
            if h.id == "xsoar-good":
                h.related_integration = good_integration
            elif h.id == "xsoar-bad":
                h.related_integration = bad_integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "xsoar-bad" in results[0].message
        assert "xsoar" in results[0].message

    def test_union_across_multiple_capabilities(self):
        """
        Given: Handler has 2 capabilities: cap-A required_license=["xsiam"],
               cap-B required_license=["xsoar"]. Integration supportedModules=["xsiam", "xsoar"].
        When: CO112 runs.
        Then: No errors — union of licenses covers both modules.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "cap-a",
                        "title": "Cap A",
                        "description": "First",
                        "config": {"required_license": ["xsiam"]},
                    },
                    {
                        "id": "cap-b",
                        "title": "Cap B",
                        "description": "Second",
                        "config": {"required_license": ["xsoar"]},
                    },
                ]
            },
            handlers=[
                {
                    "capabilities": [
                        {
                            "id": "cap-a",
                            "auth_options": [{"id": "auth-1", "workloads": ["w1"]}],
                        },
                        {
                            "id": "cap-b",
                            "auth_options": [{"id": "auth-2", "workloads": ["w2"]}],
                        },
                    ],
                }
            ],
        )
        integration = create_integration_object(
            paths=["supportedModules"], values=[["xsiam", "xsoar"]]
        )
        connector.handlers[0].related_integration = integration

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO113 — IsMirroringOmittedValidator
# ============================================================


class TestCO113IsMirroringOmitted:
    """Tests for CO113 validator: mirroring fields must not appear in capability configurations."""

    def test_no_mirroring_fields_passes(self):
        """
        Given: A default connector with no mirroring fields in capability configurations.
        When: CO113 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object()

        validator = IsMirroringOmittedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_mirroring_field_in_capability_config(self):
        """
        Given: A connector with 'mirror_direction' field in a capability's configurations.
        When: CO113 runs.
        Then: A validation error is returned mentioning the forbidden field.
        """
        connector = create_connector_object()
        # Inject a forbidden field into the first capability's configurations
        connector.capabilities[0].configurations = [
            FieldGroup(
                fields=[
                    ConnectorField(
                        id="mirror_direction",
                        title="Mirror Direction",
                        field_type="select",
                    ),
                ]
            )
        ]

        validator = IsMirroringOmittedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "mirror_direction" in results[0].message
        assert "test-capability" in results[0].message

    def test_multiple_mirroring_fields_all_reported(self):
        """
        Given: A connector with all 3 forbidden mirroring fields in capability configurations.
        When: CO113 runs.
        Then: A single validation error listing all 3 forbidden fields.
        """
        connector = create_connector_object()
        # Inject all three forbidden fields into the first capability's configurations
        connector.capabilities[0].configurations = [
            FieldGroup(
                fields=[
                    ConnectorField(
                        id="mirror_direction",
                        title="Mirror Direction",
                        field_type="select",
                    ),
                    ConnectorField(
                        id="close_incident",
                        title="Close Incident",
                        field_type="checkbox",
                    ),
                    ConnectorField(
                        id="close_out",
                        title="Close Out",
                        field_type="checkbox",
                    ),
                ]
            )
        ]

        validator = IsMirroringOmittedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "mirror_direction" in results[0].message
        assert "close_incident" in results[0].message
        assert "close_out" in results[0].message
