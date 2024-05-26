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
        - Case 1: Two valid description
        - Case 2: One valid empty description.
        - Case 3: One invalid description that contains the word 'demisto'
    When
    - Calling the IsContainDemistoWordValidator is_valid function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Should pass.
        - Case 2: Should pass.
        - Case 2: Should fail.
    """
    from demisto_sdk.commands.validate.validators.DS_validators. DS107_is_descrription_contains_demisto_word import (
        IsDescriptionContainsDemistoWordValidator,
    )
    integration = create_integration_object(
                    description_content="This is a valid description.",
                    pack_info={"name": "test1"},
                )
    integration.description_file
    integration.description_file.file_content = file_content

    is_valid = IsDescriptionContainsDemistoWordValidator().is_valid([integration])
    assert result_len == len(is_valid)
