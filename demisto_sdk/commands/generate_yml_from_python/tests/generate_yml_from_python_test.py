import copy
import datetime
import inspect
import textwrap

import pytest

from demisto_sdk.commands.generate_yml_from_python.generate_yml import \
    YMLGenerator
from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import \
    YMLMetadataCollector


def dedent(code_line, spaces_num):
    indent = spaces_num * ' '
    tab = '\t'
    if code_line.startswith(indent):
        code_line = code_line[spaces_num:]
    if code_line.startswith(tab):
        code_line = code_line[len(tab):]
    return code_line


def save_code_as_integration(code, full_path, configuration=None, conf_in_second_line=False,
                             docstring=''):
    code_snippet_lines = inspect.getsourcelines(code)[0][1:]
    first_indent = len(code_snippet_lines[0]) - len(code_snippet_lines[0].lstrip())
    code_snippet_dedented = [dedent(code_line, first_indent) for code_line in code_snippet_lines]
    code_snippet = ''.join(code_snippet_dedented)
    if docstring:
        code_snippet = code_snippet.replace('**docstring**', docstring)

    if configuration:
        if conf_in_second_line:
            code_lines = code_snippet.split('\n')
            rest_of_code = '\n'.join(code_lines[1:])
            print(f"{code_lines[0]}\nconfiguration={configuration}\n\n{rest_of_code}")
            full_path.write_text(f"{code_lines[0]}\nconfiguration={configuration}\n\n{rest_of_code}")
        else:
            full_path.write_text(f"configuration={configuration}\n\n{code_snippet}")
    else:
        full_path.write_text(code_snippet)


EMPTY_INTEGRATION_DICT = {'category': 'Utilities',
                          'commonfields': {'id': 'some_name', 'version': -1},
                          'configuration': [],
                          'description': '',
                          'display': 'some name',
                          'fromversion': '6.0.0',
                          'name': 'some_name',
                          'script': {'commands': [],
                                     'dockerimage': 'demisto/python3:latest',
                                     'feed': False,
                                     'isfetch': False,
                                     'longRunning': False,
                                     'longRunningPort': False,
                                     'runonce': False,
                                     'script': '-',
                                     'subtype': 'python3',
                                     'type': 'python'},
                          'tests': ['No tests']}

BASIC_CONF_KEY_DICT = {
    "display": "some_name",
    "name": "some_name",
    "type": 0,
    "required": False
}


class TestImportDependencies:
    def test_unrunnable_code_yml_generation(self):
        pass

    def test_generation_with_implicit_imports_in_code(self):
        pass

    def test_generation_with_subscriptable_imports(self):
        pass


class TestConfigurationGeneration:

    @pytest.mark.parametrize("configuration, expected_update",
                             [({"integration_name": "some_name"},
                               {"name": "some_name"}),
                              ({"integration_name": "some_name", "display": "not_some_name"},
                               {"display": "not_some_name"}),
                              ({"integration_name": "some_name", "image": "some_image"},
                               {"image": "some_image"}),
                              ({"integration_name": "some_name", "detailed_description": "some_detailed_description"},
                               {"detaileddescription": "some_detailed_description"}),
                              ({"integration_name": "some_name", "description": "some_description"},
                               {"description": "some_description"}),
                              ({"integration_name": "some_name", "category": "some_category"},
                               {"category": "some_category"}),
                              ],  # TODO: fill in all details
                             ids=["integration_name", "display", "image", "detailed_description",
                                  "description", "category"])
    def test_generate_general_configuration(self, tmp_path, configuration, expected_update):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import \
                YMLMetadataCollector
            metadata_collector = YMLMetadataCollector(**configuration)

            def some_func():
                """Some func doc"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration=configuration)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_dict.update(expected_update)
        assert expected_dict == yml_generator.get_metadata_dict()

    @pytest.mark.parametrize("configuration, expected_update",
                             [({"integration_name": "some_name", "docker_image": "some_dockerimage"},
                               {"dockerimage": "some_dockerimage"}),
                              ({"integration_name": "some_name", "is_feed": True},
                               {"feed": True}),
                              ({"integration_name": "some_name", "is_feed": False},
                               {"feed": False})
                              ],  # TODO: fill in all details
                             ids=["docker_image", "is_feed=True", "is_feed=False"])
    def test_generate_general_script_configuration(self, tmp_path, configuration, expected_update):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import \
                YMLMetadataCollector
            metadata_collector = YMLMetadataCollector(**configuration)

            def some_func():
                """Some func doc"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration=configuration)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_dict["script"].update(expected_update)
        assert expected_dict == yml_generator.get_metadata_dict()

    @pytest.mark.parametrize("configuration, expected_update",
                             [({"name": "some_confkey_name"},
                               {"name": "some_confkey_name", "display": "some_confkey_name"}),
                              ({"name": "some_confkey_name", "display": "some_display_name"},
                               {"name": "some_confkey_name", "display": "some_display_name"}),
                              ({"name": "some_name", "required": True}, {"name": "some_name", "required": True}),
                              ({"name": "some_name", "required": False}, {"name": "some_name", "required": False})
                              ],  # TODO: fill in all details
                             ids=["name", "display", "required=True", "required=False"])
    def test_generate_conf_keys(self, tmp_path, configuration, expected_update):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
                ConfKey, YMLMetadataCollector)

            metadata_collector = YMLMetadataCollector(integration_name="some_name",
                                                      conf=[ConfKey(**configuration)])

            def some_func():
                """Some func doc"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration=configuration)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_conf = copy.deepcopy(BASIC_CONF_KEY_DICT)
        expected_conf.update(expected_update)
        expected_dict["configuration"] = [expected_conf]
        assert expected_dict == yml_generator.get_metadata_dict()

    def test_generate_full_configuration(self, tmp_path):  # TODO: make better
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
                ConfKey, YMLMetadataCollector)

            metadata_collector = YMLMetadataCollector(integration_name="some_name",
                                                      conf=[ConfKey(name="confkey1"),
                                                            ConfKey(name="confkey2")])

            def some_func():
                """Some func doc"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration='')
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()

        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_dict.update({

        })
        expected_dict["configuration"] = [{'display': 'confkey1',
                                           'name': 'confkey1',
                                           'required': False,
                                           'type': 0},
                                          {'display': 'confkey2',
                                           'name': 'confkey2',
                                           'required': False,
                                           'type': 0}]
        assert expected_dict == yml_generator.get_metadata_dict()


BASIC_COMMAND_DICT = {'arguments': [],
                      'deprecated': False,
                      'description': 'Some other description',
                      'name': 'some-command',
                      'outputs': []}

BASIC_IN_ARG_DICT = {'default': False,
                     'name': 'some_arg',
                     'description': 'some_description',
                     'isArray': False,
                     'required': True,
                     'secret': False}

BASIC_OUT_ARG_DICT = {"contextPath": "some.some_out",
                      "description": "some desc",
                      "type": "Unknown"}


class TestCommandGeneration:
    @pytest.mark.parametrize("configuration, expected_update",
                             [({"command_name": "funky-command"}, {"name": "funky-command",
                                                                   "description": "Some funky command"}),
                              ({"command_name": "funky-command", "deprecated": True},
                               {"name": "funky-command", "description": "Some funky command", "deprecated": True}),
                              ({"command_name": "funky-command", "deprecated": False},
                               {"name": "funky-command", "description": "Some funky command", "deprecated": False}),
                              ({"command_name": "funky-command", "execution": True},
                               {"name": "funky-command", "description": "Some funky command", "execution": True}),
                              ({"command_name": "funky-command", "execution": False},
                               {"name": "funky-command", "description": "Some funky command", "execution": False})
                              ],
                             ids=["name", "deprecated=True", "deprecated=False", "execution=True", "execution=False"])
    def test_generate_command_generic(self, tmp_path, configuration, expected_update):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import \
                YMLMetadataCollector

            metadata_collector = YMLMetadataCollector(integration_name="some_name")

            @metadata_collector.command(**configuration)
            def funky_command():
                """Some funky command"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration=configuration)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_command = copy.deepcopy(BASIC_COMMAND_DICT)
        expected_command.update(expected_update)
        expected_dict["script"]["commands"] = [expected_command]
        assert expected_dict == yml_generator.get_metadata_dict()

    @pytest.mark.skip(reason="MISSING FEATURE")
    def test_long_description(self, tmp_path):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import \
                YMLMetadataCollector

            metadata_collector = YMLMetadataCollector(integration_name="some_name")

            @metadata_collector.command(command_name="funky-command")
            def funky_command():
                """Some funky command
                Some interesting details and stuff

                other stuff
                """
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration="")
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_dict["script"]["commands"] = [{
            'arguments': [],
            'deprecated': False,
            'description': 'Some funky command\n    Some interesting details and stuff',
            'name': 'funky-command',
            'outputs': []
        }]
        assert expected_dict == yml_generator.get_metadata_dict()

    def test_restored_args_not_in_command_metadata(self, tmp_path):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
                InputArgument, OutputArgument, YMLMetadataCollector)

            metadata_collector = YMLMetadataCollector(integration_name="some_name")

            @metadata_collector.command(command_name="funky-command", outputs_prefix='funk', execution=False,
                                        outputs_list=[OutputArgument(name="out1", output_type=str,
                                                                     description='desc1')],
                                        inputs_list=[InputArgument(name="in1")])
            def funky_command(client, outputs_prefix, execution, args):
                """Some funky command"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration="")
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        generated_dict = yml_generator.get_metadata_dict()

        # Make sure something was generated.
        assert "out1" in generated_dict["script"]["commands"][0]["outputs"][0]["contextPath"]

        arguments = generated_dict["script"]["commands"][0]["arguments"]
        args_names = [arguments[i]["name"] for i in range(len(arguments))]
        for restored_arg in YMLMetadataCollector.RESTORED_ARGS:
            assert restored_arg not in args_names

    def test_restored_args(self):
        # return it as a dict in the command and assert its right
        pass

    @pytest.mark.parametrize("configuration, expected_update",
                             [({"name": "some_input_arg"}, {"name": "some_input_arg", "description": "some_input_arg"}),
                              ({"name": "some_input_arg", "description": "some desc"},
                               {"name": "some_input_arg", "description": "some desc"}),
                              ],  # TODO: fill in the details, options included
                             ids=["name", "description"])
    def test_inputs_from_input_list(self, tmp_path, configuration, expected_update):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
                InputArgument, YMLMetadataCollector)

            metadata_collector = YMLMetadataCollector(integration_name="some_name")

            @metadata_collector.command(command_name="some-command",
                                        inputs_list=[InputArgument(**configuration)])
            def funky_command():
                """Some other description"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration=configuration)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_command = copy.deepcopy(BASIC_COMMAND_DICT)
        expected_arg = copy.deepcopy(BASIC_IN_ARG_DICT)
        expected_arg.update(expected_update)
        expected_command["arguments"] = [expected_arg]
        expected_dict["script"]["commands"] = [expected_command]
        assert expected_dict == yml_generator.get_metadata_dict()

    @pytest.mark.parametrize("docstring, expected_update",
                             [('Some other description\n'
                               '\n    Args:'
                               '\n        some_input_arg: some desc.',
                               {"name": "some_input_arg", "description": "some desc."}),
                              ('Some other description\n'
                               '\n    Args:'
                               '\n        some_input_arg: required. some desc.\n',
                               {"name": "some_input_arg", "description": "some desc.", "required": True}),
                              ],  # TODO: fill in the details
                             ids=["basic", "required"])
    def test_inputs_from_declaration(self, tmp_path, docstring, expected_update):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
                InputArgument, YMLMetadataCollector)

            metadata_collector = YMLMetadataCollector(integration_name="some_name")

            @metadata_collector.command(command_name="some-command")
            def funky_command():
                """**docstring**"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, docstring=docstring)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_command = copy.deepcopy(BASIC_COMMAND_DICT)
        expected_arg = copy.deepcopy(BASIC_IN_ARG_DICT)
        expected_arg.update(expected_update)
        expected_command["arguments"] = [expected_arg]
        expected_dict["script"]["commands"] = [expected_command]
        assert expected_dict == yml_generator.get_metadata_dict()

    def test_outputs_from_declaration(self):
        pass

    def test_outputs_from_output_list(self, tmp_path):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
                OutputArgument, YMLMetadataCollector)

            metadata_collector = YMLMetadataCollector(integration_name="some_name")

            @metadata_collector.command(command_name="some-command", outputs_prefix="some",
                                        outputs_list=[OutputArgument(name="some_out",
                                                                     description="some desc")])
            def funky_command():
                """Some other description"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_command = copy.deepcopy(BASIC_COMMAND_DICT)
        expected_out = copy.deepcopy(BASIC_OUT_ARG_DICT)
        expected_command["outputs"] = [expected_out]
        expected_dict["script"]["commands"] = [expected_command]
        assert expected_dict == yml_generator.get_metadata_dict()

    @pytest.mark.parametrize("configuration, expected_update",
                             [('str', {"type": "String"}),
                              ('int', {"type": "Number"}),
                              ('float', {"type": "Number"}),
                              ('bool', {"type": "Boolean"}),
                              ('dict', {"type": "Unknown"}),
                              ('list', {"type": "Unknown"}),
                              ('datetime.datetime', {"type": "Date"})
                              ],
                             ids=["str", "int", "float", "bool", "dict", "list", "datetime"])
    def test_outputs_types_from_output_list(self, tmp_path, configuration, expected_update):
        integration_path = tmp_path / "integration_name.py"

        def code_snippet():
            import datetime

            from demisto_sdk.commands.generate_yml_from_python.yml_metadata_collector import (
                OutputArgument, YMLMetadataCollector)

            metadata_collector = YMLMetadataCollector(integration_name="some_name")

            @metadata_collector.command(command_name="some-command", outputs_prefix="some",
                                        outputs_list=[OutputArgument(name="some_out",
                                                                     description="some desc",
                                                                     output_type=configuration)])
            def funky_command():
                """Some other description"""
                print("func")

        save_code_as_integration(code=code_snippet, full_path=integration_path, configuration=configuration,
                                 conf_in_second_line=True)
        yml_generator = YMLGenerator(filename=integration_path)
        yml_generator.generate()
        expected_dict = copy.deepcopy(EMPTY_INTEGRATION_DICT)
        expected_command = copy.deepcopy(BASIC_COMMAND_DICT)
        expected_out = copy.deepcopy(BASIC_OUT_ARG_DICT)
        expected_out.update(expected_update)
        expected_command["outputs"] = [expected_out]
        expected_dict["script"]["commands"] = [expected_command]
        assert expected_dict == yml_generator.get_metadata_dict()

    def test_input_list_overrides_docstring(self):
        pass

    def test_output_list_overrides_docstring(self):
        pass

    def test_multiple_output_prefixes(self):
        pass


class TestYMLGeneration:
    def test_yml_file_making(self):
        pass

    def test_complete_integration_generation(self):
        pass

    def test_no_metadata_collector_defined(self):
        pass
