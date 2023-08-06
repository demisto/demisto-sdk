from pathlib import Path

from demisto_sdk.commands.common.tools import is_external_repository
from demisto_sdk.scripts.update_additional_dependencies import (
    update_additional_dependencies,
)


def test_in_external_repo(mocker):
    """
    When
            Running update_additional_dependencies while not in a repository
    Then
            Make sure the script does not fail
    """
    assert is_external_repository()
    assert update_additional_dependencies(Path(), Path(), ()) == 0
