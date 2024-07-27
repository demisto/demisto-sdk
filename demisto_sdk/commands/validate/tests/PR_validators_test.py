from demisto_sdk.commands.common.constants import (
    PARSING_RULE_ID_SUFFIX,
    PARSING_RULE_NAME_SUFFIX,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_parsing_rule_object,
)
from demisto_sdk.commands.validate.validators.PR_validators.PR101_invalid_parsing_rule_suffix_name import (
    ParsingRuleSuffixNameValidator,
)


def test_parsing_rule_with_valid_suffixes():
    """
    Given:
        A parsing rule with valid name and id.
    When:
        Calling Validate.
    Then:
        The validation should not fail.
    """
    parsing_rule = create_parsing_rule_object(
        paths=["id", "name"],
        values=[
            "Example_" + PARSING_RULE_ID_SUFFIX,
            "Example " + PARSING_RULE_NAME_SUFFIX,
        ],
    )
    assert (
        len(
            ParsingRuleSuffixNameValidator().obtain_invalid_content_items(
                [parsing_rule]
            )
        )
        == 0
    )


def test_parsing_rule_with_invalid_id_suffix():
    """
    Given:
        A parsing rule with valid name but invalid id.
    When:
        Calling Validate.
    Then:
        The validation should fail.
    """
    parsing_rule = create_parsing_rule_object(
        paths=["id", "name"], values=["Example_", "Example " + PARSING_RULE_NAME_SUFFIX]
    )
    assert (
        len(
            ParsingRuleSuffixNameValidator().obtain_invalid_content_items(
                [parsing_rule]
            )
        )
        == 1
    )


def test_parsing_rule_with_invalid_name_suffix():
    """
    Given:
        A parsing rule with valid id but invalid name.
    When:
        Calling Validate.
    Then:
        The validation should fail.
    """
    parsing_rule = create_parsing_rule_object(
        paths=["id", "name"],
        values=["Example_" + PARSING_RULE_ID_SUFFIX, "Example Parsing"],
    )
    assert (
        len(
            ParsingRuleSuffixNameValidator().obtain_invalid_content_items(
                [parsing_rule]
            )
        )
        == 1
    )
