import pytest
from demisto_sdk.commands.common.constants import (
    PACKAGE_YML_FILE_REGEX, PACKS_CHANGELOG_REGEX, PACKS_CLASSIFIERS_REGEX,
    PACKS_DASHBOARDS_REGEX, PACKS_INCIDENT_FIELDS_REGEX,
    PACKS_INCIDENT_TYPES_REGEX, PACKS_INTEGRATION_PY_REGEX,
    PACKS_INTEGRATION_TEST_PY_REGEX, PACKS_INTEGRATION_YML_REGEX,
    PACKS_LAYOUTS_REGEX, PACKS_PACKAGE_META_REGEX, PACKS_PLAYBOOK_YML_REGEX,
    PACKS_SCRIPT_PY_REGEX, PACKS_SCRIPT_TEST_PY_REGEX, PACKS_SCRIPT_YML_REGEX,
    PACKS_TEST_PLAYBOOKS_REGEX, PACKS_WIDGETS_REGEX)
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
    (['Packs/XDR/Playbooks/XDR.yml'], ['Packs/Playbooks/XDR/XDR_test.py'], [PACKS_PLAYBOOK_YML_REGEX]),
    (['Packs/XDR/TestPlaybooks/playbook.yml'], ['Packs/TestPlaybooks/nonpb.xml'], [PACKS_TEST_PLAYBOOKS_REGEX]),
    (['Packs/Sade/Classifiers/yarden.json'], ['Packs/Sade/Classifiers/yarden-json.txt'], [PACKS_CLASSIFIERS_REGEX]),
    (['Packs/Sade/Dashboards/yarden.json'], ['Packs/Sade/Dashboards/yarden-json.txt'], [PACKS_DASHBOARDS_REGEX]),
    (['Packs/Sade/IncidentTypes/yarden.json'], ['Packs/Sade/IncidentTypes/yarden-json.txt'],
     [PACKS_INCIDENT_TYPES_REGEX]),
    (['Packs/Sade/Widgets/yarden.json'], ['Packs/Sade/Widgets/yarden-json.txt'], [PACKS_WIDGETS_REGEX]),
    (['Packs/Sade/Layouts/yarden.json'], ['Packs/Sade/Layouts/yarden_json.yml'], [PACKS_LAYOUTS_REGEX]),
    (['Packs/Sade/package-meta.json'], ['Packs/Sade/Dashboards/yarden-json.txt'], [PACKS_PACKAGE_META_REGEX]),
    (['Packs/XDR/CHANGELOG.md'], ['Packs/Integrations/XDR/CHANGELOG.md'], [PACKS_CHANGELOG_REGEX]),
    (['Packs/Sade/IncidentFields/yarden.json'], ['Packs/Sade/IncidentFields/yarden-json.txt'],
     [PACKS_INCIDENT_FIELDS_REGEX]),
]


@pytest.mark.parametrize('acceptable,non_acceptable,regex', test_packs_regex_params)
def test_packs_regex(acceptable, non_acceptable, regex):
    for test_path in acceptable:
        assert checked_type(test_path, compared_regexes=regex)

    for test_path in non_acceptable:
        assert not checked_type(test_path, compared_regexes=regex)
