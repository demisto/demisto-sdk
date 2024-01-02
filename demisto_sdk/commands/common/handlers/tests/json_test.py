from io import StringIO

import json5  # noqa: TID251
import pytest
import ujson  # noqa: TID251

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.handlers.json.json5_handler import JSON5_Handler


class TestJSONHandler:
    @pytest.mark.parametrize("slash_count", range(4))
    def test_no_escape_chars_dumps(self, slash_count: int):
        """Check that a dumped json has no escape chars"""
        slashes = "/" * slash_count
        url = f"https:{slashes}xsoar.com"
        dumped = JSON_Handler().dumps({"url": url})
        assert (
            url in dumped
        ), "Could not find the url in the dumped file. Maybe escaped char?"

    @pytest.mark.parametrize("slash_count", range(4))
    def test_no_escape_chars_dump(self, tmpdir, slash_count: int):
        """Check that a dumped json has no escape chars"""
        file_ = tmpdir / "file.json"
        slashes = "/" * slash_count
        url = f"https:{slashes}xsoar.com"
        JSON_Handler().dump({"url": url}, file_.open("w+"))
        assert url in file_.open().read()


@pytest.mark.parametrize(
    "xsoar_handler, handler",
    [
        (
            JSON_Handler,
            ujson,
        ),
        (
            JSON5_Handler,
            json5,
        ),
    ],
)
def test_json_handler_with_indent(mocker, xsoar_handler, handler):
    """
    Given:
        - A JSON_Handler / JSON5_Handler class with indent
    When:
        - run dumps / dump method
    Then:
        - Ensure that the method is called with the expected `indent`
    """
    dumps_mock = mocker.patch.object(handler, "dumps")
    dump_mock = mocker.patch.object(handler, "dump")
    xsoar_handler(indent=4).dumps({"url": "https://xsoar.com"})
    xsoar_handler(indent=4).dump({"url": "https://xsoar.com"}, StringIO())
    assert dumps_mock.call_args[1]["indent"] == 4
    assert dump_mock.call_args[1]["indent"] == 4


@pytest.mark.parametrize(
    "xsoar_handler, handler",
    [
        (
            JSON_Handler,
            ujson,
        ),
        (
            JSON5_Handler,
            json5,
        ),
    ],
)
def test_json_handler_without_indent(mocker, xsoar_handler, handler):
    """
    Given:
        - A JSON_Handler / JSON5_Handler class without indent
    When:
        - run dumps / dump method
    Then:
        - Ensure that the method is called with indent=0
    """
    dumps_mock = mocker.patch.object(handler, "dumps")
    dump_mock = mocker.patch.object(handler, "dump")
    xsoar_handler().dumps({"url": "https://xsoar.com"})
    xsoar_handler().dump({"url": "https://xsoar.com"}, StringIO())
    assert dumps_mock.call_args[1]["indent"] == 0
    assert dump_mock.call_args[1]["indent"] == 0
