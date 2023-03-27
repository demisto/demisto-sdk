import ruamel.yaml as yaml

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)

GIT_ROOT = git_path()


def test_marketplace_version_is_xsiam():
    """
    Given:
        - A playbook which contains in its second task description the word incident, and in its third task name and
         description the word <-incident->. Also in the external description, contains three times the word incident.
        - MarketplaceVersions.MarketplaceV2 (Which is XSIAM Marketplace version)
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed
    Then:
        - Ensure incident is converted to alert when needed.
        - Ensure the wrapper is removed.
    """

    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_1.yml"
    ) as yml_file:
        data = yaml.safe_load(yml_file)

    data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
        data, MarketplaceVersions.MarketplaceV2
    )

    # convert incident to alert for XSIAM
    assert (
        data["tasks"]["2"]["task"]["description"]
        == "Assign the alert to an analyst based on the analyst's organizational role."
    )
    assert (
        data["description"]
        == "Use this playbook to investigate and remediate a potential phishing alert."
        " The playbook simultaneously engages with the user that triggered the alert,"
        " while investigating the alert itself."
    )

    # remove the wrapper for any Marketplace
    assert data["tasks"]["7"]["task"]["name"] == "Manually review the incident"
    assert (
        data["tasks"]["7"]["task"]["description"]
        == "Review the incident to determine if the email that the user reported is malicious."
    )


def test_marketplace_version_is_xsiam_2():
    """
    Given:
        - A playbook which contains in the external description, contains five times the word incident/s with or without
         the wrapper.
        - MarketplaceVersions.MarketplaceV2 (Which is XSIAM Marketplace version)
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed
    Then:
        - Ensure incident is converted to alert when needed.
        - Ensure the wrapper is removed.
    """

    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_2.yml"
    ) as yml_file:
        data = yaml.safe_load(yml_file)

    data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
        data, MarketplaceVersions.MarketplaceV2
    )

    # convert incident/s to alert/s for XSIAM when needed and remove the wrapper without replacing to alert/s
    assert data["description"] ==\
           "Use this playbook to investigate and remediate a potential phishing alert." \
           " The playbook simultaneously engages with the user that triggered the alert," \
           " while investigating the alert itself. Alerts incidents"


def test_marketplace_version_is_xsoar():
    """
    Given:
        - A playbook which contains in its second task description the word incident, and in its third task name and
         description the word <-incident->. Also in the external description, contains three times the word incident.
        - MarketplaceVersions.XSOAR
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed
    Then:
        - Ensure incident is unconverted to alert since XSOAR Marketplace is given.
        - Ensure the wrapper is removed.
    """

    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_1.yml"
    ) as yml_file:
        data = yaml.safe_load(yml_file)

    data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(data)

    # Verify that an incident is not converted to an alert when it is not in XSIAM Marketplace
    assert (
        data["tasks"]["2"]["task"]["description"]
        == "Assign the incident to an analyst based on the analyst's organizational role."
    )
    assert (
        data["description"]
        == "Use this playbook to investigate and remediate a potential phishing incident."
        " The playbook simultaneously engages with the user that triggered the incident,"
        " while investigating the incident itself."
    )

    # remove the wrapper for any Marketplace
    assert data["tasks"]["7"]["task"]["name"] == "Manually review the incident"

    assert (
        data["tasks"]["7"]["task"]["description"]
        == "Review the incident to determine if the email that the user reported is malicious."
    )
