from pathlib import Path

from Utils.github_workflow_scripts import handle_new_contribution


def test_main(mocker):
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
