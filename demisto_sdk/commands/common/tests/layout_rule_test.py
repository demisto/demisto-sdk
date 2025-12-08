from demisto_sdk.commands.common.hook_validations.layout_rule import LayoutRuleValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from TestSuite.test_tools import ChangeCWD


def test_is_valid_file(repo):
    """
    Given: A layout rule json
    When: running are_all_fields_exist
    Then: Validate that the layout rule is valid

    """
    pack = repo.create_pack("TestPack")
    dummy_layout_rule = pack.create_layout_rule(
        "MyRule",
        {
            "rule_id": "test_rule",
            "layout_id": "test_layout_id",
            "description": "This trigger is test",
            "rule_name": "test rule name",
            "alerts_filter": {
                "filter": {
                    "AND": [
                        {
                            "SEARCH_FIELD": "alert_name",
                            "SEARCH_TYPE": "CONTAINS",
                            "SEARCH_VALUE": "test",
                        }
                    ]
                }
            },
            "fromVersion": "6.0.0",
        },
    )
    structure_validator = StructureValidator(dummy_layout_rule.path)
    assert structure_validator.is_valid_scheme()
    with ChangeCWD(repo.path):
        layout_rule_validator = LayoutRuleValidator(structure_validator)
        assert layout_rule_validator.is_valid_file()


def test_is_valid_file_complicated_schema(repo):
    """
    Given: A layout rule json with nested "AND" AND "OR".
    When: running are_all_fields_exist
    Then: Validate that the layout rule is valid

    """
    pack = repo.create_pack("TestPack")
    dummy_layout_rule = pack.create_layout_rule(
        "MyRule",
        {
            "rule_id": "test_rule",
            "layout_id": "test_layout_id",
            "description": "This trigger is test",
            "rule_name": "test rule name",
            "alerts_filter": {
                "filter": {
                    "OR": [
                        {
                            "AND": [
                                {
                                    "OR": [
                                        {
                                            "SEARCH_FIELD": "alert_name",
                                            "SEARCH_TYPE": "EQ",
                                            "SEARCH_VALUE": "test1",
                                        },
                                        {
                                            "SEARCH_FIELD": "alert_name",
                                            "SEARCH_TYPE": "EQ",
                                            "SEARCH_VALUE": "test2",
                                        },
                                    ]
                                },
                                {
                                    "SEARCH_FIELD": "alert_name",
                                    "SEARCH_TYPE": "Contains",
                                    "SEARCH_VALUE": "test3",
                                },
                            ]
                        },
                        {
                            "SEARCH_FIELD": "alert_name1",
                            "SEARCH_TYPE": "EQ",
                            "SEARCH_VALUE": "test4",
                        },
                    ]
                }
            },
            "fromVersion": "6.0.0",
        },
    )
    structure_validator = StructureValidator(dummy_layout_rule.path)
    assert structure_validator.is_valid_scheme()
    with ChangeCWD(repo.path):
        layout_rule_validator = LayoutRuleValidator(structure_validator)
        assert layout_rule_validator.is_valid_file()


def test_is_not_valid_file_complicated_schema(repo):
    """
    Given: A layout rule json with nested "AND" AND "OR" and missing SEARCH_FIELD that match "test1".
    When: running are_all_fields_exist
    Then: Validate that the layout rule is not valid

    """
    pack = repo.create_pack("TestPack")
    dummy_layout_rule = pack.create_layout_rule(
        "MyRule",
        {
            "rule_id": "test_rule",
            "layout_id": "test_layout_id",
            "description": "This trigger is test",
            "rule_name": "test rule name",
            "alerts_filter": {
                "filter": {
                    "OR": [
                        {
                            "AND": [
                                {
                                    "OR": [
                                        {
                                            "SEARCH_TYPE": "EQ",
                                            "SEARCH_VALUE": "test1",
                                        },
                                        {
                                            "SEARCH_FIELD": "alert_name",
                                            "SEARCH_TYPE": "EQ",
                                            "SEARCH_VALUE": "test2",
                                        },
                                    ]
                                },
                                {
                                    "SEARCH_FIELD": "alert_name",
                                    "SEARCH_TYPE": "Contains",
                                    "SEARCH_VALUE": "test3",
                                },
                            ]
                        },
                        {
                            "SEARCH_FIELD": "alert_name1",
                            "SEARCH_TYPE": "EQ",
                            "SEARCH_VALUE": "test4",
                        },
                    ]
                }
            },
            "fromVersion": "6.0.0",
        },
    )
    structure_validator = StructureValidator(dummy_layout_rule.path)
    assert not structure_validator.is_valid_scheme()
