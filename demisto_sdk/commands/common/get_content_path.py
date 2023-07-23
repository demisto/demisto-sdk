import logging
import os
from pathlib import Path

import git

logger = logging.getLogger("demisto-sdk")


def is_external_repository() -> bool:
    """
    Returns True if script executed from private repository

    """
    try:
        git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
        private_settings_path = os.path.join(git_repo.working_dir, ".private-repo-settings")  # type: ignore
        return os.path.exists(private_settings_path)
    except git.InvalidGitRepositoryError:
        return True


def get_content_path() -> Path:
    """Get abs content path, from any CWD
    Returns:
        str: Absolute content path
    """
    try:
        if content_path := os.getenv("DEMISTO_SDK_CONTENT_PATH"):
            git_repo = git.Repo(content_path)
            logger.debug(f"Using content path: {content_path}")
        else:
            git_repo = git.Repo(Path.cwd(), search_parent_directories=True)

        remote_url = git_repo.remote().urls.__next__()
        is_fork_repo = "content" in remote_url
        is_external_repo = is_external_repository()

        if not is_fork_repo and not is_external_repo:
            raise git.InvalidGitRepositoryError
        if not git_repo.working_dir:
            return Path.cwd()
        return Path(git_repo.working_dir)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        if not os.getenv("DEMISTO_SDK_IGNORE_CONTENT_WARNING"):
            logger.info(
                "[yellow]Please run demisto-sdk in content repository![/yellow]"
            )
    return Path(".")
