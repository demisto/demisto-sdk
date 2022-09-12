from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import XSIAM_DASHBOARD
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    TextObject
from demisto_sdk.commands.common.tools import generate_xsiam_normalized_name


class XSIAMDashboardImage(TextObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)

    def normalize_file_name(self) -> str:
        return generate_xsiam_normalized_name(self._path.name, XSIAM_DASHBOARD)
