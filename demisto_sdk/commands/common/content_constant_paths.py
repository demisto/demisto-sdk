import sys
import types
from pathlib import Path
from typing import Union

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
        Path(__file__).parent.parent / "lint" / "resources" / "pylint_plugins",
    ]
]

if API_MODULES_SCRIPTS_DIR.exists():
    PYTHONPATH.extend(path.absolute() for path in API_MODULES_SCRIPTS_DIR.iterdir())

else:
    logger.debug(
        "Could not add API modules to 'PYTHONPATH' as the base directory does not exist."
    )

PYTHONPATH_STR = ":".join(str(path) for path in PYTHONPATH)


def reload_module_and_dependents(
    module_name, reload_current=True, visited=set(), module_items=None
):
    """
    Reload the given module and all modules that depend on it, recursively.
    The root module is reloaded first, followed by its dependents.

    :param module_name: The name of the module to reload.
    :param reload_current: Whether to reload the current module.
    :param visited: A set to keep track of visited modules to avoid infinite recursion.
    :param module_items: (Optional) Static list of modules to iterate over.
    """
    logger.debug(f"Visiting {module_name=}")

    if module_name in visited:
        return

    visited.add(module_name)

    if reload_current:
        # Reloading root/current module first.
        module = sys.modules.get(module_name)
        if module is None:
            logger.debug(f"Module {module_name} not found in sys.modules.")
            return

        logger.debug(f"Reloading {module_name}")
        # reload(module)

    if module_items is None:
        module_items = [(name, module) for name, module in sys.modules.items()]
    logger.debug(f"Module items: {module_items=}")

    # Finding modules that import this module.
    dependents = []
    for _module_name, _module in module_items:
        if _module_name not in visited and isinstance(_module, types.ModuleType):
            # Retrieving modules that imports the root module (this module).
            imports_root = False
            for attr_name in dir(_module):
                try:
                    attr = getattr(_module, attr_name)
                    if (
                        isinstance(attr, types.ModuleType)
                        and attr.__name__ == module_name
                    ):
                        imports_root = True
                        break
                except Exception:
                    continue  # Some attributes may cause exceptions on access.
            if imports_root:
                dependents.append(_module_name)
    logger.debug(f"Dependencies found: {dependents}")

    # Recursively reloading dependents.
    for dependent_name in dependents:
        reload_module_and_dependents(
            module_name=dependent_name,
            reload_current=True,
            visited=set(visited),
            module_items=module_items,
        )


def update_content_paths(content_path: Union[str, Path]):
    """
    Updates content paths globally and reloads dependent modules.
    :param content_path: The path to be set as the new CONTENT_PATH and derived paths.
    """

    global CONTENT_PATH
    global ALL_PACKS_DEPENDENCIES_DEFAULT_PATH
    global CONF_PATH
    global DEFAULT_ID_SET_PATH
    global MP_V2_ID_SET_PATH
    global XPANSE_ID_SET_PATH
    global LANDING_PAGE_SECTIONS_PATH
    global NATIVE_IMAGE_PATH
    global COMMON_SERVER_PYTHON_PATH
    global DEMISTO_MOCK_PATH
    global API_MODULES_SCRIPTS_DIR
    global PYTHONPATH
    global PYTHONPATH_STR
    logger.debug(f"Updating content path globally: {content_path}")

    CONTENT_PATH = Path(content_path)
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
            Path(__file__).parent.parent / "lint" / "resources" / "pylint_plugins",
        ]
    ]
    if API_MODULES_SCRIPTS_DIR.exists():
        PYTHONPATH.extend(path.absolute() for path in API_MODULES_SCRIPTS_DIR.iterdir())

    else:
        logger.debug(
            "Could not add API modules to 'PYTHONPATH' as the base directory does not exist."
        )
    PYTHONPATH_STR = ":".join(str(path) for path in PYTHONPATH)

    logger.debug(f"update_content_paths {__name__}=")
