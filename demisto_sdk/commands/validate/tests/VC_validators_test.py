from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
)
from demisto_sdk.commands.validate.validators.VC_validators.VC100_valid_version_config_file import (
    ValidVersionConfigFileValidator,
)
from demisto_sdk.commands.validate.validators.VC_validators.VC101_valid_version_config_schema import (
    ValidVersionConfigSchema,
)
from demisto_sdk.commands.validate.validators.VC_validators.VC102_valid_version_config_versions import (
    ValidVersionConfigVersions,
)

TEMP_MY_DICT = {"8.9": {"to": "1.5.0"}, "8.10": {"from": "1.5.1"}}


def test_isValidVersionConfigFile():
    pack = [create_pack_object(version_config=TEMP_MY_DICT)]
    invalid_content_items = (
        ValidVersionConfigFileValidator().obtain_invalid_content_items(pack)
    )
    assert invalid_content_items == []


def test_isValidVersionConfigSchemaValid():
    pack = [create_pack_object(version_config=TEMP_MY_DICT)]
    pack[0].version_config.file_content = TEMP_MY_DICT
    invalid_content_items = ValidVersionConfigSchema().obtain_invalid_content_items(
        pack
    )
    assert invalid_content_items == []


def test_isValidVersionConfigVersions():
    pack = [create_pack_object(version_config=TEMP_MY_DICT)]
    pack[0].version_config.file_content = TEMP_MY_DICT
    invalid_content_items = ValidVersionConfigVersions().obtain_invalid_content_items(
        pack
    )
    assert invalid_content_items == []
