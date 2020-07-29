from demisto_sdk.commands.common.content import SecretIgnore, ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=[".secrets-ignore"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, SecretIgnore)


@pytest.mark.parametrize(argnames="file", argvalues=[".secrets-ignore"])
def test_prefix(datadir, file: str):
    obj = SecretIgnore(datadir[file])
    assert obj._normalized_file_name() == ".secrets-ignore"
