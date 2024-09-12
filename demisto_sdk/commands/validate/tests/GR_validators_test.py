import pytest
from pytest_mock import MockerFixture

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.conf_json import ConfJSON
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.GR_validators import (
    GR104_is_pack_display_name_already_exists,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place_all_files import (
    MarketplacesFieldValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place_list_files import (
    MarketplacesFieldValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_all_files import (
    IsPackDisplayNameAlreadyExistsValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_list_files import (
    IsPackDisplayNameAlreadyExistsValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR105_duplicate_content_id_all_files import (
    DuplicateContentIdValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR105_duplicate_content_id_list_files import (
    DuplicateContentIdValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR106_is_testplaybook_in_use_all_files import (
    IsTestPlaybookInUseValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR106_is_testplaybook_in_use_list_files import (
    IsTestPlaybookInUseValidatorListFiles,
)
from TestSuite.repo import Repo

MP_XSOAR = [MarketplaceVersions.XSOAR.value]
MP_V2 = [MarketplaceVersions.MarketplaceV2.value]
MP_XSOAR_AND_V2 = [
    MarketplaceVersions.XSOAR.value,
    MarketplaceVersions.MarketplaceV2.value,
]


def test_IsPackDisplayNameAlreadyExistsValidatorListFiles_obtain_invalid_content_items(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorListFiles obtain_invalid_content_items function, on one of the duplicate packs.
    Then
        - Validate that we got the error messages for the duplicate name.
    """
    mocker.patch.object(
        GR104_is_pack_display_name_already_exists,
        "CONTENT_PATH",
        new=graph_repo.path,
    )
    graph_repo.create_pack(name="pack1")

    graph_repo.create_pack(name="pack2")
    graph_repo.packs[1].pack_metadata.update(
        {
            "name": "pack1",
        }
    )

    graph_repo.create_pack(name="pack3")

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = (
        IsPackDisplayNameAlreadyExistsValidatorListFiles().obtain_invalid_content_items(
            [graph_repo.packs[0], graph_repo.packs[2]]
        )
    )

    assert len(results) == 1
    assert results[0].message == "Pack 'pack1' has a duplicate display_name as: pack2."


def test_IsPackDisplayNameAlreadyExistsValidatorAllFiles_obtain_invalid_content_items(
    mocker: MockerFixture, graph_repo: Repo
):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorAllFiles obtain_invalid_content_items function.
    Then
        - Validate that we got the error messages for the duplicate name.
    """
    mocker.patch.object(
        GR104_is_pack_display_name_already_exists,
        "CONTENT_PATH",
        new=graph_repo.path,
    )
    graph_repo.create_pack(name="pack1")

    graph_repo.create_pack(name="pack2")
    graph_repo.packs[1].pack_metadata.update(
        {
            "name": "pack1",
        }
    )

    graph_repo.create_pack(name="pack3")

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = (
        IsPackDisplayNameAlreadyExistsValidatorAllFiles().obtain_invalid_content_items(
            [pack for pack in graph_repo.packs]
        )
    )

    assert len(results) == 2


@pytest.fixture
def prepared_graph_repo(graph_repo: Repo):
    """
    Setup mocked content graph for Graph Validators tests.

    **Note:**
    Currently, the graph is constructed specifically for 'MarketplaceFieldValidator' test. However,
    it can be enhanced to serve other graph validator tests as well.
    """

    sample_pack = graph_repo.create_pack("SamplePack")
    sample_pack.set_data(marketplaces=MP_XSOAR_AND_V2)
    sample_pack.create_script(
        "SampleScript", code='demisto.execute_command("SampleScriptTwo", dArgs)'
    ).set_data(marketplaces=MP_XSOAR_AND_V2)
    integration = sample_pack.create_integration(
        name="SampleIntegration", code="from TestApiModule import *"
    )
    integration.set_commands(["test-command"])
    integration.set_data(
        tests=["SampleTestPlaybook"],
        defaultclassifier="SampleClassifier",
        marketplaces=MP_XSOAR_AND_V2,
    )

    sample_pack_2 = graph_repo.create_pack("SamplePack2")
    sample_pack_2.set_data(marketplaces=MP_XSOAR_AND_V2)
    sample_pack_2.create_script(
        "TestApiModule", code='demisto.execute_command("SampleScriptTwo", dArgs)'
    ).set_data(marketplaces=MP_XSOAR_AND_V2)
    sample_pack_2.create_classifier("SampleClassifier")
    sample_pack_2.create_test_playbook("SampleTestPlaybook")
    sample_pack_2.create_test_playbook("TestPlaybookNoInUse")
    sample_pack_2.create_test_playbook("TestPlaybookDeprecated").set_data(
        deprecated="true"
    )

    sample_pack_3 = graph_repo.create_pack("SamplePack3")
    sample_pack_3.set_data(marketplaces=MP_XSOAR)
    sample_pack_3.create_script("SampleScriptTwo").set_data(marketplaces=MP_XSOAR)

    sample_pack_4 = graph_repo.create_pack("SamplePack4")
    sample_pack_4.set_data(marketplaces=MP_XSOAR_AND_V2)
    sample_pack_4.create_integration(name="SampleIntegration")
    # duplicate integration as in sample_pack for testing GR 105
    sample_pack_4.create_widget(name="SampleWidget")
    sample_pack.create_widget(name="SampleWidget")
    return graph_repo


@pytest.mark.parametrize(
    "pack_indices, expected_messages",
    [
        (
            slice(0, 1),  # First pack only.
            {
                "Content item 'SampleScript' can be used in the 'marketplacev2, xsoar, xsoar_saas' marketplaces, "
                "however it uses content items: 'SampleScriptTwo' which are not supported in all of the marketplaces "
                "of 'SampleScript'."
            },
        ),
        (
            slice(1, None),  # All packs except the first.
            {
                "Content item 'TestApiModule' can be used in the 'marketplacev2, xsoar, xsoar_saas' marketplaces, "
                "however it uses content items: 'SampleScriptTwo' which are not supported in all of the marketplaces "
                "of 'TestApiModule'.",
                "Content item 'SampleScript' can be used in the 'marketplacev2, xsoar, xsoar_saas' marketplaces, "
                "however it uses content items: 'SampleScriptTwo' which are not supported in all of the marketplaces "
                "of 'SampleScript'.",
            },
        ),
    ],
)
def test_MarketplacesFieldValidatorListFiles_obtain_invalid_content_items(
    prepared_graph_repo: Repo, pack_indices, expected_messages
):
    """
    Given
    - A content repo.
    When
    - Running MarketplacesFieldValidatorListFiles obtain_invalid_content_items() function on specific packs.
    Then
    - Validate the existence of invalid marketplaces usages.
    - Invalid content items shall be found, searched over specific packs, with expected error messages listed in
        `expected_messages`.
    """
    graph_interface = prepared_graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    pack_objects = [
        pack.get_graph_object(graph_interface) for pack in prepared_graph_repo.packs
    ]

    to_validate = pack_objects[pack_indices]
    validation_results = (
        MarketplacesFieldValidatorListFiles().obtain_invalid_content_items(to_validate)
    )
    assert expected_messages == {result.message for result in validation_results}


@pytest.mark.parametrize(
    "pack_indices",
    [
        slice(0, 1),  # First pack only.
        slice(1, None),  # All packs except the first.
        slice(None, None),  # All packs.
    ],
)
def test_MarketplacesFieldValidatorAllFiles_obtain_invalid_content_items(
    prepared_graph_repo: Repo, pack_indices
):
    """
    Given
    - A content repo.
    When
    - Running MarketplacesFieldValidatorAllFiles obtain_invalid_content_items() function with different pack slices.
    Then
    - Validate the validator ignores the provided specific packs and validates all content items in the content graph.
    - Validate the existence of invalid marketplaces usages.
    - Two invalid content items shall be found, with expected error message listed in `expected__messages`.
    """
    expected_messages = {
        "Content item 'TestApiModule' can be used in the 'marketplacev2, xsoar, xsoar_saas' marketplaces, "
        "however it uses content items: 'SampleScriptTwo' which are not supported in all of the marketplaces "
        "of 'TestApiModule'.",
        "Content item 'SampleScript' can be used in the 'marketplacev2, xsoar, xsoar_saas' marketplaces, "
        "however it uses content items: 'SampleScriptTwo' which are not supported in all of the marketplaces "
        "of 'SampleScript'.",
    }

    graph_interface = prepared_graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    pack_objects = [
        pack.get_graph_object(graph_interface) for pack in prepared_graph_repo.packs
    ]

    to_validate = pack_objects[pack_indices]
    validation_results = (
        MarketplacesFieldValidatorAllFiles().obtain_invalid_content_items(to_validate)
    )
    assert expected_messages == {result.message for result in validation_results}


def test_IsTestPlaybookInUseValidatorAllFiles_is_valid(
    mocker: MockerFixture, prepared_graph_repo: Repo
):
    """
    Tests the IsTestPlaybookInUseValidatorAllFiles validator for different scenarios of test playbooks.

    Given:
    - A graph interface with prepared repository data.
    - Three test playbooks: one in use, one not in use, and one deprecated.

    When:
    - Validating each test playbook using the IsTestPlaybookInUseValidatorAllFiles.

    Then:
    - Ensure that the validator correctly identifies the playbook in use with no errors.
    - Ensure that the validator correctly identifies the playbook not in use and returns an appropriate error message.
    - Ensure that the validator correctly identifies the deprecated playbook with no errors.
    """
    mock_conf = ConfJSON.from_path("demisto_sdk/tests/test_files/conf.json")
    mocker.patch.object(ConfJSON, "from_path", return_value=mock_conf)
    graph_interface = prepared_graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    playbook_in_use = (
        prepared_graph_repo.packs[1].test_playbooks[0].get_graph_object(graph_interface)
    )
    validation_results = (
        IsTestPlaybookInUseValidatorListFiles().obtain_invalid_content_items(
            [playbook_in_use]
        )
    )
    assert validation_results == []  # the test playbook in use

    playbook_no_in_use = (
        prepared_graph_repo.packs[1].test_playbooks[1].get_graph_object(graph_interface)
    )
    validation_results = (
        IsTestPlaybookInUseValidatorAllFiles().obtain_invalid_content_items(
            [playbook_no_in_use]
        )
    )
    assert (
        validation_results[0].message
        == (  # the test playbook not in use
            "Test playbook 'TestPlaybookNoInUse' is not linked to any content item."
            " Make sure at least one integration, script or playbook mentions the test-playbook id under the `tests:` key."
        )
    )

    playbook_deprecated = (
        prepared_graph_repo.packs[1].test_playbooks[2].get_graph_object(graph_interface)
    )
    validation_results = (
        IsTestPlaybookInUseValidatorListFiles().obtain_invalid_content_items(
            [playbook_deprecated]
        )
    )
    assert validation_results == []  # the test playbook is deprecated


def test_DuplicateContentIdValidatorListFiles_is_valid(prepared_graph_repo: Repo):
    """
    Test case for the DuplicateContentIdValidatorListFiles validator.

    This test ensures that the validator correctly identifies when there are no duplicate IDs
    in the content items of the prepared graph repository.

    When:
    - Validating all pack objects in the prepared graph repository.

    Then:
    - The validator should return an empty list, indicating no duplicate IDs were found.
    """
    graph_interface = prepared_graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    pack_objects = [
        pack.get_graph_object(graph_interface) for pack in prepared_graph_repo.packs
    ]
    validation_results = (
        DuplicateContentIdValidatorListFiles().obtain_invalid_content_items(
            pack_objects
        )
    )
    assert validation_results == []


def test_DuplicateContentIdValidatorListFiles_integration_is_invalid(
    prepared_graph_repo: Repo,
):
    """
    Test case for the DuplicateContentIdValidatorListFiles validator with duplicate integration IDs.

    This test ensures that the validator correctly identifies duplicate IDs
    in integration content items from different packs in the prepared graph repository.

    When:
    - Validating integration objects from two different packs.

    Then:
    - The validator should return validation results indicating duplicate IDs were found.
    - The validation messages should correctly identify the duplicate 'SampleIntegration' ID
      in both packs.
    """
    graph_interface = prepared_graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    pack_objects = [
        prepared_graph_repo.packs[0].integrations[0].get_graph_object(graph_interface),
        prepared_graph_repo.packs[3].integrations[0].get_graph_object(graph_interface),
    ]
    validation_results = (
        DuplicateContentIdValidatorListFiles().obtain_invalid_content_items(
            pack_objects
        )
    )
    assert len(validation_results) == 2


def test_DuplicateContentIdValidatorListFiles_widget_is_invalid(
    prepared_graph_repo: Repo,
):
    """
    Test case for the DuplicateContentIdValidatorListFiles validator with duplicate widget IDs.

    This test ensures that the validator correctly identifies duplicate IDs
    in widget content items from different packs in the prepared graph repository.

    When:
    - Validating widget objects from two different packs.

    Then:
    - The validator should return validation results indicating duplicate IDs were found.
    - The validation messages should correctly identify the duplicate 'SampleWidget' ID
      in both packs.
    """
    graph_interface = prepared_graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    pack_objects = [
        prepared_graph_repo.packs[0].widgets[0].get_graph_object(graph_interface),
        prepared_graph_repo.packs[3].widgets[0].get_graph_object(graph_interface),
    ]
    validation_results = (
        DuplicateContentIdValidatorListFiles().obtain_invalid_content_items(
            pack_objects
        )
    )
    assert len(validation_results) == 2


def test_DuplicateContentIdValidatorAllFiles_is_invalid(prepared_graph_repo: Repo):
    """
    Test case for the DuplicateContentIdValidatorAllFiles validator with duplicate IDs.

    This test ensures that the validator correctly identifies duplicate IDs
    in content items from different packs in the prepared graph repository.

    When:
    - Validating objects from all packs.

    Then:
    - The validator should return validation results indicating duplicate IDs were found.
    - The validation messages should correctly identify the duplicate 'SampleIntegration' and 'SampleWidget' IDs
      in different packs.
    """
    graph_interface = prepared_graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    validation_results = (
        DuplicateContentIdValidatorAllFiles().obtain_invalid_content_items([])
    )
    assert len(validation_results) == 4
