import json
import os

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.unify.xdrc_template_unifier import \
    XDRCTemplateUnifier

TESTS_DIR = f'{git_path()}/demisto_sdk/tests'


def test_unify_xdrc_template():
    """
    Given
    - Dummy XDRC Template.
    - No output path.

    When
    - Running Unify on it.

    Then
    - Ensure Unify xdrc template works
    """
    input_path = TESTS_DIR + '/test_files/Packs/DummyPack/XDRCTemplates/DummyXDRCTemplate'
    output_path = TESTS_DIR + '/test_files/Packs/DummyPack/XDRCTemplates/'

    unifier = XDRCTemplateUnifier(input=input_path, output=output_path)
    json_files = unifier.unify()

    expected_json_path = TESTS_DIR + '/test_files/Packs/DummyPack/XDRCTemplates/external-xdrctemplate-DummyXDRCTemplate.json'
    export_json_path = json_files[0]

    assert export_json_path == expected_json_path

    expected_json_file = {'content_global_id': '1',
                          'name': 'Dummmy',
                          'os_type': 'AGENT_OS_LINUX',
                          'profile_type': 'STANDARD',
                          'yaml_template': 'dGVzdDogZHVtbXlfdGVzdA=='}
    with open(expected_json_path, 'r') as real_file:
        assert expected_json_file == json.load(real_file)

    os.remove(expected_json_path)
