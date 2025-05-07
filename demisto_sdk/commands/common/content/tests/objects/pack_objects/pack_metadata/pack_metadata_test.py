from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from shutil import rmtree

import pytest
from more_itertools import one
from packaging.version import parse
from pytest import MonkeyPatch

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    PACKS_DIR,
    XSOAR_AUTHOR,
    XSOAR_SUPPORT,
    XSOAR_SUPPORT_URL,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content.objects.pack_objects import PackMetaData
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.docker.docker_image import DockerImage
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.content_graph.common import (
    ContentType,
)
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.pack_content_items import (
    PackContentItems,
)
from demisto_sdk.commands.content_graph.objects.pack_metadata import PackMetadata
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_integration,
)
from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from TestSuite.test_tools import ChangeCWD

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
PACK_METADATA = TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / "pack_metadata.json"
UNIT_TEST_DATA = src_root() / "commands" / "create_artifacts" / "tests" / "data"


@contextmanager
def temp_dir():
    """Create Temp directory for test.

     Open:
        - Create temp directory.

    Close:
        - Delete temp directory.
    """
    temp = UNIT_TEST_DATA / "temp"
    try:
        temp.mkdir(parents=True, exist_ok=True)
        yield temp
    finally:
        rmtree(temp)


def test_objects_factory():
    obj = path_to_pack_object(PACK_METADATA)
    assert isinstance(obj, PackMetaData)


def test_prefix():
    obj = PackMetaData(PACK_METADATA)
    assert obj.normalize_file_name() == PACK_METADATA.name


def test_created_setter_bad_string_data():
    obj = PackMetaData(PACK_METADATA)
    original_created_date = obj.created

    obj.created = "Obviously not a date"

    assert obj.created == original_created_date


def test_created_setter_datetime():
    obj = PackMetaData(PACK_METADATA)

    new_date_time = datetime(2020, 12, 31, 23, 59, 59)

    obj.created = new_date_time

    assert obj.created == new_date_time


def test_updated_setter_bad_string_data():
    obj = PackMetaData(PACK_METADATA)
    original_updated_date = obj.updated

    obj.updated = "Obviously not a date"

    assert obj.updated == original_updated_date


def test_updated_setter_datetime():
    obj = PackMetaData(PACK_METADATA)

    new_date_time = datetime(2020, 12, 31, 23, 59, 59)

    obj.updated = new_date_time

    assert obj.updated == new_date_time


def test_legacy_setter():
    obj = PackMetaData(PACK_METADATA)

    obj.legacy = False
    assert not obj.legacy

    obj.legacy = True
    assert obj.legacy


@pytest.mark.parametrize(
    "url, support, email, expected_url, expected_email",
    [
        ("some url", "xsoar", "some email", "some url", "some email"),
        (None, "xsoar", "some email", XSOAR_SUPPORT_URL, "some email"),
        (None, "Partner", None, None, None),
    ],
)
def test_support_details_getter(url, support, email, expected_url, expected_email):
    obj = PackMetaData(PACK_METADATA)
    obj.url = url
    obj.support = support
    obj.email = email

    support_details = obj.support_details

    assert expected_url == support_details.get("url")
    assert expected_email == support_details.get("email")


@pytest.mark.parametrize(
    "support, author, expected_author, expected_log",
    [
        (XSOAR_SUPPORT, XSOAR_AUTHOR, XSOAR_AUTHOR, None),
        ("someone", "someone", "someone", None),
        (
            XSOAR_SUPPORT,
            "someone",
            "someone",
            f"someone author doest not match {XSOAR_AUTHOR} default value",
        ),
    ],
)
def test_author_getter(caplog, mocker, support, author, expected_author, expected_log):
    obj = PackMetaData(PACK_METADATA)
    obj.support = support
    obj.author = author

    assert obj.author == expected_author

    if expected_log:
        record = one(caplog.records)
        assert record.levelname == "WARNING"
        assert (
            record.message
            == "someone author doest not match Cortex XSOAR default value"
        )


@pytest.mark.parametrize(
    "new_price, expected_price", [(10, 10), ("10", 10), ("not int", 0)]
)
def test_price_setter_bad_int(new_price, expected_price):
    obj = PackMetaData(PACK_METADATA)

    obj.price = new_price

    assert obj.price == expected_price


def test_dump_with_price(mocker):
    def mock_json_dump(file_content, metadata_file, indent, sort_keys):
        assert file_content["premium"] is not None
        assert file_content["vendorId"]
        assert file_content["vendorName"]

    import builtins

    from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json

    obj = PackMetaData(PACK_METADATA)
    obj.price = 1
    obj.premium = True
    obj.vendor_id = "id"
    obj.vendor_name = "name"

    mocker.patch.object(builtins, "open", autospec=True)
    mocker.patch.object(json, "dump", side_effect=mock_json_dump)

    obj.dump_metadata_file("metadata_file")


def test_load_user_metadata_basic(repo):
    """
    When:
        - Dumping a specific pack, processing the pack's metadata.

    Given:
        - Pack object.

    Then:
        - Verify that pack's metadata information was loaded successfully.

    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager,
    )

    pack_1 = repo.setup_one_pack("Pack1")
    pack_1.pack_metadata.write_json(
        {
            "name": "Pack Number 1",
            "description": "A description for the pack",
            "created": "2020-06-08T15:37:54Z",
            "price": 0,
            "support": "xsoar",
            "url": "some url",
            "email": "some email",
            "currentVersion": "1.1.1",
            "author": "Cortex XSOAR",
            "tags": ["tag1"],
            "dependencies": [{"dependency": {"dependency": "1"}}],
        }
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(
                artifacts_path=temp,
                content_version="6.0.0",
                zip=False,
                suffix="",
                cpus=1,
                packs=True,
            )

    pack_1_metadata = artifact_manager.content.packs["Pack1"].metadata
    pack_1_metadata.load_user_metadata("Pack1", "Pack Number 1", pack_1.path)

    assert pack_1_metadata.id == "Pack1"
    assert pack_1_metadata.name == "Pack Number 1"
    assert pack_1_metadata.description == "A description for the pack"
    assert pack_1_metadata.created == datetime(2020, 6, 8, 15, 37, 54)
    assert pack_1_metadata.price == 0
    assert pack_1_metadata.support == "xsoar"
    assert pack_1_metadata.url == "some url"
    assert pack_1_metadata.email == "some email"
    assert pack_1_metadata.certification == "certified"
    assert pack_1_metadata.current_version == parse("1.1.1")
    assert pack_1_metadata.author == "Cortex XSOAR"
    assert pack_1_metadata.tags == ["tag1"]
    assert pack_1_metadata.dependencies == [{"dependency": {"dependency": "1"}}]


def test_load_user_metadata_advanced(repo):
    """
    When:
        - Dumping a specific pack, processing the pack's metadata.

    Given:
        - Pack object.

    Then:
        - Verify that pack's metadata information was loaded successfully.

    """
    from demisto_sdk.commands.create_artifacts.content_artifacts_creator import (
        ArtifactsManager,
    )

    pack_1 = repo.setup_one_pack("Pack1")
    pack_1.pack_metadata.write_json(
        {
            "name": "Pack Number 1",
            "price": 10,
            "tags": ["tag1"],
            "useCases": ["usecase1"],
            "vendorId": "vendorId",
            "vendorName": "vendorName",
        }
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            artifact_manager = ArtifactsManager(
                artifacts_path=temp,
                content_version="6.0.0",
                zip=False,
                suffix="",
                cpus=1,
                packs=True,
            )

    pack_1_metadata = artifact_manager.content.packs["Pack1"].metadata
    pack_1_metadata.load_user_metadata("Pack1", "Pack Number 1", pack_1.path)

    assert pack_1_metadata.id == "Pack1"
    assert pack_1_metadata.name == "Pack Number 1"
    assert pack_1_metadata.price == 10
    assert pack_1_metadata.vendor_id == "vendorId"
    assert pack_1_metadata.vendor_name == "vendorName"
    assert pack_1_metadata.tags == ["tag1", "Use Case"]


def test_load_user_metadata_no_metadata_file(caplog, repo, mocker, monkeypatch):
    """
    When:
        - Dumping a pack with no pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.
    """
    caplog.set_level("ERROR")
    pack_1 = repo.setup_one_pack("Pack1")
    pack_1.pack_metadata.write_json(
        {
            "name": "Pack Number 1",
            "price": "price",
            "tags": ["tag1"],
            "useCases": ["usecase1"],
            "vendorId": "vendorId",
            "vendorName": "vendorName",
        }
    )
    Path(pack_1.pack_metadata.path).unlink()

    content_object_pack = Pack(pack_1.path)
    pack_1_metadata = content_object_pack.metadata
    pack_1_metadata.load_user_metadata("Pack1", "Pack Number 1", pack_1.path)
    assert "Pack Number 1 pack is missing pack_metadata.json file." in caplog.text


def test_load_user_metadata_invalid_price(caplog, repo, mocker, monkeypatch):
    """
    When:
        - Dumping a pack with invalid price in pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """
    caplog.set_level("ERROR")
    pack_1 = repo.setup_one_pack("Pack1")
    pack_1.pack_metadata.write_json(
        {
            "name": "Pack Number 1",
            "price": "price",
            "tags": ["tag1"],
            "useCases": ["usecase1"],
            "vendorId": "vendorId",
            "vendorName": "vendorName",
        }
    )

    content_object_pack = Pack(pack_1.path)
    pack_1_metadata = content_object_pack.metadata
    pack_1_metadata.load_user_metadata("Pack1", "Pack Number 1", pack_1.path)

    assert (
        "Pack Number 1 pack price is not valid. The price was set to 0." in caplog.text
    )


def test_load_user_metadata_bad_pack_metadata_file(caplog, repo, mocker, monkeypatch):
    """
    When:
        - Dumping a pack with invalid pack_metadata file.

    Given:
        - Pack object.

    Then:
        - Verify that exceptions are written to the logger.

    """

    pack_1 = repo.setup_one_pack("Pack1")
    pack_1.pack_metadata.write_as_text("Invalid of course {")
    content_object_pack = Pack(pack_1.path)

    pack_1_metadata = content_object_pack.metadata
    pack_1_metadata.load_user_metadata("Pack1", "Pack Number 1", pack_1.path)

    assert "Failed loading Pack Number 1 user metadata." in caplog.text


@pytest.mark.parametrize("is_external, expected", [(True, ""), (False, "123")])
def test__enhance_pack_properties__internal_and_external(
    mocker, is_external, expected, monkeypatch: MonkeyPatch
):
    """Tests the _enhance_pack_properties method for internal and external packs.
    Given:
        - Pack object.
    When:
        - Calling the _enhance_pack_properties method.
    Then:
        - Verify that the version_info is set correctly.
        Scenario 1: When the pack is external than the version_info should be empty.
        Scenario 2: When the pack is internal than the version_info should be set to the CI_PIPELINE_ID env variable.
    """
    my_instance = PackMetadata(
        name="test",
        display_name="",
        description="",
        created="",
        legacy=False,
        support="",
        url="",
        email="",
        eulaLink="",
        price=0,
        hidden=False,
        commit="",
        downloads=0,
        keywords=[],
        searchRank=0,
        excludedDependencies=[],
        videos=[],
        modules=[],
    )  # type: ignore
    mocker.patch(
        "demisto_sdk.commands.content_graph.objects.pack_metadata.is_external_repository",
        return_value=is_external,
    )
    monkeypatch.setenv("CI_PIPELINE_ID", "123")
    my_instance._enhance_pack_properties(
        marketplace=MarketplaceVersions.XSOAR,
        pack_id="9",
        content_items=PackContentItems(),  # type: ignore
    )
    assert my_instance.version_info == expected


@pytest.mark.parametrize(
    "marketplace_version, current_fromversion, new_fromversion, current_toversion, new_toversion, expected_toversion",
    [
        (MarketplaceVersions.XSOAR, "5.5.0", "8.0.0", "7.9.9", "8.2.0", "7.9.9"),
        (MarketplaceVersions.XSOAR, "5.5.0", "6.5.0", "7.2.0", "7.9.9", "7.9.9"),
        (
            MarketplaceVersions.XSOAR,
            "5.5.0",
            "6.5.0",
            "7.9.9",
            DEFAULT_CONTENT_ITEM_TO_VERSION,
            "",
        ),
        (MarketplaceVersions.XSOAR_SAAS, "5.5.0", "8.0.0", "6.2.0", "8.5.0", "8.5.0"),
    ],
)
def test_replace_item_if_has_higher_toversion(
    marketplace_version,
    current_fromversion,
    new_fromversion,
    current_toversion,
    new_toversion,
    expected_toversion,
):
    """Tests the _replace_item_if_has_higher_toversion
    updates to the highest version supported by the MarketplaceVersions.XSOAR
    ARGS:
        marketplace_version: MarketplaceVersions the flow is running on.
        current_fromversion: current fromversion of content item in the pack metadata
        new_fromversion: the fromversion of content item in the pack metadata
        current_toversion: current toversion of content item in the pack metadata
        new_toversion: a new toversion of content item
        expected_toversion
    Given:
        - a Pack Metadata and an integration uploading to MarketplaceVersions.XSOAR
    When:
        - Calling the _replace_item_if_has_higher_toversion method.
    Then:
        - Verify that the content_item_metadata toversion is set correctly.
        Scenario 1: On MarketplaceVersions.XSOAR should not update the metadata to a version higher than 7.9.9
        Scenario 2: On MarketplaceVersions.XSOAR should update to higher version while still lower than the max 7.9.9
        Scenario 3: On all marketplaces will update the metdata of content item toversion to empty if new toversion is DEFAULT_CONTENT_ITEM_TO_VERSION
        Scenario 4: On MarketplaceVersions.XSOAR_SAAS should update metadata to the highest version.
    """
    content_item_metadata = {
        "fromversion": current_fromversion,
        "toversion": current_toversion,
    }
    marketplace = marketplace_version
    my_instance = PackMetadata(
        name="test",
        display_name="",
        description="",
        created="",
        legacy=False,
        support="",
        url="",
        email="",
        eulaLink="",
        price=0,
        hidden=False,
        commit="",
        downloads=0,
        keywords=[],
        searchRank=0,
        excludedDependencies=[],
        videos=[],
        modules=[],
    )  # type: ignore
    integration = mock_integration()
    integration.toversion = new_toversion
    integration.fromversion = new_fromversion
    my_instance._replace_item_if_has_higher_toversion(
        integration, content_item_metadata, integration.summary(), marketplace
    )
    assert content_item_metadata["toversion"] == expected_toversion


def mock_integration_for_data_source(
    name,
    display_name,
    is_fetch=False,
    is_fetch_events=False,
    is_remote_sync_in=False,
    is_fetch_samples=False,
    is_feed=False,
    deprecated=False,
    marketplaces=MarketplaceVersions.MarketplaceV2,
    path=Path("Packs"),
):
    if not isinstance(marketplaces, list):
        marketplaces = [marketplaces]
    return Integration(
        id=name,
        content_type=ContentType.INTEGRATION,
        node_id=f"{ContentType.INTEGRATION}:{name}",
        path=path,
        fromversion="5.0.0",
        toversion="99.99.99",
        display_name=display_name,
        name=name,
        marketplaces=marketplaces,
        deprecated=deprecated,
        type="python3",
        docker_image=DockerImage("demisto/python3:3.10.11.54799"),
        category="blabla",
        commands=[Command(name="test-command", description="")],
        is_fetch=is_fetch,
        is_fetch_events=is_fetch_events,
        is_remote_sync_in=is_remote_sync_in,
        is_fetch_samples=is_fetch_samples,
        is_feed=is_feed,
    )


@pytest.mark.parametrize(
    "support_level, include_name, expected_output",
    (
        (
            None,
            False,
            [
                "Partner Contribution Same Name",
                "partner_contribution_different_name",
                "regular_integration_different_name",
                "Samples Fetch",
                "Some Mirroring",
            ],
        ),
        (
            "partner",
            False,
            [
                "Partner Contribution Same Name",
                "partner_contribution_different_name",
                "regular_integration_different_name",
                "Samples Fetch",
                "Some Mirroring",
            ],
        ),
        (
            None,
            True,
            [
                {
                    "id": "Partner Contribution Same Name",
                    "name": "Partner Contribution Same Name (Partner Contribution)",
                },
                {
                    "id": "partner_contribution_different_name",
                    "name": "Partner Contribution Different Name (Partner Contribution)",
                },
                {
                    "id": "regular_integration_different_name",
                    "name": "Regular Integration Different Name",
                },
                {"id": "Samples Fetch", "name": "Samples Fetch"},
                {"id": "Some Mirroring", "name": "Some Mirroring"},
            ],
        ),
        (
            "partner",
            True,
            [
                {
                    "id": "Partner Contribution Same Name",
                    "name": "Partner Contribution Same Name",
                },
                {
                    "id": "partner_contribution_different_name",
                    "name": "Partner Contribution Different Name",
                },
                {
                    "id": "regular_integration_different_name",
                    "name": "Regular Integration Different Name",
                },
                {"id": "Samples Fetch", "name": "Samples Fetch"},
                {"id": "Some Mirroring", "name": "Some Mirroring"},
            ],
        ),
    ),
)
def test_get_valid_data_source_integrations(
    support_level, include_name, expected_output
):
    """
    Given:
        - Support level and whether to include the name

    When:
        - Getting valid data source integrations for a pack

    Then:
        - The correct data source integration return, with the expected name
    """
    integrations = [
        mock_integration_for_data_source(
            "Partner Contribution Same Name",
            "Partner Contribution Same Name (Partner Contribution)",
            is_fetch=True,
        ),
        mock_integration_for_data_source(
            "partner_contribution_different_name",
            "Partner Contribution Different Name (Partner Contribution)",
            is_fetch_events=True,
        ),
        mock_integration_for_data_source(
            "regular_integration_different_name",
            "Regular Integration Different Name",
            is_fetch=True,
        ),
        mock_integration_for_data_source(
            "Not Fetching Integration", "Not Fetching Integration", is_fetch=False
        ),
        mock_integration_for_data_source(
            "Deprecated Integration",
            "Deprecated Integration",
            is_fetch=True,
            deprecated=True,
        ),
        mock_integration_for_data_source(
            "Not XSIAM Integration",
            "Not XSIAM Integration",
            is_fetch=True,
            marketplaces=MarketplaceVersions.XSOAR_ON_PREM,
        ),
        mock_integration_for_data_source(
            "Some Feed", "Some Feed", is_fetch=True, is_feed=True
        ),
        mock_integration_for_data_source(
            "Samples Fetch", "Samples Fetch", is_fetch_samples=True
        ),
        mock_integration_for_data_source(
            "Some Mirroring", "Some Mirroring", is_remote_sync_in=True
        ),
    ]

    content_items = PackContentItems()
    content_items.integration.extend(integrations)

    result = PackMetadata.get_valid_data_source_integrations(
        content_items, support_level, include_name
    )
    assert result == expected_output


@pytest.mark.parametrize(
    "support, given_default_data_source_id, integrations, expected_default_data_source",
    (
        (
            "partner",
            "partner_support",
            [
                mock_integration_for_data_source(
                    "partner_support",
                    "Partner Support (Partner Contribution)",
                    is_fetch=True,
                ),
                mock_integration_for_data_source(
                    "other_partner_support",
                    "Other Partner Support (Partner Contribution)",
                    is_fetch=True,
                ),
            ],
            {"id": "partner_support", "name": "Partner Support"},
        ),
        (
            "xsoar",
            "xsoar_support",
            [
                mock_integration_for_data_source(
                    "xsoar_support", "XSOAR Support", is_fetch=True
                ),
                mock_integration_for_data_source(
                    "Other XSOAR Support", "Other XSOAR Support", is_fetch=True
                ),
            ],
            {"id": "xsoar_support", "name": "XSOAR Support"},
        ),
        (
            "xsoar",
            None,
            [
                mock_integration_for_data_source(
                    "One Fetching Integration",
                    "One Fetching Integration",
                    is_fetch=True,
                ),
                mock_integration_for_data_source(
                    "Not Fetching Integration",
                    "Not Fetching Integration",
                    is_fetch=False,
                ),
                mock_integration_for_data_source(
                    "Deprecated Integration",
                    "Deprecated Integration",
                    is_fetch=True,
                    deprecated=True,
                ),
                mock_integration_for_data_source(
                    "Feed Integration", "Feed Integration", is_fetch=True, is_feed=True
                ),
            ],
            {"id": "One Fetching Integration", "name": "One Fetching Integration"},
        ),
    ),
)
def test_set_default_data_source(
    support, given_default_data_source_id, integrations, expected_default_data_source
):
    """
    Given:
        - Support level, default data source name and id, pack integrations names and ids

    When:
        - Setting a default data source to a pack

    Then:
        - The correct data source integration is set
    """
    content_items, my_instance = mock_pack_metadata_for_data_source(
        support=support,
        default_data_source=given_default_data_source_id,
        integrations=integrations,
    )

    my_instance._set_default_data_source(content_items)
    assert my_instance.default_data_source_id == expected_default_data_source.get("id")
    assert my_instance.default_data_source_name == expected_default_data_source.get(
        "name"
    )


def mock_pack_metadata_for_data_source(support, default_data_source, integrations):
    my_instance = PackMetadata(
        name="test",
        display_name="",
        description="",
        created="",
        legacy=False,
        support=support,
        url="",
        email="",
        eulaLink="",
        price=0,
        hidden=False,
        commit="",
        downloads=0,
        keywords=[],
        searchRank=0,
        excludedDependencies=[],
        videos=[],
        modules=[],
        default_data_source_id=default_data_source,
    )  # type: ignore

    content_items = PackContentItems()
    content_items.integration.extend(integrations)
    return content_items, my_instance


@pytest.mark.parametrize(
    "content_item, incident_to_alert, expected_description",
    [
        (
            create_playbook_object(
                ["id", "name", "description"],
                ["playbook-incidents", "playbook-incidents", "playbook-incidents"],
            ),
            True,
            "playbook-alerts",
        ),
        (
            create_playbook_object(
                ["id", "name", "description"],
                ["playbook-incidents", "playbook-incidents", "playbook-incidents"],
            ),
            False,
            "my playbook tester",
        ),
        (
            create_playbook_object(
                ["id", "name", "description"],
                ["playbook-incidents", "playbook-incidents", "my playbook tester"],
            ),
            True,
            "my playbook tester",
        ),
    ],
)
def test_replace_item_if_has_higher_toversion_on_playbook(
    content_item, incident_to_alert, expected_description
):
    """
    Given:
        a Pack Metadata, playbook, incidents_to_alerts flag.
        - Case 1: Playbook with description different from the one in the metadata and incidents_to_alerts=True.
        - Case 2: Playbook with description different from the one in the metadata and incidents_to_alerts=False.
        - Case 3: Playbook with description similar to the one in the metadata and incidents_to_alerts=True.
    When:
        - Calling the _replace_item_if_has_higher_toversion method.
    Then:
        Ensure the id and the name fields in hte metadata we left untouched and the description is changed accordingly.
        - Case 1: description should change.
        - Case 2: description shouldn't change.
        - Case 3: description shouldn't change.
    """
    content_item_metadata = {
        "toversion": "99.99.99",
        "id": "my playbook tester",
        "name": "my playbook tester",
        "description": "my playbook tester",
    }
    my_instance = PackMetadata(
        name="test",
        display_name="",
        description="",
        created="",
        legacy=False,
        support="",
        url="",
        email="",
        eulaLink="",
        price=0,
        hidden=False,
        commit="",
        downloads=0,
        keywords=[],
        searchRank=0,
        excludedDependencies=[],
        videos=[],
        modules=[],
    )  # type: ignore
    my_instance._replace_item_if_has_higher_toversion(
        content_item,
        content_item_metadata,
        content_item.summary(MarketplaceVersions.MarketplaceV2, incident_to_alert),
        MarketplaceVersions.MarketplaceV2,
        incident_to_alert=incident_to_alert,
    )
    assert content_item_metadata["id"] == "my playbook tester"
    assert content_item_metadata["name"] == "my playbook tester"
    assert content_item_metadata["description"] == expected_description
