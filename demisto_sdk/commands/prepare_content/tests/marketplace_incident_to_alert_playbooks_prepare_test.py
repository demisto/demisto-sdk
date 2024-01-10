from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_playbook,
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)

GIT_ROOT = git_path()


def test_marketplace_version_is_xsiam():
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

    data = get_yaml(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_1.yml"
    )

    playbook_dummy = mock_playbook(
        name="playbook_1",
    )

    data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
        playbook_dummy,
        data,
        current_marketplace=MarketplaceVersions.MarketplaceV2,
        supported_marketplaces=[
            MarketplaceVersions.XSOAR,
            MarketplaceVersions.MarketplaceV2,
        ],
    )

    # convert incident to alert for XSIAM in descriptions
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

    # assert fields changed from incident to alert
    assert data["tasks"]["3"]["task"]["script"] == "Builtin|||setAlert"
    assert (
        data["tasks"]["3"]["task"]["scriptarguments"]["id"]["complex"]["root"]
        == "alert"
    )
    assert data["tasks"]["6"]["message"]["body"]["simple"] == "${alert.id}"
    assert data["tasks"]["3"]["scriptarguments"]["type"]["simple"] == "alert"
    assert (
        data["tasks"]["2"]["scriptarguments"]["message"]["simple"]
        == "*RRN*: ${alert.rrn}\n\n\n*Findings:*\n```\n${.=JSON.stringify(val.incident.prismacloudfindingsresults,"
        "null,2)}\n```\n\n*IAM Permissions*:\n``` \n${.=JSON.stringify(val.incident.prismacloudiamresults,null,"
        "2)}\n```\n"
    )

    # assert fields did NOT change from incident to alert
    assert (
        data["tasks"]["3"]["scriptarguments"]["IncidentIDs"]["complex"]["root"]
        == "EmailCampaign.incidents"
    )
    assert data["outputs"][0]["contextPath"] == "incident.fieldname"


def test_marketplace_version_is_xsiam_2():
    """
    Given:
        - A playbook which contains the word incident/s (with or without a wrapper) in the external description five times.
        - MarketplaceVersions.MarketplaceV2 (Which is XSIAM Marketplace version) as the current marketplace.
        - MarketplaceVersions.MarketplaceV2 as the supported marketplaces for this playbook.
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed
    Then:
        - Ensure incident is converted to alert when needed.
        - Ensure the wrapper is removed.
        - Ensure the access fields have changed even when the playbook is only supported in MarketplaceVersions.MarketplaceV2.
    """

    data = get_yaml(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_2.yml"
    )

    playbook_dummy = mock_playbook(
        name="playbook_1",
    )

    data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
        playbook_dummy,
        data,
        current_marketplace=MarketplaceVersions.MarketplaceV2,
        supported_marketplaces=[MarketplaceVersions.MarketplaceV2],
    )

    # convert incident/s to alert/s for XSIAM when needed and remove the wrapper without replacing to alert/s
    assert (
        data["description"]
        == "Use this playbook to investigate and remediate a potential phishing alert."
        " The playbook simultaneously engages with the user that triggered the alert,"
        " while investigating the alert itself. Alerts incidents"
    )

    # assert access fields have changed even as this playbook is supported only in XSAIM and not both marketplaces
    assert data["tasks"]["3"]["task"]["script"] == "Builtin|||setAlert"
    assert (
        data["tasks"]["3"]["task"]["scriptarguments"]["id"]["complex"]["root"]
        == "alert"
    )


def test_marketplace_version_is_xsoar():
    """
    Given:
        - A playbook which contains in its second task description the word incident, and in its third task name and
         description the word <-incident->. Also in the external description, contains three times the word incident.
        - MarketplaceVersions.XSOAR as the current marketplace.
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed
    Then:
        - Ensure incident is unconverted to alert since XSOAR Marketplace is given.
        - Ensure the wrapper is removed.
        - Ensure that access fields did NOT change from incident to alert as this playbook is in XSOAR.
    """

    data = get_yaml(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_3.yml"
    )

    playbook_dummy = mock_playbook(
        name="playbook_1",
    )
    data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(playbook_dummy, data)

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

    # assert fields did NOT change from incident to alert
    assert data["tasks"]["3"]["task"]["script"] == "Builtin|||setIncident"
    assert (
        data["tasks"]["3"]["task"]["scriptarguments"]["id"]["complex"]["root"]
        == "incident"
    )
    assert data["tasks"]["6"]["message"]["body"]["simple"] == "${incident.id}"
    assert data["tasks"]["3"]["scriptarguments"]["type"]["simple"] == "incident"
