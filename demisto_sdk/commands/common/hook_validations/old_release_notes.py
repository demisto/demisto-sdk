import os
import re

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.tools import (
    old_get_latest_release_notes_text,
    old_get_release_notes_file_path,
    run_command,
)


class OldReleaseNotesValidator(BaseValidator):
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        file_path (str): the path to the file we are examining at the moment.
        release_notes_path (str): the path to the changelog file of the examined file.
        latest_release_notes (str): the text of the UNRELEASED section in the changelog file.
        master_diff (str): the changes in the changelog file compared to origin/master.
    """

    COMMENT_FILLER_REGEX = r"- ?$"
    SINGLE_LINE_REAL_COMMENT_REGEX = r"[a-zA-Z0-9].*\.$"
    MULTI_LINE_REAL_COMMENT_REGEX = r"(\t+| {2,4})- .*\.$"
    LINK_TO_RELEASE_NOTES_STANDARD = "https://xsoar.pan.dev/docs/integrations/changelog"

    def __init__(
        self,
        file_path,
        ignored_errors=None,
        print_as_warnings=False,
        suppress_print=False,
        specific_validations=None,
    ):
        super().__init__(
            ignored_errors=ignored_errors,
            print_as_warnings=print_as_warnings,
            suppress_print=suppress_print,
            specific_validations=specific_validations,
        )
        self.file_path = file_path
        self.release_notes_path = old_get_release_notes_file_path(self.file_path)
        self.latest_release_notes = old_get_latest_release_notes_text(
            self.release_notes_path
        )
        self.master_diff = self.get_master_diff()

    def get_master_diff(self):
        """Gets difference between current branch and origin/master

        git diff with the --unified=100 option means that if there exists a
        difference between origin/master and current branch, the output will have at most 100
        lines of context.

        Returns:
            str. empty string if no changes made or no origin/master branch, otherwise full difference context.
        """
        return run_command(
            f"git diff --unified=100 " f"origin/master {self.release_notes_path}"
        )

    @error_codes("RN101")
    def is_release_notes_changed(self):
        """Validates that a new comment was added to release notes.

        Returns:
            bool. True if comment was added, False otherwise.
        """
        # there exists a difference between origin/master and current branch
        if self.master_diff:
            diff_releases = self.master_diff.split("##")
            unreleased_section = diff_releases[1]
            unreleased_section_lines = unreleased_section.split("\n")

            adds_in_diff = 0
            removes_in_diff = 0

            for line in unreleased_section_lines:
                if line.startswith("+"):
                    adds_in_diff += 1
                elif line.startswith("-") and not re.match(r"- *$", line):
                    removes_in_diff += 1

            # means that at least one new line was added
            if adds_in_diff - removes_in_diff > 0:
                return True

        error_message, error_code = Errors.no_new_release_notes(self.release_notes_path)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False

        return True

    def is_valid_one_line_comment(self, release_notes_comments):
        if re.match(
            self.SINGLE_LINE_REAL_COMMENT_REGEX, release_notes_comments[0]
        ) or re.match(self.COMMENT_FILLER_REGEX, release_notes_comments[0]):
            return True

        return False

    def is_valid_multi_line_comment(self, release_notes_comments):
        for comment in release_notes_comments:
            if not (
                re.match(self.MULTI_LINE_REAL_COMMENT_REGEX, comment)
                or re.match(self.COMMENT_FILLER_REGEX, comment)
            ):
                return False

        return True

    @error_codes("RN101,RN102")
    def is_valid_release_notes_structure(self):
        """Validates that the release notes written in the correct manner.

        Returns:
            bool. True if release notes structure valid, False otherwise
        """
        if self.latest_release_notes is not None:
            release_notes_comments = self.latest_release_notes.split("\n")

        else:
            error_message, error_code = Errors.no_new_release_notes(
                self.release_notes_path
            )
            if self.handle_error(
                error_message, error_code, file_path=self.release_notes_path
            ):
                return False

            return True

        if not release_notes_comments[-1]:
            release_notes_comments = release_notes_comments[:-1]

        if len(release_notes_comments) == 1 and self.is_valid_one_line_comment(
            release_notes_comments
        ):
            return True

        elif len(release_notes_comments) <= 1:
            error_message, error_code = Errors.release_notes_not_formatted_correctly(
                self.LINK_TO_RELEASE_NOTES_STANDARD
            )
            if self.handle_error(
                error_message, error_code, file_path=self.release_notes_path
            ):
                return False

        else:
            if self.is_valid_one_line_comment(release_notes_comments):
                release_notes_comments = release_notes_comments[1:]

            if not self.is_valid_multi_line_comment(release_notes_comments):
                (
                    error_message,
                    error_code,
                ) = Errors.release_notes_not_formatted_correctly(
                    self.LINK_TO_RELEASE_NOTES_STANDARD
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.release_notes_path
                ):
                    return False

        return True

    @error_codes("RN100")
    def validate_file_release_notes_exists(self):
        """Validate that the file has proper release notes when modified.

        Returns:
            bool. True if release notes file exists, False otherwise.
        """
        # checks that release notes file exists and contains text
        if not (os.path.isfile(self.release_notes_path) and self.latest_release_notes):
            error_message, error_code = Errors.missing_release_notes(
                self.release_notes_path
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def is_file_valid(self, branch_name=""):
        """Checks if given file is valid.

        Return:
            bool. True if file's release notes are valid, False otherwise.
        """
        # verifying that the other tests are even necessary
        if not self.validate_file_release_notes_exists():
            return False

        if branch_name != "master":
            validations = [
                self.is_release_notes_changed(),
                self.is_valid_release_notes_structure(),
            ]

        else:
            validations = [self.is_valid_release_notes_structure()]

        return all(validations)
