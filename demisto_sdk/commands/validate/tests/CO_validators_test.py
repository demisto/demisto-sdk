"""Tests for CO (Connector) validators - CO100-CO106, CO164."""

import copy
from types import SimpleNamespace

import pytest

from demisto_sdk.commands.common.constants import (
    ALL_SUPPORTED_MODULES,
    MarketplaceVersions,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_connector_object,
    create_integration_object,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO100_is_connector_ownership_fields_align import (
    IsConnectorOwnershipFieldsAlignValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO101_is_author_image_present import (
    IsAuthorImagePresentValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO102_is_publisher_valid import (
    IsPublisherValidValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO103_is_connector_id_title_aligned import (
    IsConnectorIdTitleAlignedValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO104_is_vendor_matches_provider import (
    IsVendorMatchesProviderValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO105_is_categories_union_superset_of_packs import (
    IsCategoriesUnionSupersetOfPacksValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO106_is_tags_union_superset_of_packs import (
    IsTagsUnionSupersetOfPacksValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO107_is_valid_capabilities_metadata import (
    IsValidCapabilitiesMetadataValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO109_is_instance_name_template_valid import (
    EXPECTED_INSTANCE_NAME_FIELD,
    IsInstanceNameTemplateValidValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO110_is_capability_name_valid import (
    IsCapabilityNameValidValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO111_grouped_connector_xsoar_only_capabilities import (
    GroupedConnectorXSOAROnlyCapabilitiesValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO112_has_sub_capability import (
    HasSubCapabilityValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO113_is_sub_capability_id_derived import (
    IsSubCapabilityIdDerivedValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO114_is_matching_license import (
    IsMatchingLicenseValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO116_is_connector_matches_integration_flags import (
    IsConnectorMatchesIntegrationFlagsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO117_is_capability_title_valid import (
    IsCapabilityTitleValidValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO118_is_valid_connection_metadata import (
    IsValidConnectionMetadataValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO119_no_connection_general_configurations import (
    NoConnectionGeneralConfigurationsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO120_is_proxy_and_insecure_exists import (
    IsProxyAndInsecureExistsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO121_is_valid_interpolation import (
    IsValidInterpolationValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO122_is_valid_viewgroup import (
    IsValidViewgroupValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO123_is_profile_fields_covered import (
    IsProfileFieldsCoveredValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO124_is_valid_grouped_connector_auth import (
    IsValidGroupedConnectorAuthValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO125_is_auth_profile_has_engine import (
    IsAuthProfileHasEngineValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO126_is_valid_engine_params import (
    IsValidEngineParamsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO129_is_valid_configurations_metadata import (
    IsValidConfigurationsMetadataValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO155_is_handler_module_xsoar import (
    IsHandlerModuleXsoarValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO156_is_handler_ownership_fields_align import (
    IsHandlerOwnershipFieldsAlignValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO159_is_handler_has_valid_test_connection import (
    IsHandlerHasValidTestConnectionValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO161_is_fetch_capabilities_contain_actions import (
    IsFetchCapabilitiesContainActionsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO162_is_valid_workloads import (
    IsValidWorkloadsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO164_is_matching_integration_exist import (
    IsMatchingIntegrationExistValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO165_is_handler_matching_pack_exist import (
    IsHandlerMatchingPackExistValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO170_is_handler_migration_constants import (
    IsHandlerMigrationConstantsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO171_is_collection_sub_capability_fetch_flag_valid import (
    IsCollectionSubCapabilityFetchFlagValidValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO172_is_fetch_flag_gated_on_own_sub_capability import (
    IsFetchFlagGatedOnOwnSubCapabilityValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO175_no_removed_connector_params import (
    NoRemovedConnectorParamsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO176_no_change_connector_ids import (
    NoChangeConnectorIDsValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO179_no_param_required_tightened import (
    NoParamRequiredTightenedValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO181_no_removed_auth_option import (
    NoRemovedAuthOptionValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO183_no_grouped_flag_flipped import (
    NoGroupedFlagFlippedValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO190_no_reserved_param_names import (
    NoReservedParamNamesValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO194_is_sub_capability_title_derived import (
    IsSubCapabilityTitleDerivedValidator,
)

VALID_CONNECTION_DESCRIPTION = (
    "Enter the credentials to securely authorize the connection"
)


def _stub_integration(provider=None, categories=None, tags=None):
    """Build a lightweight integration-like stub for connector validators.

    The pack-aware validators (CO104/CO105/CO106) only read
    ``related_integration.provider`` and ``related_integration.in_pack``
    (``.categories`` / ``.tags``), so a SimpleNamespace suffices and avoids
    building a full Integration + Pack graph fixture.
    """
    in_pack = None
    if categories is not None or tags is not None:
        in_pack = SimpleNamespace(
            categories=categories or [],
            tags=tags or [],
        )
    return SimpleNamespace(provider=provider, in_pack=in_pack)


# ============================================================
# CO164 - IsMatchingIntegrationExistValidator
# ============================================================


class TestCO164IsMatchingIntegrationExist:
    """Tests for CO164 validator: every XSOAR handler must have a resolved integration."""

    def test_valid_handler_with_matched_integration(self):
        """
        Given: A connector whose XSOAR handler has related_integration set.
        When: CO164 runs.
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
        When: CO164 runs.
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
        When: CO164 runs.
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
        When: CO164 runs.
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

    def test_handler_resolved_but_label_drifted_from_yml_id_fails(self):
        """
        Given: A connector whose XSOAR handler was resolved (via graph
               fallback) to an integration, but the ``xsoar-integration-id``
               label does NOT equal the integration's YML ``object_id``
               verbatim (e.g. slugified handler label, canonical YML id
               with spaces/mixed case).
        When: CO164 runs.
        Then: A validation error is returned - this invariant is what lets
              CO122/CO139 compare against ``integration.object_id`` verbatim.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-drifted",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "palo-alto-networks-threat-vault-v2",
                        },
                    },
                },
            ]
        )
        integration = create_integration_object()
        # object_id is the canonical YML id (with spaces / mixed case).
        integration.object_id = "Palo Alto Networks Threat Vault v2"
        connector.handlers[0].related_integration = integration

        validator = IsMatchingIntegrationExistValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "palo-alto-networks-threat-vault-v2" in msg
        assert "Palo Alto Networks Threat Vault v2" in msg
        assert "match verbatim" in msg

    def test_multiple_connectors_independent_results(self):
        """
        Given: Two connectors - one valid (handler linked), one invalid (unresolved).
        When: CO164 runs on both.
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
# CO100 - IsConnectorOwnershipFieldsAlignValidator
# ============================================================


class TestCO100IsConnectorOwnershipFieldsAlign:
    """Tests for CO100: maintainers must contain '@xsoar-content'."""

    def test_valid_maintainers_contains_xsoar_content(self):
        """
        Given: A connector whose ownership.maintainers contains '@xsoar-content'.
        When: CO100 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={
                "metadata": {"ownership": {"maintainers": ["@xsoar-content"]}}
            }
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_maintainers_missing_xsoar_content(self):
        """
        Given: A connector whose ownership.maintainers lacks '@xsoar-content'.
        When: CO100 runs.
        Then: A validation error is returned.
        """
        connector = create_connector_object(
            connector_overrides={
                "metadata": {"ownership": {"maintainers": ["@someone-else"]}}
            }
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "@xsoar-content" in results[0].message

    def test_invalid_empty_maintainers(self):
        """
        Given: A connector whose ownership.maintainers is empty.
        When: CO100 runs.
        Then: A validation error is returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"ownership": {"maintainers": []}}}
        )

        validator = IsConnectorOwnershipFieldsAlignValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1


# ============================================================
# CO101 - IsAuthorImagePresentValidator
# ============================================================


class TestCO101IsAuthorImagePresent:
    """Tests for CO101: metadata.author_image must be present and non-empty."""

    def test_valid_author_image_present(self):
        """
        Given: A connector with a non-empty metadata.author_image.
        When: CO101 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"author_image": "test-connector.png"}}
        )

        validator = IsAuthorImagePresentValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_author_image_missing(self):
        """
        Given: A connector with no metadata.author_image (default template).
        When: CO101 runs.
        Then: A validation error is returned.
        """
        connector = create_connector_object()
        assert not connector.connector_metadata.author_image

        validator = IsAuthorImagePresentValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "author_image" in results[0].message

    def test_invalid_author_image_empty_string(self):
        """
        Given: A connector with an empty/whitespace metadata.author_image.
        When: CO101 runs.
        Then: A validation error is returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"author_image": "   "}}
        )

        validator = IsAuthorImagePresentValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1


# ============================================================
# CO102 - IsPublisherValidValidator
# ============================================================


class TestCO102IsPublisherValid:
    """Tests for CO102: metadata.publisher must be 'Palo Alto Networks'."""

    def test_valid_publisher(self):
        """
        Given: A connector whose publisher is 'Palo Alto Networks'.
        When: CO102 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"publisher": "Palo Alto Networks"}}
        )

        validator = IsPublisherValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_publisher(self):
        """
        Given: A connector whose publisher is not 'Palo Alto Networks'.
        When: CO102 runs.
        Then: A validation error is returned mentioning the expected publisher.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"publisher": "Some Other Vendor"}}
        )

        validator = IsPublisherValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "Palo Alto Networks" in results[0].message
        assert "Some Other Vendor" in results[0].message


# ============================================================
# CO103 - IsConnectorIdTitleAlignedValidator
# ============================================================


class TestCO103IsConnectorIdTitleAligned:
    """Tests for CO103: slugify(title) must equal id."""

    def test_valid_id_matches_slugified_title(self):
        """
        Given: A connector whose id equals slugify(title).
        When: CO103 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_id="cisco-security",
            connector_overrides={"metadata": {"title": "Cisco Security"}},
        )

        validator = IsConnectorIdTitleAlignedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_id_does_not_match_title(self):
        """
        Given: A connector whose id does not match slugify(title).
        When: CO103 runs.
        Then: A validation error is returned with the expected id.
        """
        connector = create_connector_object(
            connector_id="wrong-id",
            connector_overrides={"metadata": {"title": "Cisco Security"}},
        )

        validator = IsConnectorIdTitleAlignedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "cisco-security" in results[0].message

    def test_valid_id_with_dash_collapse(self):
        """
        Given: A title containing ' - ' which slugifies to a single dash.
        When: CO103 runs.
        Then: The connector whose id matches the collapsed slug is valid.
        """
        connector = create_connector_object(
            connector_id="aws-s3",
            connector_overrides={"metadata": {"title": "AWS - S3"}},
        )

        validator = IsConnectorIdTitleAlignedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_valid_id_with_parentheses_stripped(self):
        """
        Given: A title containing parentheses, which are stripped and the
               surrounding dash-run collapsed (e.g. real UCP connector
               "Trellix Endpoint (HX)" -> "trellix-endpoint-hx").
        When: CO103 runs.
        Then: The connector whose id matches the stripped/collapsed slug is
              valid.
        """
        connector = create_connector_object(
            connector_id="trellix-endpoint-hx",
            connector_overrides={"metadata": {"title": "Trellix Endpoint (HX)"}},
        )

        validator = IsConnectorIdTitleAlignedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_id_keeps_parentheses(self):
        """
        Given: A connector id that (incorrectly) keeps the parentheses from the
               title instead of stripping them.
        When: CO103 runs.
        Then: A validation error with the expected stripped id is returned.
        """
        connector = create_connector_object(
            connector_id="saas-security-(aperture)",
            connector_overrides={"metadata": {"title": "SaaS Security (Aperture)"}},
        )

        validator = IsConnectorIdTitleAlignedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "saas-security-aperture" in results[0].message


# ============================================================
# CO104 - IsVendorMatchesProviderValidator
# ============================================================


class TestCO104IsVendorMatchesProvider:
    """Tests for CO104: vendor must match linked integration(s) provider."""

    def test_valid_vendor_matches_provider(self):
        """
        Given: A connector whose vendor matches its handler's integration provider.
        When: CO104 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"vendor": "TestProvider"}}
        )
        connector.handlers[0].related_integration = _stub_integration(
            provider="TestProvider"
        )

        validator = IsVendorMatchesProviderValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_vendor_mismatch(self):
        """
        Given: A connector whose vendor differs from the integration provider.
        When: CO104 runs.
        Then: A validation error is returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"vendor": "WrongVendor"}}
        )
        connector.handlers[0].related_integration = _stub_integration(
            provider="TestProvider"
        )

        validator = IsVendorMatchesProviderValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "WrongVendor" in results[0].message
        assert "TestProvider" in results[0].message

    def test_invalid_providers_differ_across_handlers(self):
        """
        Given: A connector whose two handlers reference integrations with
               differing providers.
        When: CO104 runs.
        Then: A validation error is returned flagging the differing providers.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"vendor": "ProviderA"}},
            handlers=[
                {
                    "id": "xsoar-a",
                    "triggering": {"labels": {"xsoar-integration-id": "A"}},
                },
                {
                    "id": "xsoar-b",
                    "triggering": {"labels": {"xsoar-integration-id": "B"}},
                },
            ],
        )
        connector.handlers[0].related_integration = _stub_integration(
            provider="ProviderA"
        )
        connector.handlers[1].related_integration = _stub_integration(
            provider="ProviderB"
        )

        validator = IsVendorMatchesProviderValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "differing" in results[0].message

    def test_no_resolved_integration_skipped(self):
        """
        Given: A connector whose handler has no resolved integration.
        When: CO104 runs.
        Then: No validation errors (nothing to compare against).
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"vendor": "Whatever"}}
        )
        # related_integration is None by default.

        validator = IsVendorMatchesProviderValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO105 - IsCategoriesUnionSupersetOfPacksValidator
# ============================================================


class TestCO105IsCategoriesUnionSupersetOfPacks:
    """Tests for CO105: categories must contain the union of parent-pack categories."""

    def test_valid_categories_superset(self):
        """
        Given: A connector whose categories cover every parent-pack category.
        When: CO105 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={
                "metadata": {"categories": ["Network Security", "Analytics & SIEM"]}
            }
        )
        connector.handlers[0].related_integration = _stub_integration(
            categories=["Network Security"]
        )

        validator = IsCategoriesUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_missing_category(self):
        """
        Given: A connector missing a category declared by its parent pack.
        When: CO105 runs.
        Then: A validation error listing the missing category is returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"categories": ["Analytics & SIEM"]}}
        )
        connector.handlers[0].related_integration = _stub_integration(
            categories=["Network Security"]
        )

        validator = IsCategoriesUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "Network Security" in results[0].message

    def test_union_across_multiple_handlers(self):
        """
        Given: Two handlers whose parent packs contribute different categories.
        When: CO105 runs.
        Then: The connector must contain the union; a missing one is flagged.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"categories": ["Cat A"]}},
            handlers=[
                {
                    "id": "xsoar-a",
                    "triggering": {"labels": {"xsoar-integration-id": "A"}},
                },
                {
                    "id": "xsoar-b",
                    "triggering": {"labels": {"xsoar-integration-id": "B"}},
                },
            ],
        )
        connector.handlers[0].related_integration = _stub_integration(
            categories=["Cat A"]
        )
        connector.handlers[1].related_integration = _stub_integration(
            categories=["Cat B"]
        )

        validator = IsCategoriesUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "Cat B" in results[0].message

    def test_no_pack_categories_skipped(self):
        """
        Given: A connector whose linked integrations declare no categories.
        When: CO105 runs.
        Then: No validation errors (nothing to compare against).
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _stub_integration(categories=[])

        validator = IsCategoriesUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_category_casing_difference_not_flagged(self):
        """
        Given: A parent-pack category that is capital-cased by the pack parser
               ("Messaging And Conferencing") while the connector declares the
               same category with lowercase joiners ("Messaging and
               Conferencing") -- the exact zoom scenario.
        When: CO105 runs.
        Then: No validation error is returned; the comparison is
              case-insensitive so a mere casing difference is not a mismatch.
        """
        connector = create_connector_object(
            connector_overrides={
                "metadata": {
                    "categories": [
                        "Messaging and Conferencing",
                        "Data Enrichment & Threat Intelligence",
                    ]
                }
            }
        )
        # Pack side arrives capital-cased (as Pack.categories does in prod).
        connector.handlers[0].related_integration = _stub_integration(
            categories=[
                "Messaging And Conferencing",
                "Data Enrichment & Threat Intelligence",
            ]
        )

        validator = IsCategoriesUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_genuinely_missing_category_still_flagged_despite_casing(self):
        """
        Given: A connector that matches one pack category only by casing but is
               genuinely missing a second, different pack category.
        When: CO105 runs.
        Then: The genuinely missing category is still flagged (the case-
              insensitive fix must not suppress real misses).
        """
        connector = create_connector_object(
            connector_overrides={
                "metadata": {"categories": ["messaging and conferencing"]}
            }
        )
        connector.handlers[0].related_integration = _stub_integration(
            categories=["Messaging And Conferencing", "Network Security"]
        )

        validator = IsCategoriesUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        # The genuinely-missing category is flagged.
        missing_part = results[0].message.split("Parent-pack categories union")[0]
        assert "Network Security" in missing_part
        # The casing-only match must NOT be reported as missing (it may still
        # appear in the informational union list, so only check the missing part).
        assert "Messaging" not in missing_part


# ============================================================
# CO106 - IsTagsUnionSupersetOfPacksValidator
# ============================================================


class TestCO106IsTagsUnionSupersetOfPacks:
    """Tests for CO106: tags must contain the union of parent-pack tags."""

    def test_valid_tags_superset(self):
        """
        Given: A connector whose tags cover every parent-pack tag.
        When: CO106 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"tags": ["Forensics", "Endpoint"]}}
        )
        connector.handlers[0].related_integration = _stub_integration(
            tags=["Forensics"]
        )

        validator = IsTagsUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_missing_tag(self):
        """
        Given: A connector missing a tag declared by its parent pack.
        When: CO106 runs.
        Then: A validation error listing the missing tag is returned.
        """
        connector = create_connector_object(
            connector_overrides={"metadata": {"tags": ["Endpoint"]}}
        )
        connector.handlers[0].related_integration = _stub_integration(
            tags=["Forensics"]
        )

        validator = IsTagsUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "Forensics" in results[0].message

    def test_no_pack_tags_skipped(self):
        """
        Given: A connector whose linked integrations declare no tags.
        When: CO106 runs.
        Then: No validation errors (nothing to compare against).
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _stub_integration(tags=[])

        validator = IsTagsUnionSupersetOfPacksValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO107 - IsValidCapabilitiesMetadataValidator
# ============================================================

VALID_CAPABILITIES_TITLE = "Capabilities"
VALID_CAPABILITIES_DESCRIPTION = "Name and configure the instance capabilities"


class TestCO107IsValidCapabilitiesMetadata:
    """Tests for CO107: capabilities.yaml metadata title/description/help."""

    def test_valid_capabilities_metadata_non_grouped(self):
        """
        Given: A non-grouped connector whose capabilities metadata has the
               correct title and description and no help.
        When: CO107 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            capabilities_data={
                "metadata": {
                    "title": VALID_CAPABILITIES_TITLE,
                    "description": VALID_CAPABILITIES_DESCRIPTION,
                }
            }
        )

        validator = IsValidCapabilitiesMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_valid_capabilities_metadata_grouped(self):
        """
        Given: A grouped connector whose capabilities metadata has the correct
               title and description and no help.
        When: CO107 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            capabilities_data={
                "metadata": {
                    "title": VALID_CAPABILITIES_TITLE,
                    "description": VALID_CAPABILITIES_DESCRIPTION,
                }
            },
        )

        validator = IsValidCapabilitiesMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_title(self):
        """
        Given: A connector whose capabilities metadata.title is not
               'Capabilities'.
        When: CO107 runs.
        Then: A validation error mentioning the title is returned.
        """
        connector = create_connector_object(
            capabilities_data={
                "metadata": {
                    "title": "Wrong Title",
                    "description": VALID_CAPABILITIES_DESCRIPTION,
                }
            }
        )

        validator = IsValidCapabilitiesMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "metadata.title" in results[0].message

    def test_invalid_description(self):
        """
        Given: A connector whose capabilities metadata.description is wrong.
        When: CO107 runs.
        Then: A validation error mentioning the description is returned.
        """
        connector = create_connector_object(
            capabilities_data={
                "metadata": {
                    "title": VALID_CAPABILITIES_TITLE,
                    "description": "Wrong description",
                }
            }
        )

        validator = IsValidCapabilitiesMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "metadata.description" in results[0].message

    def test_help_present_on_grouped_is_flagged(self):
        """
        Given: A grouped connector whose capabilities metadata declares help.
        When: CO107 runs.
        Then: A validation error mentioning help is returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            capabilities_data={
                "metadata": {
                    "title": VALID_CAPABILITIES_TITLE,
                    "description": VALID_CAPABILITIES_DESCRIPTION,
                    "help": "some help text",
                }
            },
        )

        validator = IsValidCapabilitiesMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "metadata.help" in results[0].message

    def test_help_present_on_non_grouped_is_ignored(self):
        """
        Given: A non-grouped connector whose capabilities metadata declares
               help.
        When: CO107 runs.
        Then: No validation errors are returned - help is only checked for
              grouped connectors.
        """
        connector = create_connector_object(
            capabilities_data={
                "metadata": {
                    "title": VALID_CAPABILITIES_TITLE,
                    "description": VALID_CAPABILITIES_DESCRIPTION,
                    "help": "some help text",
                }
            }
        )

        validator = IsValidCapabilitiesMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_all_invalid_combined_grouped(self):
        """
        Given: A grouped connector whose capabilities metadata is wrong on all
               counts (title, description, and a present help).
        When: CO107 runs.
        Then: A single ValidationResult reports all three problems.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            capabilities_data={
                "metadata": {
                    "title": "Nope",
                    "description": "Nope",
                    "help": "some help text",
                }
            },
        )

        validator = IsValidCapabilitiesMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "metadata.title" in msg
        assert "metadata.description" in msg
        assert "metadata.help" in msg


# ============================================================
# CO109 - IsInstanceNameTemplateValidValidator
# ============================================================


def _general_configs_with_instance_name(instance_name_field):
    """Build a capabilities_data override placing the given instance_name field
    inside general_configurations.configurations."""
    return {
        "general_configurations": {
            "description": "General configurations for all capabilities",
            "configurations": [{"fields": [instance_name_field]}],
        }
    }


class TestCO109IsInstanceNameTemplateValid:
    """Tests for CO109: capabilities.yaml must include the verbatim
    instance_name field template."""

    def test_valid_instance_name_template(self):
        """
        Given: A connector whose capabilities general_configurations includes
               the exact verbatim instance_name field template.
        When: CO109 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            capabilities_data=_general_configs_with_instance_name(
                copy.deepcopy(EXPECTED_INSTANCE_NAME_FIELD)
            )
        )

        validator = IsInstanceNameTemplateValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_instance_name_field_missing(self):
        """
        Given: A connector whose capabilities general_configurations has no
               instance_name field (the default template).
        When: CO109 runs.
        Then: A validation error noting the missing field is returned.
        """
        connector = create_connector_object()

        validator = IsInstanceNameTemplateValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "no instance_name field found" in results[0].message

    def test_instance_name_template_mismatch(self):
        """
        Given: A connector whose instance_name field deviates from the verbatim
               template (changed title).
        When: CO109 runs.
        Then: A validation error noting the mismatch is returned.
        """
        mutated = copy.deepcopy(EXPECTED_INSTANCE_NAME_FIELD)
        mutated["title"] = "Instance Name Changed"
        connector = create_connector_object(
            capabilities_data=_general_configs_with_instance_name(mutated)
        )

        validator = IsInstanceNameTemplateValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "does not match the required verbatim template" in results[0].message

    def test_instance_name_template_extra_key_flagged(self):
        """
        Given: A connector whose instance_name field carries an extra key not in
               the verbatim template.
        When: CO109 runs.
        Then: A validation error noting the mismatch is returned (exact match).
        """
        mutated = copy.deepcopy(EXPECTED_INSTANCE_NAME_FIELD)
        mutated["unexpected_key"] = "surprise"
        connector = create_connector_object(
            capabilities_data=_general_configs_with_instance_name(mutated)
        )

        validator = IsInstanceNameTemplateValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "does not match the required verbatim template" in results[0].message


# ============================================================
# CO110 - IsCapabilityNameValidValidator
# ============================================================


def _capability(cap_id, sub_ids=None):
    """Build a minimal capabilities.yaml capability entry."""
    cap = {
        "id": cap_id,
        "title": cap_id,
        "description": "desc",
        "default_enabled": False,
        "required": False,
    }
    if sub_ids:
        cap["sub_capabilities"] = [
            {
                "id": sub_id,
                "title": sub_id,
                "default_enabled": False,
                "required": False,
            }
            for sub_id in sub_ids
        ]
    return cap


def _xsoar_handler_subscribing_to(*capability_ids):
    """Build a handler override (XSOAR by default) subscribing to the given
    capability/sub-capability ids."""
    return {
        "capabilities": [
            {
                "id": cap_id,
                "auth_options": [{"id": "test-auth", "workloads": ["test-workload"]}],
            }
            for cap_id in capability_ids
        ]
    }


class TestCO110IsCapabilityNameValid:
    """Tests for CO110: XSOAR-owned capability/sub-capability ids must be one of
    the allowed ids."""

    def test_valid_parent_capability(self):
        """
        Given: An XSOAR handler subscribing to a capability whose id is an
               allowed capability id.
        When: CO110 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            capabilities_data={"capabilities": [_capability("fetch-issues")]},
            handlers=[_xsoar_handler_subscribing_to("fetch-issues")],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_parent_capability(self):
        """
        Given: An XSOAR handler subscribing to a capability whose id is NOT an
               allowed capability id.
        When: CO110 runs.
        Then: A validation error listing the invalid id is returned.
        """
        connector = create_connector_object(
            capabilities_data={"capabilities": [_capability("not-a-capability")]},
            handlers=[_xsoar_handler_subscribing_to("not-a-capability")],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "not-a-capability" in results[0].message

    def test_non_xsoar_capability_skipped(self):
        """
        Given: A non-XSOAR handler subscribing to a capability with an invalid
               id (handler module is not xsoar).
        When: CO110 runs.
        Then: No validation errors are returned - non-XSOAR capabilities are
              skipped.
        """
        connector = create_connector_object(
            capabilities_data={"capabilities": [_capability("not-a-capability")]},
            handlers=[
                {
                    "metadata": {"module": "cwp", "ownership": {"team": "cwp"}},
                    "capabilities": [
                        {
                            "id": "not-a-capability",
                            "auth_options": [
                                {"id": "test-auth", "workloads": ["test-workload"]}
                            ],
                        }
                    ],
                }
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_valid_sub_capability_base_prefix(self):
        """
        Given: An XSOAR handler subscribing to a sub-capability whose base
               prefix is an allowed capability id.
        When: CO110 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    _capability("fetch-issues", sub_ids=["fetch-issues_myint"])
                ]
            },
            handlers=[_xsoar_handler_subscribing_to("fetch-issues_myint")],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_sub_capability_base_prefix(self):
        """
        Given: An XSOAR handler subscribing to a sub-capability whose base
               prefix is NOT an allowed capability id.
        When: CO110 runs.
        Then: A validation error listing the invalid sub-capability id is
              returned.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    _capability("fetch-issues", sub_ids=["bogus-base_myint"])
                ]
            },
            handlers=[
                _xsoar_handler_subscribing_to("fetch-issues", "bogus-base_myint")
            ],
        )

        validator = IsCapabilityNameValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "bogus-base_myint" in results[0].message


# ============================================================
# CO111 - GroupedConnectorXSOAROnlyCapabilitiesValidator
# ============================================================


class TestCO111GroupedConnectorXSOAROnlyCapabilities:
    """Tests for CO111: a grouped connector may only contain XSOAR-owned
    handlers/capabilities."""

    def test_grouped_all_xsoar_handlers_valid(self):
        """
        Given: A grouped connector whose handlers are all XSOAR-owned.
        When: CO111 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )

        validator = GroupedConnectorXSOAROnlyCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_grouped_non_xsoar_handler_flagged(self):
        """
        Given: A grouped connector with a non-XSOAR handler (module != xsoar).
        When: CO111 runs.
        Then: A validation error listing the non-XSOAR handler is returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            handlers=[
                {
                    "id": "cwp-handler",
                    "metadata": {"module": "cwp", "ownership": {"team": "cwp"}},
                }
            ],
        )

        validator = GroupedConnectorXSOAROnlyCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "cwp-handler" in results[0].message

    def test_non_grouped_short_circuits(self):
        """
        Given: A non-grouped connector with a non-XSOAR handler.
        When: CO111 runs.
        Then: No validation errors are returned - CO111 is grouped-only.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "cwp-handler",
                    "metadata": {"module": "cwp", "ownership": {"team": "cwp"}},
                }
            ],
        )

        validator = GroupedConnectorXSOAROnlyCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO112 - HasSubCapabilityValidator
# ============================================================


class TestCO112HasSubCapability:
    """Tests for CO112: each capability in a grouped connector must declare at
    least one sub-capability."""

    def test_grouped_capability_with_sub_capability_valid(self):
        """
        Given: A grouped connector whose capability declares a sub-capability.
        When: CO112 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            capabilities_data={
                "capabilities": [
                    _capability("fetch-issues", sub_ids=["fetch-issues_myint"])
                ]
            },
        )

        validator = HasSubCapabilityValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_grouped_capability_without_sub_capability_flagged(self):
        """
        Given: A grouped connector whose capability has no sub-capabilities.
        When: CO112 runs.
        Then: A validation error listing that capability is returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            capabilities_data={"capabilities": [_capability("fetch-issues")]},
        )

        validator = HasSubCapabilityValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "fetch-issues" in results[0].message

    def test_non_grouped_short_circuits(self):
        """
        Given: A non-grouped connector whose capability has no sub-capabilities.
        When: CO112 runs.
        Then: No validation errors are returned - CO112 is grouped-only.
        """
        connector = create_connector_object(
            capabilities_data={"capabilities": [_capability("fetch-issues")]},
        )

        validator = HasSubCapabilityValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO113 - IsSubCapabilityIdDerivedValidator
# ============================================================


def _grouped_connector_with_sub_capability(sub_id, sub_title):
    """Build a grouped connector whose 'fetch-issues' capability has one
    sub-capability (sub_id/sub_title), with an XSOAR handler subscribing to it
    and a resolved integration whose display_name is 'My Integration' and
    xsoar-integration-id is 'MyInt' (-> normalized 'myint')."""
    connector = create_connector_object(
        connector_overrides={"settings": {"grouped": True}},
        capabilities_data={
            "capabilities": [
                {
                    "id": "fetch-issues",
                    "title": "Fetch Issues",
                    "description": "desc",
                    "default_enabled": False,
                    "required": False,
                    "sub_capabilities": [
                        {
                            "id": sub_id,
                            "title": sub_title,
                            "default_enabled": False,
                            "required": False,
                        }
                    ],
                }
            ]
        },
        handlers=[
            {
                "id": "xsoar-myint",
                "triggering": {
                    "type": "PUB_SUB",
                    "labels": {
                        "xsoar-integration-id": "MyInt",
                        "xsoar-pack-id": "MyPack",
                    },
                },
                "capabilities": [
                    {
                        "id": sub_id,
                        "auth_options": [
                            {"id": "test-auth", "workloads": ["test-workload"]}
                        ],
                    }
                ],
            }
        ],
    )
    connector.handlers[0].related_integration = SimpleNamespace(
        display_name="My Integration"
    )
    return connector


class TestCO113IsSubCapabilityIdDerived:
    """Tests for CO113: sub-capability id must be
    '<capability_id>_<normalized_integration_id>'.

    Title correctness lives in CO194 (not this validator). CO113 is
    scoped to newly-added connectors via ``expected_git_statuses`` at the
    class level; the tests below drive ``obtain_invalid_content_items``
    directly to exercise the pure logic — the git-status gate is applied
    by the base ``BaseValidator.should_run`` path and is verified in a
    separate test.
    """

    def test_valid_sub_capability_id(self):
        """
        Given: A grouped connector whose sub-capability id is correctly
               derived (mismatched title is intentionally ignored — CO194 owns
               titles).
        When: CO113 runs.
        Then: No validation errors are returned.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Wrong Title But Ignored"
        )

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_sub_capability_id(self):
        """
        Given: A grouped connector whose sub-capability id is not derived from
               the parent capability + normalized integration id.
        When: CO113 runs.
        Then: A validation error naming the expected id is returned.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_wrong", "My Integration"
        )

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "fetch-issues_myint" in results[0].message

    def test_title_mismatch_is_not_flagged(self):
        """
        Given: A grouped connector whose sub-capability id is correct but
               whose title does not match the integration display name.
        When: CO113 runs.
        Then: No validation errors are returned — title checks now live in
              CO194.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Some Other Title"
        )

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_unresolved_integration_does_not_fail_id_check(self):
        """
        Given: A grouped connector whose sub-capability id is correct and
               whose backing integration didn't resolve (no content graph).
        When: CO113 runs.
        Then: No validation error is returned. Unlike the old behaviour,
              CO113 no longer flags unresolved integrations because those
              only affect the title check (now in CO194); the id itself was
              already validated structurally against the handler.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "My Integration"
        )
        connector.handlers[0].related_integration = None

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_structural_pattern_failure_without_handler(self):
        """
        Given: A grouped connector with a sub-capability id that does not start
               with '<capability_id>_' and has no subscribing handler.
        When: CO113 runs.
        Then: The structural id pattern is enforced (no silent pass), even
              though the '>=1 handler' rule is handled within UCP itself.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "My Integration"
        )
        # Rename the YAML sub-capability to a malformed id that no handler
        # subscribes to (the handler still subscribes to 'fetch-issues_myint').
        connector.capabilities[0].sub_capabilities[0].id = "totally-wrong"

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "must follow the pattern" in results[0].message

    def test_non_grouped_short_circuits(self):
        """
        Given: A non-grouped connector with a badly-derived sub-capability.
        When: CO113 runs.
        Then: No validation errors are returned - CO113 is grouped-only.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_wrong", "Wrong Title"
        )
        connector.settings.grouped = False

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_expected_git_statuses_is_added_only(self):
        """
        Given: The CO113 validator class.
        When: Its ``expected_git_statuses`` attribute is inspected.
        Then: It is restricted to ``GitStatuses.ADDED`` so the SDK's
              ``should_run_according_to_status`` gate skips CO113 for any
              already-published (MODIFIED / RENAMED / no-status) connector.
              This is what grandfathers existing non-mechanical ids.
        """
        from demisto_sdk.commands.common.constants import GitStatuses

        assert IsSubCapabilityIdDerivedValidator.expected_git_statuses == [
            GitStatuses.ADDED
        ]


class TestNormalizeIntegrationId:
    """Direct tests for the new mechanical normalization rule."""

    @pytest.mark.parametrize(
        "integration_id, expected",
        [
            # Basic lowercase + space -> dash.
            ("MyInt", "myint"),
            ("My Integration", "my-integration"),
            # Dashes with surrounding spaces collapse.
            ("AWS - Athena - Beta", "aws-athena-beta"),
            ("Cortex XDR - IOC", "cortex-xdr-ioc"),
            ("MailListener - POP3", "maillistener-pop3"),
            # Periods are stripped.
            ("Tenable.io", "tenable-io"),
            ("Tenable.sc", "tenable-sc"),
            ("AppSentinels.ai", "appsentinels-ai"),
            ("OpenCTI Feed 4.X", "opencti-feed-4-x"),
            ("abuse.ch SSL Blacklist Feed", "abuse-ch-ssl-blacklist-feed"),
            # Parentheses are stripped.
            ("Mail Sender (New)", "mail-sender-new"),
            (
                "Microsoft Management Activity API (O365 Azure Events)",
                "microsoft-management-activity-api-o365-azure-events",
            ),
            (
                "Skyhigh Secure Web Gateway (On Prem)",
                "skyhigh-secure-web-gateway-on-prem",
            ),
            ("Server Message Block (SMB) v2", "server-message-block-smb-v2"),
            (
                "VMware Workspace ONE UEM (AirWatch MDM)",
                "vmware-workspace-one-uem-airwatch-mdm",
            ),
            # Question marks are stripped.
            ("Have I Been Pwned? V2", "have-i-been-pwned-v2"),
            # Ampersands are stripped mechanically (ATT&CK -> att-ck, NOT
            # attack; grandfathered content is unaffected because CO113
            # runs on ADDED only).
            ("MITRE ATT&CK v2", "mitre-att-ck-v2"),
            # Multiple runs collapse.
            ("A  B", "a-b"),
            ("A--B", "a-b"),
            # Leading/trailing punctuation trims.
            ("  hello  ", "hello"),
            ("--x--", "x"),
        ],
    )
    def test_mechanical_normalization(self, integration_id, expected):
        from demisto_sdk.commands.validate.validators.CO_validators.CO113_is_sub_capability_id_derived import (
            normalize_integration_id,
        )

        assert normalize_integration_id(integration_id) == expected


# ============================================================
# CO194 - IsSubCapabilityTitleDerivedValidator
# ============================================================


class TestCO194IsSubCapabilityTitleDerived:
    """Tests for CO194: sub-capability title must equal the linked
    integration's display name, enforced on ALL grouped connectors (no
    git-status gate — titles are display-only and safe to change)."""

    def test_valid_title(self):
        """
        Given: A grouped connector whose sub-capability title matches the
               integration display name.
        When: CO194 runs.
        Then: No validation errors are returned.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "My Integration"
        )

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_title(self):
        """
        Given: A grouped connector whose sub-capability title does NOT match
               the integration display name.
        When: CO194 runs.
        Then: A validation error naming the expected title is returned.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Wrong Title"
        )

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "My Integration" in results[0].message
        assert "Wrong Title" in results[0].message

    def test_bad_id_but_correct_title_passes(self):
        """
        Given: A grouped connector whose sub-capability id is mis-derived but
               whose title matches the integration display name.
        When: CO194 runs.
        Then: No validation errors are returned — CO194 owns titles only;
              id derivation is CO113's concern.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_wrong", "My Integration"
        )
        # The subscribing handler still points at 'fetch-issues_wrong', so we
        # do find the handler and its resolved integration display name.

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_unresolved_integration_is_flagged_as_unverifiable(self):
        """
        Given: A grouped connector whose sub-capability has a subscribing
               handler, but the handler's referenced integration was NOT
               resolved (related_integration is None, e.g. no content graph).
        When: CO194 runs.
        Then: A validation error is returned describing the check as
              unverifiable (no silent pass on a missing graph).
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "My Integration"
        )
        connector.handlers[0].related_integration = None

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "could not be verified" in results[0].message

    def test_no_subscribing_handler_is_skipped(self):
        """
        Given: A grouped connector whose sub-capability has no subscribing
               handler (the '>=1 handler' rule lives in UCP itself).
        When: CO194 runs.
        Then: No validation errors are returned — we have nothing to compare
              the title to.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Any Title"
        )
        # Rename the sub-cap to a slug no handler subscribes to.
        connector.capabilities[0].sub_capabilities[0].id = "fetch-issues_orphan"

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_non_grouped_short_circuits(self):
        """
        Given: A non-grouped connector with a mismatched sub-capability title.
        When: CO194 runs.
        Then: No validation errors are returned - CO194 is grouped-only.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Wrong Title"
        )
        connector.settings.grouped = False

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_no_git_status_gate(self):
        """
        Given: The CO194 validator class.
        When: Its ``expected_git_statuses`` attribute is inspected.
        Then: It is empty/None so CO194 runs on ALL grouped connectors
              regardless of git status (unlike CO113, which is ADDED-only).
        """
        # Default in BaseValidator is [] which means "run on any status".
        assert not IsSubCapabilityTitleDerivedValidator.expected_git_statuses

    def test_non_xsoar_handler_is_skipped(self):
        """
        Given: A grouped connector whose sub-capability's only subscribing
               handler is a non-XSOAR (SaaS identity / data-security / posture)
               handler with no backing XSOAR integration.
        When: CO194 runs.
        Then: No validation errors are returned — non-XSOAR handlers have no
              integration display_name to compare against.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Any Title"
        )
        # Convert the sole subscribing handler into a non-XSOAR SaaS handler.
        h = connector.handlers[0]
        h.metadata.module = "identity"
        h.metadata.ownership.team = "identity"
        h.triggering.labels = {"identity-content-id": "gsuite"}
        h.related_integration = None
        assert not h.is_xsoar  # sanity — precondition

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_xsoar_handler_missing_integration_id_is_flagged(self):
        """
        Given: An XSOAR handler subscribing to a sub-capability but declaring
               NO ``xsoar-integration-id`` label.
        When: CO194 runs.
        Then: A validation error is returned — every XSOAR handler MUST label
              its backing integration; a missing id is a real content bug, not
              something to silently skip.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Any Title"
        )
        connector.handlers[0].triggering.labels = {"xsoar-pack-id": "MyPack"}
        connector.handlers[0].related_integration = None
        assert connector.handlers[0].is_xsoar  # still XSOAR
        assert not connector.handlers[0].xsoar_integration_id  # no int-id

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "does not" in results[0].message
        assert "xsoar-integration-id" in results[0].message

    def test_unresolved_integration_message_mentions_platform(self):
        """
        Given: An XSOAR sub-capability whose subscribing handler references an
               integration id but the integration didn't resolve (e.g. its
               ``marketplaces`` don't include ``PLATFORM``).
        When: CO194 runs.
        Then: The error message mentions the ``PLATFORM`` marketplaces hint so
              content authors know exactly what to check.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "My Integration"
        )
        connector.handlers[0].related_integration = None

        validator = IsSubCapabilityTitleDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "PLATFORM" in results[0].message


# ============================================================
# CO114 - IsMatchingLicenseValidator
# ============================================================


def _stub_integration_modules(supported_modules, pack_modules=None, platform=True):
    """Build a minimal integration stub for get_content_item_supported_modules.

    ``supported_modules`` is the integration's own supportedModules (None to
    inherit from the pack). ``pack_modules`` sets the parent pack's
    supportedModules (None => platform defaults when the integration's is None).
    """
    marketplaces = [MarketplaceVersions.PLATFORM] if platform else []
    pack = SimpleNamespace(supportedModules=pack_modules)
    return SimpleNamespace(
        marketplaces=marketplaces,
        supportedModules=supported_modules,
        pack=pack,
    )


def _connector_with_license(required_license, integration=None, resolve=True):
    """Grouped connector: one 'fetch-issues' sub-capability with the given
    required_license, an XSOAR handler subscribing to it, and (optionally) a
    resolved integration stub."""
    connector = create_connector_object(
        connector_overrides={"settings": {"grouped": True}},
        capabilities_data={
            "capabilities": [
                {
                    "id": "fetch-issues",
                    "title": "Fetch Issues",
                    "description": "desc",
                    "default_enabled": False,
                    "required": False,
                    "sub_capabilities": [
                        {
                            "id": "fetch-issues_myint",
                            "title": "My Integration",
                            "default_enabled": False,
                            "required": False,
                            "config": (
                                {"required_license": required_license}
                                if required_license is not None
                                else None
                            ),
                        }
                    ],
                }
            ]
        },
        handlers=[
            {
                "id": "xsoar-myint",
                "triggering": {
                    "type": "PUB_SUB",
                    "labels": {
                        "xsoar-integration-id": "MyInt",
                        "xsoar-pack-id": "MyPack",
                    },
                },
                "capabilities": [
                    {
                        "id": "fetch-issues_myint",
                        "auth_options": [
                            {"id": "test-auth", "workloads": ["test-workload"]}
                        ],
                    }
                ],
            }
        ],
    )
    if resolve:
        connector.handlers[0].related_integration = (
            integration
            if integration is not None
            else _stub_integration_modules(["xsiam", "agentix"])
        )
    else:
        connector.handlers[0].related_integration = None
    return connector


class TestCO114IsMatchingLicense:
    """Tests for CO114: a capability/sub-capability's required_license must be a
    subset of the backing integration's supported modules."""

    def test_required_license_subset_is_valid(self):
        """
        Given: A sub-capability whose required_license is a subset of the
               integration's supported modules.
        When: CO114 runs.
        Then: No validation errors are returned.
        """
        connector = _connector_with_license(
            ["xsiam"], integration=_stub_integration_modules(["xsiam", "agentix"])
        )

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_required_license_not_subset_is_flagged(self):
        """
        Given: A sub-capability requiring a license the integration does not
               support.
        When: CO114 runs.
        Then: A validation error naming the missing license is returned.
        """
        connector = _connector_with_license(
            ["xsiam", "edr"], integration=_stub_integration_modules(["xsiam"])
        )

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "edr" in results[0].message

    def test_no_required_license_means_all_modules(self):
        """
        Given: A sub-capability with NO required_license (=> requires ALL
               modules) but the integration supports only some.
        When: CO114 runs.
        Then: A validation error is returned (all-modules is not a subset).
        """
        connector = _connector_with_license(
            None, integration=_stub_integration_modules(["xsiam", "agentix"])
        )

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1

    def test_no_required_license_with_all_modules_is_valid(self):
        """
        Given: A sub-capability with NO required_license (=> requires ALL
               modules) and the integration supports ALL modules.
        When: CO114 runs.
        Then: No validation errors are returned.
        """
        connector = _connector_with_license(
            None,
            integration=_stub_integration_modules(list(ALL_SUPPORTED_MODULES)),
        )

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_unresolved_integration_is_flagged(self):
        """
        Given: An XSOAR sub-capability whose subscribing handler's integration
               was not resolved (related_integration is None).
        When: CO114 runs.
        Then: A validation error is returned (never silently skipped) and the
              message mentions the marketplaces=PLATFORM hint.
        """
        connector = _connector_with_license(["xsiam"], resolve=False)

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "cannot be verified" in results[0].message
        assert "PLATFORM" in results[0].message

    def test_non_xsoar_handler_is_skipped(self):
        """
        Given: A sub-capability whose only subscribing handler is a non-XSOAR
               (e.g. SaaS identity / data-security / posture) handler, so it has
               no backing XSOAR integration whose modules we could compare
               against.
        When: CO114 runs.
        Then: No validation errors are returned — non-XSOAR handlers are out of
              scope for CO114 (they don't have an XSOAR integration to license
              against).
        """
        connector = _connector_with_license(
            ["xsiam"], integration=_stub_integration_modules(["xsiam"])
        )
        # Convert the sole subscribing handler into a non-XSOAR SaaS handler.
        h = connector.handlers[0]
        h.metadata.module = "identity"
        h.metadata.ownership.team = "identity"
        # Drop the xsoar-integration-id label since non-XSOAR handlers don't
        # have one; the check must bail before touching this either way.
        h.triggering.labels = {"identity-content-id": "gsuite"}
        h.related_integration = None
        assert not h.is_xsoar  # sanity — precondition for this test

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_xsoar_handler_missing_integration_id_is_flagged(self):
        """
        Given: An XSOAR handler subscribing to a sub-capability but declaring
               NO ``xsoar-integration-id`` label.
        When: CO114 runs.
        Then: A validation error is returned — every XSOAR handler MUST label
              its backing integration; a missing id is a real content bug, not
              something to silently skip (which would hide the real issue).
        """
        connector = _connector_with_license(["xsiam"], resolve=False)
        # Blank the xsoar-integration-id but keep the handler XSOAR.
        connector.handlers[0].triggering.labels = {"xsoar-pack-id": "MyPack"}
        assert connector.handlers[0].is_xsoar  # still XSOAR
        assert not connector.handlers[0].xsoar_integration_id  # but no int-id

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "does not declare an 'xsoar-integration-id'" in results[0].message


# ============================================================
# CO116 - IsConnectorMatchesIntegrationFlagsValidator
# ============================================================


def _stub_integration_flags(**flags):
    """Build a minimal integration stub exposing fetch-flag attributes.

    Any flag not provided defaults to False, mirroring the content-graph
    Integration model defaults (is_fetch, is_fetch_events, is_fetch_assets,
    is_fetch_credentials, is_feed).
    """
    defaults = {
        "is_fetch": False,
        "is_fetch_events": False,
        "is_fetch_assets": False,
        "is_fetch_credentials": False,
        "is_feed": False,
    }
    defaults.update(flags)
    return SimpleNamespace(**defaults)


def _connector_with_collection_sub_capability(
    cap_id, sub_id, integration=None, resolve=True
):
    """Grouped connector with a single collection capability whose sub-capability
    is subscribed to by an XSOAR handler, optionally backed by a resolved
    integration stub."""
    connector = create_connector_object(
        connector_overrides={"settings": {"grouped": True}},
        capabilities_data={
            "capabilities": [
                {
                    "id": cap_id,
                    "title": cap_id,
                    "description": "desc",
                    "default_enabled": False,
                    "required": False,
                    "sub_capabilities": [
                        {
                            "id": sub_id,
                            "title": sub_id,
                            "default_enabled": False,
                            "required": False,
                        }
                    ],
                }
            ]
        },
        handlers=[
            {
                "id": "xsoar-myint",
                "triggering": {
                    "type": "PUB_SUB",
                    "labels": {
                        "xsoar-integration-id": "MyInt",
                        "xsoar-pack-id": "MyPack",
                    },
                },
                "capabilities": [
                    {
                        "id": sub_id,
                        "auth_options": [
                            {"id": "test-auth", "workloads": ["test-workload"]}
                        ],
                    }
                ],
            }
        ],
    )
    if resolve:
        connector.handlers[0].related_integration = (
            integration if integration is not None else _stub_integration_flags()
        )
    else:
        connector.handlers[0].related_integration = None
    return connector


class TestCO116IsConnectorMatchesIntegrationFlags:
    """Tests for CO116: a declared collection capability/sub-capability must be
    backed by the integration's matching fetch flag."""

    def test_log_collection_with_flag_enabled_is_valid(self):
        """
        Given: A log-collection sub-capability whose integration has
               is_fetch_events (isfetchevents) enabled.
        When: CO116 runs.
        Then: No validation errors are returned.
        """
        connector = _connector_with_collection_sub_capability(
            "log-collection",
            "log-collection_myint",
            integration=_stub_integration_flags(is_fetch_events=True),
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_log_collection_with_flag_disabled_is_flagged(self):
        """
        Given: A log-collection sub-capability whose integration has
               is_fetch_events disabled.
        When: CO116 runs.
        Then: A validation error naming isfetchevents is returned.
        """
        connector = _connector_with_collection_sub_capability(
            "log-collection",
            "log-collection_myint",
            integration=_stub_integration_flags(is_fetch_events=False),
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "isfetchevents" in results[0].message
        assert "log-collection_myint" in results[0].message

    def test_fetch_issues_with_flag_enabled_is_valid(self):
        """
        Given: A fetch-issues sub-capability whose integration has is_fetch
               (isfetch) enabled.
        When: CO116 runs.
        Then: No validation errors are returned.
        """
        connector = _connector_with_collection_sub_capability(
            "fetch-issues",
            "fetch-issues_myint",
            integration=_stub_integration_flags(is_fetch=True),
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_non_collection_capability_is_skipped(self):
        """
        Given: An automation-and-remediation sub-capability (not a collection
               capability) whose integration has every fetch flag disabled.
        When: CO116 runs.
        Then: No validation errors are returned - non-collection capabilities
              are not checked.
        """
        connector = _connector_with_collection_sub_capability(
            "automation-and-remediation",
            "automation-and-remediation_myint",
            integration=_stub_integration_flags(),
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_unresolved_integration_is_flagged(self):
        """
        Given: A collection sub-capability whose subscribing handler's
               integration was not resolved.
        When: CO116 runs.
        Then: A validation error is returned (never silently skipped).
        """
        connector = _connector_with_collection_sub_capability(
            "log-collection", "log-collection_myint", resolve=False
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "cannot be verified" in results[0].message

    def test_feed_capability_uses_is_feed_flag(self):
        """
        Given: A threat-intelligence-and-enrichment sub-capability whose
               integration has is_feed (feed) disabled.
        When: CO116 runs.
        Then: A validation error naming the 'feed' flag is returned.
        """
        connector = _connector_with_collection_sub_capability(
            "threat-intelligence-and-enrichment",
            "threat-intelligence-and-enrichment_myint",
            integration=_stub_integration_flags(is_feed=False),
        )

        validator = IsConnectorMatchesIntegrationFlagsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "feed" in results[0].message


# ============================================================
# CO117 - IsCapabilityTitleValidValidator
# ============================================================


def _connector_with_capability_title(cap_id, title):
    """Connector with a single (leaf) capability having the given id and title.

    Attaches a default (XSOAR) handler subscribing to ``cap_id`` so the
    capability is XSOAR-owned - CO117 only checks XSOAR-owned capabilities.
    """
    return create_connector_object(
        capabilities_data={
            "capabilities": [
                {
                    "id": cap_id,
                    "title": title,
                    "description": "desc",
                    "default_enabled": False,
                    "required": False,
                }
            ]
        },
        handlers=[_xsoar_handler_subscribing_to(cap_id)],
    )


class TestCO117IsCapabilityTitleValid:
    """Tests for CO117: a capability's title must be the Title Case of its id,
    with the connector word 'and' kept lowercase."""

    def test_valid_simple_title(self):
        """
        Given: A capability 'fetch-issues' with title 'Fetch Issues'.
        When: CO117 runs.
        Then: No validation errors are returned.
        """
        connector = _connector_with_capability_title("fetch-issues", "Fetch Issues")

        validator = IsCapabilityTitleValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_valid_title_with_lowercase_and(self):
        """
        Given: A capability 'automation-and-remediation' with title
               'Automation and Remediation' (the 'and' kept lowercase).
        When: CO117 runs.
        Then: No validation errors are returned.
        """
        connector = _connector_with_capability_title(
            "automation-and-remediation", "Automation and Remediation"
        )

        validator = IsCapabilityTitleValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_valid_multi_word_title_with_and(self):
        """
        Given: A capability 'threat-intelligence-and-enrichment' with title
               'Threat Intelligence and Enrichment'.
        When: CO117 runs.
        Then: No validation errors are returned.
        """
        connector = _connector_with_capability_title(
            "threat-intelligence-and-enrichment",
            "Threat Intelligence and Enrichment",
        )

        validator = IsCapabilityTitleValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_title_wrong_casing(self):
        """
        Given: A capability 'fetch-issues' with title 'fetch issues'.
        When: CO117 runs.
        Then: A validation error naming the expected title is returned.
        """
        connector = _connector_with_capability_title("fetch-issues", "fetch issues")

        validator = IsCapabilityTitleValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "Fetch Issues" in results[0].message

    def test_invalid_title_capitalized_and(self):
        """
        Given: A capability 'automation-and-remediation' whose title
               capitalizes 'And' ('Automation And Remediation').
        When: CO117 runs.
        Then: A validation error is returned - 'and' must be lowercase.
        """
        connector = _connector_with_capability_title(
            "automation-and-remediation", "Automation And Remediation"
        )

        validator = IsCapabilityTitleValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "Automation and Remediation" in results[0].message

    def test_sub_capability_titles_are_not_checked(self):
        """
        Given: A capability whose sub-capability title is the integration
               display name (not a title-cased id).
        When: CO117 runs.
        Then: No validation errors are returned - CO117 checks parent
              capabilities only.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "fetch-issues",
                        "title": "Fetch Issues",
                        "description": "desc",
                        "default_enabled": False,
                        "required": False,
                        "sub_capabilities": [
                            {
                                "id": "fetch-issues_jira-v3",
                                "title": "Atlassian Jira v3",
                                "default_enabled": False,
                                "required": False,
                            }
                        ],
                    }
                ]
            },
            handlers=[
                _xsoar_handler_subscribing_to("fetch-issues", "fetch-issues_jira-v3")
            ],
        )

        validator = IsCapabilityTitleValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_non_xsoar_capability_skipped(self):
        """
        Given: A connector whose only capability ('identity') is subscribed
               to by a non-XSOAR handler and carries a title
               ('Identity Posture') that does NOT match the Title Case of the
               id ('Identity').
        When: CO117 runs.
        Then: No validation errors are returned - CO117 only checks
              XSOAR-owned capabilities (closed list). Non-XSOAR capabilities
              like posture capabilities own their own titles and are out of
              scope. This is the exact scenario producing false positives
              on connectors like googleworkspace, microsoft365-services,
              and salesforce.
        """
        connector = create_connector_object(
            capabilities_data={
                "capabilities": [
                    {
                        "id": "identity",
                        "title": "Identity Posture",
                        "description": "desc",
                        "default_enabled": False,
                        "required": False,
                    }
                ]
            },
            handlers=[
                {
                    "metadata": {"module": "cwp", "ownership": {"team": "cwp"}},
                    "capabilities": [
                        {
                            "id": "identity",
                            "auth_options": [
                                {"id": "test-auth", "workloads": ["test-workload"]}
                            ],
                        }
                    ],
                }
            ],
        )

        validator = IsCapabilityTitleValidValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO118 - IsValidConnectionMetadataValidator
# ============================================================


class TestCO118IsValidConnectionMetadata:
    """Tests for CO118: connection.yaml metadata title/description."""

    def test_valid_connection_metadata(self):
        """
        Given: A connector whose connection metadata has the correct title
               and description.
        When: CO118 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connection_data={
                "metadata": {
                    "title": "Connection",
                    "description": VALID_CONNECTION_DESCRIPTION,
                }
            }
        )

        validator = IsValidConnectionMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_title(self):
        """
        Given: A connector whose connection metadata.title is not 'Connection'.
        When: CO118 runs.
        Then: A validation error mentioning the title is returned.
        """
        connector = create_connector_object(
            connection_data={
                "metadata": {
                    "title": "Wrong Title",
                    "description": VALID_CONNECTION_DESCRIPTION,
                }
            }
        )

        validator = IsValidConnectionMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "metadata.title" in results[0].message

    def test_invalid_description(self):
        """
        Given: A connector whose connection metadata.description is wrong.
        When: CO118 runs.
        Then: A validation error mentioning the description is returned.
        """
        connector = create_connector_object(
            connection_data={
                "metadata": {
                    "title": "Connection",
                    "description": "Wrong description",
                }
            }
        )

        validator = IsValidConnectionMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "metadata.description" in results[0].message

    def test_all_invalid_combined(self):
        """
        Given: A connector whose connection metadata is wrong on all counts.
        When: CO118 runs.
        Then: A single ValidationResult reports both problems.
        """
        connector = create_connector_object(
            connection_data={
                "metadata": {
                    "title": "Nope",
                    "description": "Nope",
                }
            }
        )

        validator = IsValidConnectionMetadataValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "metadata.title" in msg
        assert "metadata.description" in msg


# ============================================================
# CO119 - NoConnectionGeneralConfigurationsValidator
# ============================================================


class TestCO119NoConnectionGeneralConfigurations:
    """Tests for CO119: grouped connectors must not declare
    'general_configurations' in connection.yaml.
    """

    @staticmethod
    def _gc_block():
        """A minimal but structurally-valid general_configurations block."""
        return {
            "description": "Common configurations for all connection profiles",
            "configurations": [
                {
                    "fields": [
                        {
                            "id": "server_url",
                            "title": "Server URL",
                            "field_type": "input",
                        }
                    ]
                }
            ],
        }

    def test_non_grouped_with_general_configurations_passes(self):
        """
        Given: A NON-grouped connector whose connection.yaml declares
               'general_configurations'.
        When: CO119 runs.
        Then: No validation errors are returned (rule is grouped-only).
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": self._gc_block(),
            }
        )
        # Sanity: the fixture is really non-grouped.
        assert not (connector.settings and connector.settings.grouped)

        validator = NoConnectionGeneralConfigurationsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_grouped_without_general_configurations_passes(self):
        """
        Given: A grouped connector whose connection.yaml does NOT declare
               'general_configurations'.
        When: CO119 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        # Sanity: the template really has no general_configurations.
        assert (
            connector.connection is not None
            and connector.connection.general_configurations is None
        )

        validator = NoConnectionGeneralConfigurationsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_grouped_with_general_configurations_fails(self):
        """
        Given: A grouped connector whose connection.yaml DOES declare
               'general_configurations'.
        When: CO119 runs.
        Then: A single ValidationResult is returned pointing at
              connection.yaml.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "general_configurations": self._gc_block(),
            },
        )

        validator = NoConnectionGeneralConfigurationsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "general_configurations" in msg
        assert connector.object_id in msg
        # Path is the connection.yaml file, per the CO118 pattern.
        assert str(results[0].path).endswith("connection.yaml")


# ============================================================
# CO120 - IsProxyAndInsecureExistsValidator
# ============================================================


def _make_integration_with_params(*names: str):
    """Stub integration exposing ``params`` with the given ``name`` values.

    CO120 only reads ``integration.params[*].name`` (mirrors IN100), so a
    ``SimpleNamespace`` per param is enough - no need for real Parameter /
    Integration Pydantic construction.
    """
    return SimpleNamespace(params=[SimpleNamespace(name=n) for n in names])


def _override_resolved(handler, mapping):
    """Replace ``handler.resolved_params`` with a list built from a
    ``{connector_param_name: content_param_name}`` dict.

    CO120 only reads ``rp.content_param_name`` so the other fields on
    ResolvedParamMapping can be defaulted.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        ResolvedParamMapping,
    )

    handler.resolved_params = [
        ResolvedParamMapping(
            connector_param_name=cn,
            content_param_name=rn,
        )
        for cn, rn in mapping.items()
    ]


class TestCO120IsProxyAndInsecureExists:
    """Tests for CO120: XSOAR handlers must expose 'proxy'/'insecure'
    when the backing integration declares those params.
    """

    def test_non_xsoar_handler_skipped(self):
        """
        Given: A connector whose handler is non-XSOAR
               (metadata.module != 'xsoar').
        When: CO120 runs.
        Then: The handler is skipped and no error is emitted, even when the
              integration has proxy/insecure params.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "sspm-myint",
                    "metadata": {
                        "module": "sspm",
                        "ownership": {
                            "team": "SSPM",
                            "maintainers": ["@sspm-team"],
                        },
                    },
                }
            ]
        )
        # Sanity: not XSOAR.
        assert not connector.handlers[0].is_xsoar

        connector.handlers[0].related_integration = _make_integration_with_params(
            "proxy", "insecure"
        )
        # Do not touch resolved_params - handler is skipped entirely anyway.

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_integration_without_proxy_or_insecure_passes(self):
        """
        Given: An XSOAR handler whose integration declares no proxy/insecure
               param.
        When: CO120 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "client_id", "client_secret"
        )
        _override_resolved(connector.handlers[0], {})

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_xsoar_handler_unresolved_integration_is_error(self):
        """
        Given: An XSOAR handler whose ``related_integration`` was NOT
               resolved (None).
        When: CO120 runs.
        Then: A ValidationResult flags it (per updated design - unresolved
              XSOAR handlers are a real bug, not something to silently pass).
        """
        connector = create_connector_object()
        assert connector.handlers[0].is_xsoar  # precondition
        connector.handlers[0].related_integration = None

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "no resolvable backing integration" in msg
        assert connector.object_id in msg

    def test_direct_ids_present_passes(self):
        """
        Given: Integration has 'proxy' and 'insecure' params AND the handler
               resolves 'proxy'/'insecure' content_param_names directly
               (standard-shaped connection.yaml or ungrouped connector).
        When: CO120 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "proxy", "insecure"
        )
        _override_resolved(
            connector.handlers[0],
            {"proxy": "proxy", "insecure": "insecure"},
        )

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_serializer_renamed_ids_pass(self):
        """
        Given: Grouped connector with namespaced field ids (e.g.
               'plain_jira_v3_proxy') that are renamed to 'proxy' /
               'insecure' by serializer.yaml field_mappings.
        When: CO120 runs.
        Then: The check accepts the resolved content_param_name equally -
              no errors emitted.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "proxy", "insecure"
        )
        _override_resolved(
            connector.handlers[0],
            {
                "plain_jira_v3_proxy": "proxy",
                "plain_jira_v3_insecure": "insecure",
            },
        )

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_proxy_missing_fails(self):
        """
        Given: Integration declares 'proxy' AND 'insecure' but the handler
               only exposes 'insecure' (via any mechanism).
        When: CO120 runs.
        Then: Exactly one ValidationResult flags the missing 'proxy' family.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "proxy", "insecure"
        )
        _override_resolved(
            connector.handlers[0],
            {"insecure": "insecure"},
        )

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "'proxy'" in msg
        # Confirm we did NOT also emit an 'insecure' finding.
        assert "'insecure' param" not in msg

    def test_insecure_missing_fails(self):
        """
        Given: Integration declares 'proxy' AND 'insecure' but the handler
               only exposes 'proxy'.
        When: CO120 runs.
        Then: Exactly one ValidationResult flags the missing 'insecure'
              family.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "proxy", "insecure"
        )
        _override_resolved(
            connector.handlers[0],
            {"proxy": "proxy"},
        )

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "'insecure'" in msg

    def test_both_missing_fails_twice(self):
        """
        Given: Integration declares both families but the handler exposes
               neither.
        When: CO120 runs.
        Then: Two ValidationResults - one per family - are returned.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "proxy", "insecure"
        )
        _override_resolved(connector.handlers[0], {})

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 2
        joined = " | ".join(r.message for r in results)
        assert "'proxy'" in joined
        assert "'insecure'" in joined

    def test_insecure_alias_is_accepted(self):
        """
        Given: Integration YML uses the alternative alias 'unsecure' AND
               the handler exposes 'verify' (another alias in the same
               family).
        When: CO120 runs.
        Then: Passes - detection uses the full alias set on both sides.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "unsecure"
        )
        _override_resolved(
            connector.handlers[0],
            {"trust_any_cert": "verify"},
        )

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_proxy_alias_useproxy_is_accepted(self):
        """
        Given: Integration declares 'useproxy' AND the handler exposes
               'use_proxy'.
        When: CO120 runs.
        Then: Passes.
        """
        connector = create_connector_object()
        connector.handlers[0].related_integration = _make_integration_with_params(
            "useproxy"
        )
        _override_resolved(
            connector.handlers[0],
            {"foo": "use_proxy"},
        )

        validator = IsProxyAndInsecureExistsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []


# ============================================================
# CO121 - IsValidInterpolationValidator
# ============================================================


def _make_integration_with_params_objs(*name_type_pairs):
    """Stub integration exposing ``params`` where each entry has a ``name``
    AND a ``type``. Used for CO121 (Sub-rule D needs param.type).

    ``name_type_pairs`` is an iterable of ``(name, type)`` tuples.
    """
    return SimpleNamespace(
        params=[SimpleNamespace(name=n, type=t) for (n, t) in name_type_pairs]
    )


def _make_interpolated_profile(
    profile_id: str,
    mapping: str,
    field_specs,
):
    """Build a connector connection.yaml override that defines a single
    interpolated profile with the given interpolation_mapping and fields.

    ``field_specs`` is an iterable of dicts describing each field, e.g.
    ``[{"id": "credentials_username", "auth_parameter": "username"}]``.
    Setting ``auth_parameter`` populates ``metadata.auth.parameter``.
    Setting ``publish`` (bool) populates ``metadata.event.publish`` — used
    by CO121 Sub-rule E (an interpolated field must not also publish).
    """
    fields = []
    for spec in field_specs:
        field = {
            "id": spec["id"],
            "title": spec.get("title", spec["id"]),
            "field_type": spec.get("field_type", "input"),
        }
        metadata: dict = {}
        if spec.get("auth_parameter"):
            metadata["auth"] = {"parameter": spec["auth_parameter"]}
        if "publish" in spec:
            metadata["event"] = {"publish": bool(spec["publish"])}
        if metadata:
            field["metadata"] = metadata
        fields.append(field)

    return {
        "profiles": [
            {
                "id": profile_id,
                "type": "plain",
                "title": "Test Profile",
                "description": "for CO121 tests",
                "metadata": {
                    "xsoar": {
                        "interpolated": True,
                        "interpolation_mapping": mapping,
                    }
                },
                "configurations": [{"fields": fields}],
            }
        ]
    }


def _wire_handler_to_profile(connector, profile_id: str, integration):
    """Point the connector's first handler at the given profile id and stub
    its ``related_integration`` to the supplied namespace.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        HandlerAuthOption,
        HandlerCapability,
    )

    h = connector.handlers[0]
    h.capabilities = [
        HandlerCapability(
            id="automation-and-remediation",
            auth_options=[HandlerAuthOption(id=profile_id)],
        )
    ]
    h.related_integration = integration


class TestCO121IsValidInterpolation:
    """Tests for CO121: interpolation_mapping must be internally consistent
    (LEFT is a valid profile auth-field name; LEFT is not a reserved general
    param; RIGHT resolves in the integration; credentials suffix only on
    type-9 params).
    """

    def test_non_interpolated_profile_is_skipped(self):
        """
        Given: A profile with metadata.xsoar.interpolated=false and NO
               interpolation_mapping.
        When: CO121 runs.
        Then: No validation errors.
        """
        connector = create_connector_object(
            connection_data={
                "profiles": [
                    {
                        "id": "plain.myint",
                        "type": "plain",
                        "title": "T",
                        "description": "D",
                        "metadata": {"xsoar": {"interpolated": False}},
                        "configurations": [
                            {"fields": [{"id": "x", "field_type": "input"}]}
                        ],
                    }
                ]
            }
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_valid_mapping_passes(self):
        """
        Given: An interpolated profile whose LEFT keys are valid auth-field
               names and RIGHT values resolve on the backing integration.
        When: CO121 runs.
        Then: No validation errors.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="username:credentials.identifier,password:credentials.password",
                field_specs=[
                    {"id": "credentials_username", "auth_parameter": "username"},
                    {"id": "credentials_password", "auth_parameter": "password"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == [], [r.message for r in results]

    def test_left_is_reserved_engine_fails(self):
        """
        Sub-rule B: LEFT 'engine' is a reserved param and must not appear
        on the LEFT.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="engine:credentials.identifier",
                field_specs=[
                    {"id": "engine", "auth_parameter": "engine"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "reserved general param" in msg
        assert "'engine'" in msg

    def test_left_is_reserved_proxy_fails(self):
        """
        Sub-rule B: 'proxy' as LEFT must fail even when the profile has a
        matching field id (matching field is irrelevant — the rule bans
        the LEFT position for reserved params outright).
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="proxy:proxy",
                field_specs=[
                    {"id": "proxy", "auth_parameter": "proxy"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("proxy", 8)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "reserved general param" in results[0].message

    def test_left_not_in_profile_fails(self):
        """
        Sub-rule A: LEFT that is neither a field id nor a
        metadata.auth.parameter in the profile is a fail.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="does_not_exist:credentials.password",
                field_specs=[
                    {"id": "credentials", "auth_parameter": "credentials"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert (
            "does not match any field id or metadata.auth.parameter"
            in results[0].message
        )

    def test_left_matches_field_id_serialized_form(self):
        """
        Sub-rule A: LEFT is allowed to match either the field's ``id``
        (serialized form) OR its ``metadata.auth.parameter`` (deserialized
        form). Here it matches the raw ``id``.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="raw_field_id:credentials.password",
                field_specs=[
                    # No auth_parameter — LEFT lookup falls back to field.id
                    {"id": "raw_field_id"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == [], [r.message for r in results]

    def test_right_not_in_integration_fails(self):
        """
        Sub-rule C: RIGHT (after stripping the credentials suffix) must
        exist as a param on the backing integration.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="username:ghost_param.identifier",
                field_specs=[
                    {"id": "credentials_username", "auth_parameter": "username"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("api_key", 4)),  # no ghost_param
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "not declared on the backing integration" in results[0].message
        assert "'ghost_param'" in results[0].message

    def test_credentials_suffix_on_non_type9_fails(self):
        """
        Sub-rule D: '.password' suffix is only valid when the integration
        param has type=9. Here we use type=4 (ENCRYPTED) so the suffix is
        wrong.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="api_key:api_key.password",
                field_specs=[
                    {"id": "credentials_key", "auth_parameter": "api_key"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("api_key", 4)),  # ENCRYPTED, not AUTH
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "credentials suffix" in msg
        assert "type=9" in msg

    def test_no_suffix_no_type_check(self):
        """
        Sub-rule D only triggers when the credentials suffix is present.
        A plain 1:1 mapping (`api_key:api_key`) with a non-9 param is
        perfectly valid.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="api_key:api_key",
                field_specs=[
                    {"id": "credentials_key", "auth_parameter": "api_key"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("api_key", 4)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == [], [r.message for r in results]

    def test_no_xsoar_handler_references_profile_skips_C_D(self):
        """
        When no XSOAR handler references the profile, sub-rules C/D are
        skipped (they need the integration). Sub-rules A/B still run.
        Here: LEFT is valid → no error.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.orphan",
                mapping="username:something_wrong.identifier",
                field_specs=[
                    {"id": "credentials_username", "auth_parameter": "username"},
                ],
            )
        )
        # Do NOT wire any handler to this profile — the fixture's default
        # handler references "test-auth" (see connector_handler.yaml).

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == [], [r.message for r in results]

    def test_malformed_pair_missing_colon(self):
        """
        A malformed 'left:right' pair (no colon) is caught by the LEFT-A
        check and RIGHT-empty check.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="not_a_pair",
                field_specs=[
                    {"id": "credentials", "auth_parameter": "credentials"},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        # We expect BOTH the "LEFT not found" AND the "RIGHT empty" details
        # (2 ValidationResults with the same profile_id).
        messages = [r.message for r in results]
        assert any("does not match any field id" in m for m in messages)
        assert any("RIGHT for LEFT 'not_a_pair' is empty" in m for m in messages)

    # ---- Sub-rule E: LEFT must NOT target a publish=true field ----
    # Complements CO123 (non-interpolated => publish=true). A field that is
    # interpolated is consumed by auth and must NOT also publish to the
    # runtime integration, otherwise the raw pre-interpolation value would
    # leak through as a param.

    def test_left_targets_published_field_fails(self):
        """
        Sub-rule E: A LEFT key whose profile field carries
        ``metadata.event.publish: true`` must be flagged - a published
        field cannot also be the target of an interpolation mapping.

        Given: An interpolated profile whose ``username`` auth field has
               ``metadata.event.publish: true`` AND is referenced on the
               LEFT of interpolation_mapping.
        When: CO121 runs.
        Then: One validation error mentioning the publish/interpolation
              mutual-exclusion for that LEFT key.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="username:credentials.identifier",
                field_specs=[
                    {
                        "id": "credentials_username",
                        "auth_parameter": "username",
                        "publish": True,  # violates Sub-rule E
                    },
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1, [r.message for r in results]
        msg = results[0].message
        assert "'username'" in msg
        # The message must clearly convey the publish/interpolation conflict.
        assert "publish" in msg.lower()
        assert "interpolat" in msg.lower()

    def test_left_targets_unpublished_field_passes(self):
        """
        Sub-rule E: An interpolated LEFT that resolves to a field with
        ``publish`` absent or explicitly ``false`` is valid.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="username:credentials.identifier",
                field_specs=[
                    {
                        "id": "credentials_username",
                        "auth_parameter": "username",
                        "publish": False,
                    },
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == [], [r.message for r in results]

    def test_left_matches_field_id_with_publish_true_fails(self):
        """
        Sub-rule E: LEFT resolution must also work when the mapping
        references the raw ``field.id`` (not the ``auth.parameter``
        alias). A published raw-id field is still a Sub-rule E violation.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="raw_field_id:credentials.password",
                field_specs=[
                    {"id": "raw_field_id", "publish": True},
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1, [r.message for r in results]
        msg = results[0].message
        assert "'raw_field_id'" in msg
        assert "publish" in msg.lower()

    def test_reserved_left_with_publish_true_only_reports_reserved(self):
        """
        Guard against double-reporting: a reserved LEFT (e.g. ``engine``)
        that also happens to be marked ``publish=true`` should still only
        emit Sub-rule B (reserved), not both B and E - Sub-rule B is the
        primary/harder failure and Sub-rule E is skipped for reserved LEFTs.
        """
        connector = create_connector_object(
            connection_data=_make_interpolated_profile(
                profile_id="plain.myint",
                mapping="engine:credentials.identifier",
                field_specs=[
                    {
                        "id": "engine",
                        "auth_parameter": "engine",
                        "publish": True,
                    },
                ],
            )
        )
        _wire_handler_to_profile(
            connector,
            "plain.myint",
            _make_integration_with_params_objs(("credentials", 9)),
        )

        validator = IsValidInterpolationValidator()
        results = validator.obtain_invalid_content_items([connector])

        # Exactly one finding, and it must be the "reserved" one - the
        # publish-vs-interpolation rule must not double-report on top of it.
        assert len(results) == 1, [r.message for r in results]
        assert "reserved general param" in results[0].message


# ============================================================
# CO122 - IsValidViewgroupValidator
# ============================================================


def _stub_related_integration(object_id: str, display_name: str):
    """Stub ``handler.related_integration`` with only the fields CO122
    reads: ``object_id`` and ``display_name``.
    """
    return SimpleNamespace(object_id=object_id, display_name=display_name)


def _grouped_connector_with_view_groups(view_groups):
    """Build a grouped connector whose connection.yaml declares the given
    ``view_groups`` list (list of dicts with id/label/help_text)."""
    return create_connector_object(
        connector_overrides={"settings": {"grouped": True}},
        connection_data={"view_groups": view_groups},
    )


class TestCO122IsValidViewgroup:
    """Tests for CO122: grouped connectors must have a view_group per XSOAR
    handler, matching the handler's integration id AND display_name.
    """

    def test_non_grouped_short_circuits(self):
        """
        Given: A non-grouped connector (view_groups absent by design).
        When: CO122 runs.
        Then: No validation errors are returned - CO122 is grouped-only.
        """
        connector = create_connector_object()
        # Even if we wire up a broken view_group state, non-grouped should skip.
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_valid_matching_view_group_passes(self):
        """
        Given: A grouped connector with a single XSOAR handler whose resolved
               integration id and display_name match a declared view_group.
        When: CO122 runs.
        Then: No validation errors are returned.
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "my-integration", "label": "My Integration"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_missing_view_group_id_fails(self):
        """
        Given: A grouped connector whose XSOAR handler's integration id has
               NO matching view_group in connection.yaml.
        When: CO122 runs.
        Then: One ValidationResult is returned, naming the expected id.
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "some-other-vg", "label": "Some Other"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "my-integration" in results[0].message
        assert "normalizes to" in results[0].message

    def test_wrong_view_group_label_fails(self):
        """
        Given: A grouped connector whose view_group.id matches but whose
               view_group.label does NOT match the integration's display_name.
        When: CO122 runs.
        Then: One ValidationResult is returned, naming both labels.
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "my-integration", "label": "Wrong Label"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "Wrong Label" in msg
        assert "My Integration" in msg

    def test_xsoar_handler_unresolved_integration_is_error(self):
        """
        Given: A grouped connector whose XSOAR handler has no resolved
               ``related_integration`` (graph miss or unmapped id).
        When: CO122 runs.
        Then: A ValidationResult is emitted (NOT silently skipped) -
              per the CO120 directive that unresolved XSOAR handlers are
              errors, not skips.
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "my-integration", "label": "My Integration"}]
        )
        connector.handlers[0].related_integration = None

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "no resolved integration" in results[0].message

    def test_non_xsoar_handler_is_skipped(self):
        """
        Given: A grouped connector with a NON-XSOAR handler (out of scope).
               The connection.yaml view_groups intentionally do NOT declare
               anything for this handler.
        When: CO122 runs.
        Then: No validation errors are returned - non-XSOAR handlers are
              never our team's responsibility.

        Note: this test uses a mixed connector because CO111 forbids
        pure non-XSOAR grouped connectors; here we just want to prove the
        skip logic doesn't count the non-XSOAR handler.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "view_groups": [{"id": "my-integration", "label": "My Integration"}]
            },
            handlers=[
                # The default XSOAR handler + resolves to my-integration.
                {},
                # A second, NON-XSOAR handler with no view_group to speak of.
                {
                    "id": "cwp-handler",
                    "metadata": {
                        "module": "cwp",
                        "ownership": {"team": "cwp"},
                    },
                },
            ],
        )
        # Assign integrations by handler.id (not index) - the parser may
        # sort handlers alphabetically ('cwp-handler' < 'xsoar-test').
        for handler in connector.handlers:
            if handler.is_xsoar:
                handler.related_integration = _stub_related_integration(
                    "my-integration", "My Integration"
                )
            else:
                # Intentionally set a mismatching integration on the
                # non-XSOAR handler - CO122 should still skip it.
                handler.related_integration = _stub_related_integration(
                    "cwp-thing", "CWP Thing"
                )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_multiple_xsoar_handlers_all_valid_passes(self):
        """
        Given: A grouped connector with two XSOAR handlers, each with a
               matching view_group (id + label).
        When: CO122 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "view_groups": [
                    {"id": "int-one", "label": "Integration One"},
                    {"id": "int-two", "label": "Integration Two"},
                ]
            },
            handlers=[{"id": "xsoar-int-one"}, {"id": "xsoar-int-two"}],
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "int-one", "Integration One"
        )
        connector.handlers[1].related_integration = _stub_related_integration(
            "int-two", "Integration Two"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_multiple_xsoar_handlers_one_bad_id_fails(self):
        """
        Given: A grouped connector with two XSOAR handlers; the second one
               has no matching view_group.
        When: CO122 runs.
        Then: A single ValidationResult per connector, aggregating all
              handler-level issues, is returned.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "view_groups": [
                    {"id": "int-one", "label": "Integration One"},
                    # int-two intentionally missing.
                ]
            },
            handlers=[{"id": "xsoar-int-one"}, {"id": "xsoar-int-two"}],
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "int-one", "Integration One"
        )
        connector.handlers[1].related_integration = _stub_related_integration(
            "int-two", "Integration Two"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        # First handler's issue absent, second handler's issue present.
        assert "int-two" in results[0].message
        assert "xsoar-int-two" in results[0].message

    def test_empty_view_groups_with_xsoar_handler_fails(self):
        """
        Given: A grouped connector with no view_groups at all but an XSOAR
               handler that expects one.
        When: CO122 runs.
        Then: A ValidationResult is returned.
        """
        connector = _grouped_connector_with_view_groups([])
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "my-integration" in results[0].message

    def test_error_message_names_connector_and_path(self):
        """
        Given: A failing grouped connector.
        When: CO122 runs.
        Then: The message includes the connector id and the path is the
              connection.yaml file (per the CO119 pattern).
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "wrong", "label": "Wrong"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert connector.object_id in results[0].message
        assert str(results[0].path).endswith("connection.yaml")

    def test_view_group_id_verbatim_match_passes(self):
        """
        Given: A grouped connector whose XSOAR handler resolves to an
               integration and whose connection.yaml declares a
               view_group with the SAME id verbatim + matching label.
        When: CO122 runs.
        Then: No validation errors.
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "my-integration", "label": "My Integration"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_view_group_id_slugified_form_passes_when_label_matches(self):
        """
        Given: A grouped connector whose XSOAR handler resolves to an
               integration with a display-form id 'Syslog Sender' and a
               view_group whose id is the slugified form 'syslog-sender'
               with matching label.
        When: CO122 runs.
        Then: No validation errors - id comparison is lenient
              (case/space/dash/underscore/dot are all ignored).
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "syslog-sender", "label": "Syslog Sender"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "Syslog Sender", "Syslog Sender"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_view_group_id_normalization_ignores_case_space_dash_underscore_dot(self):
        """
        Given: Integration id ``Palo Alto Networks_Threat.Vault-v2`` and
               view_group id ``paloaltonetworksthreatvaultv2`` (all
               separators dropped, lowercase).
        When: CO122 runs.
        Then: No validation errors - both normalize to the same form.
        """
        connector = _grouped_connector_with_view_groups(
            [
                {
                    "id": "paloaltonetworksthreatvaultv2",
                    "label": "Palo Alto Networks Threat Vault v2",
                }
            ]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "Palo Alto Networks_Threat.Vault-v2",
            "Palo Alto Networks Threat Vault v2",
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_view_group_id_normalization_strips_parentheses_and_punctuation(self):
        """
        Given: Integration id containing parentheses, ampersand,
               question mark (e.g. ``Mail Sender (New)``,
               ``MITRE ATT&CK v2``, ``Have I Been Pwned? V2``) and a
               view_group whose id has all non-alphanumeric characters
               stripped (e.g. ``mailsendernew``, ``mitreattackv2``).
        When: CO122 runs.
        Then: No validation errors - both sides collapse to the same
              alphanumeric-only canonical form.
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "mailsendernew", "label": "Mail Sender (New)"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "Mail Sender (New)", "Mail Sender (New)"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_view_group_label_must_match_display_name_verbatim(self):
        """
        Given: view_group id normalizes to integration id (id-side is
               fine) BUT the view_group label does NOT equal
               integration.display_name verbatim.
        When: CO122 runs.
        Then: CO122 flags the label mismatch - label is customer-facing
              and MUST equal display_name verbatim (no lenient compare).
        """
        connector = _grouped_connector_with_view_groups(
            [{"id": "syslog-sender", "label": "Syslog Sender wrong"}]
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "Syslog Sender", "Syslog Sender"
        )

        validator = IsValidViewgroupValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "label='Syslog Sender wrong'" in msg
        assert "display_name" in msg


# ============================================================
# Capabilities test helpers (shared by CO176 and other capability tests)
# ============================================================


def _capabilities_payload(capabilities):
    """Build a capabilities.yaml override dict with the given capability list."""
    return {"capabilities": capabilities}


# ============================================================
# CO123 - IsProfileFieldsCoveredValidator
# ============================================================


def _profile_with_fields(profile_id: str, fields: list) -> dict:
    """Build a connection.yaml profile block with the given fields.

    Each entry in ``fields`` is a dict describing one ConnectorField
    (id, field_type, metadata, ...). All fields are placed in a single
    FieldGroup row inside ``configurations``.
    """
    return {
        "id": profile_id,
        "type": "plain",
        "title": "T",
        "configurations": [{"fields": fields}],
    }


def _xsoar_handler_using_profile(handler_id: str, profile_id: str) -> dict:
    """Build a handler override dict that references ``profile_id`` via
    ``capabilities[].auth_options[].id`` (XSOAR-owned by default)."""
    return {
        "id": handler_id,
        "capabilities": [
            {
                "id": "fetch-issues",
                "auth_options": [{"id": profile_id, "workloads": ["test-workload"]}],
            }
        ],
    }


class TestCO123IsProfileFieldsCovered:
    """Tests for CO123: every non-auth field on an XSOAR-referenced auth
    profile must have metadata.event.publish=true; ``engine_mode`` is
    the single documented exemption.
    """

    def test_all_non_auth_fields_publish_passes(self):
        """
        Given: A connector whose XSOAR-referenced profile has one auth field
               (no publish needed) and one non-auth field with publish=true.
        When: CO123 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [
                            {
                                "id": "username",
                                "field_type": "input",
                                "metadata": {"auth": {"parameter": "username"}},
                            },
                            {
                                "id": "log_level",
                                "field_type": "select",
                                "metadata": {"event": {"publish": True}},
                            },
                        ],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_non_auth_field_missing_publish_fails(self):
        """
        Given: A non-auth field on an XSOAR-referenced profile with
               no metadata.event.publish.
        When: CO123 runs.
        Then: One ValidationResult per offending field is returned.
        """
        connector = create_connector_object(
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [
                            {
                                "id": "log_level",
                                "field_type": "select",
                                # metadata absent - no publish flag at all.
                            }
                        ],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "log_level" in msg
        assert "plain.myint" in msg
        assert "publish" in msg

    def test_non_auth_field_publish_false_fails(self):
        """
        Given: A non-auth field with metadata.event.publish explicitly set
               to false.
        When: CO123 runs.
        Then: A ValidationResult is returned - publish must be exactly
              True (not merely present).
        """
        connector = create_connector_object(
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [
                            {
                                "id": "log_level",
                                "field_type": "select",
                                "metadata": {"event": {"publish": False}},
                            }
                        ],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "log_level" in results[0].message

    def test_auth_field_never_needs_publish(self):
        """
        Given: An auth field (metadata.auth.parameter set) with no
               event.publish flag.
        When: CO123 runs.
        Then: No error - auth fields are exempt because they are consumed
              by the auth flow, not published as integration params.
        """
        connector = create_connector_object(
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [
                            {
                                "id": "api_key",
                                "field_type": "input",
                                "metadata": {"auth": {"parameter": "api_key"}},
                            }
                        ],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_engine_mode_is_exempt(self):
        """
        Given: A field with id=='engine_mode' and NO event.publish.
        When: CO123 runs.
        Then: No error - engine_mode is the single documented exemption
              (UI-only field controlling the engine picker, not an
              integration param).
        """
        connector = create_connector_object(
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [{"id": "engine_mode", "field_type": "select"}],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_profile_not_referenced_by_xsoar_handler_is_skipped(self):
        """
        Given: A profile that no XSOAR handler references (only a non-XSOAR
               handler references it).
        When: CO123 runs.
        Then: No error - CO123 only enforces the rule for XSOAR-owned
              profiles.
        """
        connector = create_connector_object(
            handlers=[
                # A NON-XSOAR handler references the profile.
                {
                    "id": "cwp-handler",
                    "metadata": {"module": "cwp", "ownership": {"team": "cwp"}},
                    "capabilities": [
                        {
                            "id": "fetch-issues",
                            "auth_options": [
                                {
                                    "id": "plain.cwponly",
                                    "workloads": ["test-workload"],
                                }
                            ],
                        }
                    ],
                }
            ],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.cwponly",
                        [
                            {
                                "id": "log_level",
                                "field_type": "select",
                                # Intentionally no publish - would fail
                                # if XSOAR-referenced.
                            }
                        ],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_multiple_offenders_produce_multiple_results(self):
        """
        Given: A profile with two non-auth fields, neither has publish.
        When: CO123 runs.
        Then: Two ValidationResults are returned - one per field.
        """
        connector = create_connector_object(
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [
                            {"id": "log_level", "field_type": "select"},
                            {"id": "region", "field_type": "input"},
                        ],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 2
        offenders = {r.message.split("field '")[1].split("'")[0] for r in results}
        assert offenders == {"log_level", "region"}

    def test_no_connection_file_short_circuits(self):
        """
        Given: A connector with no ConnectorConnectionData (e.g. broken
               parse or missing connection.yaml).
        When: CO123 runs.
        Then: No error - nothing to validate.

        Uses the default fixture and then wipes ``connector.connection``
        to simulate the missing-file state cleanly.
        """
        connector = create_connector_object()
        connector.connection = None

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_grouped_namespaced_engine_mode_resolved_via_serializer_passes(self):
        """
        Given: A grouped connector whose profile exposes a NAMESPACED
               engine_mode field id (e.g. ``plain_myint_engine_mode``) with
               NO ``event.publish`` flag, and whose owning XSOAR handler's
               ``resolved_params`` (from serializer.yaml) rewrites that raw
               id to the canonical ``engine_mode``.
        When: CO123 runs.
        Then: No validation errors - the exemption must resolve namespaced
              ids through the handler's serializer before comparing to the
              canonical ``engine_mode``. This mirrors CO125/CO126 behavior
              and prevents the false positives seen on real grouped
              connectors (okta, cyberark, circl, ...).
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [
                            {
                                "id": "plain_myint_engine_mode",
                                "field_type": "radio",
                                # No event.publish - engine_mode is exempt.
                            }
                        ],
                    )
                ]
            },
        )
        # Serializer rewrite: namespaced raw id -> canonical engine_mode.
        _override_resolved(
            connector.handlers[0],
            {"plain_myint_engine_mode": "engine_mode"},
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_grouped_namespaced_engine_mode_without_serializer_fails(self):
        """
        Given: A grouped connector with a NAMESPACED engine_mode field id
               but NO serializer rewrite in ``resolved_params``.
        When: CO123 runs.
        Then: The namespaced id does not resolve to canonical
              ``engine_mode`` so the exemption does NOT apply, and CO123
              flags the field as missing publish. This proves the resolver
              path is not silently accepting raw namespaced ids without a
              serializer mapping (matches CO125/CO126 design).
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [
                            {
                                "id": "plain_myint_engine_mode",
                                "field_type": "radio",
                            }
                        ],
                    )
                ]
            },
        )
        # No _override_resolved: identity-only default.

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "plain_myint_engine_mode" in results[0].message

    def test_error_path_points_to_connection_yaml(self):
        """
        Given: A failing profile.
        When: CO123 runs.
        Then: The result path ends in connection.yaml (per CO118/CO119).
        """
        connector = create_connector_object(
            handlers=[_xsoar_handler_using_profile("xsoar-h", "plain.myint")],
            connection_data={
                "profiles": [
                    _profile_with_fields(
                        "plain.myint",
                        [{"id": "log_level", "field_type": "select"}],
                    )
                ]
            },
        )

        validator = IsProfileFieldsCoveredValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert str(results[0].path).endswith("connection.yaml")


# ============================================================
# CO190 - NoReservedParamNamesValidator
# ============================================================


class TestCO190NoReservedParamNames:
    """Tests for CO190: integrations must not use reserved param names."""

    def test_valid_no_reserved_params(self):
        """
        Given: An integration whose params use only non-reserved names.
        When: CO190 runs.
        Then: No validation errors are returned.
        """
        integration = create_integration_object()

        validator = NoReservedParamNamesValidator()
        results = validator.obtain_invalid_content_items([integration])

        assert len(results) == 0

    def test_invalid_reserved_param(self):
        """
        Given: An integration that defines a reserved param name ('engine').
        When: CO190 runs.
        Then: A validation error listing the reserved name is returned.
        """
        integration = create_integration_object(
            paths=["configuration"],
            values=[
                [
                    {"display": "Engine", "name": "engine", "type": 0},
                    {"display": "URL", "name": "server", "type": 0},
                ]
            ],
        )

        validator = NoReservedParamNamesValidator()
        results = validator.obtain_invalid_content_items([integration])

        assert len(results) == 1
        assert "engine" in results[0].message

    def test_multiple_reserved_params(self):
        """
        Given: An integration defining several reserved param names.
        When: CO190 runs.
        Then: A single ValidationResult lists every reserved name used.
        """
        integration = create_integration_object(
            paths=["configuration"],
            values=[
                [
                    {"display": "Engine", "name": "engine", "type": 0},
                    {"display": "Engine Mode", "name": "engine_mode", "type": 0},
                    {"display": "Instance Name", "name": "instance_name", "type": 0},
                    {"display": "Engine Group", "name": "enginegroup", "type": 0},
                ]
            ],
        )

        validator = NoReservedParamNamesValidator()
        results = validator.obtain_invalid_content_items([integration])

        assert len(results) == 1
        msg = results[0].message
        assert "engine" in msg
        assert "engine_mode" in msg
        assert "instance_name" in msg
        assert "enginegroup" in msg


# ============================================================
# CO124 - IsValidGroupedConnectorAuthValidator
# ============================================================


_OMIT = object()


def _profile_with_mapping(profile_id: str, mapping_value):
    """Build a profile block with an auth surface (one field carrying
    ``metadata.auth.parameter``) whose
    ``metadata.xsoar.interpolation_mapping`` is exactly ``mapping_value``.
    Pass ``_OMIT`` to omit the key entirely.

    The auth field is required so CO124's Sub-rule B (skip profiles with
    no auth surface) does NOT fire and we can exercise the mapping-value
    checks in isolation.
    """
    profile: dict = {
        "id": profile_id,
        "type": "plain",
        "title": "T",
        "configurations": [
            {
                "fields": [
                    {
                        "id": "u",
                        "field_type": "input",
                        "metadata": {"auth": {"parameter": "username"}},
                    }
                ]
            }
        ],
    }
    if mapping_value is _OMIT:
        profile["metadata"] = {"xsoar": {}}
    else:
        profile["metadata"] = {"xsoar": {"interpolation_mapping": mapping_value}}
    return profile


def _profile_without_auth_surface(profile_id: str, mapping_value=_OMIT):
    """Build a profile with ONLY framework fields (no
    ``metadata.auth.parameter`` on any field, no ``vault_mappings``).
    Used to exercise CO124's Sub-rule B skip guard.
    """
    profile: dict = {
        "id": profile_id,
        "type": "passthrough",
        "title": "No Auth",
        "configurations": [
            {"fields": [{"id": "proxy", "field_type": "checkbox"}]},
            {"fields": [{"id": "insecure", "field_type": "checkbox"}]},
            {"fields": [{"id": "engine_mode", "field_type": "radio"}]},
        ],
    }
    if mapping_value is _OMIT:
        profile["metadata"] = {"xsoar": {"interpolated": True}}
    else:
        profile["metadata"] = {
            "xsoar": {
                "interpolated": True,
                "interpolation_mapping": mapping_value,
            }
        }
    return profile


class TestCO124IsValidGroupedConnectorAuth:
    """Tests for CO124: every profile in a grouped connector must declare
    a non-empty metadata.xsoar.interpolation_mapping string.
    """

    def test_non_grouped_short_circuits(self):
        """
        Given: A standard (non-grouped) connector whose profile has NO
               interpolation_mapping.
        When: CO124 runs.
        Then: No errors - CO124 is grouped-only.
        """
        connector = create_connector_object(
            connection_data={"profiles": [_profile_with_mapping("plain.x", _OMIT)]}
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_grouped_with_valid_mapping_passes(self):
        """
        Given: A grouped connector whose profile has a non-empty
               interpolation_mapping.
        When: CO124 runs.
        Then: No errors.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    _profile_with_mapping("plain.x", "username:credentials.identifier")
                ]
            },
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_grouped_with_missing_mapping_fails(self):
        """
        Given: A grouped connector whose profile has metadata.xsoar but
               no interpolation_mapping key at all.
        When: CO124 runs.
        Then: One ValidationResult naming the profile and 'missing'.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={"profiles": [_profile_with_mapping("plain.x", _OMIT)]},
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "plain.x" in results[0].message
        assert "missing" in results[0].message

    def test_grouped_with_empty_string_mapping_fails(self):
        """
        Given: A grouped connector whose profile has
               interpolation_mapping="" (present but empty).
        When: CO124 runs.
        Then: One ValidationResult naming the profile and 'empty'.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={"profiles": [_profile_with_mapping("plain.x", "")]},
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "plain.x" in results[0].message
        assert "empty" in results[0].message

    def test_grouped_with_whitespace_only_mapping_fails(self):
        """
        Given: A grouped connector whose profile has
               interpolation_mapping="   " (whitespace only).
        When: CO124 runs.
        Then: One ValidationResult (treated as empty).
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={"profiles": [_profile_with_mapping("plain.x", "   ")]},
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "empty" in results[0].message

    def test_grouped_with_multiple_profiles_reports_all_offenders(self):
        """
        Given: A grouped connector with 3 profiles - one good, one
               missing mapping, one empty mapping.
        When: CO124 runs.
        Then: 2 ValidationResults are returned, one per offender.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    _profile_with_mapping("plain.good", "u:v"),
                    _profile_with_mapping("plain.missing", _OMIT),
                    _profile_with_mapping("plain.empty", ""),
                ]
            },
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 2
        messages = [r.message for r in results]
        assert any("plain.missing" in m and "missing" in m for m in messages)
        assert any("plain.empty" in m and "empty" in m for m in messages)
        assert not any("plain.good" in m for m in messages)

    def test_error_path_points_to_connection_yaml(self):
        """
        Given: A failing grouped connector.
        When: CO124 runs.
        Then: The result path ends in connection.yaml (per CO118/CO119).
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={"profiles": [_profile_with_mapping("plain.x", _OMIT)]},
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert str(results[0].path).endswith("connection.yaml")

    def test_no_connection_short_circuits(self):
        """
        Given: A grouped connector with no ConnectorConnectionData
               (missing/broken connection.yaml).
        When: CO124 runs.
        Then: No errors - nothing to validate.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}}
        )
        connector.connection = None

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    # ------------------------------------------------------------------
    # Sub-rule B: skip profiles with no auth surface.
    # Regression coverage for the 39 real-world false-positives seen in
    # unified-connectors-content (passthrough feed profiles + external_auth
    # "No Authentication Required" tiles).
    # ------------------------------------------------------------------

    def test_grouped_passthrough_without_auth_surface_is_skipped(self):
        """
        Given: A grouped connector with a passthrough profile that
               exposes ONLY framework fields (proxy / insecure /
               engine_mode) and NO metadata.xsoar.interpolation_mapping.
               This mirrors the shape of ~35 real intel-feed profiles
               (e.g. passthrough.nmap, passthrough.dnstwist,
               passthrough.tor_exit_addresses_feed).
        When: CO124 runs.
        Then: No errors - Sub-rule B skips profiles with no auth surface.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [_profile_without_auth_surface("passthrough.nmap_like")]
            },
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_grouped_external_auth_without_auth_surface_is_skipped(self):
        """
        Given: A grouped connector with an external_auth "No
               Authentication Required" tile (no auth fields, no mapping).
               Mirrors external_auth.dbot_truth_bombs,
               external_auth.sample_incident_generator,
               external_auth.zoom_feed.
        When: CO124 runs.
        Then: No errors - Sub-rule B skips.
        """
        profile = _profile_without_auth_surface("external_auth.no_auth_tile")
        profile["type"] = "external_auth"
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={"profiles": [profile]},
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_grouped_profile_with_vault_mappings_still_requires_mapping(self):
        """
        Given: A grouped connector with a passthrough profile that has
               NO field-level auth.parameter but DOES declare
               ``vault_mappings`` (so it draws credentials from a vault).
               The mapping is missing.
        When: CO124 runs.
        Then: One ValidationResult - vault_mappings counts as an auth
              surface, so Sub-rule B does NOT skip and the missing
              mapping is flagged.
        """
        profile = _profile_without_auth_surface("passthrough.vault_only")
        profile["vault_mappings"] = [
            {
                "id": "credentials",
                "map": {"user": "client_id", "password": "client_secret"},
            }
        ]
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={"profiles": [profile]},
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "passthrough.vault_only" in results[0].message
        assert "missing" in results[0].message

    def test_grouped_mixed_profiles_only_reports_ones_with_auth_surface(self):
        """
        Given: A grouped connector with 3 profiles:
                 - one passthrough feed (no auth surface, no mapping)  -> skip
                 - one profile with an auth field and a valid mapping  -> ok
                 - one profile with an auth field but NO mapping        -> ERROR
        When: CO124 runs.
        Then: Exactly one ValidationResult, naming the third profile.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    _profile_without_auth_surface("passthrough.feed"),
                    _profile_with_mapping(
                        "plain.ok", "username:credentials.identifier"
                    ),
                    _profile_with_mapping("plain.needs_mapping", _OMIT),
                ]
            },
        )

        validator = IsValidGroupedConnectorAuthValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "plain.needs_mapping" in results[0].message
        assert "missing" in results[0].message
        # The auth-less passthrough feed must NOT appear.
        assert "passthrough.feed" not in results[0].message


# ============================================================
# CO125 - IsAuthProfileHasEngineValidator
# ============================================================


def _engine_field(field_id: str) -> dict:
    """Minimal engine-triplet field dict."""
    return {"id": field_id, "field_type": "select"}


def _standard_general_configurations(field_ids: list) -> dict:
    """Build a connection.yaml general_configurations block containing
    the given field ids as a single FieldGroup."""
    return {
        "description": "Common configs",
        "configurations": [
            {"fields": [_engine_field(fid) for fid in field_ids]},
        ],
    }


def _grouped_profile(profile_id: str, field_ids: list) -> dict:
    """Grouped-connector profile block with the given field ids inside
    its own ``configurations``."""
    return {
        "id": profile_id,
        "type": "plain",
        "title": "T",
        "configurations": [
            {"fields": [_engine_field(fid) for fid in field_ids]},
        ],
    }


class TestCO125IsAuthProfileHasEngine:
    """Tests for CO125: every auth profile must expose the engine triplet
    (``engine_mode``, ``engine``, ``engine_group`` / ``engineGroup``).

    Grouped connectors: checked per-profile inside
    ``profile.configurations``. Standard connectors: checked once at
    ``connection.general_configurations``. Appendix G integrations
    (EDL, TAXII Server, etc.) are skipped by CO125 - CO127 handles them.
    """

    # ------------------------------------------------------------------
    # Standard (non-grouped) - general_configurations
    # ------------------------------------------------------------------

    def test_standard_all_three_engine_ids_passes(self):
        """
        Given: A standard connector whose general_configurations exposes
               engine_mode, engine, AND engine_group.
        When: CO125 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_general_configurations(
                    ["engine_mode", "engine", "engine_group"]
                ),
            }
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_standard_accepts_camelcase_engine_group(self):
        """
        Given: A standard connector using the camelCase ``engineGroup``
               spelling instead of ``engine_group``.
        When: CO125 runs.
        Then: No validation errors are returned - both spellings accepted.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_general_configurations(
                    ["engine_mode", "engine", "engineGroup"]
                ),
            }
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_standard_missing_engine_mode_fails(self):
        """
        Given: A standard connector whose general_configurations has
               ``engine`` + ``engine_group`` but NO ``engine_mode``.
        When: CO125 runs.
        Then: A single ValidationResult naming ``engine_mode`` as missing.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_general_configurations(
                    ["engine", "engine_group"]
                ),
            }
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "engine_mode" in msg
        assert "general_configurations" in msg

    def test_standard_missing_engine_fails(self):
        """
        Given: A standard connector missing ``engine`` from
               general_configurations.
        When: CO125 runs.
        Then: A ValidationResult naming ``engine`` as missing.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_general_configurations(
                    ["engine_mode", "engine_group"]
                ),
            }
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "'engine'" in results[0].message

    def test_standard_missing_engine_group_fails(self):
        """
        Given: A standard connector missing engine_group (both spellings)
               from general_configurations.
        When: CO125 runs.
        Then: A ValidationResult naming ``engine_group`` as missing.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_general_configurations(
                    ["engine_mode", "engine"]
                ),
            }
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "engine_group" in results[0].message

    def test_standard_missing_all_three_lists_all_three(self):
        """
        Given: A standard connector with an empty general_configurations
               (no engine fields at all).
        When: CO125 runs.
        Then: A single ValidationResult naming all three engine ids.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": {
                    "description": "empty",
                    "configurations": [],
                },
            }
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "engine_mode" in msg
        assert "'engine'" in msg
        assert "engine_group" in msg

    def test_standard_no_general_configurations_fails(self):
        """
        Given: A standard connector whose connection.yaml has NO
               general_configurations block at all.
        When: CO125 runs.
        Then: A ValidationResult - the engine picker is required.
        """
        connector = create_connector_object()
        # Sanity: default fixture has no general_configurations.
        assert (
            connector.connection is not None
            and connector.connection.general_configurations is None
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "general_configurations" in results[0].message

    # ------------------------------------------------------------------
    # Grouped - per-profile
    # ------------------------------------------------------------------

    def test_grouped_all_profiles_have_engine_triplet_passes(self):
        """
        Given: A grouped connector whose single profile exposes all three
               engine ids inside ``profile.configurations``.
        When: CO125 runs.
        Then: No validation errors.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    _grouped_profile(
                        "plain.myint",
                        ["engine_mode", "engine", "engine_group"],
                    )
                ]
            },
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_grouped_profile_missing_engine_params_fails(self):
        """
        Given: A grouped connector whose profile has no engine fields.
        When: CO125 runs.
        Then: A single ValidationResult naming the profile id.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [_grouped_profile("plain.myint", ["username", "password"])]
            },
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "plain.myint" in msg
        assert "engine_mode" in msg

    def test_grouped_multiple_profiles_reports_each_offender(self):
        """
        Given: A grouped connector with two profiles, one good and one bad.
        When: CO125 runs.
        Then: Exactly one ValidationResult - the bad profile.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    _grouped_profile(
                        "plain.good",
                        ["engine_mode", "engine", "engine_group"],
                    ),
                    _grouped_profile(
                        "plain.bad",
                        ["username"],
                    ),
                ]
            },
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "plain.bad" in results[0].message
        assert "plain.good" not in results[0].message

    # ------------------------------------------------------------------
    # Appendix G exclusion + short-circuits
    # ------------------------------------------------------------------

    def test_appendix_g_integration_is_skipped(self):
        """
        Given: A standard connector whose XSOAR handler resolves to an
               integration on the Appendix G engine/proxy exclusion list
               (here: 'TAXII Server'), and its general_configurations
               deliberately omits every engine field.
        When: CO125 runs.
        Then: No validation errors - Appendix G integrations are
              excluded from CO125; CO127 validates the opposite direction.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_general_configurations(
                    ["some_other_field"]
                ),
            }
        )
        # Wire the XSOAR handler to an Appendix G integration id.
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="TAXII Server",
            display_name="TAXII Server",
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_appendix_g_normalization_matches_hyphens_and_case(self):
        """
        Given: An XSOAR handler resolving to 'aws-sns-listener' (Appendix G
               entry stored as 'AWS-SNS-Listener').
        When: CO125 runs.
        Then: Normalization matches - connector is skipped, no results.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_general_configurations(
                    ["some_other_field"]
                ),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="aws-sns-listener",
            display_name="AWS SNS Listener",
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_no_connection_short_circuits(self):
        """
        Given: A connector with no ConnectorConnectionData (missing or
               broken connection.yaml).
        When: CO125 runs.
        Then: No errors - nothing to validate.
        """
        connector = create_connector_object()
        connector.connection = None

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_error_path_points_to_connection_yaml(self):
        """
        Given: A failing standard connector.
        When: CO125 runs.
        Then: The result path ends in connection.yaml (per CO118/CO119).
        """
        connector = create_connector_object()
        # Default fixture has no general_configurations - guaranteed fail.

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert str(results[0].path).endswith("connection.yaml")

    # ------------------------------------------------------------------
    # Grouped serializer resolution (regression: raw namespaced ids
    # from grouped connectors like Qualys were false-positived before
    # CO125 was retrofitted to consult handler.resolved_params).
    # ------------------------------------------------------------------

    def test_grouped_namespaced_ids_resolved_via_serializer_pass(self):
        """
        Given: A grouped connector whose profile exposes NAMESPACED engine
               field ids (e.g. ``plain_qualys_fim_engine_mode``) - as
               happens on real disk for grouped connectors like Qualys -
               and whose owning XSOAR handler's ``resolved_params`` (built
               from serializer.yaml at parse time) rewrites those ids to
               the canonical ``engine_mode`` / ``engine`` / ``engineGroup``.
        When: CO125 runs.
        Then: No validation errors - CO125 must resolve raw connection.yaml
              ids through the handler's serializer before checking presence
              of the engine triplet. Historically CO125 did an exact-id
              match against the connection.yaml, which false-positived
              every grouped connector on disk.
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            handlers=[
                _xsoar_handler_using_profile("xsoar-h", "plain.myint"),
            ],
            connection_data={
                "profiles": [
                    _grouped_profile(
                        "plain.myint",
                        [
                            # Raw ids, namespaced with the profile prefix.
                            "plain_myint_engine_mode",
                            "plain_myint_engine",
                            "plain_myint_engineGroup",
                        ],
                    )
                ]
            },
        )
        # Serializer field_mappings simulation: raw namespaced ids ->
        # canonical integration param names (what parser produces from
        # serializer.yaml).
        _override_resolved(
            connector.handlers[0],
            {
                "plain_myint_engine_mode": "engine_mode",
                "plain_myint_engine": "engine",
                "plain_myint_engineGroup": "engineGroup",
            },
        )

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_grouped_namespaced_ids_without_resolver_fail_reported(self):
        """
        Given: A grouped connector with NAMESPACED engine ids but NO
               serializer rewrite in ``resolved_params`` (either no
               serializer.yaml on disk, or the mapping is incomplete).
        When: CO125 runs.
        Then: The namespaced ids do NOT match the canonical engine ids
              and CO125 reports the profile as missing all three engine
              params. This proves the resolver is not silently accepting
              raw namespaced ids - it explicitly requires the serializer
              rewrite (which is the design intent).
        """
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            handlers=[
                _xsoar_handler_using_profile("xsoar-h", "plain.myint"),
            ],
            connection_data={
                "profiles": [
                    _grouped_profile(
                        "plain.myint",
                        [
                            "plain_myint_engine_mode",
                            "plain_myint_engine",
                            "plain_myint_engineGroup",
                        ],
                    )
                ]
            },
        )
        # No _override_resolved call: default resolved_params come from
        # the parser and are identity-only (no serializer.yaml written by
        # create_connector_object).

        validator = IsAuthProfileHasEngineValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "plain.myint" in msg
        assert "engine_mode" in msg


# ============================================================
# CO126 - IsValidEngineParamsValidator
# ============================================================


def _canonical_engine_mode_field(field_id: str = "engine_mode") -> dict:
    """A minimal but spec-compliant engine_mode field dict.

    Matches the canonical Qualys shape: radio, horizontal, 3 keys.
    """
    return {
        "id": field_id,
        "field_type": "radio",
        "options": {
            "orientation": "horizontal",
            "values": [
                {"key": "no_engine", "label": "No engine"},
                {"key": "engine", "label": "Engine"},
                {"key": "engineGroup", "label": "Engine Group"},
            ],
        },
    }


def _canonical_engine_field(
    field_id: str = "engine",
    integration_id: str = "MyInt",
    dynamic_field: str = "engine",
) -> dict:
    """A minimal spec-compliant engine/engineGroup select field."""
    return {
        "id": field_id,
        "field_type": "select",
        "metadata": {
            "xsoar": {"config_type": "backend"},
            "dynamic_values": {
                "provider": "xsoar",
                "trigger": ["on_create", "on_edit"],
                "params": {
                    "integrationID": integration_id,
                    "dynamicField": dynamic_field,
                },
            },
        },
    }


def _canonical_engine_triplet(integration_id: str = "MyInt") -> list:
    """The three engine fields in the order they appear on disk."""
    return [
        _canonical_engine_mode_field(),
        _canonical_engine_field("engine", integration_id, "engine"),
        _canonical_engine_field("engineGroup", integration_id, "engine-group"),
    ]


def _standard_engine_gc(triplet: list) -> dict:
    """Wrap an engine triplet as a general_configurations block."""
    return {
        "description": "Common configs",
        "configurations": [{"fields": triplet}],
    }


class TestCO126IsValidEngineParams:
    """Tests for CO126: engine triplet field-shape conformance.

    CO125 (presence) is a prerequisite; CO126 only inspects fields that
    are already there. Sub-rules covered: A/B/C engine_mode shape,
    D same-FieldGroup, E field_type, F config_type, G/H/I dynamic_values.
    """

    # ------------------------------------------------------------------
    # Happy paths + short-circuits
    # ------------------------------------------------------------------

    def test_standard_canonical_triplet_passes(self):
        """
        Given: A standard connector whose general_configurations exposes
               a fully spec-compliant engine triplet.
        When: CO126 runs.
        Then: No validation errors.
        """
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(
                    _canonical_engine_triplet("MyInt")
                ),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )

        validator = IsValidEngineParamsValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert results == []

    def test_no_engine_fields_short_circuits(self):
        """
        Given: A standard connector with no engine fields at all
               (CO125's territory, not CO126's).
        When: CO126 runs.
        Then: No validation errors - CO126 only inspects fields present.
        """
        connector = create_connector_object()
        validator = IsValidEngineParamsValidator()
        results = validator.obtain_invalid_content_items([connector])
        assert results == []

    def test_no_connection_short_circuits(self):
        """
        Given: A connector with no ConnectorConnectionData.
        When: CO126 runs.
        Then: No errors.
        """
        connector = create_connector_object()
        connector.connection = None
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_appendix_g_integration_is_skipped(self):
        """
        Given: A connector whose XSOAR handler resolves to an Appendix G
               integration (e.g. TAXII Server) - even with a broken
               triplet, CO126 must skip it (CO127 covers those).
        When: CO126 runs.
        Then: No errors.
        """
        broken = _canonical_engine_triplet("MyInt")
        broken[0]["field_type"] = "input"  # broken engine_mode
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(broken),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="TAXII Server", display_name="TAXII Server"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_appendix_h_integration_skips_options_key_set_check(self):
        """
        Given: A connector whose XSOAR handler resolves to an Appendix H
               (single-engine) integration and whose engine_mode.options
               has ONLY 2 keys (no_engine + engine). CO128 enforces the
               2-key shape; CO126 must NOT double-flag it under sub-rule C.
        When: CO126 runs (all other sub-rules still evaluated).
        Then: The options-keys mismatch is NOT reported. Any OTHER
              violation would still be reported.
        """
        # Use the same integration id in the field as the handler will
        # resolve to; the H-appendix opt-out only silences sub-rule C
        # (option-key-set), not sub-rule H (integrationID match).
        triplet = _canonical_engine_triplet("Slack")
        # Trim to 2 keys (Appendix H shape).
        triplet[0]["options"]["values"] = [
            {"key": "no_engine", "label": "No engine"},
            {"key": "engine", "label": "Engine"},
        ]
        # Drop engineGroup entirely too (Appendix H doesn't emit it).
        triplet = triplet[:2]
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="Slack", display_name="Slack"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------------
    # engine_mode sub-rules (A, B, C)
    # ------------------------------------------------------------------

    def test_engine_mode_wrong_field_type_fails(self):
        """A: engine_mode must be a radio."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[0]["field_type"] = "select"
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "engine_mode field_type must be 'radio'" in results[0].message

    def test_engine_mode_wrong_orientation_fails(self):
        """B: engine_mode.options.orientation must be horizontal."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[0]["options"]["orientation"] = "vertical"
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "orientation must be 'horizontal'" in results[0].message

    def test_engine_mode_wrong_options_keys_fails(self):
        """C: engine_mode.options.values keys must be exactly the set."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[0]["options"]["values"] = [
            {"key": "no_engine", "label": "No engine"},
            {"key": "wrong_key", "label": "Wrong"},
        ]
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "engine_mode.options.values keys" in msg
        assert "wrong_key" in msg

    # ------------------------------------------------------------------
    # Same FieldGroup (D)
    # ------------------------------------------------------------------

    def test_engine_fields_split_across_groups_fails(self):
        """D: all three engine fields must live in the same FieldGroup."""
        triplet = _canonical_engine_triplet("MyInt")
        # Split: engine_mode in one group, engine + engineGroup in another.
        connector = create_connector_object(
            connection_data={
                "general_configurations": {
                    "description": "d",
                    "configurations": [
                        {"fields": [triplet[0]]},
                        {"fields": triplet[1:]},
                    ],
                }
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "same FieldGroup" in results[0].message

    # ------------------------------------------------------------------
    # engine / engineGroup sub-rules (E, F, G, H, I, J)
    # ------------------------------------------------------------------

    def test_engine_wrong_field_type_fails(self):
        """E: engine.field_type must be select."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[1]["field_type"] = "input"
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "engine field_type must be 'select'" in results[0].message

    def test_engine_wrong_config_type_fails(self):
        """F: metadata.xsoar.config_type must be backend."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[1]["metadata"]["xsoar"]["config_type"] = "frontend"
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "config_type must be 'backend'" in results[0].message

    def test_engine_missing_dynamic_values_fails(self):
        """G: metadata.dynamic_values must be present."""
        triplet = _canonical_engine_triplet("MyInt")
        del triplet[1]["metadata"]["dynamic_values"]
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "engine metadata.dynamic_values is missing" in results[0].message

    def test_engine_wrong_provider_fails(self):
        """G: dynamic_values.provider must be xsoar."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[1]["metadata"]["dynamic_values"]["provider"] = "external"
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "provider must be 'xsoar'" in results[0].message

    def test_engine_missing_on_edit_trigger_fails(self):
        """G: trigger set must contain BOTH on_create and on_edit."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[1]["metadata"]["dynamic_values"]["trigger"] = ["on_create"]
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "on_edit" in results[0].message

    def test_engine_wrong_integration_id_fails(self):
        """H: params.integrationID must match handler's integration."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[1]["metadata"]["dynamic_values"]["params"]["integrationID"] = "OtherInt"
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "integrationID" in msg
        assert "OtherInt" in msg

    def test_engine_group_wrong_dynamic_field_fails(self):
        """I: engineGroup.dynamicField must be 'engine-group'."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[2]["metadata"]["dynamic_values"]["params"]["dynamicField"] = "engine"
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "engine_group" in msg
        assert "'engine-group'" in msg

    # ------------------------------------------------------------------
    # Grouped connector (serializer rewrites)
    # ------------------------------------------------------------------

    def test_grouped_namespaced_ids_pass_after_serializer_resolution(self):
        """Grouped connector where connection.yaml has NAMESPACED ids
        that the handler's serializer rewrites back to the canonical
        engine_mode / engine / engineGroup. CO126 must find and inspect
        the engine fields via the resolved names.
        """
        triplet = _canonical_engine_triplet("MyInt")
        # Namespace the ids.
        triplet[0]["id"] = "plain_myint_engine_mode"
        triplet[1]["id"] = "plain_myint_engine"
        triplet[2]["id"] = "plain_myint_engineGroup"

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            handlers=[
                _xsoar_handler_using_profile("xsoar-h", "plain.myint"),
            ],
            connection_data={
                "profiles": [
                    _grouped_profile("plain.myint", []),
                ]
            },
        )
        # Replace the auto-created empty profile fields with the
        # namespaced triplet.
        from demisto_sdk.commands.content_graph.objects.connector import (
            ConnectorField,
            FieldGroup,
        )

        connector.connection.profiles[0].configurations = [
            FieldGroup(fields=[ConnectorField(**f) for f in triplet])
        ]
        # Wire the serializer mapping + resolved integration.
        _override_resolved(
            connector.handlers[0],
            {
                "plain_myint_engine_mode": "engine_mode",
                "plain_myint_engine": "engine",
                "plain_myint_engineGroup": "engineGroup",
            },
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )

        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------------
    # Error path + connector id in message
    # ------------------------------------------------------------------

    def test_error_path_points_to_connection_yaml(self):
        """Error path is connection.yaml (per CO118/CO119 pattern)."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[0]["field_type"] = "select"  # break engine_mode
        connector = create_connector_object(
            connection_data={
                "general_configurations": _standard_engine_gc(triplet),
            }
        )
        connector.handlers[0].related_integration = SimpleNamespace(
            object_id="MyInt", display_name="My Int"
        )
        results = IsValidEngineParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert str(results[0].path).endswith("connection.yaml")
        assert connector.object_id in results[0].message


# ============================================================
# CO129 - IsValidConfigurationsMetadataValidator
# ============================================================


def _write_configurations_yaml(
    connector,
    title: str = "Configuration",
    description: str = "Adjust and refine your configuration settings",
    include_metadata: bool = True,
) -> None:
    """Write a minimal configurations.yaml onto the connector's on-disk
    directory (the temp dir created by create_connector_object). The
    validator reads configurations_file.file_content which will pick this
    up on first access.

    Pass ``include_metadata=False`` to write a valid YAML but omit the
    metadata block entirely.
    """
    import yaml as _yaml

    conn_dir = connector.path
    if conn_dir.is_file():
        conn_dir = conn_dir.parent
    payload: dict = {}
    if include_metadata:
        payload["metadata"] = {"title": title, "description": description}
    payload["view_groups"] = []
    with open(conn_dir / "configurations.yaml", "w") as f:
        _yaml.dump(payload, f)


class TestCO129IsValidConfigurationsMetadata:
    """Tests for CO129: configurations.yaml metadata block must expose
    ``title == 'Configuration'`` AND
    ``description == 'Adjust and refine your configuration settings'``.
    """

    def test_valid_metadata_passes(self):
        """
        Given: A connector with a spec-compliant configurations.yaml
               metadata block.
        When: CO129 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        _write_configurations_yaml(connector)
        results = IsValidConfigurationsMetadataValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_missing_configurations_file_short_circuits(self):
        """
        Given: A connector with NO configurations.yaml on disk (many
               connectors legitimately don't have one).
        When: CO129 runs.
        Then: No errors - nothing to validate.
        """
        connector = create_connector_object()
        # Explicitly do NOT write configurations.yaml.
        results = IsValidConfigurationsMetadataValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_wrong_title_fails(self):
        """B: title is wrong."""
        connector = create_connector_object()
        _write_configurations_yaml(connector, title="Config")
        results = IsValidConfigurationsMetadataValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "metadata.title must be 'Configuration'" in msg
        assert "'Config'" in msg
        assert str(results[0].path).endswith("configurations.yaml")

    def test_wrong_description_fails(self):
        """
        Given: A connector whose configurations.yaml uses the shorter
               'Adjust and refine your configuration' (matches the
               manifest text but NOT the enforced disk consensus).
        When: CO129 runs.
        Then: A ValidationResult is returned - CO129 enforces the disk
              consensus with the trailing 'settings' word.
        """
        connector = create_connector_object()
        _write_configurations_yaml(
            connector,
            description="Adjust and refine your configuration",
        )
        results = IsValidConfigurationsMetadataValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "metadata.description must be" in msg
        assert "'Adjust and refine your configuration settings'" in msg

    def test_both_wrong_aggregates_into_single_result(self):
        """
        Given: A connector whose configurations.yaml has both wrong
               title AND wrong description.
        When: CO129 runs.
        Then: A single ValidationResult with BOTH sub-rule failures
              aggregated into the message.
        """
        connector = create_connector_object()
        _write_configurations_yaml(
            connector,
            title="Wrong Title",
            description="Wrong description",
        )
        results = IsValidConfigurationsMetadataValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "metadata.title must be" in msg
        assert "metadata.description must be" in msg

    def test_metadata_block_absent_fails(self):
        """
        Given: A connector whose configurations.yaml exists but has no
               top-level ``metadata`` block at all.
        When: CO129 runs.
        Then: A single ValidationResult explaining that metadata is
              missing / not a mapping.
        """
        connector = create_connector_object()
        _write_configurations_yaml(connector, include_metadata=False)
        results = IsValidConfigurationsMetadataValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "metadata block is missing or not a mapping" in results[0].message

    def test_error_message_names_connector(self):
        """Message includes the connector id (per CO118 pattern)."""
        connector = create_connector_object()
        _write_configurations_yaml(connector, title="Wrong")
        results = IsValidConfigurationsMetadataValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert connector.object_id in results[0].message


# ============================================================
# CO130 test helpers
# ============================================================
def _write_connector_yaml_file(connector, filename: str, payload: dict) -> None:
    """Write ``filename`` (e.g. 'configurations.yaml') into the on-disk
    directory that backs ``connector`` (the temp dir made by
    ``create_connector_object``). The validator's related_file accessors
    read the file lazily so writing after parse is fine.
    """
    import yaml as _yaml

    conn_dir = connector.path
    if conn_dir.is_file():
        conn_dir = conn_dir.parent
    with open(conn_dir / filename, "w") as f:
        _yaml.dump(payload, f)


def _fetch_issues_capability_entry(
    capability_id: str = "fetch-issues",
    include_incidentType: bool = True,
    include_incidentFetchInterval: bool = True,
    include_incomingMapperId: bool = True,
    include_mappingId: bool = True,
    incidentType_type: str = "select",
    incidentType_dyn: str = "incident-type",
    incidentFetchInterval_type: str = "duration",
    incomingMapperId_type: str = "select",
    incomingMapperId_dyn: str = "mapper-incoming",
    mappingId_type: str = "select",
    mappingId_dyn: str = "classifier",
) -> dict:
    """Build a raw configurations.yaml `configurations[]` entry dict for
    the fetch-issues capability, letting each sub-check be individually
    perturbed for negative tests."""
    fields = []
    if include_incidentType:
        fields.append(
            {
                "id": "incidentType",
                "title": "Issue Type",
                "field_type": incidentType_type,
                "metadata": {
                    "dynamic_values": {
                        "provider": "xsoar",
                        "trigger": ["on_create", "on_edit"],
                        "params": {
                            "integrationID": "TestIntegration",
                            "dynamicField": incidentType_dyn,
                        },
                    }
                },
            }
        )
    if include_incidentFetchInterval:
        fields.append(
            {
                "id": "incidentFetchInterval",
                "title": "Issues Fetch Interval",
                "field_type": incidentFetchInterval_type,
                "options": {
                    "units": ["days", "hours", "minutes"],
                    "output_format": "minutes",
                    "default_value": {"minutes": 1},
                },
            }
        )
    if include_incomingMapperId:
        fields.append(
            {
                "id": "incomingMapperId",
                "title": "Incoming Mapper",
                "field_type": incomingMapperId_type,
                "metadata": {
                    "dynamic_values": {
                        "provider": "xsoar",
                        "trigger": ["on_create", "on_edit"],
                        "params": {
                            "integrationID": "TestIntegration",
                            "dynamicField": incomingMapperId_dyn,
                        },
                    },
                    "xsoar": {"config_type": "backend"},
                },
            }
        )
    if include_mappingId:
        fields.append(
            {
                "id": "mappingId",
                "title": "Classifier",
                "field_type": mappingId_type,
                "metadata": {
                    "dynamic_values": {
                        "provider": "xsoar",
                        "trigger": ["on_create", "on_edit"],
                        "params": {
                            "integrationID": "TestIntegration",
                            "dynamicField": mappingId_dyn,
                        },
                    },
                    "xsoar": {"config_type": "backend"},
                },
            }
        )
    return {
        "id": capability_id,
        "configurations": [{"fields": fields}],
    }


def _write_configurations_with_fetch_issues(
    connector, capability_id: str = "fetch-issues", **field_overrides
) -> None:
    """Write a configurations.yaml with a fetch-issues capability entry."""
    entry = _fetch_issues_capability_entry(
        capability_id=capability_id, **field_overrides
    )
    _write_connector_yaml_file(
        connector,
        "configurations.yaml",
        {
            "metadata": {
                "title": "Configuration",
                "description": "Adjust and refine your configuration settings",
            },
            "view_groups": [],
            "configurations": [entry],
        },
    )


def _make_valid_serializer(capability_id: str = "fetch-issues"):
    """Build a SerializerData model with the correct computed_fields
    isFetch rule for the given capability id."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        ComputedCondition,
        ComputedConditionGroup,
        ComputedFieldRule,
        ComputedOutput,
        SerializerData,
    )

    return SerializerData(
        field_mappings=[],
        computed_fields=[
            ComputedFieldRule(
                output=[ComputedOutput(id="isFetch", value=True)],
                any_of=[
                    ComputedConditionGroup(
                        conditions=[
                            ComputedCondition(
                                type="capability",
                                options={
                                    "capability_id": capability_id,
                                    "value": "on",
                                },
                            )
                        ]
                    )
                ],
            )
        ],
    )


def _wire_handler_for_fetch_issues(
    connector,
    capability_id: str = "fetch-issues",
    serializer=None,
    handler_index: int = 0,
) -> None:
    """Point ``connector.handlers[handler_index]`` at ``capability_id``
    (adding it as a HandlerCapability) and attach ``serializer`` (or
    the default valid serializer). Marks the handler as XSOAR-owned so
    it participates in CO130's iteration."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        HandlerCapability,
    )

    handler = connector.handlers[handler_index]
    handler.metadata.module = "xsoar"
    handler.capabilities = [
        HandlerCapability(
            id=capability_id,
            auth_options=[],
            workloads=[],
            actions=[],
        )
    ]
    handler.serializer = _make_valid_serializer(capability_id=capability_id)
    if serializer is not None:
        handler.serializer = serializer


class TestCO130IsValidFetch:
    """Tests for CO130: fetch-issues capability wiring.

    Two parts per subscribing XSOAR handler:
    - Part 1: serializer.yaml computed_fields emit `isFetch: true`
      under capability condition `<cap_id> == on`.
    - Part 2: configurations.yaml has an entry with id == cap_id,
      containing incidentType/incidentFetchInterval/incomingMapperId/
      mappingId with correct field_type + dynamicField.
    """

    # ------------------------------------------------------------
    # Skip / no-op cases
    # ------------------------------------------------------------
    def test_no_fetch_issues_capability_short_circuits(self):
        """A connector whose handlers don't subscribe to fetch-issues
        produces no results."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        # default handler subscribes to "test-capability", not fetch-issues
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert results == []

    def test_non_xsoar_handler_is_skipped(self):
        """A fully non-XSOAR handler subscribing to fetch-issues is
        NOT checked. ``is_xsoar`` is an OR of {module, team,
        maintainers} — all three signals must be non-xsoar for the
        handler to be treated as non-XSOAR."""
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerCapability,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        # Override all three xsoar signals so is_xsoar is False.
        handler.metadata.module = "third_party"
        handler.metadata.ownership.team = "third_party"
        handler.metadata.ownership.maintainers = ["@third-party-content"]
        handler.capabilities = [
            HandlerCapability(
                id="fetch-issues", auth_options=[], workloads=[], actions=[]
            )
        ]
        handler.serializer = None  # would fail Part 1 if it were XSOAR
        # No configurations.yaml either - would fail Part 2 if XSOAR
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert results == []

    # ------------------------------------------------------------
    # Fully-valid happy path
    # ------------------------------------------------------------
    def test_valid_fetch_issues_wiring_passes(self):
        """XSOAR handler subscribes to fetch-issues, serializer emits
        isFetch, configurations.yaml has the required 4 fields."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(connector)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert results == []

    def test_valid_grouped_namespaced_capability_id_passes(self):
        """Grouped connectors namespace capability ids (e.g.
        `fetch-issues_qualys_fim`). CO130 must match by prefix."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(
            connector, capability_id="fetch-issues_myprofile"
        )
        _write_configurations_with_fetch_issues(
            connector, capability_id="fetch-issues_myprofile"
        )
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert results == []

    # ------------------------------------------------------------
    # Part 1 - serializer computed_fields failures
    # ------------------------------------------------------------
    def test_missing_serializer_fails(self):
        """Handler has no serializer at all - Part 1 fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        # Force serializer to None (helper defaulted it to valid).
        connector.handlers[0].serializer = None
        _write_configurations_with_fetch_issues(connector)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        msg = results[0].message
        assert "isFetch" in msg and "computed_fields" in msg

    def test_serializer_computed_fields_flag_missing_fails(self):
        """Serializer exists but has no isFetch computed rule."""
        from demisto_sdk.commands.content_graph.objects.connector import (
            SerializerData,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(
            connector,
            serializer=SerializerData(field_mappings=[], computed_fields=[]),
        )
        _write_configurations_with_fetch_issues(connector)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "does not emit" in results[0].message

    def test_serializer_computed_flag_wrong_capability_id_fails(self):
        """Rule emits isFetch but under the WRONG capability id."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        # Wire handler at cap-id "fetch-issues" but serializer references
        # something else.
        wrong_ser = _make_valid_serializer(capability_id="log-collection")
        _wire_handler_for_fetch_issues(connector, serializer=wrong_ser)
        _write_configurations_with_fetch_issues(connector)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "does not emit" in results[0].message
        assert "'fetch-issues == on'" in results[0].message

    def test_serializer_computed_flag_value_false_fails(self):
        """Rule structure exists but value is False (must be True)."""
        from demisto_sdk.commands.content_graph.objects.connector import (
            ComputedCondition,
            ComputedConditionGroup,
            ComputedFieldRule,
            ComputedOutput,
            SerializerData,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        bad_ser = SerializerData(
            field_mappings=[],
            computed_fields=[
                ComputedFieldRule(
                    output=[ComputedOutput(id="isFetch", value=False)],
                    any_of=[
                        ComputedConditionGroup(
                            conditions=[
                                ComputedCondition(
                                    type="capability",
                                    options={
                                        "capability_id": "fetch-issues",
                                        "value": "on",
                                    },
                                )
                            ]
                        )
                    ],
                )
            ],
        )
        _wire_handler_for_fetch_issues(connector, serializer=bad_ser)
        _write_configurations_with_fetch_issues(connector)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "does not emit" in results[0].message

    # ------------------------------------------------------------
    # Part 2 - configurations entry / field failures
    # ------------------------------------------------------------
    def test_configurations_file_missing_fails(self):
        """XSOAR handler subscribes to fetch-issues but there's no
        configurations.yaml at all."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        # Do NOT write configurations.yaml
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert (
            "no `configurations[]` entry with id 'fetch-issues'" in results[0].message
        )

    def test_capability_configurations_entry_missing_fails(self):
        """configurations.yaml exists but has no entry for fetch-issues."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_connector_yaml_file(
            connector,
            "configurations.yaml",
            {
                "metadata": {
                    "title": "Configuration",
                    "description": "Adjust and refine your configuration settings",
                },
                "view_groups": [],
                "configurations": [{"id": "other-capability", "configurations": []}],
            },
        )
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert (
            "no `configurations[]` entry with id 'fetch-issues'" in results[0].message
        )

    def test_missing_incidentType_field_fails(self):
        """Required field `incidentType` absent."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(connector, include_incidentType=False)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "missing required field 'incidentType'" in results[0].message

    def test_missing_incidentFetchInterval_field_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(
            connector, include_incidentFetchInterval=False
        )
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "missing required field 'incidentFetchInterval'" in results[0].message

    def test_missing_incomingMapperId_field_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(
            connector, include_incomingMapperId=False
        )
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "missing required field 'incomingMapperId'" in results[0].message

    def test_missing_mappingId_field_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(connector, include_mappingId=False)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "missing required field 'mappingId'" in results[0].message

    def test_incidentFetchInterval_wrong_field_type_fails(self):
        """incidentFetchInterval must be a `duration` field, not `input`."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(
            connector, incidentFetchInterval_type="input"
        )
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        msg = results[0].message
        assert "'incidentFetchInterval'" in msg
        assert "field_type='input'" in msg
        assert "must be 'duration'" in msg

    def test_incidentType_wrong_field_type_fails(self):
        """incidentType must be a select."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(connector, incidentType_type="input")
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        msg = results[0].message
        assert "'incidentType'" in msg
        assert "must be 'select'" in msg

    def test_incidentType_wrong_dynamic_field_fails(self):
        """incidentType.dynamicField must be 'incident-type'."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(
            connector, incidentType_dyn="issue-type"
        )
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        msg = results[0].message
        assert "'incidentType'" in msg
        assert "dynamicField='issue-type'" in msg
        assert "must be 'incident-type'" in msg

    def test_mappingId_wrong_dynamic_field_fails(self):
        """mappingId.dynamicField must be 'classifier'."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(connector, mappingId_dyn="mapping")
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "dynamicField='mapping'" in results[0].message
        assert "must be 'classifier'" in results[0].message

    def test_incomingMapperId_wrong_dynamic_field_fails(self):
        """incomingMapperId.dynamicField must be 'mapper-incoming'."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(
            connector, incomingMapperId_dyn="incoming-mapper"
        )
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "dynamicField='incoming-mapper'" in results[0].message
        assert "must be 'mapper-incoming'" in results[0].message

    # ------------------------------------------------------------
    # Result-splitting: per-handler serializer vs per-capability
    # configurations. Enables handler-scoped ``.connector-ignore``
    # entries (``[file:<handler-folder>/serializer.yaml]``) for
    # Part-1 defects while keeping Part-2 defects filterable by
    # ``[file:configurations.yaml]``.
    # ------------------------------------------------------------
    def test_multiple_problems_emit_separate_results_per_owning_file(self):
        """Missing serializer AND missing field -> two results, each
        keyed by the file that owns the fix.

        Historical shape aggregated everything into one result with
        path=configurations.yaml, which defeats per-handler
        ``.connector-ignore`` filtering (the ignore key
        ``<folder>/serializer.yaml`` was never resolved for a
        configurations-file result).
        """
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        connector.handlers[0].serializer = None
        _write_configurations_with_fetch_issues(connector, include_mappingId=False)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 2

        serializer_results = [
            r for r in results if str(r.path).endswith("serializer.yaml")
        ]
        configurations_results = [
            r for r in results if str(r.path).endswith("configurations.yaml")
        ]
        assert len(serializer_results) == 1
        assert len(configurations_results) == 1
        assert "does not emit" in serializer_results[0].message
        assert "missing required field 'mappingId'" in configurations_results[0].message

    def test_serializer_defect_path_points_to_handler_serializer_yaml(self):
        """A Part-1 (missing ``isFetch``) result's path must be
        ``<handler-folder>/serializer.yaml`` so per-handler
        ``.connector-ignore`` entries actually filter it (mirrors
        CO171/CO172)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        connector.handlers[0].serializer = None
        # Configurations wired correctly so ONLY the Part-1 defect fires.
        _write_configurations_with_fetch_issues(connector)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert str(results[0].path).endswith("serializer.yaml")

    def test_configurations_defect_path_points_to_configurations_yaml(self):
        """A Part-2 (missing required field) result's path stays at
        ``configurations.yaml`` — the configurations entry is a
        connector-scoped concern shared across every handler
        subscribing to that capability id."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO130_is_valid_fetch import (
            IsValidFetchValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_fetch_issues(connector)
        _write_configurations_with_fetch_issues(connector, include_incidentType=False)
        results = IsValidFetchValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert str(results[0].path).endswith("configurations.yaml")


# ============================================================
# CO136 test helpers
# ============================================================
def _default_ignore_field(
    raw_id: str = "defaultIgnore",
    field_type: str = "checkbox",
    config_type: str = "backend",
) -> dict:
    """Build a raw `defaultIgnore` field dict for configurations.yaml."""
    return {
        "id": raw_id,
        "title": "Do not use in CLI by default",
        "field_type": field_type,
        "metadata": {"xsoar": {"config_type": config_type}},
        "options": {
            "default_value": False,
            "create_modifiers": {"required": False, "hidden": False},
            "edit_modifiers": {"required": False, "hidden": False},
        },
    }


def _automation_capability_entry(
    capability_id: str = "automation-and-remediation",
    include_default_ignore: bool = True,
    **field_overrides,
) -> dict:
    """Build a raw configurations.yaml `configurations[]` entry dict
    for the automation capability. When ``include_default_ignore`` is
    False, the entry has NO fields (used for the missing-field case)."""
    fields = []
    if include_default_ignore:
        fields.append(_default_ignore_field(**field_overrides))
    return {
        "id": capability_id,
        "configurations": [{"advanced": True, "fields": fields}] if fields else [],
    }


def _write_configurations_with_automation(
    connector,
    capability_id: str = "automation-and-remediation",
    include_default_ignore: bool = True,
    **field_overrides,
) -> None:
    entry = _automation_capability_entry(
        capability_id=capability_id,
        include_default_ignore=include_default_ignore,
        **field_overrides,
    )
    _write_connector_yaml_file(
        connector,
        "configurations.yaml",
        {
            "metadata": {
                "title": "Configuration",
                "description": "Adjust and refine your configuration settings",
            },
            "view_groups": [],
            "configurations": [entry],
        },
    )


def _wire_handler_for_automation(
    connector,
    capability_id: str = "automation-and-remediation",
    handler_index: int = 0,
    serializer=None,
) -> None:
    """Point the connector's handler at the automation capability.
    Optionally attach a serializer for field-mappings resolution
    testing."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        HandlerCapability,
    )

    handler = connector.handlers[handler_index]
    handler.metadata.module = "xsoar"
    handler.capabilities = [
        HandlerCapability(
            id=capability_id,
            auth_options=[],
            workloads=[],
            actions=[],
        )
    ]
    handler.serializer = serializer


def _make_serializer_with_field_mapping(raw_id: str, runtime_name: str):
    """Build a SerializerData that renames ``raw_id`` -> ``runtime_name``."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        FieldMapping,
        SerializerData,
    )

    return SerializerData(
        field_mappings=[FieldMapping(id=raw_id, field_name=runtime_name)],
        computed_fields=[],
    )


class TestCO136IsValidAutomationCapability:
    """Tests for CO136: automation-and-remediation capability wiring.

    For each XSOAR handler subscribing to the capability (bare id or
    grouped-namespaced variant), the corresponding configurations
    entry must contain a `defaultIgnore` field (post-serializer
    field_mappings resolution) with:
    - field_type: checkbox
    - metadata.xsoar.config_type: backend
    """

    # ------------------------------------------------------------
    # Skip cases
    # ------------------------------------------------------------
    def test_no_automation_capability_short_circuits(self):
        """A connector whose handlers don't subscribe to automation
        produces no results (even if configurations.yaml is absent)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        # default handler subscribes to "test-capability", not automation
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_non_xsoar_handler_is_skipped(self):
        """A fully non-XSOAR handler subscribing to automation is
        NOT checked. ``is_xsoar`` is an OR of {module, team,
        maintainers} — all three signals must be non-xsoar for the
        handler to be treated as non-XSOAR."""
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerCapability,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        # Override all three xsoar signals so is_xsoar is False.
        handler.metadata.module = "third_party"
        handler.metadata.ownership.team = "third_party"
        handler.metadata.ownership.maintainers = ["@third-party-content"]
        handler.capabilities = [
            HandlerCapability(
                id="automation-and-remediation",
                auth_options=[],
                workloads=[],
                actions=[],
            )
        ]
        handler.serializer = None
        # No configurations.yaml either — would fail if XSOAR-owned
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------
    def test_valid_automation_wiring_passes(self):
        """Bare capability id, defaultIgnore present with correct shape."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        _write_configurations_with_automation(connector)
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_valid_grouped_namespaced_capability_id_passes(self):
        """Grouped connectors namespace capability ids (e.g.
        `automation-and-remediation_qualysv2`). CO136 matches by
        prefix."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(
            connector, capability_id="automation-and-remediation_myprofile"
        )
        _write_configurations_with_automation(
            connector, capability_id="automation-and-remediation_myprofile"
        )
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_namespaced_default_ignore_resolved_via_serializer_passes(self):
        """Grouped connector where connection.yaml uses a namespaced
        raw id (`xsoar-qualys_fim_defaultIgnore`) that the serializer
        renames back to `defaultIgnore`. Post-resolution the check
        should pass."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        serializer = _make_serializer_with_field_mapping(
            raw_id="xsoar-qualys_fim_defaultIgnore",
            runtime_name="defaultIgnore",
        )
        _wire_handler_for_automation(
            connector,
            capability_id="automation-and-remediation_qualys_fim",
            serializer=serializer,
        )
        _write_configurations_with_automation(
            connector,
            capability_id="automation-and-remediation_qualys_fim",
            raw_id="xsoar-qualys_fim_defaultIgnore",
        )
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_namespaced_default_ignore_without_serializer_fails(self):
        """Same grouped connector but WITHOUT the serializer rename -
        the raw namespaced id doesn't resolve to `defaultIgnore` so
        the check fails with 'missing defaultIgnore field'."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(
            connector,
            capability_id="automation-and-remediation_qualys_fim",
            serializer=None,
        )
        _write_configurations_with_automation(
            connector,
            capability_id="automation-and-remediation_qualys_fim",
            raw_id="xsoar-qualys_fim_defaultIgnore",
        )
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "missing the required `defaultIgnore` field" in results[0].message

    # ------------------------------------------------------------
    # Failure paths - missing entry / missing field
    # ------------------------------------------------------------
    def test_configurations_file_missing_fails(self):
        """XSOAR handler subscribes to automation but no
        configurations.yaml on disk."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        # Do NOT write configurations.yaml
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert (
            "no `configurations[]` entry with id 'automation-and-remediation'"
            in results[0].message
        )

    def test_capability_entry_missing_fails(self):
        """configurations.yaml exists but has no entry for automation."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        _write_connector_yaml_file(
            connector,
            "configurations.yaml",
            {
                "metadata": {
                    "title": "Configuration",
                    "description": "Adjust and refine your configuration settings",
                },
                "view_groups": [],
                "configurations": [{"id": "other-capability", "configurations": []}],
            },
        )
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert (
            "no `configurations[]` entry with id 'automation-and-remediation'"
            in results[0].message
        )

    def test_default_ignore_field_missing_fails(self):
        """The automation entry exists but has no `defaultIgnore`
        field."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        _write_configurations_with_automation(connector, include_default_ignore=False)
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "missing the required `defaultIgnore` field" in results[0].message

    # ------------------------------------------------------------
    # Failure paths - wrong field shape
    # ------------------------------------------------------------
    def test_default_ignore_wrong_field_type_fails(self):
        """`defaultIgnore` present but field_type is not `checkbox`."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        _write_configurations_with_automation(connector, field_type="input")
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "field_type='input'" in msg
        assert "must be 'checkbox'" in msg

    def test_default_ignore_wrong_config_type_fails(self):
        """`defaultIgnore` present but metadata.xsoar.config_type is
        not `backend`."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        _write_configurations_with_automation(connector, config_type="frontend")
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "config_type='frontend'" in msg
        assert "must be 'backend'" in msg

    def test_default_ignore_missing_config_type_fails(self):
        """`defaultIgnore` field has no metadata.xsoar block at all."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        # Custom write: field without metadata
        entry = {
            "id": "automation-and-remediation",
            "configurations": [
                {
                    "advanced": True,
                    "fields": [
                        {
                            "id": "defaultIgnore",
                            "title": "Do not use in CLI by default",
                            "field_type": "checkbox",
                            # NO metadata block
                        }
                    ],
                }
            ],
        }
        _write_connector_yaml_file(
            connector,
            "configurations.yaml",
            {
                "metadata": {
                    "title": "Configuration",
                    "description": "Adjust and refine your configuration settings",
                },
                "view_groups": [],
                "configurations": [entry],
            },
        )
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "config_type='None'" in results[0].message

    def test_multiple_shape_issues_aggregate(self):
        """Both wrong field_type AND wrong config_type - both reported."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        _write_configurations_with_automation(
            connector, field_type="input", config_type="frontend"
        )
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "field_type='input'" in msg
        assert "must be 'checkbox'" in msg
        assert "config_type='frontend'" in msg
        assert "must be 'backend'" in msg

    def test_error_path_points_to_configurations_yaml(self):
        """Result.path should point at configurations.yaml."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO136_is_valid_automation_capability import (
            IsValidAutomationCapabilityValidator,
        )

        connector = create_connector_object()
        _wire_handler_for_automation(connector)
        _write_configurations_with_automation(connector, include_default_ignore=False)
        results = IsValidAutomationCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert str(results[0].path).endswith("configurations.yaml")


# ============================================================
# CO137 test helpers
# ============================================================
def _valid_duration_field(field_id: str = "incidentFetchInterval", **overrides) -> dict:
    """Build a canonical-shape duration field dict. Override any leaf via
    kwargs, e.g. ``units=['minutes']`` to make it fail sub-rule A."""
    options = {
        "units": ["days", "hours", "minutes"],
        "output_format": "minutes",
        "default_value": {"minutes": 1},
        "create_modifiers": {"hidden": False},
        "edit_modifiers": {"hidden": False},
    }
    options.update(overrides)
    return {
        "id": field_id,
        "title": "Fetch Interval",
        "field_type": "duration",
        "options": options,
    }


def _write_connection_with_duration_in_general(connector, field: dict) -> None:
    """Write a connection.yaml that has ONE duration field under
    top-level general_configurations."""
    payload = {
        "metadata": {"title": "Connection", "description": "desc"},
        "general_configurations": {
            "description": "gc",
            "configurations": [{"fields": [field]}],
        },
        "profiles": [],
    }
    _write_connector_yaml_file(connector, "connection.yaml", payload)


def _write_connection_with_duration_in_profile(connector, field: dict) -> None:
    """Write a connection.yaml with a duration field inside a profile."""
    payload = {
        "metadata": {"title": "Connection", "description": "desc"},
        "general_configurations": {"description": "gc", "configurations": []},
        "profiles": [
            {
                "id": "plain.test",
                "type": "plain",
                "title": "Test",
                "configurations": [{"fields": [field]}],
            }
        ],
    }
    _write_connector_yaml_file(connector, "connection.yaml", payload)


def _write_configurations_with_duration_in_general(connector, field: dict) -> None:
    """Write a configurations.yaml with a duration field under top-level
    general_configurations."""
    payload = {
        "metadata": {
            "title": "Configuration",
            "description": "Adjust and refine your configuration settings",
        },
        "view_groups": [],
        "general_configurations": {
            "description": "gc",
            "configurations": [{"fields": [field]}],
        },
        "configurations": [],
    }
    _write_connector_yaml_file(connector, "configurations.yaml", payload)


def _write_configurations_with_duration_in_capability(
    connector, field: dict, capability_id: str = "log-collection"
) -> None:
    """Write a configurations.yaml with a duration field inside a
    per-capability configurations entry."""
    payload = {
        "metadata": {
            "title": "Configuration",
            "description": "Adjust and refine your configuration settings",
        },
        "view_groups": [],
        "configurations": [
            {
                "id": capability_id,
                "configurations": [{"fields": [field]}],
            }
        ],
    }
    _write_connector_yaml_file(connector, "configurations.yaml", payload)


class TestCO137IsValidDurationTypeParam:
    """Tests for CO137: every duration field must satisfy the canonical
    shape (units, output_format, per-unit default caps)."""

    # ------------------------------------------------------------
    # Skip case
    # ------------------------------------------------------------
    def test_no_duration_fields_short_circuits(self):
        """A connector with no duration fields anywhere produces no
        results."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        # default template has no duration fields
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Happy paths - each of the 4 locations
    # ------------------------------------------------------------
    def test_valid_duration_in_connection_general_configurations_passes(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_connection_with_duration_in_general(connector, _valid_duration_field())
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_valid_duration_in_connection_profile_passes(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_connection_with_duration_in_profile(connector, _valid_duration_field())
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_valid_duration_in_configurations_general_passes(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_general(
            connector, _valid_duration_field()
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_valid_duration_in_configurations_capability_passes(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector, _valid_duration_field(), capability_id="log-collection"
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Sub-rule A: units mismatch
    # ------------------------------------------------------------
    def test_units_missing_fails(self):
        """options.units absent."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        bad_field = _valid_duration_field()
        del bad_field["options"]["units"]
        _write_configurations_with_duration_in_capability(connector, bad_field)
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "options.units=None" in msg
        assert "['days', 'hours', 'minutes']" in msg

    def test_units_wrong_order_fails(self):
        """units contains right keys but in the wrong order."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(units=["minutes", "hours", "days"]),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "options.units=['minutes', 'hours', 'days']" in results[0].message

    def test_units_subset_fails(self):
        """units missing a required key (only minutes)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(units=["minutes"]),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "options.units=['minutes']" in results[0].message

    # ------------------------------------------------------------
    # Sub-rule B: output_format mismatch
    # ------------------------------------------------------------
    def test_output_format_wrong_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(output_format="seconds"),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "options.output_format='seconds'" in results[0].message
        assert "must be 'minutes'" in results[0].message

    def test_output_format_missing_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        bad_field = _valid_duration_field()
        del bad_field["options"]["output_format"]
        _write_configurations_with_duration_in_capability(connector, bad_field)
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "options.output_format=None" in results[0].message

    # ------------------------------------------------------------
    # Sub-rule C: hours > 23
    # ------------------------------------------------------------
    def test_hours_over_cap_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(default_value={"hours": 24}),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "options.default_value.hours=24" in msg
        assert "must be <= 23" in msg

    def test_hours_boundary_23_passes(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(default_value={"hours": 23}),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Sub-rule D: minutes > 59
    # ------------------------------------------------------------
    def test_minutes_over_cap_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(default_value={"minutes": 60}),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "options.default_value.minutes=60" in msg
        assert "must be <= 59" in msg

    def test_minutes_boundary_59_passes(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(default_value={"minutes": 59}),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Aggregation + path + edge cases
    # ------------------------------------------------------------
    def test_multiple_issues_aggregate(self):
        """Wrong units + wrong output_format + over-cap hours in one field."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        _write_configurations_with_duration_in_capability(
            connector,
            _valid_duration_field(
                units=["minutes"],
                output_format="seconds",
                default_value={"hours": 30, "minutes": 80},
            ),
        )
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "options.units=['minutes']" in msg
        assert "options.output_format='seconds'" in msg
        assert "options.default_value.hours=30" in msg
        assert "options.default_value.minutes=80" in msg

    def test_missing_options_dict_fails(self):
        """Field has no `options` at all."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        bad_field = {
            "id": "somedur",
            "title": "Some Duration",
            "field_type": "duration",
        }
        _write_configurations_with_duration_in_capability(connector, bad_field)
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "has no `options` mapping" in results[0].message

    def test_non_duration_field_is_ignored(self):
        """A `checkbox`/`input`/`select` field with wrong `units` in options is
        NOT flagged - CO137 only walks fields whose `field_type == duration`."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO137_is_valid_duration_type_param import (
            IsValidDurationTypeParamValidator,
        )

        connector = create_connector_object()
        non_duration_field = {
            "id": "somecheck",
            "title": "some checkbox",
            "field_type": "checkbox",
            "options": {"units": ["nonsense"], "output_format": "garbage"},
        }
        _write_configurations_with_duration_in_capability(connector, non_duration_field)
        results = IsValidDurationTypeParamValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []


# ============================================================
# CO139 test helpers
# ============================================================
def _valid_log_level_field(raw_id: str = "integrationLogLevel", **overrides) -> dict:
    """Build a canonical-shape integrationLogLevel field dict. Override
    any leaf via kwargs to intentionally break individual sub-rules."""
    field_type = overrides.pop("field_type", "select")
    config_type = overrides.pop("config_type", "backend")
    searchable = overrides.pop("searchable", True)
    clearable = overrides.pop("clearable", True)
    values = overrides.pop(
        "values",
        [
            {"key": "Off", "label": "Off"},
            {"key": "Debug", "label": "Debug"},
            {"key": "Verbose", "label": "Verbose"},
        ],
    )
    metadata = overrides.pop("metadata", None)
    if metadata is None:
        metadata = {"xsoar": {"config_type": config_type}}
    return {
        "id": raw_id,
        "title": "Log Level",
        "field_type": field_type,
        "metadata": metadata,
        "options": {
            "searchable": searchable,
            "clearable": clearable,
            "values": values,
        },
    }


def _standard_log_level_configurations(
    required_for_capabilities,
    field=None,
    include_field=True,
):
    """Build a standard-connector `general_configurations.configurations`
    list containing ONE field-group entry with the log-level field."""
    fields = []
    if include_field:
        fields.append(field or _valid_log_level_field())
    return [
        {
            "required_for_capabilities": list(required_for_capabilities),
            "fields": fields,
        }
    ]


def _grouped_log_level_configurations(
    view_group_id: str,
    field=None,
    advanced: bool = True,
    include_field: bool = True,
):
    """Build a grouped-connector `general_configurations.configurations`
    entry for ONE view_group with the log-level field."""
    fields = []
    if include_field:
        fields.append(field or _valid_log_level_field())
    entry = {
        "view_group": view_group_id,
        "fields": fields,
    }
    if advanced:
        entry["advanced"] = True
    return entry


def _write_configurations_with_log_level(
    connector,
    general_config_entries,
    other_configurations=None,
):
    """Write a configurations.yaml with the given general_configurations
    entries. Other top-level 'configurations' entries can be provided
    for aggregation tests."""
    payload = {
        "metadata": {
            "title": "Configuration",
            "description": "Adjust and refine your configuration settings",
        },
        "view_groups": [],
        "general_configurations": {
            "configurations": general_config_entries,
        },
        "configurations": other_configurations or [],
    }
    _write_connector_yaml_file(connector, "configurations.yaml", payload)


def _wire_xsoar_handler_with_caps(
    connector,
    capability_ids,
    handler_index: int = 0,
    serializer=None,
):
    """Point the connector's handler at XSOAR + subscribe it to the
    given capability ids (may be a single id string or a list)."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        HandlerCapability,
    )

    if isinstance(capability_ids, str):
        capability_ids = [capability_ids]
    handler = connector.handlers[handler_index]
    handler.metadata.module = "xsoar"
    handler.capabilities = [
        HandlerCapability(id=cid, auth_options=[], workloads=[], actions=[])
        for cid in capability_ids
    ]
    handler.serializer = serializer


class TestCO139IsHandlerContainLoglevel:
    """Tests for CO139: every XSOAR handler must be reachable by an
    `integrationLogLevel` (select, config_type=backend) field under
    `configurations.yaml` `general_configurations`. Standard connectors
    aggregate `required_for_capabilities` across matching entries;
    grouped connectors index entries by `view_group` and require
    `advanced: true`.
    """

    # ------------------------------------------------------------
    # Skip cases
    # ------------------------------------------------------------
    def test_no_xsoar_handlers_short_circuits(self):
        """Connector with only non-XSOAR handlers is skipped even if
        no configurations.yaml is present."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        # Turn the default XSOAR handler into a non-XSOAR handler.
        connector.handlers[0].metadata.module = "cwp"
        connector.handlers[0].metadata.ownership.team = "cwp"
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_no_configurations_file_short_circuits(self):
        """XSOAR handler present but no configurations.yaml -> other
        validators cover the missing-file case; CO139 skips."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        # No configurations.yaml written.
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Hard failure: XSOAR handlers present but no integrationLogLevel
    # ------------------------------------------------------------
    def test_no_integration_log_level_field_at_all_fails(self):
        """configurations.yaml exists but has NO integrationLogLevel
        field anywhere -> hard failure (not silent skip)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                # A group with a completely unrelated field.
                {
                    "required_for_capabilities": ["automation-and-remediation"],
                    "fields": [{"id": "someOtherField", "field_type": "input"}],
                }
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "no `integrationLogLevel` field is declared" in msg

    # ------------------------------------------------------------
    # Standard happy path + failures
    # ------------------------------------------------------------
    def test_standard_valid_covering_all_caps_passes(self):
        """Standard connector: single general_configurations entry
        whose required_for_capabilities covers every XSOAR handler
        capability -> passes."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(
            connector,
            ["automation-and-remediation", "fetch-issues"],
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=[
                    "automation-and-remediation",
                    "fetch-issues",
                ]
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_standard_missing_capability_in_rfc_fails(self):
        """Standard connector: required_for_capabilities doesn't cover
        one of the handler's capabilities -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(
            connector,
            ["automation-and-remediation", "fetch-issues"],
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"]
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "does not cover" in msg
        assert "fetch-issues" in msg

    def test_standard_union_across_multiple_entries_passes(self):
        """Standard connector: two general_configurations entries each
        with the log-level field, whose combined
        `required_for_capabilities` covers everything -> passes."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(
            connector,
            ["automation-and-remediation", "fetch-issues"],
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                {
                    "required_for_capabilities": ["automation-and-remediation"],
                    "fields": [_valid_log_level_field()],
                },
                {
                    "required_for_capabilities": ["fetch-issues"],
                    "fields": [_valid_log_level_field()],
                },
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Standard: field-shape sub-rule failures
    # ------------------------------------------------------------
    def test_standard_wrong_field_type_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"],
                field=_valid_log_level_field(field_type="input"),
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "field_type='input'" in msg
        assert "must be 'select'" in msg

    def test_standard_wrong_config_type_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"],
                field=_valid_log_level_field(config_type="frontend"),
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "config_type='frontend'" in results[0].message

    def test_standard_missing_options_dict_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        bad_field = {
            "id": "integrationLogLevel",
            "title": "Log Level",
            "field_type": "select",
            "metadata": {"xsoar": {"config_type": "backend"}},
            # NO options
        }
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                {
                    "required_for_capabilities": ["automation-and-remediation"],
                    "fields": [bad_field],
                }
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "`options` mapping is missing" in results[0].message

    def test_standard_searchable_false_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"],
                field=_valid_log_level_field(searchable=False),
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "options.searchable" in results[0].message

    def test_standard_clearable_false_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"],
                field=_valid_log_level_field(clearable=False),
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "options.clearable" in results[0].message

    def test_standard_missing_values_key_fails(self):
        """options.values missing one of the required keys (Off /
        Debug / Verbose) -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"],
                field=_valid_log_level_field(
                    values=[
                        {"key": "Off", "label": "Off"},
                        {"key": "Debug", "label": "Debug"},
                        # Missing Verbose
                    ]
                ),
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "options.values is missing keys" in results[0].message
        assert "'Verbose'" in results[0].message

    # ------------------------------------------------------------
    # Grouped happy path + failures
    # ------------------------------------------------------------
    def test_grouped_valid_per_view_group_passes(self):
        """Grouped connector: each XSOAR handler's view_group has its
        own general_configurations entry with `advanced: true` and the
        canonical log-level field -> passes."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        connector.handlers[0].related_integration = _stub_related_integration(
            "qualysfim", "Qualys FIM"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(view_group_id="qualysfim")
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_view_group_id_verbatim_match_passes(self):
        """Grouped connector: view_group.id equals integration.object_id
        verbatim (baseline case)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        connector.handlers[0].related_integration = _stub_related_integration(
            "my-integration", "My Integration"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(view_group_id="my-integration")
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_slugified_view_group_id_passes_via_normalization(self):
        """Grouped connector: view_group.id is the slugified form of
        the integration id (e.g. 'syslog-sender' for integration
        'Syslog Sender') - CO139 uses the same alphanumeric-only
        normalization as CO122, so both collapse to 'syslogsender' and
        the lookup succeeds."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        connector.handlers[0].related_integration = _stub_related_integration(
            "Syslog Sender", "Syslog Sender"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(view_group_id="syslog-sender")
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_view_group_id_normalization_strips_punctuation(self):
        """Grouped connector: integration id contains punctuation
        (e.g. 'Mail Sender (New)') and view_group.id has all
        non-alphanumeric characters stripped ('mailsendernew') - both
        collapse to the same canonical form."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        connector.handlers[0].related_integration = _stub_related_integration(
            "Mail Sender (New)", "Mail Sender (New)"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(view_group_id="mailsendernew")
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_missing_view_group_entry_fails(self):
        """Grouped connector: handler's view_group has no matching
        general_configurations entry -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        connector.handlers[0].related_integration = _stub_related_integration(
            "qualysfim", "Qualys FIM"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                # entry exists but for a different view_group
                _grouped_log_level_configurations(view_group_id="qualysv2")
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "no" in msg and "normalizes to 'qualysfim'" in msg

    def test_grouped_missing_advanced_true_fails(self):
        """Grouped connector: view_group entry present but missing
        `advanced: true` -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        connector.handlers[0].related_integration = _stub_related_integration(
            "qualysfim", "Qualys FIM"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(
                    view_group_id="qualysfim", advanced=False
                )
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "`advanced: true`" in results[0].message

    def test_grouped_unresolved_integration_fails(self):
        """Grouped connector: XSOAR handler has no related_integration
        -> fails (cannot determine view_group)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        connector.handlers[0].related_integration = None
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(view_group_id="qualysfim")
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "no resolved integration" in results[0].message

    def test_grouped_namespaced_field_id_resolved_via_serializer_passes(self):
        """Grouped connector where configurations.yaml uses a
        namespaced raw id (`xsoar-qualys_fim_integrationLogLevel`)
        that the serializer renames back to `integrationLogLevel`.
        Post-resolution the check should pass."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        serializer = _make_serializer_with_field_mapping(
            raw_id="xsoar-qualys_fim_integrationLogLevel",
            runtime_name="integrationLogLevel",
        )
        _wire_xsoar_handler_with_caps(
            connector,
            ["automation-and-remediation_qualys_fim"],
            serializer=serializer,
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "qualysfim", "Qualys FIM"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(
                    view_group_id="qualysfim",
                    field=_valid_log_level_field(
                        raw_id="xsoar-qualys_fim_integrationLogLevel"
                    ),
                )
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_namespaced_field_without_serializer_fails(self):
        """Same grouped connector but WITHOUT the serializer rename -
        the raw namespaced id doesn't resolve to `integrationLogLevel`
        so the check fails with the 'no field declared' message."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
        )
        _wire_xsoar_handler_with_caps(
            connector,
            ["automation-and-remediation_qualys_fim"],
            serializer=None,
        )
        connector.handlers[0].related_integration = _stub_related_integration(
            "qualysfim", "Qualys FIM"
        )
        _write_configurations_with_log_level(
            connector,
            general_config_entries=[
                _grouped_log_level_configurations(
                    view_group_id="qualysfim",
                    field=_valid_log_level_field(
                        raw_id="xsoar-qualys_fim_integrationLogLevel"
                    ),
                )
            ],
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "no `integrationLogLevel` field is declared" in results[0].message

    # ------------------------------------------------------------
    # Aggregation + result path
    # ------------------------------------------------------------
    def test_multiple_issues_aggregate_into_one_result(self):
        """Multiple shape sub-rule failures aggregate into a single
        ValidationResult per connector."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"],
                field=_valid_log_level_field(
                    field_type="input",
                    config_type="frontend",
                    searchable=False,
                ),
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "field_type='input'" in msg
        assert "config_type='frontend'" in msg
        assert "options.searchable" in msg

    def test_error_path_points_to_configurations_yaml(self):
        """Result.path should point at configurations.yaml."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO139_is_handler_contain_loglevel import (
            IsHandlerContainLoglevelValidator,
        )

        connector = create_connector_object()
        _wire_xsoar_handler_with_caps(connector, ["automation-and-remediation"])
        _write_configurations_with_log_level(
            connector,
            general_config_entries=_standard_log_level_configurations(
                required_for_capabilities=["automation-and-remediation"],
                field=_valid_log_level_field(field_type="input"),
            ),
        )
        results = IsHandlerContainLoglevelValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert str(results[0].path).endswith("configurations.yaml")


# ============================================================
# CO144 test helpers
# ============================================================
def _grouped_connector_with_capabilities(capability_specs):
    """Build a grouped connector with a set of parent capabilities +
    sub-capabilities. ``capability_specs`` is a list of
    (parent_id, [sub_ids...]) tuples.
    """
    return create_connector_object(
        connector_overrides={"settings": {"grouped": True}},
        capabilities_data={
            "capabilities": [
                _capability(parent_id, sub_ids=sub_ids)
                for parent_id, sub_ids in capability_specs
            ]
        },
    )


def _write_configurations_yaml_with_entries(connector, entries):
    """Write configurations.yaml with the given top-level
    `configurations[]` entries."""
    _write_connector_yaml_file(
        connector,
        "configurations.yaml",
        {
            "metadata": {
                "title": "Configuration",
                "description": "Adjust and refine your configuration settings",
            },
            "view_groups": [],
            "configurations": entries,
        },
    )


class TestCO144IsConfigOnSubCapability:
    """Tests for CO144: in grouped connectors, `configurations.yaml`
    `configurations[]` entries must use sub-capability ids (never bare
    parent capability ids), and every declared sub-capability must
    have a matching `configurations[]` entry.
    """

    # ------------------------------------------------------------
    # Skip cases
    # ------------------------------------------------------------
    def test_non_grouped_short_circuits(self):
        """Non-grouped connector -> CO144 does not fire even if
        configurations.yaml has parent-capability ids."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = create_connector_object(
            capabilities_data={"capabilities": [_capability("fetch-issues")]},
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[{"id": "fetch-issues", "configurations": []}],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_no_configurations_and_no_sub_caps_short_circuits(self):
        """Grouped connector with no sub-caps declared AND no
        configurations.yaml -> nothing to check."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            capabilities_data={"capabilities": []},
        )
        # No configurations.yaml written.
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Rule 3 - entry.id must be a sub-cap id
    # ------------------------------------------------------------
    def test_grouped_valid_sub_capability_entries_pass(self):
        """Grouped connector: each entry id is a declared sub-capability
        id -> passes."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                (
                    "automation-and-remediation",
                    [
                        "automation-and-remediation_qualysv2",
                        "automation-and-remediation_qualys_fim",
                    ],
                ),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                {
                    "id": "automation-and-remediation_qualysv2",
                    "configurations": [],
                },
                {
                    "id": "automation-and-remediation_qualys_fim",
                    "configurations": [],
                },
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_bare_parent_capability_id_fails(self):
        """Grouped connector: entry.id is a bare parent capability id
        (e.g. `automation-and-remediation`) instead of a sub-cap id
        -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                ("automation-and-remediation", ["automation-and-remediation_qualysv2"]),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                {"id": "automation-and-remediation", "configurations": []},
                # Also include the correct sub-cap entry so rule 4 doesn't
                # add a second finding here (this test focuses on rule 3).
                {
                    "id": "automation-and-remediation_qualysv2",
                    "configurations": [],
                },
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "'automation-and-remediation'" in msg
        assert "bare parent capability id" in msg

    def test_grouped_unknown_entry_id_fails(self):
        """Grouped connector: entry.id is neither a sub-cap id nor a
        parent cap id -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                ("automation-and-remediation", ["automation-and-remediation_qualysv2"]),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                {"id": "some-random-id", "configurations": []},
                {
                    "id": "automation-and-remediation_qualysv2",
                    "configurations": [],
                },
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "'some-random-id'" in results[0].message
        assert "does not match any declared sub-capability id" in results[0].message

    def test_grouped_entry_missing_id_fails(self):
        """Grouped connector: `configurations[]` entry has no `id`
        key -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                ("automation-and-remediation", ["automation-and-remediation_qualysv2"]),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                {"configurations": []},  # no id
                {
                    "id": "automation-and-remediation_qualysv2",
                    "configurations": [],
                },
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "missing or non-string `id`" in results[0].message

    # ------------------------------------------------------------
    # Rule 4 - every sub-cap must have a matching entry
    # ------------------------------------------------------------
    def test_grouped_missing_sub_capability_entry_fails(self):
        """Grouped connector: a declared sub-cap has no matching
        `configurations[]` entry -> fails."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                (
                    "automation-and-remediation",
                    [
                        "automation-and-remediation_qualysv2",
                        "automation-and-remediation_qualys_fim",
                    ],
                ),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                # Only qualysv2 is covered; qualys_fim is missing.
                {
                    "id": "automation-and-remediation_qualysv2",
                    "configurations": [],
                },
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "declared sub-capabilities have no matching" in msg
        assert "'automation-and-remediation_qualys_fim'" in msg

    def test_grouped_all_sub_capabilities_missing_fails(self):
        """Grouped connector: configurations.yaml exists but has NO
        entries and multiple sub-caps declared -> fails, listing all
        missing sub-caps."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                (
                    "automation-and-remediation",
                    [
                        "automation-and-remediation_qualysv2",
                        "automation-and-remediation_qualys_fim",
                    ],
                ),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "'automation-and-remediation_qualysv2'" in msg
        assert "'automation-and-remediation_qualys_fim'" in msg

    def test_grouped_empty_entry_carries_view_group_passes(self):
        """§3.7 rule 4 lets a sub-cap emit an empty
        `configurations: []` entry to carry only the view_group. That
        should PASS CO144 (entry exists for the sub-cap)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                ("fetch-issues", ["fetch-issues_qualysv2"]),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                {
                    "id": "fetch-issues_qualysv2",
                    "view_group": "qualysv2",
                    "configurations": [],
                },
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Aggregation + result path
    # ------------------------------------------------------------
    def test_grouped_multiple_issues_aggregate_into_one_result(self):
        """Multiple violations (bare parent id used + missing sub-cap
        + unknown id) all aggregate into a single ValidationResult."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                (
                    "automation-and-remediation",
                    [
                        "automation-and-remediation_qualysv2",
                        "automation-and-remediation_qualys_fim",
                    ],
                ),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                # violation A: bare parent id
                {"id": "automation-and-remediation", "configurations": []},
                # violation B: unknown id
                {"id": "unknown-id", "configurations": []},
                # note: neither qualysv2 nor qualys_fim entries present,
                # so violation C: both sub-caps missing.
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1  # aggregated into ONE result
        msg = results[0].message
        assert "bare parent capability id" in msg
        assert "unknown-id" in msg
        assert "declared sub-capabilities have no matching" in msg

    def test_error_path_points_to_configurations_yaml(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO144_is_config_on_sub_capability import (
            IsConfigOnSubCapabilityValidator,
        )

        connector = _grouped_connector_with_capabilities(
            [
                ("automation-and-remediation", ["automation-and-remediation_qualysv2"]),
            ]
        )
        _write_configurations_yaml_with_entries(
            connector,
            entries=[
                {"id": "automation-and-remediation", "configurations": []},
                {
                    "id": "automation-and-remediation_qualysv2",
                    "configurations": [],
                },
            ],
        )
        results = IsConfigOnSubCapabilityValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert str(results[0].path).endswith("configurations.yaml")


# ============================================================
# CO146 (merged CO146 + CO147) test helpers
# ============================================================
def _write_summary_yaml(connector, payload) -> None:
    """Write summary.yaml to the connector's on-disk directory."""
    _write_connector_yaml_file(connector, "summary.yaml", payload)


class TestCO146IsSummaryPresentAndValidMetadata:
    """Tests for the merged CO146/CO147: `summary.yaml` must exist,
    and its `metadata.title` must equal 'Summary' and
    `metadata.description` must equal 'Review your instance
    configuration'."""

    # ------------------------------------------------------------
    # Presence (was CO146)
    # ------------------------------------------------------------
    def test_missing_summary_yaml_fails(self):
        """No summary.yaml on disk -> hard fail."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        # do NOT write summary.yaml
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "summary.yaml is missing" in results[0].message

    # ------------------------------------------------------------
    # Metadata contents (was CO147)
    # ------------------------------------------------------------
    def test_valid_metadata_passes(self):
        """Canonical title + description -> passes."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        _write_summary_yaml(
            connector,
            {
                "metadata": {
                    "title": "Summary",
                    "description": "Review your instance configuration",
                },
            },
        )
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    def test_wrong_title_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        _write_summary_yaml(
            connector,
            {
                "metadata": {
                    "title": "Nope",
                    "description": "Review your instance configuration",
                },
            },
        )
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "metadata.title='Nope'" in msg
        assert "must be 'Summary'" in msg

    def test_wrong_description_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        _write_summary_yaml(
            connector,
            {
                "metadata": {
                    "title": "Summary",
                    "description": "View documentation for this connector",
                },
            },
        )
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "metadata.description=" in msg
        assert "must be 'Review your instance configuration'" in msg

    def test_missing_metadata_block_fails(self):
        """summary.yaml exists but has no `metadata` mapping."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        _write_summary_yaml(connector, {"other_key": {}})
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "missing the required `metadata`" in results[0].message

    def test_missing_title_and_description_both_flagged(self):
        """metadata.title AND metadata.description both missing -> BOTH
        reported in a single aggregated ValidationResult."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        _write_summary_yaml(connector, {"metadata": {}})
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1  # aggregated
        msg = results[0].message
        assert "metadata.title=None" in msg
        assert "metadata.description=None" in msg
        assert "must be 'Summary'" in msg
        assert "must be 'Review your instance configuration'" in msg

    def test_top_level_not_mapping_fails(self):
        """summary.yaml content is a list (or some other non-dict)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        _write_summary_yaml(connector, ["not", "a", "dict"])
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "not a mapping" in results[0].message

    def test_error_path_points_to_summary_yaml(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO146_is_summary_present_and_valid_metadata import (
            IsSummaryPresentAndValidMetadataValidator,
        )

        connector = create_connector_object()
        _write_summary_yaml(
            connector,
            {"metadata": {"title": "Nope", "description": "Nope"}},
        )
        results = (
            IsSummaryPresentAndValidMetadataValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert str(results[0].path).endswith("summary.yaml")


# ============================================================
# HandlerData.is_xsoar semantics
# ============================================================
class TestHandlerIsXsoarSemantics:
    """Tests locking the widened `HandlerData.is_xsoar` semantics.

    `is_xsoar` is an OR of {module=="xsoar", team=="xsoar",
    "@xsoar-content" in maintainers}. Any single matching signal is
    sufficient. This ensures misconfigured XSOAR handlers (module
    correct but team wrong, or vice versa) still surface to
    XSOAR-scoped validators — so CO155/CO156/CO158 can own the fix
    rather than the handler being silently invisible.
    """

    def _fresh_handler(self):
        connector = create_connector_object()
        handler = connector.handlers[0]
        # Clear every xsoar signal so each test starts from a clean
        # non-xsoar baseline.
        handler.metadata.module = "third_party"
        handler.metadata.ownership.team = "third_party"
        handler.metadata.ownership.maintainers = ["@third-party-content"]
        return handler

    def test_only_module_xsoar_is_true(self):
        handler = self._fresh_handler()
        handler.metadata.module = "xsoar"
        assert handler.is_xsoar

    def test_only_team_xsoar_is_true(self):
        handler = self._fresh_handler()
        handler.metadata.ownership.team = "xsoar"
        assert handler.is_xsoar

    def test_only_maintainers_xsoar_is_true(self):
        handler = self._fresh_handler()
        handler.metadata.ownership.maintainers = ["@xsoar-content"]
        assert handler.is_xsoar

    def test_no_xsoar_signal_is_false(self):
        handler = self._fresh_handler()
        # All three signals overridden to non-xsoar values in _fresh_handler.
        assert not handler.is_xsoar


# ============================================================
# CO148 test helpers
# ============================================================
def _hide_engine_trigger(prefix: str = "") -> dict:
    """Canonical 'hide <prefix>engine when engine_mode != engine' trigger."""
    return {
        "conditions": {
            "id": f"{prefix}engine_mode",
            "behavior": "value",
            "operator": "neq",
            "value": "engine",
        },
        "effects": [
            {"id": f"{prefix}engine", "action": {"hidden": True}},
        ],
    }


def _hide_engine_group_trigger(prefix: str = "") -> dict:
    """Canonical 'hide <prefix>engineGroup when engine_mode != engineGroup'."""
    return {
        "conditions": {
            "id": f"{prefix}engine_mode",
            "behavior": "value",
            "operator": "neq",
            "value": "engineGroup",
        },
        "effects": [
            {"id": f"{prefix}engineGroup", "action": {"hidden": True}},
        ],
    }


def _unlock_proxy_trigger(prefix: str = "") -> dict:
    """Canonical 'unlock <prefix>proxy when engine or engineGroup is set'."""
    return {
        "conditions": {
            "operator": "OR",
            "children": [
                {
                    "id": f"{prefix}engine",
                    "behavior": "value",
                    "operator": "is_not_empty",
                },
                {
                    "id": f"{prefix}engineGroup",
                    "behavior": "value",
                    "operator": "is_not_empty",
                },
            ],
        },
        "effects": [
            {"id": f"{prefix}proxy", "action": {"read_only": False}},
        ],
    }


def _canonical_engine_trigger_set(prefix: str = "") -> list:
    """The 3 canonical engine triggers for a given prefix."""
    return [
        _hide_engine_trigger(prefix),
        _hide_engine_group_trigger(prefix),
        _unlock_proxy_trigger(prefix),
    ]


def _write_triggers_yaml(connector, triggers: list) -> None:
    _write_connector_yaml_file(connector, "triggers.yaml", {"triggers": triggers})


def _stamp_proxy_resolved_param(
    connector,
    raw_id: str = "proxy",
    runtime_name: str = "proxy",
) -> None:
    """Give the connector's first XSOAR handler a resolved_params entry
    that CO148 recognizes as 'connector exposes a proxy field with raw
    id raw_id'. Mirrors CO120 test setup so the two validators stay
    consistent.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        ResolvedParamMapping,
    )

    existing = list(connector.handlers[0].resolved_params or [])
    existing.append(
        ResolvedParamMapping(
            connector_param_name=raw_id,
            content_param_name=runtime_name,
        )
    )
    connector.handlers[0].resolved_params = existing


def _connector_with_standard_engine_fields(with_proxy: bool = True):
    """Standard connector with bare engine triplet in
    connection.general_configurations.

    When with_proxy is True (default), also stamps a 'proxy'
    resolved_param on the first XSOAR handler so CO148 will require
    the unlock-proxy trigger. Set to False to simulate a connector
    that has engine fields but no proxy field (CO148 should then
    skip the unlock-proxy check for it).
    """
    connector = create_connector_object(
        connection_data={
            "general_configurations": _standard_engine_gc(_canonical_engine_triplet()),
        },
    )
    if with_proxy:
        _stamp_proxy_resolved_param(connector, raw_id="proxy", runtime_name="proxy")
    return connector


def _stamp_engine_resolved_params(
    connector,
    prefix: str,
    handler_index: int = 0,
) -> None:
    """Give ``connector.handlers[handler_index]`` resolved_params
    entries for the engine triplet under ``prefix`` — ``<prefix>engine_mode``,
    ``<prefix>engine``, ``<prefix>engineGroup`` — so CO148's
    ``_prefix_proxy_map`` discovers the picker.

    The connector parser only auto-populates resolved_params from
    profile fields when the profile id appears in the handler's
    auth_options. Tests that put the triplet inside a profile
    (grouped style) without matching auth_options never surface
    those field ids, so we stamp them here to mirror what the
    parser would produce.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        ResolvedParamMapping,
    )

    existing = list(connector.handlers[handler_index].resolved_params or [])
    for suffix in ("engine_mode", "engine", "engineGroup"):
        field_id = f"{prefix}{suffix}"
        if any(rp.connector_param_name == field_id for rp in existing):
            continue
        existing.append(
            ResolvedParamMapping(
                connector_param_name=field_id,
                content_param_name=field_id,
            )
        )
    connector.handlers[handler_index].resolved_params = existing


def _connector_with_prefixed_engine_fields(
    prefix: str = "plain_myint_", with_proxy: bool = True
):
    """Grouped-style connector with prefixed engine triplet in a profile.

    Also stamps the engine triplet as resolved_params on the first
    XSOAR handler so CO148's ``_prefix_proxy_map`` discovers the
    ``<prefix>engine_mode`` picker (the parser only surfaces profile
    fields whose profile id matches the handler's auth_options).

    When with_proxy is True (default), also stamps a '<prefix>proxy'
    resolved_param so CO148 requires the prefixed unlock-proxy trigger.
    """
    connector = create_connector_object(
        connector_overrides={"settings": {"grouped": True}},
        connection_data={
            "profiles": [
                {
                    "id": "plain",
                    "type": "plain",
                    "configurations": [
                        {
                            "fields": [
                                _canonical_engine_mode_field(
                                    field_id=f"{prefix}engine_mode"
                                ),
                                _canonical_engine_field(
                                    field_id=f"{prefix}engine",
                                    integration_id="MyInt",
                                    dynamic_field="engine",
                                ),
                                _canonical_engine_field(
                                    field_id=f"{prefix}engineGroup",
                                    integration_id="MyInt",
                                    dynamic_field="engine-group",
                                ),
                            ],
                        },
                    ],
                },
            ],
        },
    )
    _stamp_engine_resolved_params(connector, prefix=prefix)
    if with_proxy:
        _stamp_proxy_resolved_param(
            connector, raw_id=f"{prefix}proxy", runtime_name="proxy"
        )
    return connector


class TestCO148IsValidEngineTriggers:
    """Tests for CO148: triggers.yaml must contain the 3 canonical
    engine triggers for every `<prefix>engine_mode` field declared in
    connection.yaml."""

    # ------------------------------------------------------------
    # Skip cases
    # ------------------------------------------------------------
    def test_no_engine_mode_field_short_circuits(self):
        """Connector without any engine_mode field -> skip (Appendix G)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = create_connector_object()  # default has no engine fields
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_no_connection_yaml_short_circuits(self):
        """Connector whose connection is missing entirely -> skip."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = create_connector_object()
        connector.connection = None
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    # ------------------------------------------------------------
    # Standard connector (bare ids) happy path + failures
    # ------------------------------------------------------------
    def test_standard_valid_all_three_triggers_pass(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        _write_triggers_yaml(connector, _canonical_engine_trigger_set(""))
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_standard_missing_triggers_yaml_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        # do NOT write triggers.yaml
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "triggers.yaml is missing" in results[0].message

    def test_standard_missing_hide_engine_trigger_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        # Ship only the two OTHER triggers.
        _write_triggers_yaml(
            connector,
            [_hide_engine_group_trigger(""), _unlock_proxy_trigger("")],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "missing 'hide engine when engine_mode != engine'" in results[0].message

    def test_standard_missing_hide_engine_group_trigger_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        _write_triggers_yaml(
            connector,
            [_hide_engine_trigger(""), _unlock_proxy_trigger("")],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert (
            "missing 'hide engineGroup when engine_mode != engineGroup'"
            in results[0].message
        )

    def test_standard_missing_unlock_proxy_trigger_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        _write_triggers_yaml(
            connector,
            [_hide_engine_trigger(""), _hide_engine_group_trigger("")],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert (
            "missing 'unlock proxy when engine or engineGroup is selected'"
            in results[0].message
        )

    # ------------------------------------------------------------
    # Malformed variants
    # ------------------------------------------------------------
    def test_standard_hide_engine_wrong_action_hidden_fails(self):
        """Trigger exists but action.hidden is missing / not True -> fail."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        broken_hide_engine = _hide_engine_trigger("")
        broken_hide_engine["effects"][0]["action"] = {"hidden": False}
        _write_triggers_yaml(
            connector,
            [
                broken_hide_engine,
                _hide_engine_group_trigger(""),
                _unlock_proxy_trigger(""),
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "missing 'hide engine" in results[0].message

    def test_standard_unlock_proxy_wrong_readonly_true_fails(self):
        """Unlock proxy trigger present but read_only is True (wrong)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        broken = _unlock_proxy_trigger("")
        broken["effects"][0]["action"] = {"read_only": True}
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger(""),
                _hide_engine_group_trigger(""),
                broken,
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "unlock proxy" in results[0].message

    def test_standard_unlock_proxy_missing_child_fails(self):
        """Unlock proxy trigger has only 1 child (missing engineGroup)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        broken = _unlock_proxy_trigger("")
        broken["conditions"]["children"] = [
            broken["conditions"]["children"][0]
        ]  # keep only 1 child
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger(""),
                _hide_engine_group_trigger(""),
                broken,
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "unlock proxy" in results[0].message

    # ------------------------------------------------------------
    # Grouped connector (prefixed ids) happy path + failures
    # ------------------------------------------------------------
    def test_grouped_valid_prefixed_triggers_pass(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_prefixed_engine_fields("plain_myint_")
        _write_triggers_yaml(
            connector,
            _canonical_engine_trigger_set("plain_myint_"),
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_missing_all_triggers_for_prefix_fails(self):
        """Prefixed connection.yaml fields but bare-id triggers only ->
        fails all 3 for the prefix."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_prefixed_engine_fields("plain_myint_")
        _write_triggers_yaml(
            connector, _canonical_engine_trigger_set("")
        )  # bare, wrong prefix
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "'plain_myint_'" in msg
        # All 3 sub-triggers should be reported missing.
        assert "hide engine when engine_mode" in msg
        assert "hide engineGroup" in msg
        assert "unlock proxy" in msg

    def test_grouped_multiple_prefixes_aggregate(self):
        """Grouped connector with 2 profiles → both prefixes checked
        independently; issues aggregate into 1 result."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    {
                        "id": "plain",
                        "type": "plain",
                        "configurations": [
                            {
                                "fields": [
                                    _canonical_engine_mode_field(
                                        field_id="plain_myint_engine_mode"
                                    ),
                                    _canonical_engine_field(
                                        field_id="plain_myint_engine",
                                        integration_id="MyInt",
                                        dynamic_field="engine",
                                    ),
                                    _canonical_engine_field(
                                        field_id="plain_myint_engineGroup",
                                        integration_id="MyInt",
                                        dynamic_field="engine-group",
                                    ),
                                ],
                            },
                        ],
                    },
                    {
                        "id": "oauth",
                        "type": "oauth",
                        "configurations": [
                            {
                                "fields": [
                                    _canonical_engine_mode_field(
                                        field_id="oauth_myint_engine_mode"
                                    ),
                                    _canonical_engine_field(
                                        field_id="oauth_myint_engine",
                                        integration_id="MyInt",
                                        dynamic_field="engine",
                                    ),
                                    _canonical_engine_field(
                                        field_id="oauth_myint_engineGroup",
                                        integration_id="MyInt",
                                        dynamic_field="engine-group",
                                    ),
                                ],
                            },
                        ],
                    },
                ],
            },
        )
        # Stamp the engine triplet as resolved_params on the first
        # XSOAR handler for BOTH prefixes so CO148's
        # _prefix_proxy_map discovers both engine pickers (the parser
        # only surfaces profile fields whose profile id matches the
        # handler's auth_options).
        _stamp_engine_resolved_params(connector, prefix="plain_myint_")
        _stamp_engine_resolved_params(connector, prefix="oauth_myint_")
        # Both profiles expose a proxy field (per CO120), so the
        # unlock-proxy trigger IS required for both prefixes.
        _stamp_proxy_resolved_param(
            connector, raw_id="plain_myint_proxy", runtime_name="proxy"
        )
        _stamp_proxy_resolved_param(
            connector, raw_id="oauth_myint_proxy", runtime_name="proxy"
        )
        # Ship triggers ONLY for the plain_myint_ prefix; oauth_myint_ is
        # completely missing -> the 3 oauth triggers should all be flagged.
        _write_triggers_yaml(connector, _canonical_engine_trigger_set("plain_myint_"))
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1  # aggregated
        msg = results[0].message
        assert "'oauth_myint_'" in msg
        assert "'plain_myint_'" not in msg  # plain_myint_ is fine

    # ------------------------------------------------------------
    # Aggregation + path
    # ------------------------------------------------------------
    def test_standard_multiple_missing_triggers_aggregate(self):
        """Missing 2 out of 3 triggers -> both reported in 1 result."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        _write_triggers_yaml(connector, [_hide_engine_trigger("")])  # only 1
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "hide engineGroup" in msg
        assert "unlock proxy" in msg

    # ------------------------------------------------------------
    # Conditional unlock-proxy check (based on CO120-style proxy
    # exposure). The unlock-proxy trigger is ONLY required when a
    # proxy field actually exists for the connector; otherwise
    # emitting one would violate the Go OPA cross-file rule.
    # ------------------------------------------------------------
    def test_standard_no_proxy_field_skips_unlock_proxy_check(self):
        """Connector has engine fields but NO proxy field exposed by any
        XSOAR handler (resolved_params has no proxy alias). The unlock-
        proxy trigger MUST NOT be required — only the 2 hide triggers."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields(with_proxy=False)
        # Ship ONLY the 2 hide triggers; no unlock-proxy trigger at all.
        _write_triggers_yaml(
            connector,
            [_hide_engine_trigger(""), _hide_engine_group_trigger("")],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_standard_no_proxy_field_still_requires_hide_triggers(self):
        """Even without a proxy field, the two hide triggers are still
        mandatory (engine + engineGroup fields exist unconditionally)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields(with_proxy=False)
        # Ship NO triggers at all -> both hide triggers should be flagged
        # BUT NOT the unlock-proxy trigger.
        _write_triggers_yaml(connector, [])
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "hide engine when engine_mode" in msg
        assert "hide engineGroup" in msg
        assert "unlock proxy" not in msg

    def test_standard_useproxy_alias_is_accepted_as_unlock_target(self):
        """When the connector's proxy field is named 'useproxy' (a valid
        CO120 alias), the unlock-proxy trigger targeting id='useproxy'
        must be accepted."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields(with_proxy=False)
        _stamp_proxy_resolved_param(
            connector, raw_id="useproxy", runtime_name="useproxy"
        )
        # Build an unlock-proxy trigger whose effect targets 'useproxy'.
        unlock_useproxy = _unlock_proxy_trigger("")
        unlock_useproxy["effects"][0]["id"] = "useproxy"
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger(""),
                _hide_engine_group_trigger(""),
                unlock_useproxy,
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_standard_use_proxy_alias_is_accepted_as_unlock_target(self):
        """When the connector's proxy field is named 'use_proxy' (a
        valid CO120 alias), the unlock-proxy trigger targeting
        id='use_proxy' must be accepted."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields(with_proxy=False)
        _stamp_proxy_resolved_param(
            connector, raw_id="use_proxy", runtime_name="use_proxy"
        )
        unlock_use_proxy = _unlock_proxy_trigger("")
        unlock_use_proxy["effects"][0]["id"] = "use_proxy"
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger(""),
                _hide_engine_group_trigger(""),
                unlock_use_proxy,
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_standard_serializer_renamed_proxy_uses_raw_id_target(self):
        """When serializer renames a namespaced raw id (e.g.
        'foo_proxy') to the runtime name 'proxy', the trigger MUST
        target the RAW id 'foo_proxy' (triggers.yaml uses raw ids).
        Targeting the runtime name 'proxy' when it isn't the raw id
        would violate the Go OPA cross-file rule."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields(with_proxy=False)
        # Handler's resolved_params: raw id 'foo_proxy' renamed to 'proxy'.
        _stamp_proxy_resolved_param(connector, raw_id="foo_proxy", runtime_name="proxy")
        # Correct: trigger targets the raw id 'foo_proxy' -> passes.
        unlock_ok = _unlock_proxy_trigger("")
        unlock_ok["effects"][0]["id"] = "foo_proxy"
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger(""),
                _hide_engine_group_trigger(""),
                unlock_ok,
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_standard_unlock_proxy_wrong_target_id_fails(self):
        """Trigger with a proxy field present, but the effect targets
        a raw id that no XSOAR handler exposes -> must fail."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()  # exposes 'proxy'
        bad = _unlock_proxy_trigger("")
        bad["effects"][0]["id"] = "some_other_field"  # not the real proxy id
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger(""),
                _hide_engine_group_trigger(""),
                bad,
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "unlock proxy" in results[0].message

    def test_grouped_prefix_without_proxy_skips_only_that_unlock(self):
        """Grouped connector: plain_myint_ profile exposes proxy but
        oauth_myint_ profile does not. Both hide triggers required for
        both prefixes; unlock-proxy required ONLY for plain_myint_."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    {
                        "id": "plain",
                        "type": "plain",
                        "configurations": [
                            {
                                "fields": [
                                    _canonical_engine_mode_field(
                                        field_id="plain_myint_engine_mode"
                                    ),
                                    _canonical_engine_field(
                                        field_id="plain_myint_engine",
                                        integration_id="MyInt",
                                        dynamic_field="engine",
                                    ),
                                    _canonical_engine_field(
                                        field_id="plain_myint_engineGroup",
                                        integration_id="MyInt",
                                        dynamic_field="engine-group",
                                    ),
                                ],
                            },
                        ],
                    },
                    {
                        "id": "oauth",
                        "type": "oauth",
                        "configurations": [
                            {
                                "fields": [
                                    _canonical_engine_mode_field(
                                        field_id="oauth_myint_engine_mode"
                                    ),
                                    _canonical_engine_field(
                                        field_id="oauth_myint_engine",
                                        integration_id="MyInt",
                                        dynamic_field="engine",
                                    ),
                                    _canonical_engine_field(
                                        field_id="oauth_myint_engineGroup",
                                        integration_id="MyInt",
                                        dynamic_field="engine-group",
                                    ),
                                ],
                            },
                        ],
                    },
                ],
            },
        )
        # Only plain_myint_ exposes a proxy field.
        _stamp_proxy_resolved_param(
            connector, raw_id="plain_myint_proxy", runtime_name="proxy"
        )
        # Ship both hide triggers for both prefixes AND unlock-proxy
        # ONLY for plain_myint_. This must pass.
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger("plain_myint_"),
                _hide_engine_group_trigger("plain_myint_"),
                _unlock_proxy_trigger("plain_myint_"),
                _hide_engine_trigger("oauth_myint_"),
                _hide_engine_group_trigger("oauth_myint_"),
                # No unlock-proxy for oauth_myint_ (no proxy field for it).
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_grouped_two_handlers_share_bare_prefix_no_proxy_leakage(self):
        """Regression: grouped connector where two profiles share the empty
        (bare) prefix, split across two XSOAR handlers -- one handler exposes
        engine_mode/engine/engineGroup with NO proxy field, the other exposes
        ONLY proxy. CO148 must scope proxy detection PER HANDLER via
        ``resolved_params``: since no single handler exposes BOTH engine_mode
        and proxy under the bare prefix, the bare unlock-proxy trigger must
        NOT be required, and hide-triggers only must pass.

        This locks the fix for the cross-profile proxy leakage that caused
        false-positives on cisco-security, red-hat-ansible, mongodb, imperva,
        box-automation-and-collection, threatconnect,
        m365-automation-and-collection, and salesforce.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            ResolvedParamMapping,
        )
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        # Grouped connector with TWO profiles, both using bare (empty)
        # prefix. Profile A carries the engine triplet; profile B carries a
        # single proxy field. They share the empty prefix -- the same shape
        # as cisco-security's plain.amp + plain.ampv2.
        connector = create_connector_object(
            connector_overrides={"settings": {"grouped": True}},
            connection_data={
                "profiles": [
                    {
                        "id": "profile_a",
                        "type": "plain",
                        "configurations": [
                            {
                                "fields": [
                                    _canonical_engine_mode_field(
                                        field_id="engine_mode"
                                    ),
                                    _canonical_engine_field(
                                        field_id="engine",
                                        integration_id="MyInt",
                                        dynamic_field="engine",
                                    ),
                                    _canonical_engine_field(
                                        field_id="engineGroup",
                                        integration_id="MyInt",
                                        dynamic_field="engine-group",
                                    ),
                                ],
                            },
                        ],
                    },
                    {
                        "id": "profile_b",
                        "type": "plain",
                        "configurations": [
                            {
                                "fields": [
                                    {
                                        "id": "proxy",
                                        "type": "boolean",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            handlers=[
                {"id": "xsoar-a"},
                {"id": "xsoar-b"},
            ],
        )

        # Handler A is bound to profile_a and only exposes the engine fields.
        connector.handlers[0].resolved_params = [
            ResolvedParamMapping(
                connector_param_name="engine_mode",
                content_param_name="engine_mode",
            ),
            ResolvedParamMapping(
                connector_param_name="engine",
                content_param_name="engine",
            ),
            ResolvedParamMapping(
                connector_param_name="engineGroup",
                content_param_name="engineGroup",
            ),
        ]
        # Handler B is bound to profile_b and only exposes the proxy field --
        # crucially, NOT engine_mode, so the bare-prefix engine_mode must not
        # be paired with any proxy field on this handler either.
        connector.handlers[1].resolved_params = [
            ResolvedParamMapping(
                connector_param_name="proxy",
                content_param_name="proxy",
            ),
        ]

        # Only the two hide triggers for the bare prefix are shipped. No
        # unlock-proxy trigger for the empty prefix -- and CO148 must NOT
        # complain, because no handler exposes both engine_mode and proxy
        # under that prefix.
        _write_triggers_yaml(
            connector,
            [
                _hide_engine_trigger(""),
                _hide_engine_group_trigger(""),
            ],
        )
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == []

    def test_error_path_points_to_triggers_yaml(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO148_is_valid_engine_triggers import (
            IsValidEngineTriggersValidator,
        )

        connector = _connector_with_standard_engine_fields()
        _write_triggers_yaml(connector, [])  # empty triggers list
        results = IsValidEngineTriggersValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert str(results[0].path).endswith("triggers.yaml")


# ============================================================
# CO150 test helpers
# ============================================================
CO150_MESSAGE = (
    "A selected capability enables this setting. "
    "Clear the active dependency to disable it"
)


def _auto_enable_trigger(fetch_cap_ids: list, automation_cap_id: str) -> dict:
    """Canonical CO150 auto-enable trigger for a handler."""
    return {
        "conditions": {
            "operator": "OR",
            "children": [
                {
                    "id": cid,
                    "behavior": "selected",
                    "operator": "eq",
                    "value": True,
                }
                for cid in fetch_cap_ids
            ],
        },
        "effects": [
            {
                "id": automation_cap_id,
                "action": {"read_only": True, "enabled": True},
                "message": CO150_MESSAGE,
            }
        ],
    }


def _stamp_connector_capabilities(connector, cap_ids: list) -> None:
    """Set ``connector.capabilities`` to a list of CapabilityData
    stubs with the given ids (top-level, no sub-capabilities). Used
    to advertise the ``automation-and-remediation`` cap so CO150
    knows the handler has a lock target."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        CapabilityData,
    )

    connector.capabilities = [CapabilityData(id=cid) for cid in cap_ids]


def _connector_with_multi_fetch(handler_flag_maps: list):
    """Build a connector whose N handlers each emit one or more fetch
    flags via ``serializer.computed_fields``.

    Each entry in ``handler_flag_maps`` is a dict describing ONE
    handler. Keys are flag ids (e.g. ``isFetch``, ``isFetchEvents``,
    ``feed``, ``isFetchAssets``, ``isFetchCredentials``, or a
    non-fetch flag like ``isMappable`` for negative cases) and values
    are the gating capability id. For every (flag_id, cap_id) pair we
    add ONE ``ComputedFieldRule`` that outputs ``flag_id=True`` under
    a ``capability`` condition ``{capability_id: cap_id, value: on}``
    — the exact shape CO149/CO150 discovery walks.

    Handlers are marked XSOAR-owned and also carry a
    ``HandlerCapability`` per unique cap id, mirroring the wiring
    that ``_wire_handler_for_fetch_issues`` produces for CO130.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        ComputedCondition,
        ComputedConditionGroup,
        ComputedFieldRule,
        ComputedOutput,
        HandlerCapability,
        SerializerData,
    )

    # One handler per entry. ``create_connector_object`` merges each
    # handler override on top of the default handler template, so we
    # only need to give each handler a distinct id.
    handler_overrides = [
        {"id": f"xsoar-fetch-{idx}"} for idx, _ in enumerate(handler_flag_maps)
    ]
    connector = create_connector_object(handlers=handler_overrides)

    for handler, flag_map in zip(connector.handlers, handler_flag_maps):
        handler.metadata.module = "xsoar"

        rules = []
        cap_ids_seen: list = []
        for flag_id, cap_id in flag_map.items():
            rules.append(
                ComputedFieldRule(
                    output=[ComputedOutput(id=flag_id, value=True)],
                    any_of=[
                        ComputedConditionGroup(
                            conditions=[
                                ComputedCondition(
                                    type="capability",
                                    options={
                                        "capability_id": cap_id,
                                        "value": "on",
                                    },
                                )
                            ]
                        )
                    ],
                )
            )
            if cap_id not in cap_ids_seen:
                cap_ids_seen.append(cap_id)

        handler.serializer = SerializerData(
            field_mappings=[],
            computed_fields=rules,
        )
        handler.capabilities = [
            HandlerCapability(
                id=cid,
                auth_options=[],
                workloads=[],
                actions=[],
            )
            for cid in cap_ids_seen
        ]

    return connector


class TestCO150IsCollectionAutoEnablesAutomation:
    """Tests for CO150: for each handler emitting a fetch flag (via
    serializer computed_fields) that also has an
    ``automation-and-remediation`` cap on the connector, triggers.yaml
    must contain the canonical auto-enable trigger."""

    # ------------------------------------------------------------
    # Skip cases
    # ------------------------------------------------------------
    def test_no_fetch_handlers_short_circuits(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = create_connector_object()
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    def test_fetch_handler_without_automation_cap_short_circuits(self):
        """A handler with a fetch cap but no automation-and-remediation
        cap declared on the connector → nothing to lock → skip."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        # No automation-and-remediation declared → skip.
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    def test_non_fetch_serializer_flag_ignored(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch(
            [{"isMappable": "mapping-support"}]  # not a fetch flag
        )
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    # ------------------------------------------------------------
    # Valid cases
    # ------------------------------------------------------------
    def test_single_fetch_cap_with_or_wrapper_passes(self):
        """Single fetch cap still requires the OR wrapper (children of
        length 1)."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        _write_triggers_yaml(
            connector,
            [_auto_enable_trigger(["fetch-issues"], "automation-and-remediation")],
        )
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    def test_two_fetch_caps_full_or_passes(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch(
            [
                {
                    "isFetch": "fetch-issues",
                    "isFetchEvents": "log-collection",
                }
            ]
        )
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        _write_triggers_yaml(
            connector,
            [
                _auto_enable_trigger(
                    ["fetch-issues", "log-collection"],
                    "automation-and-remediation",
                )
            ],
        )
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    def test_grouped_namespaced_ids_pass(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        suffix = "akamai-waf-siem"
        fetch_ids = [
            f"fetch-issues_{suffix}",
            f"log-collection_{suffix}",
        ]
        automation_id = f"automation-and-remediation_{suffix}"
        connector = _connector_with_multi_fetch(
            [{"isFetch": fetch_ids[0], "isFetchEvents": fetch_ids[1]}]
        )
        _stamp_connector_capabilities(connector, [automation_id])
        _write_triggers_yaml(
            connector, [_auto_enable_trigger(fetch_ids, automation_id)]
        )
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    # ------------------------------------------------------------
    # Hard-fail cases
    # ------------------------------------------------------------
    def test_missing_triggers_yaml_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        # No _write_triggers_yaml call.
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "triggers.yaml is missing" in results[0].message

    def test_missing_auto_enable_trigger_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        _write_triggers_yaml(connector, [])  # empty triggers
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "fetch-issues" in results[0].message
        assert "automation-and-remediation" in results[0].message

    def test_wrong_message_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        bad = _auto_enable_trigger(["fetch-issues"], "automation-and-remediation")
        bad["effects"][0]["message"] = "Wrong message"
        _write_triggers_yaml(connector, [bad])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_action_missing_enabled_key_fails(self):
        """Action must have BOTH read_only and enabled."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        bad = _auto_enable_trigger(["fetch-issues"], "automation-and-remediation")
        bad["effects"][0]["action"] = {"read_only": True}  # missing enabled
        _write_triggers_yaml(connector, [bad])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_action_extra_key_fails(self):
        """Strict action shape: extra keys beyond read_only+enabled fail."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        bad = _auto_enable_trigger(["fetch-issues"], "automation-and-remediation")
        bad["effects"][0]["action"] = {
            "read_only": True,
            "enabled": True,
            "hidden": False,
        }
        _write_triggers_yaml(connector, [bad])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_missing_child_in_or_fails(self):
        """OR children must EXACTLY match the fetch cap set."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch(
            [
                {
                    "isFetch": "fetch-issues",
                    "isFetchEvents": "log-collection",
                }
            ]
        )
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        # Provide a trigger with only one child instead of two.
        bad = _auto_enable_trigger(["fetch-issues"], "automation-and-remediation")
        _write_triggers_yaml(connector, [bad])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_extra_child_in_or_fails(self):
        """OR children must EXACTLY match the fetch cap set — extras fail."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        bad = _auto_enable_trigger(
            ["fetch-issues", "log-collection"],
            "automation-and-remediation",
        )
        _write_triggers_yaml(connector, [bad])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_child_value_false_fails(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        bad = _auto_enable_trigger(["fetch-issues"], "automation-and-remediation")
        bad["conditions"]["children"][0]["value"] = False
        _write_triggers_yaml(connector, [bad])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_non_or_condition_fails(self):
        """Even for single fetch cap, the wrapping must be OR."""
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        # Bare non-OR condition — CO150 rejects.
        bad = {
            "conditions": {
                "id": "fetch-issues",
                "behavior": "selected",
                "operator": "eq",
                "value": True,
            },
            "effects": [
                {
                    "id": "automation-and-remediation",
                    "action": {"read_only": True, "enabled": True},
                    "message": CO150_MESSAGE,
                }
            ],
        }
        _write_triggers_yaml(connector, [bad])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    # ------------------------------------------------------------
    # Multi-handler independence + aggregation
    # ------------------------------------------------------------
    def test_multi_handler_independent(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch(
            [
                {
                    "isFetch": "fetch-issues_akamai-waf-siem",
                    "isFetchEvents": "log-collection_akamai-waf-siem",
                },
                {
                    "isFetch": "fetch-issues_guardicore-v2",
                },
            ]
        )
        _stamp_connector_capabilities(
            connector,
            [
                "automation-and-remediation_akamai-waf-siem",
                "automation-and-remediation_guardicore-v2",
            ],
        )
        _write_triggers_yaml(
            connector,
            [
                _auto_enable_trigger(
                    [
                        "fetch-issues_akamai-waf-siem",
                        "log-collection_akamai-waf-siem",
                    ],
                    "automation-and-remediation_akamai-waf-siem",
                ),
                _auto_enable_trigger(
                    ["fetch-issues_guardicore-v2"],
                    "automation-and-remediation_guardicore-v2",
                ),
            ],
        )
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert results == []

    def test_multi_handler_one_missing_aggregates(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch(
            [
                {"isFetch": "fetch-issues_akamai-waf-siem"},
                {"isFetch": "fetch-issues_guardicore-v2"},
            ]
        )
        _stamp_connector_capabilities(
            connector,
            [
                "automation-and-remediation_akamai-waf-siem",
                "automation-and-remediation_guardicore-v2",
            ],
        )
        # Only provide trigger for the first integration.
        _write_triggers_yaml(
            connector,
            [
                _auto_enable_trigger(
                    ["fetch-issues_akamai-waf-siem"],
                    "automation-and-remediation_akamai-waf-siem",
                )
            ],
        )
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "guardicore-v2" in msg
        # akamai should NOT appear in the error.
        assert "akamai-waf-siem" not in msg

    def test_error_path_points_to_triggers_yaml(self):
        from demisto_sdk.commands.validate.validators.CO_validators.CO150_is_collection_auto_enables_automation import (
            IsCollectionAutoEnablesAutomationValidator,
        )

        connector = _connector_with_multi_fetch([{"isFetch": "fetch-issues"}])
        _stamp_connector_capabilities(connector, ["automation-and-remediation"])
        _write_triggers_yaml(connector, [])
        results = (
            IsCollectionAutoEnablesAutomationValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert str(results[0].path).endswith("triggers.yaml")


# ---------------------------------------------------------------------------
# CO155 tests
# ---------------------------------------------------------------------------


def _clear_xsoar_signals(handler) -> None:
    """Reset every XSOAR signal on a handler to non-xsoar defaults."""
    handler.metadata.module = "third_party"
    handler.metadata.ownership.team = "third_party"
    handler.metadata.ownership.maintainers = ["@third-party-content"]


class TestCO155IsHandlerModuleXsoar:
    """Tests for CO155: every XSOAR-classified handler (via HandlerData.is_xsoar
    — OR of {module=="xsoar", team=="xsoar", "@xsoar-content" in maintainers})
    must carry the canonical self-declaring signal ``metadata.module: xsoar``.
    """

    def test_module_xsoar_passes(self):
        """
        Given: A default connector whose handler has metadata.module == "xsoar".
        When: CO155 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        # Sanity: the default template sets module=xsoar.
        assert connector.handlers[0].metadata.module == "xsoar"

        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_xsoar_by_team_missing_module_fails(self):
        """
        Given: An xsoar-classified handler (team == "xsoar") whose
               metadata.module is missing.
        When: CO155 runs.
        Then: One error is emitted referencing the handler.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        # Clear maintainers signal so team is the only xsoar-classifying flag.
        handler.metadata.ownership.maintainers = ["@third-party-content"]
        # Break module while leaving team == "xsoar" (still is_xsoar via team).
        handler.metadata.module = None
        assert handler.is_xsoar is True

        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert handler.id in results[0].message
        assert "expected 'xsoar'" in results[0].message

    def test_xsoar_by_maintainers_missing_module_fails(self):
        """
        Given: An xsoar-classified handler (maintainers contains
               "@xsoar-content") whose metadata.module is missing.
        When: CO155 runs.
        Then: One error is emitted referencing the handler.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.metadata.ownership.team = "third_party"
        handler.metadata.ownership.maintainers = ["@xsoar-content"]
        handler.metadata.module = None
        assert handler.is_xsoar is True

        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert handler.id in results[0].message

    def test_xsoar_by_maintainers_wrong_module_fails(self):
        """
        Given: An xsoar-classified handler whose metadata.module is set to a
               non-xsoar value (e.g. "third_party").
        When: CO155 runs.
        Then: One error is emitted; the actual (wrong) module value is
              surfaced in the message.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.metadata.ownership.team = "third_party"
        handler.metadata.ownership.maintainers = ["@xsoar-content"]
        handler.metadata.module = "third_party"
        assert handler.is_xsoar is True

        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "third_party" in results[0].message

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A handler with no xsoar signals whatsoever (module/team/
               maintainers all non-xsoar).
        When: CO155 runs.
        Then: No error — the handler is not xsoar-classified so the rule
              does not apply.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        _clear_xsoar_signals(handler)
        assert handler.is_xsoar is False

        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_error_per_handler_not_per_connector(self):
        """
        Given: A connector with two xsoar-classified handlers, both with
               non-xsoar module values.
        When: CO155 runs.
        Then: Two errors are emitted (one per failing handler), not a single
              connector-level aggregate.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-handler-a",
                    "metadata": {
                        "module": "third_party",
                        # Keep team=xsoar (template default) so is_xsoar is True.
                    },
                },
                {
                    "id": "xsoar-handler-b",
                    "metadata": {
                        "module": None,
                    },
                },
            ]
        )
        assert all(h.is_xsoar for h in connector.handlers)

        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 2
        offenders = {
            hid
            for hid in ("xsoar-handler-a", "xsoar-handler-b")
            if any(hid in r.message for r in results)
        }
        assert offenders == {"xsoar-handler-a", "xsoar-handler-b"}

    def test_mixed_valid_and_invalid_handlers(self):
        """
        Given: One valid xsoar handler and one invalid xsoar handler in the
               same connector.
        When: CO155 runs.
        Then: Only the invalid handler produces an error.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-good",
                    "metadata": {"module": "xsoar"},
                },
                {
                    "id": "xsoar-bad",
                    "metadata": {"module": "third_party"},
                },
            ]
        )
        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "xsoar-bad" in results[0].message
        assert "xsoar-good" not in results[0].message

    def test_error_path_points_to_handler_yaml(self):
        """
        Given: An xsoar-classified handler with a wrong module.
        When: CO155 runs.
        Then: The ValidationResult.path points at the handler.yaml
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-test",
                    "metadata": {"module": "third_party"},
                },
            ]
        )
        results = IsHandlerModuleXsoarValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO156 tests
# ---------------------------------------------------------------------------


class TestCO156IsHandlerOwnershipFieldsAlign:
    """Tests for CO156: every XSOAR-classified handler (via HandlerData.is_xsoar)
    must have `metadata.ownership.team == "xsoar"` AND `"@xsoar-content"` in
    `metadata.ownership.maintainers` (contains-check, mirroring CO100).
    Both problems on the same handler are aggregated into a single result.
    """

    def test_aligned_ownership_passes(self):
        """
        Given: A default connector whose handler has team=xsoar and
               maintainers contains '@xsoar-content'.
        When: CO156 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        # Sanity: template default is aligned.
        handler.metadata.ownership.team = "xsoar"
        handler.metadata.ownership.maintainers = ["@xsoar-content"]

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_wrong_team_fails(self):
        """
        Given: An xsoar-classified handler (via maintainers) whose
               team != 'xsoar'.
        When: CO156 runs.
        Then: One error citing the team problem.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.metadata.ownership.team = "third_party"
        handler.metadata.ownership.maintainers = ["@xsoar-content"]
        assert handler.is_xsoar is True

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert handler.id in msg
        assert "team" in msg
        assert "third_party" in msg
        # Should NOT complain about maintainers.
        assert "maintainers must contain" not in msg

    def test_missing_maintainer_fails(self):
        """
        Given: An xsoar-classified handler (via team) whose maintainers does
               NOT contain '@xsoar-content'.
        When: CO156 runs.
        Then: One error citing the maintainers problem.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.metadata.ownership.team = "xsoar"
        handler.metadata.ownership.maintainers = ["@some-other-team"]
        assert handler.is_xsoar is True

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert handler.id in msg
        assert "maintainers must contain '@xsoar-content'" in msg
        assert "@some-other-team" in msg

    def test_empty_maintainers_fails(self):
        """
        Given: An xsoar-classified handler (via team) whose maintainers list
               is empty.
        When: CO156 runs.
        Then: One error citing the maintainers problem; current-list rendered
              as '[]'.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.metadata.ownership.team = "xsoar"
        handler.metadata.ownership.maintainers = []
        assert handler.is_xsoar is True

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "maintainers must contain '@xsoar-content'" in msg
        assert "[]" in msg

    def test_both_problems_aggregate_into_single_result(self):
        """
        Given: An xsoar-classified handler (via module) with BOTH wrong team
               AND missing maintainer.
        When: CO156 runs.
        Then: A single result carrying both problem sentences (joined by
              '; ') — no double-emission per handler.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        # is_xsoar via module only.
        handler.metadata.module = "xsoar"
        handler.metadata.ownership.team = "third_party"
        handler.metadata.ownership.maintainers = ["@third-party-content"]
        assert handler.is_xsoar is True

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert "team" in msg
        assert "maintainers must contain" in msg
        # Both problem sentences joined by '; '.
        assert "; " in msg

    def test_co_maintainers_permitted(self):
        """
        Given: An xsoar-classified handler whose maintainers contains
               '@xsoar-content' PLUS additional co-maintainers.
        When: CO156 runs.
        Then: No error — CO156 uses a contains-check (mirroring CO100), so
              co-maintainers are permitted.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.metadata.ownership.team = "xsoar"
        handler.metadata.ownership.maintainers = [
            "@xsoar-content",
            "@partner-team",
            "@another-team",
        ]

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A handler with no xsoar signals (all three cleared).
        When: CO156 runs.
        Then: No error — the rule does not apply to non-xsoar handlers.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        _clear_xsoar_signals(handler)
        assert handler.is_xsoar is False

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_error_per_handler_not_per_connector(self):
        """
        Given: A connector with two xsoar-classified handlers, both
               misaligned.
        When: CO156 runs.
        Then: Two results (one per failing handler), not a single aggregated
              connector-level result.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-handler-a",
                    "metadata": {
                        "ownership": {
                            "team": "third_party",
                            "maintainers": ["@xsoar-content"],
                        }
                    },
                },
                {
                    "id": "xsoar-handler-b",
                    "metadata": {
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@other"],
                        }
                    },
                },
            ]
        )
        assert all(h.is_xsoar for h in connector.handlers)

        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 2
        offenders = {
            hid
            for hid in ("xsoar-handler-a", "xsoar-handler-b")
            if any(hid in r.message for r in results)
        }
        assert offenders == {"xsoar-handler-a", "xsoar-handler-b"}

    def test_mixed_valid_and_invalid_handlers(self):
        """
        Given: One aligned xsoar handler + one misaligned.
        When: CO156 runs.
        Then: Only the misaligned one produces a result.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-good",
                    "metadata": {
                        "ownership": {
                            "team": "xsoar",
                            "maintainers": ["@xsoar-content"],
                        }
                    },
                },
                {
                    "id": "xsoar-bad",
                    "metadata": {
                        "ownership": {
                            "team": "wrong",
                            "maintainers": ["@xsoar-content"],
                        }
                    },
                },
            ]
        )
        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "xsoar-bad" in results[0].message
        assert "xsoar-good" not in results[0].message

    def test_error_path_points_to_handler_yaml(self):
        """
        Given: A misaligned xsoar handler.
        When: CO156 runs.
        Then: The ValidationResult.path is the offending handler.yaml
              (mirroring CO155 handler-scoped path behaviour).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-test",
                    "metadata": {
                        "ownership": {
                            "team": "third_party",
                            "maintainers": [],
                        }
                    },
                },
            ]
        )
        results = IsHandlerOwnershipFieldsAlignValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO165 tests
# ---------------------------------------------------------------------------


def _stub_integration_with_pack(
    object_id: str = "TestIntegration", pack_id: str = "TestPack"
) -> SimpleNamespace:
    """Build a lightweight integration stub carrying the two fields CO165 uses.

    CO165 only touches ``related_integration.pack_id`` and
    ``related_integration.object_id``. The heavy ``create_integration_object``
    helper returns a real Integration whose ``pack_id`` is a computed property
    hard to override in-place, so tests use this stub instead.
    """
    return SimpleNamespace(object_id=object_id, pack_id=pack_id)


class TestCO165IsHandlerMatchingPackExist:
    """Tests for CO165: every XSOAR handler's `xsoar-pack-id` triggering label
    must match the pack that owns the handler's resolved integration
    (``handler.related_integration.pack_id``). Consistency-based; uses only
    already-resolved data.
    """

    def test_matching_pack_id_passes(self):
        """
        Given: An XSOAR handler with xsoar-pack-id='TestPack' (template
               default) and a resolved integration whose pack_id is 'TestPack'.
        When: CO165 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        # Sanity: template default is xsoar-pack-id: TestPack.
        assert handler.xsoar_pack_id == "TestPack"
        handler.related_integration = _stub_integration_with_pack(
            object_id="TestIntegration", pack_id="TestPack"
        )

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_missing_pack_id_label_fails(self):
        """
        Given: A handler whose triggering.labels omits xsoar-pack-id
               entirely (only xsoar-integration-id is present).
        When: CO165 runs.
        Then: One error citing the missing label.
        """
        connector = create_connector_object(handlers=[{"id": "xsoar-nopack"}])
        handler = connector.handlers[0]
        # The connector template's default labels include xsoar-pack-id,
        # and `handlers=[{...}]` merges rather than replaces, so overwrite
        # the labels dict directly to actually remove the pack-id label.
        handler.triggering.labels = {"xsoar-integration-id": "TestIntegration"}
        assert handler.xsoar_pack_id is None
        handler.related_integration = _stub_integration_with_pack()

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert handler.id in msg
        assert "missing xsoar-pack-id" in msg

    def test_unresolved_integration_fails(self):
        """
        Given: A handler with an xsoar-pack-id label but no resolved
               related_integration (integration missing from content graph).
        When: CO165 runs.
        Then: One error indicating the pack-id cannot be verified; message
              points at CO164 as the underlying cause.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        assert handler.xsoar_pack_id == "TestPack"
        assert handler.related_integration is None

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert handler.id in msg
        assert "TestPack" in msg
        assert "cannot be verified" in msg
        assert "CO164" in msg

    def test_mismatched_pack_id_fails(self):
        """
        Given: A handler with xsoar-pack-id='DeclaredPack' but the resolved
               integration lives in a pack called 'ActualPack'.
        When: CO165 runs.
        Then: One error naming the declared, actual, and integration ids.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-mismatched",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "TestIntegration",
                            "xsoar-pack-id": "DeclaredPack",
                        }
                    },
                },
            ]
        )
        handler = connector.handlers[0]
        handler.related_integration = _stub_integration_with_pack(
            object_id="TestIntegration", pack_id="ActualPack"
        )

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        msg = results[0].message
        assert handler.id in msg
        assert "DeclaredPack" in msg
        assert "ActualPack" in msg
        assert "TestIntegration" in msg
        assert "does not match" in msg

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A handler with no xsoar signals (module/team/maintainers all
               non-xsoar) and no pack-id label.
        When: CO165 runs.
        Then: No error \u2014 the handler is not xsoar-classified so the rule does
              not apply.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        _clear_xsoar_signals(handler)
        # Even if we clear pack-id, the handler shouldn't produce an error
        # because it's not xsoar-scoped.
        assert handler.is_xsoar is False

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_error_per_handler_not_per_connector(self):
        """
        Given: A connector with two xsoar handlers - one missing the label,
               one with a mismatched pack.
        When: CO165 runs.
        Then: Two results (one per failing handler), not aggregated.
        """
        connector = create_connector_object(
            handlers=[
                {"id": "xsoar-nopack"},
                {"id": "xsoar-mismatched"},
            ]
        )
        # Address handlers by id (the connector may sort them alphabetically
        # so index-based access is unsafe).
        by_id = {h.id: h for h in connector.handlers}
        nopack = by_id["xsoar-nopack"]
        mismatched = by_id["xsoar-mismatched"]

        # Nopack: strip pack-id from the (merged) template labels.
        nopack.triggering.labels = {"xsoar-integration-id": "TestIntegration"}
        nopack.related_integration = _stub_integration_with_pack()

        # Mismatched: label says WrongPack, actual owner is ActualPack.
        mismatched.triggering.labels = {
            "xsoar-integration-id": "TestIntegration",
            "xsoar-pack-id": "WrongPack",
        }
        mismatched.related_integration = _stub_integration_with_pack(
            pack_id="ActualPack"
        )

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 2
        offenders = {
            hid
            for hid in ("xsoar-nopack", "xsoar-mismatched")
            if any(hid in r.message for r in results)
        }
        assert offenders == {"xsoar-nopack", "xsoar-mismatched"}

    def test_mixed_valid_and_invalid_handlers(self):
        """
        Given: One valid handler (matching pack) + one invalid (mismatched).
        When: CO165 runs.
        Then: Only the invalid one produces a result.
        """
        connector = create_connector_object(
            handlers=[
                {"id": "xsoar-good"},
                {"id": "xsoar-bad"},
            ]
        )
        # Address handlers by id (connector may sort them alphabetically).
        by_id = {h.id: h for h in connector.handlers}
        good = by_id["xsoar-good"]
        bad = by_id["xsoar-bad"]

        good.triggering.labels = {
            "xsoar-integration-id": "TestIntegration",
            "xsoar-pack-id": "MatchingPack",
        }
        good.related_integration = _stub_integration_with_pack(pack_id="MatchingPack")

        bad.triggering.labels = {
            "xsoar-integration-id": "TestIntegration",
            "xsoar-pack-id": "WrongPack",
        }
        bad.related_integration = _stub_integration_with_pack(pack_id="ActualPack")

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "xsoar-bad" in results[0].message
        assert "xsoar-good" not in results[0].message

    def test_error_path_points_to_handler_yaml(self):
        """
        Given: An xsoar handler with a mismatched pack-id.
        When: CO165 runs.
        Then: ValidationResult.path is the offending handler.yaml (mirrors
              CO155/156/157 handler-scoped path behaviour).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-test",
                    "triggering": {
                        "labels": {
                            "xsoar-integration-id": "TestIntegration",
                            "xsoar-pack-id": "WrongPack",
                        }
                    },
                },
            ]
        )
        connector.handlers[0].related_integration = _stub_integration_with_pack(
            pack_id="ActualPack"
        )

        results = IsHandlerMatchingPackExistValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO159 tests
# ---------------------------------------------------------------------------


def _canonical_test_connection():
    """Return a fresh canonical HandlerTestConnection block matching the
    manifest requirement.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        HandlerTestConnection,
    )

    return HandlerTestConnection(
        type="service",
        service="xsoar",
        endpoint="/settings/integration/connector/verification",
    )


def _stamp_canonical_tc(handler) -> None:
    """Overwrite both test_connection and test_connection_metro on a handler
    with fresh canonical blocks so CO159 passes for the baseline handler.
    """
    handler.test_connection = _canonical_test_connection()
    handler.test_connection_metro = _canonical_test_connection()


class TestCO159IsHandlerHasValidTestConnection:
    """Tests for CO159: every XSOAR handler must carry both `test_connection`
    and `test_connection_metro` equal to exactly
    `{type: service, service: xsoar, endpoint: /settings/integration/connector/verification}`.
    """

    def test_canonical_both_blocks_passes(self):
        """
        Given: A handler whose test_connection and test_connection_metro
               both equal the canonical block.
        When: CO159 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        _stamp_canonical_tc(connector.handlers[0])

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_default_empty_test_connection_fails(self):
        """
        Given: The template default handler where both blocks are empty
               (test_connection has all-None fields; test_connection_metro is
               None).
        When: CO159 runs.
        Then: One result aggregating problems from both blocks.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert handler.id in msg
        assert "test_connection.type" in msg
        assert "test_connection.service" in msg
        assert "test_connection.endpoint" in msg
        assert "test_connection_metro block is missing" in msg

    def test_metro_missing_fails(self):
        """
        Given: A handler with a valid test_connection but no
               test_connection_metro.
        When: CO159 runs.
        Then: One result citing only the missing-metro problem (base block
              is fine).
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.test_connection = _canonical_test_connection()
        handler.test_connection_metro = None

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "test_connection_metro block is missing" in msg
        # base block should not appear as a problem
        assert "test_connection.type" not in msg
        assert "test_connection.service" not in msg
        assert "test_connection.endpoint" not in msg

    def test_wrong_type_fails(self):
        """
        Given: test_connection.type == 'endpoint' (not 'service').
        When: CO159 runs.
        Then: A single result citing the type mismatch in the base block.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerTestConnection,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.test_connection = HandlerTestConnection(
            type="endpoint",
            service="xsoar",
            endpoint="/settings/integration/connector/verification",
        )
        handler.test_connection_metro = _canonical_test_connection()

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "test_connection.type is 'endpoint'" in msg
        assert "expected 'service'" in msg

    def test_wrong_service_fails(self):
        """
        Given: test_connection.service == 'other' (not 'xsoar').
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerTestConnection,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.test_connection = HandlerTestConnection(
            type="service",
            service="other",
            endpoint="/settings/integration/connector/verification",
        )
        handler.test_connection_metro = _canonical_test_connection()

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "test_connection.service is 'other'" in results[0].message
        assert "expected 'xsoar'" in results[0].message

    def test_wrong_endpoint_fails(self):
        """
        Given: test_connection.endpoint is a different path.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerTestConnection,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.test_connection = HandlerTestConnection(
            type="service",
            service="xsoar",
            endpoint="/wrong/endpoint",
        )
        handler.test_connection_metro = _canonical_test_connection()

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "test_connection.endpoint is '/wrong/endpoint'" in results[0].message

    def test_extra_host_fails(self):
        """
        Given: A canonical test_connection that additionally sets `host`.
        When: CO159 runs.
        Then: One result citing the extra host field.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerTestConnection,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        forbidden_host = "bad-host-value"
        handler.test_connection = HandlerTestConnection(
            type="service",
            service="xsoar",
            endpoint="/settings/integration/connector/verification",
            host=forbidden_host,
        )
        handler.test_connection_metro = _canonical_test_connection()

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "test_connection.host must be omitted" in results[0].message
        assert forbidden_host in results[0].message

    def test_extra_headers_fails(self):
        """
        Given: A canonical test_connection that additionally sets `headers`.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerTestConnection,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.test_connection = HandlerTestConnection(
            type="service",
            service="xsoar",
            endpoint="/settings/integration/connector/verification",
            headers={"X-Custom": "yes"},
        )
        handler.test_connection_metro = _canonical_test_connection()

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "test_connection.headers must be omitted" in results[0].message

    def test_both_blocks_wrong_aggregates(self):
        """
        Given: Both blocks are wrong (different types).
        When: CO159 runs.
        Then: A single result covering both blocks (aggregated by '; ').
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerTestConnection,
        )

        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.test_connection = HandlerTestConnection(
            type="endpoint",
            service="xsoar",
            endpoint="/settings/integration/connector/verification",
        )
        handler.test_connection_metro = HandlerTestConnection(
            type="service",
            service="other",
            endpoint="/settings/integration/connector/verification",
        )

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "test_connection.type is 'endpoint'" in msg
        assert "test_connection_metro.service is 'other'" in msg
        assert "; " in msg

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A non-xsoar handler with a completely broken test_connection.
        When: CO159 runs.
        Then: No error - the rule does not apply to non-xsoar handlers.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        _clear_xsoar_signals(handler)
        assert handler.is_xsoar is False

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_error_per_handler_not_per_connector(self):
        """
        Given: Two xsoar handlers, both broken.
        When: CO159 runs.
        Then: Two results (one per failing handler).
        """
        connector = create_connector_object(
            handlers=[
                {"id": "xsoar-handler-a"},
                {"id": "xsoar-handler-b"},
            ]
        )
        # Both handlers keep the template default (empty blocks) -> both fail.
        assert all(h.is_xsoar for h in connector.handlers)

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 2
        offenders = {
            hid
            for hid in ("xsoar-handler-a", "xsoar-handler-b")
            if any(hid in r.message for r in results)
        }
        assert offenders == {"xsoar-handler-a", "xsoar-handler-b"}

    def test_mixed_valid_and_invalid_handlers(self):
        """
        Given: One valid xsoar handler + one invalid.
        When: CO159 runs.
        Then: Only the invalid one produces a result.
        """
        connector = create_connector_object(
            handlers=[
                {"id": "xsoar-good"},
                {"id": "xsoar-bad"},
            ]
        )
        by_id = {h.id: h for h in connector.handlers}
        _stamp_canonical_tc(by_id["xsoar-good"])
        # xsoar-bad keeps default empty blocks.

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "xsoar-bad" in results[0].message
        assert "xsoar-good" not in results[0].message

    def test_error_path_points_to_handler_yaml(self):
        """
        Given: An xsoar handler with broken test_connection wiring.
        When: CO159 runs.
        Then: ValidationResult.path is the offending handler.yaml
              (mirrors CO155/156/165 handler-scoped path behaviour).
        """
        connector = create_connector_object()
        # Template defaults leave both blocks empty/None -> failure.

        results = (
            IsHandlerHasValidTestConnectionValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO161 tests
# ---------------------------------------------------------------------------


def _cap_with_actions(cap_id: str, action_types: list, **extras):
    """Build a HandlerCapability dict-shaped block that create_connector_object
    can consume, with the given cap id and a list of action.type strings.
    """
    entry = {
        "id": cap_id,
        "auth_options": [
            {
                "id": "plain.test",
                "workloads": ["xsoar-pod", "xsoar-automationhub-runner"],
            }
        ],
        "actions": [{"type": t} for t in action_types],
    }
    entry.update(extras)
    return entry


class TestCO161IsFetchCapabilitiesContainActions:
    """Tests for CO161: every subscribed fetch-family capability must
    declare its required reset-state action. `automation-and-remediation`
    is intentionally NOT in the required-action mapping.
    """

    def test_no_fetch_capabilities_passes(self):
        """
        Given: A handler whose only capability is a non-fetch/non-automation
               capability (e.g. 'incident-response').
        When: CO161 runs.
        Then: No errors - the mapping doesn't apply.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-generic",
                    "capabilities": [_cap_with_actions("incident-response", [])],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_fetch_secrets_has_no_required_action(self):
        """
        Given: fetch-secrets capability with no actions.
        When: CO161 runs.
        Then: No error - fetch-secrets is stateless per the mapping.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-secrets",
                    "capabilities": [_cap_with_actions("fetch-secrets", [])],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_fetch_issues_with_correct_action_passes(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-fetchissues",
                    "capabilities": [
                        _cap_with_actions("fetch-issues", ["reset_incidents_last_run"])
                    ],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_fetch_issues_missing_action_fails(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-fetchissues",
                    "capabilities": [_cap_with_actions("fetch-issues", [])],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "fetch-issues" in msg
        assert "reset_incidents_last_run" in msg

    def test_namespaced_capability_id_stripped_to_base(self):
        """
        Given: A namespaced cap id 'fetch-issues_akamai-waf-siem' with
               the correct action.
        When: CO161 runs.
        Then: No error - the base id is stripped before mapping lookup.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-nsissues",
                    "capabilities": [
                        _cap_with_actions(
                            "fetch-issues_akamai-waf-siem",
                            ["reset_incidents_last_run"],
                        )
                    ],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_wrong_action_type_fails(self):
        """
        Given: fetch-issues capability with an action but of the wrong type.
        When: CO161 runs.
        Then: One error citing the required-vs-found types.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-fetchissues",
                    "capabilities": [
                        _cap_with_actions("fetch-issues", ["reset_events_last_run"])
                    ],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "reset_incidents_last_run" in msg
        assert "reset_events_last_run" in msg

    def test_all_fetch_families_valid_passes(self):
        """
        Given: A handler with one capability from each fetch family, each
               with its correct action, plus fetch-secrets (stateless),
               automation-and-remediation (not a fetch family, no action
               required), and a non-fetch cap.
        When: CO161 runs.
        Then: No error.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-multi",
                    "capabilities": [
                        _cap_with_actions("fetch-issues", ["reset_incidents_last_run"]),
                        _cap_with_actions("log-collection", ["reset_events_last_run"]),
                        _cap_with_actions(
                            "fetch-assets-and-vulnerabilities",
                            ["reset_assets_last_run"],
                        ),
                        _cap_with_actions(
                            "threat-intelligence-and-enrichment",
                            ["reset_feed_last_run"],
                        ),
                        _cap_with_actions("automation-and-remediation", []),
                        _cap_with_actions("fetch-secrets", []),
                        _cap_with_actions("incident-response", []),
                    ],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_automation_and_remediation_only_no_action_passes(self):
        """
        Given: An XSOAR handler whose only capability is
               `automation-and-remediation` and declares no actions
               (like cuckoo-sandbox on disk).
        When: CO161 runs.
        Then: No error - automation-and-remediation is NOT a fetch family
              and is intentionally excluded from the required-action mapping.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-cuckoo-sandbox",
                    "capabilities": [
                        _cap_with_actions(
                            "automation-and-remediation_cuckoo-sandbox", []
                        )
                    ],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_automation_and_remediation_with_optional_action_passes(self):
        """
        Given: A handler with `automation-and-remediation` that DOES
               declare an action (e.g. `reset_integration_context`).
        When: CO161 runs.
        Then: No error - actions on automation-and-remediation are always
              permitted, they're just never required.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-with-optional-action",
                    "capabilities": [
                        _cap_with_actions(
                            "automation-and-remediation",
                            ["reset_integration_context"],
                        )
                    ],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_multiple_capabilities_aggregate_into_single_result(self):
        """
        Given: Multiple fetch-family capabilities all missing their required
               actions, alongside an automation-and-remediation cap with no
               actions (which must NOT be reported).
        When: CO161 runs.
        Then: A single per-handler result listing only the fetch-family
              offenders. `automation-and-remediation` is never reported.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-broken",
                    "capabilities": [
                        _cap_with_actions("fetch-issues", []),
                        _cap_with_actions("log-collection", []),
                        _cap_with_actions("automation-and-remediation", []),
                    ],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        msg = results[0].message
        assert "fetch-issues" in msg
        assert "log-collection" in msg
        assert "reset_incidents_last_run" in msg
        assert "reset_events_last_run" in msg
        # automation-and-remediation must NOT be reported since it is not
        # in the required-action mapping.
        assert "automation-and-remediation" not in msg
        assert "reset_integration_context" not in msg
        # Aggregation separator between the two fetch-family findings.
        assert "; " in msg

    def test_non_xsoar_handler_ignored(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-nx",
                    "capabilities": [_cap_with_actions("fetch-issues", [])],
                }
            ]
        )
        _clear_xsoar_signals(connector.handlers[0])

        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_error_path_points_to_handler_yaml(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-broken",
                    "capabilities": [_cap_with_actions("fetch-issues", [])],
                }
            ]
        )
        results = (
            IsFetchCapabilitiesContainActionsValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO162 tests
# ---------------------------------------------------------------------------


def _cap_with_workloads(
    cap_id: str,
    auth_options_workloads: list,
    cap_level_workloads: list = None,
):
    """Build a HandlerCapability dict where:
    - Each entry in ``auth_options_workloads`` produces one auth_option with
      that specific ``workloads`` list.
    - ``cap_level_workloads`` (optional) sets the anonymous capability-level
      ``workloads``.
    """
    entry: dict = {
        "id": cap_id,
        "auth_options": [
            {"id": f"plain.{i}", "workloads": list(w)}
            for i, w in enumerate(auth_options_workloads)
        ],
    }
    if cap_level_workloads is not None:
        entry["workloads"] = list(cap_level_workloads)
    return entry


class TestCO162IsValidWorkloads:
    """Tests for CO162: every auth_options[].workloads must equal the
    canonical set {xsoar-automationhub-runner, xsoar-pod} (order-insensitive),
    and no capability may declare the anonymous capability-level workloads
    shape.
    """

    def test_canonical_workloads_passes(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-wl",
                    "capabilities": [
                        _cap_with_workloads(
                            "fetch-issues",
                            [["xsoar-pod", "xsoar-automationhub-runner"]],
                        )
                    ],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 0

    def test_reverse_order_passes(self):
        """Order-insensitive: reverse order still equals the canonical set."""
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-wl-rev",
                    "capabilities": [
                        _cap_with_workloads(
                            "fetch-issues",
                            [["xsoar-automationhub-runner", "xsoar-pod"]],
                        )
                    ],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 0

    def test_missing_workload_fails(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-wl-missing",
                    "capabilities": [
                        _cap_with_workloads("fetch-issues", [["xsoar-pod"]])
                    ],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        msg = results[0].message
        assert "fetch-issues" in msg
        assert "plain.0" in msg
        assert "xsoar-automationhub-runner" in msg

    def test_extra_workload_fails(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-wl-extra",
                    "capabilities": [
                        _cap_with_workloads(
                            "fetch-issues",
                            [
                                [
                                    "xsoar-pod",
                                    "xsoar-automationhub-runner",
                                    "xsoar-extra",
                                ]
                            ],
                        )
                    ],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "xsoar-extra" in results[0].message

    def test_empty_workloads_fails(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-wl-empty",
                    "capabilities": [_cap_with_workloads("fetch-issues", [[]])],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert "[]" in results[0].message

    def test_capability_level_workloads_fails(self):
        """
        Given: A capability that carries capability-level workloads (the
               anonymous auth: none shape) alongside auth_options.
        When: CO162 runs.
        Then: The capability-level workloads presence is flagged
              (regardless of whether auth_options themselves are valid).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-cap-wl",
                    "capabilities": [
                        _cap_with_workloads(
                            "fetch-issues",
                            [["xsoar-pod", "xsoar-automationhub-runner"]],
                            cap_level_workloads=[
                                "xsoar-pod",
                                "xsoar-automationhub-runner",
                            ],
                        )
                    ],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        msg = results[0].message
        assert "capability-level workloads" in msg
        assert "auth_options" in msg

    def test_multiple_auth_options_aggregate(self):
        """
        Given: A capability with 2 auth_options, both with broken workloads.
        When: CO162 runs.
        Then: One aggregated result citing both auth_options.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-multi-ao",
                    "capabilities": [
                        _cap_with_workloads(
                            "fetch-issues",
                            [["xsoar-pod"], []],
                        )
                    ],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        msg = results[0].message
        assert "plain.0" in msg
        assert "plain.1" in msg
        assert "; " in msg

    def test_non_xsoar_handler_ignored(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-nx",
                    "capabilities": [
                        _cap_with_workloads("fetch-issues", [["xsoar-pod"]])
                    ],
                }
            ]
        )
        _clear_xsoar_signals(connector.handlers[0])

        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 0

    def test_error_path_points_to_handler_yaml(self):
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-wl-broken",
                    "capabilities": [
                        _cap_with_workloads("fetch-issues", [["xsoar-pod"]])
                    ],
                }
            ]
        )
        results = IsValidWorkloadsValidator().obtain_invalid_content_items([connector])
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO170 tests
# ---------------------------------------------------------------------------


class TestCO170IsHandlerMigrationConstants:
    """Tests for CO170: every XSOAR handler must carry
    ``triggering.type: "PUB_SUB"`` (per DESIGN §3.8).
    """

    def test_default_pub_sub_passes(self):
        """
        Given: The default connector template (triggering.type == "PUB_SUB").
        When: CO170 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        # Sanity: the default template sets triggering.type = "PUB_SUB".
        assert connector.handlers[0].triggering.type == "PUB_SUB"

        results = IsHandlerMigrationConstantsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_wrong_triggering_type_fails(self):
        """
        Given: An XSOAR handler with triggering.type set to a non-PUB_SUB value
               (e.g. "ZERO_SCALE").
        When: CO170 runs.
        Then: One error is emitted; both the expected and the actual value are
              surfaced in the message.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.triggering.type = "ZERO_SCALE"

        results = IsHandlerMigrationConstantsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert handler.id in results[0].message
        assert "'PUB_SUB'" in results[0].message
        assert "'ZERO_SCALE'" in results[0].message

    def test_missing_triggering_type_fails(self):
        """
        Given: An XSOAR handler whose triggering.type is unset (None).
        When: CO170 runs.
        Then: One error is emitted; ``None`` is surfaced as the actual value.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.triggering.type = None

        results = IsHandlerMigrationConstantsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert handler.id in results[0].message
        assert "None" in results[0].message

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A non-xsoar handler (all three xsoar signals cleared) with a
               broken triggering.type.
        When: CO170 runs.
        Then: No error - the validator only inspects XSOAR handlers.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        _clear_xsoar_signals(handler)
        handler.triggering.type = "ZERO_SCALE"
        assert handler.is_xsoar is False

        results = IsHandlerMigrationConstantsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_error_per_handler_not_per_connector(self):
        """
        Given: A connector with multiple XSOAR handlers, all with wrong
               triggering.type.
        When: CO170 runs.
        Then: One error per offending handler (not one per connector), each
              carrying the corresponding handler.id in the message.
        """
        connector = create_connector_object(
            handlers=[
                {"id": "xsoar-a"},
                {"id": "xsoar-b"},
            ]
        )
        # Address handlers by id to survive alphabetical sorting.
        by_id = {h.id: h for h in connector.handlers}
        by_id["xsoar-a"].triggering.type = "ZERO_SCALE"
        by_id["xsoar-b"].triggering.type = None

        results = IsHandlerMigrationConstantsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 2
        offenders = {"xsoar-a", "xsoar-b"}
        assert {
            h_id for h_id in offenders if any(h_id in r.message for r in results)
        } == offenders

    def test_mixed_valid_and_invalid_handlers(self):
        """
        Given: A connector where one XSOAR handler is valid and another is
               invalid.
        When: CO170 runs.
        Then: Only the offending handler is flagged.
        """
        connector = create_connector_object(
            handlers=[
                {"id": "xsoar-good"},
                {"id": "xsoar-bad"},
            ]
        )
        by_id = {h.id: h for h in connector.handlers}
        # xsoar-good keeps the default PUB_SUB; xsoar-bad is broken.
        by_id["xsoar-bad"].triggering.type = "ZERO_SCALE"

        results = IsHandlerMigrationConstantsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "xsoar-bad" in results[0].message
        assert "xsoar-good" not in results[0].message

    def test_error_path_points_to_handler_yaml(self):
        """
        Given: A connector with one offending XSOAR handler.
        When: CO170 runs.
        Then: The result's path points at that handler's ``handler.yaml``.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.triggering.type = "ZERO_SCALE"

        results = IsHandlerMigrationConstantsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == handler.file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO171 / CO172 tests
# ---------------------------------------------------------------------------


def _serializer_with_rules(rules):
    """Build a SerializerData with the given ComputedFieldRule list."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        SerializerData,
    )

    return SerializerData(field_mappings=[], computed_fields=rules)


def _fetch_flag_rule(
    flag_id: str,
    capability_id: str,
    value=True,
    condition_value: str = "on",
    condition_type: str = "capability",
):
    """Build one ComputedFieldRule that outputs ``flag_id: value`` gated on
    the given capability condition."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        ComputedCondition,
        ComputedConditionGroup,
        ComputedFieldRule,
        ComputedOutput,
    )

    return ComputedFieldRule(
        output=[ComputedOutput(id=flag_id, value=value)],
        any_of=[
            ComputedConditionGroup(
                conditions=[
                    ComputedCondition(
                        type=condition_type,
                        options={
                            "capability_id": capability_id,
                            "value": condition_value,
                        },
                    )
                ]
            )
        ],
    )


def _handler_capability(cap_id: str):
    from demisto_sdk.commands.content_graph.objects.connector import (
        HandlerCapability,
    )

    return HandlerCapability(id=cap_id, auth_options=[], workloads=[], actions=[])


class TestCO171IsCollectionSubCapabilityFetchFlagValid:
    """Tests for CO171: every subscribed collection sub-capability
    must have a matching fetch-flag emission in the handler's
    serializer.yaml, gated on the right capability+value.
    """

    def test_related_file_type_includes_serializer(self):
        """
        Given: The CO171 validator class as declared.
        When: We inspect its ``related_file_type``.
        Then: It contains BOTH ``CONNECTOR_HANDLER`` and
              ``CONNECTOR_SERIALIZER``.

        Why this is a real gate, not paperwork:

        * ``ConnectorsValidator.should_run`` calls
          ``is_error_ignored(err, ignorable, item, self.related_file_type)``
          which iterates ``related_file_type`` and calls
          ``_resolve_ignore_file_keys``. ``CONNECTOR_HANDLER`` alone yields
          only ``<folder>/handler.yaml``, so a per-serializer
          ``.connector-ignore`` entry keyed by
          ``<folder>/serializer.yaml`` is never consulted and the
          validator runs unignored.
        * CO171 emits ``path = <handler_dir>/serializer.yaml``. The
          author-facing convention (and what CO130 does — see its
          ``related_file_type`` and the NOTE above it) is a serializer-scoped
          ignore. Dropping ``CONNECTOR_SERIALIZER`` silently reintroduces
          the CI regression where those ignores had no effect.
        """
        from demisto_sdk.commands.content_graph.parsers.related_files import (
            RelatedFileType,
        )

        validator = IsCollectionSubCapabilityFetchFlagValidValidator()
        assert RelatedFileType.CONNECTOR_HANDLER in validator.related_file_type
        assert RelatedFileType.CONNECTOR_SERIALIZER in validator.related_file_type

    def test_no_collection_cap_short_circuits(self):
        """
        Given: A handler that subscribes to no collection sub-capability
               (e.g. only 'incident-response') and has no serializer.
        When: CO171 runs.
        Then: No error - nothing to enforce.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("incident-response")]
        handler.serializer = None

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_canonical_fetch_issues_wiring_passes(self):
        """
        Given: A handler subscribing to fetch-issues with the canonical
               serializer rule emitting isFetch: true gated correctly.
        When: CO171 runs.
        Then: No error.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "fetch-issues")]
        )

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_grouped_namespaced_cap_passes(self):
        """
        Given: Grouped connector cap id 'fetch-issues_akamai-waf-siem' with
               a matching serializer rule.
        When: CO171 runs.
        Then: No error - base id is stripped for the mapping lookup.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        cap_id = "fetch-issues_akamai-waf-siem"
        handler.capabilities = [_handler_capability(cap_id)]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", cap_id)]
        )

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_missing_serializer_fails(self):
        """
        Given: Handler subscribes to fetch-issues but has no serializer.
        When: CO171 runs.
        Then: One error citing the missing serializer file.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = None

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "serializer.yaml is missing" in results[0].message

    def test_wrong_flag_id_fails(self):
        """
        Given: fetch-issues subscribed, but serializer emits isFetchEvents
               (wrong mapping) instead of isFetch.
        When: CO171 runs.
        Then: One error - no rule emits the expected isFetch.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetchEvents", "fetch-issues")]
        )

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "isFetch" in results[0].message

    def test_wrong_condition_value_fails(self):
        """
        Given: isFetch emitted but gated on value 'off' (not 'on').
        When: CO171 runs.
        Then: One error - the gate is wrong.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "fetch-issues", condition_value="off")]
        )

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1

    def test_gate_targets_different_cap_fails(self):
        """
        Given: Handler subscribes to fetch-issues, but the isFetch rule is
               gated on a different capability id.
        When: CO171 runs.
        Then: One error - the rule doesn't gate on THIS subscribed cap.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "some-other-cap")]
        )

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1

    def test_all_five_families_pass(self):
        """
        Given: A handler subscribing to all 5 collection sub-caps with a
               correct rule per flag.
        When: CO171 runs.
        Then: No error.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [
            _handler_capability("fetch-issues"),
            _handler_capability("log-collection"),
            _handler_capability("fetch-assets-and-vulnerabilities"),
            _handler_capability("fetch-secrets"),
            _handler_capability("threat-intelligence-and-enrichment"),
        ]
        handler.serializer = _serializer_with_rules(
            [
                _fetch_flag_rule("isFetch", "fetch-issues"),
                _fetch_flag_rule("isFetchEvents", "log-collection"),
                _fetch_flag_rule("isFetchAssets", "fetch-assets-and-vulnerabilities"),
                _fetch_flag_rule("isFetchCredentials", "fetch-secrets"),
                _fetch_flag_rule("feed", "threat-intelligence-and-enrichment"),
            ]
        )

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_multiple_missing_aggregate(self):
        """
        Given: Handler subscribes to two collection caps and the serializer
               is missing rules for both.
        When: CO171 runs.
        Then: One aggregated result citing both offenders.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [
            _handler_capability("fetch-issues"),
            _handler_capability("log-collection"),
        ]
        handler.serializer = _serializer_with_rules([])

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "fetch-issues" in results[0].message
        assert "log-collection" in results[0].message

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A non-xsoar handler subscribed to fetch-issues with a broken
               serializer.
        When: CO171 runs.
        Then: No error - the validator only inspects XSOAR handlers.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        _clear_xsoar_signals(handler)
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = None
        assert handler.is_xsoar is False

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_error_path_points_to_serializer_yaml(self):
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules([])

        results = IsCollectionSubCapabilityFetchFlagValidValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert str(results[0].path).endswith("serializer.yaml")


class TestCO172IsFetchFlagGatedOnOwnSubCapability:
    """Tests for CO172: every fetch-flag emission in the serializer
    must be gated on a cap this handler subscribes to AND whose base id
    matches the emitted flag's family.
    """

    def test_no_serializer_short_circuits(self):
        """
        Given: A handler with no serializer.
        When: CO172 runs.
        Then: No error - CO171 covers the missing serializer case.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = None

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_no_fetch_flag_output_short_circuits(self):
        """
        Given: A serializer that emits only a non-fetch flag (e.g.
               incidentFetchInterval).
        When: CO172 runs.
        Then: No error - only fetch flags are validated by this rule.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("incidentFetchInterval", "fetch-issues", value="1")]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_valid_wiring_passes(self):
        """
        Given: isFetch gated on the subscribed fetch-issues cap.
        When: CO172 runs.
        Then: No error.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "fetch-issues")]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_grouped_namespaced_id_passes(self):
        """
        Given: isFetch gated on 'fetch-issues_akamai-waf-siem' and the
               handler subscribes to that exact id.
        When: CO172 runs.
        Then: No error - namespaced id matches after base-id derivation.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        cap_id = "fetch-issues_akamai-waf-siem"
        handler.capabilities = [_handler_capability(cap_id)]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", cap_id)]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_gate_on_non_subscribed_cap_fails(self):
        """
        Given: isFetch gated on 'fetch-issues_other' but handler subscribes
               only to 'fetch-issues_ours'.
        When: CO172 runs.
        Then: One error - the gate references a cap this handler doesn't
              subscribe to.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues_ours")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "fetch-issues_other")]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "isFetch" in results[0].message

    def test_gate_on_wrong_family_fails(self):
        """
        Given: isFetch (fetch-issues family) gated on a cap of a different
               family (log-collection) that IS subscribed.
        When: CO172 runs.
        Then: One error - base id family doesn't match the flag.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [
            _handler_capability("fetch-issues"),
            _handler_capability("log-collection"),
        ]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "log-collection")]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_automation_cap_gate_fails_subsumes_co173(self):
        """
        Given: A fetch flag gated on 'automation-and-remediation' - the
               CO173 negative rule.
        When: CO172 runs.
        Then: One error - automation-and-remediation is not in the mapping,
              so it fails the family check.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [
            _handler_capability("automation-and-remediation"),
        ]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "automation-and-remediation")]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1

    def test_no_capability_gate_fails(self):
        """
        Given: A fetch-flag rule with only a `type: field` condition,
               no capability gate.
        When: CO172 runs.
        Then: One error citing the missing capability gate.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [
                _fetch_flag_rule(
                    "isFetch",
                    "fetch-issues",
                    condition_type="field",
                )
            ]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "no `type: capability` gate" in results[0].message

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A non-xsoar handler with a broken fetch-flag emission.
        When: CO172 runs.
        Then: No error - only XSOAR handlers are inspected.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        _clear_xsoar_signals(handler)
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "unrelated-cap")]
        )
        assert handler.is_xsoar is False

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 0

    def test_multiple_bad_rules_aggregate(self):
        """
        Given: Two fetch-flag rules, both mis-gated on the same handler.
        When: CO172 runs.
        Then: One aggregated result listing both problems.
        """
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [
                _fetch_flag_rule("isFetch", "wrong-cap"),
                _fetch_flag_rule("isFetchEvents", "other-wrong-cap"),
            ]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert "isFetch" in results[0].message
        assert "isFetchEvents" in results[0].message

    def test_error_path_points_to_serializer_yaml(self):
        connector = create_connector_object()
        handler = connector.handlers[0]
        handler.capabilities = [_handler_capability("fetch-issues")]
        handler.serializer = _serializer_with_rules(
            [_fetch_flag_rule("isFetch", "wrong-cap")]
        )

        results = (
            IsFetchFlagGatedOnOwnSubCapabilityValidator().obtain_invalid_content_items(
                [connector]
            )
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert str(results[0].path).endswith("serializer.yaml")


# ---------------------------------------------------------------------------
# CO175 tests
# ---------------------------------------------------------------------------


def _resolved_param(name: str, source_file: str = "connection.yaml"):
    """Build a ResolvedParamMapping mimicking parser output."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        ResolvedParamMapping,
    )

    return ResolvedParamMapping(
        connector_param_name=name,
        content_param_name=name,
        is_serialized=False,
        source_file=source_file,
    )


def _set_resolved_params(handler, names):
    """Overwrite handler.resolved_params with the given connector-side names."""
    handler.resolved_params = [_resolved_param(n) for n in names]


class TestCO175NoRemovedConnectorParams:
    """Tests for CO175: no `connector_param_name` in a handler's prior
    resolved_params may be missing in the new version.
    """

    def test_no_change_is_valid(self):
        """
        Given: A connector whose handler resolved_params equal the prior
               version's set.
        When: CO175 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_resolved_params(connector.handlers[0], ["proxy", "insecure", "url"])
        _set_resolved_params(old_connector.handlers[0], ["proxy", "insecure", "url"])
        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_added_param_is_valid(self):
        """
        Given: New version adds a param that wasn't in the prior version.
        When: CO175 runs.
        Then: No error - additions are allowed.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_resolved_params(old_connector.handlers[0], ["proxy", "insecure"])
        _set_resolved_params(connector.handlers[0], ["proxy", "insecure", "new_param"])
        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_removed_param_flagged(self):
        """
        Given: New version drops a param present in the prior version.
        When: CO175 runs.
        Then: One validation error listing the removed param.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_resolved_params(old_connector.handlers[0], ["proxy", "insecure", "url"])
        _set_resolved_params(connector.handlers[0], ["proxy", "insecure"])
        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "url" in results[0].message
        assert connector.handlers[0].id in results[0].message

    def test_multiple_removed_params_aggregate(self):
        """
        Given: Two params removed from the same handler.
        When: CO175 runs.
        Then: One aggregated result citing both removed params.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_resolved_params(
            old_connector.handlers[0], ["proxy", "insecure", "url", "port"]
        )
        _set_resolved_params(connector.handlers[0], ["proxy", "insecure"])
        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "url" in results[0].message
        assert "port" in results[0].message

    def test_no_old_object_skipped(self):
        """
        Given: A connector with no old_base_content_object.
        When: CO175 runs.
        Then: No error - nothing to compare against.
        """
        connector = create_connector_object()
        _set_resolved_params(connector.handlers[0], ["proxy", "insecure"])
        assert connector.old_base_content_object is None

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A non-xsoar handler with removed params.
        When: CO175 runs.
        Then: No error - only XSOAR handlers are diffed.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _clear_xsoar_signals(connector.handlers[0])
        _clear_xsoar_signals(old_connector.handlers[0])

        _set_resolved_params(old_connector.handlers[0], ["proxy", "insecure"])
        _set_resolved_params(connector.handlers[0], [])
        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_newly_added_handler_skipped(self):
        """
        Given: The new version has an additional handler that wasn't in the
               prior version (so has no prior resolved_params to compare).
        When: CO175 runs.
        Then: No error for the newly-added handler.
        """
        connector = create_connector_object(
            handlers=[{"id": "xsoar-old"}, {"id": "xsoar-new"}]
        )
        old_connector = create_connector_object(handlers=[{"id": "xsoar-old"}])

        # Match the shared handler's params exactly so it doesn't flag.
        old_by_id = {h.id: h for h in old_connector.handlers}
        new_by_id = {h.id: h for h in connector.handlers}
        _set_resolved_params(old_by_id["xsoar-old"], ["shared"])
        _set_resolved_params(new_by_id["xsoar-old"], ["shared"])
        _set_resolved_params(new_by_id["xsoar-new"], ["only_new"])

        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_error_per_handler_not_per_connector(self):
        """
        Given: Two XSOAR handlers each remove a different param.
        When: CO175 runs.
        Then: One result per offending handler, each carrying its own
              handler.id and its own removed param.
        """
        connector = create_connector_object(
            handlers=[{"id": "xsoar-a"}, {"id": "xsoar-b"}]
        )
        old_connector = create_connector_object(
            handlers=[{"id": "xsoar-a"}, {"id": "xsoar-b"}]
        )

        old_by_id = {h.id: h for h in old_connector.handlers}
        new_by_id = {h.id: h for h in connector.handlers}
        _set_resolved_params(old_by_id["xsoar-a"], ["url", "proxy"])
        _set_resolved_params(new_by_id["xsoar-a"], ["proxy"])
        _set_resolved_params(old_by_id["xsoar-b"], ["port", "insecure"])
        _set_resolved_params(new_by_id["xsoar-b"], ["insecure"])

        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 2
        offenders = {r.message for r in results}
        assert any("xsoar-a" in m and "'url'" in m for m in offenders)
        assert any("xsoar-b" in m and "'port'" in m for m in offenders)

    def test_error_path_points_to_handler_yaml(self):
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_resolved_params(old_connector.handlers[0], ["url"])
        _set_resolved_params(connector.handlers[0], [])
        connector.old_base_content_object = old_connector

        results = NoRemovedConnectorParamsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO176 tests
# ---------------------------------------------------------------------------


def _stub_profile(profile_id: str):
    """Build a minimal ConnectionProfile-shaped object addressable by id."""
    from demisto_sdk.commands.content_graph.objects.connector import (
        ConnectionProfile,
    )

    return ConnectionProfile(
        id=profile_id,
        type=None,
        title=None,
        description=None,
        view_group=None,
        vault_support=None,
        vault_mappings=[],
        discovery_url=None,
        token_endpoint=None,
        authorization_endpoint=None,
        client_id=None,
        client_secret=None,
        refresh_token_scope=None,
        options=None,
        metadata=None,
        configurations=[],
    )


def _set_profile_ids(connector, profile_ids):
    """Overwrite connector.connection.profiles with the given ids."""
    if connector.connection is None:
        return
    connector.connection.profiles = [_stub_profile(pid) for pid in profile_ids]


def _set_view_group_ids(connector, view_group_ids):
    """Overwrite connector.connection.view_groups with stubs carrying the
    given ids. Non-grouped connectors typically have an empty list here.
    """
    from demisto_sdk.commands.content_graph.objects.connector import ViewGroup

    if connector.connection is None:
        return
    connector.connection.view_groups = [ViewGroup(id=vgid) for vgid in view_group_ids]


class TestCO176NoChangeConnectorIDs:
    """Tests for CO176: the prior set of ids in each of the 6 id families
    (connector_id, handler_id, capability_id, sub_capability_id, profile_id,
    view_group_id) must be a subset of the new set (renames and removals
    both fail; additions are allowed).
    """

    def test_no_change_is_valid(self):
        """
        Given: A connector whose id families equal the prior version's.
        When: CO176 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_no_old_object_skipped(self):
        """
        Given: A connector with no old_base_content_object.
        When: CO176 runs.
        Then: No error - nothing to compare against.
        """
        connector = create_connector_object()
        assert connector.old_base_content_object is None

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_added_handler_is_valid(self):
        """
        Given: New version adds a new handler; every prior id is preserved.
        When: CO176 runs.
        Then: No error - additions are allowed.
        """
        old_connector = create_connector_object(handlers=[{"id": "xsoar-a"}])
        connector = create_connector_object(
            handlers=[{"id": "xsoar-a"}, {"id": "xsoar-b"}]
        )
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_removed_handler_flagged(self):
        """
        Given: New version drops a handler present in the prior version.
        When: CO176 runs.
        Then: One error citing the missing handler_id.
        """
        old_connector = create_connector_object(
            handlers=[{"id": "xsoar-a"}, {"id": "xsoar-b"}]
        )
        connector = create_connector_object(handlers=[{"id": "xsoar-a"}])
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "handler_id" in results[0].message
        assert "xsoar-b" in results[0].message

    def test_renamed_handler_flagged(self):
        """
        Given: A handler renamed between versions (id changed).
        When: CO176 runs.
        Then: One error - the prior id is missing from the new set.
        """
        old_connector = create_connector_object(handlers=[{"id": "xsoar-old-name"}])
        connector = create_connector_object(handlers=[{"id": "xsoar-new-name"}])
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "handler_id" in results[0].message
        assert "xsoar-old-name" in results[0].message

    def test_renamed_connector_id_flagged(self):
        """
        Given: The top-level connector id changed between versions.
        When: CO176 runs.
        Then: One error citing the missing connector_id.
        """
        old_connector = create_connector_object(connector_id="orig-connector")
        connector = create_connector_object(connector_id="renamed-connector")
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "connector_id" in results[0].message
        assert "orig-connector" in results[0].message

    def test_removed_capability_flagged(self):
        """
        Given: A capability present in the prior version is removed.
        When: CO176 runs.
        Then: One error citing the missing capability_id.
        """
        old_connector = create_connector_object(
            capabilities_data=_capabilities_payload(
                [
                    {"id": "cap-a", "title": "Cap A"},
                    {"id": "cap-b", "title": "Cap B"},
                ]
            )
        )
        connector = create_connector_object(
            capabilities_data=_capabilities_payload([{"id": "cap-a", "title": "Cap A"}])
        )
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "capability_id" in results[0].message
        assert "cap-b" in results[0].message

    def test_removed_sub_capability_flagged(self):
        """
        Given: A sub-capability present in the prior version is removed.
        When: CO176 runs.
        Then: One error citing the missing sub_capability_id.
        """
        old_connector = create_connector_object(
            capabilities_data=_capabilities_payload(
                [
                    {
                        "id": "cap-a",
                        "title": "Cap A",
                        "sub_capabilities": [
                            {"id": "sub-1", "title": "Sub 1"},
                            {"id": "sub-2", "title": "Sub 2"},
                        ],
                    }
                ]
            )
        )
        connector = create_connector_object(
            capabilities_data=_capabilities_payload(
                [
                    {
                        "id": "cap-a",
                        "title": "Cap A",
                        "sub_capabilities": [
                            {"id": "sub-1", "title": "Sub 1"},
                        ],
                    }
                ]
            )
        )
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "sub_capability_id" in results[0].message
        assert "sub-2" in results[0].message

    def test_removed_profile_id_flagged(self):
        """
        Given: A profile id present in the prior version is removed.
        When: CO176 runs.
        Then: One error citing the missing profile_id.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_profile_ids(old_connector, ["basic-auth", "oauth2"])
        _set_profile_ids(connector, ["basic-auth"])
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "profile_id" in results[0].message
        assert "oauth2" in results[0].message

    def test_removed_view_group_id_flagged(self):
        """
        Given: A view_group id present in the prior version is removed
               (grouped-connector scenario).
        When: CO176 runs.
        Then: One error citing the missing view_group_id.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_view_group_ids(old_connector, ["service-a", "service-b"])
        _set_view_group_ids(connector, ["service-a"])
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "view_group_id" in results[0].message
        assert "service-b" in results[0].message

    def test_non_grouped_no_view_groups_is_valid(self):
        """
        Given: A non-grouped connector - both old and new have no view_groups.
        When: CO176 runs.
        Then: No error - the family is naturally a no-op for non-grouped.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        # Neither side declares any view_groups.
        assert not (old_connector.connection and old_connector.connection.view_groups)
        assert not (connector.connection and connector.connection.view_groups)
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_multiple_families_aggregate_into_one_result(self):
        """
        Given: A handler AND a capability are both removed in the new version.
        When: CO176 runs.
        Then: A single aggregated result per connector citing both families.
        """
        old_connector = create_connector_object(
            handlers=[{"id": "xsoar-a"}, {"id": "xsoar-b"}],
            capabilities_data=_capabilities_payload(
                [
                    {"id": "cap-a", "title": "Cap A"},
                    {"id": "cap-b", "title": "Cap B"},
                ]
            ),
        )
        connector = create_connector_object(
            handlers=[{"id": "xsoar-a"}],
            capabilities_data=_capabilities_payload(
                [{"id": "cap-a", "title": "Cap A"}]
            ),
        )
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "handler_id" in results[0].message
        assert "xsoar-b" in results[0].message
        assert "capability_id" in results[0].message
        assert "cap-b" in results[0].message

    def test_error_path_points_to_connector_root(self):
        old_connector = create_connector_object(
            handlers=[{"id": "xsoar-a"}, {"id": "xsoar-b"}]
        )
        connector = create_connector_object(handlers=[{"id": "xsoar-a"}])
        connector.old_base_content_object = old_connector

        results = NoChangeConnectorIDsValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.path


# ---------------------------------------------------------------------------
# CO179 tests
# ---------------------------------------------------------------------------


_NO_DEFAULT = object()  # sentinel: caller did not pass default_value at all


def _field(
    field_id: str,
    create_required=None,
    edit_required=None,
    default_value=_NO_DEFAULT,
):
    """Build a ConnectorField carrying the given create/edit `required`
    modifier values. Passing ``None`` for a modifier omits the modifier
    block entirely, which the validator treats as False.

    ``default_value``: pass any concrete value (including ``None``, ``""``,
    ``0``, ``False``) to populate ``options.default_value``. Omit the
    argument entirely (sentinel-defaulted) to leave ``options.default_value``
    at its Pydantic default (``None``, meaning "no default declared").
    This distinction matters because CO179's default-exemption uses
    ``default_value is not None`` — so ``default_value=None`` explicitly
    is semantically the same as omitting it.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        ConnectorField,
        FieldModifiers,
        FieldOptions,
    )

    create_mod = (
        FieldModifiers(required=create_required)
        if create_required is not None
        else None
    )
    edit_mod = (
        FieldModifiers(required=edit_required) if edit_required is not None else None
    )
    options_kwargs = {
        "create_modifiers": create_mod,
        "edit_modifiers": edit_mod,
    }
    if default_value is not _NO_DEFAULT:
        options_kwargs["default_value"] = default_value
    return ConnectorField(
        id=field_id,
        title=field_id,
        options=FieldOptions(**options_kwargs),
    )


def _connection_with_general_fields(fields):
    """Build a ConnectorConnectionData whose general_configurations
    exposes the given ConnectorField list under a single FieldGroup.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        ConnectorConnectionData,
        FieldGroup,
        GeneralConfigurations,
    )

    return ConnectorConnectionData(
        general_configurations=GeneralConfigurations(
            configurations=[FieldGroup(fields=list(fields))]
        ),
        profiles=[],
    )


def _set_connection_general_fields(connector, fields):
    """Attach a connection.general_configurations block with the given
    ConnectorField list to the connector.
    """
    connector.connection = _connection_with_general_fields(fields)


class TestCO179NoParamRequiredTightened:
    """Tests for CO179: no XSOAR-visible field on an XSOAR handler may have
    `options.create_modifiers.required` OR `options.edit_modifiers.required`
    transition from false/unset to `true` between the prior and new versions.
    """

    def test_no_change_is_valid(self):
        """
        Given: A connector whose field modifiers are identical to the
               prior version.
        When: CO179 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False, edit_required=False)]
        )
        _set_connection_general_fields(
            connector, [_field("url", create_required=False, edit_required=False)]
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_create_modifier_tightened_flagged(self):
        """
        Given: A field whose `create_modifiers.required` flips false → true.
        When: CO179 runs.
        Then: One validation error mentioning the field and 'create'.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False, edit_required=False)]
        )
        _set_connection_general_fields(
            connector, [_field("url", create_required=True, edit_required=False)]
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "url" in results[0].message
        assert "create" in results[0].message
        assert "edit" not in results[0].message

    def test_edit_modifier_tightened_flagged(self):
        """
        Given: A field whose `edit_modifiers.required` flips false → true.
        When: CO179 runs.
        Then: One validation error mentioning the field and 'edit'.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False, edit_required=False)]
        )
        _set_connection_general_fields(
            connector, [_field("url", create_required=False, edit_required=True)]
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "url" in results[0].message
        assert "edit" in results[0].message

    def test_both_modifiers_tightened_flagged(self):
        """
        Given: Both create AND edit modifiers flip false → true on same field.
        When: CO179 runs.
        Then: One validation error mentioning both.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False, edit_required=False)]
        )
        _set_connection_general_fields(
            connector, [_field("url", create_required=True, edit_required=True)]
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "url" in results[0].message
        assert "create" in results[0].message
        assert "edit" in results[0].message

    def test_unset_to_true_treated_as_tightening(self):
        """
        Given: Old field had no modifier block (None); new field explicitly
               sets create_modifiers.required=True.
        When: CO179 runs.
        Then: Flagged - missing/unset counts as False, so any explicit True
              is a tightening.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector,
            [_field("url")],  # no modifiers at all
        )
        _set_connection_general_fields(connector, [_field("url", create_required=True)])
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "url" in results[0].message

    def test_relaxation_true_to_false_is_valid(self):
        """
        Given: Old field was required; new field is optional.
        When: CO179 runs.
        Then: No error - relaxation is always allowed.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=True, edit_required=True)]
        )
        _set_connection_general_fields(
            connector, [_field("url", create_required=False, edit_required=False)]
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_added_required_field_is_valid(self):
        """
        Given: A brand-new field that is required (not present in prior version).
        When: CO179 runs.
        Then: No error - only field ids present in BOTH versions are checked.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(old_connector, [])
        _set_connection_general_fields(
            connector, [_field("new_field", create_required=True, edit_required=True)]
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_removed_field_is_ignored(self):
        """
        Given: A required field present in old but absent from new.
        When: CO179 runs.
        Then: No error from CO179 (CO175 handles removals).
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("gone", create_required=True)]
        )
        _set_connection_general_fields(connector, [])
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_no_old_object_skipped(self):
        """
        Given: A connector with no old_base_content_object.
        When: CO179 runs.
        Then: No error - nothing to compare against.
        """
        connector = create_connector_object()
        _set_connection_general_fields(connector, [_field("url", create_required=True)])
        assert connector.old_base_content_object is None

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A non-xsoar handler where a field tightens.
        When: CO179 runs.
        Then: No error - only XSOAR handlers are diffed.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _clear_xsoar_signals(connector.handlers[0])
        _clear_xsoar_signals(old_connector.handlers[0])

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False)]
        )
        _set_connection_general_fields(connector, [_field("url", create_required=True)])
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_multiple_tightened_fields_aggregate(self):
        """
        Given: Two fields on the same handler both tighten.
        When: CO179 runs.
        Then: One aggregated result citing both field ids.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector,
            [
                _field("url", create_required=False),
                _field("port", create_required=False),
            ],
        )
        _set_connection_general_fields(
            connector,
            [
                _field("url", create_required=True),
                _field("port", create_required=True),
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "url" in results[0].message
        assert "port" in results[0].message

    def test_error_path_points_to_handler_yaml(self):
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False)]
        )
        _set_connection_general_fields(connector, [_field("url", create_required=True)])
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")

    # ------------------------------------------------------------------
    # Default-value exemption: a False->True `required` transition is
    # ALLOWED when the new field carries an explicit
    # ``options.default_value`` - the platform substitutes the default
    # for existing instances, so upgrade doesn't break saves.
    # Rule: exempt iff ``field.options.default_value is not None``
    # (presence semantics, matches the "system uses default if it doesn't
    # exist" rationale). Missing options.default_value / omitted argument
    # / explicit None all mean "no default declared" and remain flagged.
    # ------------------------------------------------------------------

    def test_create_tightened_with_default_value_is_exempt(self):
        """
        Given: A field whose ``create_modifiers.required`` flips
               false -> true AND the new field declares an explicit
               ``options.default_value``.
        When: CO179 runs.
        Then: No validation error - existing instances get the default
              on save, so the transition is non-breaking.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False)]
        )
        _set_connection_general_fields(
            connector,
            [
                _field(
                    "url",
                    create_required=True,
                    default_value="https://example.com",
                )
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == [], [r.message for r in results]

    def test_edit_tightened_with_default_value_is_exempt(self):
        """
        Same exemption applies to ``edit_modifiers.required`` transitions
        - the exemption is per-field, not per-modifier-kind.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", edit_required=False)]
        )
        _set_connection_general_fields(
            connector,
            [
                _field(
                    "url",
                    edit_required=True,
                    default_value="https://example.com",
                )
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == [], [r.message for r in results]

    def test_unset_to_true_with_default_value_is_exempt(self):
        """
        Same exemption applies to the "modifier was omitted, now
        explicitly True" tightening path already covered by
        ``test_unset_to_true_treated_as_tightening``.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(old_connector, [_field("url")])
        _set_connection_general_fields(
            connector,
            [
                _field(
                    "url",
                    create_required=True,
                    default_value="https://example.com",
                )
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == [], [r.message for r in results]

    def test_tightened_without_default_value_still_flagged(self):
        """
        Regression guard: a field with ``options`` present but no
        ``default_value`` (Pydantic default of ``None``) must still be
        flagged - the default-value exemption is opt-in, not implicit.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False)]
        )
        # Explicitly omit default_value - matches the pre-exemption
        # behavior; must still fail.
        _set_connection_general_fields(connector, [_field("url", create_required=True)])
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1, [r.message for r in results]
        assert "url" in results[0].message

    def test_default_value_explicit_none_is_not_exempt(self):
        """
        Semantic pin: ``default_value=None`` explicitly is the SAME as
        omitting it (no default declared), so the exemption does NOT
        fire and the tightening is flagged.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector, [_field("url", create_required=False)]
        )
        _set_connection_general_fields(
            connector,
            [_field("url", create_required=True, default_value=None)],
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1, [r.message for r in results]
        assert "url" in results[0].message

    def test_default_value_falsy_is_exempt(self):
        """
        Semantic pin: falsy-but-present default values (``""``, ``0``,
        ``False``) all count as "default declared" and exempt the field.
        These are legitimate defaults for string / duration / checkbox
        field types respectively.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector,
            [
                _field("str_field", create_required=False),
                _field("int_field", create_required=False),
                _field("bool_field", create_required=False),
            ],
        )
        _set_connection_general_fields(
            connector,
            [
                _field("str_field", create_required=True, default_value=""),
                _field("int_field", create_required=True, default_value=0),
                _field("bool_field", create_required=True, default_value=False),
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert results == [], [r.message for r in results]

    def test_default_value_exemption_is_per_field(self):
        """
        Mixed case: on the same handler, one field tightens with a
        default (exempt) and another tightens without (flagged). Only
        the second field appears in the aggregated result.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_connection_general_fields(
            old_connector,
            [
                _field("with_default", create_required=False),
                _field("no_default", create_required=False),
            ],
        )
        _set_connection_general_fields(
            connector,
            [
                _field(
                    "with_default",
                    create_required=True,
                    default_value="ok",
                ),
                _field("no_default", create_required=True),
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoParamRequiredTightenedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1, [r.message for r in results]
        msg = results[0].message
        assert "no_default" in msg
        assert "with_default" not in msg


# ---------------------------------------------------------------------------
# CO181 tests
# ---------------------------------------------------------------------------


def _handler_capability_with_auth_options(cap_id: str, auth_options: list):
    """Build a HandlerCapability with the given auth_options list.

    Each entry in ``auth_options`` is a dict ``{id, methods?}`` where
    ``methods`` may contain plain strings or ``{id, scopes?}`` dicts.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        HandlerAuthMethod,
        HandlerAuthOption,
        HandlerCapability,
    )

    built_aos = []
    for ao in auth_options:
        methods_raw = ao.get("methods", []) or []
        methods = []
        for m in methods_raw:
            if isinstance(m, dict):
                methods.append(
                    HandlerAuthMethod(id=m["id"], scopes=m.get("scopes", []))
                )
            else:
                methods.append(m)  # keep as string
        built_aos.append(
            HandlerAuthOption(
                id=ao["id"],
                scopes=ao.get("scopes", []),
                workloads=ao.get("workloads", []),
                methods=methods,
            )
        )
    return HandlerCapability(id=cap_id, auth_options=built_aos)


def _set_handler_capabilities(handler, caps):
    """Overwrite ``handler.capabilities`` with the given list of
    HandlerCapability objects.
    """
    handler.capabilities = list(caps)


class TestCO181NoRemovedAuthOption:
    """Tests for CO181: no auth_options[].id (per handler+cap) or
    auth_options[].methods[].id (per handler+cap+auth_option) present in
    the prior version may be removed.
    """

    def test_no_change_is_valid(self):
        """
        Given: A connector whose handler auth_options and methods equal the
               prior version's set.
        When: CO181 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        cap = _handler_capability_with_auth_options(
            "cap-a", [{"id": "oauth2", "methods": ["client_credentials"]}]
        )
        _set_handler_capabilities(connector.handlers[0], [cap])
        _set_handler_capabilities(old_connector.handlers[0], [cap])
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_added_auth_option_is_valid(self):
        """
        Given: A new auth_option added to an existing capability.
        When: CO181 runs.
        Then: No error - additions are allowed.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}])],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a", [{"id": "oauth2"}, {"id": "api_key"}]
                )
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_removed_auth_option_flagged(self):
        """
        Given: An auth_option present in the prior version is dropped.
        When: CO181 runs.
        Then: One validation error citing the capability and removed auth_option.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a", [{"id": "oauth2"}, {"id": "api_key"}]
                )
            ],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}])],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "cap-a" in results[0].message
        assert "api_key" in results[0].message

    def test_renamed_auth_option_flagged(self):
        """
        Given: An auth_option id is renamed (same cap, different id).
        When: CO181 runs.
        Then: The old id is reported as removed.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}])],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2_v2"}])],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "'oauth2'" in results[0].message
        assert "oauth2_v2" not in results[0].message

    def test_removed_method_flagged(self):
        """
        Given: An auth_option survives but one of its methods is removed.
        When: CO181 runs.
        Then: One validation error citing cap+auth_option and removed method.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a",
                    [{"id": "oauth2", "methods": ["client_credentials", "auth_code"]}],
                )
            ],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a", [{"id": "oauth2", "methods": ["client_credentials"]}]
                )
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "cap-a" in results[0].message
        assert "oauth2" in results[0].message
        assert "auth_code" in results[0].message

    def test_object_form_method_supported(self):
        """
        Given: Methods declared in object form ``{id, scopes}`` (not plain str).
        When: CO181 runs on a removed object-form method.
        Then: The method id is extracted from the object and reported.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a",
                    [
                        {
                            "id": "oauth2",
                            "methods": [
                                {"id": "client_credentials", "scopes": ["a"]},
                                {"id": "auth_code", "scopes": ["b"]},
                            ],
                        }
                    ],
                )
            ],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a",
                    [
                        {
                            "id": "oauth2",
                            "methods": [{"id": "client_credentials", "scopes": ["a"]}],
                        }
                    ],
                )
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "auth_code" in results[0].message

    def test_capability_dropped_is_not_reported_here(self):
        """
        Given: A whole capability is dropped between versions (CO176's
               capability_id family covers this).
        When: CO181 runs.
        Then: No CO181 error - it only fires for auth_options on capabilities
              that survive.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [
                _handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}]),
                _handler_capability_with_auth_options("cap-b", [{"id": "api_key"}]),
            ],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}])],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_no_old_object_skipped(self):
        """
        Given: A connector with no old_base_content_object.
        When: CO181 runs.
        Then: No error - nothing to compare against.
        """
        connector = create_connector_object()
        _set_handler_capabilities(
            connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}])],
        )
        assert connector.old_base_content_object is None

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A non-xsoar handler with removed auth_options.
        When: CO181 runs.
        Then: No error - only XSOAR handlers are diffed.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _clear_xsoar_signals(connector.handlers[0])
        _clear_xsoar_signals(old_connector.handlers[0])

        _set_handler_capabilities(
            old_connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a", [{"id": "oauth2"}, {"id": "api_key"}]
                )
            ],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}])],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_multiple_offenders_aggregate(self):
        """
        Given: Two capabilities on the same handler each lose an auth_option.
        When: CO181 runs.
        Then: One aggregated result citing both capabilities.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a", [{"id": "oauth2"}, {"id": "api_key"}]
                ),
                _handler_capability_with_auth_options(
                    "cap-b", [{"id": "oauth2"}, {"id": "basic"}]
                ),
            ],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [
                _handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}]),
                _handler_capability_with_auth_options("cap-b", [{"id": "oauth2"}]),
            ],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "cap-a" in results[0].message
        assert "cap-b" in results[0].message
        assert "api_key" in results[0].message
        assert "basic" in results[0].message

    def test_error_path_points_to_handler_yaml(self):
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_handler_capabilities(
            old_connector.handlers[0],
            [
                _handler_capability_with_auth_options(
                    "cap-a", [{"id": "oauth2"}, {"id": "api_key"}]
                )
            ],
        )
        _set_handler_capabilities(
            connector.handlers[0],
            [_handler_capability_with_auth_options("cap-a", [{"id": "oauth2"}])],
        )
        connector.old_base_content_object = old_connector

        results = NoRemovedAuthOptionValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        assert str(results[0].path).endswith("handler.yaml")


# ---------------------------------------------------------------------------
# CO183 tests
# ---------------------------------------------------------------------------


def _set_grouped(connector, value):
    """Set ``connector.settings.grouped`` to ``value``, materializing a
    default ConnectorSettings if the connector had none.
    """
    from demisto_sdk.commands.content_graph.objects.connector import (
        ConnectorSettings,
    )

    if connector.settings is None:
        connector.settings = ConnectorSettings()
    connector.settings.grouped = value


class TestCO183NoGroupedFlagFlipped:
    """Tests for CO183: ``settings.grouped`` must not change value between
    the prior and new versions of a connector.
    """

    def test_no_change_false_to_false_valid(self):
        """
        Given: Both old and new connectors have `settings.grouped == False`.
        When: CO183 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_grouped(old_connector, False)
        _set_grouped(connector, False)
        connector.old_base_content_object = old_connector

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_no_change_true_to_true_valid(self):
        """
        Given: Both old and new have `settings.grouped == True`.
        When: CO183 runs.
        Then: No validation errors.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_grouped(old_connector, True)
        _set_grouped(connector, True)
        connector.old_base_content_object = old_connector

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_false_to_true_flagged(self):
        """
        Given: Old grouped=False, new grouped=True.
        When: CO183 runs.
        Then: One validation error citing the old and new values.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_grouped(old_connector, False)
        _set_grouped(connector, True)
        connector.old_base_content_object = old_connector

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "False" in results[0].message
        assert "True" in results[0].message

    def test_true_to_false_flagged(self):
        """
        Given: Old grouped=True, new grouped=False.
        When: CO183 runs.
        Then: One validation error citing the old and new values.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_grouped(old_connector, True)
        _set_grouped(connector, False)
        connector.old_base_content_object = old_connector

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "True" in results[0].message
        assert "False" in results[0].message

    def test_missing_settings_treated_as_false(self):
        """
        Given: Old version has no `settings` block (equivalent to False);
               new version explicitly sets grouped=False.
        When: CO183 runs.
        Then: No error - both sides resolve to False.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        old_connector.settings = None
        _set_grouped(connector, False)
        connector.old_base_content_object = old_connector

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_missing_settings_to_true_flagged(self):
        """
        Given: Old version has no `settings` block (resolves to False);
               new version explicitly sets grouped=True.
        When: CO183 runs.
        Then: One error - False → True is still a flip.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()

        old_connector.settings = None
        _set_grouped(connector, True)
        connector.old_base_content_object = old_connector

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert "True" in results[0].message

    def test_no_old_object_skipped(self):
        """
        Given: A connector with no old_base_content_object.
        When: CO183 runs.
        Then: No error - nothing to compare against.
        """
        connector = create_connector_object()
        _set_grouped(connector, True)
        assert connector.old_base_content_object is None

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 0

    def test_error_path_points_to_connector_root(self):
        connector = create_connector_object()
        old_connector = create_connector_object()

        _set_grouped(old_connector, False)
        _set_grouped(connector, True)
        connector.old_base_content_object = old_connector

        results = NoGroupedFlagFlippedValidator().obtain_invalid_content_items(
            [connector]
        )
        assert len(results) == 1
        assert results[0].path is not None
        assert results[0].path == connector.path
