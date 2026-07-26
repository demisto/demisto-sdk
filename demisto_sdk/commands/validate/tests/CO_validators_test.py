"""Tests for CO (Connector) validators - CO100-CO106, CO164."""

from pathlib import Path
from types import SimpleNamespace

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
    the template 'XSOAR handler for <name> integration', where <name> is the
    resolved related integration's name. One error is emitted per failing
    handler (not per connector).
    """

    def test_valid_handler_description(self):
        """
        Given: A connector whose XSOAR handler has a resolved integration and a
               description matching 'XSOAR handler for <name> integration'.
        When: CO157 runs.
        Then: No validation errors are returned.
        """
        integration = create_integration_object()
        connector = create_connector_object(
            handlers=[
                {
                    "id": "xsoar-test",
                    "metadata": {
                        "description": (
                            f"XSOAR handler for {integration.name} integration"
                        ),
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
        assert f"XSOAR handler for {integration.name} integration" in msg
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
                        "description": (
                            f"XSOAR handler for {integration.name} integration"
                        ),
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
