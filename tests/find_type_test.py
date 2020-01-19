import pytest
from demisto_sdk.validation.type_file.find_type import *


data_test_get_dict_from_file = [
    ('tests/test_files/classifier.json', 'json'),
    ('tests/test_files/integration.yml', 'yml'),
    ('test', None),
    (None, None)
]
data_test_find_type = [
    ('tests/test_files/classifier.json', 'classifier'),
    ('tests/test_files/dashboard.json', 'dashboard'),
    ('tests/test_files/incidentfield.json', 'incidentfield'),
    ('tests/test_files/incidenttype.json', 'incidenttype'),
    ('tests/test_files/indicatorfield.json', 'indicatorfield'),
    ('tests/test_files/integration.yml', 'integration'),
    ('tests/test_files/layout.json', 'layout'),
    ('tests/test_files/playbook.yml', 'playbook'),
    ('tests/test_files/report.json', 'report'),
    ('tests/test_files/reputation.json', 'reputation'),
    ('tests/test_files/script.yml', 'script'),
    ('tests/test_files/widget.json', 'widget'),
    ('tests/test_files/test', None),
    ('', None)
]


@pytest.mark.parametrize('path, _type', data_test_get_dict_from_file)
def test_get_dict_from_file(path, _type):
    output = get_dict_from_file(str(path))[1]
    assert output == _type, f'get_dict_from_file({_input}) returns: {output} instead {expected}'


@pytest.mark.parametrize('path, _type', data_test_find_type)
def test_find_type(path, _type):
    output = find_type(str(path))
    assert output == _type, f'find_type({_input}) returns: {output} instead {expected}'
