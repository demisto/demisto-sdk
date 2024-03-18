from configparser import ConfigParser, MissingSectionHeaderError
from pathlib import Path
from typing import Union

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


def check_configuration_file(command, args):
    config_file_path = ".demisto-sdk-conf"
    true_synonyms = ["true", "True", "t", "1"]
    if Path(config_file_path).is_file():
        try:
            config = ConfigParser(allow_no_value=True)
            config.read(config_file_path)
            config_sections = {
                section: dict(config[section]) for section in config.sections()
            }
            logger.info(
                f"[yellow].demisto-sdk-conf sections={config_sections}[/yellow]"
            )
            if command in config.sections():
                for key in config[command]:
                    if key in args:
                        # if the key exists in the args we will run it over if it is either:
                        # a - a flag currently not set and is defined in the conf file
                        # b - not a flag but an arg that is currently None and there is a value for it in the conf file
                        if args[key] is False and config[command][key] in true_synonyms:
                            args[key] = True

                        elif args[key] is None and config[command][key] is not None:
                            args[key] = config[command][key]

                    # if the key does not exist in the current args, add it
                    else:
                        if config[command][key] in true_synonyms:
                            args[key] = True

                        else:
                            args[key] = config[command][key]

        except MissingSectionHeaderError:
            pass
