from abc import ABC
from pathlib import Path
from typing import ClassVar, List, Sequence

import typer
from more_itertools import split_at
from tqdm import tqdm
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
    set(ContentType.folders()) | set(TESTS_AND_DOC_DIRECTORIES) | {RELEASE_NOTES_DIR}
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

ALLOWED_SUFFIXES = frozenset(
    (
        ".yml",
        ".json",
        ".md",
        ".png",
        ".py",
        ".svg",
        ".txt",
        ".js",
        ".xif",
        ".ps1",
        "",
    )
)
DIRS_ALLOWING_SPACE_IN_FILENAMES = (TEST_PLAYBOOKS_DIR,)
app = typer.Typer()


class InvalidPathException(Exception, ABC):
    message: ClassVar[str]


class SpacesInFileName(InvalidPathException):
    message = "File name contains spaces."


class InvalidDepthZeroFile(InvalidPathException):
    message = "The file cannot be saved directly under the pack folder."


class InvalidDepthOneFolder(InvalidPathException):
    message = "The name of the first level folder under the pack is not allowed."


class InvalidDepthOneFile(InvalidPathException):
    message = "The folder containing this file cannot directly contain files. Add another folder under it."


class InvalidLayoutFileName(InvalidPathException):
    message = "The Layout folder can only contain JSON files, with names starting with `layout-` or `layoutscontainer-`"


class InvalidIntegrationScriptFileName(InvalidPathException):
    message = "This file's name must start with the name of its parent folder."


class InvalidIntegrationScriptFileType(InvalidPathException):
    message = "This file type is not allowed under this folder."


class InvalidIntegrationScriptMarkdownFileName(InvalidPathException):
    message = (
        "This file's name must either be (parent folder)_description.md, or README.md"
    )


class InvalidSuffix(InvalidPathException):
    message = "This file's suffix is not allowed."


class InvalidCommandExampleFile(InvalidPathException):
    message = "This file's name must be command_examples"


class ExemptedPath(Exception, ABC):
    message: ClassVar[str]


class PathOutsidePacks(ExemptedPath):
    message = "Path is not under Packs"


class PathIsFolder(ExemptedPath):
    message = "Folder paths are not validated"


class PathUnderDeprecatedContent(ExemptedPath):
    message = "Paths under DeprecatedContent are not validated."


class PathIsUnified(ExemptedPath):
    message = "Paths of unified content items are not validated."


class PathIsTestOrDocData(ExemptedPath):
    message = "Paths under test_data or doc_files are not validated."


def _validate(path: Path) -> None:
    """Runs the logic and raises exceptions on skipped/errorneous paths"""
    logger.debug(f"checking {path}")
    if path.is_dir():
        raise PathIsFolder
    if PACKS_FOLDER not in path.parts:
        raise PathOutsidePacks

    if "Tests" in path.parts and (path.parts).index("Tests") < (path.parts).index(
        PACKS_FOLDER
    ):  # if Tests comes before Packs, it's not a real content path
        raise PathOutsidePacks

    parts_before_packs, parts_after_packs = tuple(
        split_at(path.parts, lambda v: v == PACKS_FOLDER, maxsplit=1)
    )

    if parts_after_packs[0] in {"DeprecatedContent", "D2"}:  # Pack name
        """
        This set neither does nor should contain all names of deprecated packs.
        D2 is unique with the files it has, so it is explicitly mentioned here.
        Avoid extending this set beyond these values.
        """
        raise PathUnderDeprecatedContent

    if set(path.parts).intersection(TESTS_AND_DOC_DIRECTORIES):
        raise PathIsTestOrDocData

    parts_inside_pack = parts_after_packs[1:]  # everything after Packs/<pack name>
    depth = len(parts_inside_pack) - 1

    if depth == 0:  # file is directly under pack
        if path.name not in ZERO_DEPTH_FILES:
            raise InvalidDepthZeroFile
        return  # following checks assume the depth>0, so we stop here

    if (first_level_folder := parts_inside_pack[0]) not in DEPTH_ONE_FOLDERS:
        raise InvalidDepthOneFolder

    if " " in path.stem and set(parts_after_packs).isdisjoint(
        DIRS_ALLOWING_SPACE_IN_FILENAMES
    ):
        raise SpacesInFileName

    if path.suffix not in ALLOWED_SUFFIXES:
        raise InvalidSuffix

    if depth == 1:  # Packs/myPack/<first level folder>/<the file>
        _exempt_unified_files(path, first_level_folder)  # Raises PathIsUnified

        if first_level_folder not in DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES:
            # Packs/MyPack/SomeFolderThatShouldntHaveFilesDirectly/<file>
            raise InvalidDepthOneFile

        if first_level_folder == LAYOUTS_DIR and not (
            path.stem.startswith(("layout-", "layoutscontainer-"))
            and path.suffix == ".json"
        ):
            raise InvalidLayoutFileName

    if depth == 2 and first_level_folder in {
        ContentType.INTEGRATION.as_folder,
        ContentType.SCRIPT.as_folder,
    }:
        _validate_integration_script_file(path, parts_after_packs)


def _validate_integration_script_file(path: Path, parts_after_packs: Sequence[str]):
    """Only use from _validate"""
    parent = path.parent.name

    if path.suffix == ".png":
        if path.stem != f"{parent}_image":
            raise InvalidIntegrationScriptFileName

    elif path.suffix in {".yml", ".js"}:
        if path.stem != parent:
            raise InvalidIntegrationScriptFileName

    elif path.suffix == ".ps1":
        if path.stem not in {parent, f"{parent}.Tests"}:
            raise InvalidIntegrationScriptFileName

    elif path.suffix == ".py":
        if path.stem not in {
            parent,
            f"{parent}_test",
            "conftest",
            ".vulture_whitelist",
        }:
            raise InvalidIntegrationScriptFileName

    elif path.suffix == ".md":
        if path.stem not in {"README", f"{parent}_description"}:
            raise InvalidIntegrationScriptMarkdownFileName

    elif not path.suffix:
        if path.stem in {"command_examples", ".pylintrc"}:
            return
        if (
            path.stem == "LICENSE"
            and parts_after_packs[0] == "FireEye-Detection-on-Demand"
        ):
            # Decided to exempt this pack only from using LICENSE files.
            return
        if "command" in path.stem and "example" in path.stem:
            # `command example`, `commands examples` and other single/plural, delimiters permutations
            raise InvalidCommandExampleFile
        raise InvalidIntegrationScriptFileName

    elif (
        path.suffix
        not in {  # remaining supported suffixes in integration/script folders
            ".png",
            ".svg",
            ".txt",
        }
    ):
        raise InvalidIntegrationScriptFileType


def _exempt_unified_files(path: Path, first_level_folder: str):
    """Raises PathIsUnified when necessary. Only use from _validate"""
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


def validate(
    path: Path,
    github_action: bool,
    skip_depth_one_file: bool = False,
    skip_depth_one_folder: bool = False,
    skip_depth_zero_file: bool = False,
    skip_integration_script_file_name: bool = False,
    skip_integration_script_file_type: bool = False,
    skip_markdown: bool = False,
    skip_suffix: bool = False,
) -> bool:
    """Validate a path, returning a boolean answer after handling skip/error exceptions"""
    try:
        _validate(path)
        logger.debug(f"[green]{path} is valid[/green]")
        return True

    except InvalidPathException as e:
        for exception_type, skip in {
            # Allows gradual application
            InvalidDepthOneFile: skip_depth_one_file,
            InvalidDepthOneFolder: skip_depth_one_folder,
            InvalidDepthZeroFile: skip_depth_zero_file,
            InvalidIntegrationScriptFileName: skip_integration_script_file_name,
            InvalidIntegrationScriptFileType: skip_integration_script_file_type,
            InvalidIntegrationScriptMarkdownFileName: skip_markdown,
            InvalidSuffix: skip_suffix,
        }.items():
            if isinstance(e, exception_type) and skip:
                logger.warning(f"skipping {path} ({e.message})")
                return True

        if github_action:
            print(  # noqa: T201
                f"::error file={path},line=1,endLine=1,title=Invalid Path::{e.message}"
            )
        else:
            logger.error(f"Invalid {path}: {e.message}")
        return False

    except ExemptedPath as e:
        logger.debug(f"Skipped {path}: {e.message}")
        return True

    except Exception:
        logger.exception(f"Error checking {path}")
        return False


@app.command(name="validate")
def validate_paths(
    paths: Annotated[
        List[Path], typer.Argument(exists=True, file_okay=True, dir_okay=True)
    ],
    github_action: Annotated[bool, typer.Option(envvar="GITHUB_ACTIONS")] = False,
    skip_depth_one_file: bool = False,
    skip_depth_one_folder: bool = False,
    skip_depth_zero_file: bool = False,
    skip_integration_script_file_name: bool = False,
    skip_integration_script_file_type: bool = False,
    skip_markdown: bool = False,
    skip_suffix: bool = False,
) -> None:
    """Validate given paths"""
    if not all(
        (
            validate(
                path,
                github_action,
                skip_depth_one_file=skip_depth_one_file,
                skip_depth_one_folder=skip_depth_one_folder,
                skip_depth_zero_file=skip_depth_zero_file,
                skip_integration_script_file_name=skip_integration_script_file_name,
                skip_integration_script_file_type=skip_integration_script_file_type,
                skip_markdown=skip_markdown,
                skip_suffix=skip_suffix,
            )
            for path in paths
        )
    ):
        raise typer.Exit(1)


@app.command(name="validate-all")
def validate_all(
    content_path: Annotated[Path, typer.Argument(dir_okay=True, file_okay=False)],
    skip_depth_one_file: bool = False,
    skip_depth_one_folder: bool = False,
    skip_depth_zero_file: bool = False,
    skip_integration_script_file_name: bool = False,
    skip_integration_script_file_type: bool = False,
    skip_markdown: bool = False,
    skip_suffix: bool = False,
):
    """
    Used in the SDK CI for testing compatibility with content.
    Skip arguments will be removed in future versions.
    """
    logger.info(f"Content path: {content_path.resolve()}")
    paths = sorted(content_path.rglob("*"))
    invalid = len(
        [
            path
            for path in tqdm(paths)
            if path.is_file()
            and not validate(
                path,
                github_action=False,
                skip_depth_one_file=skip_depth_one_file,
                skip_depth_one_folder=skip_depth_one_folder,
                skip_depth_zero_file=skip_depth_zero_file,
                skip_integration_script_file_name=skip_integration_script_file_name,
                skip_integration_script_file_type=skip_integration_script_file_type,
                skip_markdown=skip_markdown,
                skip_suffix=skip_suffix,
            )
        ]
    )
    valid = (total := len(paths)) - invalid
    logger.info(f"{total=},[green]{valid=}[/green],[red]{invalid=}[/red]")


def main():
    logging_setup()
    app()


if __name__ == "__main__":
    main()
