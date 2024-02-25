from abc import ABC
from pathlib import Path
from typing import ClassVar

import typer
from more_itertools import split_at
from typing_extensions import Annotated

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

ZERO_DEPTH_FILES = frozenset(
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

DEPTH_ONE_FOLDERS = frozenset(ContentType.folders()) | {
    RELEASE_NOTES_DIR,
    DOC_FILES_DIR,
}

DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES = frozenset(
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


class InvalidPathException(Exception, ABC):
    message: ClassVar[str]


class PathOutsidePacks(InvalidPathException):
    message = "Path is not under Packs"


class PathIsFolder(Exception):
    ...


class PathUnderDeprecatedContent(Exception):
    ...


class InvalidDepthZeroFile(InvalidPathException):
    message = "The file cannot be saved direclty under the pack folder."


class InvalidDepthOneFolder(InvalidPathException):
    message = "The first folder under the pack is not allowed."


class InvalidDepthTwoFile(InvalidPathException):
    message = "The folder containing this file cannot directly contain files. Add another folder under it."


def validate_path(path: Path) -> None:
    logger.debug(f"checking {path=}")
    if path.is_dir():
        raise PathIsFolder

    if PACKS_FOLDER not in path.parts:
        raise PathOutsidePacks  # TODO

    if "DeprecatedContent" in path.parts:
        raise PathUnderDeprecatedContent

    parts_before_packs, parts_after_packs = tuple(
        split_at(path.parts, lambda v: v == PACKS_FOLDER, maxsplit=1)
    )

    parts_after_pack = parts_after_packs[1:]  # everything after Packs/<pack name>
    depth = len(parts_after_pack) - 1

    if depth == 0:  # file is directly under pack
        if path.name not in ZERO_DEPTH_FILES:
            raise InvalidDepthZeroFile
        return

    if (first_level_folder := parts_after_pack[0]) not in DEPTH_ONE_FOLDERS:
        raise InvalidDepthOneFolder

    if depth == 1:  # Packs/some_pack/Scripts/script-foo.yml
        for prefix, folder in (
            ("script", ContentType.SCRIPT),
            ("integration", ContentType.INTEGRATION),
        ):
            if (
                path.name.startswith(prefix)
                and first_level_folder == folder.as_folder
                and (path.suffix in {".md", ".yml"})  # these fail validate-all
            ):
                # old, unified format, e.g. Packs/some_pack/Scripts/script-foo.yml
                logger.warning(
                    "Unified files (while discouraged), are exempt from path validation, skipping them"
                )
                return
    if (
        depth == 2
        and first_level_folder not in DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES
    ):
        # Packs/MyPack/SomeFolderThatShouldntHaveFilesDirectly/<modified file>
        raise InvalidDepthTwoFile


def main(
    path: Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=True)],
    github_action: Annotated[bool, typer.Option(envvar="GITHUB_ACTIONS")] = False,
) -> None:
    try:
        validate_path(path)
        logger.debug(f"[green]{path=} is valid[/green]")

    except PathIsFolder:
        logger.warning(f"{path!s} is a folder, skipping")

    except PathUnderDeprecatedContent:
        logger.warning(f"{path!s} is under the DeprecatedContent folder, skipping")

    except InvalidPathException as e:
        if github_action:
            print(  # noqa: T201
                f"::error file={path},line=1,endLine=1,title=Invalid Path::{e.message}"
            )
        else:
            logger.error(f"Path {path} is invalid: {e.message}")
            raise typer.Exit(1)

    except Exception:
        logger.exception(f"Failed checking path {path}")
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
