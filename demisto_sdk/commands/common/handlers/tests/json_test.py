import pytest

from demisto_sdk.commands.common.handlers import JSON_Handler


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
