from demisto_sdk.commands.validate.tests.test_tools import (
    create_xdrc_template_object,
)
from demisto_sdk.commands.validate.validators.XT_validators.XT101_standardized_fields import (
    XDRCTemplateStandardizedFieldsValidator,
)


class TestXDRCTemplateStandardizedFieldsValidator:
    def test_valid_xdrc_template_with_standard_fields(self):
        """
        Given
        an XDRC template that contains only the standard "id" field (no deprecated field).
        When
        - Calling XDRCTemplateStandardizedFieldsValidator.obtain_invalid_content_items.
        Then
        - No validation errors are returned (length 0).
        """
        content_item = create_xdrc_template_object()
        # Ensure only the standard field exists
        data = content_item.data
        data.pop("content_global_id", None)
        data.update(
            {
                "os_type": "windows",
                "profile_type": "endpoint",
                "name": "Test Template",
                "id": "test-template-id",
                "from_xdr_version": "1.0.0",
                "yaml_template": "template content",
            }
        )

        validator = XDRCTemplateStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([content_item])

        assert len(results) == 0

    def test_invalid_xdrc_template_with_old_field_only(self):
        """
        Given
        an XDRC template that contains only the deprecated "content_global_id" (no standard "id").
        When
        - Calling XDRCTemplateStandardizedFieldsValidator.obtain_invalid_content_items.
        Then
        - One validation error is returned with error code XT101.
        """
        content_item = create_xdrc_template_object()
        data = content_item.data
        data.pop("id", None)
        data.update(
            {
                "os_type": "windows",
                "profile_type": "endpoint",
                "name": "Test Template",
                "content_global_id": "old-global-id",
                "from_xdr_version": "1.0.0",
                "yaml_template": "template content",
            }
        )

        validator = XDRCTemplateStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([content_item])

        assert len(results) == 1
        assert results[0].validator.error_code == "XT101"

    def test_valid_xdrc_template_with_both_fields(self):
        """
        Given
        an XDRC template that contains both the deprecated "content_global_id" and standard "id".
        When
        - Calling XDRCTemplateStandardizedFieldsValidator.obtain_invalid_content_items.
        Then
        - No validation errors are returned (backward compatibility is allowed).
        """
        content_item = create_xdrc_template_object()
        data = content_item.data
        data.update(
            {
                "os_type": "windows",
                "profile_type": "endpoint",
                "name": "Test Template",
                "id": "test-template-id",
                "content_global_id": "old-global-id",  # Backward compatibility
                "from_xdr_version": "1.0.0",
                "yaml_template": "template content",
            }
        )

        validator = XDRCTemplateStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([content_item])

        assert len(results) == 0

    def test_valid_xdrc_template_without_old_field(self):
        """
        Given
        an XDRC template that contains the standard "id" and does not contain the deprecated field.
        When
        - Calling XDRCTemplateStandardizedFieldsValidator.obtain_invalid_content_items.
        Then
        - No validation errors are returned.
        """
        content_item = create_xdrc_template_object()
        data = content_item.data
        data.pop("content_global_id", None)
        data.update(
            {
                "os_type": "windows",
                "profile_type": "endpoint",
                "name": "Test Template",
                "id": "test-template-id",
                "from_xdr_version": "1.0.0",
                "yaml_template": "template content",
            }
        )

        validator = XDRCTemplateStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([content_item])

        assert len(results) == 0
