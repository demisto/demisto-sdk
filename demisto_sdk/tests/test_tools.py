import json
from functools import partial
from pathlib import Path
from typing import Callable

import pytest
import yaml
from _pytest import tmpdir
from demisto_sdk.commands.common.tools import get_content_file_type_dump


def create_temp_file(tmp_path: tmpdir.tmp_path, file_content: str, filename: str = 'file.txt') -> str:
    """ Creates a temporary file with contents

    Args:
        tmp_path: tmp_path object
        file_content: Contents of a file
        filename: name of the file (default `file.txt`)

    Returns:
        path to the temporary file
    """
    file_like = tmp_path / filename
    file_like.write_text(file_content)
    return str(Path(file_like))


CONTENT_PARSER_INPUT = [
    ('file_path.yml', yaml.dump),
    ('file_path.yaml', yaml.dump),
    ('file_path.json', partial(json.dumps, indent=4)),
    ('file_path.other', str)
]


@pytest.mark.parametrize('file_path, expected', CONTENT_PARSER_INPUT)
def test_get_content_file_type_dump(file_path: str, expected: Callable[[str], str]):
    """
        Given
        - A file path

        When
        - Running the method 'get_content_file_type_dump' on it

        Then
        -  Ensure the method is 'json.dumps' if the file is a json file
        -  Ensure the method is 'yaml.dump' if the file is a yml file
        -  Ensure the method is 'str' if the file is any other unknown type
    """
    assert get_content_file_type_dump(file_path) == expected or \
        get_content_file_type_dump(file_path).func == expected.func
