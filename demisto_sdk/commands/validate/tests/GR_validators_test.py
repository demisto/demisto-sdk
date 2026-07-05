from collections import defaultdict
from typing import Optional
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from demisto_sdk.commands.common.constants import GitStatuses, MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.base_content import UnknownContent
from demisto_sdk.commands.content_graph.objects.conf_json import ConfJSON
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.relationship import RelationshipData
from demisto_sdk.commands.validate.tests.test_tools import (
    create_agentix_action_object,
    create_playbook_object,
)
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
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
from demisto_sdk.commands.validate.validators.GR_validators.GR110_is_agentix_action_using_existing_content_item_valid import (
    IsAgentixActionUsingExistingContentItemValidator,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR111_is_agentix_action_display_name_already_exists_valid import (
    IsAgentixActionDisplayNameAlreadyExistsValidator,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR112_is_agentix_action_name_already_exists_valid import (
    IsAgentixActionNameAlreadyExistsValidator,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR114_is_non_mandatory_supported_modules_compatibility_all_files import (
    IsNonMandatorySupportedModulesCompatibilityAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR114_is_non_mandatory_supported_modules_compatibility_list_files import (
    IsNonMandatorySupportedModulesCompatibilityListFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR115_action_name_changed_requires_skill_rn_list_files import (
    IsActionNameChangedRequiresSkillRNValidatorListFiles,
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
def repo_for_test_agentix_skill_unknown_action(graph_repo):
    """A repository with a single pack containing an AgentixSkill whose body
    references an action id that does not exist in the repository."""
    pack = graph_repo.create_pack("SkillPack")
    skill = pack.create_agentix_skill("MySkill")
    skill.create_default_agentix_skill(
        name="My Skill",
        skill_id="my-skill-id",
        skill_content="Use <action=does-not-exist-action> to do the thing.",
    )
    return graph_repo


def test_IsUsingUnknownContentValidator__agentix_skill_missing_action__all_files(
    repo_for_test_agentix_skill_unknown_action: Repo,
):
    """
    Given:
        - A content graph with an AgentixSkill whose body references an action id
          ('does-not-exist-action') that is not present in the repository.
    When:
        - The GR103 validation runs across the entire repository (-a).
    Then:
        - GR103 reports the skill as using unknown content (the missing action).
    """
    graph_interface = repo_for_test_agentix_skill_unknown_action.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingUnknownContentValidatorAllFiles().obtain_invalid_content_items(
        content_items=[]
    )
    assert len(results) == 1
    assert "does-not-exist-action" in results[0].message


def test_IsUsingUnknownContentValidator__agentix_skill_existing_action__all_files(
    graph_repo,
):
    """
    Given:
        - A content graph with an AgentixSkill whose body references an action id
          that DOES exist in the repository (an AgentixAction with that id).
    When:
        - The GR103 validation runs across the entire repository (-a).
    Then:
        - GR103 reports no unknown-content usage for the skill.
    """
    pack = graph_repo.create_pack("SkillPack")
    action = pack.create_agentix_action("MyAction")
    action.create_default_agentix_action()
    # The default action's id comes from its YAML 'commonfields.id'.
    action_id = action.yml.read_dict()["commonfields"]["id"]

    skill = pack.create_agentix_skill("MySkill")
    skill.create_default_agentix_skill(
        name="My Skill",
        skill_id="my-skill-id",
        skill_content=f"Use <action={action_id}> to do the thing.",
    )

    graph_interface = graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsUsingUnknownContentValidatorAllFiles().obtain_invalid_content_items(
        content_items=[]
    )
    # The skill's action reference is resolved, so the skill itself must not be
    # reported as using unknown content. (The default action may have its own
    # unrelated unknown 'underlyingcontentitem' dependency, which is not our concern here.)
    assert not any("My Skill" in result.message for result in results)


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
        "The following mandatory dependencies missing required modules: SearchIncidents is missing: ["
        in results[0].message
    )
    assert results[0].content_object.object_id == "Script1"


@pytest.fixture
def repo_for_test_gr_109_no_supported_modules_in_pack_a_metadata(graph_repo: Repo):
    """
    Creates a test repository for testing GR109 when the caller's pack metadata
    has no supportedModules key.

    Structure:
    - Pack A (PLATFORM): no supportedModules in pack metadata.
                         Script1 has no supportedModules on the item itself either,
                         so it falls back to ALL platform modules.
    - Pack B (PLATFORM): supportedModules: ["module_x"] in pack metadata.
                         SearchIncidents script has no supportedModules on the item,
                         so it inherits ["module_x"] from its pack.

    Script1 calls demisto.executeCommand("SearchIncidents", {}) creating a dependency.
    Because Script1 effectively supports ALL platform modules but SearchIncidents only
    supports ["module_x"], Script1 is invalid.
    """
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
            # No supportedModules - falls back to all platform modules
        }
    )
    pack_a.create_script(
        "Script1", code='demisto.executeCommand("SearchIncidents", {})'
    )

    pack_b = graph_repo.create_pack("Pack B")
    pack_b.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ],
            "supportedModules": ["module_x"],
        }
    )
    yml_search_incidents = {
        "commonfields": {"id": "SearchIncidents", "version": -1},
        "name": "SearchIncidents",
        "comment": "this is script SearchIncidents",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
    }
    pack_b.create_script(
        "SearchIncidents",
        code='demisto.executeCommand("SearchIncidents", {})',
        yml=yml_search_incidents,
    )

    return graph_repo


def test_SupportedModulesCompatibility_no_supported_modules_in_pack_a_metadata(
    repo_for_test_gr_109_no_supported_modules_in_pack_a_metadata: Repo,
):
    """
    Given:
        Pack A has no supportedModules in its pack metadata (falls back to all platform
        modules). Script1 in Pack A depends on SearchIncidents in Pack B, which only
        supports ["module_x"] (inherited from its pack metadata).
    When:
        Running the IsSupportedModulesCompatibility validator on all files.
    Then:
        Script1 is invalid because it effectively requires all platform modules but
        SearchIncidents only supports ["module_x"].
    """
    graph_interface = (
        repo_for_test_gr_109_no_supported_modules_in_pack_a_metadata.create_graph()
    )
    BaseValidator.graph_interface = graph_interface
    results = IsSupportedModulesCompatibilityAllFiles().obtain_invalid_content_items([])

    assert len(results) == 1
    assert results[0].content_object.object_id == "Script1"
    assert "SearchIncidents is missing:" in results[0].message


@pytest.fixture
def repo_for_test_gr_109_mismatch_command(graph_repo: Repo):
    """
    Creates a test repository with a single pack to test the command mismatch part of GR109 validation.

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains Script1, which contain command_x.
              Script1 is configured with `supportedModules: ["module_x"]`.
              command_x is used in the script and configured with `supportedModules: ["module_x", "module_y"]`.
    """
    yml = {
        "commonfields": {"id": "Integration1", "version": -1},
        "name": "Integration1",
        "display": "Integration1",
        "description": "this is an integration Integration1",
        "category": "category",
        "provider": "Integration1",
        "supportedModules": ["module_x"],
        "script": {
            "type": "python",
            "subtype": "python3",
            "script": "-",
            "commands": [
                {
                    "name": "command_x",
                    "description": "description",
                    "arguments": [],
                    "supportedModules": ["module_x", "module_y"],
                }
            ],
            "dockerimage": None,
        },
        "configuration": [],
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
    pack_a.create_integration("Integration1", yml=yml)

    return graph_repo


def test_SupportedModulesCompatibility_invalid_all_files_mismatch_command(
    repo_for_test_gr_109_mismatch_command: Repo,
):
    """
    Given:
        A repository where "command_x" (with `supportedModules: ['module_x', 'module_y']`)
        is included in "Integration1" (with `supportedModules: ['module_x']`).
    When:
        Running the IsSupportedModulesCompatibility validator on all files.
    Then:
        The validator should identify "Integration1" as invalid, reporting that it is missing the required"module_y".
    """
    graph_interface = repo_for_test_gr_109_mismatch_command.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsSupportedModulesCompatibilityAllFiles().obtain_invalid_content_items([])

    assert len(results) == 1
    assert (
        results[0].message
        == "The following mandatory dependencies missing required modules: Integration1 is missing: [module_y]"
    )
    assert results[0].content_object.object_id == "Integration1"


def test_SupportedModulesCompatibility_invalid_list_files_mismatch_command(
    repo_for_test_gr_109_mismatch_command: Repo,
):
    """
    Given:
        A repository where "Script1" (with `supportedModules: ['module_x']`)
        depends on "SearchIncidents", which does not support "module_x".
    When:
        The IsSupportedModulesCompatibility validator runs specifically on "Integration1".
    Then:
        The validator should identify "Integration1" as invalid, reporting it is missing the required "module_y".
    """
    graph_interface = repo_for_test_gr_109_mismatch_command.create_graph()
    BaseValidator.graph_interface = graph_interface

    results = IsSupportedModulesCompatibilityListFiles().obtain_invalid_content_items(
        [repo_for_test_gr_109_mismatch_command.packs[0].integrations[0].object]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "The following mandatory dependencies missing required modules: Integration1 is missing: [module_y]"
    )
    assert results[0].content_object.object_id == "Integration1"


@pytest.fixture
def repo_for_test_gr_109_mismatch_playbook(graph_repo: Repo):
    """
    Creates a test repository with a single pack to test the playbook mismatch part of GR109 validation.

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains a playbook named playbook1 and a command named command_x.
              playbook1 uses command_x.
              playbook1 is configured with `supportedModules: ["module_x"]`.
              command_x does not support "module_x".
    """
    # Create the pack
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.set_data(marketplaces=[MarketplaceVersions.PLATFORM.value])
    integration1 = pack_a.create_integration(name="integration1")
    integration1.set_data(
        script={
            "type": "python",
            "subtype": "python3",
            "script": "-",
            "commands": [
                {
                    "name": "command_x",
                    "description": "description",
                    "arguments": [],
                    "supportedModules": ["module_x"],
                }
            ],
            "dockerimage": None,
        }
    )

    # Create the playbook that uses command_x with supportedModules
    # starttaskid and nexttasks ensure task "0" is on the mandatory execution path
    playbook_yml = {
        "id": "playbook1",
        "name": "playbook1",
        "starttaskid": "0",
        "supportedModules": ["module_x", "module_y"],
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "0",
                "type": "regular",
                "nexttasks": {"#none#": ["1"]},
                "task": {
                    "id": "0",
                    "name": "run command_x",
                    "description": "Uses command_x",
                    "script": "command_x",
                    "type": "regular",
                    "iscommand": True,
                    "brand": "Integration1",
                },
            },
            "1": {
                "id": "1",
                "taskid": "1",
                "type": "title",
                "task": {
                    "id": "1",
                    "name": "Done",
                    "type": "title",
                    "iscommand": False,
                    "brand": "",
                },
            },
        },
    }
    pack_a.create_playbook("playbook1", yml=playbook_yml)

    return graph_repo


def test_SupportedModulesCompatibility_invalid_all_files_mismatch_playbook(
    repo_for_test_gr_109_mismatch_playbook: Repo,
):
    """
    Given:
        A repository where "playbook1" (with `supportedModules: ['module_x']`)
        depends on "command_x", which does not support "module_x".
    When:
        Running the IsSupportedModulesCompatibility validator on all files.
    Then:
        The validator should identify "playbook1" as invalid, reporting that "command_x" is missing "module_x".
    """
    graph_interface = repo_for_test_gr_109_mismatch_playbook.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsSupportedModulesCompatibilityAllFiles().obtain_invalid_content_items([])

    assert len(results) == 1
    assert (
        results[0].message
        == "Module compatibility issue detected for mandatory dependency: Content item 'playbook1' has incompatible commands: [command_x]. Make sure the commands used are supported by the same modules as the content item."
    )
    assert results[0].content_object.object_id == "playbook1"


def test_SupportedModulesCompatibility_invalid_list_files_mismatch_playbook(
    repo_for_test_gr_109_mismatch_playbook: Repo,
):
    """
    Given:
        A repository where "playbook1" (with `supportedModules: ['module_x']`)
        depends on "command_x", which does not support "module_x".
    When:
        The IsSupportedModulesCompatibility validator runs specifically on "playbook1".
    Then:
        The validator should identify "playbook1" as invalid, reporting that "command_x"
        is missing the required "module_x".
    """
    graph_interface = repo_for_test_gr_109_mismatch_playbook.create_graph()
    BaseValidator.graph_interface = graph_interface

    results = IsSupportedModulesCompatibilityListFiles().obtain_invalid_content_items(
        [repo_for_test_gr_109_mismatch_playbook.packs[0].playbooks[0].object]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "Module compatibility issue detected for mandatory dependency: Content item 'playbook1' has incompatible commands: [command_x]. Make sure the commands used are supported by the same modules as the content item."
    )
    assert results[0].content_object.object_id == "playbook1"


@pytest.fixture
def repo_for_test_gr_109_cache_pollution(graph_repo: Repo):
    """
    Creates a test repository to reproduce the GR109 shared-cache pollution bug.

    Structure:
    - Pack A (platform marketplace), one integration with two commands:
        - command_x: supportedModules ["module_x"]  -> genuine mismatch with playbook1
        - safe_command: no supportedModules         -> supports all, can never mismatch
    - playbook1: supportedModules ["module_x", "module_y"], using BOTH commands on the
      mandatory execution path.
    """
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.set_data(marketplaces=[MarketplaceVersions.PLATFORM.value])
    integration1 = pack_a.create_integration(name="integration1")
    integration1.set_data(
        script={
            "type": "python",
            "subtype": "python3",
            "script": "-",
            "commands": [
                {
                    "name": "command_x",
                    "description": "description",
                    "arguments": [],
                    "supportedModules": ["module_x"],
                },
                {
                    "name": "safe_command",
                    "description": "description",
                    "arguments": [],
                },
            ],
            "dockerimage": None,
        }
    )

    playbook_yml = {
        "id": "playbook1",
        "name": "playbook1",
        "starttaskid": "0",
        "supportedModules": ["module_x", "module_y"],
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "0",
                "type": "regular",
                "nexttasks": {"#none#": ["1"]},
                "task": {
                    "id": "0",
                    "name": "run command_x",
                    "description": "Uses command_x",
                    "script": "command_x",
                    "type": "regular",
                    "iscommand": True,
                    "brand": "Integration1",
                },
            },
            "1": {
                "id": "1",
                "taskid": "1",
                "type": "regular",
                "nexttasks": {"#none#": ["2"]},
                "task": {
                    "id": "1",
                    "name": "run safe_command",
                    "description": "Uses safe_command",
                    "script": "safe_command",
                    "type": "regular",
                    "iscommand": True,
                    "brand": "Integration1",
                },
            },
            "2": {
                "id": "2",
                "taskid": "2",
                "type": "title",
                "task": {
                    "id": "2",
                    "name": "Done",
                    "type": "title",
                    "iscommand": False,
                    "brand": "",
                },
            },
        },
    }
    pack_a.create_playbook("playbook1", yml=playbook_yml)

    return graph_repo


def test_GR109_ignores_safe_commands_after_cache_pollution(
    repo_for_test_gr_109_cache_pollution: Repo,
):
    """
    Given:
        A platform playbook ("playbook1", supportedModules ['module_x', 'module_y'])
        that uses both "command_x" (supportedModules ['module_x'] -> genuine mismatch)
        and "safe_command" (no supportedModules -> supports all, never a mismatch).
    When:
        Another validator first loads ALL of the playbook's USES relationships into the
        shared graph cache (simulated via graph.search), and then the
        IsSupportedModulesCompatibility validator runs on all files.
    Then:
        Only "command_x" is reported as incompatible; "safe_command" must NOT appear.
    """
    graph_interface = repo_for_test_gr_109_cache_pollution.create_graph()
    BaseValidator.graph_interface = graph_interface

    # Simulate a prior validator (e.g. PB131) loading the playbook's full USES set into
    # the shared, append-only cache.
    graph_interface.search(content_type=ContentType.PLAYBOOK, object_id="playbook1")

    # Sanity-check that the cache is actually polluted with BOTH commands, so this test
    # would fail on the pre-fix (unguarded) handler.
    playbook_obj = next(
        obj
        for obj in graph_interface._id_to_obj.values()
        if getattr(obj, "object_id", None) == "playbook1"
    )
    used_command_ids = {rel.content_item_to.object_id for rel in playbook_obj.uses}
    assert {"command_x", "safe_command"} <= used_command_ids

    results = IsSupportedModulesCompatibilityAllFiles().obtain_invalid_content_items([])

    assert len(results) == 1
    assert results[0].content_object.object_id == "playbook1"
    assert "command_x" in results[0].message
    assert "safe_command" not in results[0].message


@pytest.fixture
def repo_for_test_gr_114(graph_repo: Repo):
    """
    Creates a test repository for testing GR114 validator (non-mandatory dependencies).

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains an IndicatorType "MyIndicatorType" with `supportedModules: ["module_x"]`
              that has a non-mandatory dependency on script "ReputationScript" via reputationScriptName.
    - Pack B: Contains "ReputationScript" with `supportedModules: ["module_y"]`.
              Note: "ReputationScript" does *not* list "module_x" in its supportedModules.

    The indicator_type -> script dependency via reputationScriptName is non-mandatory (is_mandatory=False),
    which is what GR114 validates.
    """
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
        }
    )
    pack_a.create_indicator_type(
        "MyIndicatorType",
        content={
            "id": "MyIndicatorType",
            "details": "MyIndicatorType",
            "preProcessingScript": "",
            "fromVersion": "6.10.0",
            "reputationScriptName": "ReputationScript",
            "supportedModules": ["module_x"],
        },
    )

    pack_b = graph_repo.create_pack("Pack B")
    pack_b.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
        }
    )
    script_yml = {
        "commonfields": {"id": "ReputationScript", "version": -1},
        "name": "ReputationScript",
        "comment": "Reputation script",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
        "supportedModules": ["module_y"],
    }
    pack_b.create_script("ReputationScript", yml=script_yml)

    return graph_repo


def test_NonMandatorySupportedModulesCompatibility_invalid_all_files(
    repo_for_test_gr_114: Repo,
):
    """
    Given:
        A repository where "MyIndicatorType" (with `supportedModules: ['module_x']`)
        has a non-mandatory dependency on "ReputationScript", which does not support "module_x".
    When:
        Running the IsNonMandatorySupportedModulesCompatibility validator on all files.
    Then:
        The validator should identify "MyIndicatorType" as invalid (warning), reporting that
        "ReputationScript" is missing "module_x".
    """
    graph_interface = repo_for_test_gr_114.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsNonMandatorySupportedModulesCompatibilityAllFiles().obtain_invalid_content_items(
        []
    )

    assert len(results) == 1
    assert (
        results[0].message
        == "The following non-mandatory dependencies have missing required modules: ReputationScript is missing: [module_x]"
    )
    assert results[0].content_object.object_id == "MyIndicatorType"


def test_NonMandatorySupportedModulesCompatibility_invalid_list_files(
    repo_for_test_gr_114: Repo,
):
    """
    Given:
        A repository where "MyIndicatorType" (with `supportedModules: ['module_x']`)
        has a non-mandatory dependency on "ReputationScript", which does not support "module_x".
    When:
        The IsNonMandatorySupportedModulesCompatibility validator runs specifically on "MyIndicatorType".
    Then:
        The validator should identify "MyIndicatorType" as invalid (warning), reporting that
        "ReputationScript" is missing the required "module_x".
    """
    graph_interface = repo_for_test_gr_114.create_graph()
    BaseValidator.graph_interface = graph_interface

    results = IsNonMandatorySupportedModulesCompatibilityListFiles().obtain_invalid_content_items(
        [repo_for_test_gr_114.packs[0].indicator_types[0].object]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "The following non-mandatory dependencies have missing required modules: ReputationScript is missing: [module_x]"
    )
    assert results[0].content_object.object_id == "MyIndicatorType"


@pytest.fixture
def repo_for_test_gr_114_valid(graph_repo: Repo):
    """
    Creates a test repository for testing GR114 validator where the dependency is valid.

    This fixture sets up a graph repository where "MyIndicatorType" has a non-mandatory
    dependency on "ReputationScript", and "ReputationScript" supports all modules that
    "MyIndicatorType" supports.
    """
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
        }
    )
    pack_a.create_indicator_type(
        "MyIndicatorType",
        content={
            "id": "MyIndicatorType",
            "details": "MyIndicatorType",
            "preProcessingScript": "",
            "fromVersion": "6.10.0",
            "reputationScriptName": "ReputationScript",
            "supportedModules": ["module_x"],
        },
    )

    pack_b = graph_repo.create_pack("Pack B")
    pack_b.pack_metadata.update(
        {
            "marketplaces": [
                MarketplaceVersions.MarketplaceV2.value,
                MarketplaceVersions.PLATFORM.value,
            ]
        }
    )
    script_yml = {
        "commonfields": {"id": "ReputationScript", "version": -1},
        "name": "ReputationScript",
        "comment": "Reputation script",
        "type": "python",
        "subtype": "python3",
        "script": "-",
        "skipprepare": [],
        "supportedModules": ["module_x", "module_y"],
    }
    pack_b.create_script("ReputationScript", yml=script_yml)

    return graph_repo


def test_NonMandatorySupportedModulesCompatibility_valid_all_files(
    repo_for_test_gr_114_valid: Repo,
):
    """
    Given:
        A repository where "MyIndicatorType" (with `supportedModules: ['module_x']`)
        has a non-mandatory dependency on "ReputationScript", which supports "module_x".
    When:
        Running the IsNonMandatorySupportedModulesCompatibility validator on all files.
    Then:
        The validator should pass with no results.
    """
    graph_interface = repo_for_test_gr_114_valid.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsNonMandatorySupportedModulesCompatibilityAllFiles().obtain_invalid_content_items(
        []
    )

    assert len(results) == 0


@pytest.fixture
def repo_for_test_gr_114_mismatch_command(graph_repo: Repo):
    """
    Creates a test repository to test the command mismatch part of GR114 validation.

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains Integration1 with `supportedModules: ["module_x"]`.
              Integration1 has command_x with `supportedModules: ["module_x", "module_y"]`.
    """
    yml = {
        "commonfields": {"id": "Integration1", "version": -1},
        "name": "Integration1",
        "display": "Integration1",
        "description": "this is an integration Integration1",
        "category": "category",
        "provider": "Integration1",
        "supportedModules": ["module_x"],
        "script": {
            "type": "python",
            "subtype": "python3",
            "script": "-",
            "commands": [
                {
                    "name": "command_x",
                    "description": "description",
                    "arguments": [],
                    "supportedModules": ["module_x", "module_y"],
                }
            ],
            "dockerimage": None,
        },
        "configuration": [],
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
    pack_a.create_integration("Integration1", yml=yml)

    return graph_repo


def test_NonMandatorySupportedModulesCompatibility_invalid_all_files_mismatch_command(
    repo_for_test_gr_114_mismatch_command: Repo,
):
    """
    Given:
        A repository where "command_x" (with `supportedModules: ['module_x', 'module_y']`)
        is included in "Integration1" (with `supportedModules: ['module_x']`).
    When:
        Running the IsNonMandatorySupportedModulesCompatibility validator on all files.
    Then:
        The validator should not flag command-level mismatches for non-mandatory dependencies,
        since GR114 only checks non-mandatory USES relationships (not HAS_COMMAND relationships).
        Command-level module mismatches are only checked by GR109 (mandatory dependencies).
    """
    graph_interface = repo_for_test_gr_114_mismatch_command.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsNonMandatorySupportedModulesCompatibilityAllFiles().obtain_invalid_content_items(
        []
    )

    assert len(results) == 0


def test_NonMandatorySupportedModulesCompatibility_invalid_list_files_mismatch_command(
    repo_for_test_gr_114_mismatch_command: Repo,
):
    """
    Given:
        A repository where "command_x" (with `supportedModules: ['module_x', 'module_y']`)
        is included in "Integration1" (with `supportedModules: ['module_x']`).
    When:
        The IsNonMandatorySupportedModulesCompatibility validator runs specifically on "Integration1".
    Then:
        The validator should not flag command-level mismatches for non-mandatory dependencies,
        since GR114 only checks non-mandatory USES relationships (not HAS_COMMAND relationships).
        Command-level module mismatches are only checked by GR109 (mandatory dependencies).
    """
    graph_interface = repo_for_test_gr_114_mismatch_command.create_graph()
    BaseValidator.graph_interface = graph_interface

    results = IsNonMandatorySupportedModulesCompatibilityListFiles().obtain_invalid_content_items(
        [repo_for_test_gr_114_mismatch_command.packs[0].integrations[0].object]
    )
    assert len(results) == 0


@pytest.fixture
def repo_for_test_gr_114_mismatch_playbook(graph_repo: Repo):
    """
    Creates a test repository to test the playbook/content-item mismatch part of GR114 validation.

    This fixture sets up a graph repository with the following structure:
    - Pack A: Contains a playbook named playbook1 and a command named command_x.
              playbook1 uses command_x.
              playbook1 is configured with `supportedModules: ["module_x", "module_y"]`.
              command_x only supports "module_x".
    """
    pack_a = graph_repo.create_pack("Pack A")
    pack_a.set_data(marketplaces=[MarketplaceVersions.PLATFORM.value])
    integration1 = pack_a.create_integration(name="integration1")
    integration1.set_data(
        script={
            "type": "python",
            "subtype": "python3",
            "script": "-",
            "commands": [
                {
                    "name": "command_x",
                    "description": "description",
                    "arguments": [],
                    "supportedModules": ["module_x"],
                }
            ],
            "dockerimage": None,
        }
    )

    playbook_yml = {
        "id": "playbook1",
        "name": "playbook1",
        "supportedModules": ["module_x", "module_y"],
        "tasks": {
            "0": {
                "id": "0",
                "taskid": "0",
                "type": "regular",
                "task": {
                    "id": "0",
                    "name": "run command_x",
                    "description": "Uses command_x",
                    "script": "command_x",
                    "type": "regular",
                    "iscommand": True,
                    "brand": "Integration1",
                },
            }
        },
    }
    pack_a.create_playbook("playbook1", yml=playbook_yml)

    return graph_repo


def test_NonMandatorySupportedModulesCompatibility_invalid_all_files_mismatch_playbook(
    repo_for_test_gr_114_mismatch_playbook: Repo,
):
    """
    Given:
        A repository where "playbook1" (with `supportedModules: ['module_x', 'module_y']`)
        uses "command_x", which only supports "module_x".
    When:
        Running the IsNonMandatorySupportedModulesCompatibility validator on all files.
    Then:
        The validator should identify "playbook1" as invalid (warning), reporting that
        "command_x" is missing "module_y".
    """
    graph_interface = repo_for_test_gr_114_mismatch_playbook.create_graph()
    BaseValidator.graph_interface = graph_interface
    results = IsNonMandatorySupportedModulesCompatibilityAllFiles().obtain_invalid_content_items(
        []
    )

    assert len(results) == 1
    assert (
        results[0].message
        == "Module compatibility issue detected for non-mandatory dependency: Content item 'playbook1' has incompatible commands: [command_x]. Make sure the commands used are supported by the same modules as the content item."
    )
    assert results[0].content_object.object_id == "playbook1"


def test_NonMandatorySupportedModulesCompatibility_invalid_list_files_mismatch_playbook(
    repo_for_test_gr_114_mismatch_playbook: Repo,
):
    """
    Given:
        A repository where "playbook1" (with `supportedModules: ['module_x', 'module_y']`)
        uses "command_x", which only supports "module_x".
    When:
        The IsNonMandatorySupportedModulesCompatibility validator runs specifically on "playbook1".
    Then:
        The validator should identify "playbook1" as invalid (warning), reporting that
        "command_x" is missing the required "module_y".
    """
    graph_interface = repo_for_test_gr_114_mismatch_playbook.create_graph()
    BaseValidator.graph_interface = graph_interface

    results = IsNonMandatorySupportedModulesCompatibilityListFiles().obtain_invalid_content_items(
        [repo_for_test_gr_114_mismatch_playbook.packs[0].playbooks[0].object]
    )
    assert len(results) == 1
    assert (
        results[0].message
        == "Module compatibility issue detected for non-mandatory dependency: Content item 'playbook1' has incompatible commands: [command_x]. Make sure the commands used are supported by the same modules as the content item."
    )
    assert results[0].content_object.object_id == "playbook1"


@pytest.fixture
def repo_for_test_gr_110(graph_repo: Repo):
    """
    Creates a test repository for testing GR110 validator.
    """
    # Pack 1: Simple integration and script
    pack_1 = graph_repo.create_pack("Pack1")

    # Create integration with commands
    integration = pack_1.create_integration("MyIntegration")
    integration.set_commands(["test-command", "get-incidents"])

    # Create simple script
    pack_1.create_script("MyScript")

    # Create simple playbook
    pack_1.create_playbook("MyPlaybook")

    return graph_repo


def test_gr110_missing_underlying_command(repo_for_test_gr_110: Repo):
    """
    Given:
        - An Agentix Action referencing a non-existing command.
    When:
        - Running the GR110 validator.
    Then:
        - A validation error should be returned indicating the content item was not found.
    """
    action = create_agentix_action_object(
        action_name="TestAction",
        paths=[
            "underlyingcontentitem.name",
            "underlyingcontentitem.id",
            "underlyingcontentitem.type",
            "underlyingcontentitem.command",
        ],
        values=[
            "MyIntegration",
            "MyIntegration",
            "command",
            "nonexistent-command",
        ],
    )

    graph_interface = repo_for_test_gr_110.create_graph()
    BaseValidator.graph_interface = graph_interface

    validator = IsAgentixActionUsingExistingContentItemValidator()
    results = validator.obtain_invalid_content_items_using_graph([action], False)

    assert "could not be found in the Content repository" in results[0].message


def test_gr110_unsupported_content_type(repo_for_test_gr_110: Repo):
    """
    Given:
        - An Agentix Action referencing an unsupported content type (widget).
    When:
        - Running the GR110 validator.
    Then:
        - A validation error should be returned about unsupported content type.
    """
    action = create_agentix_action_object(
        action_name="TestAction",
        paths=[
            "underlyingcontentitem.name",
            "underlyingcontentitem.id",
            "underlyingcontentitem.type",
        ],
        values=[
            "MyIntegration",
            "MyIntegration",
            "widget",  # unsupported type
        ],
    )

    graph_interface = repo_for_test_gr_110.create_graph()
    BaseValidator.graph_interface = graph_interface

    validator = IsAgentixActionUsingExistingContentItemValidator()
    results = validator.obtain_invalid_content_items_using_graph([action], False)

    assert len(results) == 1
    assert "unsupported in Agentix" in results[0].message


def test_gr110_builtin_command_skipped(repo_for_test_gr_110: Repo):
    """
    Given:
        - An Agentix Action referencing a built-in command.
    When:
        - Running the GR110 validator.
    Then:
        - No validation errors should be reported (built-in commands are skipped).
    """
    action = create_agentix_action_object(
        action_name="TestAction",
        paths=[
            "underlyingcontentitem.name",
            "underlyingcontentitem.type",
            "underlyingcontentitem.id",
        ],
        values=[
            "_builtin_",
            "command",
            "_builtin_",
        ],
    )

    graph_interface = repo_for_test_gr_110.create_graph()
    BaseValidator.graph_interface = graph_interface

    validator = IsAgentixActionUsingExistingContentItemValidator()
    results = validator.obtain_invalid_content_items_using_graph([action], False)

    assert len(results) == 0


def test_gr110_valid_command_reference(repo_for_test_gr_110: Repo, mocker):
    """
    Given:
        - An Agentix Action referencing an existing integration command.
    When:
        - Running the GR110 validator.
    Then:
        - No validation errors should be reported.
    """
    action = create_agentix_action_object(
        action_name="TestAction",
        paths=[
            "underlyingcontentitem.name",
            "underlyingcontentitem.type",
            "underlyingcontentitem.id",
            "underlyingcontentitem.command",
        ],
        values=[
            "MyIntegration",
            "command",
            "MyIntegration",
            "test-command",
        ],
    )

    graph_interface = repo_for_test_gr_110.create_graph()
    BaseValidator.graph_interface = graph_interface

    validator = IsAgentixActionUsingExistingContentItemValidator()

    mock_command_node = mocker.Mock()
    mocker.patch.object(validator.graph, "search", return_value=[mock_command_node])

    results = validator.obtain_invalid_content_items_using_graph([action], False)

    assert len(results) == 1


def test_gr110_valid_script_reference(repo_for_test_gr_110: Repo, mocker):
    """
    Given:
        - An Agentix Action referencing an existing script.
    When:
        - Running the GR110 validator.
    Then:
        - No validation errors should be reported.
    """
    action = create_agentix_action_object(
        action_name="TestAction",
        paths=[
            "underlyingcontentitem.name",
            "underlyingcontentitem.type",
            "underlyingcontentitem.id",
            "underlyingcontentitem.command",
        ],
        values=[
            "MyScript",
            "script",
            "MyScript",
            "",
        ],
    )

    graph_interface = repo_for_test_gr_110.create_graph()
    BaseValidator.graph_interface = graph_interface

    validator = IsAgentixActionUsingExistingContentItemValidator()
    mock_script_node = mocker.Mock()
    mocker.patch.object(validator.graph, "search", return_value=[mock_script_node])

    results = validator.obtain_invalid_content_items_using_graph([action], False)

    assert len(results) == 0


def test_gr110_valid_playbook_reference(repo_for_test_gr_110: Repo, mocker):
    """
    Given:
        - An Agentix Action referencing an existing playbook.
    When:
        - Running the GR110 validator.
    Then:
        - No validation errors should be reported.
    """
    action = create_agentix_action_object(
        action_name="TestAction",
        paths=[
            "underlyingcontentitem.name",
            "underlyingcontentitem.type",
            "underlyingcontentitem.id",
            "underlyingcontentitem.command",
        ],
        values=["MyPlaybook", "playbook", "MyPlaybook", ""],
    )

    graph_interface = repo_for_test_gr_110.create_graph()
    BaseValidator.graph_interface = graph_interface

    validator = IsAgentixActionUsingExistingContentItemValidator()
    mock_playbook_node = mocker.Mock()
    mocker.patch.object(validator.graph, "search", return_value=[mock_playbook_node])

    results = validator.obtain_invalid_content_items_using_graph([action], False)

    assert len(results) == 0


def test_IsAgentixActionNameAlreadyExistsValidator_obtain_invalid_content_items_using_graph(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, with 1 agentix action in each, and 2 of them are with the same name
    When
        - running IsAgentixActionNameAlreadyExistsValidator obtain_invalid_content_items function, on one of the packs with the duplicate agentix action name.
    Then
        - Validate that we got the error messages for the duplicate name.
    """
    graph_repo.setup_one_pack(name="pack1")
    graph_repo.setup_one_pack(name="pack2")
    graph_repo.setup_one_pack(name="pack3")
    graph_repo.packs[1].agentix_actions[0].set_agentix_action_name("test")
    graph_repo.packs[2].agentix_actions[0].set_agentix_action_name("test")

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsAgentixActionNameAlreadyExistsValidator().obtain_invalid_content_items_using_graph(
        [
            graph_repo.packs[0].agentix_actions[0],
            graph_repo.packs[2].agentix_actions[0],
        ],
        validate_all_files=False,
    )

    assert len(results) == 1


def test_IsAgentixActionDisplayNameAlreadyExistsValidator_obtain_invalid_content_items_using_graph(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, with 1 agentix action in each, and 2 of them are with the same display name
    When
        - running IsAgentixActionDisplayNameAlreadyExistsValidator obtain_invalid_content_items function, on one of the packs with the duplicate agentix action display.
    Then
        - Validate that we got the error messages for the duplicate display name.
    """
    graph_repo.setup_one_pack(name="pack1")
    graph_repo.setup_one_pack(name="pack2")
    graph_repo.setup_one_pack(name="pack3")
    graph_repo.packs[1].agentix_actions[0].set_agentix_action_display("test")
    graph_repo.packs[2].agentix_actions[0].set_agentix_action_display("test")

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsAgentixActionDisplayNameAlreadyExistsValidator().obtain_invalid_content_items_using_graph(
        [
            graph_repo.packs[0].agentix_actions[0],
            graph_repo.packs[2].agentix_actions[0],
        ],
        validate_all_files=False,
    )

    assert len(results) == 1


# --- GR113 Tests ---


def _create_playbook_with_uses(
    playbook_name: str, dependency_names: list[str]
) -> Playbook:
    """Helper to create a Playbook with pre-populated USES relationships."""
    playbook = create_playbook_object(paths=["name"], values=[playbook_name])
    relationships: defaultdict[RelationshipType, set[RelationshipData]] = defaultdict(
        set
    )
    for idx, dep_name in enumerate(dependency_names):
        target_id = f"db-{dep_name}-{idx}"
        dep_node = UnknownContent(
            object_id=dep_name, name=dep_name, database_id=target_id
        )
        relationships[RelationshipType.USES].add(
            RelationshipData(
                relationship_type=RelationshipType.USES,
                source_id=f"db-{playbook_name}",
                target_id=target_id,
                content_item_to=dep_node,
            )
        )
    playbook.relationships_data = relationships
    return playbook


@pytest.mark.parametrize(
    "source, dep_names, expected_count",
    [
        ("autonomous", ["RegularPackScript"], 1),
        ("partner", ["NonPartnerScript"], 1),
        ("autonomous", ["Script1", "Script2", "Script3"], 1),
        ("autonomous", [], 0),  # no invalid deps → graph returns empty
    ],
    ids=["autonomous-invalid", "partner-invalid", "multiple-deps", "no-invalid-deps"],
)
def test_managed_playbook_dependencies_all_files(
    mocker, source, dep_names, expected_count
):
    """
    Given:
        - A playbook in a managed pack with the given source and invalid dependencies.
    When:
        - Running IsValidManagedPlaybookDependenciesValidatorAllFiles.
    Then:
        - The expected number of validation results is returned, with source in the message.
    """
    from demisto_sdk.commands.validate.validators.GR_validators.GR113_is_valid_managed_playbook_dependencies_all_files import (
        IsValidManagedPlaybookDependenciesValidatorAllFiles,
    )

    graph_return = []
    if dep_names:
        graph_return = [(_create_playbook_with_uses("TestPlaybook", dep_names), source)]

    mock_graph = MagicMock()
    mock_graph.find_managed_playbooks_with_invalid_dependencies.return_value = (
        graph_return
    )
    BaseValidator.graph_interface = mock_graph
    mocker.patch(
        "demisto_sdk.commands.validate.validators.GR_validators"
        ".GR113_is_valid_managed_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )

    results = IsValidManagedPlaybookDependenciesValidatorAllFiles().obtain_invalid_content_items(
        []
    )
    assert len(results) == expected_count
    if expected_count:
        assert source in results[0].message
        for dep in dep_names:
            assert dep in results[0].message


def test_managed_playbook_dependencies_list_files(mocker):
    """
    Given:
        - A playbook in a managed pack with an invalid sub-playbook dependency.
    When:
        - Running IsValidManagedPlaybookDependenciesValidatorListFiles.
    Then:
        - One validation result is returned with the dependency name in the message.
    """
    from demisto_sdk.commands.validate.validators.GR_validators.GR113_is_valid_managed_playbook_dependencies_list_files import (
        IsValidManagedPlaybookDependenciesValidatorListFiles,
    )

    playbook = _create_playbook_with_uses("ManagedPB", ["BadSubPlaybook"])
    mock_graph = MagicMock()
    mock_graph.find_managed_playbooks_with_invalid_dependencies.return_value = [
        (playbook, "autonomous")
    ]
    BaseValidator.graph_interface = mock_graph
    mocker.patch(
        "demisto_sdk.commands.validate.validators.GR_validators"
        ".GR113_is_valid_managed_playbook_dependencies.get_core_pack_list",
        return_value=["Base", "CommonScripts"],
    )
    results = IsValidManagedPlaybookDependenciesValidatorListFiles().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == 1
    assert "BadSubPlaybook" in results[0].message


def test_IsAgentixActionNameAlreadyExistsValidator_non_overlapping_versions(
    graph_repo: Repo,
):
    """
    Given:
        A pack with two Agentix Actions with the same name but non-overlapping version ranges.
    When:
        Running IsAgentixActionNameAlreadyExistsValidator.
    Then:
        No validation errors should be reported since they target different version ranges.
    """
    pack = graph_repo.create_pack("pack1")
    action1 = pack.create_agentix_action("action_v1")
    action1.create_default_agentix_action(
        name="test", action_id="test_v1", display="test"
    )
    action1.yml.update({"fromversion": "8.0.0", "toversion": "8.14.0"})

    action2 = pack.create_agentix_action("action_v2")
    action2.create_default_agentix_action(
        name="test", action_id="test_v2", display="test"
    )
    action2.yml.update({"fromversion": "8.15.0", "toversion": "99.99.99"})

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsAgentixActionNameAlreadyExistsValidator().obtain_invalid_content_items_using_graph(
        [action1, action2],
        validate_all_files=True,
    )

    assert len(results) == 0


def test_IsAgentixActionDisplayNameAlreadyExistsValidator_non_overlapping_versions(
    graph_repo: Repo,
):
    """
    Given:
        A pack with two Agentix Actions with the same display name but non-overlapping version ranges.
    When:
        Running IsAgentixActionDisplayNameAlreadyExistsValidator.
    Then:
        No validation errors should be reported since they target different version ranges.
    """
    pack = graph_repo.create_pack("pack1")
    action1 = pack.create_agentix_action("action_v1")
    action1.create_default_agentix_action(
        name="test_v1", action_id="test_v1", display="test"
    )
    action1.yml.update({"fromversion": "8.0.0", "toversion": "8.14.0"})

    action2 = pack.create_agentix_action("action_v2")
    action2.create_default_agentix_action(
        name="test_v2", action_id="test_v2", display="test"
    )
    action2.yml.update({"fromversion": "8.15.0", "toversion": "99.99.99"})

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsAgentixActionDisplayNameAlreadyExistsValidator().obtain_invalid_content_items_using_graph(
        [action1, action2],
        validate_all_files=True,
    )

    assert len(results) == 0


def _build_repo_with_skill_using_action(graph_repo: Repo):
    """Create a repo with an AgentixAction and an AgentixSkill that references it.

    Returns the (graph_interface, action_object, action_id) tuple, where
    ``action_object`` is the graph-resolved AgentixAction whose ``used_by``
    relationship points to the skill. The skill references the action by its id
    (``commonfields.id``), which is what GR115 uses to resolve dependents.
    """
    pack = graph_repo.create_pack("SkillPack")
    action = pack.create_agentix_action("MyAction")
    action.create_default_agentix_action()
    action_id = action.yml.read_dict()["commonfields"]["id"]

    skill = pack.create_agentix_skill("MySkill")
    skill.create_default_agentix_skill(
        name="My Skill",
        skill_id="my-skill-id",
        skill_content=f"Use <action={action_id}> to do the thing.",
    )

    graph_interface = graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface

    action_objects = graph_interface.search(
        content_type=ContentType.AGENTIX_ACTION, object_id=action_id
    )
    assert action_objects, "expected the action to exist in the graph"
    return graph_interface, action_objects[0], action_id


def _make_skill_with_pack_versions(
    mocker,
    *,
    old_version: Optional[str],
    current_version: Optional[str],
    has_old_baseline: bool = True,
    pack: object = "__unset__",
):
    """Build a mock dependent AgentixSkill whose pack exposes versions.

    ``was_pack_version_bumped`` reads ``pack.current_version`` and
    ``pack.old_base_content_object.current_version``, where ``pack`` is the
    skill's ``in_pack`` property. This helper lets tests control those two
    values directly (repo-agnostic), simulate a brand-new pack (no master
    baseline) or a missing pack.
    """
    skill = mocker.Mock()
    skill.object_id = "my-skill-id"
    skill.pack_id = "SkillPack"

    if pack != "__unset__":
        skill.in_pack = pack
        return skill

    pack_mock = mocker.Mock()
    pack_mock.current_version = current_version
    if has_old_baseline:
        # ``was_pack_version_bumped`` requires the master baseline to be a real
        # ``Pack`` (it guards with ``isinstance(old_obj, Pack)``), so spec the
        # mock to that class for the isinstance check to pass.
        old_baseline = mocker.Mock(spec=Pack)
        old_baseline.current_version = old_version
        pack_mock.old_base_content_object = old_baseline
    else:
        pack_mock.old_base_content_object = None
    skill.in_pack = pack_mock
    return skill


def _renamed_action(mocker, graph_repo: Repo):
    """Build a graph-resolved action whose 'name' changed vs. its old version."""
    _, action, _ = _build_repo_with_skill_using_action(graph_repo)
    old_action = mocker.Mock()
    old_action.name = "Old Action Name"  # name changed
    action.git_status = GitStatuses.MODIFIED
    action.old_base_content_object = old_action
    return action


def test_GR115_action_renamed_skill_missing_rn(mocker, graph_repo: Repo):
    """
    Given:
        - An AgentixAction whose 'name' field changed and whose dependent skill's
          pack version was NOT bumped (same version on branch and master).
    When:
        - Running the GR115 validator on the renamed action.
    Then:
        - A single validation error is returned for the dependent skill.
    """
    action = _renamed_action(mocker, graph_repo)

    skill = _make_skill_with_pack_versions(
        mocker, old_version="1.0.0", current_version="1.0.0"
    )
    mocker.patch.object(
        IsActionNameChangedRequiresSkillRNValidatorListFiles,
        "get_dependent_skills",
        return_value=[skill],
    )

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 1
    assert "Old Action Name" in results[0].message
    assert "my-skill-id" in results[0].message


def test_GR115_action_renamed_skill_has_rn(mocker, graph_repo: Repo):
    """
    Given:
        - An AgentixAction whose 'name' field changed and whose dependent skill's
          pack version WAS bumped (branch version > master version).
    When:
        - Running the GR115 validator on the renamed action.
    Then:
        - No validation error is returned.
    """
    action = _renamed_action(mocker, graph_repo)

    skill = _make_skill_with_pack_versions(
        mocker, old_version="1.0.0", current_version="1.0.1"
    )
    mocker.patch.object(
        IsActionNameChangedRequiresSkillRNValidatorListFiles,
        "get_dependent_skills",
        return_value=[skill],
    )

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 0


def test_GR115_cross_repo_skill_with_bump_passes(mocker, graph_repo: Repo):
    """
    Given:
        - A renamed AgentixAction (e.g. in `content`) and a dependent skill that
          lives in a different repo (e.g. `content-private`). The skill is a graph
          node with NO git-status (None), but its pack version WAS bumped vs.
          master.
    When:
        - Running the GR115 validator on the renamed action.
    Then:
        - No validation error is returned, because the version-bump check is
          repo-agnostic and recognizes the bump despite missing git-status.
    """
    action = _renamed_action(mocker, graph_repo)

    skill = _make_skill_with_pack_versions(
        mocker, old_version="2.3.0", current_version="2.3.1"
    )
    skill.git_status = None  # cross-repo / graph node: no local git status
    skill.in_pack.git_status = None
    mocker.patch.object(
        IsActionNameChangedRequiresSkillRNValidatorListFiles,
        "get_dependent_skills",
        return_value=[skill],
    )

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 0


def test_GR115_cross_repo_skill_without_bump_fails(mocker, graph_repo: Repo):
    """
    Given:
        - A renamed AgentixAction and a cross-repo dependent skill (no git-status)
          whose pack version was NOT bumped vs. master.
    When:
        - Running the GR115 validator on the renamed action.
    Then:
        - A validation error is returned, since no version bump is detected.
    """
    action = _renamed_action(mocker, graph_repo)

    skill = _make_skill_with_pack_versions(
        mocker, old_version="2.3.0", current_version="2.3.0"
    )
    skill.git_status = None
    skill.in_pack.git_status = None
    mocker.patch.object(
        IsActionNameChangedRequiresSkillRNValidatorListFiles,
        "get_dependent_skills",
        return_value=[skill],
    )

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 1
    assert "my-skill-id" in results[0].message


def test_GR115_brand_new_pack_skill_passes(mocker, graph_repo: Repo):
    """
    Given:
        - A renamed AgentixAction and a dependent skill whose pack is brand new
          (no master baseline / ``old_base_content_object is None``).
    When:
        - Running the GR115 validator on the renamed action.
    Then:
        - No validation error is returned (a newly introduced skill needs no RN
          for the action rename).
    """
    action = _renamed_action(mocker, graph_repo)

    skill = _make_skill_with_pack_versions(
        mocker,
        old_version=None,
        current_version="1.0.0",
        has_old_baseline=False,
    )
    mocker.patch.object(
        IsActionNameChangedRequiresSkillRNValidatorListFiles,
        "get_dependent_skills",
        return_value=[skill],
    )

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 0


def test_GR115_unresolvable_pack_passes(mocker, graph_repo: Repo):
    """
    Given:
        - A renamed AgentixAction and a dependent skill whose pack cannot be
          resolved (``pack is None``).
    When:
        - Running the GR115 validator on the renamed action.
    Then:
        - No validation error is returned (missing data must not cause a false
          failure).
    """
    action = _renamed_action(mocker, graph_repo)

    skill = _make_skill_with_pack_versions(
        mocker, old_version=None, current_version=None, pack=None
    )
    mocker.patch.object(
        IsActionNameChangedRequiresSkillRNValidatorListFiles,
        "get_dependent_skills",
        return_value=[skill],
    )

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 0


def test_GR115_action_not_renamed(mocker, graph_repo: Repo):
    """
    Given:
        - A modified AgentixAction whose 'name' field did NOT change (only its id
          would be irrelevant here).
    When:
        - Running the GR115 validator on the action.
    Then:
        - No validation error is returned (no name change means nothing to validate).
    """
    _, action, _ = _build_repo_with_skill_using_action(graph_repo)

    old_action = mocker.Mock()
    old_action.name = action.name  # same name => no rename
    action.git_status = GitStatuses.MODIFIED
    action.old_base_content_object = old_action

    dependents_mock = mocker.patch.object(
        IsActionNameChangedRequiresSkillRNValidatorListFiles,
        "get_dependent_skills",
    )

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 0
    dependents_mock.assert_not_called()


def test_GR115_action_added(mocker, graph_repo: Repo):
    """
    Given:
        - A newly added AgentixAction (no previous version exists).
    When:
        - Running the GR115 validator on the action.
    Then:
        - No validation error is returned (a rename requires a previous version).
    """
    _, action, _ = _build_repo_with_skill_using_action(graph_repo)

    action.git_status = GitStatuses.ADDED
    action.old_base_content_object = None

    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 0


def test_GR115_action_renamed_no_dependent_skills(mocker, graph_repo: Repo):
    """
    Given:
        - A renamed AgentixAction with NO dependent skills.
    When:
        - Running the GR115 validator on the action.
    Then:
        - No validation error is returned.
    """
    pack = graph_repo.create_pack("LonelyActionPack")
    action_ts = pack.create_agentix_action("LonelyAction")
    action_ts.create_default_agentix_action()
    action_id = action_ts.yml.read_dict()["commonfields"]["id"]

    graph_interface = graph_repo.create_graph()
    BaseValidator.graph_interface = graph_interface

    action_objects = graph_interface.search(
        content_type=ContentType.AGENTIX_ACTION, object_id=action_id
    )
    action = action_objects[0]

    old_action = mocker.Mock()
    old_action.name = "Old Action Name"  # name changed, but no skills depend on it
    action.git_status = GitStatuses.MODIFIED
    action.old_base_content_object = old_action

    # The action has no dependent skills, so GR115 must return no results
    # regardless of any Release Note / pack-version-bump check.
    results = IsActionNameChangedRequiresSkillRNValidatorListFiles().obtain_invalid_content_items(
        [action]
    )

    assert len(results) == 0
