import pytest

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION, GENERAL_DEFAULT_FROMVERSION, FileType)
from demisto_sdk.commands.format.format_constants import VERSION_6_0_0
from demisto_sdk.commands.format.update_generic import BaseUpdate


class TestFormattingFromVersionKey:

    def init_BaseUpdate(self, base_update: BaseUpdate, version_to_set='', oldfile_version='', assume_yes=True, existing_fromVersion=''):
        base_update.verbose = False
        base_update.data = {}
        base_update.from_version_key = 'fromversion'
        if existing_fromVersion:
            base_update.data[base_update.from_version_key] = existing_fromVersion
        base_update.from_version = version_to_set
        base_update.old_file = {}
        base_update.assume_yes = assume_yes
        if oldfile_version:
            base_update.old_file = {base_update.from_version_key: oldfile_version}

    def test_update_fromVersion_from_flag(self, mocker):
        """
        Given
            - A content item and a version to set.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the specific test version.
        """

        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, VERSION_6_0_0)
        base_update.set_fromVersion()
        assert base_update.data.get(base_update.from_version_key) == VERSION_6_0_0

    def test_update_fromVersion_from_oldFile(self, mocker):
        """
        Given
            - A content item with oldfile version.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the specific test version.
        """

        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, oldfile_version=VERSION_6_0_0)
        base_update.set_fromVersion()
        assert base_update.data.get(base_update.from_version_key) == VERSION_6_0_0

    def test_update_fromVersion_from_data_with_oldfile(self, mocker):
        """
        Given
            - A content item with data & oldfile fromVersion.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data remain.
        """

        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        mocker.patch.object(BaseUpdate, 'is_new_supported_integration', return_value=False)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, oldfile_version=GENERAL_DEFAULT_FROMVERSION, existing_fromVersion=VERSION_6_0_0)
        base_update.set_fromVersion()
        assert base_update.data.get(base_update.from_version_key) == VERSION_6_0_0

    def test_update_fromVersion_from_data_with_worng_fromVersion(self, mocker):
        """
        Given
            - A new special content item with existing fromVersion key and his lower than the default for this type.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key updated to the content type default fromVersion.
        """
        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        mocker.patch.object(BaseUpdate, 'is_new_supported_integration', return_value=False)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, existing_fromVersion='5.5.0')
        base_update.set_fromVersion(FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.JOB))
        assert base_update.data.get(base_update.from_version_key) == FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.JOB)

    special_content_items = [FileType.JOB,
                             FileType.LISTS,
                             FileType.PRE_PROCESS_RULES,
                             FileType.GENERIC_TYPE]

    @pytest.mark.parametrize(argnames='content_type', argvalues=special_content_items)
    def test_update_fromVersion_from_default_contentItem(self, mocker, content_type):
        """
        Given
            - A new special content item.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the specific default content item version.
        """
        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update)
        base_update.set_fromVersion(FILETYPE_TO_DEFAULT_FROMVERSION.get(content_type))
        assert base_update.data.get(base_update.from_version_key) == FILETYPE_TO_DEFAULT_FROMVERSION.get(content_type)

    def test_update_fromVersion_from_default_contentItem_askuser_True(self, mocker):
        """
        Given
            - A new content item.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data was set to the GENERAL_DEFAULT_FROMVERSION
             item version if the user answers Y.
        """
        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, assume_yes=False)
        mocker.patch.object(BaseUpdate, 'get_answer', return_value='Y')
        base_update.set_fromVersion()
        assert base_update.data.get(base_update.from_version_key) == GENERAL_DEFAULT_FROMVERSION

    def test_update_fromVersion_from_default_contentItem_askuser_False(self, mocker):
        """
        Given
            - A new content item.
        When
            - Calling set_fromVersion method.
        Then
            - Ensure that fromVersion key in the file data hasn't been generated.
        """
        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update, assume_yes=False)
        mocker.patch.object(BaseUpdate, 'get_answer', return_value='F')
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
        mocker.patch.object(BaseUpdate, '__init__', return_value=None)
        base_update = BaseUpdate()
        self.init_BaseUpdate(base_update)
        base_update.set_fromVersion('5.5.0')
        assert base_update.data.get(base_update.from_version_key) == GENERAL_DEFAULT_FROMVERSION
