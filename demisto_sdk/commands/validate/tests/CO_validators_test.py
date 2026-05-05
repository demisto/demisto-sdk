"""Tests for CO (Connector) validators — CO100, CO101, CO112, and CO113."""

from unittest.mock import MagicMock

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectorField,
    FieldGroup,
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
from demisto_sdk.commands.validate.validators.CO_validators.CO112_is_matching_license import (
    IsMatchingLicenseValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO113_is_mirroring_omitted import (
    IsMirroringOmittedValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO114_is_handler_ownership_fields_align import (
    IsHandlerOwnershipFieldsAlignValidator,
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
