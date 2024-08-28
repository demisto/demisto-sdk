from pathlib import Path
from typing import Dict, List

import demisto_client

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger

XSOAR_CONFIG_FILE_JSON = "xsoar_config.json"
MARKETPLACE_PACKS_SECTION = "marketplace_packs"
CUSTOM_PACKS_SECTION = "custom_packs"


class XSOARConfigFileUpdater:
    """
    XSOARConfigFileUpdater is a class that's designed to update and edit the XSOAR Config File.

    Attributes:
        pack_id (str): The Pack ID to add to XSOAR Configuration File
        pack_data (str): The Pack Data to add to XSOAR Configuration File -
        Pack URL for Custom Pack and Pack Version for OOTB Pack
        add_marketplace_pack: (bool) Add the Pack to the MarketPlace Packs section in the Configuration File
        add_custom_pack (bool): Add the Pack to the Custom Packs section in the Configuration File
        add_all_marketplace_packs (bool): Add all the installed MarketPlace Packs to the XSOAR Configuration File
        file_path (str): XSOAR Configuration File path, the default value is in the repo level
    """

    def __init__(
        self,
        pack_id: str,
        pack_data: str,
        add_marketplace_pack: bool = False,
        add_custom_pack: bool = False,
        add_all_marketplace_packs: bool = False,
        insecure: bool = False,
        file_path: str = XSOAR_CONFIG_FILE_JSON,
        **kwargs,
    ):
        self.pack_id = pack_id
        self.pack_data = pack_data
        self.add_marketplace_pack = add_marketplace_pack
        self.add_custom_pack = add_custom_pack
        self.add_all_marketplace_packs = add_all_marketplace_packs
        self.insecure = insecure
        self.file_path = file_path
        self.client = None

    def update(self) -> int:
        """
        Update the Configuration File according the usr input.
        :return: The exit code
        """
        exit_code: int = self.update_config_file_manager()
        return exit_code

    def update_config_file_manager(self) -> int:
        """
        Manages all XSOAR Configuration File command flows
        :return The exit code of each flow
        """
        if not self.verify_flags():
            return 1
        elif self.add_all_marketplace_packs:
            self.add_all_installed_packs_to_config_file()
        elif self.add_marketplace_pack:
            self.update_marketplace_pack()
        elif self.add_custom_pack:
            self.update_custom_pack()
        return 0

    def verify_flags(self) -> bool:
        """
        Verifies that the flags configuration given by the user is correct
        :return: The verification result
        """
        is_valid_pack_structure = True

        if self.add_marketplace_pack or self.add_custom_pack:
            if not self.pack_id:
                is_valid_pack_structure = False
                logger.info("<red>Error: Missing option '-pi' / '--pack-id'.</red>")
            if not self.pack_data:
                is_valid_pack_structure = False
                logger.info("<red>Error: Missing option '-pd' / '--pack-data'.</red>")
        return is_valid_pack_structure

    def add_all_installed_packs_to_config_file(self):
        """
        Update the MarketPlace Packs Section in the Configuration File with all the installed packs on the machine.
        """
        marketplace_packs = self.get_installed_packs()
        self.update_xsoar_config_data(
            section_name=MARKETPLACE_PACKS_SECTION, data_to_update=marketplace_packs
        )

    def get_installed_packs(self) -> List[Dict[str, str]]:
        """
        Gets the current installed packs on the machine.
        """
        client = demisto_client.configure(verify_ssl=self.insecure)
        res = client.generic_request("/contentpacks/metadata/installed", "GET")
        installed_packs_data = eval(res[0])

        installed_packs = [
            {"id": pack["id"], "version": pack["currentVersion"]}
            for pack in installed_packs_data
        ]
        return installed_packs

    def update_marketplace_pack(self):
        """
        Add / Update the MarketPlace Packs Section in the Configuration File with the new pack data.
        """
        new_pack = {"id": self.pack_id, "version": self.pack_data}
        self.update_xsoar_config_data(
            section_name=MARKETPLACE_PACKS_SECTION, data_to_update=new_pack
        )

    def update_custom_pack(self):
        """
        Add / Update the Custom Packs Section in the Configuration File with the new pack data.
        """
        new_pack = {"id": self.pack_id, "url": self.pack_data}
        self.update_xsoar_config_data(
            section_name=CUSTOM_PACKS_SECTION, data_to_update=new_pack
        )

    def update_xsoar_config_data(self, section_name, data_to_update):
        """
        Add / Update the Configuration File according to the section and data that provided.
        """
        config_file_info = self.get_xsoar_config_data()
        if config_file_info.get(section_name):
            if isinstance(data_to_update, list):
                config_file_info[section_name].extend(data_to_update)
            if isinstance(data_to_update, dict):
                config_file_info[section_name].append(data_to_update)
        else:
            config_file_info[section_name] = (
                [data_to_update] if isinstance(data_to_update, dict) else data_to_update
            )
        self.set_xsoar_config_data(config_file_info=config_file_info)

    def get_xsoar_config_data(self):
        config_file_info = {}
        if Path(self.file_path).exists():
            with open(self.file_path) as config_file:
                try:
                    config_file_info = json.load(config_file)
                except json.JSONDecodeError:  # In case that the file exits but empty
                    pass
        return config_file_info

    def set_xsoar_config_data(self, config_file_info):
        with open(self.file_path, "w") as config_file:
            json.dump(config_file_info, config_file, indent=4)
