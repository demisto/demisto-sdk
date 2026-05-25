"""Tests for CO (Connector) validators — CO100, CO101, CO109, CO110, CO111, CO112, CO113, CO114, CO116, CO117, CO119, CO123, and CO130."""

from typing import List, Optional
from unittest.mock import MagicMock

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectorField,
    FieldGroup,
    ResolvedParamMapping,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_connector_object,
    create_integration_object,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.CO_validators.CO100_is_matching_integration_exist import (
    IsMatchingIntegrationExistValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO101_is_matching_pack_exist import (
    IsMatchingPackExistValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO109_no_hidden_param_in_connector import (
    NoHiddenParamInConnectorValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO110_no_removed_connector_params import (
    NoRemovedConnectorParamsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO111_no_change_connector_ids import (
    NoChangeConnectorIdsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO112_is_matching_license import (
    IsMatchingLicenseValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO113_is_mirroring_omitted import (
    IsMirroringOmittedValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO114_is_handler_ownership_fields_align import (
    IsHandlerOwnershipFieldsAlignValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO116_is_connector_matches_integration_flags import (
    CAPABILITY_FLAG_REQUIREMENTS,
    INTEGRATION_TO_LONGRUNNING_CAPABILITY,
    IsConnectorMatchesIntegrationFlagsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO117_no_orphaned_handler_capability_ids import (
    NoOrphanedHandlerCapabilityIdsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO119_is_capability_name_valid import (
    CANONICAL_CAPABILITY_IDS,
    IsCapabilityNameValidValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO123_is_connector_ownership_fields_align import (
    IsConnectorOwnershipFieldsAlignValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_every_integration_param_covered import (
    IsEveryIntegrationParamCoveredValidator,
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
# CO101 — IsMatchingPackExistValidator
# ============================================================


class TestCO101IsMatchingPackExist:
    """Tests for CO101 validator: every XSOAR handler must reference a pack
    that exists in the content graph."""

    @staticmethod
    def _set_graph(mocker, search_return):
        """Helper: install a mock graph_interface on BaseValidator.

        ``search_return`` is the value returned by ``graph.search(...)``.
        """
        mock_graph = MagicMock()
        mock_graph.search.return_value = search_return
        mocker.patch.object(BaseValidator, "graph_interface", mock_graph)
        return mock_graph

    def test_handler_with_existing_pack_passes(self, mocker):
        """
        Given: A connector whose XSOAR handler has xsoar_pack_id and the graph
               returns a matching pack.
        When: CO101 runs.
        Then: No validation errors are returned.
        """
        self._set_graph(mocker, search_return=[MagicMock()])
        connector = create_connector_object()
        assert connector.handlers[0].xsoar_pack_id == "TestPack"

        validator = IsMatchingPackExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_with_unresolved_pack_id_fails(self, mocker):
        """
        Given: A connector whose XSOAR handler has xsoar_pack_id but the graph
               returns no matching pack.
        When: CO101 runs.
        Then: A validation error is returned mentioning the pack ID.
        """
        self._set_graph(mocker, search_return=[])
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-unresolved",
                    "triggering": {
                        "labels": {
                            "xsoar-pack-id": "FakePack",
                        },
                    },
                },
            ]
        )

        validator = IsMatchingPackExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "FakePack" in results[0].message
        assert "not found" in results[0].message

    def test_handler_missing_pack_id_fails(self, mocker):
        """
        Given: A connector whose XSOAR handler has no xsoar_pack_id at all.
        When: CO101 runs.
        Then: A validation error is returned about the missing label.
        """
        self._set_graph(mocker, search_return=[MagicMock()])
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-no-pack",
                    "triggering": {
                        "labels": None,
                    },
                },
            ]
        )

        validator = IsMatchingPackExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "missing xsoar-pack-id" in results[0].message
        assert "xsoar-no-pack" in results[0].message

    def test_both_failure_cases_combined(self, mocker):
        """
        Given: A connector with two XSOAR handlers — one with an unresolved
               pack ID and one missing the pack ID entirely.
        When: CO101 runs.
        Then: A single ValidationResult is returned containing both issues.
        """
        self._set_graph(mocker, search_return=[])
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-unresolved",
                    "triggering": {
                        "labels": {
                            "xsoar-pack-id": "FakePack",
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

        validator = IsMatchingPackExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "FakePack" in msg
        assert "not found" in msg
        assert "missing xsoar-pack-id" in msg
        assert "xsoar-no-label" in msg

    def test_non_xsoar_handler_ignored(self, mocker):
        """
        Given: A connector with a non-XSOAR handler (module != 'xsoar') that
               has neither a valid pack_id nor any pack_id.
        When: CO101 runs.
        Then: No validation errors — non-XSOAR handlers are skipped entirely.
        """
        self._set_graph(mocker, search_return=[])
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

        validator = IsMatchingPackExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_graph_unavailable_fails_as_missing(self, mocker):
        """
        Given: BaseValidator.graph_interface is None and an XSOAR handler
               declares an xsoar_pack_id.
        When: CO101 runs.
        Then: The pack is treated as missing -> "not found" failure.
        """
        mocker.patch.object(BaseValidator, "graph_interface", None)
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-no-graph",
                    "triggering": {
                        "labels": {
                            "xsoar-pack-id": "AnyPack",
                        },
                    },
                },
            ]
        )

        validator = IsMatchingPackExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "AnyPack" in results[0].message
        assert "not found" in results[0].message

    def test_multiple_connectors_independent_results(self, mocker):
        """
        Given: Two connectors — one valid (pack found), one invalid (no pack_id).
        When: CO101 runs on both.
        Then: Only the invalid connector produces a validation error.
        """
        self._set_graph(mocker, search_return=[MagicMock()])
        valid_connector = create_connector_object(connector_id="valid-conn")
        assert valid_connector.handlers[0].xsoar_pack_id == "TestPack"

        invalid_connector = create_connector_object(
            connector_id="invalid-conn",
            handlers=[
                {
                    "id": "xsoar-no-pack",
                    "triggering": {
                        "labels": None,
                    },
                },
            ],
        )

        validator = IsMatchingPackExistValidator()
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


# ============================================================
# CO114 — IsHandlerOwnershipFieldsAlignValidator
# ============================================================


class TestCO114IsHandlerOwnershipFieldsAlign:
    """Tests for CO114 validator: any handler with module='xsoar' must have a
    fully aligned metadata.ownership block (team='xsoar', maintainers contains
    '@xsoar-content', all exact case)."""

    def test_aligned_xsoar_handler_passes(self):
        """
        Given: A connector whose XSOAR handler has module='xsoar', team='xsoar',
               and maintainers containing '@xsoar-content'.
        When: CO114 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "aligned-handler",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@xsoar-content"],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_partner_handler_skipped(self):
        """
        Given: A connector whose handler is a partner handler (module='partner').
        When: CO114 runs.
        Then: The handler is skipped entirely — no validation errors.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "partner-handler",
                    "metadata": {
                        "module": "partner",
                        "ownership": {
                            "team": "partner-team",
                            "maintainers": ["@partner-dev"],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_module_case_mismatch_fails(self):
        """
        Given: A connector with a handler whose module is 'XSOAR' (uppercase).
        When: CO114 runs.
        Then: A validation error reports the module case-mismatch.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "module-upper",
                    "metadata": {
                        "module": "XSOAR",
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@xsoar-content"],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "module='XSOAR'" in msg
        assert "case mismatch" in msg

    def test_team_case_mismatch_fails(self):
        """
        Given: A connector with module='xsoar' but team='XSOAR' (uppercase).
        When: CO114 runs.
        Then: A validation error reports the team case-mismatch.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "team-upper",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "XSOAR",
                            "maintainers": ["@xsoar-content"],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "team='XSOAR'" in msg
        assert "case mismatch" in msg

    def test_team_completely_wrong_value_fails(self):
        """
        Given: A connector with module='xsoar' but team='partner'.
        When: CO114 runs.
        Then: A validation error reports the wrong team value (no case-mismatch
              wording — the value is genuinely wrong, not a casing issue).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "team-wrong",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "partner",
                            "maintainers": ["@xsoar-content"],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "team='partner'" in msg
        assert "must be exactly 'xsoar'" in msg
        assert "case mismatch" not in msg

    def test_missing_ownership_block_fails(self):
        """
        Given: A connector with module='xsoar' but the ownership block left
               at the Pydantic empty default (team='', maintainers=[]).
        When: CO114 runs.
        Then: A validation error reports the missing ownership block. The
              R3/R4 messages should NOT also be emitted (R2 supersedes).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "no-ownership",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "",
                            "maintainers": [],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "missing the metadata.ownership block" in msg
        # R3/R4 must NOT also fire when block is empty
        assert "team=''" not in msg
        assert "missing '@xsoar-content'" not in msg

    def test_missing_xsoar_content_maintainer_fails(self):
        """
        Given: A connector with module='xsoar', team='xsoar', but maintainers
               does not contain '@xsoar-content'.
        When: CO114 runs.
        Then: A validation error reports the missing maintainer (without a
              case-mismatch suffix — there's no case-insensitive match).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "missing-maintainer",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@dev1"],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "missing '@xsoar-content' in maintainers" in msg
        assert "['@dev1']" in msg
        assert "case mismatch" not in msg

    def test_maintainer_case_mismatch_fails(self):
        """
        Given: A connector with module='xsoar', team='xsoar', and maintainers
               containing '@XSOAR-Content' (case-insensitive match only).
        When: CO114 runs.
        Then: A validation error reports the missing maintainer WITH a
              case-mismatch suffix.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "maintainer-upper",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@XSOAR-Content"],
                        },
                    },
                },
            ]
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "missing '@xsoar-content' in maintainers" in msg
        assert "case mismatch detected, fix the case" in msg

    def test_multiple_handlers_with_multiple_issues(self):
        """
        Given: A connector with two xsoar-module handlers, each with different
               ownership issues (one with case-mismatched team + missing
               maintainer; one with missing ownership block entirely).
        When: CO114 runs.
        Then: A SINGLE ValidationResult is returned, listing both handlers
              and ALL their issues.
        """
        connector = create_connector_object(
            connector_id="cs-falcon",
            handlers=[
                {
                    "id": "detection-handler",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "XSOAR",
                            "maintainers": ["@dev1"],
                        },
                    },
                },
                {
                    "id": "event-handler",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "",
                            "maintainers": [],
                        },
                    },
                },
            ],
        )

        validator = IsHandlerOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "cs-falcon" in msg
        # First handler — both team case mismatch and missing maintainer
        assert "detection-handler" in msg
        assert "team='XSOAR'" in msg
        assert "case mismatch" in msg
        assert "missing '@xsoar-content'" in msg
        assert "['@dev1']" in msg
        # Second handler — missing ownership block
        assert "event-handler" in msg
        assert "missing the metadata.ownership block" in msg


# ============================================================
# CO123 — IsConnectorOwnershipFieldsAlignValidator
# ============================================================


# Reusable connector-level override: maintainers list with the @xsoar-content
# tag (required when the connector contains at least one XSOAR handler).
ALIGNED_CONNECTOR_OVERRIDES = {
    "metadata": {"ownership": {"maintainers": ["@xsoar-content"]}}
}

# Reusable handler config: a single fully-aligned xsoar handler
# (module='xsoar', team='xsoar', maintainers contains '@xsoar-content').
ALIGNED_XSOAR_HANDLER = {
    "id": "xsoar-handler",
    "metadata": {
        "module": "xsoar",
        "ownership": {
            "team": "xsoar",
            "maintainers": ["@xsoar-content"],
        },
    },
}


class TestCO123IsConnectorOwnershipFieldsAlign:
    """Tests for CO123 validator: a connector with at least one XSOAR handler
    must contain '@xsoar-content' in its connector-level
    metadata.ownership.maintainers field (exact, case-sensitive)."""

    def test_xsoar_handler_with_aligned_connector_maintainer_passes(self):
        """
        Given: A connector with one aligned XSOAR handler AND connector-level
               metadata.ownership.maintainers containing '@xsoar-content'.
        When:  CO123 runs.
        Then:  No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides=ALIGNED_CONNECTOR_OVERRIDES,
            handlers=[ALIGNED_XSOAR_HANDLER],
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_no_xsoar_handlers_skips_validation(self):
        """
        Given: A connector whose only handler is a partner handler (not XSOAR),
               and connector-level maintainers does NOT contain
               '@xsoar-content'.
        When:  CO123 runs.
        Then:  The connector is skipped entirely — no validation errors,
               because the trigger gate (at least one XSOAR handler) is not
               met.
        """
        # Default connector template uses maintainers=['@test'] (no
        # '@xsoar-content'), so we don't need to override that — just make
        # sure no handler is XSOAR.
        connector = create_connector_object(
            handlers=[
                {
                    "id": "partner-handler",
                    "metadata": {
                        "module": "partner",
                        "ownership": {
                            "team": "partner-team",
                            "maintainers": ["@partner-dev"],
                        },
                    },
                },
            ]
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_xsoar_handler_with_missing_connector_maintainer_fails(self):
        """
        Given: A connector with one aligned XSOAR handler BUT connector-level
               metadata.ownership.maintainers does NOT contain
               '@xsoar-content' (no case-insensitive variant either).
        When:  CO123 runs.
        Then:  A single validation error reports the missing tag and lists
               the offending xsoar handler id. The error message does NOT
               include the "case mismatch" hint.
        """
        connector = create_connector_object(
            connector_id="missing-maintainer-connector",
            connector_overrides={
                "metadata": {"ownership": {"maintainers": ["@some-other-team"]}}
            },
            handlers=[ALIGNED_XSOAR_HANDLER],
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "missing-maintainer-connector" in msg
        assert "missing '@xsoar-content'" in msg
        assert "'xsoar-handler'" in msg
        assert "['@some-other-team']" in msg
        assert "case mismatch" not in msg.lower()

    def test_xsoar_handler_with_case_mismatched_maintainer_fails(self):
        """
        Given: A connector with one aligned XSOAR handler BUT connector-level
               maintainers contains '@XSOAR-Content' (case-insensitive match
               only) — not the exact '@xsoar-content' tag.
        When:  CO123 runs.
        Then:  A validation error reports the missing tag WITH the
               "case mismatch detected, fix the case" hint.
        """
        connector = create_connector_object(
            connector_id="case-mismatch-connector",
            connector_overrides={
                "metadata": {"ownership": {"maintainers": ["@XSOAR-Content"]}}
            },
            handlers=[ALIGNED_XSOAR_HANDLER],
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "missing '@xsoar-content'" in msg
        assert "['@XSOAR-Content']" in msg
        assert "Case mismatch detected, fix the case." in msg

    def test_multiple_xsoar_handlers_single_error_lists_all_ids(self):
        """
        Given: A connector with TWO aligned XSOAR handlers and connector-level
               maintainers missing '@xsoar-content'.
        When:  CO123 runs.
        Then:  A SINGLE ValidationResult is returned (one per connector, NOT
               one per handler) that lists BOTH xsoar handler ids.
        """
        connector = create_connector_object(
            connector_id="multi-handler-connector",
            connector_overrides={"metadata": {"ownership": {"maintainers": ["@dev"]}}},
            handlers=[
                {
                    "id": "detection-handler",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@xsoar-content"],
                        },
                    },
                },
                {
                    "id": "event-handler",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@xsoar-content"],
                        },
                    },
                },
            ],
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "multi-handler-connector" in msg
        assert "'detection-handler'" in msg
        assert "'event-handler'" in msg

    def test_misaligned_xsoar_handlers_do_not_trigger_validation(self):
        """
        Given: A connector whose only 'xsoar-module' handler has team='XSOAR'
               (case mismatch) — meaning `HandlerData.is_xsoar` is False
               because the property requires team=='xsoar' (exact lowercase),
               AND connector-level maintainers is missing '@xsoar-content'.
        When:  CO123 runs.
        Then:  No validation errors — the trigger gate uses
               `connector.xsoar_handlers` which filters via is_xsoar, so a
               misaligned handler does NOT count. (CO114 handles those.)
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"ownership": {"maintainers": ["@dev"]}}},
            handlers=[
                {
                    "id": "misaligned-xsoar-handler",
                    "metadata": {
                        "module": "xsoar",
                        "ownership": {
                            "team": "XSOAR",  # wrong case → is_xsoar False
                            "maintainers": ["@xsoar-content"],
                        },
                    },
                },
            ],
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO117 — NoOrphanedHandlerCapabilityIdsValidator
# ============================================================


class TestCO117NoOrphanedHandlerCapabilityIds:
    """Tests for CO117 validator: every capability id claimed by a handler's
    ``capabilities[].id`` must be declared in the connector's capabilities.yaml
    (as either a top-level capability id or a nested sub_capabilities[].id).

    Per-id strict: a handler is reported when ANY claimed id is undeclared
    (even if other claimed ids are valid).
    """

    def test_handler_claims_only_declared_top_level_id_passes(self):
        """
        Given: The default connector — capabilities.yaml declares
               'test-capability' and the default handler claims
               capabilities=[{id: 'test-capability'}].
        When:  CO117 runs.
        Then:  No validation errors.
        """
        connector = create_connector_object()

        validator = NoOrphanedHandlerCapabilityIdsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_claims_declared_sub_capability_id_passes(self):
        """
        Given: capabilities.yaml declares a top-level 'top-cap' that has a
               nested sub_capability 'sub-cap'. The handler claims 'sub-cap'
               (the nested id, not the top-level one).
        When:  CO117 runs.
        Then:  No validation errors — nested sub_capability ids are part of
               the valid-id set.
        """
        connector = create_connector_object(
            connector_id="sub-cap-connector",
            capabilities_data={
                "capabilities": [
                    {
                        "id": "top-cap",
                        "title": "Top",
                        "description": "Top capability",
                        "sub_capabilities": [
                            {"id": "sub-cap", "title": "Sub"},
                        ],
                    },
                ],
            },
            handlers=[
                {
                    "id": "sub-handler",
                    "capabilities": [{"id": "sub-cap"}],
                },
            ],
        )

        validator = NoOrphanedHandlerCapabilityIdsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_with_empty_capabilities_list_is_skipped(self):
        """
        Given: A handler with an empty ``capabilities: []`` list (nothing
               claimed at all).
        When:  CO117 runs.
        Then:  No validation errors — there is nothing to validate. (A
               separate validator would be the right place for a "handler
               must claim at least one capability" rule.)
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "empty-cap-handler",
                    "capabilities": [],
                },
            ],
        )

        validator = NoOrphanedHandlerCapabilityIdsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_claims_undeclared_id_fails(self):
        """
        Given: capabilities.yaml declares only 'test-capability', but the
               handler claims 'missing-cap' (which is not declared anywhere).
        When:  CO117 runs.
        Then:  A single ValidationResult reports the handler id and the
               unknown capability id, plus the declared id set for context.
        """
        connector = create_connector_object(
            connector_id="orphan-cap-connector",
            handlers=[
                {
                    "id": "orphan-handler",
                    "capabilities": [{"id": "missing-cap"}],
                },
            ],
        )

        validator = NoOrphanedHandlerCapabilityIdsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "orphan-cap-connector" in msg
        assert "'orphan-handler'" in msg
        assert "'missing-cap'" in msg
        assert "'test-capability'" in msg  # the declared set is shown for context

    def test_handler_with_partial_mix_of_known_and_unknown_is_reported(self):
        """
        Given: capabilities.yaml declares 'test-capability'. A handler claims
               two ids: 'test-capability' (known) AND 'bogus-cap' (unknown).
        When:  CO117 runs.
        Then:  A validation error fires — per-id strict mode reports the
               unknown id even though one other id is valid. The error
               message must list ONLY the unknown id, not the known one.
        """
        connector = create_connector_object(
            connector_id="partial-orphan-connector",
            handlers=[
                {
                    "id": "mixed-handler",
                    "capabilities": [
                        {"id": "test-capability"},
                        {"id": "bogus-cap"},
                    ],
                },
            ],
        )

        validator = NoOrphanedHandlerCapabilityIdsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "'bogus-cap'" in msg
        # The known id should NOT appear in the per-handler unknown-ids list.
        # It WILL appear in the "declared in capabilities.yaml" suffix though,
        # so anchor the assertion on the "claims undeclared capability id(s):"
        # segment.
        unknown_segment = msg.split("claims undeclared capability id(s):")[1].split(
            "(declared"
        )[0]
        assert "'test-capability'" not in unknown_segment
        assert "'bogus-cap'" in unknown_segment

    def test_multiple_orphan_handlers_one_validation_result_lists_all(self):
        """
        Given: A connector with TWO handlers, each claiming a different
               undeclared id ('missing-A' and 'missing-B'). Only
               'test-capability' is declared in capabilities.yaml.
        When:  CO117 runs.
        Then:  A SINGLE ValidationResult is returned (one per connector,
               matching the CO114/CO123 pattern), and both offending
               handler ids and both unknown capability ids appear in the
               combined message.
        """
        connector = create_connector_object(
            connector_id="multi-orphan-connector",
            handlers=[
                {
                    "id": "handler-A",
                    "capabilities": [{"id": "missing-A"}],
                },
                {
                    "id": "handler-B",
                    "capabilities": [{"id": "missing-B"}],
                },
            ],
        )

        validator = NoOrphanedHandlerCapabilityIdsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "multi-orphan-connector" in msg
        assert "'handler-A'" in msg
        assert "'handler-B'" in msg
        assert "'missing-A'" in msg
        assert "'missing-B'" in msg


# ============================================================
# CO109 — NoHiddenParamInConnectorValidator
# ============================================================


def _build_connector_with_hidden_param_setup(
    *,
    integration_param_overrides: list,
    connector_id: str = "co109-connector",
    capability_id: str = "test-capability",
    field_id: str = "server_url",
    yaml_param_name: str = "server",
    handler_capability_id: Optional[str] = None,
):
    """Helper: build a connector + integration tuple plumbed for CO109 tests.

    - capabilities.yaml declares one capability with one configuration field
      whose id == ``field_id``.
    - The handler claims ``handler_capability_id`` (defaults to ``capability_id``).
    - handler.resolved_params maps connector_param_name=field_id ->
      content_param_name=yaml_param_name.
    - related_integration is created with the supplied configuration list.

    Returns the parsed Connector with `.handlers[0].related_integration` set.
    """
    claim_id = handler_capability_id or capability_id
    connector = create_connector_object(
        connector_id=connector_id,
        capabilities_data={
            "capabilities": [
                {
                    "id": capability_id,
                    "title": "Test Cap",
                    "description": "Test cap with one field",
                },
            ],
        },
        handlers=[
            {
                "id": "xsoar-handler",
                "capabilities": [{"id": claim_id}],
            },
        ],
    )

    # The connector parser only pulls per-capability configurations from
    # configurations.yaml, not from inline ``capabilities[].configurations``
    # in capabilities.yaml. Override the parsed CapabilityData.configurations
    # directly so the field shows up in the handler-reachable set.
    connector.capabilities[0].configurations = [
        FieldGroup(
            fields=[
                ConnectorField(
                    id=field_id,
                    title="Server URL",
                    field_type="input",
                ),
            ],
        ),
    ]

    integration = create_integration_object(
        paths=["configuration"],
        values=[integration_param_overrides],
    )

    connector.handlers[0].related_integration = integration
    connector.handlers[0].resolved_params = [
        ResolvedParamMapping(
            connector_param_name=field_id,
            content_param_name=yaml_param_name,
            is_serialized=False,
            source_file="capabilities.yaml",
        ),
    ]
    return connector


class TestCO109NoHiddenParamInConnector:
    """Tests for CO109 validator: every XSOAR-handler-reachable connector
    field that resolves back to an integration YAML parameter must NOT be
    hidden on the Cortex Platform.

    Hidden-on-platform = ``hidden: true`` OR ``hidden`` list containing
    ``"platform"``. Carve-out: a hidden YAML param with a non-None
    ``defaultvalue`` is exempted (mirrors Step 2.6 of the connectus
    migration mapper).
    """

    def test_visible_param_passes(self):
        """
        Given: A connector whose handler references a YAML param that is
               NOT hidden (no `hidden` field at all).
        When:  CO109 runs.
        Then:  No validation errors.
        """
        connector = _build_connector_with_hidden_param_setup(
            integration_param_overrides=[
                {"name": "server", "type": 0, "required": False},
            ],
        )

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_hidden_true_boolean_fails(self):
        """
        Given: A connector whose handler references a YAML param marked
               `hidden: true` (no YAML defaultvalue).
        When:  CO109 runs.
        Then:  One ValidationResult reports the field id and resolved
               YAML param name.
        """
        connector = _build_connector_with_hidden_param_setup(
            integration_param_overrides=[
                {"name": "server", "type": 0, "hidden": True},
            ],
        )

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "co109-connector" in msg
        assert "'xsoar-handler'" in msg
        assert "'server_url'" in msg
        assert "'server'" in msg

    def test_hidden_list_with_platform_fails(self):
        """
        Given: A YAML param with `hidden: ["xsoar_saas", "platform"]`.
        When:  CO109 runs.
        Then:  One ValidationResult — "platform" in the list triggers the
               failure even alongside other marketplaces.
        """
        connector = _build_connector_with_hidden_param_setup(
            integration_param_overrides=[
                {
                    "name": "server",
                    "type": 0,
                    "hidden": ["xsoar_saas", "platform"],
                },
            ],
        )

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "'server'" in results[0].message

    def test_hidden_list_without_platform_passes(self):
        """
        Given: A YAML param with `hidden: ["xsoar_saas"]` (no "platform").
        When:  CO109 runs.
        Then:  No validation errors — only the literal string "platform"
               in the list triggers the failure.
        """
        connector = _build_connector_with_hidden_param_setup(
            integration_param_overrides=[
                {
                    "name": "server",
                    "type": 0,
                    "hidden": ["xsoar_saas"],
                },
            ],
        )

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_hidden_true_with_yml_defaultvalue_passes_via_carveout(self):
        """
        Given: A YAML param with `hidden: true` AND a non-None
               `defaultvalue` in the YAML.
        When:  CO109 runs.
        Then:  No validation errors — the carve-out mirrors the Step 2.6
               mapper rule (a hidden param with a YAML default is
               acceptable because the user never has to interact with it).
        """
        connector = _build_connector_with_hidden_param_setup(
            integration_param_overrides=[
                {
                    "name": "server",
                    "type": 0,
                    "hidden": True,
                    "defaultvalue": "https://default.example.com",
                },
            ],
        )

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_field_with_no_resolved_param_is_silently_skipped(self):
        """
        Given: A connector field reachable from the handler whose id has
               NO entry in handler.resolved_params (parser couldn't resolve
               it; e.g. missing serializer + non-identity mapping).
        When:  CO109 runs.
        Then:  No validation errors — per Q4 design decision, fields that
               cannot be resolved via resolved_params are silently skipped.
        """
        connector = _build_connector_with_hidden_param_setup(
            integration_param_overrides=[
                {"name": "server", "type": 0, "hidden": True},
            ],
        )
        # Wipe resolved_params so the field cannot be looked up.
        connector.handlers[0].resolved_params = []

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_no_related_integration_skipped(self):
        """
        Given: A connector handler with `related_integration=None`
               (CO100's domain).
        When:  CO109 runs.
        Then:  No validation errors — CO109 does not double-report.
        """
        connector = _build_connector_with_hidden_param_setup(
            integration_param_overrides=[
                {"name": "server", "type": 0, "hidden": True},
            ],
        )
        connector.handlers[0].related_integration = None

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_non_xsoar_handlers_are_not_checked(self):
        """
        Given: A connector whose only handler is a partner handler (not
               XSOAR) that references a hidden YAML param.
        When:  CO109 runs.
        Then:  No validation errors — CO109 only inspects
               connector.xsoar_handlers (matches CO100/CO101/CO114 gate).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "partner-handler",
                    "metadata": {
                        "module": "partner",
                        "ownership": {
                            "team": "partner-team",
                            "maintainers": ["@partner-dev"],
                        },
                    },
                    "capabilities": [{"id": "test-capability"}],
                },
            ],
        )

        # Same field-injection trick used by the helper.
        connector.capabilities[0].configurations = [
            FieldGroup(
                fields=[
                    ConnectorField(
                        id="server_url",
                        title="Server URL",
                        field_type="input",
                    ),
                ],
            ),
        ]

        integration = create_integration_object(
            paths=["configuration"],
            values=[[{"name": "server", "type": 0, "hidden": True}]],
        )
        connector.handlers[0].related_integration = integration
        connector.handlers[0].resolved_params = [
            ResolvedParamMapping(
                connector_param_name="server_url",
                content_param_name="server",
                is_serialized=False,
                source_file="capabilities.yaml",
            ),
        ]

        validator = NoHiddenParamInConnectorValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO111 — NoChangeConnectorIdsValidator
# ============================================================


class TestCO111NoChangeConnectorIds:
    """Tests for CO111 validator: breaking-change check that catches
    removed or renamed IDs in an XSOAR-supported connector.

    Trigger gate: connector has at least one XSOAR handler.
    Detection: for every ID in the old version (connector.yaml.id +
    capabilities[].id + sub_capabilities[].id + connection profile ids +
    handler.id per-file), the corresponding new-version set must contain
    that id. Any missing id fails. Additions are non-breaking and pass.
    Output: one ValidationResult per connector, grouped by file path.
    """

    def test_no_changes_passes(self):
        """
        Given: An XSOAR-supported connector whose old and new versions
               have identical IDs across all four file types.
        When:  CO111 runs.
        Then:  No validation errors.
        """
        new = create_connector_object(connector_id="stable-conn")
        old = create_connector_object(connector_id="stable-conn")
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 0

    def test_no_xsoar_handlers_skipped(self):
        """
        Given: A connector whose only handler is a partner handler (not
               XSOAR), AND its old version had a different connector id.
        When:  CO111 runs.
        Then:  No validation errors — the trigger gate (at least one XSOAR
               handler in the NEW connector) is not met, so CO111 does not
               apply.
        """
        partner_handler = {
            "id": "partner-handler",
            "metadata": {
                "module": "partner",
                "ownership": {
                    "team": "partner-team",
                    "maintainers": ["@partner-dev"],
                },
            },
        }
        new = create_connector_object(
            connector_id="renamed-id", handlers=[partner_handler]
        )
        old = create_connector_object(
            connector_id="original-id", handlers=[partner_handler]
        )
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 0

    def test_connector_id_renamed_fails(self):
        """
        Given: An XSOAR-supported connector whose connector.yaml.id changed.
        When:  CO111 runs.
        Then:  A single ValidationResult lists the old connector id under
               the 'connector.yaml' bucket.
        """
        new = create_connector_object(connector_id="new-id")
        old = create_connector_object(connector_id="old-id")
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        assert "new-id" in msg  # connector header
        assert "connector.yaml" in msg
        assert "'old-id'" in msg

    def test_capability_id_removed_fails(self):
        """
        Given: An XSOAR-supported connector whose old version had a
               capability id 'removed-cap' that no longer exists in new.
        When:  CO111 runs.
        Then:  A single ValidationResult lists the missing capability id
               under the 'capabilities.yaml' bucket.
        """
        new = create_connector_object(connector_id="cap-conn")
        # Inject old capabilities directly (bypassing the parser).
        from demisto_sdk.commands.content_graph.objects.connector import (
            CapabilityData,
        )

        old = create_connector_object(connector_id="cap-conn")
        old.capabilities = list(old.capabilities) + [
            CapabilityData(
                id="removed-cap",
                title="Removed",
                description="Capability that will be removed",
            ),
        ]
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        assert "capabilities.yaml" in msg
        assert "'removed-cap'" in msg

    def test_sub_capability_id_removed_fails(self):
        """
        Given: An XSOAR-supported connector whose old version's capability
               had a sub_capability id 'removed-sub' that no longer exists
               in new (the parent capability is still present).
        When:  CO111 runs.
        Then:  A ValidationResult lists the missing sub_capability id under
               the 'capabilities.yaml' bucket (nested ids are validated the
               same as top-level ones).
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            CapabilityData,
            SubCapability,
        )

        new = create_connector_object(connector_id="sub-conn")
        old = create_connector_object(connector_id="sub-conn")
        # Replace the default capability with one that has a sub-cap in OLD.
        old.capabilities = [
            CapabilityData(
                id="test-capability",
                title="Test",
                description="Top cap",
                sub_capabilities=[
                    SubCapability(id="removed-sub", title="Removed sub"),
                ],
            ),
        ]
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        assert "capabilities.yaml" in msg
        assert "'removed-sub'" in msg

    def test_handler_id_renamed_in_same_dir_fails(self):
        """
        Given: An XSOAR-supported connector where a handler directory was
               kept (same handler_dir_name) but its id was renamed.
        When:  CO111 runs.
        Then:  A ValidationResult lists the old handler id under the
               components/handlers/<dir>/handler.yaml bucket. The fact
               that the new id is a different value is enough to flag —
               renames-in-place are the most subtle breaking change.
        """
        new = create_connector_object(connector_id="h-conn")
        old = create_connector_object(connector_id="h-conn")
        # Both connectors have one handler in dir 'xsoar_test' (slug of the
        # template handler id 'xsoar-test'). Rename the new handler's id.
        new.handlers[0].id = "new-handler-id"
        # OLD keeps original id 'xsoar-test'.
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        # Path is constructed from handler_dir_name, which is 'xsoar_test'
        # (the template's dir; see create_connector_object).
        assert "components/handlers/xsoar_test/handler.yaml" in msg
        assert "'xsoar-test'" in msg  # the OLD id

    def test_addition_is_not_breaking(self):
        """
        Given: An XSOAR-supported connector where the NEW version added a
               brand-new capability id, but every OLD id is preserved.
        When:  CO111 runs.
        Then:  No validation errors — additions are non-breaking.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            CapabilityData,
        )

        new = create_connector_object(connector_id="add-conn")
        new.capabilities = list(new.capabilities) + [
            CapabilityData(
                id="brand-new-cap",
                title="New",
                description="Added in this revision",
            ),
        ]
        old = create_connector_object(connector_id="add-conn")
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 0

    def test_multiple_removals_one_validation_result_groups_by_file(self):
        """
        Given: An XSOAR-supported connector with TWO removals across two
               file types: a capability id removed AND the handler id
               renamed in-place.
        When:  CO111 runs.
        Then:  A SINGLE ValidationResult per connector (CO114/CO123
               pattern). The message contains BOTH file-type sections and
               BOTH removed ids.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            CapabilityData,
        )

        new = create_connector_object(connector_id="multi-rm")
        # Rename the handler id in place.
        new.handlers[0].id = "new-handler"

        old = create_connector_object(connector_id="multi-rm")
        # Old had an extra capability that is now removed.
        old.capabilities = list(old.capabilities) + [
            CapabilityData(
                id="old-extra-cap",
                title="Extra",
                description="Removed in new",
            ),
        ]
        new.old_base_content_object = old

        validator = NoChangeConnectorIdsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        # Both removal sections present in a single message.
        assert "capabilities.yaml" in msg
        assert "'old-extra-cap'" in msg
        assert "components/handlers/xsoar_test/handler.yaml" in msg
        assert "'xsoar-test'" in msg


# ============================================================
# CO119 — IsCapabilityNameValidValidator
# ============================================================


class TestCO119IsCapabilityNameValid:
    """Tests for CO119 validator: every capability id claimed by an XSOAR
    handler must be a canonical top-level capability OR a sub_capability
    nested under a canonical parent (per Q1=a / Q2=a / Q3=b in design).

    Canonical set:
      automation, fetch-assets-and-vulnerabilities, fetch-issues,
      fetch-secrets, log-collection, threat-intelligence-enrichment.
    """

    def test_canonical_set_has_exactly_six_entries(self):
        """Sanity guard: if someone adds a 7th to CANONICAL_CAPABILITY_IDS
        without updating the spec, this test will scream first."""
        assert len(CANONICAL_CAPABILITY_IDS) == 6

    def test_handler_claims_canonical_top_level_passes(self):
        """
        Given: A connector whose XSOAR handler claims 'automation' (the
               default capabilities.yaml template uses 'test-capability',
               so override it to use the canonical 'automation' instead).
        When:  CO119 runs.
        Then:  No validation errors.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "automation",
                        "title": "Automation",
                        "description": "Run automations",
                    },
                ],
            },
            handlers=[
                {
                    "id": "xsoar-auto",
                    "capabilities": [{"id": "automation"}],
                },
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_claims_sub_cap_under_canonical_parent_passes(self):
        """
        Given: capabilities.yaml declares a top-level 'automation' (canonical)
               with a sub_capability 'xsoar_x-automation'; handler claims
               'xsoar_x-automation'.
        When:  CO119 runs.
        Then:  No validation errors — sub-cap inherits canonical status
               from its parent.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "automation",
                        "title": "Automation",
                        "description": "Run automations",
                        "sub_capabilities": [
                            {"id": "xsoar_x-automation", "title": "X"},
                        ],
                    },
                ],
            },
            handlers=[
                {
                    "id": "xsoar-sub",
                    "capabilities": [{"id": "xsoar_x-automation"}],
                },
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_claims_invalid_top_level_fails(self):
        """
        Given: A handler claims 'made-up-cap' which is NOT in the canonical
               set and not declared anywhere in capabilities.yaml.
        When:  CO119 runs.
        Then:  Single ValidationResult per connector lists the bad id +
               the canonical set for reference.
        """
        connector = create_connector_object(
            connector_id="bad-top-conn",
            capabilities_data={
                "capabilities": [
                    {
                        "id": "automation",
                        "title": "Automation",
                        "description": "Run automations",
                    },
                ],
            },
            handlers=[
                {
                    "id": "xsoar-bad",
                    "capabilities": [{"id": "made-up-cap"}],
                },
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "bad-top-conn" in msg
        assert "'xsoar-bad'" in msg
        assert "'made-up-cap'" in msg
        # The error message lists the canonical set for reference.
        assert "'automation'" in msg

    def test_handler_claims_sub_cap_under_NON_canonical_parent_fails(self):
        """
        Given: capabilities.yaml has a top-level 'custom-cap' (NOT in the
               canonical set) with a sub_capability 'sub-1'; an XSOAR
               handler claims 'sub-1'.
        When:  CO119 runs.
        Then:  Failure — per Q2=a, sub-caps under non-canonical parents
               are themselves invalid.
        """
        connector = create_connector_object(
            connector_id="non-canon-parent-conn",
            capabilities_data={
                "capabilities": [
                    {
                        "id": "custom-cap",
                        "title": "Custom",
                        "description": "Custom (non-canonical)",
                        "sub_capabilities": [
                            {"id": "sub-1", "title": "Sub-1"},
                        ],
                    },
                ],
            },
            handlers=[
                {
                    "id": "xsoar-sub-bad",
                    "capabilities": [{"id": "sub-1"}],
                },
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "'sub-1'" in msg
        assert "'xsoar-sub-bad'" in msg

    def test_all_six_canonical_names_recognized(self):
        """
        Given: A connector that declares all 6 canonical top-level
               capabilities and one handler claiming each in turn.
        When:  CO119 runs.
        Then:  No validation errors — every canonical id is accepted.
        """
        canonical = sorted(CANONICAL_CAPABILITY_IDS)
        # One handler per canonical capability; each handler claims its
        # matching canonical id.
        handlers = [
            {
                "id": f"xsoar-h{i}",
                "capabilities": [{"id": cap_id}],
            }
            for i, cap_id in enumerate(canonical)
        ]
        capabilities = [
            {
                "id": cap_id,
                "title": cap_id.replace("-", " ").title(),
                "description": f"{cap_id} capability",
            }
            for cap_id in canonical
        ]
        connector = create_connector_object(
            connector_id="all-canon",
            capabilities_data={"capabilities": capabilities},
            handlers=handlers,
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_with_empty_capabilities_list_is_skipped(self):
        """
        Given: XSOAR handler with empty ``capabilities: []`` list.
        When:  CO119 runs.
        Then:  No validation errors — there is nothing to validate.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "empty-cap-handler",
                    "capabilities": [],
                },
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_non_xsoar_handlers_are_skipped(self):
        """
        Given: A connector whose only handler is a partner handler claiming
               a totally bogus capability id.
        When:  CO119 runs.
        Then:  No validation errors — Q1=a: non-xsoar handlers are out of
               CO119's scope.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "partner-handler",
                    "metadata": {
                        "module": "partner",
                        "ownership": {
                            "team": "partner-team",
                            "maintainers": ["@partner-dev"],
                        },
                    },
                    "capabilities": [{"id": "wildly-non-canonical"}],
                },
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_multiple_violations_merged_into_one_validation_result(self):
        """
        Given: A connector with TWO XSOAR handlers each claiming a different
               invalid capability id.
        When:  CO119 runs.
        Then:  A single ValidationResult is returned (matching CO114/CO117
               pattern) listing both handler ids and both bad ids.
        """
        connector = create_connector_object(
            connector_id="multi-bad",
            capabilities_data={
                "capabilities": [
                    {"id": "automation", "title": "Automation", "description": "Auto"},
                ],
            },
            handlers=[
                {
                    "id": "xsoar-h1",
                    "capabilities": [{"id": "made-up-A"}],
                },
                {
                    "id": "xsoar-h2",
                    "capabilities": [{"id": "made-up-B"}],
                },
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "multi-bad" in msg
        assert "'xsoar-h1'" in msg
        assert "'xsoar-h2'" in msg
        assert "'made-up-A'" in msg
        assert "'made-up-B'" in msg


# ============================================================
# CO110 — NoRemovedConnectorParamsValidator
# ============================================================


class TestCO110NoRemovedConnectorParams:
    """Tests for CO110 validator: breaking-change check that catches
    removed (or renamed-without-serializer-bridge) parameter ids across
    every param-bearing bucket of an XSOAR-supported connector.

    Trigger gate: connector has at least one XSOAR handler.
    Detection (per bucket — capability '<id>', connection.yaml
    (general_configurations), connection.yaml (profile '<id>')):
    every field id in the OLD bucket must be either (a) present in the
    matching NEW bucket OR (b) bridged by a NEW handler serializer
    entry whose ``field_name`` equals the old id. Missing-and-unbridged
    ids fail. Additions are non-breaking and pass.
    """

    @staticmethod
    def _add_capability_field(connector, cap_id: str, field_id: str) -> None:
        """Helper: append a ConnectorField with id=field_id to the FIRST
        FieldGroup of the named capability's configurations list. Creates
        the FieldGroup if the capability has none.
        """
        for cap in connector.capabilities:
            if cap.id == cap_id:
                if not cap.configurations:
                    cap.configurations = [FieldGroup(fields=[])]
                cap.configurations[0].fields.append(
                    ConnectorField(
                        id=field_id,
                        title=field_id.replace("_", " ").title(),
                        field_type="input",
                    )
                )
                return
        raise ValueError(f"capability '{cap_id}' not found on connector")

    @staticmethod
    def _add_profile_field(connector, profile_id: str, field_id: str) -> None:
        """Helper: append a ConnectorField with id=field_id to the FIRST
        FieldGroup of the named connection profile's configurations list.
        Creates the FieldGroup if the profile has none.
        """
        assert connector.connection is not None
        for profile in connector.connection.profiles:
            if profile.id == profile_id:
                if not profile.configurations:
                    profile.configurations = [FieldGroup(fields=[])]
                profile.configurations[0].fields.append(
                    ConnectorField(
                        id=field_id,
                        title=field_id.replace("_", " ").title(),
                        field_type="input",
                    )
                )
                return
        raise ValueError(f"profile '{profile_id}' not found on connection")

    @staticmethod
    def _set_general_configurations(connector, field_ids: list) -> None:
        """Helper: replace ``connection.general_configurations`` with a
        single FieldGroup containing one input field per id in field_ids.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            GeneralConfigurations,
        )

        assert connector.connection is not None
        connector.connection.general_configurations = GeneralConfigurations(
            configurations=[
                FieldGroup(
                    fields=[
                        ConnectorField(
                            id=fid,
                            title=fid.replace("_", " ").title(),
                            field_type="input",
                        )
                        for fid in field_ids
                    ]
                )
            ]
        )

    @staticmethod
    def _set_handler_serializer_bridges(
        connector, handler_idx: int, bridges: list
    ) -> None:
        """Helper: set handler.serializer.field_mappings on the
        handler_idx-th handler so each entry in ``bridges`` (a list of
        ``(new_id, old_id)`` tuples) becomes a FieldMapping bridge.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            FieldMapping,
            SerializerData,
        )

        connector.handlers[handler_idx].serializer = SerializerData(
            field_mappings=[
                FieldMapping(id=new_id, field_name=old_id) for new_id, old_id in bridges
            ]
        )

    def test_no_changes_passes(self):
        """
        Given: An XSOAR-supported connector whose old and new versions
               have identical field ids across all buckets.
        When:  CO110 runs.
        Then:  No validation errors.
        """
        new = create_connector_object(connector_id="stable-conn")
        old = create_connector_object(connector_id="stable-conn")
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 0

    def test_no_xsoar_handlers_skipped(self):
        """
        Given: A connector whose only handler is a partner handler (not
               XSOAR), AND its old version had a field that was removed
               in the new version.
        When:  CO110 runs.
        Then:  No validation errors — the XSOAR-handler gate is not
               met, so CO110 does not apply.
        """
        partner_handler = {
            "id": "partner-handler",
            "metadata": {
                "module": "partner",
                "ownership": {
                    "team": "partner-team",
                    "maintainers": ["@partner-dev"],
                },
            },
        }
        new = create_connector_object(
            connector_id="partner-only", handlers=[partner_handler]
        )
        old = create_connector_object(
            connector_id="partner-only", handlers=[partner_handler]
        )
        # Drop a profile field from NEW so a diff would normally fire.
        new.connection.profiles[0].configurations = []
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 0

    def test_general_configurations_param_removed_fails(self):
        """
        Given: An XSOAR-supported connector whose OLD version had a
               connection.yaml general_configurations field ``timeout``
               that no longer exists in NEW.
        When:  CO110 runs.
        Then:  A ValidationResult lists ``timeout`` under the
               ``connection.yaml (general_configurations)`` bucket.
        """
        new = create_connector_object(connector_id="gc-conn")
        old = create_connector_object(connector_id="gc-conn")
        # OLD had a timeout general-config field; NEW has none.
        self._set_general_configurations(old, ["timeout"])
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        assert "gc-conn" in msg
        assert "connection.yaml (general_configurations)" in msg
        assert "'timeout'" in msg

    def test_per_capability_param_removed_fails(self):
        """
        Given: An XSOAR-supported connector whose OLD version had a field
               id ``old_mailbox_param`` under capability ``test-capability``
               (the template capability) that no longer exists in NEW.
        When:  CO110 runs.
        Then:  A ValidationResult lists the missing field id under the
               ``capability 'test-capability'`` bucket.
        """
        new = create_connector_object(connector_id="cap-conn")
        old = create_connector_object(connector_id="cap-conn")
        self._add_capability_field(old, "test-capability", "old_mailbox_param")
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        assert "capability 'test-capability'" in msg
        assert "'old_mailbox_param'" in msg

    def test_connection_profile_auth_param_removed_fails(self):
        """
        Given: An XSOAR-supported connector whose OLD ``default``
               connection profile had an ``api_url`` field that is removed
               in NEW (the template starts with api_url; we drop it).
        When:  CO110 runs.
        Then:  A ValidationResult lists ``api_url`` under the
               ``connection.yaml (profile 'default')`` bucket.
        """
        new = create_connector_object(connector_id="auth-conn")
        old = create_connector_object(connector_id="auth-conn")
        # OLD keeps the template's api_url; NEW drops it.
        new.connection.profiles[0].configurations = []
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        assert "connection.yaml (profile 'default')" in msg
        assert "'api_url'" in msg

    def test_param_renamed_with_serializer_bridge_passes(self):
        """
        Given: An XSOAR-supported connector whose OLD had a field id
               ``foo`` under a capability, and NEW has that field
               renamed to ``xsoar_test_foo`` PLUS the NEW handler's
               serializer carries ``{id: xsoar_test_foo, field_name: foo}``
               so the platform can still resolve the old id.
        When:  CO110 runs.
        Then:  No validation errors — the serializer escape hatch
               bridges the rename (this is what
               ``manifest_generator.dedup_field_id_and_register``
               produces during multi-handler dedup, and CO110 must not
               flag those legitimate renames).
        """
        new = create_connector_object(connector_id="bridge-conn")
        old = create_connector_object(connector_id="bridge-conn")
        self._add_capability_field(old, "test-capability", "foo")
        self._add_capability_field(new, "test-capability", "xsoar_test_foo")
        self._set_handler_serializer_bridges(
            new, handler_idx=0, bridges=[("xsoar_test_foo", "foo")]
        )
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 0

    def test_param_renamed_without_serializer_bridge_fails(self):
        """
        Given: An XSOAR-supported connector whose OLD had field id ``foo``
               under a capability, and NEW has it renamed to ``bar`` with
               NO matching serializer bridge.
        When:  CO110 runs.
        Then:  A ValidationResult flags ``foo`` as removed (the rename is
               indistinguishable from a deletion from the platform's
               perspective, and without a serializer bridge there's no
               way to resolve the old id).
        """
        new = create_connector_object(connector_id="rename-conn")
        old = create_connector_object(connector_id="rename-conn")
        self._add_capability_field(old, "test-capability", "foo")
        self._add_capability_field(new, "test-capability", "bar")
        # No serializer entry on new.
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        assert "capability 'test-capability'" in msg
        assert "'foo'" in msg
        # 'bar' is the new id (addition) — must NOT be listed as removed.
        assert "'bar'" not in msg

    def test_addition_only_is_not_breaking(self):
        """
        Given: An XSOAR-supported connector where NEW added brand-new
               fields to a capability and to a connection profile, but
               every OLD field id is preserved.
        When:  CO110 runs.
        Then:  No validation errors — additions are non-breaking.
        """
        new = create_connector_object(connector_id="add-only")
        old = create_connector_object(connector_id="add-only")
        # Only NEW adds fields; old stays minimal.
        self._add_capability_field(new, "test-capability", "brand_new_cap_field")
        self._add_profile_field(new, "default", "brand_new_auth_field")
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 0

    def test_multiple_buckets_grouped_in_one_validation_result(self):
        """
        Given: An XSOAR-supported connector with removals across THREE
               distinct buckets simultaneously: a capability field, a
               general_configurations field, AND a connection profile
               field.
        When:  CO110 runs.
        Then:  A SINGLE ValidationResult per connector (the CO111 / CO114
               / CO123 pattern). The message lists ALL three buckets and
               the removed id in each.
        """
        new = create_connector_object(connector_id="multi-rm")
        old = create_connector_object(connector_id="multi-rm")

        # Bucket 1: capability field 'cap_only' removed.
        self._add_capability_field(old, "test-capability", "cap_only")
        # Bucket 2: general_configurations 'gc_only' removed.
        self._set_general_configurations(old, ["gc_only"])
        # Bucket 3: profile field 'api_url' removed (template starts with it
        # in old; we drop it in new).
        new.connection.profiles[0].configurations = []
        new.old_base_content_object = old

        validator = NoRemovedConnectorParamsValidator()
        results = validator.obtain_invalid_content_items([new])

        assert len(results) == 1
        msg = results[0].message
        # All three bucket labels appear in the same single message.
        assert "capability 'test-capability'" in msg
        assert "'cap_only'" in msg
        assert "connection.yaml (general_configurations)" in msg
        assert "'gc_only'" in msg
        assert "connection.yaml (profile 'default')" in msg
        assert "'api_url'" in msg


# ============================================================
# CO116 — IsConnectorMatchesIntegrationFlagsValidator
# ============================================================


class TestCO116IsConnectorMatchesIntegrationFlags:
    """Tests for CO116 validator: cross-validate connector capability
    declarations against the matched integration's script flags.

    Trigger gate: each XSOAR handler with a resolved
    ``related_integration`` is checked independently. Handlers without
    a resolved integration are skipped (CO100's concern).

    Detection (per handler, per declared capability):
      - ``fetch-issues`` requires ``script.isfetch: true``
        (``isfetch:platform: false`` disables it; ``:platform`` only
        consulted when base is True).
      - ``log-collection`` requires ``script.isfetchevents: true``.
      - ``fetch-assets-and-vulnerabilities`` requires
        ``script.isfetchassets: true``.
      - ``threat-intelligence-enrichment`` requires ``script.feed: true``.
      - ``fetch-secrets`` and ``automation`` are EXEMPT (never checked).

    Long-running exemption (NARROW, per-capability): a specific
    capability is exempt if (a) the integration has
    ``script.longRunning: true`` AND (b)
    ``INTEGRATION_TO_LONGRUNNING_CAPABILITY[integration.object_id]``
    points to that exact capability.

    Output: one ValidationResult per handler with all unforgiven
    mismatches grouped in a single message.
    """

    @staticmethod
    def _make_integration_mock(
        script: Optional[dict] = None, object_id: str = "TestIntegration"
    ) -> MagicMock:
        """Build a minimal Integration stand-in for CO116.

        ``script`` is exposed as a dict (the validator's
        ``_get_integration_script`` helper accepts dicts directly). The
        ``object_id`` doubles as the integration id used to look up the
        long-running exemption.
        """
        integration = MagicMock()
        integration.script = script if script is not None else {}
        integration.object_id = object_id
        return integration

    @staticmethod
    def _set_handler_capabilities(connector, cap_ids: List[str]) -> None:
        """Replace the first handler's capabilities with the given ids
        (no auth options — CO116 doesn't read them).
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerCapability,
        )

        connector.handlers[0].capabilities = [
            HandlerCapability(id=cap_id) for cap_id in cap_ids
        ]

    def test_no_xsoar_handlers_skipped(self):
        """
        Given: A connector whose only handler is a partner handler, with
               a declared capability that would normally trigger a flag
               check.
        When:  CO116 runs.
        Then:  No validation errors — the XSOAR-handler gate is not
               met (``connector.xsoar_handlers`` is empty).
        """
        partner_handler = {
            "id": "partner-handler",
            "metadata": {
                "module": "partner",
                "ownership": {
                    "team": "partner-team",
                    "maintainers": ["@partner-dev"],
                },
            },
            "capabilities": [{"id": "fetch-issues"}],
        }
        connector = create_connector_object(
            connector_id="partner-only", handlers=[partner_handler]
        )
        # related_integration with isfetch=false — would normally fail.
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetch": False}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_without_related_integration_skipped(self):
        """
        Given: An XSOAR handler with NO resolved related_integration.
        When:  CO116 runs.
        Then:  No validation errors — CO100 handles the missing-
               integration case; CO116 must not pile on.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues"])
        assert connector.handlers[0].related_integration is None

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_fetch_issues_with_isfetch_true_passes(self):
        """
        Given: Handler declares ``fetch-issues`` capability, integration
               has ``script.isfetch: true`` (no platform override).
        When:  CO116 runs.
        Then:  No validation errors.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetch": True}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_fetch_issues_with_isfetch_false_fails(self):
        """
        Given: Handler declares ``fetch-issues``, integration has
               ``script.isfetch: false`` (no platform override).
        When:  CO116 runs.
        Then:  ValidationResult lists the capability mismatch.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetch": False}, object_id="NoFetchIntegration"
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "fetch-issues" in msg
        assert "script.isfetch" in msg
        assert "NoFetchIntegration" in msg

    def test_fetch_issues_platform_variant_alone_does_not_enable(self):
        """
        Given: Handler declares ``fetch-issues``, integration has
               ``script.isfetch: false`` AND
               ``script.isfetch:platform: true``.
        When:  CO116 runs.
        Then:  ValidationResult fires — the platform variant can only
               *disable* a fetch, never *enable* one (mirrors Rule 3's
               ``isfetch is True and isfetch:platform is not False``).
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetch": False, "isfetch:platform": True}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1

    def test_fetch_issues_platform_variant_false_disables_a_true_base(self):
        """
        Given: Handler declares ``fetch-issues``, integration has
               ``script.isfetch: true`` BUT
               ``script.isfetch:platform: false``.
        When:  CO116 runs.
        Then:  ValidationResult fires — the platform explicitly
               disabled the fetch even though the base flag is True.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetch": True, "isfetch:platform": False}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1

    def test_log_collection_with_isfetchevents_false_fails(self):
        """
        Given: Handler declares ``log-collection``, integration has
               ``script.isfetchevents: false``.
        When:  CO116 runs.
        Then:  ValidationResult fires.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["log-collection"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetchevents": False}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "log-collection" in results[0].message
        assert "script.isfetchevents" in results[0].message

    def test_fetch_assets_with_isfetchassets_false_fails(self):
        """
        Given: Handler declares ``fetch-assets-and-vulnerabilities``,
               integration has ``script.isfetchassets: false``.
        When:  CO116 runs.
        Then:  ValidationResult fires.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-assets-and-vulnerabilities"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetchassets": False}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "fetch-assets-and-vulnerabilities" in results[0].message
        assert "script.isfetchassets" in results[0].message

    def test_threat_intelligence_with_feed_false_fails(self):
        """
        Given: Handler declares ``threat-intelligence-enrichment``,
               integration has ``script.feed: false``.
        When:  CO116 runs.
        Then:  ValidationResult fires.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["threat-intelligence-enrichment"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"feed": False}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "threat-intelligence-enrichment" in results[0].message
        assert "script.feed" in results[0].message

    def test_fetch_secrets_capability_is_exempt(self):
        """
        Given: Handler declares ``fetch-secrets``, integration has NONE
               of the fetch flags enabled (and no isFetchCredentials
               param). This would NOT be flagged by CO116 because
               fetch-secrets is exempt per the spec — Rule 1 in the
               mapper gates it on a *config param*, not a script flag,
               which the validator deliberately does not check.
        When:  CO116 runs.
        Then:  No validation errors.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-secrets"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_automation_capability_is_exempt(self):
        """
        Given: Handler declares ``automation``, integration has NO
               fetch flags. Automation is exempt because Rule 6 derives
               it from command presence, not a script flag.
        When:  CO116 runs.
        Then:  No validation errors.
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["automation"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_long_running_narrow_exemption_for_matching_capability(self):
        """
        Given: Handler declares ``fetch-issues``, integration is
               ``QRadar v3`` (mapped to ``fetch-issues`` in
               INTEGRATION_TO_LONGRUNNING_CAPABILITY) with
               ``longRunning: true`` and NO ``isfetch`` flag.
        When:  CO116 runs.
        Then:  No validation errors — the narrow long-running exemption
               fires because the mismatched capability matches the one
               listed for this integration id.
        """
        assert INTEGRATION_TO_LONGRUNNING_CAPABILITY.get("QRadar v3") == (
            "fetch-issues"
        )
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"longRunning": True, "isfetch": False},
            object_id="QRadar v3",
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_long_running_narrow_exemption_does_NOT_apply_to_other_caps(self):
        """
        Given: Handler declares BOTH ``fetch-issues`` AND
               ``log-collection``. Integration is ``QRadar v3``
               (long-running → ``fetch-issues``) with ``longRunning:
               true``, ``isfetch: false``, ``isfetchevents: false``.
        When:  CO116 runs.
        Then:  ValidationResult fires for ``log-collection`` only.
               ``fetch-issues`` is exempt (the narrow long-running
               exemption applies to it), but ``log-collection`` is NOT
               (the integration is not mapped to log-collection).
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues", "log-collection"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={
                "longRunning": True,
                "isfetch": False,
                "isfetchevents": False,
            },
            object_id="QRadar v3",
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "log-collection" in msg
        # fetch-issues should NOT appear in the mismatch list (exempt).
        # Use a precise check on the mismatch-line marker to avoid false
        # negatives if 'fetch-issues' appears in headers etc.
        assert "capability 'fetch-issues'" not in msg
        assert "capability 'log-collection'" in msg

    def test_long_running_without_integration_in_dict_does_not_exempt(self):
        """
        Given: Handler declares ``fetch-issues``, integration has
               ``longRunning: true`` AND ``isfetch: false``, but the
               integration id is NOT in
               INTEGRATION_TO_LONGRUNNING_CAPABILITY.
        When:  CO116 runs.
        Then:  ValidationResult fires — without an entry in the dict,
               long-running gives no exemption (narrow rule).
        """
        unknown_id = "ThisIdIsDeliberatelyMissingFromTheDict"
        assert unknown_id not in INTEGRATION_TO_LONGRUNNING_CAPABILITY
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"longRunning": True, "isfetch": False},
            object_id=unknown_id,
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "fetch-issues" in results[0].message

    def test_multiple_mismatches_one_handler_one_validation_result(self):
        """
        Given: A handler declares BOTH ``fetch-issues`` and
               ``log-collection``; the integration has NEITHER flag
               enabled (and is NOT long-running).
        When:  CO116 runs.
        Then:  A SINGLE ValidationResult per handler with BOTH
               mismatches in its message (CO112-style grouping).
        """
        connector = create_connector_object()
        self._set_handler_capabilities(connector, ["fetch-issues", "log-collection"])
        connector.handlers[0].related_integration = self._make_integration_mock(
            script={"isfetch": False, "isfetchevents": False}
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "fetch-issues" in msg
        assert "log-collection" in msg
        assert "script.isfetch" in msg
        assert "script.isfetchevents" in msg

    def test_capability_flag_requirements_has_exactly_four_entries(self):
        """
        Given: The CAPABILITY_FLAG_REQUIREMENTS table exported by the
               CO116 module.
        When:  Inspected by this sanity check.
        Then:  It contains EXACTLY the four canonical fetch-gated
               capabilities — fetch-issues, log-collection,
               fetch-assets-and-vulnerabilities,
               threat-intelligence-enrichment. fetch-secrets and
               automation must NOT appear (they are intentionally
               exempt).
        """
        assert set(CAPABILITY_FLAG_REQUIREMENTS.keys()) == {
            "fetch-issues",
            "log-collection",
            "fetch-assets-and-vulnerabilities",
            "threat-intelligence-enrichment",
        }
        assert "fetch-secrets" not in CAPABILITY_FLAG_REQUIREMENTS
        assert "automation" not in CAPABILITY_FLAG_REQUIREMENTS


# ============================================================
# CO130 — IsEveryIntegrationParamCoveredValidator
# ============================================================


def _build_connector_with_coverage_setup(
    *,
    integration_param_overrides: list,
    resolved_pairs: List[tuple],
    capability_id: str = "test-capability",
    connector_field_ids: Optional[List[str]] = None,
    connector_id: str = "co130-connector",
    handler_capability_id: Optional[str] = None,
):
    """Helper: build a connector + integration tuple plumbed for CO130
    tests.

    Args:
      integration_param_overrides: full ``configuration`` list passed to
        ``create_integration_object`` — each entry is a YAML param dict
        (must include ``name``; may include ``hidden`` / ``defaultvalue``).
      resolved_pairs: list of (connector_param_name, content_param_name)
        tuples. One ``ResolvedParamMapping`` is created per tuple and
        attached to ``handler[0].resolved_params``.
      capability_id: the id of the single CapabilityData declared in
        capabilities.yaml (also the default handler claim).
      connector_field_ids: list of ConnectorField ids placed inside the
        capability's configurations bucket. Defaults to the
        connector_param_name of every resolved_pairs entry (so coverage
        is "wired up" by default for every resolved mapping).
      handler_capability_id: override what the handler claims (defaults
        to ``capability_id``).

    Returns the parsed Connector with ``handlers[0].related_integration``
    and ``handlers[0].resolved_params`` set.
    """
    claim_id = handler_capability_id or capability_id
    connector = create_connector_object(
        connector_id=connector_id,
        capabilities_data={
            "capabilities": [
                {
                    "id": capability_id,
                    "title": "Test Cap",
                    "description": "Test cap for CO130 coverage tests",
                },
            ],
        },
        handlers=[
            {
                "id": "xsoar-handler",
                "capabilities": [{"id": claim_id}],
            },
        ],
    )

    if connector_field_ids is None:
        connector_field_ids = [pair[0] for pair in resolved_pairs]

    connector.capabilities[0].configurations = [
        FieldGroup(
            fields=[
                ConnectorField(
                    id=fid,
                    title=fid.replace("_", " ").title(),
                    field_type="input",
                )
                for fid in connector_field_ids
            ],
        ),
    ]

    integration = create_integration_object(
        paths=["configuration"],
        values=[integration_param_overrides],
    )

    connector.handlers[0].related_integration = integration
    connector.handlers[0].resolved_params = [
        ResolvedParamMapping(
            connector_param_name=connector_name,
            content_param_name=yaml_name,
            is_serialized=False,
            source_file="capabilities.yaml",
        )
        for connector_name, yaml_name in resolved_pairs
    ]
    return connector


class TestCO130IsEveryIntegrationParamCovered:
    """Tests for CO130 validator: every VISIBLE integration YAML param
    must be covered by a reachable connector field via the handler's
    resolved_params.

    Trigger gate: each XSOAR handler with a resolved
    ``related_integration`` is checked independently. Handlers missing
    an integration are skipped (CO100's concern).

    Coverage semantics:
      - covered = set of ``content_param_name`` for every
        ``resolved_params`` entry whose ``connector_param_name`` is
        reachable from this handler.
      - visible = set of integration YAML param names that are neither
        hidden-on-platform NOR a mirroring param (CO113's
        FORBIDDEN_MIRRORING_FIELDS).
      - uncovered = visible - covered. Non-empty -> ValidationResult.

    Exemptions:
      - ``hidden: true`` and ``hidden: [..., 'platform']`` params are
        exempt.
      - ``mirror_direction`` / ``close_incident`` / ``close_out``
        (FORBIDDEN_MIRRORING_FIELDS) are exempt.
    """

    def test_no_xsoar_handlers_skipped(self):
        """
        Given: A connector whose only handler is a partner handler,
               with an uncovered visible param that WOULD normally fail.
        When:  CO130 runs.
        Then:  No validation errors — the XSOAR-handler gate is not
               met (``connector.xsoar_handlers`` is empty).
        """
        partner_handler = {
            "id": "partner-handler",
            "metadata": {
                "module": "partner",
                "ownership": {
                    "team": "partner-team",
                    "maintainers": ["@partner-dev"],
                },
            },
        }
        connector = create_connector_object(
            connector_id="partner-only", handlers=[partner_handler]
        )
        integration = create_integration_object(
            paths=["configuration"],
            values=[[{"name": "lonely_param", "display": "Lonely"}]],
        )
        connector.handlers[0].related_integration = integration
        connector.handlers[0].resolved_params = []

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_without_related_integration_skipped(self):
        """
        Given: An XSOAR handler with NO resolved related_integration.
        When:  CO130 runs.
        Then:  No validation errors — CO100 handles the missing-
               integration case; CO130 must not pile on.
        """
        connector = create_connector_object()
        assert connector.handlers[0].related_integration is None

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_all_visible_params_covered_passes(self):
        """
        Given: Integration with two visible params (``server``,
               ``port``), and the handler's resolved_params + reachable
               fields cover both.
        When:  CO130 runs.
        Then:  No validation errors.
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[
                {"name": "server", "display": "Server"},
                {"name": "port", "display": "Port"},
            ],
            resolved_pairs=[("server_url", "server"), ("port_field", "port")],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_visible_param_not_covered_fails(self):
        """
        Given: Integration has two visible params (``server``, ``port``)
               but the connector only covers ``server`` — ``port`` has
               no matching resolved_params entry.
        When:  CO130 runs.
        Then:  ValidationResult lists ``port`` as uncovered.
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[
                {"name": "server", "display": "Server"},
                {"name": "port", "display": "Port"},
            ],
            resolved_pairs=[("server_url", "server")],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "'port'" in msg
        # Covered params must NOT appear in the uncovered list.
        assert "'server'" not in msg

    def test_hidden_true_param_not_covered_passes(self):
        """
        Given: Integration has a visible param ``server`` (covered) AND
               a hidden param ``debug`` (NOT covered).
        When:  CO130 runs.
        Then:  No validation errors — ``debug`` is hidden so it is
               exempt from the coverage requirement.
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[
                {"name": "server", "display": "Server"},
                {"name": "debug", "display": "Debug", "hidden": True},
            ],
            resolved_pairs=[("server_url", "server")],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_hidden_list_with_platform_param_not_covered_passes(self):
        """
        Given: A param marked hidden=[..., 'platform'] (hidden in the
               platform UI) is NOT covered.
        When:  CO130 runs.
        Then:  No validation errors — platform-hidden params are
               exempt.
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[
                {"name": "server", "display": "Server"},
                {
                    "name": "legacy_flag",
                    "display": "Legacy",
                    "hidden": ["platform", "xsoar"],
                },
            ],
            resolved_pairs=[("server_url", "server")],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_hidden_list_without_platform_param_uncovered_fails(self):
        """
        Given: A param has ``hidden: ['xsoar_saas']`` — hidden in
               another marketplace but NOT in platform. It is NOT
               covered by the connector.
        When:  CO130 runs.
        Then:  ValidationResult fires — only ``hidden: true`` and
               ``hidden: [..., 'platform']`` are exempted; other hidden
               lists must still be covered because the param is visible
               on the platform.
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[
                {"name": "server", "display": "Server"},
                {
                    "name": "saas_only",
                    "display": "SaaS Only",
                    "hidden": ["xsoar_saas"],
                },
            ],
            resolved_pairs=[("server_url", "server")],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "'saas_only'" in msg

    def test_mirror_direction_param_not_covered_passes(self):
        """
        Given: An integration with the canonical mirroring param
               ``mirror_direction`` (FORBIDDEN_MIRRORING_FIELDS) that is
               NOT covered by the connector.
        When:  CO130 runs.
        Then:  No validation errors — mirroring params are exempt per
               CO113's FORBIDDEN_MIRRORING_FIELDS set (re-imported by
               CO130 for source-of-truth alignment).
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[
                {"name": "server", "display": "Server"},
                {"name": "mirror_direction", "display": "Mirror Direction"},
            ],
            resolved_pairs=[("server_url", "server")],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_resolved_params_unreachable_field_does_NOT_count(self):
        """
        Given: ``resolved_params`` declares a mapping
               ``foo_field -> foo`` but ``foo_field`` is NOT in the
               handler-reachable field set (the connector has no field
               with id ``foo_field`` in any reachable bucket).
        When:  CO130 runs.
        Then:  ValidationResult fires because ``foo`` is uncovered
               (resolved_params alone is insufficient — the field must
               actually be present in a reachable bucket for the
               mapping to count as coverage).
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[{"name": "foo", "display": "Foo"}],
            resolved_pairs=[("foo_field", "foo")],
            # Override field ids: NO field has id 'foo_field' in the
            # reachable bucket. Coverage is therefore not satisfied
            # even though resolved_params says it is.
            connector_field_ids=["unrelated_field"],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "'foo'" in results[0].message

    def test_multiple_uncovered_params_one_handler_grouped(self):
        """
        Given: A handler whose integration has THREE uncovered visible
               params (``a``, ``b``, ``c``).
        When:  CO130 runs.
        Then:  A SINGLE ValidationResult per connector lists all three
               uncovered names in one message (CO109-style grouping).
        """
        connector = _build_connector_with_coverage_setup(
            integration_param_overrides=[
                {"name": "a"},
                {"name": "b"},
                {"name": "c"},
            ],
            resolved_pairs=[],
            connector_field_ids=[],
        )

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        # Sorted-determinism is guaranteed by _check_handler iterating
        # sorted(uncovered).
        assert "'a'" in msg
        assert "'b'" in msg
        assert "'c'" in msg
        # All three lines under the same handler header.
        assert msg.count("handler 'xsoar-handler'") == 3

    def test_multiple_handlers_independent_coverage(self):
        """
        Given: A connector with TWO XSOAR handlers, each pointing at a
               different integration. Handler A fully covers its
               integration; Handler B has an uncovered visible param.
        When:  CO130 runs.
        Then:  A SINGLE ValidationResult per connector reports ONLY
               Handler B's uncovered param. Handler A's complete
               coverage does NOT contribute (per-handler scope, Q4=a).
        """
        # Two XSOAR handlers, each pointed at its own integration.
        connector = create_connector_object(
            connector_id="multi-handler",
            capabilities_data={
                "capabilities": [
                    {
                        "id": "cap-a",
                        "title": "Cap A",
                        "description": "Cap A",
                    },
                    {
                        "id": "cap-b",
                        "title": "Cap B",
                        "description": "Cap B",
                    },
                ],
            },
            handlers=[
                {
                    "id": "xsoar-handler-a",
                    "capabilities": [{"id": "cap-a"}],
                },
                {
                    "id": "xsoar-handler-b",
                    "capabilities": [{"id": "cap-b"}],
                },
            ],
        )

        # Wire up per-capability configurations so reachable fields
        # match what resolved_params says.
        connector.capabilities[0].configurations = [
            FieldGroup(
                fields=[
                    ConnectorField(
                        id="server_a",
                        title="Server A",
                        field_type="input",
                    )
                ],
            ),
        ]
        connector.capabilities[1].configurations = [
            FieldGroup(
                fields=[
                    ConnectorField(
                        id="server_b",
                        title="Server B",
                        field_type="input",
                    )
                ],
            ),
        ]

        # Handler A: fully covers its integration's only visible param.
        integration_a = create_integration_object(
            paths=["configuration"],
            values=[[{"name": "yaml_a", "display": "YAML A"}]],
        )
        connector.handlers[0].related_integration = integration_a
        connector.handlers[0].resolved_params = [
            ResolvedParamMapping(
                connector_param_name="server_a",
                content_param_name="yaml_a",
                is_serialized=False,
                source_file="capabilities.yaml",
            )
        ]

        # Handler B: integration has TWO visible params, only one covered.
        integration_b = create_integration_object(
            paths=["configuration"],
            values=[
                [
                    {"name": "yaml_b", "display": "YAML B"},
                    {"name": "uncovered_b", "display": "Uncovered B"},
                ]
            ],
        )
        connector.handlers[1].related_integration = integration_b
        connector.handlers[1].resolved_params = [
            ResolvedParamMapping(
                connector_param_name="server_b",
                content_param_name="yaml_b",
                is_serialized=False,
                source_file="capabilities.yaml",
            )
        ]

        validator = IsEveryIntegrationParamCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        # Handler B's uncovered param is reported.
        assert "xsoar-handler-b" in msg
        assert "'uncovered_b'" in msg
        # Handler A has no issues — must not appear in the message.
        assert "xsoar-handler-a" not in msg
        assert "'yaml_a'" not in msg
