import os
import pytest
import shutil

from demisto_sdk.tests.constants_test import SOURCE_FORMAT_INCIDENTFIELD_COPY, DESTINATION_FORMAT_INCIDENTFIELD_COPY, \
    SOURCE_FORMAT_INCIDENTTYPE_COPY, DESTINATION_FORMAT_INCIDENTTYPE_COPY, SOURCE_FORMAT_INDICATORFIELD_COPY, \
    DESTINATION_FORMAT_INDICATORFIELD_COPY, SOURCE_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_INDICATORTYPE_COPY,\
    SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY, SOURCE_FORMAT_DASHBOARD_COPY,\
    DESTINATION_FORMAT_DASHBOARD_COPY


from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.common.configuration import Configuration


class TestFormattingJson:
    def setup(self):
        conf = Configuration()
        self.test_output_dir_path = os.path.join(conf.sdk_env_dir, 'tests', 'test_files', 'Formatting', 'Results')
        os.makedirs(self.test_output_dir_path)

    def teardown(self):
        if self.test_output_dir_path:
            shutil.rmtree(self.test_output_dir_path)

    FORMAT_FILES = [
        (SOURCE_FORMAT_INCIDENTFIELD_COPY, DESTINATION_FORMAT_INCIDENTFIELD_COPY, 1),
        (SOURCE_FORMAT_INCIDENTTYPE_COPY, DESTINATION_FORMAT_INCIDENTTYPE_COPY, 1),
        (SOURCE_FORMAT_INDICATORFIELD_COPY, DESTINATION_FORMAT_INDICATORFIELD_COPY, 1),
        (SOURCE_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_INDICATORTYPE_COPY, 1),
        (SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_INCIDENTTYPE_COPY, 1),
        (SOURCE_FORMAT_INCIDENTTYPE_COPY, DESTINATION_FORMAT_LAYOUT_COPY, 1),
        (SOURCE_FORMAT_DASHBOARD_COPY, DESTINATION_FORMAT_DASHBOARD_COPY, 1),
    ]

    @pytest.mark.parametrize('source, target ,answer', FORMAT_FILES)
    def test_format_file(self, source, target, answer):
        shutil.copyfile(source, target)
        res = format_manager(False, source_file=source, output_file_name=self.test_output_dir_path, old_file=False)
        assert res is answer
