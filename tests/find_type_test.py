import pytest
from demisto_sdk.validation.type_file.find_type import *


data_test_get_dict_from_file = [
    ('test_files/classifier.json', 'json'),
    ('test_files/integration.yml', 'yml'),
    ('test', None),
    (None, None)
]
data_test_find_type = [
    ('test_files/classifier.json', 'classifier'),
    ('test_files/dashboard.json', 'dashboard'),
    ('test_files/incidentfield.json', 'incidentfield'),
    ('test_files/incidenttype.json', 'incidenttype'),
    ('test_files/indicatorfield.json', 'indicatorfield'),
    ('test_files/integration.yml', 'integration'),
    ('test_files/layout.json', 'layout'),
    ('test_files/playbook.yml', 'playbook'),
    ('test_files/report.json', 'report'),
    ('test_files/reputation.json', 'reputation'),
    ('test_files/script.yml', 'script'),
    ('test_files/widget.json', 'widget'),
    ('test_files/test', None),
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
