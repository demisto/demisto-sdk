import ast
import filecmp
import itertools
import os
import pytest
from ast import parse
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.generate_unit_tests.generate_unit_tests import run_generate_unit_tests

ARGS = [({'use_demisto': False}, 'malwarebazaar_all.txt'),
        ({'use_demisto': False, 'commands': 'malwarebazaar-comment-add'}, 'malwarebazaar_specific_command.txt')]


def compare_ast(node1, node2):
    """
     Recursively comparing ast objects.
    """
    if type(node1) is not type(node2):
        return False
    if isinstance(node1, ast.AST):
        for k, v in vars(node1).items():
            if k in ('lineno', 'col_offset', 'ctx'):
                continue
            if not compare_ast(v, getattr(node2, k)):
                return False
        return True
    elif isinstance(node1, list):
        return all(itertools.starmap(compare_ast, zip(node1, node2)))
    else:
        return node1 == node2


class TestUnitTestsGenerator:
    test_files_path = os.path.join(git_path(), 'demisto_sdk', 'commands', 'generate_unit_tests', 'tests', 'test_files')
    input_path = None
    output_dir = None

    @classmethod
    def setup_class(cls):
        cls.input_path = os.path.join(cls.test_files_path, 'inputs', 'malwarebazaar.py')
        cls.output_dir = os.path.join(cls.test_files_path, 'outputs')


    @pytest.mark.parametrize('args, desired', ARGS)
    def test_tests_generated_successfully(self, args, desired):
        """
        Given
        - input arguments for the command
        - desired path to generate the test file into.

        When
        - generating config file from the postman collection

        Then
        - ensure the config file is generated
        - the config file should be identical to the one we have under resources folder
        """
        args.update({'input_path': self.input_path,
                     'output_dir': self.output_dir,
                     'test_data_path': 'demisto_sdk/commands/generate_unit_tests/tests/test_files/outputs'})

        output_path = os.path.join(self.output_dir, 'malwarebazaar_test.py')
        desired = os.path.join(self.output_dir, desired)

        if os.path.exists(output_path):
            os.remove(output_path)

        run_generate_unit_tests(**args)


        with open(output_path, 'r') as f:
            output_source = f.read()

        with open(desired, 'r') as f:
            output_desired = f.read()

        assert compare_ast(parse(output_source), parse(output_desired))


