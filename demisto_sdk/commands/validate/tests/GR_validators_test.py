import logging
from pathlib import Path

import pytest

from demisto_sdk.commands.common.hook_validations.graph_validator import GraphValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.commands.create import (
    create_content_graph,
)
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.content_graph.tests.graph_validator_test import (
    repository as imported_repository,
)
from demisto_sdk.commands.content_graph.tests.graph_validator_test import (
    setup_method as imported_setup_method,
)
from TestSuite.test_tools import str_in_call_args_list
from demisto_sdk.commands.validate.tests.test_tools import create_script_object
from demisto_sdk.commands.validate.validators.GR_validators.GR106_duplicated_script_name import DuplicatedScriptNameValidator

GIT_PATH = Path(git_path())


@pytest.fixture(autouse=True)
def setup_method(mocker):
    imported_setup_method(mocker)


@pytest.fixture
def repository(mocker) -> ContentDTO:
    imported_repository(mocker)


def test_validate_unique_script_name(repository: ContentDTO, mocker):
    """
    Given
        - A content repo
    When
        - running the validation "validate_unique_script_name"
    Then
        - Validate the existence of duplicate script names
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        
    results = DuplicatedScriptNameValidator().is_valid([create_script_object(), create_script_object()])
    
    
    # with GraphValidator(update_graph=False) as graph_validator:
    #     create_content_graph(graph_validator.graph)
    #     is_valid = graph_validator.validate_unique_script_name()

    assert not len(results)

    assert str_in_call_args_list(
        logger_error.call_args_list,
        "Cannot create a script with the name setAlert, "
        "because a script with the name setIncident already exists.\n",
    )

    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "Cannot create a script with the name getAlert, "
        "because a script with the name getIncident already exists.\n",
    )

    # Ensure that the script-name-incident-to-alert ignore is working
    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "Cannot create a script with the name getAlerts, "
        "because a script with the name getIncidents already exists.\n",
    )
