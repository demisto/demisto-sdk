"""Tests for CO (Connector) validators - CO100-CO106, CO164."""

import copy
from pathlib import Path
from types import SimpleNamespace

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
from demisto_sdk.commands.validate.validators.CO_validators.CO118_is_valid_connection_metadata import (
    IsValidConnectionMetadataValidator,
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
    '<capability_id>_<normalized_integration_id>' and title must equal the
    integration display name."""

    def test_valid_sub_capability_id_and_title(self):
        """
        Given: A grouped connector whose sub-capability id and title are both
               correctly derived.
        When: CO113 runs.
        Then: No validation errors are returned.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "My Integration"
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

    def test_invalid_sub_capability_title(self):
        """
        Given: A grouped connector whose sub-capability title does not match the
               integration display name.
        When: CO113 runs.
        Then: A validation error naming the expected title is returned.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "Wrong Title"
        )

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "My Integration" in results[0].message

    def test_unresolved_integration_is_flagged(self):
        """
        Given: A grouped connector whose sub-capability has a subscribing
               handler, but the handler's referenced integration was NOT
               resolved (related_integration is None, e.g. no content graph).
        When: CO113 runs.
        Then: The title check is reported as unverifiable rather than silently
              skipped - a validation error is returned.
        """
        connector = _grouped_connector_with_sub_capability(
            "fetch-issues_myint", "My Integration"
        )
        # Simulate the no-graph case: the integration never resolved.
        connector.handlers[0].related_integration = None

        validator = IsSubCapabilityIdDerivedValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "could not be verified" in results[0].message

    def test_structural_pattern_failure_without_handler(self):
        """
        Given: A grouped connector with a sub-capability id that does not start
               with '<capability_id>_' and has no subscribing handler.
        When: CO113 runs.
        Then: The structural id pattern is enforced (no silent pass), even
              though the '>=1 handler' rule is owned by CO115.
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
        Given: A sub-capability whose subscribing handler's integration was not
               resolved (related_integration is None).
        When: CO114 runs.
        Then: A validation error is returned (never silently skipped).
        """
        connector = _connector_with_license(["xsiam"], resolve=False)

        validator = IsMatchingLicenseValidator()
        results = validator.obtain_invalid_content_items([connector])

        assert len(results) == 1
        assert "cannot be verified" in results[0].message


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
# CO177 - NoRemovedCapabilitiesValidator
# ============================================================


def _capabilities_payload(capabilities):
    """Build a capabilities.yaml override dict with the given capability list."""
    return {"capabilities": capabilities}


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
