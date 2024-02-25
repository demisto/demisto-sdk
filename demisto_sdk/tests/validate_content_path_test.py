from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import CONTENT_ENTITIES_DIRS, PACKS_FOLDER
from demisto_sdk.scripts.validate_content_path import (
    DEPTH_ONE_FOLDERS,
    DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES,
    ZERO_DEPTH_FILES,
    InvalidDepthOneFile,
    InvalidDepthOneFolder,
    InvalidDepthZeroFile,
    PathIsFolder,
    PathUnderDeprecatedContent,
    validate_path,
)


def test_content_entities_dir_length():
    """
    This test is here so we don't forget to update FOLDERS_ALLOWED_TO_CONTAIN_FILES when adding/removing content types.
    If this test failed, it's likely you modified either CONTENT_ENTITIES_DIRS or FOLDERS_ALLOWED_TO_CONTAIN_FILES.
    Update the test values accordingly.
    """
    assert len(set(DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES)) == 28
    assert len(set(CONTENT_ENTITIES_DIRS)) == 31

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
def test_depth_zero_valid(file_name: str):
    validate_path(Path(PACKS_FOLDER, "MyPack", file_name))


@pytest.mark.parametrize("file_name", ("foo.py", "bar.md"))
def test_depth_zero_invalid(file_name: str):
    with pytest.raises(InvalidDepthZeroFile):
        validate_path(Path(PACKS_FOLDER, "MyPack", file_name))


@pytest.mark.parametrize("nested", (True, False))
def test_depth_one_folder_fail(nested: bool):
    """
    Given
            A name of a folder, which is not allowed as a first-level folder
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure the validation raises InvalidDepthOneFolder
    """
    assert (folder_name := "folder_name") not in DEPTH_ONE_FOLDERS
    mid_path = (folder_name, "foo", "bar") if nested else (folder_name)
    with pytest.raises(InvalidDepthOneFolder):
        validate_path(Path(DUMMY_PACK_PATH, *mid_path, "file"))


@pytest.mark.parametrize("folder", DEPTH_ONE_FOLDERS)
@pytest.mark.parametrize("nested", (True, False))
def test_depth_one_folder_pass(folder: str, nested: bool):
    """
    Given
            A name of a folder, which is NOT allowed as a first-level folder
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure the validation passes (without raising)
    """
    assert folder in DEPTH_ONE_FOLDERS
    mid_path = (folder, "foo", "bar") if nested else (folder,)
    validate_path(Path(DUMMY_PACK_PATH, *mid_path, "file"))


@pytest.mark.parametrize("folder", DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES)
def test_depth_two_pass(folder: str):
    """
    Given
            A name of a folder, which may not contain files directly
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure the validation passes (without raising)
    """
    validate_path(DUMMY_PACK_PATH / folder / "file")


@pytest.mark.parametrize("folder", folders_not_allowed_to_contain_files)
def test_depth_two_fail(folder: str):
    """
    Given
            A name of a folder, which may not contain files directly
    When
            Running validate_path on a file created directly under the folder
    Then
            Make sure InvalidDepthTwoFile is raised
    """
    with pytest.raises(InvalidDepthOneFile):
        validate_path(DUMMY_PACK_PATH / folder / "file")


@pytest.mark.parametrize(
    "folder",
    folders_not_allowed_to_contain_files | DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES,
)
def test_third_level_pass(folder: str):
    """
    Given
            A name of a folder
    When
            Running validate on a file created in a folder under that folder second-level
    Then
            Make sure the validation passes
    """
    validate_path(Path(f"content/Packs/myPack/{folder}/subfolder/file"))


@pytest.mark.parametrize(
    "path",
    (
        pytest.param(
            Path("Packs/myPack/Scripts/script-foo.yml"), id="Unified script (yml)"
        ),
        pytest.param(
            Path("Packs/myPack/Scripts/script-foo.md"), id="Unified script (md)"
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
def test_excempt_paths(path: Path):
    """
    Given
            A file under a path exempt
    When
            Running validate_path on the path
    Then
            Make sure the validation passes (without raising)
    """
    validate_path(path)


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
        validate_path(Path("Packs/DeprecatedContent", path))


def test_first_level_folders_subset():
    assert DEPTH_ONE_FOLDERS_ALLOWED_TO_CONTAIN_FILES.issubset(DEPTH_ONE_FOLDERS)


def test_dir(repo):
    """
    Given
            A repo
    When
            Calling validate_path on a folder
    Then
            Make sure it raises the apporpiate exception
    """
    pack = repo.create_pack("myPack")
    integration = pack.create_integration()
    for folder in (pack.path, integration.path):
        with pytest.raises(PathIsFolder):
            validate_path(folder)
