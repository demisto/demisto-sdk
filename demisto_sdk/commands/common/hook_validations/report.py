from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)


class ReportValidator(ContentEntityValidator):
    """ReportValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_file(self, validate_rn=True):
        """Check whether the report file is valid or not"""

        return all(
            [
                self.is_valid_fromversion(),
                self.are_fromversion_and_toversion_in_correct_format(),
                self.are_fromversion_toversion_synchronized(),
            ]
        )

    def is_valid_version(self):
        """No version for a report"""
        pass
