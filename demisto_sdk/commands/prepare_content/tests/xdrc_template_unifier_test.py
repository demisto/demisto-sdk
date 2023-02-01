import json
import os
from pathlib import Path

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.prepare_content.prepare_upload_manager import (
    PrepareUploadManager,
)

TESTS_DIR = f"{git_path()}/demisto_sdk/tests"


def test_unify_xdrc_template():
    """
    Given
    - Dummy XDRC Template.
    - No output path.

    When
    - Running Unify on it.

    Then
    - Ensure Unify xdrc template works
    """
    input_path = (
        TESTS_DIR + "/test_files/Packs/DummyPack/XDRCTemplates/DummyXDRCTemplate"
    )
    output_path = TESTS_DIR + "/test_files/Packs/DummyPack/XDRCTemplates/"
    export_json_path = PrepareUploadManager.prepare_for_upload(
        Path(input_path), Path(output_path)
    )

    expected_json_path = (
        TESTS_DIR
        + "/test_files/Packs/DummyPack/XDRCTemplates/xdrctemplate-DummyXDRCTemplate.json"
    )

    assert export_json_path == Path(expected_json_path)

    expected_json_file = {
        "content_global_id": "1",
        "name": "Dummmy",
        "os_type": "AGENT_OS_LINUX",
        "profile_type": "STANDARD",
        "yaml_template": "dGVzdDogZHVtbXlfdGVzdA==",
    }
    with open(expected_json_path) as real_file:
        assert expected_json_file == json.load(real_file)

    os.remove(export_json_path)
