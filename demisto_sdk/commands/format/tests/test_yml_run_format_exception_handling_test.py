import logging
import pytest
from unittest.mock import Mock, patch

from demisto_sdk.commands.common.constants import (
    ALERT_FETCH_REQUIRED_PARAMS,
    FEED_REQUIRED_PARAMS,
    GENERAL_DEFAULT_FROMVERSION,
    INCIDENT_FETCH_REQUIRED_PARAMS,
    NO_TESTS_DEPRECATED,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import is_string_uuid
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.format.update_generic import BaseUpdate
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.format.update_integration import IntegrationYMLFormat
from demisto_sdk.commands.format.update_playbook import (
    PlaybookYMLFormat,
    TestPlaybookYMLFormat,
)
from demisto_sdk.commands.format.update_script import ScriptYMLFormat
from demisto_sdk.tests.constants_test import (
    DESTINATION_FORMAT_INTEGRATION,
    DESTINATION_FORMAT_INTEGRATION_COPY,
    DESTINATION_FORMAT_PLAYBOOK,
    DESTINATION_FORMAT_PLAYBOOK_COPY,
    DESTINATION_FORMAT_SCRIPT_COPY,
    DESTINATION_FORMAT_TEST_PLAYBOOK,
    FEED_INTEGRATION_EMPTY_VALID,
    FEED_INTEGRATION_INVALID,
    FEED_INTEGRATION_VALID,
    GIT_ROOT,
    INTEGRATION_PATH,
    INTEGRATION_SCHEMA_PATH,
    PLAYBOOK_PATH,
    PLAYBOOK_SCHEMA_PATH,
    PLAYBOOK_WITH_INCIDENT_INDICATOR_SCRIPTS,
    SCRIPT_SCHEMA_PATH,
    SOURCE_BETA_INTEGRATION_FILE,
    SOURCE_FORMAT_INTEGRATION_COPY,
    SOURCE_FORMAT_INTEGRATION_DEFAULT_VALUE,
    SOURCE_FORMAT_INTEGRATION_INVALID,
    SOURCE_FORMAT_INTEGRATION_VALID,
    SOURCE_FORMAT_PLAYBOOK,
    SOURCE_FORMAT_PLAYBOOK_COPY,
    SOURCE_FORMAT_SCRIPT_COPY,
    SOURCE_FORMAT_TEST_PLAYBOOK,
    TEST_PLAYBOOK_PATH,
)

logging.getLogger("demisto-sdk").propagate = True

FORMAT_OBJECT = [
    PlaybookYMLFormat,
    IntegrationYMLFormat,
    TestPlaybookYMLFormat,
    ScriptYMLFormat,
]


@pytest.fixture
def caplog(caplog: pytest.LogCaptureFixture):
    logger = logging.getLogger("demisto-sdk")
    caplog_formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    caplog.handler.formatter = caplog_formatter
    logger.handlers.append(caplog.handler)
    yield caplog
    logger.handlers.remove(caplog.handler)


@pytest.mark.parametrize(
    argnames="format_object",
    argvalues=FORMAT_OBJECT,
)
def test_yml_run_format_exception_handling(format_object, mocker, caplog):
    """
    Given
        - A YML object formatter
    When
        - Run run_format command and exception is raised.
    Then
        - Ensure the error is printed.
    """
    formatter = format_object(input="my_file_path")
    mocker.patch.object(
        BaseUpdateYML, "update_yml", side_effect=TestFormatting.exception_raise
    )
    mocker.patch.object(
        PlaybookYMLFormat, "update_tests", side_effect=TestFormatting.exception_raise
    )

    # logger = logging.getLogger("demisto-sdk")
    # for current_handler in logger.handlers:
    #     if current_handler.name == "console-handler":
    #         current_handler.level = logging.DEBUG
    # logger.propagate = True

    # self._caplog.set_level(logging.DEBUG)
    # import pdb; pdb.set_trace()
    with caplog.at_level(logging.DEBUG):
        formatter.run_format()
        # print(f"*** {self._caplog.text=}")
        print(f"*** {caplog.text=}")
        # assert "Failed to update file my_file_path. Error: MY ERROR" in caplog.text
        # assert "Failed to update file my_file_path. Error: MY ERROR" in self._caplog.text
        assert "Failed to update file my_file_path. Error: MY ERROR" in caplog.text
