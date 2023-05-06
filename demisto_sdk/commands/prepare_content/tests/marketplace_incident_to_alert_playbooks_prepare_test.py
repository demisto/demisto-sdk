import ruamel.yaml as yaml
from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.content_graph_commands import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_pack,
    mock_relationship,
    mock_script,
    mock_playbook
)
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)

GIT_ROOT = git_path()


@pytest.fixture
def repository(mocker):
    repository = ContentDTO(
        path=Path(),
        packs=[],
    )
    mocker.patch(
        "demisto_sdk.commands.content_graph.content_graph_builder.ContentGraphBuilder._create_content_dto",
        return_value=repository,
    )
    return repository


def create_mini_content(repository: ContentDTO):

    relationships = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "playbook_1",
                ContentType.PLAYBOOK,
                "TestPack",
                ContentType.PACK,
            )
        ],
        RelationshipType.USES_BY_ID: [
            mock_relationship(
                "playbook_1",
                ContentType.PLAYBOOK,
                "getIncident",
                ContentType.SCRIPT,
                mandatorily=True,
            ),
            mock_relationship(
                "playbook_1",
                ContentType.PLAYBOOK,
                "setIncidentByID",
                ContentType.SCRIPT,
                mandatorily=True,
            )
        ],
    }
    relationships2 = {
        RelationshipType.IN_PACK: [
            mock_relationship(
                "setIncidentByID",
                ContentType.PLAYBOOK,
                "TestPack2",
                ContentType.PACK,
            ),
            mock_relationship(
                "getIncident",
                ContentType.PLAYBOOK,
                "TestPack2",
                ContentType.PACK,
            )
        ]
    }
    pack1 = mock_pack("TestPack")
    pack2 = mock_pack("TestPack2")
    pack1.relationships = relationships
    pack2.relationships = relationships2
    pack1.content_items.playbook.append(
        mock_playbook(
            name="playbook_1",
        )
    )
    pack2.content_items.script.append(
        mock_script(
            "getIncident",
            skip_prepare=['script-name-incident-to-alert'],
        )
    )
    pack2.content_items.script.append(
        mock_script(
            "setIncidentByID",
        )
    )
    repository.packs.extend([pack1, pack2])


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

    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_1.yml"
    ) as yml_file:
        data = yaml.safe_load(yml_file)

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
        - Ensure the access fields did NOT change as the playbook is supported only in MarketplaceVersions.MarketplaceV2.
    """

    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_2.yml"
    ) as yml_file:
        data = yaml.safe_load(yml_file)

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

    # assert access fields did NOT change as this playbook is supported only in XSAIM and not both marketplaces
    assert data["tasks"]["3"]["task"]["script"] == "Builtin|||setIncident"
    assert (
        data["tasks"]["3"]["task"]["scriptarguments"]["id"]["complex"]["root"]
        == "incident"
    )


def test_marketplace_version_is_xsiam_3(repository: ContentDTO):
    """
    Given:
        - A playbook which contains scripts that names include incident/s.
        - One script is set as `skipPrepare` and a second script is not set as skip.
    When:
        - MarketplaceIncidentToAlertPlaybooksPreparer.prepare() command is executed

    Then:
        - Ensure that only a script that is not set as skip has changed from incident to alert.
    """
    create_mini_content(repository)
    with ContentGraphInterface() as interface:
        create_content_graph(interface)
        playbooks = interface.search(
            content_type=ContentType.PLAYBOOK
        )

        with open(
            f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_2.yml"
        ) as yml_file:
            data = yaml.safe_load(yml_file)

        data = MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
            playbook=playbooks[0],
            data=data,
            current_marketplace=MarketplaceVersions.MarketplaceV2,
            supported_marketplaces=[
                MarketplaceVersions.XSOAR,
                MarketplaceVersions.MarketplaceV2,
            ],
        )

    assert data["tasks"]["6"]["task"]["scriptName"] == "getIncident"
    assert data["tasks"]["7"]["task"]["scriptName"] == "setAlertByID"


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

    with open(
        f"{GIT_ROOT}/demisto_sdk/commands/prepare_content/test_files/playbook_1.yml"
    ) as yml_file:
        data = yaml.safe_load(yml_file)

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
