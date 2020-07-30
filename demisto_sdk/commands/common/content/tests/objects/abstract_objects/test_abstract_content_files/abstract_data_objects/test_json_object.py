from pathlib import Path
import pytest

from demisto_sdk.commands.common.content.content.objects.abstract_objects import JSONObject


class TestValidJSON:
    def test_valid_json_file_path(self, datadir):
        from json import load
        obj = JSONObject(datadir['sample.json'])

        assert obj.to_dict() == load(Path(datadir['sample.json']).open())

    def test_get_item(self, datadir):
        from json import load
        obj = JSONObject(datadir['sample.json'])

        assert obj["demisto-helloworld"] == load(Path(datadir['sample.json']).open())["demisto-helloworld"]

    @pytest.mark.parametrize(argnames="default_value", argvalues=["test_value"])
    def test_get(self, datadir, default_value: str):
        from json import load
        obj = JSONObject(datadir['sample.json'])

        if default_value:
            assert obj.get("no such key", default_value) == default_value
        else:
            assert obj.get("demisto-helloworld") == load(Path(datadir['sample.json']).open())["demisto-helloworld"]

    def test_dump(self, datadir):
        from json import load
        from pathlib import Path
        expected_file = Path(datadir['sample.json']).parent / 'prefix-sample.json'
        obj = JSONObject(datadir['sample.json'], "prefix")
        assert obj.dump()[0] == expected_file
        assert obj.to_dict() == load(expected_file.open())
        expected_file.unlink()


class TestInValidJSON:
    def test_dir_path(self, datadir):
        obj = JSONObject(Path(datadir['sample.json']).parent)
        with pytest.raises(BaseException) as excinfo:
            obj.to_dict()
        assert "is not valid json file, Full error" in str(excinfo)

    def test_malformed_json_data_file_path(self, datadir):
        obj = JSONObject(datadir['malformed_sample.json'])
        with pytest.raises(BaseException) as excinfo:
            obj.to_dict()
        assert "is not valid json file, Full error" in str(excinfo)

    def test_malformed_json_path(self, datadir):
        with pytest.raises(BaseException) as excinfo:
            JSONObject('Not valid path')

        assert "Unable to find json file in path" in str(excinfo)


