from typing import Union

from wcmatch.pathlib import Path

from ...abstract_objects.abstract_files.json_object import JSONObject


class ContentDescriptor(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
