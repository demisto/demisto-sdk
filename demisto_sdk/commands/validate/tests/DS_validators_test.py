import pytest

from demisto_sdk.commands.common.constants import BETA_INTEGRATION_DISCLAIMER
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
)


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


def test_IsDescriptionContainsDemistoWordValidator_is_valid():
    """
    Given
    - Integration with a valid description.
    When
    - Calling the IsContainDemistoWordValidator is_valid function.
    Then
    - Should pass.

    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS107_is_description_contains_demisto_word import (
        IsDescriptionContainsDemistoWordValidator,
    )

    integration = create_integration_object()
    integration.description_file.file_content_str = "valid description\n"
    is_valid = IsDescriptionContainsDemistoWordValidator().is_valid([integration])
    assert len(is_valid) == 0


def test_IsDescriptionContainsDemistoWordValidator_is_invalid():
    """
    Given
    - Integration with invalid description that contains the word 'demisto'.
    When
    - Calling the IsContainDemistoWordValidator is_valid function.
    Then
    - Make that the right error message is returned.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS107_is_description_contains_demisto_word import (
        IsDescriptionContainsDemistoWordValidator,
    )

    integration = create_integration_object()
    integration.description_file.file_content_str = (
        " demisto.\n demisto \n valid description\ndemisto"
    )
    is_valid = IsDescriptionContainsDemistoWordValidator().is_valid([integration])
    assert (
        is_valid[0].message
        == "Invalid keyword 'demisto' was found in lines: 1, 2, 4. For more information about the description file See: https://xsoar.pan.dev/docs/documentation/integration-description."
    )


@pytest.mark.parametrize(
    "is_beta_integration, description_file_content, result_len",
    [
        (
            False,
            "",
            0,
        ),
        (
            True,
            "",
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
        - Case 2: Should fail.
        - Case 3: Shouldn't fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS101_is_valid_beta_description import (
        IsValidBetaDescriptionValidator,
    )

    integration = create_integration_object()
    integration.is_beta = is_beta_integration
    integration.description_file.file_content_str = description_file_content

    is_valid = IsValidBetaDescriptionValidator().is_valid([integration])
    assert result_len == len(is_valid)


@pytest.mark.parametrize(
    "description_file_content, result_len",
    [
        (
            "",
            0,
        ),
        (
            "### This is a partner Contributed Integration",
            1,
        ),
    ],
)
def test_IsDescriptionContainsContribDetailsValidator_is_valid(
    description_file_content,
    result_len,
):
    """
    Given
    content_items iterables.
            - Case 1: description file without Contrib Details.
            - Case 2: description file with Contrib Details.
    When
    - Calling the IsDescriptionContainsContribDetailsValidator is valid function.
    Then
        - Make sure that the validation is implemented correctly.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS105_is_description_contains_contrib_details import (
        IsDescriptionContainsContribDetailsValidator,
    )

    integration = create_integration_object()
    integration.description_file.file_content_str = description_file_content

    is_valid = IsDescriptionContainsContribDetailsValidator().is_valid([integration])
    assert result_len == len(is_valid)


@pytest.mark.parametrize(
    "is_file_exist, result_len",
    [
        (
            True,
            0,
        ),
        (
            False,
            1,
        ),
    ],
)
def test_IsValidDescriptionNameValidator_is_valid(
    is_file_exist,
    result_len,
):
    """
    Given
    content_items iterables.
            - Case 1: the description file exist.
            - Case 2: the description file not exist.
    When
    - Calling the IsValidDescriptionNameValidator is valid function.
    Then
        - Make sure that the description file exist.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS106_is_valid_description_name import (
        IsValidDescriptionNameValidator,
    )

    integration = create_integration_object()
    integration.description_file.exist = is_file_exist

    is_valid = IsValidDescriptionNameValidator().is_valid([integration])
    assert result_len == len(is_valid)
