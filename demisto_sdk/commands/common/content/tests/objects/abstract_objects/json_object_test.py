import pytest

from demisto_sdk.commands.common.constants import (INDICATOR_TYPES_DIR,
                                                   PACKS_DIR)
from demisto_sdk.commands.common.content.errors import (ContentInitializeError,
                                                        ContentSerializeError)
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    JSONObject
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_VALID_JSON = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / INDICATOR_TYPES_DIR / 'reputation-sample_new.json'
TEST_NOT_VALID_JSON = TEST_DATA / 'malformed.json'


class TestValidJSON:
    def test_valid_json_file_path(self):
        from json import load
        obj = JSONObject(TEST_VALID_JSON)

        assert obj.to_dict() == load(TEST_VALID_JSON.open())

    def test_get_item(self):
        from json import load
        obj = JSONObject(TEST_VALID_JSON)

        assert obj["fromVersion"] == load(TEST_VALID_JSON.open())["fromVersion"]

    @pytest.mark.parametrize(argnames="default_value", argvalues=["test_value", ""])
    def test_get(self, default_value: str):
        from json import load
        obj = JSONObject(TEST_VALID_JSON)

        if default_value:
            assert obj.get("no such key", default_value) == default_value
        else:
            assert obj["fromVersion"] == load(TEST_VALID_JSON.open())["fromVersion"]

    def test_dump(self):
        from json import load
        from pathlib import Path
        expected_file = Path(TEST_VALID_JSON).parent / f'prefix-{TEST_VALID_JSON.name}'
        obj = JSONObject(TEST_VALID_JSON, "prefix")
        assert obj.dump()[0] == expected_file
        assert obj.to_dict() == load(expected_file.open())
        expected_file.unlink()


class TestInvalidJSON:
    def test_malformed_json_data_file_path(self):
        obj = JSONObject(TEST_NOT_VALID_JSON)
        with pytest.raises(ContentSerializeError):
            obj.to_dict()

    def test_malformed_json_path(self):
        with pytest.raises(ContentInitializeError):
            JSONObject('Not valid path')
