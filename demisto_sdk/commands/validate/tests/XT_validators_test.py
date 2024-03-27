from demisto_sdk.commands.validate.tests.test_tools import (
    create_xdrc_template_object,
)
from demisto_sdk.commands.validate.validators.XT_validators.XT100_xdrc_templates_files_naming_validator import (
    XdrcTemplatesFilesNamingValidator,
)


def test_XdrcTemplatesFilesNamingValidator_is_valid():
    """
    Given
        - An XDRC template with an invalid file name.
    When
    - Calling the XdrcTemplatesFilesNamingValidator is valid function.
    Then
        - Make sure the right amount of failures and messages are returned.
    """
    # file_name is xdrc_template, and dir_name is pack_0_xdrc_template, therefore, the content item is not valid
    xdrc_template = create_xdrc_template_object()
    validator = XdrcTemplatesFilesNamingValidator()
    results = validator.is_valid([xdrc_template])
    assert len(results) == 1
    assert (
        results[0].message
        == "Files in the xdrc templates directory must be titled exactly as the pack, e.g. `myPack.yml`"
    )
