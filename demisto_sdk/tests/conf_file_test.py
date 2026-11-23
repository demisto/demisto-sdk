from pathlib import Path
from typing import Optional

import typer
from typer.testing import CliRunner

from demisto_sdk.commands.common.constants import DEMISTO_SDK_CONFIG_FILE
from demisto_sdk.utils.config_file import apply_config_file_defaults
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD

runner = CliRunner()


def build_app(calls: dict) -> typer.Typer:
    """A miniature `demisto-sdk` app: a root callback that loads the
    configuration file, plus commands that record the arguments they got.
    """
    app = typer.Typer(pretty_exceptions_enable=False)

    @app.callback(invoke_without_command=True)
    def main(ctx: typer.Context):
        apply_config_file_defaults(ctx)

    @app.command(name="pre-commit")
    def pre_commit(
        input_files: Optional[list[Path]] = typer.Option(
            None, "-i", "--input", "--files"
        ),
        all_files: bool = typer.Option(False, "--all-files", "-a"),
        docker: bool = typer.Option(True, "--docker/--no-docker"),
        mode: str = typer.Option("", "--mode"),
        docker_image: Optional[str] = typer.Option(None, "--docker-image"),
        pre_commit_template_path: Optional[Path] = typer.Option(
            None, "--template-path", envvar="PRE_COMMIT_TEMPLATE_PATH"
        ),
    ):
        calls.update(
            input_files=input_files,
            all_files=all_files,
            docker=docker,
            mode=mode,
            docker_image=docker_image,
            pre_commit_template_path=pre_commit_template_path,
        )

    @app.command(name="error-code")
    def error_code(input: str = typer.Option("", "-i", "--input")):
        calls.update(input=input)

    return app


def run(repo: Repo, config: str, args: list, env: Optional[dict] = None) -> dict:
    """Write a configuration file in the repo and invoke the app from it."""
    calls: dict = {}
    repo.make_file(DEMISTO_SDK_CONFIG_FILE, file_content=config)
    with ChangeCWD(repo.path):
        result = runner.invoke(build_app(calls), args, env=env or {})
    assert result.exit_code == 0, result.output
    return calls


def test_conf_file_sets_command_defaults(repo: Repo):
    """
    Given:
        A configuration file turning a true-by-default flag off, a
        false-by-default flag on, and setting a string option.

    When:
        Running the command without passing any of these options.

    Then:
        The values from the configuration file are used.
    """
    calls = run(
        repo,
        "[pre-commit]\ndocker=false\nall_files=true\nmode=nightly\n",
        ["pre-commit"],
    )

    assert calls["docker"] is False
    assert calls["all_files"] is True
    assert calls["mode"] == "nightly"


def test_conf_file_does_not_override_command_line(repo: Repo):
    """
    Given:
        A configuration file disabling an option.

    When:
        Running the command with that option explicitly enabled.

    Then:
        The command line wins over the configuration file.
    """
    calls = run(repo, "[pre-commit]\ndocker=false\n", ["pre-commit", "--docker"])

    assert calls["docker"] is True


def test_conf_file_does_not_override_environment_variable(repo: Repo):
    """
    Given:
        A configuration file setting an option that also reads an environment
        variable.

    When:
        Running the command with that environment variable set.

    Then:
        The environment variable wins over the configuration file.
    """
    config = "[pre-commit]\npre_commit_template_path=from-config\n"

    calls = run(repo, config, ["pre-commit"])
    assert calls["pre_commit_template_path"] == Path("from-config")

    calls = run(
        repo, config, ["pre-commit"], env={"PRE_COMMIT_TEMPLATE_PATH": "from-env"}
    )
    assert calls["pre_commit_template_path"] == Path("from-env")


def test_conf_file_multi_value_option(repo: Repo):
    """
    Given:
        A configuration file setting a multi-value option to a comma separated
        list, once by parameter name and once by flag name.

    When:
        Running the command.

    Then:
        Both spellings produce the two expected values, rather than the string
        being consumed character by character.
    """
    for key in ("input_files", "input"):
        calls = run(repo, f"[pre-commit]\n{key}=Packs/A,Packs/B\n", ["pre-commit"])

        assert list(calls["input_files"]) == [Path("Packs/A"), Path("Packs/B")]


def test_conf_file_does_not_split_single_value_option(repo: Repo):
    """
    Given:
        A configuration file setting a single-value string option to a value
        that contains commas.

    When:
        Running the command.

    Then:
        The value is passed through as one string.
    """
    calls = run(
        repo, "[pre-commit]\ndocker_image=native:dev,native:ga\n", ["pre-commit"]
    )

    assert calls["docker_image"] == "native:dev,native:ga"


def test_conf_file_section_alias(repo: Repo):
    """
    Given:
        A configuration file with an `error-code-info` section, the name used
        before the file was applied through Click.

    When:
        Running the `error-code` command it configures.

    Then:
        The section is still applied.
    """
    calls = run(repo, "[error-code-info]\ninput=DO106\n", ["error-code"])

    assert calls["input"] == "DO106"


def test_conf_file_ignores_unknown_sections_and_options(repo: Repo):
    """
    Given:
        A configuration file naming a command that does not exist and an option
        the command does not have.

    When:
        Running a command.

    Then:
        Nothing fails and the command keeps its own defaults.
    """
    calls = run(
        repo,
        "[not-a-command]\ndocker=false\n\n[pre-commit]\nnot_a_real_option=1\n",
        ["pre-commit"],
    )

    assert calls["docker"] is True


def test_conf_file_malformed_is_ignored(repo: Repo):
    """
    Given:
        A configuration file without a section header.

    When:
        Running a command.

    Then:
        The file is ignored instead of raising.
    """
    calls = run(repo, "docker=false\n", ["pre-commit"])

    assert calls["docker"] is True


def test_no_conf_file(repo: Repo):
    """
    Given:
        A repo without a configuration file.

    When:
        Running a command.

    Then:
        The command runs with its own defaults.
    """
    calls: dict = {}
    with ChangeCWD(repo.path):
        result = runner.invoke(build_app(calls), ["pre-commit"])

    assert result.exit_code == 0, result.output
    assert calls["docker"] is True
    assert calls["mode"] == ""


def test_conf_file_applies_to_pre_commit_command(repo: Repo, mocker):
    """
    Given:
        A configuration file with a `pre-commit` section.

    When:
        Running the real **pre-commit** command.

    Then:
        The configured values reach `pre_commit_manager`.
    """
    from demisto_sdk.commands.pre_commit import pre_commit_command
    from demisto_sdk.commands.pre_commit.pre_commit_setup import pre_commit

    manager = mocker.patch.object(
        pre_commit_command, "pre_commit_manager", return_value=0
    )

    app = typer.Typer(pretty_exceptions_enable=False)

    @app.callback(invoke_without_command=True)
    def main(ctx: typer.Context):
        apply_config_file_defaults(ctx)

    app.command(name="pre-commit")(pre_commit)

    repo.make_file(
        DEMISTO_SDK_CONFIG_FILE,
        file_content="[pre-commit]\nall_files=true\ndocker=false\nmode=nightly\n",
    )
    with ChangeCWD(repo.path):
        result = runner.invoke(app, ["pre-commit"])

    assert result.exit_code == 0, result.output
    args, kwargs = manager.call_args
    assert args[5] is True  # all_files
    assert args[6] == "nightly"  # mode
    assert kwargs["run_docker_hooks"] is False
