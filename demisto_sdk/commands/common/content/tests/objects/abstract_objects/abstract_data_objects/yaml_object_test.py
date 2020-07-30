from pathlib import Path

import pytest

from demisto_sdk.commands.common.content.content.objects.abstract_objects import YAMLObject
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_VALID_YAML = TEST_CONTENT_REPO / 'Packs' / 'Sample01' / 'Scripts' / 'script-sample_new.yml'
TEST_NOT_VALID_YAML = path_test_files() / 'malformed.yaml'


class TestValidYAML:
    def test_valid_yaml_file_path(self):
        from ruamel.yaml import YAML
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000
        obj = YAMLObject(TEST_VALID_YAML)
        assert obj.to_dict() == yaml.load(TEST_VALID_YAML.open())

    def test_get_item(self):
        from ruamel.yaml import YAML
        obj = YAMLObject(TEST_VALID_YAML)
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000

        assert obj["fromversion"] == yaml.load(TEST_VALID_YAML.open())["fromversion"]

    @pytest.mark.parametrize(argnames="default_value", argvalues=["test_value", ""])
    def test_get(self, default_value: str):
        from ruamel.yaml import YAML
        obj = YAMLObject(TEST_VALID_YAML)
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000

        if default_value:
            assert obj.get("no such key", default_value) == default_value
        else:
            assert obj["fromversion"] == yaml.load(TEST_VALID_YAML.open())["fromversion"]

    def test_dump(self, datadir):
        from ruamel.yaml import YAML
        from pathlib import Path
        expected_file = TEST_VALID_YAML.parent / f'prefix-{TEST_VALID_YAML.name}'
        obj = YAMLObject(TEST_VALID_YAML, "prefix")
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000
        assert obj.dump()[0] == expected_file
        assert obj.to_dict() == yaml.load(expected_file.open())
        expected_file.unlink()


class TestInValidYAML:
    def test_malformed_yaml_data_file_path(self, datadir):
        obj = YAMLObject(TEST_NOT_VALID_YAML)
        with pytest.raises(BaseException) as excinfo:
            obj.to_dict()
        assert "is not valid yaml file, Full error" in str(excinfo)

    def test_malformed_yaml_path(self, datadir):
        with pytest.raises(BaseException) as excinfo:
            YAMLObject('Not valid path')

        assert "Unable to find yaml/yml file in path Not valid path'" in str(excinfo)
