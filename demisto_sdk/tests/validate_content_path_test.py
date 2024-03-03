from pathlib import Path
from typing import Tuple

import pytest

from demisto_sdk.commands.common.constants import CONTENT_ENTITIES_DIRS, PACKS_FOLDER
from demisto_sdk.scripts.validate_content_path import (
    DEPTH_ONE_FOLDERS,
    DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES,
    ZERO_DEPTH_FILES,
    DepthOneFileError,
    DepthOneFolderError,
    InvalidDepthZeroFile,
    PathIsFolder,
    PathIsUnified,
    PathUnderDeprecatedContent,
    _validate,
)


def test_content_entities_dir_length():
    """
    This test is here so we don't forget to update FOLDERS_ALLOWED_TO_CONTAIN_FILES when adding/removing content types.
    If this test failed, it's likely you modified either CONTENT_ENTITIES_DIRS or FOLDERS_ALLOWED_TO_CONTAIN_FILES.
    Update the test values accordingly.
    """
    assert len(set(DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES)) == 34

    # change this one if you added a content item folder that can't have files directly under it
    assert (
        len(
            DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES.intersection(
                CONTENT_ENTITIES_DIRS
            )
        )
        == 26
    )


folders_not_allowed_to_contain_files = (
    set(CONTENT_ENTITIES_DIRS) | DEPTH_ONE_FOLDERS
).difference(DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES)

DUMMY_PACK_PATH = Path("content", "Packs", "myPack")


@pytest.mark.parametrize("file_name", ZERO_DEPTH_FILES)
def test_depth_zero_pass(file_name: str):
    """
    Given
            A file name which is allowed directly under the pack
    When
            Running validate_path
    Then
            Make sure the validation passes
    """
    _validate(Path(PACKS_FOLDER, "MyPack", file_name))


@pytest.mark.parametrize("file_name", ("foo.py", "bar.md"))
def test_depth_zero_fail(file_name: str):
    """
    Given
            A file name which is NOT allowed directly under the pack
    When
            Running validate_path
    Then
            Make sure the validation raises InvalidDepthZeroFile
    """
    assert file_name not in ZERO_DEPTH_FILES  # sanity
    with pytest.raises(InvalidDepthZeroFile):
        _validate(Path(PACKS_FOLDER, "MyPack", file_name))


def test_first_level_folder_fail():
    """
    Given
            A name of a folder, which is NOT allowed as a first-level folder
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure the validation raises InvalidDepthOneFolder
    """
    assert (folder_name := "folder_name") not in DEPTH_ONE_FOLDERS
    with pytest.raises(DepthOneFolderError):
        _validate(Path(DUMMY_PACK_PATH, folder_name, "file"))
    with pytest.raises(DepthOneFolderError):
        _validate(Path(DUMMY_PACK_PATH, folder_name, "nested", "very nested", "file"))


@pytest.mark.parametrize("folder", DEPTH_ONE_FOLDERS)
def test_depth_one_pass(folder: str):
    """
    Given
            A name of a folder, which IS allowed as a first-level folder
    When
            Running validate_path on a file created indirectly under it
    Then
            Make sure the validation passes (without raising)
    """
    assert folder in DEPTH_ONE_FOLDERS
    _validate(Path(DUMMY_PACK_PATH, folder, "nested", "file"))
    _validate(Path(DUMMY_PACK_PATH, folder, "nested", "nested_deeper", "file"))


@pytest.mark.parametrize("folder", folders_not_allowed_to_contain_files)
def test_depth_one_fail(folder: str):
    """
    Given
            A name of a folder, which may NOT contain files directly
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure InvalidDepthTwoFile is raised
    """
    with pytest.raises(DepthOneFileError):
        _validate(DUMMY_PACK_PATH / folder / "file")


@pytest.mark.parametrize(
    "path",
    (
        pytest.param(
            Path("Packs/myPack/Scripts/script-foo.yml"),
            id="Unified script (yml)",
        ),
        pytest.param(
            Path("Packs/myPack/Scripts/script-foo.md"),
            id="Unified script (md)",
        ),
        pytest.param(
            Path("Packs/myPack/Integrations/integration-foo.yml"),
            id="Unified integration (yml)",
        ),
        pytest.param(
            Path("Packs/myPack/Integrations/integration-foo.md"),
            id="Unified integration (md)",
        ),
    ),
)
def test_unified_conten(path: Path):
    """
    Given
            A file under a path under UnifiedContent
    When
            Running validate_path on the path
    Then
            Make sure the validation raises PathIsUnified
    """
    with pytest.raises(PathIsUnified):
        _validate(path)


@pytest.mark.parametrize(
    "path",
    (
        "foo",
        "foo/bar",
        "foo/bar.py",
        "Integrations/myIntegration.yml",
        "Integrations/myIntegration/myIntegration.py",
        "Integrations/myIntegration/myIntegration.yml",
    ),
)
def test_deprecatedcontent(path: str):
    with pytest.raises(PathUnderDeprecatedContent):
        _validate(Path("Packs/DeprecatedContent", path))


def test_first_level_folders_subset():
    assert DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES.issubset(DEPTH_ONE_FOLDERS)


def test_dir(repo):
    """
    Given
            A repo
    When
            Calling validate_path on a folder path
    Then
            Make sure it raises the apporpiate exception
    """
    pack = repo.create_pack("myPack")
    integration = pack.create_integration()
    with pytest.raises(PathIsFolder):
        _validate(Path(pack.path))

    with pytest.raises(PathIsFolder):
        _validate(Path(integration.path))
