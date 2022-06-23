import functools
import tempfile

import pytest

from demisto_sdk.commands.common.mardown_lint import run_markdown_lint


@pytest.mark.parametrize('file_content, expected_error', [
    ('##Hello', 'no-missing-space-atx No space after hash on atx style heading'), (
        """
##Unreleased
   * Feature1
* feature2""", 'Unordered list indentation '
    )
])
def test_markdown_validations(file_content, expected_error, mocker):
    click_mock = mocker.patch("click.secho")
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(file_content.encode())
        temp.flush()
        ran, has_error = run_markdown_lint(temp.name)
        assert ran and has_error
        assert expected_error in click_mock.call_args.args[0]


@pytest.mark.parametrize('file_content, expected_output', [
    ('##Hello', '## Hello\n'),
    (
        """
##Unreleased
   * Feature1
* feature2""",
        """
## Unreleased

* Feature1
* feature2
"""), (
        """
## SomeHeading
Bold with **asterisk**
Bold with __underscore__
""",
        """
## SomeHeading

Bold with **asterisk**
Bold with **underscore**
"""
    )
])
def test_markdown_fixes(file_content, expected_output):
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(file_content.encode())
        temp.flush()
        run_markdown_lint(temp.name, True)
        assert functools.reduce(lambda a, b: a + b, open(temp.name).readlines()) == expected_output


def test_no_line_after_header_not_invalid():
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(
            b"""## Header
No extra line
""")
        temp.flush()
        ran, has_error = run_markdown_lint(temp.name)
        assert ran and not has_error
