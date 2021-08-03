from typing import Iterator, List

import pytest
from jsonschema import ValidationError

from demisto_sdk.commands.common.hook_validations.xsoar_config_json import \
    XSOARConfigJsonValidator


def test_schema_file_correct_path():
    """
    Given:
        Run of xsoar_config.json validator.
    When:
        Initiation of the XSOARConfigJsonValidator object.
    Then:
        Validate that the __init__ method finds the schema in the expected path.
    """
    validator = XSOARConfigJsonValidator('./')
    assert 'demisto_sdk/commands/common/schemas/xsoar_config.json' in validator.schema_path


class TestCreateSchemaValidationResultsTable:
    @staticmethod
    def errors_iterator(errors_list: List) -> Iterator[ValidationError]:
        for error in errors_list:
            yield error

    def test_create_schema_validation_results_table_no_errors(self):
        """
        Given:
            No errors were found in the xsoar_config.json file.
        When:
            Validating the file schema.
        Then:
            Validate that no output is provided by the function.
        """
        generator = self.errors_iterator([])
        _, errors_found = XSOARConfigJsonValidator.create_schema_validation_results_table(generator)
        assert not errors_found

    def test_create_schema_validation_results_table_one_error(self):
        """
        Given:
            One error was found in the xsoar_config.json file.
        When:
            Validating the file schema.
        Then:
            Validate that the table has the right data.
        """
        generator = self.errors_iterator([ValidationError('One Error')])
        errors_table, errors_found = XSOARConfigJsonValidator.create_schema_validation_results_table(generator)

        assert errors_found
        assert 'Error Message' in errors_table.field_names

        errors_table_string = errors_table.get_string()
        assert """+---+---------------+
|   | Error Message |
+---+---------------+
| 0 |   One Error   |
+---+---------------+""" == errors_table_string

    def test_create_schema_validation_results_table_multiple_errors(self):
        """
        Given:
            Multiple errors were found in the xsoar_config.json file.
        When:
            Validating the file schema.
        Then:
            Validate that the table has the right data.
        """
        generator = self.errors_iterator([ValidationError('One Error'), ValidationError('Error #2')])
        errors_table, errors_found = XSOARConfigJsonValidator.create_schema_validation_results_table(generator)

        assert errors_found
        assert 'Error Message' in errors_table.field_names

        errors_table_string = errors_table.get_string()
        assert """+---+---------------+
|   | Error Message |
+---+---------------+
| 0 |   One Error   |
| 1 |    Error #2   |
+---+---------------+""" == errors_table_string


class TestSchemaValidation:
    def test_valid_file_content(self):
        """
        Given:
            Valid configuration file.
        When:
            Validating the file schema.
        Then:
            Validates verification returns that the file is valid.
        """
        file_content = {
            "custom_packs": [
                {
                    "id": "id1",
                    "url": "url1"
                }
            ],
            "marketplace_packs": [
                {
                    "id": "id1",
                    "version": "*"
                }
            ],
            "lists": [
                {
                    "name": "List #1",
                    "value": "Value #1"
                }
            ],
            "jobs": [
                {
                    "type": "Unclassified",
                    "name": "name1",
                    "playbookId": "playbook1",
                    "scheduled": True,
                    "recurrent": True,
                    "cronView": True,
                    "cron": "0 10,15 * * *",
                    "startDate": "2021-01-07T15:10:04.000Z",
                    "endingDate": "2021-01-07T15:10:04.000Z",
                    "endingType": "never",
                    "timezoneOffset": -120,
                    "timezone": "Asia/Jerusalem",
                    "shouldTriggerNew": True,
                    "closePrevRun": True
                }
            ]
        }

        validator = XSOARConfigJsonValidator('./')
        # it gets False from failing load the configuration file, which is expected here.
        validator._is_valid = True
        validator.configuration_json = file_content

        is_valid = validator.is_valid_xsoar_config_file()

        assert is_valid

    def test_invalid_file_bad_root_section(self):
        """
        Given:
            Invalid configuration file which has a bad root section.
        When:
            Validating the file schema.
        Then:
            Validates verification returns that the file is invalid.
        """
        file_content = {
            "unexpected_section": [],
            "custom_packs": [
                {
                    "id": "id1",
                    "url": "url1"
                }
            ],
            "marketplace_packs": [
                {
                    "id": "id1",
                    "version": "*"
                }
            ],
            "lists": [
                {
                    "name": "List #1",
                    "value": "Value #1"
                }
            ],
            "jobs": [
                {
                    "type": "Unclassified",
                    "name": "name1",
                    "playbookId": "playbook1",
                    "scheduled": True,
                    "recurrent": True,
                    "cronView": True,
                    "cron": "0 10,15 * * *",
                    "startDate": "2021-01-07T15:10:04.000Z",
                    "endingDate": "2021-01-07T15:10:04.000Z",
                    "endingType": "never",
                    "timezoneOffset": -120,
                    "timezone": "Asia/Jerusalem",
                    "shouldTriggerNew": True,
                    "closePrevRun": True
                }
            ]
        }

        validator = XSOARConfigJsonValidator('./')
        # it gets False from failing load the configuration file, which is expected here.
        validator._is_valid = True
        validator.configuration_json = file_content

        is_valid = validator.is_valid_xsoar_config_file()

        assert not is_valid

    @pytest.mark.parametrize('key1, key2, key3, key4', [
        ('bad', 'id', 'name', 'name'),
        ('id', 'bad', 'name', 'name'),
        ('id', 'id', 'bad', 'name'),
        ('id', 'id', 'name', 'bad'),
    ])
    def test_invalid_file_bad_keys(self, key1, key2, key3, key4):
        """
        Given:
            Invalid configuration file which has a bad key in one of the sections.
        When:
            Validating the file schema.
        Then:
            Validates verification returns that the file is invalid.
        """
        file_content = {
            "custom_packs": [
                {
                    key1: "id1",
                    "url": "url1"
                }
            ],
            "marketplace_packs": [
                {
                    key2: "id1",
                    "version": "*"
                }
            ],
            "lists": [
                {
                    key3: "List #1",
                    "value": "Value #1"
                }
            ],
            "jobs": [
                {
                    "type": "Unclassified",
                    key4: "name1",
                    "playbookId": "playbook1",
                    "scheduled": True,
                    "recurrent": True,
                    "cronView": True,
                    "cron": "0 10,15 * * *",
                    "startDate": "2021-01-07T15:10:04.000Z",
                    "endingDate": "2021-01-07T15:10:04.000Z",
                    "endingType": "never",
                    "timezoneOffset": -120,
                    "timezone": "Asia/Jerusalem",
                    "shouldTriggerNew": True,
                    "closePrevRun": True
                }
            ]
        }

        validator = XSOARConfigJsonValidator('./')
        # it gets False from failing load the configuration file, which is expected here.
        validator._is_valid = True
        validator.configuration_json = file_content

        is_valid = validator.is_valid_xsoar_config_file()

        assert not is_valid
