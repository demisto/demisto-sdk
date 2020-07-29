from pathlib import Path
import pytest

from demisto_sdk.commands.common.content import TextObject


@pytest.mark.parametrize(argnames="valid_file", argvalues=["sample.md", "sample.txt"])
def test_valid_yaml_file_path(datadir, valid_file: str):
    obj = TextObject(datadir[valid_file])
    assert obj.to_str() == Path(datadir[valid_file]).read_text()


def test_text_data_dir_path(datadir):
    obj = TextObject(Path(datadir['sample.md']).parent)
    assert obj.to_str() == Path(datadir['sample.md']).read_text()


def test_malformed_text_path(datadir):
    with pytest.raises(BaseException) as excinfo:
        TextObject('Not valid path')

    assert "Unable to find text file in path" in str(excinfo)
