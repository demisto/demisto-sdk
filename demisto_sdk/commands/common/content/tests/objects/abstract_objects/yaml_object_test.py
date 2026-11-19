import pytest

from demisto_sdk.commands.common.constants import (
    IS_CONTENT_PRIVATE_KEY,
    IS_CONTENT_PRIVATE_ONLY_KEY,
    PACKS_DIR,
    PLAYBOOKS_DIR,
)
from demisto_sdk.commands.common.content.errors import (
    ContentInitializeError,
    ContentSerializeError,
)
from demisto_sdk.commands.common.content.objects.abstract_objects import YAMLObject
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
TEST_VALID_YAML = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / PLAYBOOKS_DIR
    / "playbook-sample_new.yml"
)
TEST_NOT_VALID_YAML = TEST_DATA / "malformed.yaml"

yaml = YAML_Handler(width=50000)


class TestValidYAML:
    def test_valid_yaml_file_path(self):
        obj = YAMLObject(TEST_VALID_YAML)
        assert obj.to_dict() == yaml.load(TEST_VALID_YAML.open())

    def test_get_item(self):
        obj = YAMLObject(TEST_VALID_YAML)

        assert obj["fromversion"] == yaml.load(TEST_VALID_YAML.open())["fromversion"]

    @pytest.mark.parametrize(argnames="default_value", argvalues=["test_value", ""])
    def test_get(self, default_value: str):
        obj = YAMLObject(TEST_VALID_YAML)
        if default_value:
            assert obj.get("no such key", default_value) == default_value
        else:
            assert (
                obj["fromversion"] == yaml.load(TEST_VALID_YAML.open())["fromversion"]
            )

    def test_dump(self, datadir):
        expected_file = TEST_VALID_YAML.parent / f"prefix-{TEST_VALID_YAML.name}"
        obj = YAMLObject(TEST_VALID_YAML, "prefix")
        assert obj.dump()[0] == expected_file
        assert obj.to_dict() == yaml.load(expected_file.open())
        expected_file.unlink()


class TestInvalidYAML:
    def test_malformed_yaml_data_file_path(self, datadir):
        obj = YAMLObject(TEST_NOT_VALID_YAML)
        with pytest.raises(ContentSerializeError):
            obj.to_dict()

    def test_malformed_yaml_path(self, datadir):
        with pytest.raises(ContentInitializeError):
            YAMLObject("Not valid path")


class TestDumpStripsCIInjectedKeys:
    def test_dump_strips_flag_from_unmodified_file(self, tmp_path):
        """
        Given:
            - An unmodified YAML file carrying the CI-injected ``is_content_private`` key.
        When:
            - Dumping the object (which used to be a raw file copy).
        Then:
            - The output has no CI-injected key and keeps every other key.
        """
        source = tmp_path / "src" / "playbook-flagged.yml"
        source.parent.mkdir()
        source.write_text(
            f"id: flagged\n{IS_CONTENT_PRIVATE_KEY}: true\nname: Flagged\n"
        )

        dumped = YAMLObject(source).dump(tmp_path / "out")[0]

        assert IS_CONTENT_PRIVATE_KEY not in dumped.read_text()
        assert yaml.load(dumped.open()) == {"id": "flagged", "name": "Flagged"}
        # The source file is never touched.
        assert IS_CONTENT_PRIVATE_KEY in source.read_text()

    def test_dump_strips_flag_from_modified_file(self, tmp_path):
        """
        Given:
            - A modified YAML object carrying both CI-injected keys.
        When:
            - Dumping the object (the serialize path).
        Then:
            - Neither key is written.
        """
        source = tmp_path / "playbook-flagged.yml"
        source.write_text(
            f"id: flagged\n{IS_CONTENT_PRIVATE_KEY}: true\n{IS_CONTENT_PRIVATE_ONLY_KEY}: true\n"
        )
        obj = YAMLObject(source)
        obj.modified = True

        dumped = obj.dump(tmp_path / "out")[0]

        assert yaml.load(dumped.open()) == {"id": "flagged"}

    def test_dump_of_file_without_flag_is_a_byte_identical_copy(self, tmp_path):
        """
        Given:
            - An unmodified YAML file without the CI-injected keys, with formatting that a re-serialization would change.
        When:
            - Dumping the object.
        Then:
            - The output is a byte-identical copy (the previous behavior is kept).
        """
        source = tmp_path / "src" / "playbook-plain.yml"
        source.parent.mkdir()
        raw = "id:   plain\n# a comment\nname:    'Plain'\n"
        source.write_text(raw)

        dumped = YAMLObject(source).dump(tmp_path / "out")[0]

        assert dumped.read_text() == raw

    def test_flag_name_only_in_a_value_is_still_copied_raw(self, tmp_path):
        """
        Given:
            - A YAML file that mentions the flag name only inside a nested value (not a top level key).
        When:
            - Dumping the object.
        Then:
            - The file is copied as is.
        """
        source = tmp_path / "src" / "playbook-nested.yml"
        source.parent.mkdir()
        raw = f"id:   nested\ndescription: mentions {IS_CONTENT_PRIVATE_KEY} here\n"
        source.write_text(raw)

        dumped = YAMLObject(source).dump(tmp_path / "out")[0]

        assert dumped.read_text() == raw

    def test_malformed_file_with_flag_name_is_copied_raw(self, tmp_path):
        """
        Given:
            - A malformed YAML file that contains the flag name as a substring.
        When:
            - Dumping the object.
        Then:
            - No error is raised and the file is copied byte for byte.
        """
        raw = f"id: [unclosed\n{IS_CONTENT_PRIVATE_KEY}: true\n"
        source = tmp_path / "src" / "playbook-malformed.yml"
        source.parent.mkdir()
        source.write_bytes(raw.encode())

        dumped = YAMLObject(source).dump(tmp_path / "out")[0]

        assert dumped.read_bytes() == raw.encode()
