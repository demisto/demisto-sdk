from pathlib import Path
from typing import Dict, Optional

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.constants import NATIVE_IMAGE_FILE_NAME

json = JSON_Handler()


class DockerNativeImageConfiguration:

    def __init__(self, tmpdir: Path):
        self.tmpdir = tmpdir
        self._native_image_config_path = tmpdir / NATIVE_IMAGE_FILE_NAME
        self.path = str(self._native_image_config_path)

    def write_native_image_config(self, data: Optional[Dict] = None):
        if data:
            with open(self.path, 'w') as file:
                json.dump(data, file)
        else:
            from demisto_sdk.commands.common.native_image import load_native_image_config
            from demisto_sdk.tests.constants_test import NATIVE_IMAGE_TEST_CONFIG_PATH

            with open(self.path, 'w') as file:
                json.dump(load_native_image_config(NATIVE_IMAGE_TEST_CONFIG_PATH), file, indent=4)
