from os.path import join
from pathlib import Path

import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path

GENERATE_DOCS_CMD = "generate-docs"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")


class TestPlaybooks:
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
        valid_playbook_with_io = join(DEMISTO_SDK_PATH, "tests/test_files/playbook-Test_playbook.yml")
        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            '-i', valid_playbook_with_io,
            '-o', tmpdir
        ]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, 'playbook-Test_playbook_README.md')

        assert result.exit_code == 0
        assert 'Start generating playbook documentation...' in result.stdout
        assert not result.stderr
        assert not result.exception
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
        valid_playbook_no_io = join(DEMISTO_SDK_PATH, "tests/test_files/Playbooks.playbook-test.yml")
        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            '-i', valid_playbook_no_io,
            '-o', tmpdir
        ]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, 'Playbooks.playbook-test_README.md')
        assert result.exit_code == 0
        assert 'Start generating playbook documentation...' in result.stdout
        assert not result.stderr
        assert not result.exception
        assert Path(readme_path).exists()
        with open(readme_path, 'r') as readme_file:
            contents = readme_file.read()
            assert 'There are no inputs for this playbook.' in contents
            assert 'There are no outputs for this playbook.' in contents

    def test_integration_generate_docs_playbook_dependencies_old_integration(self, tmpdir):
        """
        Given
        - Path to valid playbook yml file to generate docs for.
        - Path to directory to write the README.md file.

        When
        - Running the generate-docs command.

        Then
        - Ensure README.md is created.
        - Ensure integration dependencies exists.
        - Ensure Builtin not in dependencies.
        """
        valid_playbook_with_dependencies = join(DEMISTO_SDK_PATH, "tests/test_files/Packs/DummyPack/Playbooks/DummyPlaybook.yml")
        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            '-i', valid_playbook_with_dependencies,
            '-o', tmpdir
        ]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, 'DummyPlaybook_README.md')

        assert result.exit_code == 0
        assert 'Start generating playbook documentation...' in result.stdout
        assert not result.stderr
        assert not result.exception
        assert Path(readme_path).exists()
        with open(readme_path, 'r') as readme_file:
            contents = readme_file.read()
            assert 'Builtin' not in contents
            assert '### Integrations\n* DummyIntegration\n' in contents

    def test_integration_generate_docs_playbook_pack_dependencies(self, tmpdir):
        """
        Given
        - Path to valid playbook yml file to generate docs for.
        - Path to directory to write the README.md file.

        When
        - Running the generate-docs command.

        Then
        - Ensure README.md is created.
        - Ensure integration dependencies exists.
        - Ensure Builtin not in dependencies.
        """
        valid_playbook_with_dependencies = join(DEMISTO_SDK_PATH, "tests/test_files/Packs/CortexXDR/Playbooks/Cortex_XDR_Incident_Handling.yml")
        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            '-i', valid_playbook_with_dependencies,
            '-o', tmpdir
        ]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, 'Cortex_XDR_Incident_Handling_README.md')

        assert result.exit_code == 0
        assert 'Start generating playbook documentation...' in result.stdout
        assert not result.stderr
        assert not result.exception
        assert Path(readme_path).exists()
        with open(readme_path, 'r') as readme_file:
            contents = readme_file.read()
            assert 'Builtin' not in contents
            assert '### Integrations\n* PaloAltoNetworks_XDR\n' in contents


@pytest.mark.skip(reason='Just place-holder stubs for later implementation')
class TestScripts:
    def test_integration_generate_docs_script_positive(self):
        pass

    def test_integration_generate_docs_script_negative(self):
        pass


@pytest.mark.skip(reason='Just place-holder stubs for later implementation')
class TestIntegrations:
    def test_integration_generate_docs_integration_positive(self):
        pass

    def test_integration_generate_docs_integration_negative(self):
        pass
