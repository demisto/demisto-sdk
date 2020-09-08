import pytest
from demisto_sdk.commands.common.constants import PACKS_DIR, PLAYBOOKS_DIR
from demisto_sdk.commands.common.content.errors import (ContentInitializeError,
                                                        ContentSerializeError)
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    YAMLObject
from demisto_sdk.commands.common.tools import src_root
from ruamel.yaml import YAML

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_VALID_YAML = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PLAYBOOKS_DIR / 'playbook-sample_new.yml'
TEST_NOT_VALID_YAML = TEST_DATA / 'malformed.yaml'


RUYAML = YAML(typ='rt')
RUYAML.preserve_quotes = True
RUYAML.width = 50000


class TestValidYAML:
    def test_valid_yaml_file_path(self):
        obj = YAMLObject(TEST_VALID_YAML)
        assert obj.to_dict() == RUYAML.load(TEST_VALID_YAML.open())

    def test_get_item(self):
        obj = YAMLObject(TEST_VALID_YAML)

        assert obj["fromversion"] == RUYAML.load(TEST_VALID_YAML.open())["fromversion"]

    @pytest.mark.parametrize(argnames="default_value", argvalues=["test_value", ""])
    def test_get(self, default_value: str):
        obj = YAMLObject(TEST_VALID_YAML)
        if default_value:
            assert obj.get("no such key", default_value) == default_value
        else:
            assert obj["fromversion"] == RUYAML.load(TEST_VALID_YAML.open())["fromversion"]

    def test_dump(self, datadir):
        expected_file = TEST_VALID_YAML.parent / f'prefix-{TEST_VALID_YAML.name}'
        obj = YAMLObject(TEST_VALID_YAML, "prefix")
        assert obj.dump()[0] == expected_file
        assert obj.to_dict() == RUYAML.load(expected_file.open())
        expected_file.unlink()


class TestInvalidYAML:
    def test_malformed_yaml_data_file_path(self, datadir):
        obj = YAMLObject(TEST_NOT_VALID_YAML)
        with pytest.raises(ContentSerializeError):
            obj.to_dict()

    def test_malformed_yaml_path(self, datadir):
        with pytest.raises(ContentInitializeError):
            YAMLObject('Not valid path')
