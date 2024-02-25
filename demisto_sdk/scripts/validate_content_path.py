from pathlib import Path

from more_itertools import split_at

from demisto_sdk.commands.common.constants import (
    AUTHOR_IMAGE_FILE_NAME,
    CLASSIFIERS_DIR,
    CONNECTIONS_DIR,
    CORRELATION_RULES_DIR,
    DASHBOARDS_DIR,
    DOC_FILES_DIR,
    GENERIC_DEFINITIONS_DIR,
    GENERIC_MODULES_DIR,
    GENERIC_TYPES_DIR,
    GIT_IGNORE_FILE_NAME,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    JOBS_DIR,
    LAYOUT_RULES_DIR,
    LAYOUTS_DIR,
    LISTS_DIR,
    MAPPERS_DIR,
    MODELING_RULES_DIR,
    PACKS_CONTRIBUTORS_FILE_NAME,
    PACKS_FOLDER,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME,
    PACKS_README_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME,
    PARSING_RULES_DIR,
    PLAYBOOKS_DIR,
    PRE_PROCESS_RULES_DIR,
    RELEASE_NOTES_DIR,
    REPORTS_DIR,
    TEST_PLAYBOOKS_DIR,
    TRIGGER_DIR,
    WIDGETS_DIR,
    WIZARDS_DIR,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType

ZERO_DEPTH_ALLOWED_FILES = frozenset(
    (
        GIT_IGNORE_FILE_NAME,
        PACKS_PACK_IGNORE_FILE_NAME,
        PACKS_WHITELIST_FILE_NAME,
        AUTHOR_IMAGE_FILE_NAME,
        PACKS_CONTRIBUTORS_FILE_NAME,
        PACKS_README_FILE_NAME,
        PACKS_PACK_META_FILE_NAME,
    )
)

FIRST_DEPTH_ALLOWED_FOLDERS = frozenset(ContentType.folders()) | {
    RELEASE_NOTES_DIR,
    DOC_FILES_DIR,
}

FIRST_LEVEL_FOLDERS_ALLOWED_TO_CONTAIN_FILES = frozenset(
    (
        PLAYBOOKS_DIR,
        TEST_PLAYBOOKS_DIR,
        REPORTS_DIR,
        DASHBOARDS_DIR,
        INCIDENT_FIELDS_DIR,
        INCIDENT_TYPES_DIR,
        INDICATOR_FIELDS_DIR,
        INDICATOR_TYPES_DIR,
        GENERIC_TYPES_DIR,
        GENERIC_MODULES_DIR,
        GENERIC_DEFINITIONS_DIR,
        LAYOUTS_DIR,
        CLASSIFIERS_DIR,
        MAPPERS_DIR,
        CONNECTIONS_DIR,
        RELEASE_NOTES_DIR,
        DOC_FILES_DIR,
        JOBS_DIR,
        PRE_PROCESS_RULES_DIR,
        LISTS_DIR,
        PARSING_RULES_DIR,
        MODELING_RULES_DIR,
        CORRELATION_RULES_DIR,
        XSIAM_DASHBOARDS_DIR,
        XSIAM_REPORTS_DIR,
        TRIGGER_DIR,
        WIDGETS_DIR,
        WIZARDS_DIR,
        LAYOUT_RULES_DIR,
    )
)


def validate_path(path: Path) -> bool:
    logger.debug(f"checking {path=}")
    if path.is_dir():
        logger.debug(f"{path!s} is a folder, skipping")
        return True

    if PACKS_FOLDER not in path.parts:
        return False  # TODO

    _before_packs_dir, after_packs_dir = tuple(
        split_at(path.parts, lambda v: v == PACKS_FOLDER, maxsplit=1)
    )

    parts_after_pack = after_packs_dir[1:]  # everything after Packs/<pack name>
    depth = len(parts_after_pack)

    if depth == 1:  # file is directly under pack
        if path.name not in ZERO_DEPTH_ALLOWED_FILES:
            logger.error(
                f"{path.name} is not a valid file directly under the pack folder."
            )
            return False

    if (first_level_folder := parts_after_pack[0]) not in FIRST_DEPTH_ALLOWED_FOLDERS:
        logger.error(
            f"{first_level_folder} is not a valid first level folder under a pack."
        )
        return False

    if depth == 2:
        for prefix, folder in (
            ("script", ContentType.SCRIPT),
            ("integration", ContentType.INTEGRATION),
        ):
            if (
                path.name.startswith(prefix)
                and first_level_folder == folder.as_folder
                and path.suffix
                in {".md", ".yml"}  # these suffixes fail validate-all as of today
            ):
                # old, unified format, e.g. Packs/some_pack/Scripts/script-foo.yml
                logger.warning(
                    "Unified files (while discouraged), are exempt from path validation, skipping them"
                )
                return True
    if (
        depth == 3
        and first_level_folder not in FIRST_LEVEL_FOLDERS_ALLOWED_TO_CONTAIN_FILES
    ):
        # Packs/MyPack/SomeFolderThatShouldntHaveFilesDirectly/<modified file>
        logger.error(
            f"the {first_level_folder} cannot directly contain files. Add another folder under it."
        )
        return False
    
    raise NotImplementedError
