import logging
from os.path import join
from pathlib import Path

import pytest
from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from TestSuite.test_tools import str_in_call_args_list

GENERATE_DOCS_CMD = "generate-docs"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")


class TestPlaybooks:
    def test_integration_generate_docs_playbook_positive_with_io(
        self, tmpdir, mocker, monkeypatch
    ):
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
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        valid_playbook_with_io = join(
            DEMISTO_SDK_PATH, "tests/test_files/playbook-Test_playbook.yml"
        )
        runner = CliRunner(mix_stderr=False)
        arguments = [GENERATE_DOCS_CMD, "-i", valid_playbook_with_io, "-o", tmpdir]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, "playbook-Test_playbook_README.md")

        assert result.exit_code == 0
        assert not result.exception
        assert str_in_call_args_list(
            logger_info.call_args_list, "Generating playbook documentation"
        )
        assert logger_warning.call_count == 0
        assert logger_error.call_count == 0
        assert Path(readme_path).exists()
        with open(readme_path) as readme_file:
            contents = readme_file.read()
            assert (
                "| **Name** | **Description** | **Default Value** | **Required** |"
                in contents
            )
            assert "| **Path** | **Description** | **Type** |" in contents

    def test_integration_generate_docs_playbook_positive_no_io(
        self, tmpdir, mocker, monkeypatch
    ):
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
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        valid_playbook_no_io = join(
            DEMISTO_SDK_PATH, "tests/test_files/Playbooks.playbook-test.yml"
        )
        runner = CliRunner(mix_stderr=False)
        arguments = [GENERATE_DOCS_CMD, "-i", valid_playbook_no_io, "-o", tmpdir]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, "Playbooks.playbook-test_README.md")

        assert result.exit_code == 0
        assert not result.stderr
        assert not result.exception

        assert str_in_call_args_list(
            logger_info.call_args_list, "Generating playbook documentation"
        )
        assert logger_warning.call_count == 0
        assert logger_error.call_count == 0
        assert Path(readme_path).exists()
        with open(readme_path) as readme_file:
            contents = readme_file.read()
            assert "There are no inputs for this playbook." in contents
            assert "There are no outputs for this playbook." in contents

    def test_integration_generate_docs_playbook_dependencies_old_integration(
        self, tmpdir, mocker, monkeypatch
    ):
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
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        valid_playbook_with_dependencies = join(
            DEMISTO_SDK_PATH,
            "tests/test_files/Packs/DummyPack/Playbooks/DummyPlaybook.yml",
        )
        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            "-i",
            valid_playbook_with_dependencies,
            "-o",
            tmpdir,
        ]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, "DummyPlaybook_README.md")

        assert result.exit_code == 0
        assert not result.stderr
        assert not result.exception

        assert str_in_call_args_list(
            logger_info.call_args_list, "Generating playbook documentation"
        )
        assert logger_warning.call_count == 0
        assert logger_error.call_count == 0

        assert Path(readme_path).exists()
        with open(readme_path) as readme_file:
            contents = readme_file.read()
            assert "Builtin" not in contents
            assert "### Integrations\n\n* DummyIntegration\n" in contents

    def test_integration_generate_docs_playbook_pack_dependencies(
        self, tmpdir, mocker, monkeypatch
    ):
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
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        valid_playbook_with_dependencies = join(
            DEMISTO_SDK_PATH,
            "tests/test_files/Packs/CortexXDR/Playbooks/Cortex_XDR_Incident_Handling.yml",
        )
        runner = CliRunner(mix_stderr=False)
        arguments = [
            GENERATE_DOCS_CMD,
            "-i",
            valid_playbook_with_dependencies,
            "-o",
            tmpdir,
        ]
        result = runner.invoke(main, arguments)
        readme_path = join(tmpdir, "Cortex_XDR_Incident_Handling_README.md")

        assert result.exit_code == 0
        assert not result.stderr
        assert not result.exception

        assert str_in_call_args_list(
            logger_info.call_args_list, "Generating playbook documentation"
        )
        assert logger_warning.call_count == 0
        assert logger_error.call_count == 0

        assert Path(readme_path).exists()
        with open(readme_path) as readme_file:
            contents = readme_file.read()
            assert "Builtin" not in contents
            assert "### Integrations\n\n* PaloAltoNetworks_XDR\n" in contents

    def test_integration_generate_docs_positive_with_and_without_io(
        self, tmpdir, mocker, monkeypatch
    ):
        """
        Given
        - Path to valid Playbook directory which contains two yml files to generate docs for.
        - Path to directory to write the README.md files.
        - The first playbook has inputs, the second does not have inputs.
        - The first playbook has outputs, the second does not have outputs.

        When
        - Running the generate-docs command for both files.

        Then
        - Ensure two README.md are created.
        - Ensure the first README.md has an inputs section.
        - Ensure the second README.md does not have an inputs section.
        - Ensure the first README.md has an outputs section.
        - Ensure the second README.md does not have an outputs section.
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        logger_warning = mocker.patch.object(
            logging.getLogger("demisto-sdk"), "warning"
        )
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        valid_playbook_dir = join(DEMISTO_SDK_PATH, "tests/test_files/Playbooks")
        runner = CliRunner(mix_stderr=False)
        arguments = [GENERATE_DOCS_CMD, "-i", valid_playbook_dir, "-o", tmpdir]
        result = runner.invoke(main, arguments)
        readme_path_1 = join(tmpdir, "playbook-Test_playbook_README.md")
        readme_path_2 = join(tmpdir, "Playbooks.playbook-test_README.md")

        assert result.exit_code == 0
        assert not result.stderr
        assert not result.exception

        assert str_in_call_args_list(
            logger_info.call_args_list, "Generating playbook documentation"
        )
        assert logger_warning.call_count == 0
        assert logger_error.call_count == 0

        assert Path(readme_path_1).exists()
        with open(readme_path_1) as readme_file:
            contents = readme_file.read()
            assert (
                "| **Name** | **Description** | **Default Value** | **Required** |"
                in contents
            )
            assert "| **Path** | **Description** | **Type** |" in contents

        assert Path(readme_path_2).exists()
        with open(readme_path_2) as readme_file:
            contents = readme_file.read()
            assert "There are no inputs for this playbook." in contents
            assert "There are no outputs for this playbook." in contents


@pytest.mark.skip(reason="Just place-holder stubs for later implementation")
class TestScripts:
    def test_integration_generate_docs_script_positive(self):
        pass

    def test_integration_generate_docs_script_negative(self):
        pass


@pytest.mark.skip(reason="Just place-holder stubs for later implementation")
class TestIntegrations:
    def test_integration_generate_docs_integration_positive(self):
        pass

    def test_integration_generate_docs_integration_negative(self):
        pass
