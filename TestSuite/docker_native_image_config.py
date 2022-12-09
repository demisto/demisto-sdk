from pathlib import Path
from typing import Optional, Dict
from demisto_sdk.commands.common.handlers import JSON_Handler

json = JSON_Handler()


class DockerNativeImageConfiguration:

    def __init__(self, tmpdir: Path):
        self.tmpdir = tmpdir
        file_name = 'docker_native_image_config.json'
        self._native_image_config_path = tmpdir / file_name
        self.path = str(self._native_image_config_path)

    def write_native_image_config(self, data: Optional[Dict] = None):

        if data:
            with open(self.path, 'w') as file:
                json.dump(data, file)
        else:
            from demisto_sdk.tests.constants_test import NATIVE_IMAGE_TEST_CONFIG_PATH
            from demisto_sdk.commands.common.native_image import load_native_image_config

            with open(self.path, 'w') as file:
                json.dump(load_native_image_config(NATIVE_IMAGE_TEST_CONFIG_PATH), file, indent=4)
