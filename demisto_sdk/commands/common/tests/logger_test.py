import logging
import os

import pytest

from demisto_sdk.commands.common.logger import *


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


@pytest.mark.parametrize(
    "environment_variable_value, default_value, expected_result",
    [
        ("true", True, True),
        ("false", False, False),
        ("true", False, True),
        ("false", True, False),
        ("yes", False, True),
        ("no", True, False),
        ("invalid", True, True),
        ("invalid", False, False),
    ],
)
def test_environment_variable_to_bool_values(
    environment_variable_value: str, default_value: bool, expected_result: bool
):
    os.environ["TEST_ENVIRONMENT_VARIABLE"] = environment_variable_value
    assert (
        environment_variable_to_bool("TEST_ENVIRONMENT_VARIABLE", default_value)
        == expected_result
    )
    del os.environ["TEST_ENVIRONMENT_VARIABLE"]


@pytest.mark.parametrize(
    "default_value, expected_result",
    [
        (True, True),
        (False, False),
    ],
)
def test_environment_variable_to_bool_env_not_set(
    default_value: bool, expected_result: bool
):
    if os.environ.get("TEST_ENVIRONMENT_VARIABLE"):
        del os.environ["TEST_ENVIRONMENT_VARIABLE"]

    assert (
        environment_variable_to_bool("TEST_ENVIRONMENT_VARIABLE", default_value)
        == expected_result
    )


@pytest.mark.parametrize(
    "environment_variable_value, default_value, expected_result",
    [
        ("1234", 0, 1234),
        ("XXX", 0, 0),
    ],
)
def test_environment_variable_to_int_values(
    environment_variable_value: str, default_value: int, expected_result: int
):
    os.environ["TEST_ENVIRONMENT_VARIABLE"] = environment_variable_value
    assert (
        environment_variable_to_int("TEST_ENVIRONMENT_VARIABLE", default_value)
        == expected_result
    )
    del os.environ["TEST_ENVIRONMENT_VARIABLE"]


@pytest.mark.parametrize(
    "default_value, expected_result",
    [
        (1, 1),
    ],
)
def test_environment_variable_to_int_env_not_set(
    default_value: int, expected_result: int
):
    if os.environ.get("TEST_ENVIRONMENT_VARIABLE"):
        del os.environ["TEST_ENVIRONMENT_VARIABLE"]

    assert (
        environment_variable_to_int("TEST_ENVIRONMENT_VARIABLE", default_value)
        == expected_result
    )
