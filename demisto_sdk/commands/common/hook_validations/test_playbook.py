from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class TestPlaybookValidator(ContentEntityValidator):
    """TestPlaybookValidator is designed to validate the correctness of the file structure we enter to content repo for
    both test playbooks and scripts.
    """

    def is_valid_file(self, validate_rn=True):
        """Check whether the test playbook or script file is valid or not
        """

        return all([
            self.is_valid_fromversion(),
        ])
