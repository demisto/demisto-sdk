import pytest

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
    content_items.
    - Two valid descriptionץ
    When
    - Calling the IsContainDemistoWordValidator is_valid function.
    Then
    - Should pass.

    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS107_is_description_contains_demisto_word import (
        IsDescriptionContainsDemistoWordValidator,
    )
    content_items = [
        create_integration_object(
            paths=["description"], values=["valid description"]
        )
    ]
    is_valid = IsDescriptionContainsDemistoWordValidator().is_valid(content_items)
    assert len(is_valid) == 0


def test_IsDescriptionContainsDemistoWordValidator_is_invalid():
    """
    Given
    content_items.
    - invalid description that contains the word 'demisto'
    When
    - Calling the IsContainDemistoWordValidator is_valid function.
    Then
    - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
    """
    from demisto_sdk.commands.validate.validators.DS_validators.DS107_is_description_contains_demisto_word import (
        IsDescriptionContainsDemistoWordValidator,
    )
    content_items = [
        create_integration_object(
            paths=["description"], values=["demisto"]
        )
    ]
    is_valid = IsDescriptionContainsDemistoWordValidator().is_valid(content_items)
    assert is_valid[0].message == "Invalid keyword 'demisto' was found in lines: 1. For more information about the description file See: https://xsoar.pan.dev/docs/documentation/integration-description."
