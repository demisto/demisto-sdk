import os
import shutil

import pytest
from demisto_sdk.commands.format import (update_dashboard, update_incidenttype,
                                         update_indicatortype)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
from demisto_sdk.commands.format.update_incidenttype import \
    IncidentTypesJSONFormat
from demisto_sdk.commands.format.update_indicatortype import \
    IndicatorTypeJSONFormat
from demisto_sdk.commands.format.update_layout import (
    LayoutJSONFormat, LayoutsContainerJSONFormat)
from demisto_sdk.tests.constants_test import (
    DASHBOARD_PATH, DESTINATION_FORMAT_DASHBOARD_COPY,
    DESTINATION_FORMAT_INCIDENTFIELD_COPY,
    DESTINATION_FORMAT_INCIDENTTYPE_COPY,
    DESTINATION_FORMAT_INDICATORFIELD_COPY,
    DESTINATION_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_LAYOUT_COPY,
    DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY, INCIDENTFIELD_PATH,
    INCIDENTTYPE_PATH, INDICATORFIELD_PATH, INDICATORTYPE_PATH,
    INVALID_OUTPUT_PATH, LAYOUT_PATH, LAYOUT_SCHEMA_PATH,
    LAYOUTS_CONTAINER_PATH, LAYOUTS_CONTAINER_SCHEMA_PATH,
    SOURCE_FORMAT_DASHBOARD_COPY, SOURCE_FORMAT_INCIDENTFIELD_COPY,
    SOURCE_FORMAT_INCIDENTTYPE_COPY, SOURCE_FORMAT_INDICATORFIELD_COPY,
    SOURCE_FORMAT_INDICATORTYPE_COPY, SOURCE_FORMAT_LAYOUT_COPY,
    SOURCE_FORMAT_LAYOUTS_CONTAINER, SOURCE_FORMAT_LAYOUTS_CONTAINER_COPY)
from mock import patch


class TestFormattingJson:
    FORMAT_FILES = [
        (SOURCE_FORMAT_INCIDENTFIELD_COPY, DESTINATION_FORMAT_INCIDENTFIELD_COPY, INCIDENTFIELD_PATH, 0),
        (SOURCE_FORMAT_INCIDENTTYPE_COPY, DESTINATION_FORMAT_INCIDENTTYPE_COPY, INCIDENTTYPE_PATH, 0),
        (SOURCE_FORMAT_INDICATORFIELD_COPY, DESTINATION_FORMAT_INDICATORFIELD_COPY, INDICATORFIELD_PATH, 0),
        (SOURCE_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_INDICATORTYPE_COPY, INDICATORTYPE_PATH, 0),
        (SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY, LAYOUT_PATH, 0),
        (SOURCE_FORMAT_LAYOUTS_CONTAINER_COPY, DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY, LAYOUTS_CONTAINER_PATH, 0),
        (SOURCE_FORMAT_DASHBOARD_COPY, DESTINATION_FORMAT_DASHBOARD_COPY, DASHBOARD_PATH, 0),
    ]

    @pytest.mark.parametrize('source, target, path, answer', FORMAT_FILES)
    def test_format_file(self, source, target, path, answer):
        os.makedirs(path, exist_ok=True)
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


def test_update_id_indicatortype_positive(mocker, tmpdir):
    """
    Given
        - A dictionary of indicatortype file that the id is not equal to the details
    When
        - Run format on indicatortype file
    Then
        - Ensure id updated successfully
    """
    mocker.patch.object(update_indicatortype, 'IndicatorTypeJSONFormat')

    indicator_formater = IndicatorTypeJSONFormat(input='test', output=tmpdir)
    indicator_formater.data = {'id': '1234', 'details': '12345'}
    indicator_formater.update_id()
    assert indicator_formater.data['id'] == indicator_formater.data['details']


def test_update_id_indicatortype_negative(mocker, tmpdir):
    """
    Given
        - A dictionary of indicator-type file that the details field is missing
    When
        - Run format on indicator-type file
    Then
        - Ensure the return Exception is 'Missing "details" field in file test - add this field manually'
    """
    mocker.patch.object(update_indicatortype, 'IndicatorTypeJSONFormat')
    indicator_formater = IndicatorTypeJSONFormat(input='test', output=tmpdir)
    indicator_formater.data = {'id': '1234'}
    try:
        indicator_formater.update_id()
    except Exception as error:
        assert error.args[0] == 'Missing "details" field in file test - add this field manually'


def test_update_id_incidenttype_positive(mocker, tmpdir):
    """
    Given
        - A dictionary of incident-type file that the id is not equal to the name
    When
        - Run format on incident-type file
    Then
        - Ensure id updated successfully
    """
    mocker.patch.object(update_incidenttype, 'IncidentTypesJSONFormat')

    incident_formater = IncidentTypesJSONFormat(input='test', output=tmpdir)
    incident_formater.data = {'id': '1234', 'name': '12345'}
    incident_formater.update_id()
    assert incident_formater.data['id'] == incident_formater.data['name']


def test_update_id_incidenttype_negative(mocker, tmpdir):
    """
    Given
        - A dictionary of incident-type file that the name field is missing
    When
        - Run format on incident-type file
    Then
        - Ensure the return Exception is 'Missing "name" field in file test - add this field manually'
    """
    mocker.patch.object(update_incidenttype, 'IncidentTypesJSONFormat')
    incident_formater = IncidentTypesJSONFormat(input='test', output=tmpdir)
    incident_formater.data = {'id': '1234'}
    try:
        incident_formater.update_id()
    except Exception as error:
        assert error.args[0] == 'Missing "name" field in file test - add this field manually'


def test_update_id_dashboard_positive(mocker, tmpdir):
    """
    Given
        - A dictionary of dashboard file that the id is not equal to the name
    When
        - Run format on dashboard file
    Then
        - Ensure id updated successfully
    """
    mocker.patch.object(update_dashboard, 'DashboardJSONFormat')

    dashboard_formater = DashboardJSONFormat(input='test', output=tmpdir)
    dashboard_formater.data = {'id': '1234', 'name': '12345'}
    dashboard_formater.update_id()
    assert dashboard_formater.data['id'] == dashboard_formater.data['name']


def test_update_id_dashboard_negative(mocker, tmpdir):
    """
    Given
        - A dictionary of dashboard file that the name field is missing
    When
        - Run format on dashboard file
    Then
        - Ensure the return Exception is 'Missing "name" field in file test - add this field manually'
    """
    mocker.patch.object(update_dashboard, 'DashboardJSONFormat')
    dashboard_formater = DashboardJSONFormat(input='test', output=tmpdir)
    dashboard_formater.data = {'id': '1234'}
    try:
        dashboard_formater.update_id()
    except Exception as error:
        assert error.args[0] == 'Missing "name" field in file test - add this field manually'


class TestFormattingLayoutscontainer:

    @pytest.fixture(autouse=True)
    def layoutscontainer_copy(self):
        os.makedirs(LAYOUTS_CONTAINER_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_LAYOUTS_CONTAINER, DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY)
        os.remove(DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY)
        os.rmdir(LAYOUTS_CONTAINER_PATH)

    @pytest.fixture(autouse=True)
    def layoutscontainer_formatter(self, layoutscontainer_copy):
        yield LayoutsContainerJSONFormat(
            input=layoutscontainer_copy, output=DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY)

    @patch('builtins.input', lambda *args: 'incident')
    def test_set_group_field(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file with empty group field
        When
            - Run format on layout file
        Then
            - Ensure group field was updated successfully with 'incident' value
        """
        layoutscontainer_formatter.set_group_field()
        assert layoutscontainer_formatter.data.get('group') == 'incident'

    def test_remove_null_kinds(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file with empty kinds fields.
        When
            - Run format on layout file
        Then
            - Ensure that empty kind fields were removed
        """
        layoutscontainer_formatter.remove_null_kinds()
        for kind in ['close', 'details', 'detailsV2', 'edit', 'indicatorsQuickView', 'mobile']:
            assert kind not in layoutscontainer_formatter.data

    def test_remove_unnecessary_keys(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file with fields that dont exit in layoutscontainer schema.
        When
            - Run format on layout file
        Then
            - Ensure that unnecessary keys were removed
        """

        layoutscontainer_formatter.schema_path = LAYOUTS_CONTAINER_SCHEMA_PATH
        layoutscontainer_formatter.remove_null_kinds()
        layoutscontainer_formatter.remove_unnecessary_keys()
        for field in ['fromServerVersion', 'quickView', 'sortValues']:
            assert field not in layoutscontainer_formatter.data

    def test_set_description(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file without a description field
        When
            - Run format on layout file
        Then
            - Ensure that description field was updated successfully with '' value
        """
        layoutscontainer_formatter.set_description()
        assert 'description' in layoutscontainer_formatter.data

    def test_set_fromVersion(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file without a fromVersion field
        When
            - Run format on layout file
        Then
            - Ensure that fromVersion field was updated successfully with '6.0.0' value
        """
        layoutscontainer_formatter.set_fromVersion('6.0.0')
        assert layoutscontainer_formatter.data.get('fromVersion') == '6.0.0'


class TestFormattingLayout:

    @pytest.fixture(autouse=True)
    def layouts_copy(self):
        os.makedirs(LAYOUT_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY)
        os.remove(DESTINATION_FORMAT_LAYOUT_COPY)
        os.rmdir(LAYOUT_PATH)

    @pytest.fixture(autouse=True)
    def layouts_formatter(self, layouts_copy):
        yield LayoutJSONFormat(input=layouts_copy, output=DESTINATION_FORMAT_LAYOUT_COPY)

    def test_remove_unnecessary_keys(self, layouts_formatter):
        """
        Given
            - A layoutscontainer file with fields that dont exit in layoutscontainer schema.
        When
            - Run format on layout file
        Then
            - Ensure that unnecessary keys were removed
        """
        layouts_formatter.schema_path = LAYOUT_SCHEMA_PATH
        layouts_formatter.remove_unnecessary_keys()
        for field in ['fromServerVersion', 'quickView', 'sortValues', 'locked']:
            assert field not in layouts_formatter.data

    def test_set_description(self, layouts_formatter):
        """
        Given
            - A layoutscontainer file without a description field
        When
            - Run format on layout file
        Then
            - Ensure that description field was updated successfully with '' value
        """
        layouts_formatter.set_description()
        assert 'description' in layouts_formatter.data

    def test_set_toVersion(self, layouts_formatter):
        """
        Given
            - A layoutscontainer file without a fromVersion field
        When
            - Run format on layout file
        Then
            - Ensure that fromVersion field was updated successfully with '6.0.0' value
        """
        layouts_formatter.set_toVersion()
        assert layouts_formatter.data.get('toVersion') == '5.9.9'
