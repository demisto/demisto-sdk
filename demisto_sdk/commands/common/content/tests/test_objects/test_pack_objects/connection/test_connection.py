import pytest
from demisto_sdk.commands.common.content import Connection, ContentObjectFacotry


@pytest.mark.parametrize(argnames="file", argvalues=["canvas-context-sample.yml"])
def test_objects_factory(datadir, file: str):
    # Currently not supported auto-detect
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, Connection)


def test_changelog_prefix(datadir):
    obj = Connection(datadir["canvas-context-sample.yml"])
    assert obj._normalized_file_name() == "canvas-context-sample.yml"
