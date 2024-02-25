from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import CONTENT_ENTITIES_DIRS, PACKS_FOLDER
from demisto_sdk.scripts.validate_content_path import (
    FIRST_LEVEL_FOLDERS_ALLOWED_TO_CONTAIN_FILES,
    ZERO_DEPTH_ALLOWED_FILES,
    validate_path,
)


@pytest.mark.parametrize("file_name", ("foo.py", "bar.md", *ZERO_DEPTH_ALLOWED_FILES))
def test_depth_one(file_name: str):
    assert validate_path(Path(PACKS_FOLDER, "MyPack", file_name)) == (
        file_name in ZERO_DEPTH_ALLOWED_FILES
    )


@pytest.mark.parametrize("file_name", ("foo.py", "bar.md", *ZERO_DEPTH_ALLOWED_FILES))
def test_depth_two(file_name: str):
    assert validate_path(Path(PACKS_FOLDER, "MyPack", file_name)) == (
        file_name in ZERO_DEPTH_ALLOWED_FILES
    )


def test_content_entities_dir_length():
    """
    This test is here so we don't forget to update FOLDERS_ALLOWED_TO_CONTAIN_FILES when adding/removing content types.
    If this test failed, it's likely you modified either CONTENT_ENTITIES_DIRS or FOLDERS_ALLOWED_TO_CONTAIN_FILES.
    Update the test values accordingly.
    """
    assert len(set(FIRST_LEVEL_FOLDERS_ALLOWED_TO_CONTAIN_FILES)) == 28
    assert len(set(CONTENT_ENTITIES_DIRS)) == 31

    # change this one if you added a content item folder that can't have files directly under it
    assert (
        len(
            FIRST_LEVEL_FOLDERS_ALLOWED_TO_CONTAIN_FILES.intersection(
                CONTENT_ENTITIES_DIRS
            )
        )
        == 26
    )
