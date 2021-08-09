import io
import os
import shutil

import pytest

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.generate_test_playbook.test_playbook_generator import \
    (PlaybookTestsGenerator, get_command_examples)


def load_file_from_test_dir(filename):
    with io.open(os.path.join(f'{git_path()}/demisto_sdk/commands/tests', 'test_files', filename),
                 mode='r', encoding='utf-8') as f:
        return f.read()


class TestGenerateTestPlaybook:
    TEMP_DIR = 'temp'
    CREATED_DIRS = list()  # type: list

    @classmethod
    def setup_class(cls):
        print("Setups TestGenerateTestPlaybook class")
        if not os.path.exists(TestGenerateTestPlaybook.TEMP_DIR):
            os.mkdir(TestGenerateTestPlaybook.TEMP_DIR)

    @classmethod
    def teardown_class(cls):
        print("Tearing down TestGenerateTestPlaybook class")
        if os.path.exists(TestGenerateTestPlaybook.TEMP_DIR):
            shutil.rmtree(TestGenerateTestPlaybook.TEMP_DIR, ignore_errors=False, onerror=None)

    @pytest.mark.parametrize("use_all_brands,expected_yml",
                             [(False, 'fake_integration_expected_test_playbook.yml'),
                              (True, 'fake_integration_expected_test_playbook__all_brands.yml')])
    def test_generate_test_playbook(self, use_all_brands, expected_yml):
        generator = PlaybookTestsGenerator(
            input=f'{git_path()}/demisto_sdk/tests/test_files/fake_integration.yml',
            file_type='integration',
            output=TestGenerateTestPlaybook.TEMP_DIR,
            name='TestPlaybook',
            all_brands=use_all_brands
        )

        generator.run()

        with io.open(os.path.join(f'{git_path()}/demisto_sdk/tests', 'test_files', expected_yml), mode='r',
                     encoding='utf-8') as f:
            expected_test_playbook_yml = f.read()

        with io.open(os.path.join(TestGenerateTestPlaybook.TEMP_DIR, 'TestPlaybook.yml'), mode='r',
                     encoding='utf-8') as f:
            actual_test_playbook_yml = f.read()

        assert expected_test_playbook_yml == actual_test_playbook_yml


@pytest.mark.parametrize("commands, excepted_num_tasks", [('zoom-create-user,zoom-delete-user', 6), (None, 8)])
def test_generate_test_playbook_with_command_examples(tmp_path, commands, excepted_num_tasks):
    """
    Given:
        An integration yaml input with a command examples file and specified commands by the user.
    When:
        Generating a integration test playbook.
    Then:
        Ensure that the only tasks which be created are the given commands in the examples file or in the commands argument.
        Ensure that the given arguments in the examples file was generate into the test playbook tasks
    """
    command_examples = tmp_path / "command_examples"
    output_tpb = tmp_path / 'TestPlaybook'
    output_tpb.mkdir()

    with open(command_examples, 'w+') as ce:
        ce.write('!zoom-create-user first_name=fname last_name=lname email=flname@example.com\n'
                 '!zoom-create-meeting type=Instant user=fname topic=Meeting\n!zoom-delete-user user=fname')

    generator = PlaybookTestsGenerator(
        input=f'{git_path()}/demisto_sdk/tests/test_files/fake_integration.yml',
        file_type='integration',
        output=str(output_tpb),
        name='TestPlaybook',
        examples=str(command_examples),
        commands=commands
    )

    generator.run()

    tpb_yml = get_yaml(generator.test_playbook_yml_path)

    assert len(tpb_yml.get('tasks', {})) == excepted_num_tasks
    assert tpb_yml['tasks']['2']['scriptarguments']['first_name'] == {'simple': 'fname'}
    assert tpb_yml['tasks']['4']['scriptarguments']['user'] == {'simple': 'fname'}

    if commands:
        assert tpb_yml['tasks']['4']['task']['script'] == 'Zoom|||zoom-delete-user'
    else:
        assert tpb_yml['tasks']['4']['task']['script'] == 'Zoom|||zoom-create-meeting'


@pytest.mark.parametrize("command_examples, excepted_result", [
    ("command_examples", {'zoom-create-meeting': {'topic': 'Meeting', 'type': 'Instant', 'user': 'fname'},
                          'zoom-create-user': {'email': 'flname@example.com', 'first_name': 'fname',
                                               'last_name': 'lname'}}),
    ("!do-some-command arg=arg1 sarg=arg2", {"do-some-command": {"arg": "arg1", "sarg": "arg2"}})
])
def test_get_command_examples(tmp_path, command_examples, excepted_result):
    """
    Given:
        A command examples argument (file path or script command).
    When:
        Running the get_command_examples function.
    Then:
        Ensure the result as expected.
    """

    if command_examples == "command_examples":
        command_examples_arg = tmp_path / command_examples
        with open(command_examples_arg, 'w+') as ce:
            ce.write('!zoom-create-user first_name=fname last_name=lname email=flname@example.com\n'
                     '!zoom-create-meeting type=Instant user=fname topic=Meeting')
    else:
        command_examples_arg = command_examples

    result = get_command_examples(command_examples_arg)

    assert result == excepted_result
