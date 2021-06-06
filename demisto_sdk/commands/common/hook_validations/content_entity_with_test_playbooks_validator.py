from abc import ABC

from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.test_playbook import \
    TestPlaybookValidator


class ContentEntityWithTestPlaybooksValidator(ContentEntityValidator, ABC):
    def has_unskipped_test_playbook(self, id_set_file: dict, test_playbook_ids: list = []) -> bool:
        """Check if the content entity has at least one unskipped test playbook."""
        test_playbooks_unskip_status = {}

        if self.current_file.get('tests') is list:
            test_playbook_ids.extend(self.current_file.get('tests', []))

        for test_playbook_id in set(test_playbook_ids):
            test_playbooks_unskip_status[test_playbook_id] = self.is_test_playbook_unskipped(test_playbook_id,
                                                                                             id_set_file)
        if not any(test_playbooks_unskip_status.values()):
            return False
        return True

    def is_test_playbook_unskipped(self, test_playbook_id: str, id_set_file: dict) -> bool:
        """Check if a certain test playbook is unskipped."""
        test_playbooks = id_set_file.get('TestPlaybooks', [])
        test_playbook_file_path = ''
        for test_playbook in test_playbooks:
            if test_playbook_id in test_playbook.keys():
                test_playbook_file_path = test_playbook.get(test_playbook_id, {}).get('file_path', None)
                print(f"DDDD1:{test_playbook_file_path}")

        structure_validator = self.get_struct_validator_for_test_playbook(test_playbook_file_path)
        test_playbook_validator = TestPlaybookValidator(structure_validator=structure_validator)
        return test_playbook_validator.is_unskipped_playbook()

    # For easier testing
    @staticmethod
    def get_struct_validator_for_test_playbook(test_playbook_file_path: str) -> StructureValidator:
        """Return StructureValidator of a test playbook file path."""
        return StructureValidator(test_playbook_file_path)
