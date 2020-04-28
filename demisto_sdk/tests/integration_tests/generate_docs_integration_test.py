import pytest
from demisto_sdk.commands.common.git_tools import git_path
from os.path import join
from pathlib import Path

from click.testing import CliRunner
from demisto_sdk.__main__ import main

GENERATE_DOCS_CMD = "generate-docs"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
VALID_PLAYBOOK_WITH_IO = join(DEMISTO_SDK_PATH, "tests/test_files/playbook-Test_playbook.yml")
VALID_PLAYBOOK_NO_IO = join(DEMISTO_SDK_PATH, "tests/test_files/Playbooks.playbook-test.yml")


class TestPlaybooks():
    def test_integration_generate_docs_playbook_positive_with_io(self, tmpdir):
        """
        Given
        - Path to valid playbook yml file to generate docs for.
        - Path to directory to write the README.md file.
        - The playbook has inputs.
        - The playbook has outputs.

        When
        - Running the generate-docs command.

        Then
        - Ensure README.md is created.
        - Ensure README.md has an inputs section.
        - Ensure README.md has an outputs section.
        """

        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            '-i', VALID_PLAYBOOK_WITH_IO,
            '-o', tmpdir
        ]
        _ = runner.invoke(main, arguments)
        readme_path = join(tmpdir, 'README.md')

        assert Path(readme_path).exists()
        with open(readme_path, 'r') as readme_file:
            contents = readme_file.read()
            assert '| **Name** | **Description** | **Default Value** | **Required** |' in contents
            assert '| **Path** | **Description** | **Type** |' in contents

    def test_integration_generate_docs_playbook_positive_no_io(self, tmpdir):
        """
        Given
        - Path to valid playbook yml file to generate docs for.
        - Path to directory to write the README.md file.
        - The playbook does not have inputs.
        - The playbook does not have outputs.

        When
        - Running the generate-docs command.

        Then
        - Ensure README.md is created.
        - Ensure README.md does not have an inputs section.
        - Ensure README.md does not have an outputs section.
        """
        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            '-i', VALID_PLAYBOOK_NO_IO,
            '-o', tmpdir
        ]
        _ = runner.invoke(main, arguments)
        readme_path = join(tmpdir, 'README.md')

        assert Path(readme_path).exists()
        with open(readme_path, 'r') as readme_file:
            contents = readme_file.read()
            assert 'There are no inputs for this playbook.' in contents
            assert 'There are no outputs for this playbook.' in contents


@pytest.mark.skip(reason='Just place-holder stubs for later implementation')
class TestScripts():
    def test_integration_generate_docs_script_positive(self):
        pass

    def test_integration_generate_docs_script_negative(self):
        pass


@pytest.mark.skip(reason='Just place-holder stubs for later implementation')
class TestIntegrations():
    def test_integration_generate_docs_integration_positive(self):
        pass

    def test_integration_generate_docs_integration_negative(self):
        pass
