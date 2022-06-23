import os
from shutil import which
from typing import Tuple

import click

from demisto_sdk.commands.common.tools import run_command_os

RULES_TO_DISABLE = {
    'MD041',  # first-line-heading/first-line-h1
    'MD024'  # no-duplicate-header
}
RULES_TO_DISABLE_ON_VALIDATE = {
    'MD022',  # blanks-around-headings/blanks-around-headers
}


def run_markdown_lint(file: str, fix: bool = False) -> Tuple[bool, bool]:
    """

    Args:
        file: The file to run lint on
        fix: Whether found issues should be automatically fixed where possible

    Returns: A tuple where the first value is whether the function ran, and the second is whether errors were found

    """
    if which('markdownlint') is None:
        click.secho('\nSkipping markdown linting as markdownlint is not installed.\n'
                    'To install, run either `brew install markdownlint-cli` or'
                    ' `npm install -g markdownlint-cli`', fg='yellow')
        return False, False
    command = build_command(file, fix)
    out, err, code = run_command_os(command, os.getcwd())

    if out:
        click.secho(out)
    if err:
        click.secho(err)
    return True, code != 0


def build_command(file, fix):
    disable_rules = RULES_TO_DISABLE
    if not fix:
        disable_rules = disable_rules | RULES_TO_DISABLE_ON_VALIDATE
    command = f'markdownlint {file} --disable {" ".join(disable_rules)}'
    if fix:
        command += ' --fix'
    return command
