from demisto_sdk.commands.common.content import Readme, ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["README.md", "sample_README.md"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, Readme)


@pytest.mark.parametrize(argnames="file", argvalues=["README.md", "sample_README.md"])
def test_prefix(datadir, file: str):
    obj = Readme(datadir[file])
    assert obj._normalized_file_name() == file
