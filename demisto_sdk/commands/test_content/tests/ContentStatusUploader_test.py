from pathlib import Path
from typing import List

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.test_content.TestContentClasses import ContentStatusUpdater


def test_update_content_status_initialization(tmp_path: Path) -> None:
    """
    Given: content_status.json does not exist in the artifacts folder.
    When: ContentStatusUpdater is initialized and update_content_status is called with empty lists.
    Then: It should initialize content_status as empty and create the content_status.json file with correct structure.
    """
    # Given
    artifacts_folder = tmp_path
    updater = ContentStatusUpdater(artifacts_folder)
    successful_tests: List[str] = []
    failed_tests: List[str] = []

    # When
    updater.update_content_status(successful_tests, failed_tests)

    # Then
    expected_content_status = {"failed_playbooks": [], "successful_playbooks": []}
    content_status_file = artifacts_folder / "content_status.json"
    assert content_status_file.exists()
    with content_status_file.open("r") as f:
        content = json.load(f)
    assert content == expected_content_status


def test_update_content_status_with_existing_file(tmp_path: Path) -> None:
    """
    Given: content_status.json exists with some playbooks.
    When: update_content_status is called with new playbooks.
    Then: It should update the content_status with new playbooks without duplicates.
    """
    # Given
    artifacts_folder = tmp_path
    content_status_file = artifacts_folder / "content_status.json"
    initial_content_status = {
        "failed_playbooks": ["test_fail_1"],
        "successful_playbooks": ["test_success_1"],
    }
    with content_status_file.open("w") as f:
        json.dump(initial_content_status, f)

    updater = ContentStatusUpdater(artifacts_folder)
    successful_tests = [
        "test_success_2",
        "test_success_1",
    ]  # "test_success_1" is a duplicate
    failed_tests = ["test_fail_2"]

    # When
    updater.update_content_status(successful_tests, failed_tests)

    # Then
    expected_content_status = {
        "failed_playbooks": ["test_fail_1", "test_fail_2"],
        "successful_playbooks": ["test_success_1", "test_success_2"],
    }
    with content_status_file.open("r") as f:
        content = json.load(f)
    assert content == expected_content_status


def test_update_playbooks_no_duplicates(tmp_path: Path) -> None:
    """
    Given: content_status.json exists with some playbooks.
    When: update_content_status is called with playbooks that are already in content_status.
    Then: It should not add duplicates to the playbooks lists.
    """
    # Given
    artifacts_folder = tmp_path
    content_status_file = artifacts_folder / "content_status.json"
    initial_content_status = {
        "failed_playbooks": ["test_fail"],
        "successful_playbooks": ["test_success"],
    }
    with content_status_file.open("w") as f:
        json.dump(initial_content_status, f)

    updater = ContentStatusUpdater(artifacts_folder)
    successful_tests = ["test_success"]  # Duplicate
    failed_tests = ["test_fail"]  # Duplicate

    # When
    updater.update_content_status(successful_tests, failed_tests)

    # Then
    with content_status_file.open("r") as f:
        content = json.load(f)
    assert content == initial_content_status  # No changes expected


def test_initialize_content_status_keys(tmp_path: Path) -> None:
    """
    Given: content_status.json exists without required keys.
    When: update_content_status is called.
    Then: It should initialize missing keys in content_status.
    """
    # Given
    artifacts_folder = tmp_path
    content_status_file = artifacts_folder / "content_status.json"
    initial_content_status = {"some_other_key": []}
    with content_status_file.open("w") as f:
        json.dump(initial_content_status, f)

    updater = ContentStatusUpdater(artifacts_folder)
    successful_tests: List[str] = []
    failed_tests: List[str] = []

    # When
    updater.update_content_status(successful_tests, failed_tests)

    # Then
    expected_content_status = {
        "some_other_key": [],
        "failed_playbooks": [],
        "successful_playbooks": [],
    }
    with content_status_file.open("r") as f:
        content = json.load(f)
    assert content == expected_content_status
