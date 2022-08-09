from demisto_sdk.commands.common.tools import get_content_path
from pathlib import Path

CONTENT_PATH = Path(get_content_path())

ALL_PACKS_DEPENDENCIES_DEFAULT_PATH = CONTENT_PATH / 'all_packs_dependencies.json'

CONF_PATH = CONTENT_PATH / 'Tests' / 'conf.json'

DEFAULT_ID_SET_PATH = CONTENT_PATH / 'Tests' / 'id_set.json'
MP_V2_ID_SET_PATH = CONTENT_PATH / 'Tests' / 'id_set_mp_v2.json'
