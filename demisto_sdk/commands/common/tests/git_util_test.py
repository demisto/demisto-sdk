def test_find_primary_branch():
    """
    Given
        - A Git repo

    When
        - Searching for the primary branch

    Then
        - Ensure ithe returned value is either 'main', 'master', or None
    """
    from demisto_sdk.commands.common.git_util import GitUtil

    assert not GitUtil.find_primary_branch(None)

    class Object:
        pass

    empty_repo = Object()
    assert not GitUtil.find_primary_branch(empty_repo)

    repo_with_empty_remotes = Object()
    repo_with_empty_remotes.remotes = []
    assert not GitUtil.find_primary_branch(repo_with_empty_remotes)

    repo_with_empty_remotes_refs = Object()
    repo_with_empty_remotes_refs.remotes = []
    empty_refs = Object()
    repo_with_empty_remotes_refs.remotes.append(empty_refs)
    assert not GitUtil.find_primary_branch(repo_with_empty_remotes_refs)

    repo_with_remotes_refs_main = Object()
    repo_with_remotes_refs_main.remotes = []
    refs_main = Object()
    refs_main.refs = ["a", "origin/main", "c"]
    repo_with_remotes_refs_main.remotes.append(refs_main)
    assert GitUtil.find_primary_branch(repo_with_remotes_refs_main) == "main"

    repo_with_remotes_refs_master = Object()
    repo_with_remotes_refs_master.remotes = []
    refs_master = Object()
    refs_master.refs = ["a", "origin/master", "c"]
    repo_with_remotes_refs_master.remotes.append(refs_master)
    assert GitUtil.find_primary_branch(repo_with_remotes_refs_master) == "master"

    repo_with_remotes_refs_other = Object()
    repo_with_remotes_refs_other.remotes = []
    refs_other = Object()
    refs_other.refs = ["a", "b"]
    repo_with_remotes_refs_other.remotes.append(refs_other)
    assert not GitUtil.find_primary_branch(repo_with_remotes_refs_other)
