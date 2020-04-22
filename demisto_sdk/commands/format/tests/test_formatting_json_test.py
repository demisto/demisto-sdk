import os
import shutil

import pytest
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.tests.constants_test import (
    DASHBOARD_PATH, DESTINATION_FORMAT_DASHBOARD_COPY,
    DESTINATION_FORMAT_INCIDENTFIELD_COPY,
    DESTINATION_FORMAT_INCIDENTTYPE_COPY,
    DESTINATION_FORMAT_INDICATORFIELD_COPY,
    DESTINATION_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_LAYOUT_COPY,
    INCIDENTFIELD_PATH, INCIDENTTYPE_PATH, INDICATORFIELD_PATH,
    INDICATORTYPE_PATH, INVALID_OUTPUT_PATH, LAYOUT_PATH,
    SOURCE_FORMAT_DASHBOARD_COPY, SOURCE_FORMAT_INCIDENTFIELD_COPY,
    SOURCE_FORMAT_INCIDENTTYPE_COPY, SOURCE_FORMAT_INDICATORFIELD_COPY,
    SOURCE_FORMAT_INDICATORTYPE_COPY, SOURCE_FORMAT_LAYOUT_COPY)


class TestFormattingJson:
    FORMAT_FILES = [
        (SOURCE_FORMAT_INCIDENTFIELD_COPY, DESTINATION_FORMAT_INCIDENTFIELD_COPY, INCIDENTFIELD_PATH, 0),
        (SOURCE_FORMAT_INCIDENTTYPE_COPY, DESTINATION_FORMAT_INCIDENTTYPE_COPY, INCIDENTTYPE_PATH, 0),
        (SOURCE_FORMAT_INDICATORFIELD_COPY, DESTINATION_FORMAT_INDICATORFIELD_COPY, INDICATORFIELD_PATH, 0),
        (SOURCE_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_INDICATORTYPE_COPY, INDICATORTYPE_PATH, 0),
        (SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY, LAYOUT_PATH, 0),
        (SOURCE_FORMAT_DASHBOARD_COPY, DESTINATION_FORMAT_DASHBOARD_COPY, DASHBOARD_PATH, 0),
    ]

    @pytest.mark.parametrize('source, target, path, answer', FORMAT_FILES)
    def test_format_file(self, source, target, path, answer):
        os.makedirs(path)
        shutil.copyfile(source, target)
        res = format_manager(input=target, output=target)
        os.remove(target)
        os.rmdir(path)

        assert res is answer

    @pytest.mark.parametrize('invalid_output', [INVALID_OUTPUT_PATH])
    def test_output_file(self, invalid_output):
        try:
            res_invalid = format_manager(input=invalid_output, output=invalid_output)
            assert res_invalid
        except Exception as e:
            assert str(e) == "The given output path is not a specific file path.\nOnly file path can be a output path." \
                             "  Please specify a correct output."
