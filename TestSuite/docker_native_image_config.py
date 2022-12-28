from pathlib import Path
from typing import Dict, Optional

from demisto_sdk.commands.common.constants import NATIVE_IMAGE_FILE_NAME
from demisto_sdk.commands.common.handlers import JSON_Handler
from TestSuite.test_tools import suite_join_path

json = JSON_Handler()


class DockerNativeImageConfiguration:
    def __init__(self, tmpdir: Path):
        self.tmpdir = tmpdir
        self._native_image_config_path = tmpdir / NATIVE_IMAGE_FILE_NAME
        self.path = str(self._native_image_config_path)

    def write_native_image_config(self, data: Optional[Dict] = None):
        if data:
            with open(self.path, "w") as file:
                json.dump(data, file)
        else:
            default_native_image_config_file_path = (
                "assets/default_docker_native_image_config.json"
            )
            with open(self.path, "w") as file:
                with open(
                    suite_join_path(default_native_image_config_file_path)
                ) as native_image_conf_file:
                    json.dump(json.load(native_image_conf_file), file)
