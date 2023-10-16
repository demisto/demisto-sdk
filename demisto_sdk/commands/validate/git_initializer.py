
import os
from typing import Optional

from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
)
from demisto_sdk.commands.common.content import Content
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.logger import logger


class GitInitializer:
    def __init__(self, use_git=None, staged=None, skip_docker_checks=None, is_backward_check=None,
                 skip_dependencies=None, skip_pack_rn_validation=None, is_circle=None, handle_error=None, is_external_repo=None):
        self.staged = staged
        self.use_git = use_git
        self.skip_docker_checks = skip_docker_checks
        self.is_backward_check = is_backward_check
        self.skip_dependencies = skip_dependencies
        self.skip_pack_rn_validation = skip_pack_rn_validation
        self.is_circle = is_circle
        self.handle_error = handle_error
        self.is_external_repo = is_external_repo

    def validate_git_installed(self):
        try:
            self.git_util = Content.git_util()
            self.branch_name = self.git_util.get_current_git_branch_or_hash()
        except (InvalidGitRepositoryError, TypeError):
            # if we are using git - fail the validation by raising the exception.
            if self.use_git:
                raise
            # if we are not using git - simply move on.
            else:
                logger.info("Unable to connect to git")
                self.git_util = None  # type: ignore[assignment]
                self.branch_name = ""
        return self.branch_name

    def setup_prev_ver(self, prev_ver: Optional[str]):
            """Setting up the prev_ver parameter"""
            # if prev_ver parameter is set, use it
            if prev_ver:
                return prev_ver

            # If git is connected - Use it to get prev_ver
            if self.git_util:
                # If demisto exists in remotes if so set prev_ver as 'demisto/master'
                if self.git_util.check_if_remote_exists("demisto"):
                    return "demisto/master"

                # Otherwise, use git to get the primary branch
                _, branch = self.git_util.handle_prev_ver()
                return f"{DEMISTO_GIT_UPSTREAM}/" + branch

            # Default to 'origin/master'
            return f"{DEMISTO_GIT_UPSTREAM}/master"
        
    def set_prev_ver(self, prev_ver):
        if prev_ver and not prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
            self.prev_ver = self.setup_prev_ver(f"{DEMISTO_GIT_UPSTREAM}/" + prev_ver)
        else:
            self.prev_ver = self.setup_prev_ver(prev_ver)
        return self.prev_ver
    
    def collect_files_to_run(self):
        pass

    def setup_git_params(self):
        """Setting up the git relevant params"""
        self.branch_name = (
            self.git_util.get_current_git_branch_or_hash()
            if (self.git_util and not self.branch_name)
            else self.branch_name
        )

        # check remote validity
        if "/" in self.prev_ver and not self.git_util.check_if_remote_exists(
            self.prev_ver
        ):
            non_existing_remote = self.prev_ver.split("/")[0]
            logger.info(
                f"[red]Could not find remote {non_existing_remote} reverting to "
                f"{str(self.git_util.repo.remote())}[/red]"
            )
            self.prev_ver = self.prev_ver.replace(
                non_existing_remote, str(self.git_util.repo.remote())
            )

        # if running on release branch check against last release.
        if self.branch_name.startswith("21.") or self.branch_name.startswith("22."):
            self.skip_pack_rn_validation = True
            self.prev_ver = os.environ.get("GIT_SHA1")
            self.is_circle = True

            # when running against git while on release branch - show errors but don't fail the validation
            self.always_valid = True

        # On main or master don't check RN
        elif self.branch_name in ["master", "main", DEMISTO_GIT_PRIMARY_BRANCH]:
            self.skip_pack_rn_validation = True
            error_message, error_code = Errors.running_on_master_with_git()
            if self.handle_error:
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path="General",
                    warning=(not self.is_external_repo or self.is_circle),
                    drop_line=True,
                ):
                    return False
            else:
                return False
                # to implement: return validation_result
        return True
    
    def print_git_config(self):
        logger.info(
            f"\n[cyan]================= Running validation on branch {self.branch_name} =================[/cyan]"
        )
        logger.info(f"Validating against {self.prev_ver}")

        if self.branch_name in [
            self.prev_ver,
            self.prev_ver.replace(f"{DEMISTO_GIT_UPSTREAM}/", ""),
        ]:  # pragma: no cover
            logger.info("Running only on last commit")

        elif self.is_circle:
            logger.info("Running only on committed files")

        elif self.staged:
            logger.info("Running only on staged files")

        else:
            logger.info("Running on committed and staged files")

        if self.skip_pack_rn_validation:
            logger.info("Skipping release notes validation")

        if self.skip_docker_checks:
            logger.info("Skipping Docker checks")

        if not self.is_backward_check:
            logger.info("Skipping backwards compatibility checks")

        if self.skip_dependencies:
            logger.info("Skipping pack dependencies check")
