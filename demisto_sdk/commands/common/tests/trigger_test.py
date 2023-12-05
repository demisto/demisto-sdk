from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.hook_validations.triggers import TriggersValidator
from TestSuite.test_tools import ChangeCWD


def test_is_valid_file(repo):
    """
    Given: A trigger json
    When: running are_all_fields_exist
    Then: Validate that the trigger is valid
    """
    pack = repo.create_pack("TestPack")
    dummy_trigger = pack.create_trigger(
        "MyTrigger",
        {
            "trigger_id": "trigger_id",
            "playbook_id": "playbook_id",
            "suggestion_reason": "Reason",
            "description": "Description",
            "trigger_name": "trigger_name",
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
        },
    )
    structure_validator = StructureValidator(dummy_trigger.path)
    assert structure_validator.is_valid_scheme()
    with ChangeCWD(repo.path):
        trigger_validator = TriggersValidator(structure_validator)
        assert trigger_validator.is_valid_file()


def test_is_valid_file_complicated_schema(repo):
    """
    Given: A trigger json with nested "AND" AND "OR".
    When: running are_all_fields_exist
    Then: Validate that the trigger is valid
    """
    pack = repo.create_pack("TestPack")
    dummy_trigger = pack.create_trigger(
        "MyTrigger",
        {
            "trigger_id": "trigger_id",
            "playbook_id": "playbook_id",
            "suggestion_reason": "Reason",
            "description": "Description",
            "trigger_name": "trigger_name",
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
        },
    )
    structure_validator = StructureValidator(dummy_trigger.path)
    assert structure_validator.is_valid_scheme()
    with ChangeCWD(repo.path):
        trigger_validator = TriggersValidator(structure_validator)
        assert trigger_validator.is_valid_file()


def test_is_not_valid_file_complicated_schema(repo):
    """
    Given: A trigger json with nested "AND" AND "OR" and missing SEARCH_FIELD that match "test3".
    When: running are_all_fields_exist
    Then: Validate that the trigger is not valid
    """
    pack = repo.create_pack("TestPack")
    dummy_trigger = pack.create_trigger(
        "MyTrigger",
        {
            "trigger_id": "trigger_id",
            "playbook_id": "playbook_id",
            "suggestion_reason": "Reason",
            "description": "Description",
            "trigger_name": "trigger_name",
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
        },
    )
    structure_validator = StructureValidator(dummy_trigger.path)
    assert not structure_validator.is_valid_scheme()
