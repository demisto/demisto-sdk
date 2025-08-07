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
from demisto_sdk.commands.validate.validators.GR_validators.GR101_is_using_invalid_from_version_all_files import (
    IsUsingInvalidFromVersionValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR101_is_using_invalid_from_version_list_files import (
    IsUsingInvalidFromVersionValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR102_is_using_invalid_to_version_valid_all_files import (
    IsUsingInvalidToVersionValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR102_is_using_invalid_to_version_valid_list_files import (
    IsUsingInvalidToVersionValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR103_is_using_unknown_content_all_files import (
    IsUsingUnknownContentValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR103_is_using_unknown_content_list_files import (
    IsUsingUnknownContentValidatorListFiles,
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
from demisto_sdk.commands.validate.validators.GR_validators.GR107_is_deprecated_content_item_in_usage_valid_all_files import (
    IsDeprecatedContentItemInUsageValidatorAllFiles as GR107_IsDeprecatedContentItemInUsageValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR107_is_deprecated_content_item_in_usage_valid_list_files import (
    IsDeprecatedContentItemInUsageValidatorListFiles as GR107_IsDeprecatedContentItemInUsageValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR108_is_invalid_packs_dependencies_valid_all_files import (
    IsInvalidPacksDependenciesValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR108_is_invalid_packs_dependencies_valid_list_files import (
    IsInvalidPacksDependenciesValidatorListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR109_is_supported_modules_compatibility_all_files import (
    IsSupportedModulesCompatibilityAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR109_is_supported_modules_compatibility_list_files import (
    IsSupportedModulesCompatibilityListFiles,
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
    sample_pack_2.create_test_playbook("TestReputationPlaybook")
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
    assert sample_pack.integrations[0].name == "SampleIntegration", (
        f"Expected integration name 'SampleIntegration', but found '{sample_pack.integrations[0].name}'."
        "This assertion is crucial for testing GR105 see `test_DuplicateContentIdValidatorListFiles_integration_is_invalid` test,"
        "which requires duplicate integration names in sample_pack and sample_pack_4."
    )

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
    - Ensure reputation test playbook is not test if they under the `reputation_tests` key in the conf.json.
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
            " Make sure at least one integration, script or playbook mentions the test-playbook ID under the `tests:` key."
        )
    )

    playbook_deprecated = (
        prepared_graph_repo.packs[1].test_playbooks[3].get_graph_object(graph_interface)
    )
    validation_results = (
        IsTestPlaybookInUseValidatorListFiles().obtain_invalid_content_items(
            [playbook_deprecated]
        )
    )
    assert validation_results == []  # the test playbook is deprecated

    reputation_playbook = (
        prepared_graph_repo.packs[1].test_playbooks[2].get_graph_object(graph_interface)
    )
    validation_results = (
        IsTestPlaybookInUseValidatorListFiles().obtain_invalid_content_items(
            [reputation_playbook]
        )
    )
    assert validation_results == []


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


@pytest.fixture
def repo_for_test(graph_repo):
    # A repository with 3 packs:
    pack_1 = graph_repo.create_pack("Pack1")
    pack_1.create_script(
        "MyScript1", code='demisto.execute_command("does_not_exist", dArgs)'
    )
    pack_2 = graph_repo.create_pack("pack2")
    pack_2.create_test_playbook("SampleTestPlaybook")
    pack_2.create_classifier("SampleClassifier")
    pack_2.create_script(
        "MyScript2", code='demisto.execute_command("MyScript1", dArgs)'
    )

    pack_3 = graph_repo.create_pack("Pack3")
    pack_3.create_script(
        "MyScript3", code='demisto.execute_command("MyScript1", dArgs)'
    )
    return graph_repo


@pytest.fixture
def repo_for_test_SearchAlerts_MarketplaceV2(graph_repo):
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.pack_metadata.update(
        {"marketplaces": [MarketplaceVersions.MarketplaceV2.value]}
    )
    pack_a.create_script("Script1", code='demisto.executeCommand("SearchAlerts", {})')

    pack_b = graph_repo.create_pack("Pack B")
    pack_b.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.XSOAR.value,
            ]
        }
    )
    pack_b.create_script(
        "SearchIncidents", code='demisto.executeCommand("SearchIncidents", {})'
    )

    return graph_repo


def test_IsUsingUnknownContentValidator__varied_dependency_types__all_files(
    repo_for_test: Repo,
):
    """
    Given:
        - A content graph interface with preloaded repository data:
            - Pack 1: Exclusively uses unknown content.
                -  Required dependencies - ('MyScript1' references 'does_not_exist')
            - Pack 2: Utilizes a mix of 1 known and 2 unknown content items. The unknown content falls into 2 categories:
                    - Optional dependencies - ('SampleClassifier' references 'Test type')
                    - Test dependencies - ('TestPlaybookNoInUse' and 'SampleTestPlaybook' reference 'DeleteContext')
            - Pack 3: Exclusively uses known content.
    When:
        - The GR103 validation is executed across the entire repository (-a) to detect instances of unknown content usage.
    Then:
        - The validator should accurately identify the content items that are referencing unknown content.
    """
    graph_interface = repo_for_test.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingUnknownContentValidatorAllFiles().obtain_invalid_content_items(
        content_items=[]
    )
    assert len(results) == 3


def test_IsUsingUnknownContentValidator_verify_alert_to_incident_MarketplaceV2(
    repo_for_test_SearchAlerts_MarketplaceV2: Repo,
):
    """
    Given:
        - A content graph interface with preloaded repository data that contains 2 packs:
            - Pack A in XSIAM marketplace with the script Script1 that using the script SearchAlerts.
            - Pack B in marketplaces XSOAR and XSIAM with the script SearchIncidents.
    When:
        - The GR103 validation is executed across the entire repository (-a) to detect instances of unknown content usage.
    Then:
        - The validator should accurately identify there is no unknown content usage because SearchIncidents uploaded as SearchAlerts in marketplace v2.
    """
    graph_interface = repo_for_test_SearchAlerts_MarketplaceV2.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingUnknownContentValidatorAllFiles().obtain_invalid_content_items(
        content_items=[]
    )
    assert not results


@pytest.mark.parametrize(
    "item_index, expected_len_results", [(0, 1), (1, 0), (2, 1), (3, 1), (4, 0)]
)
def test_IsUsingUnknownContentValidator__different_dependency_type__list_files(
    repo_for_test: Repo, item_index, expected_len_results
):
    """
    Given:
        - A list of content objects from different packs in the repository.
    When:
        - Validating the content items, one item at a time.
    Then:
        - The validator should accurately identify the content items that are referencing unknown content:
        - Item 1: MyScript1 (references 'does_not_exist' - Required dependencies)
        - Item 2: MyScript2 (no unknown references)
        - Item 3: SampleTestPlaybook (references 'DeleteContext' - Required dependencies for a 'test' item)
        - Item 4: SampleClassifier (references 'Test type' - Optional dependencies)
        - Item 5: MyScript3 (no unknown references)
    """
    graph_interface = repo_for_test.create_graph()
    BaseValidator.graph_interface = graph_interface
    content_items = [
        repo_for_test.packs[0].scripts[0],
        repo_for_test.packs[1].scripts[0],
        repo_for_test.packs[1].test_playbooks[0],
        repo_for_test.packs[1].classifiers[0],
        repo_for_test.packs[2].scripts[0],
    ]

    results = IsUsingUnknownContentValidatorListFiles().obtain_invalid_content_items(
        [content_items[item_index].get_graph_object(graph_interface)]
    )
    assert len(results) == expected_len_results


@pytest.fixture
def repo_for_test_gr_107(graph_repo: Repo):
    playbook_dict_using_deprecate_commands = {
        "id": "UsingDeprecatedCommand",
        "name": "UsingDeprecatedCommand",
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "|||test-command",
                },
            },
            "1": {
                "id": "1",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "|||test-command",
                },
            },
        },
    }
    playbook_dict_using_deprecated_playbook = {
        "id": "UsingDeprecatedPlaybook",
        "name": "UsingDeprecatedPlaybook",
        "tasks": {
            "4": {
                "id": "4",
                "taskid": "1",
                "type": "playbook",
                "task": {
                    "id": "1",
                    "name": "DeprecatedPlaybook",
                    "playbookName": "DeprecatedPlaybook",
                },
            }
        },
    }
    pack_1 = graph_repo.create_pack("Pack1")
    integration = pack_1.create_integration("MyIntegration")
    integration.set_commands(["test-command"])
    integration.set_data(**{"script.commands[0].deprecated": "true"})
    pack_2 = graph_repo.create_pack("pack2")
    pack_2.create_playbook(
        "UsingDeprecatedCommand", yml=playbook_dict_using_deprecate_commands
    )
    pack_2.create_playbook(
        name="DeprecatedPlaybook",
        yml={
            "deprecated": "true",
            "id": "DeprecatedPlaybook",
            "name": "DeprecatedPlaybook",
        },
    )
    pack_2.create_playbook(
        name="UsingDeprecatedPlaybook", yml=playbook_dict_using_deprecated_playbook
    )
    pack_2.create_script(name="DeprecatedScript").set_data(**{"deprecated": "true"})
    pack_2.create_script(
        name="UsingDeprecatedScript",
        code='demisto.execute_command("DeprecatedScript", dArgs)',
    )
    pack_2.create_script(name="SampleScript")
    return graph_repo


@pytest.mark.parametrize(
    "playbook_index, expected_validation_count",
    [
        pytest.param(0, 1, id="Playbook using deprecated command"),
        pytest.param(2, 1, id="Playbook using deprecated playbook"),
    ],
)
def test_GR107_IsDeprecatedContentItemInUsageValidatorListFiles_invalid_playbook(
    repo_for_test_gr_107: Repo, playbook_index: int, expected_validation_count: int
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for invalid cases.

    Given:
    - A repository with deprecated content items in use.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on specific playbooks.

    Then:
    - Verify that the validator correctly identifies the usage of deprecated content items.

    Parameters:
    - playbook_index: Index of the playbook to test in the pack.
    - expected_validation_count: Expected number of validation results.
    """
    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1]
        .playbooks[playbook_index]
        .get_graph_object(graph_interface),
    ]
    validator = GR107_IsDeprecatedContentItemInUsageValidatorListFiles()
    validation_results = validator.obtain_invalid_content_items(pack_objects)

    assert len(validation_results) == expected_validation_count


def test_GR107_IsDeprecatedContentItemInUsageValidatorListFiles_invalid_script(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for an invalid script.

    Given:
    - A repository with a script that uses a deprecated content item.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on the specific script.

    Then:
    - Verify that the validator correctly identifies the usage of the deprecated content item.
    - Assert that the validation results contain exactly one item.
    """
    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1].scripts[1].get_graph_object(graph_interface),
    ]
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorListFiles().obtain_invalid_content_items(
        pack_objects
    )

    assert len(validation_results) == 1


def test_GR107_IsDeprecatedContentItemInUsageValidatorListFiles_valid_script(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for a valid script.

    Given:
    - A repository with a script that doesn't use any deprecated content items.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on the specific script.

    Then:
    - Verify that the validator correctly identifies that no deprecated content items are used.
    - Assert that the validation results are empty.
    """
    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1].scripts[2].get_graph_object(graph_interface),
    ]
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorListFiles().obtain_invalid_content_items(
        pack_objects
    )

    assert len(validation_results) == 0


def test_GR107_IsDeprecatedContentItemInUsageValidatorListFiles_used_deprecated_item(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for a valid playbook.

    Given:
    - A repository with a deprecated playbook and an integration that uses the deprecated playbook.
      The deprecated playbook does not use any deprecated content items.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on the specific playbook.

    Then:
    - Verify that the validator correctly identifies that a deprecated playbook is used by the integration.
    - Assert that the validation results contains exactly one item.
    """
    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1].playbooks[1].get_graph_object(graph_interface),
    ]
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorListFiles().obtain_invalid_content_items(
        pack_objects
    )

    assert len(validation_results) == 1


def test_GR107_deprecated_collected_used_by_deprecated(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for deprecated item using deprecated item.

    Given:
    - A repository with a deprecated script that uses another deprecated script.
      Both scripts are deprecated, so this relationship should be acceptable.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on the deprecated script that uses deprecated content.

    Then:
    - Verify that the validator correctly identifies that deprecated-to-deprecated usage is acceptable.
    - Assert that the validation results are empty since deprecated items can use other deprecated items.
    """
    # Create a deprecated script that uses the existing deprecated script
    repo_for_test_gr_107.packs[1].create_script(
        name="DeprecatedUsingDeprecated",
        code='demisto.execute_command("DeprecatedScript", dArgs)',
    ).set_data(deprecated="true")

    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1]
        .scripts[3]
        .get_graph_object(graph_interface),  # DeprecatedUsingDeprecated
    ]
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorListFiles().obtain_invalid_content_items(
        pack_objects
    )

    assert len(validation_results) == 0


def test_GR107_not_deprecated_collected_uses_deprecated(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for non-deprecated item using deprecated item.

    Given:
    - A repository with a non-deprecated script that uses a deprecated script.
      The non-deprecated script uses deprecated content items.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on the specific non-deprecated script.

    Then:
    - Verify that the validator correctly identifies that the non-deprecated script uses deprecated content.
    - Assert that the validation results contains exactly one item.
    """
    # Add non-deprecated script that uses the existing deprecated script
    repo_for_test_gr_107.packs[1].create_script(
        name="NonDeprecatedUsingDeprecated",
        code='demisto.execute_command("DeprecatedScript", dArgs)',
    )

    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1].scripts[3].get_graph_object(graph_interface),
    ]
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorListFiles().obtain_invalid_content_items(
        pack_objects
    )

    assert len(validation_results) == 1


def test_GR107_not_deprecated_collected_uses_not_deprecated(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for non-deprecated item using non-deprecated item.

    Given:
    - A repository with a non-deprecated script that uses a non-deprecated script.
      The non-deprecated script does not use any deprecated content items.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on the specific non-deprecated script.

    Then:
    - Verify that the validator correctly identifies that no deprecated content items are used.
    - Assert that the validation results are empty.
    """
    # Add non-deprecated script that uses the existing non-deprecated script
    repo_for_test_gr_107.packs[1].create_script(
        name="NonDeprecatedUsingNonDeprecated",
        code='demisto.execute_command("SampleScript", dArgs)',
    )

    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1].scripts[3].get_graph_object(graph_interface),
    ]
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorListFiles().obtain_invalid_content_items(
        pack_objects
    )

    assert len(validation_results) == 0


def test_GR107_not_being_deprecated_with_complex_chain(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorListFiles validator for script using deprecated content in complex chain.

    Given:
    - A repository with a non-deprecated script that uses deprecated content items.
      The script uses multiple deprecated content items in a complex chain.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorListFiles on the specific non-deprecated script.

    Then:
    - Verify that the validator correctly identifies that the script uses deprecated content items.
    - Assert that the validation results contains exactly one item.
    """
    # Add another deprecated script for complex chain
    repo_for_test_gr_107.packs[1].create_script(
        name="AnotherDeprecatedScript"
    ).set_data(deprecated="true")

    # Add non-deprecated script that uses deprecated scripts
    repo_for_test_gr_107.packs[1].create_script(
        name="NonDeprecatedUsingMultipleDeprecated",
        code="""
demisto.execute_command("DeprecatedScript", dArgs)
demisto.execute_command("AnotherDeprecatedScript", dArgs)
        """,
    )

    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface

    pack_objects = [
        repo_for_test_gr_107.packs[1]
        .scripts[4]
        .get_graph_object(graph_interface),  # NonDeprecatedUsingMultipleDeprecated
    ]
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorListFiles().obtain_invalid_content_items(
        pack_objects
    )

    assert len(validation_results) == 1


def test_GR107_IsDeprecatedContentItemInUsageValidatorAllFiles_is_invalid(
    repo_for_test_gr_107: Repo,
):
    """
    Test the GR107_IsDeprecatedContentItemInUsageValidatorAllFiles validator for invalid cases across all files.

    Given:
    - A repository with multiple content items, some of which use deprecated content.

    When:
    - Running the GR107_IsDeprecatedContentItemInUsageValidatorAllFiles on the entire repository.

    Then:
    - Verify that the validator correctly identifies all instances of deprecated content usage.
    - Assert that the validation results contain exactly three items.
    """
    graph_interface = repo_for_test_gr_107.create_graph()
    BaseValidator.graph_interface = graph_interface
    validation_results = GR107_IsDeprecatedContentItemInUsageValidatorAllFiles().obtain_invalid_content_items(
        []
    )
    assert len(validation_results) == 3


@pytest.fixture
def repo_with_one_pack_for_gr101_gr102(graph_repo: Repo):
    # Repo which contains 1 pack

    # Pack 1 - script uses another script (relationship)
    pack_1 = graph_repo.create_pack("Pack1")
    pack_1.create_script(name="FirstScript")
    pack_1.create_script(
        name="SecondScript",
        code='demisto.execute_command("FirstScript", dArgs)',
    )
    return graph_repo


def test_IsUsingInvalidFromVersionValidator_sanity_all_files(
    repo_with_one_pack_for_gr101_gr102,
):
    """
    Given:
        - A content graph interface with preloaded repository data:
            - Pack 1:
                    - script 1 (which used by script 2)
                    - script 2 (which uses script 1)
    When:
        - The GR101 validation is executed across the all files
    Then:
        - The validator should pass, everything is valid, sanity check
    """
    graph_interface = repo_with_one_pack_for_gr101_gr102.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingInvalidFromVersionValidatorAllFiles().obtain_invalid_content_items_using_graph(
        content_items=[]
    )
    assert len(results) == 0


def test_IsUsingInvalidFromVersionValidator_invalid(
    repo_with_one_pack_for_gr101_gr102,
):
    """
    Given:
            - Pack 1:
                    - script 1 (which used by script 2, but has fromversion=10.0.0 while script 2 has fromversion=0.0.0)
                    - script 2 (which uses script 1)
    When:
        - The GR101 validation is executed across the second script
    Then:
        - The validator should fail due to target's fromversion higher than source's fromversion. (len(results) == 1)
        - Ensure the error message as expected
    """
    repo_with_one_pack_for_gr101_gr102.packs[0].scripts[0].set_data(
        **{"fromversion": "10.0.0"}
    )  # This line fails the GR101
    graph_interface = repo_with_one_pack_for_gr101_gr102.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingInvalidFromVersionValidatorListFiles().obtain_invalid_content_items_using_graph(
        content_items=[
            repo_with_one_pack_for_gr101_gr102.packs[0]
            .scripts[1]
            .get_graph_object(graph_interface)
        ]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "Content item 'SecondScript' whose from_version is '0.0.0'"
        " is using content items: 'FirstScript' whose from_version is higher"
        " (should be <= 0.0.0)"
    )


def test_IsUsingInvalidFromVersionValidator_valid(
    repo_with_one_pack_for_gr101_gr102,
):
    """
    Given:
            - Pack 1:
                    - script 1 (which used by script 2, has fromversion=10.0.0)
                    - script 2 (which uses script 1, has fromversion=11.0.0)
    When:
        - The GR101 validation is executed across the second script
    Then:
        - The validator should pass, since script 2 which uses script 1 has a higher fromversion, valid case
    """
    repo_with_one_pack_for_gr101_gr102.packs[0].scripts[0].set_data(
        **{"fromversion": "10.0.0"}
    )
    repo_with_one_pack_for_gr101_gr102.packs[0].scripts[1].set_data(
        **{"fromversion": "11.0.0"}
    )
    graph_interface = repo_with_one_pack_for_gr101_gr102.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingInvalidFromVersionValidatorListFiles().obtain_invalid_content_items_using_graph(
        content_items=[
            repo_with_one_pack_for_gr101_gr102.packs[0]
            .scripts[1]
            .get_graph_object(graph_interface)
        ]
    )
    assert len(results) == 0


def test_IsUsingInvalidToVersionValidatorAllFiles_sanity(
    repo_with_one_pack_for_gr101_gr102,
):
    """
    Given:
        - A content graph interface with preloaded repository data:
            - Pack 1:
                    - script 1 (which used by script 2)
                    - script 2 (which uses script 1)
    When:
        - The GR102 validation is executed across the all files
    Then:
        - The validator should pass, everything is valid, sanity check
    """
    graph_interface = repo_with_one_pack_for_gr101_gr102.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingInvalidToVersionValidatorAllFiles().obtain_invalid_content_items_using_graph(
        content_items=[]
    )
    assert len(results) == 0


def test_IsUsingInvalidToVersionValidatorListFiles_invalid(
    repo_with_one_pack_for_gr101_gr102,
):
    """
    Given:
            - Pack 1:
                    - script 1 (which used by script 2, but has toversion=10.0.0 while script 2 has toversion=0.0.0)
                    - script 2 (which uses script 1)
    When:
        - The GR102 validation is executed across the second script
    Then:
        - The validator should fail due to source's toversion > target's toversion. (len(results) == 1)
        - Ensure the error message as expected
    """
    repo_with_one_pack_for_gr101_gr102.packs[0].scripts[0].set_data(
        **{"toversion": "10.0.0"}
    )  # This line fails the GR102
    graph_interface = repo_with_one_pack_for_gr101_gr102.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingInvalidToVersionValidatorListFiles().obtain_invalid_content_items_using_graph(
        content_items=[
            repo_with_one_pack_for_gr101_gr102.packs[0]
            .scripts[1]
            .get_graph_object(graph_interface)
        ]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "Content item 'SecondScript' whose to_version is '99.99.99' is using content items:"
        " 'FirstScript' whose to_version is lower than 99.99.99, making them incompatible"
    )


def test_IsUsingInvalidToVersionValidatorListFiles_valid(
    repo_with_one_pack_for_gr101_gr102,
):
    """
    Given:
            - Pack 1:
                    - script 1 (which used by script 2, has toversion=11.0.0)
                    - script 2 (which uses script 1, has toversion=10.0.0)
    When:
        - The GR102 validation is executed across the second script
    Then:
        - The validator should pass, since script 2 which uses script 1 has a lower toversion, valid case
    """
    repo_with_one_pack_for_gr101_gr102.packs[0].scripts[0].set_data(
        **{"toversion": "11.0.0"}
    )
    repo_with_one_pack_for_gr101_gr102.packs[0].scripts[1].set_data(
        **{"toversion": "10.0.0"}
    )
    graph_interface = repo_with_one_pack_for_gr101_gr102.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingInvalidToVersionValidatorListFiles().obtain_invalid_content_items_using_graph(
        content_items=[
            repo_with_one_pack_for_gr101_gr102.packs[0]
            .scripts[1]
            .get_graph_object(graph_interface)
        ]
    )
    assert len(results) == 0


@pytest.fixture
def repo_for_test_gr_108(graph_repo: Repo):
    """
    Creates a test repository with three packs for testing GR108 validator.

    This fixture sets up a graph repository with the following structure:
    - Pack1: Contains a playbook that uses a command from Pack2.
             Has a mandatory dependency on Pack2.
    - Pack2: A hidden pack containing an integration with two commands.
    - Pack3: An empty pack for additional testing scenarios.
    """
    playbook_using_pack2_command = {
        "id": "UsingPack2Command",
        "name": "UsingPack2Command",
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "1",
                "task": {
                    "id": "1",
                    "script": "MyIntegration1|||test-command-1",
                    "brand": "MyIntegration1",
                    "iscommand": "true",
                },
            }
        },
    }
    # Pack 1: playbook uses command from pack 2
    pack_1 = graph_repo.create_pack("Pack1")

    pack_1.create_playbook("UsingPack2Command", yml=playbook_using_pack2_command)

    # Define Pack2 as a mandatory dependency for Pack1
    pack_1.pack_metadata.update({"dependencies": {"Pack2": {"mandatory": True}}})

    # Pack 2: hidden
    pack_2 = graph_repo.create_pack("Pack2")
    integration = pack_2.create_integration("MyIntegration1")
    integration.set_commands(["test-command-1", "test-command-2"])
    pack_2.pack_metadata.update({"hidden": "true"})
    # Pack3
    graph_repo.create_pack("Pack3")
    return graph_repo


def test_IsInvalidPacksDependenciesValidatorAllFiles_invalid(
    repo_for_test_gr_108: Repo,
):
    """
    Given:
        A test repository with Pack1 depending on the hidden Pack2.
    When:
        Running the IsInvalidPacksDependenciesValidatorAllFiles validator.
    Then:
        The validator should return a result indicating that Pack1 depends on the hidden Pack2.
    """
    graph_interface = repo_for_test_gr_108.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsInvalidPacksDependenciesValidatorAllFiles().obtain_invalid_content_items([])
    )
    assert (
        results[0].message
        == "Pack Pack1 has hidden pack(s) Pack2 in its mandatory dependencies"
    )


def test_IsInvalidPacksDependenciesValidatorListFiles(repo_for_test_gr_108: Repo):
    """
    Given:
        A test repository with Pack1 depending on the hidden Pack2, and Pack3 with no dependencies.
    When:
        Running the IsInvalidPacksDependenciesValidatorListFiles validator on specific packs.
    Then:
        1. For Pack1: The validator should return a result indicating that Pack1 depends on the hidden Pack2.
        2. For Pack3: The validator should not return any results (no invalid dependencies).
    """
    graph_interface = repo_for_test_gr_108.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsInvalidPacksDependenciesValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_gr_108.packs[0]]
        )
    )
    assert (
        results[0].message
        == "Pack Pack1 has hidden pack(s) Pack2 in its mandatory dependencies"
    )

    results = (
        IsInvalidPacksDependenciesValidatorListFiles().obtain_invalid_content_items(
            [repo_for_test_gr_108.packs[2]]
        )
    )
    assert not results


@pytest.fixture
def repo_for_test_gr_109(graph_repo: Repo):
    """
    Creates a test repository with three packs for testing GR109 validator.

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains Script1, Script2 and Integration1 that
              Script1  uses a command from Pack_b and configured with `supportedModules: ["module_x"]`.
              script2 and integration for additional testing scenarios.
    - Pack B: Contains "SearchIncidents" script.
              Note: "Pack B" does *not* list "module_x" in its supportedModules.
    """
    yml = {
        "commonfields": {"id": "Script1", "version": -1},
        "name": "Script1",
        "comment": "this is script Script1",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
        "supportedModules": ["module_x"],
    }
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
        }
    )
    pack_a.create_script(
        "Script1", code='demisto.executeCommand("SearchAlerts", {})', yml=yml
    )
    yml2 = {
        "commonfields": {"id": "Script2", "version": -1},
        "name": "Script2",
        "comment": "this is script Script2",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
        "supportedModules": ["module_y"],
    }
    pack_a.create_script(
        "Script2", code='demisto.executeCommand("SearchAlerts", {})', yml=yml2
    )
    pack_a.create_integration("Integration1")

    pack_b = graph_repo.create_pack("Pack B")
    pack_b.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.XSOAR.value,
            ]
        }
    )
    yml3 = {
        "commonfields": {"id": "SearchIncidents", "version": -1},
        "name": "SearchIncidents",
        "comment": "this is script SearchIncidents",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
        "supportedModules": ["module_y"],
    }
    pack_b.create_script(
        "SearchIncidents",
        code='demisto.executeCommand("SearchIncidents", {})',
        yml=yml3,
    )

    return graph_repo


def test_SupportedModulesCompatibility_invalid_all_files(
    repo_for_test_gr_109: Repo,
):
    """
    Given:
        A repository where "Script1" (with `supportedModules: ['module_x']`)
        depends on "SearchIncidents", which does not support "module_x".
    When:
        Running the IsSupportedModulesCompatibility validator on all files.
    Then:
        The validator should identify "Script1" as invalid, reporting that "SearchIncidents" is missing "module_x".
    """
    graph_interface = repo_for_test_gr_109.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsSupportedModulesCompatibilityAllFiles().obtain_invalid_content_items([])

    assert len(results) == 1
    assert (
        results[0].message
        == "The following mandatory dependencies missing required modules: SearchIncidents is missing: [module_x]"
    )
    assert results[0].content_object.object_id == "Script1"


def test_SupportedModulesCompatibility_invalid_list_files(
    repo_for_test_gr_109: Repo,
):
    """
    Given:
        A repository where "Script1" (with `supportedModules: ['module_x']`)
        depends on "SearchIncidents", which does not support "module_x".
    When:
        The IsSupportedModulesCompatibility validator runs specifically on "Script1".
    Then:
        The validator should identify "Script1" as invalid, reporting that "SearchIncidents"
        is missing the required "module_x".
    """
    graph_interface = repo_for_test_gr_109.create_graph()
    BaseValidator.graph_interface = graph_interface

    results = IsSupportedModulesCompatibilityListFiles().obtain_invalid_content_items(
        [repo_for_test_gr_109.packs[0].scripts[0].object]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "The following mandatory dependencies missing required modules: SearchIncidents is missing: [module_x]"
    )
    assert results[0].content_object.object_id == "Script1"


@pytest.fixture
def repo_for_test_gr_109_with_supported_module_none_in_content_item_b(graph_repo: Repo):
    """
    Creates a test repository with three packs for testing GR109 validator.

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains Script1, Script2 and Integration1 that
              Script1  uses a command from Pack_b and configured with `supportedModules: ["module_x"]`.
              script2 and integration for additional testing scenarios.
    - Pack B: Contains "SearchIncidents" script.
              Note: "Pack B" does *not* list "module_x" in its supportedModules.
    """
    yml = {
        "commonfields": {"id": "Script1", "version": -1},
        "name": "Script1",
        "comment": "this is script Script1",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
        "supportedModules": ["module_x"],
    }
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
        }
    )
    pack_a.create_script(
        "Script1", code='demisto.executeCommand("SearchAlerts", {})', yml=yml
    )
    pack_a.create_integration("Integration1")

    pack_b = graph_repo.create_pack("Pack B")
    pack_b.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.XSOAR.value,
            ]
        }
    )
    pack_b.create_script(
        "SearchIncidents", code='demisto.executeCommand("SearchIncidents", {})'
    )

    return graph_repo


def test_SupportedModulesCompatibility_supported_module_none_in_content_item_b(
    repo_for_test_gr_109_with_supported_module_none_in_content_item_b: Repo,
):
    """
    Given:
        A repository where "Script1" (with supportedModules: ['module_x']) depends on "SearchIncidents", whose supportedModules is None.
    When:
        Running the IsSupportedModulesCompatibility validator.
    Then:
        The validator should pass
    """
    graph_interface = (
        repo_for_test_gr_109_with_supported_module_none_in_content_item_b.create_graph()
    )
    BaseValidator.graph_interface = graph_interface
    results = IsSupportedModulesCompatibilityAllFiles().obtain_invalid_content_items([])

    assert len(results) == 0


@pytest.fixture
def repo_for_test_gr_109_with_supported_module_none_in_content_item_a(graph_repo: Repo):
    """
    Creates a test repository with three packs for testing GR109 validator.

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains Script1, Script2 and Integration1 that
              Script1  uses a command from Pack_b and configured with `supportedModules: ["module_x"]`.
              script2 and integration for additional testing scenarios.
    - Pack B: Contains "SearchIncidents" script.
              Note: "Pack B" does *not* list "module_x" in its supportedModules.
    """
    yml = {
        "commonfields": {"id": "Script1", "version": -1},
        "name": "Script1",
        "comment": "this is script Script1",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
    }
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
        }
    )
    pack_a.create_script(
        "Script1", code='demisto.executeCommand("SearchAlerts", {})', yml=yml
    )
    pack_a.create_integration("Integration1")

    pack_b = graph_repo.create_pack("Pack B")
    pack_b.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.XSOAR.value,
            ],
            "supportedModules": ["X0"],
        }
    )
    pack_b.create_script(
        "SearchIncidents", code='demisto.executeCommand("SearchIncidents", {})'
    )

    return graph_repo


def test_SupportedModulesCompatibility_supported_module_none_in_content_item_a(
    repo_for_test_gr_109_with_supported_module_none_in_content_item_a: Repo,
):
    """
    Given:
        A repository where "Script1" (with `supportedModules: ['module_x']`)
        depends on "SearchIncidents", which does not support "module_x".
    When:
        Running the IsSupportedModulesCompatibility validator on all files.
    Then:
        The validator should identify "Script1" as invalid, reporting that "SearchIncidents" is missing "module_x".
    """
    graph_interface = (
        repo_for_test_gr_109_with_supported_module_none_in_content_item_a.create_graph()
    )
    BaseValidator.graph_interface = graph_interface
    results = IsSupportedModulesCompatibilityAllFiles().obtain_invalid_content_items([])

    assert len(results) == 1
    assert (
        results[0].message
        == "The following mandatory dependencies missing required modules: SearchIncidents is missing: [C1, C3, X1, X3, X5, ENT_PLUS, agentix, asm, exposure_management]"
    )
    assert results[0].content_object.object_id == "Script1"
