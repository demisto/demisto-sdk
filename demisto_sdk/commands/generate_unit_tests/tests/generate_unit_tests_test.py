import ast
import itertools
import os
from ast import parse
from pathlib import Path

import pytest

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.generate_unit_tests.generate_unit_tests import (
    UnitTestsGenerator, run_generate_unit_tests)

ARGS = [({'use_demisto': False}, 'malwarebazaar_all.py'),
        ({'use_demisto': False, 'commands': 'malwarebazaar-comment-add'}, 'malwarebazaar_specific_command.py'),
        ({'use_demisto': True}, 'malwarebazaar_all.py')]


EXAMPLES = {'readable_output': "test_md_example", 'outputs': {"MalwareBazaar": {"MalwarebazaarCommentAdd": {"comment": "test"}}}}


def compare_ast(node1, node2):
    """
     Recursively comparing ast objects.
    """
    if type(node1) is not type(node2):
        return False
    if isinstance(node1, ast.AST):
        for (k, v) in vars(node1).items():
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
    test_files_path = Path(__file__, git_path(), 'demisto_sdk', 'commands', 'generate_unit_tests', 'tests', 'test_files')
    input_path = None
    output_dir = None

    @classmethod
    def setup_class(cls):
        cls.input_path = str(Path(cls.test_files_path, 'inputs', 'malwarebazaar.py'))
        cls.output_dir = str(Path(cls.test_files_path, 'outputs'))

    @pytest.mark.parametrize('args, expected_result', ARGS)
    def test_tests_generated_successfully(self, mocker, args, expected_result):
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

        mocker.patch.object(UnitTestsGenerator, "execute_commands_into_dict", return_value=(EXAMPLES, []))

        output_path = Path(self.output_dir, 'malwarebazaar_test.py')
        desired = Path(self.output_dir, expected_result)

        run_generate_unit_tests(
            input_path=self.input_path,
            commands=args.get('commands', ''),
            output_dir=self.output_dir,
            examples='',
            insecure=False,
            use_demisto=False,
            append=False
        )

        with open(output_path, 'r') as f:
            output_source = f.read()

        with open(desired, 'r') as f:
            output_desired = f.read()

        try:
            assert compare_ast(parse(output_source), parse(output_desired))
        finally:
            if output_path.exists():
                os.remove(output_path)
