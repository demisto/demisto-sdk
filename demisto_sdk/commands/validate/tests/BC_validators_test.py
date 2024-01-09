import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_old_file_pointers,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.BC_validators.BC100_breaking_backwards_subtype import (
    BreakingBackwardsSubtypeValidator,
)


@pytest.mark.parametrize(
    "content_items, old_content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(paths=["script.subtype"], values=["python2"]),
                create_integration_object(),
            ],
            [create_integration_object(), create_integration_object()],
            1,
            [
                "Possible backwards compatibility break, You've changed the Integration subtype from python3 to python2, please undo."
            ],
        ),
        (
            [
                create_integration_object(paths=["script.subtype"], values=["python2"]),
                create_script_object(),
            ],
            [create_integration_object(), create_script_object()],
            1,
            [
                "Possible backwards compatibility break, You've changed the Integration subtype from python3 to python2, please undo."
            ],
        ),
        (
            [
                create_integration_object(paths=["script.subtype"], values=["python2"]),
                create_script_object(paths=["subtype"], values=["python2"]),
            ],
            [create_integration_object(), create_script_object()],
            2,
            [
                "Possible backwards compatibility break, You've changed the Integration subtype from python3 to python2, please undo.",
                "Possible backwards compatibility break, You've changed the Script subtype from python3 to python2, please undo.",
            ],
        ),
        (
            [create_integration_object(), create_script_object()],
            [create_integration_object(), create_script_object()],
            0,
            [],
        ),
    ],
)
def test_BreakingBackwardsSubtypeValidator(
    content_items, old_content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items and old_content_items iterables.
        - Case 1: content_items with 2 integrations where the first one has its subtype altered, and two integration with no changes in old_content_items.
        - Case 2: content_items with 1 integration where the first one has its subtype altered and one script with no subtype altered, and old_content_items with one script and integration with no changes.
        - Case 3: content_items with 1 integration where the first one has its subtype altered and 1 script where that has its subtype altered, and old_content_items with one script and integration with no changes.
        - Case 4: content_items and old_content_items with 1 integration and 1 script both with no changes
    When
    - Calling the BreakingBackwardsSubtypeValidator is valid function.
    Then
        - Make sure the right amount of failures return and that the right message is returned.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 integration.
        - Case 3: Should fail both the integration and the script
        - Case 4: Shouldn't fail any content item.
    """
    create_old_file_pointers(content_items, old_content_items)
    results = BreakingBackwardsSubtypeValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_item, expected_subtype, expected_fix_msg",
    [
        (
            create_integration_object(paths=["script.subtype"], values=["python2"]),
            "python3",
            "Changing subtype back to (python3).",
        ),
        (
            create_script_object(paths=["subtype"], values=["python2"]),
            "python3",
            "Changing subtype back to (python3).",
        ),
    ],
)
def test_BreakingBackwardsSubtypeValidator_fix(
    content_item, expected_subtype, expected_fix_msg
):
    """
    Given
        - content_item.
        - Case 1: an Integration content item where the subtype is different from the subtype of the old_content_item.
        - Case 2: a Script content item where the subtype is different from the subtype of the old_content_item.
    When
    - Calling the BreakingBackwardsSubtypeValidator fix function.
    Then
        - Make sure the the object subtype was changed to match the old_content_item subtype, and that the right fix msg is returned.
    """
    validator = BreakingBackwardsSubtypeValidator()
    validator.old_subtype[content_item.name] = "python3"
    assert validator.fix(content_item).message == expected_fix_msg
    assert content_item.subtype == expected_subtype
