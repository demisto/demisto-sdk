import json
from pathlib import Path
from requests.structures import CaseInsensitiveDict


def load_default_additional_info_dict() -> CaseInsensitiveDict:
    """ returns a CaseInsensitiveDict"""
    with (Path(__file__).parent / 'default_additional_info.json').open() as f:
        # Case insensitive to catch both `API key` and `API Key`, giving both the same value.
        return CaseInsensitiveDict(json.load(f))
