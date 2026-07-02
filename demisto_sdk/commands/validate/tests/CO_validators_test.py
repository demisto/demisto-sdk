"""Tests for CO (Connector) validators - CO100."""

from demisto_sdk.commands.validate.tests.test_tools import (
    create_connector_object,
    create_integration_object,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO100_is_matching_integration_exist import (
    IsMatchingIntegrationExistValidator,
)

# ============================================================
# CO100 - IsMatchingIntegrationExistValidator
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
        Given: A connector with two XSOAR handlers - one with an unresolved
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
        Then: No validation errors - non-XSOAR handlers are not checked.
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
        Given: Two connectors - one valid (handler linked), one invalid (unresolved).
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
