import logging

import pytest

from demisto_sdk.commands.common.logger import ColorConsoleFormatter


def _create_log_record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(None, None, None, None, msg, None, None)


@pytest.mark.parametrize(
    argnames="msg, expected",
    argvalues=[
        ("[red]foo[/red]", True),
        ("foo", False),
    ],
)
def test_record_contains_escapes(msg: str, expected: bool):
    assert (
        ColorConsoleFormatter._record_contains_escapes(_create_log_record(msg))
        == expected
    )


@pytest.mark.parametrize(
    argnames="msg, expected",
    argvalues=[
        ("[red]foo[/red]", True),
        ("foo", False),
        (" [red]foo[/red]", True),
        (" foo", False),
        ("foo [red]bar[/red]", False),
    ],
)
def test_string_starts_with_escapes(msg: str, expected: bool):
    assert ColorConsoleFormatter._string_starts_with_escapes(msg) == expected


@pytest.mark.parametrize(
    argnames="msg, expected",
    argvalues=[
        ("[red]foo[/red]", True),
        ("foo", False),
        (" [red]foo[/red]", True),
        (" foo", False),
        ("foo [red]bar[/red]", False),
    ],
)
def test_record_starts_with_escapes(msg: str, expected: bool):
    assert (
        ColorConsoleFormatter._record_starts_with_escapes(_create_log_record(msg))
        == expected
    )


@pytest.mark.parametrize(
    argnames="msg, expected",
    argvalues=[
        ("[red]foo[/red]", "[red]"),
        ("foo", ""),
        (" [red]foo[/red]", " [red]"),
        (" foo", ""),
        ("foo [red]bar[/red]", ""),
        ("[red][bold]foo[/bold][/red]", "[red][bold]"),
        ("[red foo", ""),
    ],
)
def test_get_start_escapes(msg: str, expected: bool):
    assert ColorConsoleFormatter._get_start_escapes(_create_log_record(msg)) == expected


@pytest.mark.parametrize(
    argnames="msg, string, expected",
    argvalues=[
        ("[red]foo[/red]", "bar_", "[red]bar_foo[/red]"),
        ("foo", "bar_", "bar_foo"),
        (" [red]foo[/red]", "bar_", " [red]bar_foo[/red]"),
        (" foo", "bar_", "bar_ foo"),
        ("foo [red]bar[/red]", "baz_", "baz_foo [red]bar[/red]"),
    ],
)
def test_insert_into_escapes(msg: str, string: str, expected: str):
    assert (
        ColorConsoleFormatter._insert_into_escapes(_create_log_record(msg), string)
        == expected
    )
