from pathlib import Path

import pytest

from Utils.github_workflow_scripts import handle_new_contribution


def test_main(mocker):
    """
    Given:
        - A content_roles.json.
    When:
        - A new contribution PR is opened to the SDK.
    Then:
        - Check that the github username of the contribution tl in the created file is correct.
    """
    content_roles = {
        "CONTRIBUTION_REVIEWERS": ["reviewer1", "reviewer2"],
        "CONTRIBUTION_TL": "contrib_tl",
    }
    expected_contrib_tl_username = content_roles["CONTRIBUTION_TL"]
    mocker.patch(
        "Utils.github_workflow_scripts.handle_new_contribution.get_remote_file",
        return_value=content_roles,
    )
    handle_new_contribution.main()
    f = open("contrib_tl.txt", "r")
    contrib_tl_username = f.read()
    Path.unlink(Path("contrib_tl.txt"))
    assert expected_contrib_tl_username == contrib_tl_username


content_roles_empty = {
    "CONTRIBUTION_REVIEWERS": ["reviewer1", "reviewer2"],
    "CONTRIBUTION_TL": "",
}
content_roles_without = {
    "CONTRIBUTION_REVIEWERS": ["reviewer1", "reviewer2"],
}


@pytest.mark.parametrize("content_roles", [content_roles_empty, content_roles_without])
def test_main_without_contrib_tl(mocker, content_roles):
    """
    Given:
        - A content_roles.json with an empty CONTRIBUTION_TL username or isn't existing.
    When:
        - A new contribution PR is opened to the SDK.
    Then:
        - Check that an exception is raised.
    """
    expected_error_message = (
        "There isn't a contribution TL in .github/content_roles.json"
    )
    mocker.patch(
        "Utils.github_workflow_scripts.handle_new_contribution.get_remote_file",
        return_value=content_roles,
    )
    with pytest.raises(Exception) as e:
        handle_new_contribution.main()
        assert expected_error_message == str(e.value)
