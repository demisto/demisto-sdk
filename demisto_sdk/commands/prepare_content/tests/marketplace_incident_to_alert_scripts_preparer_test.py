import ruamel.yaml as yaml

from TestSuite.script import Script
from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_scripts_prepare import (
    MarketplaceIncidentToAlertScriptsPreparer,
)


GIT_ROOT = git_path()


def create_script_for_test(tmp_path, repo):

    script = Script(
        tmpdir=tmp_path,
        name='script_incident_to_alert',
        repo=repo,
        create_unified=True
        )
    script.create_default_script(name='setIncident')
    return script


def test_marketplace_version_is_xsiam(tmp_path, repo):
    """
    Given:
        - A playbook which contains in its second task description the word incident, and in its third task name and
         description the word <-incident->. Also in the external description, contains three times the word incident.
         Additionally, multiple access fields that should be replaced from incident to alert.
        - MarketplaceVersions.MarketplaceV2 as the current marketplace.
        - [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2] as the supported marketplaces for this playbook.

        supported marketplaces for this playbook are the default ones.
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed
    Then:
        - Ensure incident is converted to alert when needed.
        - Ensure the wrapper is removed.
        - Ensure that the required fields have changed from incident to alert.
    """

    data = create_script_for_test(tmp_path, repo).yml.read_dict()

    data = MarketplaceIncidentToAlertScriptsPreparer.prepare(
        data,
        current_marketplace=MarketplaceVersions.MarketplaceV2,
        incident_to_alert=True,
    )

    assert isinstance(data, tuple)

    assert (
        data[0].get('name') == 'setIncident'
        and data[1].get('name') == 'setAlert'
    )
    return


def test_marketplace_version_is_xsoar():
    """
    Given:
        - A playbook which contains in its second task description the word incident, and in its third task name and
         description the word <-incident->. Also in the external description, contains three times the word incident.
         Additionally, multiple access fields that should be replaced from incident to alert.
        - MarketplaceVersions.MarketplaceV2 as the current marketplace.
        - [MarketplaceVersions.XSOAR, MarketplaceVersions.MarketplaceV2] as the supported marketplaces for this playbook.

        supported marketplaces for this playbook are the default ones.
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed
    Then:
        - Ensure incident is converted to alert when needed.
        - Ensure the wrapper is removed.
        - Ensure that the required fields have changed from incident to alert.
    """

    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/script_1.yml"
    ) as yml_file:
        data = yaml.safe_load(yml_file)

    data = MarketplaceIncidentToAlertScriptsPreparer.prepare(
        data,
        current_marketplace=MarketplaceVersions.MarketplaceV2,
        incident_to_alert=False,
    )

    assert (
        
    )