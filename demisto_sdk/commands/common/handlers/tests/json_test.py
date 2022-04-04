from demisto_sdk.commands.common.handlers import JSON_Handler


class TestJSONHandler:
    def test_no_escape_chars_dumps(self):
        """Check that a dumped json has no escape chars"""
        url = 'https://xsoar.com'
        dumped = JSON_Handler().dumps({'url': url})
        assert url in dumped, 'Could not find the url im the dumped file. Maybe escaped char?'

    def test_no_escape_chars_dump(self, tmpdir):
        """Check that a dumped json has no escape chars"""
        file_ = tmpdir / 'file.json'
        url = 'https://xsoar.com'
        JSON_Handler().dump({'url': url}, file_.open('w+'))
        assert url in file_.open().read()
