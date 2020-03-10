import os
import pytest
import shutil

from demisto_sdk.tests.constants_test import SOURCE_FORMAT_INCIDENTFIELD_COPY, DESTINATION_FORMAT_INCIDENTFIELD_COPY, \
    SOURCE_FORMAT_INCIDENTTYPE_COPY, DESTINATION_FORMAT_INCIDENTTYPE_COPY, SOURCE_FORMAT_INDICATORFIELD_COPY, \
    DESTINATION_FORMAT_INDICATORFIELD_COPY, SOURCE_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_INDICATORTYPE_COPY, \
    SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY, SOURCE_FORMAT_DASHBOARD_COPY, \
    DESTINATION_FORMAT_DASHBOARD_COPY

from demisto_sdk.commands.format.format_module import format_manager


class TestFormattingJson:
    FORMAT_FILES = [
        (SOURCE_FORMAT_INCIDENTFIELD_COPY, DESTINATION_FORMAT_INCIDENTFIELD_COPY, 'incidentfield', 0),
        (SOURCE_FORMAT_INCIDENTTYPE_COPY, DESTINATION_FORMAT_INCIDENTTYPE_COPY, 'incidenttype', 0),
        (SOURCE_FORMAT_INDICATORFIELD_COPY, DESTINATION_FORMAT_INDICATORFIELD_COPY, 'indicatorfield', 0),
        (SOURCE_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_INDICATORTYPE_COPY, 'indicatortype', 0),
        (SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY, 'layout', 0),
        (SOURCE_FORMAT_DASHBOARD_COPY, DESTINATION_FORMAT_DASHBOARD_COPY, 'dashboard', 0),
    ]

    @pytest.mark.parametrize('source, target ,filetype, answer', FORMAT_FILES)
    def test_format_file(self, source, target, filetype, answer):
        shutil.copyfile(source, target)
        res = format_manager(use_git=False, source_file=target, file_type=filetype, output_file_name=target,
                             old_file=False)
        os.remove(target)
        assert res is answer
