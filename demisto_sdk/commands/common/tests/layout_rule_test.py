from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.hook_validations.layout_rule import LayoutRuleValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from TestSuite.test_tools import ChangeCWD

yaml = YAML_Handler()


def test_are_all_fields_exist(repo):
    """
    Given: A layout rule json
    When: running are_all_fields_exist
    Then: Validate that the layout rule is valid

    """
    pack = repo.create_pack('TestPack')
    dummy_layout_rule = pack.create_layout_rule('MyRule', {
        "rule_id": "test_rule",
        "layout_id": "test_layout_id",
        "description": "This trigger is test",
        "layout_rule_name": "test rule name",
        "alerts_filter": {
            "filter": {
                "AND": [
                    {
                        "SEARCH_FIELD": "alert_name",
                        "SEARCH_TYPE": "CONTAINS",
                        "SEARCH_VALUE": "test"
                    }
                ]
            }
        },
        "fromVersion": "6.0.0",
        "toVersion": "6.1.9"
    })
    structure_validator = StructureValidator(dummy_layout_rule.path)
    with ChangeCWD(repo.path):
        layout_rule_validator = LayoutRuleValidator(structure_validator)
        assert layout_rule_validator.are_all_fields_exist()
