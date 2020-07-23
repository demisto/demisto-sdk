import pytest
from demisto_sdk.commands.common.constants import (
    CODE_FILES_REGEX, PACKAGE_YML_FILE_REGEX,
    PACKS_CLASSIFIER_JSON_5_9_9_REGEX, PACKS_CLASSIFIER_JSON_REGEX,
    PACKS_DASHBOARD_JSON_REGEX, PACKS_INCIDENT_FIELD_JSON_REGEX,
    PACKS_INCIDENT_TYPE_JSON_REGEX, PACKS_INTEGRATION_NON_SPLIT_YML_REGEX,
    PACKS_INTEGRATION_PY_REGEX, PACKS_INTEGRATION_TEST_PY_REGEX,
    PACKS_INTEGRATION_YML_REGEX, PACKS_LAYOUT_JSON_REGEX,
    PACKS_LAYOUTS_CONTAINER_JSON_REGEX, PACKS_MAPPER_JSON_REGEX,
    PACKS_SCRIPT_PY_REGEX, PACKS_SCRIPT_TEST_PLAYBOOK,
    PACKS_SCRIPT_TEST_PY_REGEX, PACKS_SCRIPT_YML_REGEX,
    PACKS_WIDGET_JSON_REGEX, PLAYBOOK_README_REGEX, PLAYBOOK_YML_REGEX,
    TEST_PLAYBOOK_YML_REGEX)
from demisto_sdk.commands.common.tools import checked_type

test_packs_regex_params = [
    (['Packs/XDR/Integrations/XDR/XDR.yml', 'Packs/XDR/Scripts/Random/Random.yml'],
     ['Packs/Integrations/XDR/XDR_test.py', 'Packs/Scripts/Random/Random.py'],
     [PACKAGE_YML_FILE_REGEX]),
    (['Packs/XDR/Integrations/XDR/XDR.py'],
     ['Packs/Integrations/XDR/XDR_test.py', 'Packs/Sade/Integrations/XDR/test_yarden.py'],
     [PACKS_INTEGRATION_PY_REGEX]),
    (['Packs/XDR/Integrations/XDR/XDR.yml'], ['Packs/Integrations/XDR/XDR_test.py'], [PACKS_INTEGRATION_YML_REGEX]),
    (['Packs/Sade/Integrations/XDR/XDR_test.py'], ['Packs/Sade/Integrations/yarden.py'],
     [PACKS_INTEGRATION_TEST_PY_REGEX]),

    (['Packs/XDR/Scripts/Random/Random.yml'], ['Packs/Scripts/Random/Random.py'], [PACKS_SCRIPT_YML_REGEX]),
    (['Packs/XDR/Scripts/Random/Random.py'], ['Packs/Scripts/Random/Random_test.py'], [PACKS_SCRIPT_PY_REGEX]),
    (['Packs/XDR/Scripts/Random/Random_test.py'], ['Packs/Sade/Scripts/test_yarden.pt'], [PACKS_SCRIPT_TEST_PY_REGEX]),
    (['Packs/XDR/Playbooks/XDR.yml'], ['Packs/Playbooks/XDR/XDR_test.py'], [PLAYBOOK_YML_REGEX]),
    (['Packs/XDR/TestPlaybooks/playbook.yml'], ['Packs/TestPlaybooks/nonpb.xml'], [TEST_PLAYBOOK_YML_REGEX]),
    (['Packs/Sade/Classifiers/classifier-yarden.json'], ['Packs/Sade/Classifiers/classifier-yarden-json.txt'],
     [PACKS_CLASSIFIER_JSON_REGEX]),
    (['Packs/Sade/Classifiers/classifier-test_5_9_9.json'], ['Packs/Sade/Classifiers/classifier-test_5_9_9-json.txt'],
     [PACKS_CLASSIFIER_JSON_5_9_9_REGEX]),
    (['Packs/Sade/Classifiers/classifier-mapper-test.json'], ['Packs/Sade/Classifiers/classifier-mapper-test.txt'],
     [PACKS_MAPPER_JSON_REGEX]),
    (['Packs/Sade/Dashboards/yarden.json'], ['Packs/Sade/Dashboards/yarden-json.txt'], [PACKS_DASHBOARD_JSON_REGEX]),
    (['Packs/Sade/IncidentTypes/yarden.json'], ['Packs/Sade/IncidentTypes/yarden-json.txt'],
     [PACKS_INCIDENT_TYPE_JSON_REGEX]),
    (['Packs/Sade/Widgets/yarden.json'], ['Packs/Sade/Widgets/yarden-json.txt'], [PACKS_WIDGET_JSON_REGEX]),
    (['Packs/Sade/Layouts/yarden.json'], ['Packs/Sade/Layouts/yarden_json.yml'], [PACKS_LAYOUT_JSON_REGEX]),
    (['Packs/Sade/Layouts/layoutscontainer-test.json'], ['Packs/Sade/Layouts/yarden_json.yml'],
     [PACKS_LAYOUTS_CONTAINER_JSON_REGEX]),
    (['Packs/Sade/IncidentFields/yarden.json'], ['Packs/Sade/IncidentFields/yarden-json.txt'],
     [PACKS_INCIDENT_FIELD_JSON_REGEX]),
    (
        ['Packs/XDR/Playbooks/playbook-Test.yml', 'Packs/XDR/Playbooks/Test.yml'],
        ['Packs/XDR/Playbooks/playbook-Test_CHANGELOG.md'],
        [PLAYBOOK_YML_REGEX]
    ),
    (
        ['Packs/OpenPhish/Integrations/integration-OpenPhish.yml'],
        ['Packs/OpenPhish/Integrations/OpenPhish/OpenPhish.yml'],
        [PACKS_INTEGRATION_NON_SPLIT_YML_REGEX]
    ),
    (
        ['Packs/OpenPhish/Playbooks/playbook-Foo_README.md'],
        ['Packs/OpenPhish/Playbooks/playbook-Foo_README.yml'],
        [PLAYBOOK_README_REGEX]
    ),
    (
        ['Packs/DeveloperTools/TestPlaybooks/script-CallTableToMarkdown.yml'],
        ['Packs/DeveloperTools/TestPlaybooks/CallTableToMarkdown.yml'],
        [PACKS_SCRIPT_TEST_PLAYBOOK]
    ),
    (
        ['Packs/DeveloperTools/TestPlaybooks/CallTableToMarkdown.yml'],
        ['Packs/DeveloperTools/TestPlaybooks/script-CallTableToMarkdown.yml'],
        [TEST_PLAYBOOK_YML_REGEX]
    ),
    (
        ['Packs/SomeScript/Scripts/ScriptName/ScriptName.ps1',
         'Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName.ps1',
         'Packs/SomeScript/Scripts/ScriptName/ScriptName.py',
         'Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName.py'],
        ['Packs/SomeScript/Scripts/ScriptName/ScriptName.Tests.ps1',
         'Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName.Tests.ps1',
         'Packs/SomeScript/Scripts/ScriptName/ScriptName.yml',
         'Packs/SomeScript/Scripts/ScriptName/NotTheSameScriptName.ps1',
         'Packs/SomeIntegration/Integrations/IntegrationName/NotTheSameIntegrationName.ps1',
         'Packs/SomeScript/Scripts/ScriptName/ScriptName_test.py',
         'Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName_test.py',
         'Packs/SomeScript/Scripts/ScriptName/NotTheSameScriptName.py',
         'Packs/SomeIntegration/Integrations/IntegrationName/NotTheSameIntegrationName.py'
         ],
        CODE_FILES_REGEX
    )
]


@pytest.mark.parametrize('acceptable,non_acceptable,regex', test_packs_regex_params)
def test_packs_regex(acceptable, non_acceptable, regex):
    for test_path in acceptable:
        assert checked_type(test_path, compared_regexes=regex)

    for test_path in non_acceptable:
        assert not checked_type(test_path, compared_regexes=regex)
