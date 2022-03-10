import inspect
import textwrap

import pytest

from demisto_sdk.commands.generate_yml_from_python.generate_yml import \
    YMLGenerator
from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
    CommandMetadata, ConfKey, InputArgument, YMLMetadataCollector)


def dedent(code_line, spaces_num):
    indent = spaces_num * ' '
    tab = '\t'
    if code_line.startswith(indent):
        code_line = code_line[spaces_num:]
    if code_line.startswith(tab):
        code_line = code_line[len(tab):]
    return code_line


def save_code_as_integration(code, full_path):
    code_snippet_lines = inspect.getsourcelines(code)[0][1:]
    first_indent = len(code_snippet_lines[0]) - len(code_snippet_lines[0].lstrip())
    code_snippet_dedented = [dedent(code_line, first_indent) for code_line in code_snippet_lines]
    code_snippet = ''.join(code_snippet_dedented)
    full_path.write_text(code_snippet)


class TestImportDependencies:
    def test_unrunnable_code_yml_generation(self):
        pass

    def test_generation_with_implicit_imports_in_code(self):
        pass

    def test_generation_with_subscriptable_imports(self):
        pass


class TestConfigurationGeneration:
    def test_general_stuff(self, tmp_path):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import \
                YMLMetadataCollector
            metadata_collector = YMLMetadataCollector(integration_name='some_name')

            def some_func():
                """Some func doc"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path)
        YMLGenerator(filename=integration_path)
        assert False

    def test_generate_general_configuration(self):
        pass

    def test_generate_conf_keys(self):
        pass

    def test_generate_full_configuration(self):
        pass


class TestInputsGeneration:
    # parmaterize different input lists
    def test_inputs_from_declaration(self):
        pass

    # parmaterize different input lists
    def test_inputs_from_input_list(self):
        pass


class TestOutputsGeneration:
    # parmaterize different outputs lists
    def test_outputs_from_declaration(self):
        pass

    # parmaterize different outputs lists
    def test_outputs_from_output_list(self):
        pass


class TestYMLGeneration:
    def test_complete_integration_generation(self):
        pass

    def test_restored_args_not_in_command_metadata(self):
        pass

    def test_input_list_overrides_docstring(self):
        pass

    def test_output_list_overrides_docstring(self):
        pass

    def test_no_metadata_collector_defined(self):
        pass
