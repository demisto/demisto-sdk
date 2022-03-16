import filecmp
import os
import pytest
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.generate_unit_tests.generate_unit_tests import run_generate_unit_tests

ARGS = [({'use_demisto': False}, 'malwarebazaar_all.py'),
        ({'use_demisto': False, 'commands': 'malwarebazaar-comment-add'}, 'malwarebazaar_specific_command.py')]


class TestUnitTestsGenerator:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'generate_unit_tests', 'tests', 'test_files')
    input_source = None
    output_dir = None

    @classmethod
    def setup_class(cls):
        cls.input_source = os.path.join(cls.test_files_path, 'inputs', 'malwarebazaar.py')
        cls.output_dir = os.path.join(cls.test_files_path, 'outputs')


    @pytest.mark.parametrize('args, desired', ARGS)
    def test_tests_generated_successfully(self, args, desired):
        """
        Given
        - Postman collection v2.1 of 4 Virus Total API commands

        When
        - generating config file from the postman collection

        Then
        - ensure the config file is generated
        - the config file should be identical to the one we have under resources folder
        """
        args.update({'input_path': self.input_source,
                     'output_dir': self.output_dir,
                     'test_data_path': 'demisto_sdk/commands/generate_unit_tests/tests/test_files/outputs'})
        test_file_path = os.path.join(self.output_dir, 'malwarebazaar_test.py')
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        run_generate_unit_tests(**args)
        output_path = os.path.join(self.output_dir, 'malwarebazaar_test.py')
        desired = os.path.join(self.output_dir, desired)
        assert filecmp.cmp(output_path, desired)


