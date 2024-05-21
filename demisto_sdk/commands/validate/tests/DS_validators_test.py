import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
)
from demisto_sdk.commands.common.constants import BETA_INTEGRATION_DISCLAIMER


@pytest.mark.parametrize(
    "is_beta_integration, description_file_exist, result_len",
    [
        (
            False,
            False,
            0,
        ),
        (
            False,
            True,
            0,
        ),
        (
            True,
            False,
            1,
        ),
        (
            True,
            True,
            0,
        ),
    ],
)
def test_DescriptionMissingInBetaIntegrationValidator_is_valid(
    is_beta_integration,
    description_file_exist,
    result_len,
):
    """
    Given
    content_items iterables.
            - Case 1: Not a beta integration, and no description file.
            - Case 2: Not a beta integration, with a description file.
            - Case 3: A beta integration, and no description file.
            - Case 4: A beta integration, with a description file.
    When
    - Calling the DescriptionMissingInBetaIntegrationValidator is valid function.
    Then
        - Make sure that the validation is implemented correctly for beta integrations.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail.
        - Case 4: Shouldn't fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS100_description_missing_in_beta_integration import (
        DescriptionMissingInBetaIntegrationValidator,
    )

    integration = create_integration_object()
    integration.is_beta = is_beta_integration
    integration.description_file.exist = description_file_exist

    is_valid = DescriptionMissingInBetaIntegrationValidator().is_valid([integration])
    assert result_len == len(is_valid)


@pytest.mark.parametrize(
    "is_beta_integration, description_file_content, result_len",
    [
        (
            False,
            '',
            0,
        ),
        (
            True,
            '',
            1,
        ),
        (
            True,
            BETA_INTEGRATION_DISCLAIMER,
            0,
        ),
    ],
)
def test_IsValidBetaDescriptionValidator_is_valid(
    is_beta_integration,
    description_file_content,
    result_len,
):
    """
    Given
    content_items iterables.
            - Case 1: Not a beta integration, and no beta disclaimer.
            - Case 3: A beta integration, and no beta disclaimer.
            - Case 4: A beta integration, with a beta disclaimer.
    When
    - Calling the IsValidBetaDescriptionValidator is valid function.
    Then
        - Make sure that the validation is implemented correctly for beta integrations.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 3: Should fail.
        - Case 4: Shouldn't fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS101_is_valid_beta_description import (
        IsValidBetaDescriptionValidator,
    )

    integration = create_integration_object()
    integration.is_beta = is_beta_integration
    integration.description_file.file_content_str = description_file_content

    is_valid = IsValidBetaDescriptionValidator().is_valid([integration])
    assert result_len == len(is_valid)