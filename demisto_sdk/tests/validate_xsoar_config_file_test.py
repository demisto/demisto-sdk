from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union

import pytest
from pydantic import ValidationError

from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.scripts.validate_xsoar_config_file import (
    FILE_NAME,
    NotAJSONError,
    _validate,
)


def _create_and_validate(
    file_body: Union[str, dict],
    file_name: str = FILE_NAME,
):
    """
    Generates a json file and calls validate on the created file.
    """
    body_to_write = file_body if isinstance(file_body, str) else json.dumps(file_body)

    with TemporaryDirectory() as dir:
        path = Path(dir, file_name)
        TextFile.write(body_to_write, path)
        _validate(path)


def test_valid():
    """
    Given   a dictionary equivalent to a valid configuration
    When    calling validate
    Then    make sure the validation passes
    """
    _create_and_validate(
        {
            "custom_packs": [{"id": "id1", "url": "url1"}],
            "marketplace_packs": [{"id": "id1", "version": "*"}],
            "lists": [{"name": "List #1", "value": "Value #1"}],
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
                    "closePrevRun": True,
                }
            ],
        }
    )


def test_extra_root_key():
    """
    Given   a dictionary equivalent to json with unexpected root key
    When    calling validate
    Then    make sure a ValidationError is raised
    """
    with pytest.raises(ValidationError) as e:
        _create_and_validate(
            {
                "SURPRISE": [],
                "custom_packs": [],
                "marketplace_packs": [],
                "lists": [],
                "jobs": [],
            }
        )
    assert len(e.value.errors()) == 1
    assert dict((e.value.errors())[0]) == {
        "loc": ("SURPRISE",),
        "msg": "extra fields not permitted",
        "type": "value_error.extra",
    }


@pytest.mark.parametrize("key", ("custom_packs", "marketplace_packs", "lists", "jobs"))
def test_missing_root_key(key: str):
    """
    Given   a dictionary equivalent to json with a missing root key
    When    calling validate
    Then    make sure the correct ValidationError is raised
    """
    config: dict = {
        "custom_packs": [],
        "marketplace_packs": [],
        "lists": [],
        "jobs": [],
    }
    config.pop(key)
    with pytest.raises(ValidationError) as e:
        _create_and_validate(config)
    assert len(e.value.errors()) == 1
    (e.value.errors())[0]["loc"] == (key,)
    (e.value.errors())[0]["msg"] == ("missing key")


@pytest.mark.parametrize(
    "custom_packs_id_key, marketplace_pack_id_key, list_name_key",
    [
        ("bad", "id", "name"),
        ("id", "bad", "name"),
        ("id", "id", "bad"),
    ],
)
def test_invalid_file_bad_keys(
    custom_packs_id_key: str,
    marketplace_pack_id_key: str,
    list_name_key: str,
):
    """
    Given:
        Invalid configuration file which has a bad key in one of the sections.
    When:
        Validating the file schema.
    Then:
        Validates verification returns that the file is invalid.
    """
    with pytest.raises(ValidationError) as e:
        _create_and_validate(
            {
                "custom_packs": [{custom_packs_id_key: "id1", "url": "url1"}],
                "marketplace_packs": [{marketplace_pack_id_key: "id1", "version": "*"}],
                "lists": [{list_name_key: "List #1", "value": "Value #1"}],
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
                        "closePrevRun": True,
                    }
                ],
            }
        )
    assert len(e.value.errors()) == 2
    assert {error["type"] for error in e.value.errors()} == {
        "value_error.missing",
        "value_error.extra",
    }


@pytest.mark.parametrize(
    "file_name", ("xsoar_config", "xsoar_config.yaml", "xsoar_config.yml")
)
def test_invalid_type(file_name: str):
    """
    Given   a file that isn't a json
    When    calling validate
    Then    make sure NotAJSONError is raised
    """
    with pytest.raises(NotAJSONError):
        _create_and_validate("not a json", file_name)
