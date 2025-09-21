from demisto_sdk.commands.content_graph.objects import XDRCTemplate
from demisto_sdk.commands.validate.validators.XT_validators.XT101_standardized_fields import (
    XDRCTemplateStandardizedFieldsValidator,
)


class TestXDRCTemplateStandardizedFieldsValidator:
    def test_valid_xdrc_template_with_standard_fields(self):
        """Test that XDRC template with standard 'id' field passes validation."""
        content_item = XDRCTemplate.from_dict(
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
        """Test that XDRC template with only 'content_global_id' fails validation."""
        content_item = XDRCTemplate.from_dict(
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
        """Test that XDRC template with both old and new fields passes validation."""
        content_item = XDRCTemplate.from_dict(
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
        """Test that XDRC template without old field passes validation."""
        content_item = XDRCTemplate.from_dict(
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
