from pathlib import Path

from requests.structures import CaseInsensitiveDict

from demisto_sdk.commands.common.tools import get_json


def load_default_additional_info_dict() -> CaseInsensitiveDict:
    return CaseInsensitiveDict(
        get_json(Path(__file__).absolute().parent / "default_additional_info.json")
    )
