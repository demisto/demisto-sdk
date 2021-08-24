import json
import sys
from collections import OrderedDict
from unittest.mock import MagicMock, mock_open

import mitmproxy
import pytest
from mitmproxy.http import HTTPFlow, HTTPRequest
from mitmproxy.net.http import Headers

from demisto_sdk.commands.test_content.timestamp_replacer import \
    TimestampReplacer


@pytest.fixture()
def flow():
    request = HTTPRequest(first_line_format='first_line',
                          host=b'localhost',
                          path=b'/test/',
                          http_version=b'1.1',
                          port=1234,
                          method=b'',
                          scheme=b'',
                          headers=Headers([(b"Host", b"example.com")]),
                          content=None,
                          timestamp_start=111.1)
    flow = HTTPFlow(client_conn=MagicMock(),
                    server_conn=MagicMock())
    flow.request = request
    return flow


TIMESTAMP_FORMATS = [
    '2021-01-11T13:18:12+00:00',
    '2021-01-14 17:44:00.571043',
    '1610639147',
    'Thu, 14 Jan 2021 15:45:47',
    'Thursday, 14-Jan-21 15:45:47 UTC',
    '2021-01-14T15:45:47+00:00'
]


class TestTimeStampReplacer:
    DEFAULT_OPTIONS_MAPPING = {
        'detect_timestamps': False,
        'keys_filepath': 'problematic_keys.json',
        'script_mode': 'playback',
        'debug': False
    }

    @classmethod
    def setup_class(cls):
        mitmproxy.ctx.options = MagicMock(**cls.DEFAULT_OPTIONS_MAPPING)

    def test_loader_defaults(self, mocker):
        """
        Given:
            - A timestamp replacer instance
        When:
            - Loading it's options
        Then:
            - Ensure that a call with the expected defaults is called
        """
        master_mock = mocker.MagicMock()
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.load(master_mock)
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor == 7:
            pytest.skip('The current mock syntax is supported only in python 3.8+')
        assert master_mock.add_option.call_count == 4
        for call in master_mock.add_option.mock_calls:
            assert self.DEFAULT_OPTIONS_MAPPING[call.kwargs['name']] == call.kwargs['default']

    def test_running(self, mocker):
        """
        Given:
            - A timestamp replacer instance
        When:
            - executing the 'running' method
        Then:
            - Ensure all problematic keys are loaded
        """
        problematic_keys = {'server_replay_ignore_params': 'query_key1 query_key2',
                            'server_replay_ignore_payload_params': 'payload_key1 payload_key2',
                            'keys_to_replace': 'key_to_replace1 key_to_replace2'}
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('builtins.open', mock_open(read_data=json.dumps(problematic_keys)))
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.running()
        assert time_stamp_replacer.query_keys == {'query_key2', 'query_key1'}
        assert time_stamp_replacer.form_keys == {'payload_key2', 'payload_key1'}
        assert time_stamp_replacer.json_keys == {'key_to_replace2', 'key_to_replace1'}

    @pytest.mark.parametrize('time', TIMESTAMP_FORMATS)
    def test_finding_problematic_keys_in_url_query(self, mocker, flow, time):
        """
        Given:
            - A timestamp replacer instance
        When:
            - searching a request for problematic keys that has timestamp values in the query params
        Then:
            - Ensure the problematic key is loaded into query_keys
            - Ensure the valid key is not loaded into query_keys
        """
        mocker.patch('builtins.open', mock_open())
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'record'
        flow.request._set_query([('key1', 'value1'), ('timestamp_key', time)])
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.request(flow)
        assert 'timestamp_key' in time_stamp_replacer.query_keys
        assert 'key1' not in time_stamp_replacer.query_keys

    @pytest.mark.parametrize('time', TIMESTAMP_FORMATS)
    def test_finding_problematic_keys_in_form_keys(self, mocker, flow, time):
        """
        Given:
            - A timestamp replacer instance
        When:
            - searching a request for problematic keys that has timestamp values
        Then:
            - Ensure the problematic key is loaded into form_keys
            - Ensure the valid key is not loaded into form_keys
        """
        mocker.patch('builtins.open', mock_open())
        # patching builtin.open breaks dateparser, which attempts to open a timezone file, the following patch fixes it.
        mocker.patch('dateparser.date.apply_timezone_from_settings', lambda x, _: x)
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'record'
        flow.request._set_urlencoded_form([('key1', 'value1'), ('timestamp_key', time)])
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.request(flow)
        assert 'timestamp_key' in time_stamp_replacer.form_keys
        assert 'key1' not in time_stamp_replacer.form_keys

    @pytest.mark.parametrize('time', TIMESTAMP_FORMATS)
    def test_finding_problematic_keys_in_json_keys(self, mocker, flow, time):
        """
        Given:
            - A timestamp replacer instance
        When:
            - searching a request for problematic keys that has timestamp values
        Then:
            - Ensure the problematic key is loaded into json_keys
            - Ensure the problematic key is loaded into json_keys even when it's nested
            - Ensure the valid key is not loaded into json_keys
        """
        mocker.patch('builtins.open', mock_open())
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'record'
        flow.request.method = 'POST'
        flow.request.set_content(json.dumps({'key1': 'value1',
                                             'timestamp_key': time,
                                             'dict1': {'list': ['test', time]}}).encode())
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.request(flow)
        assert 'timestamp_key' in time_stamp_replacer.json_keys
        assert 'dict1.list.1' in time_stamp_replacer.json_keys
        assert 'key1' not in time_stamp_replacer.json_keys

    def test_json_body_parsing(self, mocker, flow):
        """
        Given:
            - A timestamp replacer instance
        When:
            - Trying to parse json body
        Then:
            - Ensure the body is parsed when is't json body
            - Ensure the body is parsed when it's json body with single quotes
        """
        mocker.patch('builtins.open', mock_open())
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'record'
        flow.request.method = 'POST'
        flow.request.set_content(str({'timestamp_key': '2021-01-11T13:18:12+00:00'}).encode())
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.request(flow)
        assert 'timestamp_key' in time_stamp_replacer.json_keys

    @pytest.mark.parametrize('time', TIMESTAMP_FORMATS)
    def test_cleaning_problematic_keys_from_url_query(self, mocker, flow, time):
        """
        Given:
            - A timestamp replacer instance
        When:
            - digesting a request in playback mode
        Then:
            - Ensure the problematic key passed as query param is replaced with constant value
        """
        mocker.patch('builtins.open', mock_open())
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'playback'
        flow.request._set_query([('key1', 'value1'), ('timestamp_key', time)])
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.query_keys = ['timestamp_key']
        time_stamp_replacer.request(flow)
        for key, val in flow.request._get_query():
            if key == 'timestamp_key':
                assert val == time_stamp_replacer.constant

    @pytest.mark.parametrize('time', TIMESTAMP_FORMATS)
    def test_cleaning_problematic_keys_from_form_keys(self, mocker, flow, time):
        """
        Given:
            - A timestamp replacer instance
        When:
            - digesting a request in playback mode
        Then:
            - Ensure the problematic key passed as form key is replaced with constant value
        """
        mocker.patch('builtins.open', mock_open())
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'playback'
        flow.request._set_urlencoded_form([('key1', 'value1'), ('timestamp_key', time)])
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.form_keys = ['timestamp_key']
        time_stamp_replacer.request(flow)
        for key, val in flow.request._get_urlencoded_form():
            if key == 'timestamp_key':
                assert val == time_stamp_replacer.constant

    @pytest.mark.parametrize('time', TIMESTAMP_FORMATS)
    def test_cleaning_problematic_keys_from_json_keys(self, mocker, flow, time):
        """
        Given:
            - A timestamp replacer instance
        When:
            - digesting a request in playback mode
        Then:
            - Ensure the problematic keys passed in json body are replaced with constant value
        """
        mocker.patch('builtins.open', mock_open())
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'playback'
        flow.request.method = 'POST'
        flow.request.set_content(json.dumps({'key1': 'value1',
                                             'timestamp_key': time,
                                             'dict1': {'list': ['test', time]}}).encode())
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.json_keys = ['timestamp_key', 'dict1.list.1']
        time_stamp_replacer.request(flow)
        content = json.loads(flow.request.get_content(), object_pairs_hook=OrderedDict)
        for key, val in content.items():
            if key == 'timestamp_key':
                assert val == time_stamp_replacer.constant
            elif key == 'dict1':
                assert time_stamp_replacer.constant in val['list']

    def test_url_query_is_sorted(self, mocker, flow):
        """
        Given:
            - A timestamp replacer instance
        When:
            - searching a request for problematic keys that has timestamp values in the query params
        Then:
            - Ensure that the request query params are sorted
        """
        mocker.patch('builtins.open', mock_open())
        mitmproxy.ctx.options.detect_timestamps = True
        mitmproxy.ctx.options.script_mode = 'clean'
        flow.request._set_query([('key2', 'value2'), ('key1', 'value1')])
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.request(flow)
        updated_request = flow.request._get_query()
        assert updated_request[0] == ('key1', 'value1')
        assert updated_request[1] == ('key2', 'value2')

    def test_live_false_when_running_in_playback_state(self, flow):
        """
            Given:
                - A flow
            When:
                - script is in playback mode
            Then:
                - Ensure that the request will not go out to the real world
        """
        mitmproxy.ctx.options.script_mode = 'playback'
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.request(flow)
        assert flow.live is False

    def test_fixed_boundary(self, flow):
        """
           Given:
               - A multipart/form-data flow with a random boundary
           Then:
               - Ensure that the boundary will be replaced to 'fixed_boundary'
       """
        original_boundary = 'original_boundary'
        flow.request.headers['Content-Type'] = f'multipart/form-data; boundary={original_boundary}'
        flow.request.content = f'--{original_boundary}\nContent-Disposision: form-data; ' \
                               f'name="test"\n\nsomething\n--{original_boundary}--'.encode()
        time_stamp_replacer = TimestampReplacer()
        time_stamp_replacer.request(flow)
        assert flow.request.content == b'--fixed_boundary\nContent-Disposision: form-data; ' \
                                       b'name="test"\n\nsomething\n--fixed_boundary--'
