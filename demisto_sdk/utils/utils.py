from configparser import ConfigParser, MissingSectionHeaderError
from pathlib import Path
from typing import Union

from demisto_sdk.commands.common.constants import DEMISTO_SDK_CONFIG_FILE
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import (
    YAMLContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import (
    YAMLContentUnifiedObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import string_to_bool

ContentEntity = Union[YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject]


def get_containing_pack(content_entity: ContentEntity) -> Pack:
    """Get pack object that contains the content entity.

    Args:
        content_entity: Content entity object.

    Returns:
        Pack: Pack object that contains the content entity.
    """
    pack_path = content_entity.path
    while pack_path.parent.name.casefold() != "packs":
        pack_path = pack_path.parent
    return Pack(pack_path)


def update_command_args_from_config_file(command, args):
    config_file_path = DEMISTO_SDK_CONFIG_FILE
    if Path(config_file_path).is_file():
        try:
            config = ConfigParser(allow_no_value=True)
            config.read(config_file_path)
            config_sections = {
                section: dict(config[section]) for section in config.sections()
            }
            logger.info(
                f"<yellow>{config_file_path} sections={config_sections}</yellow>"
            )
            if command in config.sections():
                for key in config[command]:
                    value = config[command][key]
                    try:
                        boolean_value = string_to_bool(value)
                    except ValueError:
                        boolean_value = None

                    if boolean_value is True:
                        args[key] = True
                    elif boolean_value is False:
                        args[key] = False
                    else:
                        args[key] = value
        except MissingSectionHeaderError:
            pass
