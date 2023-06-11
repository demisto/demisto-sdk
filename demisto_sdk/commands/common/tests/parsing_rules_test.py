import pytest

from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.hook_validations.parsing_rule import (
    ParsingRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from TestSuite.test_tools import ChangeCWD

yaml = YAML_Handler()


def mock_handle_error(error_message, error_code, file_path):
    return error_message


@pytest.mark.parametrize(
    "rule_file_name, rule_dict, expected_error, valid",
    [
        (
            "MyRule",
            {"id": "parsing-rule", "name": "Parsing-Rule"},
            "\nThe file name should end with 'ParsingRules.yml'\nThe rule id should end with 'ParsingRule'\nThe rule name should end with 'Parsing Rule'",
            False,
        ),
        (
            "MyRule",
            {"id": "ParsingRule", "name": "Parsing Rule"},
            "\nThe file name should end with 'ParsingRules.yml'",
            False,
        ),
        (
            "MyRuleParsingRules",
            {"id": "parsing-rule", "name": "Parsing Rule"},
            "\nThe rule id should end with 'ParsingRule'",
            False,
        ),
        (
            "MyRuleParsingRules",
            {"id": "ParsingRule", "name": "Parsing-Rule"},
            "\nThe rule name should end with 'Parsing Rule'",
            False,
        ),
        (
            "MyRuleParsingRules",
            {"id": "ParsingRule", "name": "Parsing Rule"},
            "",
            True,
        ),
        (
            "MyRuleParsingRules_1_3",
            {"id": "ParsingRule", "name": "Parsing Rule"},
            "",
            True,
        ),
        (
            "MyRuleParsingRules_1_!@#",
            {"id": "ParsingRule", "name": "Parsing Rule"},
            "\nThe file name should end with 'ParsingRules.yml'",
            False,
        ),
    ],
)
def test_is_suffix_name_valid(
    mocker, repo, rule_file_name, rule_dict, expected_error, valid
):
    """
    Given: A parsing rule with valid/invalid file_name/id/name
        case 1: Wrong file_name id and name.
        case 2: Wrong file_name.
        case 3: Wrong id.
        case 4: Wrong name.
        case 5: Correct file_name id and name.
        case 6: Correct file_name (with version) id and name.
        case 7: Wrong file_name (wrong version).
    When: running is_valid_rule_suffix_name.
    Then: Validate that the parsing rule is valid/invalid and the message (in case of invalid) is as expected.
    """
    pack = repo.create_pack("TestPack")
    dummy_parsing_rule = pack.create_parsing_rule(rule_file_name)
    structure_validator = StructureValidator(dummy_parsing_rule.yml.path)
    dummy_parsing_rule.yml.write_dict(rule_dict)
    error_message = mocker.patch(
        "demisto_sdk.commands.common.hook_validations.parsing_rule.ParsingRuleValidator.handle_error",
        side_effect=mock_handle_error,
    )

    parsing_rule_validator = ParsingRuleValidator(structure_validator)

    with ChangeCWD(repo.path):
        assert parsing_rule_validator.is_valid_rule_suffix_name() == valid
        if not valid:
            assert (
                error_message.call_args[0][0].split("please check the following:")[1]
                == expected_error
            )
