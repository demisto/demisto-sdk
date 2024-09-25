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
from demisto_sdk.commands.validate.validators.GR_validators.GR101_is_using_invalid_from_version import (
    IsUsingInvalidFromVersionValidator,
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


@pytest.mark.parametrize("pack_index, expected_len_results", [(0, 1), (1, 2), (2, 0)])
def test_IsUsingUnknownContentValidator__different_dependency_type__list_files(
    repo_for_test: Repo, pack_index, expected_len_results
):
    """
    Given:
        Given:
        - A content graph interface with preloaded repository data:
            - Pack 1: Exclusively uses unknown content.
                -  Required dependencies - ('MyScript1' references 'does_not_exist')
            - Pack 2: Utilizes a mix of 1 known and 2 unknown content items. The unknown content falls into 2 categories:
                    - Optional dependencies - ('SampleClassifier' references 'Test type')
                    - Test dependencies - ('TestPlaybookNoInUse' and 'SampleTestPlaybook' reference 'DeleteContext')
            - Pack 3: Exclusively uses known content.
    When:
        - The GR103 validation is run on a specific pack to identify instances of unknown content usage.
    Then:
        - The validator should correctly identify the content items that are using unknown content.
            When running on Pack 1 - there should be 1 results.
            When running on Pack 2 - there should be 2 result.
            When running on Pack 3 - there should be 0 results.
    """
    graph_interface = repo_for_test.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingUnknownContentValidatorListFiles().obtain_invalid_content_items(
        [repo_for_test.packs[pack_index]]
    )
    assert len(results) == expected_len_results


@pytest.fixture
def repo_test_from_version(graph_repo: Repo):
    # Repo which contains two packs

    # Pack 1 - playbook uses an integration (relationship)
    pack_1 = graph_repo.create_pack("Pack1")
    playbook_using_deprecate_commands = {
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
                "1": {
                    "id": "1",
                    "taskid": "2",
                    "task": {
                        "id": "2",
                        "script": "|||UsingDeprecatedScript",
                    },
                },
            }
        },
    }
    pack_1.create_playbook(
        "UsingDeprecatedCommand", yml=playbook_using_deprecate_commands
    )
    integration = pack_1.create_integration("MyIntegration")
    integration.set_commands(["test-command"])
    integration.set_data(**{"script.commands[0].deprecated": "false"})
    dependencies = {
        "dependencies": {
            "Pack2": {"mandatory": True, "display_name": "Pack2"},
        }
    }
    pack_1.pack_metadata.update({"dependencies": dependencies})

    # Pack 2 - script uses another script (relationship)
    pack_2 = graph_repo.create_pack("Pack2")
    pack_2.create_script(name="DeprecatedScript").set_data(**{"deprecated": "true"})
    pack_2.create_script(
        name="UsingDeprecatedScript",
        code='demisto.execute_command("DeprecatedScript", dArgs)',
    )
    return graph_repo


def test_IsUsingInvalidFromVersionValidator_sanity_all_files(
    repo_test_from_version: Repo,
):
    """
    Given:
        - A content graph interface with preloaded repository data:
            - Pack 1:
                - playbook (which uses a command from the integration)
                - integration (which contains a command, used by the playbook)
            - Pack 2:
                    - script 1 (which used by script 2)
                    - script 2 (which uses script 1)
    When:
        - The GR101 validation is executed across the all files
    Then:
        - The validator should pass, everything is valid, sanity check
    """
    graph_interface = repo_test_from_version.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsUsingInvalidFromVersionValidator().obtain_invalid_content_items_using_graph(
            content_items=[]
        )
    )
    assert len(results) == 0


def test_IsUsingInvalidFromVersionValidator_invalid(
    repo_test_from_version: Repo,
):
    """
    Given:
        - A content graph interface with preloaded repository data:
            - Pack 1:
                - playbook (which uses a command from the integration)
                - integration (which contains a command, used by the playbook)
            - Pack 2:
                    - script 1 (which used by script 2, but has fromversion=10.0.0 while script 2 has fromversion=0.0.0)
                    - script 2 (which uses script 1)
    When:
        - The GR101 validation is executed across the second script
    Then:
        - The validator should fail due to target's fromversion higher than source's fromversion. (len(results) == 1)
        - Ensure the error message as expected
    """
    repo_test_from_version.packs[1].scripts[0].set_data(
        **{"fromversion": "10.0.0"}
    )  # This line fails the GR101
    graph_interface = repo_test_from_version.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsUsingInvalidFromVersionValidator().obtain_invalid_content_items_using_graph(
            content_items=[repo_test_from_version.packs[1].scripts[1]]
        )
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "Content item 'UsingDeprecatedScript' whose from_version is '0.0.0'"
        " is using content items: 'DeprecatedScript' whose from_version is higher"
        " (should be <= 0.0.0)"
    )


def test_IsUsingInvalidFromVersionValidator_valid(
    repo_test_from_version: Repo,
):
    """
    Given:
        - A content graph interface with preloaded repository data:
            - Pack 1:
                - playbook (which uses a command from the integration)
                - integration (which contains a command, used by the playbook)
            - Pack 2:
                    - script 1 (which used by script 2, has fromversion=10.0.0)
                    - script 2 (which uses script 1, has fromversion=11.0.0)
    When:
        - The GR101 validation is executed across the second script
    Then:
        - The validator should pass, since script 2 which uses script 1 has a higher fromversion, valid case
    """
    repo_test_from_version.packs[1].scripts[0].set_data(**{"fromversion": "10.0.0"})
    repo_test_from_version.packs[1].scripts[1].set_data(**{"fromversion": "11.0.0"})
    graph_interface = repo_test_from_version.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = (
        IsUsingInvalidFromVersionValidator().obtain_invalid_content_items_using_graph(
            content_items=[repo_test_from_version.packs[1].scripts[1]]
        )
    )
    assert len(results) == 0
