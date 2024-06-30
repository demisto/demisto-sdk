from demisto_sdk.commands.content_graph.commands.create import create_content_graph
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.GR_validators import (
    GR104_is_pack_display_name_already_exists,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place import (
    MarketplacesFieldValidator,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR100_uses_items_not_in_market_place_all_files import (
    MarketplacesFieldValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_all_files import (
    IsPackDisplayNameAlreadyExistsValidatorAllFiles,
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_list_files import (
    IsPackDisplayNameAlreadyExistsValidatorListFiles,
)
from TestSuite.repo import Repo


def test_IsPackDisplayNameAlreadyExistsValidatorListFiles_is_valid(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorListFiles is_valid function, on one of the duplicate packs.
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

    results = IsPackDisplayNameAlreadyExistsValidatorListFiles().is_valid(
        [graph_repo.packs[0], graph_repo.packs[2]]
    )

    assert len(results) == 1
    assert results[0].message == "Pack 'pack1' has a duplicate display_name as: pack2."


def test_IsPackDisplayNameAlreadyExistsValidatorAllFiles_is_valid(
    mocker, graph_repo: Repo
):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorAllFiles is_valid function.
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

    results = IsPackDisplayNameAlreadyExistsValidatorAllFiles().is_valid(
        [pack for pack in graph_repo.packs]
    )

    assert len(results) == 2


def test_MarketplacesFieldValidator_is_valid(setup, repository):
    """
    Given
    - A content repo.
    When
    - Running MarketplacesFieldValidator is_valid() function.
    Then
    - Validate the existence of invalid marketplaces usages.
    - A single invalid content items shall be found, with expected error message listed in
        `expected_validation_results_messages`.
    """

    graph_interface = ContentGraphInterface()
    create_content_graph(graph_interface)
    BaseValidator.graph_interface = graph_interface

    expected_validation_results_messages = {
        "Content item 'SampleIntegration' can be used in the 'xsoar, marketplacev2' marketplaces, however it uses "
        "content items: 'SampleClassifier2' which are not supported in all of the marketplaces of 'SampleIntegration'.",
    }
    # T
    packs_to_validate = repository.packs[:2]
    validation_results = MarketplacesFieldValidator().is_valid(packs_to_validate)
    assert len(validation_results) == len(expected_validation_results_messages)
    for validation_result in validation_results:
        assert validation_result.message in expected_validation_results_messages


def test_MarketplacesFieldValidatorAllFiles_is_valid(setup, repository):
    """
    Given
    - A content repo.
    When
    - Running MarketplacesFieldValidatorAllFiles is_valid() function.
    Then
    - Validate the validator ignores the provided specific packs and validates all content items in the content graph.
    - Validate the existence of invalid marketplaces usages.
    - Two invalid content items shall be found, with expected error message listed in
        `expected_validation_results_messages`.
    """
    graph_interface = ContentGraphInterface()
    create_content_graph(graph_interface)
    BaseValidator.graph_interface = graph_interface

    expected_validation_results_messages = {
        "Content item 'SamplePlaybook' can be used in the 'xsoar, xpanse' marketplaces, however it uses content items: "
        "'SamplePlaybook2' which are not supported in all of the marketplaces of 'SamplePlaybook'.",
        "Content item 'SampleIntegration' can be used in the 'xsoar, marketplacev2' marketplaces, however it uses "
        "content items: 'SampleClassifier2' which are not supported in all of the marketplaces of 'SampleIntegration'.",
    }
    packs_to_validate = repository.packs[:2]
    validation_results = MarketplacesFieldValidatorAllFiles().is_valid(packs_to_validate)
    assert len(validation_results) == len(expected_validation_results_messages)
    for validation_result in validation_results:
        assert validation_result.message in expected_validation_results_messages
