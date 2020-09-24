import json

from click.testing import CliRunner
from demisto_sdk.__main__ import main

CMD = 'response-to-mapping-fields'


def create_file_from_obj(tmp_path, obj):
    tmp_file_path = tmp_path / 'js.json'
    tmp_file_path.write_text(json.dumps(obj))
    return tmp_file_path


def output_path(tmp_path):
    return tmp_path / 'js_out.json'


def test_in_out(tmp_path):
    path = create_file_from_obj(tmp_path, {'input': 1})
    output = output_path(tmp_path)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [CMD, '-i', path, '-o', output])
    assert {'input': 'int'} == json.load(open(output))
    assert 0 == result.exit_code
    assert 'A JSON scheme was written to' in result.stdout
    assert '' in result.stderr


def test_in_no_out(tmp_path):
    path = create_file_from_obj(tmp_path, {'input': 1})
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [CMD, '-i', path])
    assert 0 == result.exit_code
    assert 'A JSON scheme was written to' in result.stdout
    assert '' in result.stderr


def test_non_existing_file():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [CMD, '-i', 'none/existing/path'])
    result.exit_code == 1
