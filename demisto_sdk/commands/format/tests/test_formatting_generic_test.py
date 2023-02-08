import pytest

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    GENERAL_DEFAULT_FROMVERSION,
    FileType,
)
from demisto_sdk.commands.format.format_constants import VERSION_6_0_0
from demisto_sdk.commands.format.update_generic import BaseUpdate
from demisto_sdk.commands.validate.validate_manager import ValidateManager


class TestFormattingFromVersionKey:
    def init_BaseUpdate(
        self,
        base_update: BaseUpdate,
        version_to_set="",
        oldfile_version="",
        assume_yes=True,
        current_fromVersion="",
    ):
        base_update.verbose = False
        base_update.data = {}
        base_update.from_version_key = "fromversion"
        if current_fromVersion:
            base_update.data[base_update.from_version_key] = current_fromVersion
        base_update.from_version = version_to_set
        base_update.old_file = {}
        base_update.assume_yes = assume_yes
        if oldfile_version:
            base_update.old_file[base_update.from_version_key] = oldfile_version

    def test_update_fromVersion_from_flag(self, mocker):
        """
        Given
            - A content item without a fromversion key in its current state.
            - The fromversion key to set is specified in the format arguments.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the specific test version.
        """

        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "is_key_in_schema_root", return_value=True)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, VERSION_6_0_0)
        base_update.set_fromVersion()
        assert base_update.data.get(base_update.from_version_key) == VERSION_6_0_0

    def test_update_fromVersion_from_oldFile(self, mocker):
        """
        Given
            - An existing content item that already contains a fromversion key of 6.0.0.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that the fromVersion key in the file remains 6.0.0.
        """

        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "is_key_in_schema_root", return_value=True)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, oldfile_version=VERSION_6_0_0)
        base_update.set_fromVersion()
        assert base_update.data.get(base_update.from_version_key) == VERSION_6_0_0

    def test_update_fromVersion_from_data_with_oldfile(self, mocker):
        """
        Given
            - An existing content item that already contains a fromversion key of 6.1.0.
            - The user manually updated the fromversion key to 6.0.0 in the current version.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion remains 6.0.0.
        """

        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "is_key_in_schema_root", return_value=True)
        base_update = BaseUpdate()
        self.init_BaseUpdate(
            base_update, oldfile_version="6.1.0", current_fromVersion=VERSION_6_0_0
        )
        base_update.set_fromVersion()
        assert base_update.data.get(base_update.from_version_key) == VERSION_6_0_0

    special_content_items = [
        FileType.JOB,
        FileType.LISTS,
        FileType.PRE_PROCESS_RULES,
        FileType.GENERIC_TYPE,
    ]

    @pytest.mark.parametrize(argnames="content_type", argvalues=special_content_items)
    def test_update_fromVersion_from_default_contentItem(self, mocker, content_type):
        """
        Given
            - A new special content item.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the specific default content item version.
        """
        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "is_key_in_schema_root", return_value=True)
        mocker.patch(
            "demisto_sdk.commands.format.update_generic.GENERAL_DEFAULT_FROMVERSION",
            "6.2.0",
        )

        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update)
        base_update.set_fromVersion(FILETYPE_TO_DEFAULT_FROMVERSION.get(content_type))
        assert base_update.data.get(
            base_update.from_version_key
        ) == FILETYPE_TO_DEFAULT_FROMVERSION.get(content_type)

    def test_update_fromVersion_from_default_contentItem_askuser_True(self, mocker):
        """
        Given
            - A new content item.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the GENERAL_DEFAULT_FROMVERSION.
             item version if the user answers Y.
        """
        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "is_key_in_schema_root", return_value=True)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, assume_yes=False)
        mocker.patch.object(BaseUpdate, "get_answer", return_value="Y")
        base_update.set_fromVersion()
        assert (
            base_update.data.get(base_update.from_version_key)
            == GENERAL_DEFAULT_FROMVERSION
        )

    def test_update_fromVersion_from_default_contentItem_askuser_False(self, mocker):
        """
        Given
            - A new content item.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data hasn't been generated.
        """
        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "is_key_in_schema_root", return_value=True)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, assume_yes=False)
        mocker.patch.object(BaseUpdate, "get_answer", return_value="F")
        base_update.set_fromVersion()
        assert base_update.from_version_key not in base_update.data

    def test_update_fromVersion_default_version_lower_then_general(self, mocker):
        """
        Given
            - A new special content item with default fromVersion that is lower than the general.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the general fromVersion.
        """
        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "is_key_in_schema_root", return_value=True)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update)
        base_update.set_fromVersion("5.5.0")
        assert (
            base_update.data.get(base_update.from_version_key)
            == GENERAL_DEFAULT_FROMVERSION
        )

    OLD_FILE = [{}, {}, {}, {}, {}, {"fromServerVersion": "6.0.0"}]
    DATA = [
        {"fromVersion": "6.0.0"},
        {"fromServerVersion": "6.0.0"},
        {"fromVersion": "6.0.0", "fromServerVersion": "6.0.0"},
        {"fromVersion": "6.0.0", "fromServerVersion": "5.0.0"},
        {"fromVersion": "5.5.0", "fromServerVersion": "6.0.0"},
        {},
    ]

    @pytest.mark.parametrize(
        "old_file, data, assume_yes",
        [
            (OLD_FILE[0], DATA[0], False),
            (OLD_FILE[1], DATA[1], False),
            (OLD_FILE[2], DATA[2], False),
            (OLD_FILE[3], DATA[3], True),
            (OLD_FILE[4], DATA[4], False),
            (OLD_FILE[5], DATA[5], False),
        ],
    )
    def test_check_server_version(self, mocker, old_file, data, assume_yes):
        """
        Given
            - An old file, data from current file, and a click.confirm result.
            Case 1: no old file, current file holds fromVersion key only.
            Case 2: no old file, current file holds fromServerVersion key only.
            Case 3: no old file, current file holds both fromServerVersion and fromVersion keys with the same value.
            Case 4: no old file, current file holds both fromServerVersion and fromVersion keys with different value,
                    assume_yes is True.
            Case 5: no old file, current file holds both fromServerVersion and fromVersion keys with different value,
                    assume_yes is False.
            Case 6: old file holds fromServerVersion key, no current file.

        When
            - Calling check_server_version method.
        Then
            - Ensure that the data holds the correct fromVersion value.
        """
        mocker.patch.object(BaseUpdate, "__init__", return_value=None)
        mocker.patch.object(BaseUpdate, "ask_user", return_value=assume_yes)
        base_update = BaseUpdate()
        base_update.old_file = old_file
        base_update.assume_yes = assume_yes
        base_update.data = data
        base_update.json_from_server_version_key = "fromServerVersion"
        base_update.from_version_key = "fromVersion"

        base_update.check_server_version()
        assert base_update.data == {"fromVersion": "6.0.0"}


@pytest.mark.parametrize(
    "is_old_file, function_validate",
    [(False, "run_validation_on_specific_files"), (True, "run_validation_using_git")],
)
def test_initiate_file_validator(mocker, is_old_file, function_validate):
    """
    Given
        - New file
        - Existing file in the repo
    When
        - Running validate on the file
    Then
        - Running validate -i on new files
        - Running validate -g on modified files
    """
    mocker.patch.object(BaseUpdate, "__init__", return_value=None)
    base_update = BaseUpdate()
    base_update.no_validate = False
    base_update.prev_ver = ""
    base_update.output_file = "output_file_path"
    base_update.validate_manager = ValidateManager
    mocker.patch.object(BaseUpdate, "is_old_file", return_value=is_old_file)

    result = mocker.patch.object(ValidateManager, function_validate)

    base_update.initiate_file_validator()
    assert result.call_count == 1
