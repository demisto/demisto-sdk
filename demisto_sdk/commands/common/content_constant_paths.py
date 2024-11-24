from pathlib import Path
from typing import Union

from demisto_sdk.commands.common.constants import NATIVE_IMAGE_FILE_NAME, TESTS_DIR
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_content_path


class ContentPaths:
    # Class-level variables (shared across all instances)
    CONTENT_PATH: Path = Path(get_content_path())
    ALL_PACKS_DEPENDENCIES_DEFAULT_PATH: Path = (
        CONTENT_PATH / "all_packs_dependencies.json"
    )
    CONF_PATH: Path = CONTENT_PATH / TESTS_DIR / "conf.json"
    DEFAULT_ID_SET_PATH: Path = CONTENT_PATH / TESTS_DIR / "id_set.json"
    MP_V2_ID_SET_PATH: Path = CONTENT_PATH / TESTS_DIR / "id_set_mp_v2.json"
    XPANSE_ID_SET_PATH: Path = CONTENT_PATH / TESTS_DIR / "id_set_xpanse.json"
    LANDING_PAGE_SECTIONS_PATH: Path = (
        CONTENT_PATH / TESTS_DIR / "Marketplace" / "landingPage_sections.json"
    )
    NATIVE_IMAGE_PATH: Path = CONTENT_PATH / TESTS_DIR / NATIVE_IMAGE_FILE_NAME
    COMMON_SERVER_PYTHON_PATH: Path = (
        CONTENT_PATH / "Packs" / "Base" / "Scripts" / "CommonServerPython"
    )
    DEMISTO_MOCK_PATH: Path = CONTENT_PATH / TESTS_DIR / "demistomock"
    API_MODULES_SCRIPTS_DIR: Path = CONTENT_PATH / "Packs" / "ApiModules" / "Scripts"
    PYTHONPATH = [
        path.absolute()
        for path in [
            CONTENT_PATH,
            COMMON_SERVER_PYTHON_PATH,
            DEMISTO_MOCK_PATH,
            Path(__file__).parent.parent / "lint" / "resources" / "pylint_plugins",
        ]
    ]
    PYTHONPATH_STR = ":".join(str(path) for path in PYTHONPATH)

    @classmethod
    def update_content_path(cls, content_path: Union[str, Path]) -> None:
        """
        Updates the class-level content path and derived paths.

        Args:
            content_path (Union[str, Path]): The new content path to set.
        """
        logger.info(f"Updating content_path globally: {content_path}")

        cls.CONTENT_PATH = Path(content_path)
        logger.info(f"CONTENT_PATH Type: {type(cls.CONTENT_PATH)}")
        cls.ALL_PACKS_DEPENDENCIES_DEFAULT_PATH = (
            cls.CONTENT_PATH / "all_packs_dependencies.json"
        )
        cls.CONF_PATH = cls.CONTENT_PATH / TESTS_DIR / "conf.json"
        cls.DEFAULT_ID_SET_PATH = cls.CONTENT_PATH / TESTS_DIR / "id_set.json"
        cls.MP_V2_ID_SET_PATH = cls.CONTENT_PATH / TESTS_DIR / "id_set_mp_v2.json"
        cls.XPANSE_ID_SET_PATH = cls.CONTENT_PATH / TESTS_DIR / "id_set_xpanse.json"
        cls.LANDING_PAGE_SECTIONS_PATH = (
            cls.CONTENT_PATH / TESTS_DIR / "Marketplace" / "landingPage_sections.json"
        )
        cls.NATIVE_IMAGE_PATH = cls.CONTENT_PATH / TESTS_DIR / NATIVE_IMAGE_FILE_NAME
        cls.COMMON_SERVER_PYTHON_PATH = (
            cls.CONTENT_PATH / "Packs" / "Base" / "Scripts" / "CommonServerPython"
        )
        cls.DEMISTO_MOCK_PATH = cls.CONTENT_PATH / TESTS_DIR / "demistomock"
        cls.API_MODULES_SCRIPTS_DIR = (
            cls.CONTENT_PATH / "Packs" / "ApiModules" / "Scripts"
        )

        cls.PYTHONPATH = [
            path.absolute()
            for path in [
                cls.CONTENT_PATH,
                cls.COMMON_SERVER_PYTHON_PATH,
                cls.DEMISTO_MOCK_PATH,
                Path(__file__).parent.parent / "lint" / "resources" / "pylint_plugins",
            ]
        ]

        if cls.API_MODULES_SCRIPTS_DIR.exists():
            cls.PYTHONPATH.extend(
                path.absolute() for path in cls.API_MODULES_SCRIPTS_DIR.iterdir()
            )
        else:
            logger.debug(
                "Could not add API modules to 'PYTHONPATH' as the base directory does not exist."
            )

        cls.PYTHONPATH_STR = ":".join(str(path) for path in cls.PYTHONPATH)
