import filecmp
import os
import shutil

import pytest
from demisto_sdk.commands.format.update_description import DescriptionFormat
from demisto_sdk.tests.constants_test import (
    DESCRIPTION_PATH, DESTINATION_FORMAT_DESCRIPTION_COPY,
    SOURCE_DESCRIPTION_FORMATTED_CONTRIB_DETAILS,
    SOURCE_DESCRIPTION_WITH_CONTRIB_DETAILS)


class TestDescriptionFormat:
    @pytest.fixture(autouse=True)
    def description_copy(self):
        os.makedirs(DESCRIPTION_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_DESCRIPTION_WITH_CONTRIB_DETAILS, DESTINATION_FORMAT_DESCRIPTION_COPY)
        if os.path.exists(DESTINATION_FORMAT_DESCRIPTION_COPY):
            os.remove(DESTINATION_FORMAT_DESCRIPTION_COPY)
        shutil.rmtree(DESCRIPTION_PATH, ignore_errors=True)

    @pytest.fixture(autouse=True)
    def description_formatter(self, description_copy):
        description_formatter = DescriptionFormat(
            input=description_copy)
        yield description_formatter

    def test_format(self, description_formatter):
        """
        Given
            - A description file that might contain community/partner details
        When
            - Run format on it
        Then
            - Ensure the details are deleted from the description file
        """
        description_formatter.remove_community_partner_details()
        assert filecmp.cmp(description_formatter.source_file, SOURCE_DESCRIPTION_FORMATTED_CONTRIB_DETAILS) is True
