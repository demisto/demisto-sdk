from pathlib import Path

import pytest

from demisto_sdk.commands.common.content import YAMLObject


class TestValidYAML:
    @pytest.mark.parametrize(argnames="valid_file", argvalues=["sample.yaml", "sample.yml"])
    def test_valid_yaml_file_path(self, datadir, valid_file: str):
        from ruamel.yaml import YAML
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000
        obj = YAMLObject(datadir[valid_file])
        assert obj.to_dict() == yaml.load(Path(datadir[valid_file]).open())

    def test_get_item(self, datadir):
        from ruamel.yaml import YAML
        obj = YAMLObject(datadir['sample.yaml'])
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000

        assert obj["demisto-helloworld"] == yaml.load(Path(datadir['sample.yaml']).open())["demisto-helloworld"]

    @pytest.mark.parametrize(argnames="default_value", argvalues=["test_value"])
    def test_get(self, datadir, default_value: str):
        from ruamel.yaml import YAML
        obj = YAMLObject(datadir['sample.yaml'])
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000

        if default_value:
            assert obj.get("no such key", default_value) == default_value
        else:
            assert obj.get("demisto-helloworld") == yaml.load(Path(datadir['sample.yaml']).open())["demisto-helloworld"]

    def test_dump(self, datadir):
        from ruamel.yaml import YAML
        from pathlib import Path
        expected_file = Path(datadir['sample.yaml']).parent / 'prefix-sample.yaml'
        obj = YAMLObject(datadir['sample.yaml'], "prefix")
        yaml = YAML(typ='rt')
        yaml.preserve_quotes = True
        yaml.width = 50000
        assert obj.dump()[0] == expected_file
        assert obj.to_dict() == yaml.load(expected_file.open())
        expected_file.unlink()


class TestInValidYAML:
    def test_dir_path(self, datadir):
        obj = YAMLObject(Path(datadir['sample.yaml']).parent)
        with pytest.raises(BaseException) as excinfo:
            obj.to_dict()
        assert "is not valid yaml file, Full error" in str(excinfo)

    def test_malformed_yaml_data_file_path(self, datadir):
        obj = YAMLObject(datadir['malformed_sample.yaml'])
        with pytest.raises(BaseException) as excinfo:
            obj.to_dict()
        assert "is not valid yaml file, Full error" in str(excinfo)

    def test_malformed_yaml_path(self, datadir):
        with pytest.raises(BaseException) as excinfo:
            YAMLObject('Not valid path')

        assert "Unable to find yaml/yml file in path Not valid path'" in str(excinfo)
