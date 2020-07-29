from demisto_sdk.commands.common.content import DocFile, ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["TIM_-_Process_Domain_Age_With_Whois.png"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, DocFile)


@pytest.mark.parametrize(argnames="file", argvalues=["TIM_-_Process_Domain_Age_With_Whois.png"])
def test_prefix(datadir, file: str):
    obj = DocFile(datadir[file])
    assert obj._normalized_file_name() == "TIM_-_Process_Domain_Age_With_Whois.png"
