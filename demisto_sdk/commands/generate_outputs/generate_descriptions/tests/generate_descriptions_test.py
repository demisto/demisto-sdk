import os

import requests_mock

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_json, get_yaml

# Test data files


FAKE_INTEGRATION_YML = open(
    f'{git_path()}/demisto_sdk/commands/generate_outputs/generate_descriptions/tests/test_data/input_integration.yml', 'r').read()
FAKE_OUTPUT_AI21 = get_json(
    f'{git_path()}/demisto_sdk/commands/generate_outputs/generate_descriptions/tests/test_data/ai21_response.json')
LOGPROB_INPUT_AI21 = get_json(
    f'{git_path()}/demisto_sdk/commands/generate_outputs/generate_descriptions/tests/test_data/logprob_res.json')


def test_ai21_api_request(mocker):
    """
        Given
           - A prompt
        When
           - generating ai descriptions
        Then
           - Ensure the descriptions are generated with probability indicators
    """
    from demisto_sdk.commands.generate_outputs.generate_descriptions import \
        generate_descriptions

    mocker.patch.dict(os.environ, {'AI21_KEY': '123'})

    with requests_mock.Mocker() as m:
        # Mock get requests
        m.post('https://api.ai21.com/studio/v1/j1-large/complete',
               status_code=200, json=FAKE_OUTPUT_AI21)

        assert generate_descriptions.ai21_api_request('test', {}) == \
            'The ThreatStream Platform.'
        assert generate_descriptions.ai21_api_request('test',
                                                      {'prob_check': True}) == \
            'The ThreatStream **Platform**.'


def test_build_description_with_probabilities():
    """
        Given
          - A logprop dict
        When
          - generating probability string
        Then
          - Ensure the output is wrapped with *'s
    """
    from demisto_sdk.commands.generate_outputs.generate_descriptions import \
        generate_descriptions

    assert generate_descriptions.build_description_with_probabilities(
        LOGPROB_INPUT_AI21) == 'The **Unkown**'


def test_generate_ai_descriptions(mocker, tmp_path):
    """
      Given
         - An integration YAML without descriptions
      When
         - using generate_ai_descriptions
      Then
         - Ensure the descriptions are generated
    """
    from demisto_sdk.commands.generate_outputs.generate_descriptions import \
        generate_descriptions

    mocker.patch.dict(os.environ, {'AI21_KEY': '123'})

    input = tmp_path / "input_generate_ai_descriptions.yml"
    output = tmp_path / "output_generate_ai_descriptions.yml"
    with open(input, 'w') as f:
        f.write(FAKE_INTEGRATION_YML)

    with requests_mock.Mocker() as m:
        # Mock get requests
        m.post('https://api.ai21.com/studio/v1/j1-large/complete',
               status_code=200, json=FAKE_OUTPUT_AI21)

        generate_descriptions.generate_ai_descriptions(str(input), str(output),
                                                       interactive=False,
                                                       verbose=False)

        output_dict = get_yaml(str(output))
        for output in output_dict.get("script").get("commands")[0].get("outputs"):
            assert output.get("description") == "The ThreatStream **Platform**."
