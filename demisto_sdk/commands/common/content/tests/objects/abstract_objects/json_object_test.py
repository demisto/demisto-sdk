import pytest

from demisto_sdk.commands.common.constants import (
    INDICATOR_TYPES_DIR,
    IS_CONTENT_PRIVATE_KEY,
    IS_CONTENT_PRIVATE_ONLY_KEY,
    PACKS_DIR,
)
from demisto_sdk.commands.common.content.errors import (
    ContentInitializeError,
    ContentSerializeError,
)
from demisto_sdk.commands.common.content.objects.abstract_objects import JSONObject
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
TEST_VALID_JSON = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / INDICATOR_TYPES_DIR
    / "reputation-sample_new.json"
)
TEST_NOT_VALID_JSON = TEST_DATA / "malformed.json"


json = JSON_Handler()


class TestValidJSON:
    def test_valid_json_file_path(self):
        with open(TEST_VALID_JSON) as f:
            assert JSONObject(TEST_VALID_JSON).to_dict() == json.load(f)

    def test_get_item(self):
        with open(TEST_VALID_JSON) as f:
            assert (
                JSONObject(TEST_VALID_JSON)["fromVersion"]
                == json.load(f)["fromVersion"]
            )

    @pytest.mark.parametrize(argnames="default_value", argvalues=["test_value", ""])
    def test_get(self, default_value: str):
        obj = JSONObject(TEST_VALID_JSON)

        if default_value:
            assert obj.get("no such key", default_value) == default_value
        else:
            with open(TEST_VALID_JSON) as f:
                assert obj["fromVersion"] == json.load(f)["fromVersion"]

    def test_dump(self):
        from pathlib import Path

        expected_file = Path(TEST_VALID_JSON).parent / f"prefix-{TEST_VALID_JSON.name}"
        obj = JSONObject(TEST_VALID_JSON, "prefix")
        assert obj.dump()[0] == expected_file
        with open(expected_file) as f:
            assert obj.to_dict() == json.load(f)
        expected_file.unlink()


class TestInvalidJSON:
    def test_malformed_json_data_file_path(self):
        with pytest.raises(ContentSerializeError):
            JSONObject(TEST_NOT_VALID_JSON).to_dict()

    def test_malformed_json_path(self):
        with pytest.raises(ContentInitializeError):
            JSONObject("Not valid path")


def test_dump_strips_ci_injected_keys_and_copies_other_files_as_is(tmp_path):
    flagged = tmp_path / "flagged.json"
    flagged.write_text(
        json.dumps(
            {
                "id": "a",
                IS_CONTENT_PRIVATE_KEY: True,
                IS_CONTENT_PRIVATE_ONLY_KEY: True,
            }
        )
    )
    plain = tmp_path / "plain.json"
    plain.write_text('{\n  "id":   "b"\n}\n')

    assert json.loads(JSONObject(flagged).dump(tmp_path / "out")[0].read_text()) == {
        "id": "a"
    }
    assert JSONObject(plain).dump(tmp_path / "out")[0].read_text() == plain.read_text()
