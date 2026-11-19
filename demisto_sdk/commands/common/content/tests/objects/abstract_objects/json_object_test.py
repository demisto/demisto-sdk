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


class TestDumpStripsCIInjectedKeys:
    def test_dump_strips_flag_from_unmodified_file(self, tmp_path):
        """
        Given:
            - An unmodified JSON file carrying the CI-injected ``is_content_private`` key.
        When:
            - Dumping the object (which used to be a raw file copy).
        Then:
            - The output has no CI-injected key and keeps every other key.
        """
        source = tmp_path / "src" / "classifier-flagged.json"
        source.parent.mkdir()
        source.write_text(json.dumps({"id": "flagged", IS_CONTENT_PRIVATE_KEY: True}))

        dumped = JSONObject(source).dump(tmp_path / "out")[0]

        assert IS_CONTENT_PRIVATE_KEY not in dumped.read_text()
        assert json.loads(dumped.read_text()) == {"id": "flagged"}
        # The source file is never touched.
        assert IS_CONTENT_PRIVATE_KEY in source.read_text()

    def test_dump_strips_pack_flag_from_unmodified_file(self, tmp_path):
        """
        Given:
            - An unmodified JSON file carrying the CI-injected ``is_content_private_only`` key.
        When:
            - Dumping the object.
        Then:
            - The output has no CI-injected key.
        """
        source = tmp_path / "pack_metadata.json"
        source.write_text(json.dumps({"name": "P", IS_CONTENT_PRIVATE_ONLY_KEY: True}))

        dumped = JSONObject(source).dump(tmp_path / "out")[0]

        assert json.loads(dumped.read_text()) == {"name": "P"}

    def test_dump_strips_flag_from_modified_file(self, tmp_path):
        """
        Given:
            - A modified JSON object carrying the CI-injected key.
        When:
            - Dumping the object (the serialize path).
        Then:
            - The key is not written.
        """
        source = tmp_path / "classifier-flagged.json"
        source.write_text(json.dumps({"id": "flagged", IS_CONTENT_PRIVATE_KEY: True}))
        obj = JSONObject(source)
        obj.modified = True

        dumped = obj.dump(tmp_path / "out")[0]

        assert json.loads(dumped.read_text()) == {"id": "flagged"}

    def test_dump_of_file_without_flag_is_a_byte_identical_copy(self, tmp_path):
        """
        Given:
            - An unmodified JSON file without the CI-injected keys, with formatting that a re-serialization would change.
        When:
            - Dumping the object.
        Then:
            - The output is a byte-identical copy (the previous behavior is kept).
        """
        source = tmp_path / "src" / "classifier-plain.json"
        source.parent.mkdir()
        raw = '{\n  "id":   "plain",\n\n  "type": "classification"\n}\n'
        source.write_text(raw)

        dumped = JSONObject(source).dump(tmp_path / "out")[0]

        assert dumped.read_text() == raw

    def test_malformed_file_with_flag_name_is_copied_raw(self, tmp_path):
        """
        Given:
            - A malformed JSON file that contains the flag name as a substring.
        When:
            - Dumping the object.
        Then:
            - No error is raised and the file is copied byte for byte.
        """
        raw = f'{{"id": "a", "{IS_CONTENT_PRIVATE_KEY}": true,'
        source = tmp_path / "src" / "classifier-malformed.json"
        source.parent.mkdir()
        source.write_bytes(raw.encode())

        dumped = JSONObject(source).dump(tmp_path / "out")[0]

        assert dumped.read_bytes() == raw.encode()
