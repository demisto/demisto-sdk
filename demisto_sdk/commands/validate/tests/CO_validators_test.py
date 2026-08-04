"""Tests for CO (Connector) validators - CO100-CO106, CO164."""

import copy
from pathlib import Path
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
from demisto_sdk.commands.validate.validators.CO_validators.CO194_is_sub_capability_title_derived import (
    IsSubCapabilityTitleDerivedValidator,
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
from demisto_sdk.commands.validate.validators.CO_validators.CO157_is_handler_description_templated import (
    IsHandlerDescriptionTemplatedValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO164_is_matching_integration_exist import (
    IsMatchingIntegrationExistValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO177_no_removed_capabilities import (
    NoRemovedCapabilitiesValidator,
)
from demisto_sdk.commands.validate.validators.CO_validators.CO190_no_reserved_param_names import (
    NoReservedParamNamesValidator,
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
                "auth_options": [
                    {"id": "test-auth", "workloads": ["test-workload"]}
                ],
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
                _xsoar_handler_subscribing_to(
                    "fetch-issues", "bogus-base_myint"
                )
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
            ("Skyhigh Secure Web Gateway (On Prem)", "skyhigh-secure-web-gateway-on-prem"),
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
            integration
            if integration is not None
            else _stub_integration_flags()
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
    """Connector with a single (leaf) capability having the given id and title."""
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
        connector = _connector_with_capability_title(
            "fetch-issues", "Fetch Issues"
        )

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
        connector = _connector_with_capability_title(
            "fetch-issues", "fetch issues"
        )

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
    return SimpleNamespace(
        params=[SimpleNamespace(name=n) for n in names]
    )


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

        connector.handlers[0].related_integration = (
            _make_integration_with_params("proxy", "insecure")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("client_id", "client_secret")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("proxy", "insecure")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("proxy", "insecure")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("proxy", "insecure")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("proxy", "insecure")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("proxy", "insecure")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("unsecure")
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
        connector.handlers[0].related_integration = (
            _make_integration_with_params("useproxy")
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
        params=[
            SimpleNamespace(name=n, type=t) for (n, t) in name_type_pairs
        ]
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
    """
    fields = []
    for spec in field_specs:
        field = {
            "id": spec["id"],
            "title": spec.get("title", spec["id"]),
            "field_type": spec.get("field_type", "input"),
        }
        if spec.get("auth_parameter"):
            field["metadata"] = {"auth": {"parameter": spec["auth_parameter"]}}
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
        assert "does not match any field id or metadata.auth.parameter" in results[0].message

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
        assert "id=" in results[0].message

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
                "view_groups": [
                    {"id": "my-integration", "label": "My Integration"}
                ]
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


# ============================================================
# CO177 - NoRemovedCapabilitiesValidator
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
                "auth_options": [
                    {"id": profile_id, "workloads": ["test-workload"]}
                ],
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
                        [
                            {"id": "engine_mode", "field_type": "select"}
                        ],
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
# CO177 - NoRemovedCapabilitiesValidator
# ============================================================


class TestCO177NoRemovedCapabilities:
    """Tests for CO177: capabilities/sub-capabilities must not be removed."""

    def test_no_change_is_valid(self):
        """
        Given: A modified connector whose capabilities equal the prior version.
        When: CO177 runs.
        Then: No validation errors are returned.
        """
        connector = create_connector_object()
        old_connector = create_connector_object()
        connector.old_base_content_object = old_connector

        validator = NoRemovedCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_added_capability_is_valid(self):
        """
        Given: A connector that ADDS a capability relative to the prior version.
        When: CO177 runs.
        Then: No validation errors (additions are allowed).
        """
        old_connector = create_connector_object(
            capabilities_data=_capabilities_payload([{"id": "cap-a", "title": "Cap A"}])
        )
        connector = create_connector_object(
            capabilities_data=_capabilities_payload(
                [
                    {"id": "cap-a", "title": "Cap A"},
                    {"id": "cap-b", "title": "Cap B"},
                ]
            )
        )
        connector.old_base_content_object = old_connector

        validator = NoRemovedCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_removed_capability_flagged(self):
        """
        Given: A connector that REMOVES a capability present in the prior version.
        When: CO177 runs.
        Then: A validation error listing the removed capability is returned.
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

        validator = NoRemovedCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "cap-b" in results[0].message

    def test_removed_sub_capability_flagged(self):
        """
        Given: A connector that removes a SUB-capability from a kept capability.
        When: CO177 runs.
        Then: A validation error listing the removed sub-capability is returned.
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

        validator = NoRemovedCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "sub-2" in results[0].message

    def test_no_old_object_skipped(self):
        """
        Given: A connector with no old_base_content_object.
        When: CO177 runs.
        Then: No validation errors (nothing to compare against).
        """
        connector = create_connector_object()
        assert connector.old_base_content_object is None

        validator = NoRemovedCapabilitiesValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


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
# CO157 - IsHandlerDescriptionTemplatedValidator
# ============================================================


class TestCO157IsHandlerDescriptionTemplated:
    """Tests for CO157: each XSOAR handler's metadata.description must follow
    the template 'XSOAR handler for <name>.', where <name> is the
    resolved related integration's name. One error is emitted per failing
    handler (not per connector).
    """

    def test_valid_handler_description(self):
        """
        Given: A connector whose XSOAR handler has a resolved integration and a
               description matching 'XSOAR handler for <name>.'.
        When: CO157 runs.
        Then: No validation errors are returned.
        """
        integration = create_integration_object()
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-test",
                    "metadata": {
                        "description": (f"XSOAR handler for {integration.name}."),
                    },
                },
            ]
        )
        connector.handlers[0].related_integration = integration

        validator = IsHandlerDescriptionTemplatedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_invalid_handler_description(self):
        """
        Given: A connector whose XSOAR handler has a resolved integration but a
               description that does not match the template.
        When: CO157 runs.
        Then: A single validation error is returned referencing the handler and
              the expected description.
        """
        integration = create_integration_object()
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-test",
                    "metadata": {
                        "description": "Some other description",
                    },
                },
            ]
        )
        connector.handlers[0].related_integration = integration

        validator = IsHandlerDescriptionTemplatedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        msg = results[0].message
        assert "xsoar-test" in msg
        assert f"XSOAR handler for {integration.name}." in msg
        # The handler.yaml path is surfaced via ValidationResult.path (like CO118),
        # sourced from the reusable HandlerData.file_path property.
        assert results[0].path is not None
        assert results[0].path == connector.handlers[0].file_path
        expected_suffix = (
            Path("components") / "handlers" / "xsoar_test" / "handler.yaml"
        )
        assert str(results[0].path).endswith(str(expected_suffix))

    def test_handler_file_path_property_is_stamped(self):
        """
        Given: A connector parsed from disk.
        When: Accessing handler.file_path on its handlers.
        Then: Each handler resolves its own handler.yaml under the connector,
              proving the connector stamps connector_path onto every handler
              (reusable by all handler-level validators).
        """
        connector = create_connector_object(
            handlers=[{"id": "xsoar-test", "metadata": {"description": "x"}}]
        )

        handler = connector.handlers[0]
        assert handler.connector_path == connector.path
        assert handler.file_path == (
            connector.path
            / "components"
            / "handlers"
            / handler.handler_dir_name
            / "handler.yaml"
        )

    def test_handler_file_path_none_without_connector(self):
        """
        Given: A HandlerData constructed in isolation (no connector).
        When: Accessing file_path.
        Then: It returns None rather than raising.
        """
        from demisto_sdk.commands.content_graph.objects.connector import (
            HandlerData,
        )

        handler = HandlerData(id="lonely", handler_dir_name="lonely")
        assert handler.connector_path is None
        assert handler.file_path is None

    def test_error_per_handler_not_per_connector(self):
        """
        Given: A connector with two XSOAR handlers, both with invalid
               descriptions.
        When: CO157 runs.
        Then: Two validation errors are returned (one per failing handler),
              not a single connector-level error.
        """
        integration = create_integration_object()
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-handler-a",
                    "metadata": {"description": "wrong A"},
                },
                {
                    "id": "xsoar-handler-b",
                    "metadata": {"description": "wrong B"},
                },
            ]
        )
        for handler in connector.handlers:
            handler.related_integration = integration

        validator = IsHandlerDescriptionTemplatedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 2
        handler_ids_in_messages = {
            hid
            for hid in ("xsoar-handler-a", "xsoar-handler-b")
            if any(hid in r.message for r in results)
        }
        assert handler_ids_in_messages == {"xsoar-handler-a", "xsoar-handler-b"}

    def test_mixed_valid_and_invalid_handlers(self):
        """
        Given: A connector with one valid handler description and one invalid.
        When: CO157 runs.
        Then: Only the invalid handler produces an error.
        """
        integration = create_integration_object()
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-good",
                    "metadata": {
                        "description": (f"XSOAR handler for {integration.name}."),
                    },
                },
                {
                    "id": "xsoar-bad",
                    "metadata": {"description": "nope"},
                },
            ]
        )
        for handler in connector.handlers:
            handler.related_integration = integration

        validator = IsHandlerDescriptionTemplatedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "xsoar-bad" in results[0].message
        assert "xsoar-good" not in results[0].message

    def test_non_xsoar_handler_ignored(self):
        """
        Given: A connector with a non-XSOAR handler (module != 'xsoar').
        When: CO157 runs.
        Then: No validation errors - non-XSOAR handlers are not checked.
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "other-handler",
                    "metadata": {
                        "module": "other",
                        "description": "arbitrary description",
                        "ownership": {"team": "other-team"},
                    },
                    "triggering": {"labels": None},
                },
            ]
        )
        assert len(connector.xsoar_handlers) == 0

        validator = IsHandlerDescriptionTemplatedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0

    def test_handler_without_resolved_integration_skipped(self):
        """
        Given: A connector whose XSOAR handler has no resolved
               related_integration.
        When: CO157 runs.
        Then: No error is produced for that handler - the template <name>
              cannot be determined without a resolved integration (CO164
              covers the unresolved-integration case).
        """
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-test",
                    "metadata": {"description": "whatever"},
                },
            ]
        )
        assert connector.handlers[0].related_integration is None

        validator = IsHandlerDescriptionTemplatedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 0


# ============================================================
# CO124 - IsValidGroupedConnectorAuthValidator
# ============================================================


_OMIT = object()


def _profile_with_mapping(profile_id: str, mapping_value):
    """Build a profile block whose metadata.xsoar.interpolation_mapping
    is exactly ``mapping_value``. Pass ``_OMIT`` to omit the key entirely.
    """
    profile: dict = {
        "id": profile_id,
        "type": "plain",
        "title": "T",
        "configurations": [
            {"fields": [{"id": "u", "field_type": "input"}]}
        ],
    }
    if mapping_value is _OMIT:
        profile["metadata"] = {"xsoar": {}}
    else:
        profile["metadata"] = {
            "xsoar": {"interpolation_mapping": mapping_value}
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
            connection_data={
                "profiles": [_profile_with_mapping("plain.x", _OMIT)]
            }
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
                    _profile_with_mapping(
                        "plain.x", "username:credentials.identifier"
                    )
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
            connection_data={
                "profiles": [_profile_with_mapping("plain.x", _OMIT)]
            },
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
            connection_data={
                "profiles": [_profile_with_mapping("plain.x", "")]
            },
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
            connection_data={
                "profiles": [_profile_with_mapping("plain.x", "   ")]
            },
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
            connection_data={
                "profiles": [_profile_with_mapping("plain.x", _OMIT)]
            },
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
                "profiles": [
                    _grouped_profile("plain.myint", ["username", "password"])
                ]
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
    hidden: bool = True,
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
        "options": {
            "create_modifiers": {"hidden": hidden},
            "edit_modifiers": {"hidden": hidden},
        },
    }


def _canonical_engine_triplet(integration_id: str = "MyInt") -> list:
    """The three engine fields in the order they appear on disk."""
    return [
        _canonical_engine_mode_field(),
        _canonical_engine_field(
            "engine", integration_id, "engine", hidden=True
        ),
        _canonical_engine_field(
            "engineGroup", integration_id, "engine-group", hidden=True
        ),
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
    D same-FieldGroup, E field_type, F config_type, G/H/I dynamic_values,
    J hidden-by-default.
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
        triplet[1]["metadata"]["dynamic_values"]["params"]["integrationID"] = (
            "OtherInt"
        )
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
        triplet[2]["metadata"]["dynamic_values"]["params"]["dynamicField"] = (
            "engine"
        )
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

    def test_engine_hidden_false_fails(self):
        """J: hidden must be true on both create and edit modifiers."""
        triplet = _canonical_engine_triplet("MyInt")
        triplet[1]["options"]["create_modifiers"]["hidden"] = False
        triplet[1]["options"]["edit_modifiers"]["hidden"] = False
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
        assert "create_modifiers.hidden must be true" in msg
        assert "edit_modifiers.hidden must be true" in msg

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
