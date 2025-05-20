from pathlib import Path

from demisto_sdk.commands.common.constants import NATIVE_IMAGE_FILE_NAME, TESTS_DIR
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_content_path

CONTENT_PATH: Path = Path(get_content_path())

ALL_PACKS_DEPENDENCIES_DEFAULT_PATH = CONTENT_PATH / "all_packs_dependencies.json"

CONF_PATH = CONTENT_PATH / TESTS_DIR / "conf.json"

DEFAULT_ID_SET_PATH = CONTENT_PATH / TESTS_DIR / "id_set.json"
MP_V2_ID_SET_PATH = CONTENT_PATH / TESTS_DIR / "id_set_mp_v2.json"
XPANSE_ID_SET_PATH = CONTENT_PATH / TESTS_DIR / "id_set_xpanse.json"
LANDING_PAGE_SECTIONS_PATH = (
    CONTENT_PATH / TESTS_DIR / "Marketplace" / "landingPage_sections.json"
)
NATIVE_IMAGE_PATH = CONTENT_PATH / "Tests" / NATIVE_IMAGE_FILE_NAME

COMMON_SERVER_PYTHON_PATH = (
    CONTENT_PATH / "Packs" / "Base" / "Scripts" / "CommonServerPython"
)
DEMISTO_MOCK_PATH = CONTENT_PATH / TESTS_DIR / "demistomock"
API_MODULES_SCRIPTS_DIR = CONTENT_PATH / "Packs" / "ApiModules" / "Scripts"

PYTHONPATH = [
    path.absolute()
    for path in [
        Path(CONTENT_PATH),
        COMMON_SERVER_PYTHON_PATH,
        DEMISTO_MOCK_PATH,
        Path(__file__).parent.parent / "pre_commit" / "resources" / "pylint_plugins",
    ]
]

if API_MODULES_SCRIPTS_DIR.exists():
    PYTHONPATH.extend(path.absolute() for path in API_MODULES_SCRIPTS_DIR.iterdir())

else:
    logger.debug(
        "Could not add API modules to 'PYTHONPATH' as the base directory does not exist."
    )

PYTHONPATH_STR = ":".join(str(path) for path in PYTHONPATH)
