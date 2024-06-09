
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_all_files import (
    IsPackDisplayNameAlreadyExistsValidatorAllFiles
)
from demisto_sdk.commands.validate.validators.GR_validators.GR104_is_pack_display_name_already_exists_list_files import (
    IsPackDisplayNameAlreadyExistsValidatorListFiles,
)
from TestSuite.repo import Repo


def test_IsPackDisplayNameAlreadyExistsValidatorListFiles_is_valid(graph_repo: Repo):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorListFiles is_valid function.
    Then
        - Validate that we got the error messages for the duplicate name.
    """

    graph_repo.create_pack(name='pack1')

    graph_repo.create_pack(name='pack2')
    graph_repo.packs[1].pack_metadata.update({"name": 'pack1',})

    graph_repo.create_pack(name='pack3')

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsPackDisplayNameAlreadyExistsValidatorListFiles().is_valid(
        [pack for pack in graph_repo.packs]
    )

    assert len(results) == 2


def test_IsPackDisplayNameAlreadyExistsValidatorAllFiles_is_valid(graph_repo: Repo):
    """
    Given
        - 3 packs, and 2 of them are with the same name
    When
        - running IsPackDisplayNameAlreadyExistsValidatorAllFiles is_valid function.
    Then
        - Validate that we got the error messages for the duplicate name.
    """

    graph_repo.create_pack(name='pack1')

    graph_repo.create_pack(name='pack2')
    graph_repo.packs[1].pack_metadata.update({"name": 'pack1', })

    graph_repo.create_pack(name='pack3')

    BaseValidator.graph_interface = graph_repo.create_graph()

    results = IsPackDisplayNameAlreadyExistsValidatorAllFiles().is_valid(
        [pack for pack in graph_repo.packs]
    )

    assert len(results) == 2
