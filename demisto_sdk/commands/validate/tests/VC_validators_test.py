from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
)
from demisto_sdk.commands.validate.validators.VC_validators.VC100_valid_version_config_file import (
    ValidVersionConfigFileValidator,
)


def test_isValidVersionConfigFile():
    my_dict = '{"8.9": {"to": "1.5.0"}, "8.10": {"from": "1.5.1"}}'
    pack = [create_pack_object(version_config=my_dict)]
    pack[0].version_config.file_content = my_dict
    invalid_content_items = (
        ValidVersionConfigFileValidator().obtain_invalid_content_items(pack)
    )
    assert invalid_content_items == []
