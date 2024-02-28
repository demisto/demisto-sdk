from abc import ABC
from pathlib import Path
from typing import ClassVar, List

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
    TESTS_AND_DOC_DIRECTORIES,
    TRIGGER_DIR,
    WIDGETS_DIR,
    WIZARDS_DIR,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
)
from demisto_sdk.commands.common.logger import logger, logging_setup
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

DEPTH_ONE_FOLDERS = (
    set(ContentType.folders()) | set(TESTS_AND_DOC_DIRECTORIES)
).difference(
    (
        "Packs",
        "BaseContents",
        "BaseNodes",
        "BasePlaybooks",
        "BaseScripts",
        "TestScripts",
        "CommandOrScripts",
    )
)

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
        *TESTS_AND_DOC_DIRECTORIES,
    )
)


class InvalidPathException(Exception, ABC):
    message: ClassVar[str]


class SeparatorsInFileNameError(InvalidPathException):
    message = "file name has a separator (space, hypen, underscore)"


class InvalidDepthZeroFile(InvalidPathException):
    message = "The file cannot be saved direclty under the pack folder."


class DepthOneFolderError(InvalidPathException):
    message = "The first folder under the pack is not allowed."


class DepthOneFileError(InvalidPathException):
    message = "The folder containing this file cannot directly contain files. Add another folder under it."


class ExemptedPath(Exception, ABC):
    message: ClassVar[str]


class PathOutsidePacks(ExemptedPath):
    message = "Path is not under Packs"


class PathIsFolder(ExemptedPath):
    message = "Path is to a folder, these are not validated."


class PathUnderDeprecatedContent(ExemptedPath):
    message = "Path under DeprecatedContent, these are not validated."


class PathIsUnified(ExemptedPath):
    message = "Path is of a unified content item, these are not validated."


def _validate(path: Path) -> None:
    """Runs the logic and raises exceptions on skipped/errorneous paths"""
    logger.debug(f"checking {path=}")
    if path.is_dir():
        raise PathIsFolder

    if PACKS_FOLDER not in path.parts:
        raise PathOutsidePacks

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
        raise DepthOneFolderError

    if depth == 1:  # Packs/myPack/Scripts/script-foo.yml
        for prefix, folder in (
            ("script", ContentType.SCRIPT),
            ("integration", ContentType.INTEGRATION),
        ):
            if (
                first_level_folder == folder.as_folder
                and path.name.startswith(f"{prefix}-")
                and (path.suffix in {".md", ".yml"})  # these fail validate-all
            ):
                # old, unified format, e.g. Packs/myPack/Scripts/script-foo.yml
                raise PathIsUnified

        if first_level_folder not in DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES:
            # Packs/MyPack/SomeFolderThatShouldntHaveFilesDirectly/<file>
            raise DepthOneFileError


def validate(path: Path, github_action: bool) -> bool:
    """Validate a path, returning a boolean answer after handling skip/error exceptions"""
    try:
        _validate(path)
        logger.debug(f"{path} is valid")
        return True

    except InvalidPathException as e:
        if github_action:
            print(  # noqa: T201
                f"::error file={path},line=1,endLine=1,title=Invalid Path::{e.message}"
            )
        else:
            logger.debug(f"{path} is invalid: {e.message}")
        return False

    except ExemptedPath as e:
        logger.debug(f"{path} is skipped: {e.message}")
        return True

    except Exception:
        logger.exception(f"Failed checking path {path}")
        return False


def cli(
    paths: Annotated[
        List[Path], typer.Argument(exists=True, file_okay=True, dir_okay=True)
    ],
    github_action: Annotated[bool, typer.Option(envvar="GITHUB_ACTIONS")] = False,
) -> None:
    result = [validate(path, github_action) for path in paths]
    if not all(result):
        raise typer.Exit(1)


def main():
    logging_setup()
    typer.run(cli)


if __name__ == "__main__":
    main()
