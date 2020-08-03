import os
import shutil

import pytest
from demisto_sdk.commands.format import (update_dashboard, update_incidenttype,
                                         update_indicatortype)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.format.update_classifier import (
    ClassifierJSONFormat, OldClassifierJSONFormat)
from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
from demisto_sdk.commands.format.update_incidenttype import \
    IncidentTypesJSONFormat
from demisto_sdk.commands.format.update_indicatortype import \
    IndicatorTypeJSONFormat
from demisto_sdk.commands.format.update_layout import (
    LayoutJSONFormat, LayoutsContainerJSONFormat)
from demisto_sdk.commands.format.update_mapper import MapperJSONFormat
from demisto_sdk.commands.format.update_report import ReportJSONFormat
from demisto_sdk.commands.format.update_widget import WidgetJSONFormat
from demisto_sdk.tests.constants_test import (
    CLASSIFIER_5_9_9_SCHEMA_PATH, CLASSIFIER_PATH, CLASSIFIER_SCHEMA_PATH,
    DASHBOARD_PATH, DESTINATION_FORMAT_CLASSIFIER,
    DESTINATION_FORMAT_CLASSIFIER_5_9_9, DESTINATION_FORMAT_DASHBOARD_COPY,
    DESTINATION_FORMAT_INCIDENTFIELD_COPY,
    DESTINATION_FORMAT_INCIDENTTYPE_COPY,
    DESTINATION_FORMAT_INDICATORFIELD_COPY,
    DESTINATION_FORMAT_INDICATORTYPE_COPY, DESTINATION_FORMAT_LAYOUT_COPY,
    DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY, DESTINATION_FORMAT_MAPPER,
    DESTINATION_FORMAT_REPORT, DESTINATION_FORMAT_WIDGET, INCIDENTFIELD_PATH,
    INCIDENTTYPE_PATH, INDICATORFIELD_PATH, INDICATORTYPE_PATH,
    INVALID_OUTPUT_PATH, LAYOUT_PATH, LAYOUT_SCHEMA_PATH,
    LAYOUTS_CONTAINER_PATH, LAYOUTS_CONTAINER_SCHEMA_PATH, MAPPER_PATH,
    MAPPER_SCHEMA_PATH, REPORT_PATH, SOURCE_FORMAT_CLASSIFIER,
    SOURCE_FORMAT_CLASSIFIER_5_9_9, SOURCE_FORMAT_DASHBOARD_COPY,
    SOURCE_FORMAT_INCIDENTFIELD_COPY, SOURCE_FORMAT_INCIDENTTYPE_COPY,
    SOURCE_FORMAT_INDICATORFIELD_COPY, SOURCE_FORMAT_INDICATORTYPE_COPY,
    SOURCE_FORMAT_LAYOUT_COPY, SOURCE_FORMAT_LAYOUTS_CONTAINER,
    SOURCE_FORMAT_LAYOUTS_CONTAINER_COPY, SOURCE_FORMAT_MAPPER,
    SOURCE_FORMAT_REPORT, SOURCE_FORMAT_WIDGET, WIDGET_PATH)
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
        (SOURCE_FORMAT_MAPPER, DESTINATION_FORMAT_MAPPER, MAPPER_PATH, 0),
        (SOURCE_FORMAT_CLASSIFIER, DESTINATION_FORMAT_CLASSIFIER, CLASSIFIER_PATH, 0),
        (SOURCE_FORMAT_CLASSIFIER_5_9_9, DESTINATION_FORMAT_CLASSIFIER_5_9_9, CLASSIFIER_PATH, 0),
        (SOURCE_FORMAT_WIDGET, DESTINATION_FORMAT_WIDGET, WIDGET_PATH, 0)
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
    indicator_formater.update_id(field='details')
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
        layoutscontainer_formatter = LayoutsContainerJSONFormat(
            input=layoutscontainer_copy, output=DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY)
        layoutscontainer_formatter.schema_path = LAYOUTS_CONTAINER_SCHEMA_PATH
        yield layoutscontainer_formatter

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

    def test_remove_null_fields(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file with empty kinds fields.
        When
            - Run format on layout file
        Then
            - Ensure that empty kind fields were removed
        """
        layoutscontainer_formatter.remove_null_fields()
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

        layoutscontainer_formatter.remove_null_fields()
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
            - A layout file with fields that dont exit in layout schema.
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
            - A layout file without a description field
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
            - A layout file without a toVersion field
        When
            - Run format on layout file
        Then
            - Ensure that toVersion field was updated successfully with '5.9.9' value
        """
        layouts_formatter.set_toVersion()
        assert layouts_formatter.data.get('toVersion') == '5.9.9'


class TestFormattingClassifier:

    @pytest.fixture(autouse=True)
    def classifier_copy(self):
        os.makedirs(CLASSIFIER_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_CLASSIFIER, DESTINATION_FORMAT_CLASSIFIER)
        os.remove(DESTINATION_FORMAT_CLASSIFIER)
        os.rmdir(CLASSIFIER_PATH)

    @pytest.fixture(autouse=True)
    def classifier_formatter(self, classifier_copy):
        yield ClassifierJSONFormat(input=classifier_copy, output=DESTINATION_FORMAT_CLASSIFIER)

    def test_remove_unnecessary_keys(self, classifier_formatter):
        """
        Given
            - A classifier file with fields that dont exit in classifier schema.
        When
            - Run format on classifier file
        Then
            - Ensure that unnecessary keys were removed
        """
        classifier_formatter.schema_path = CLASSIFIER_SCHEMA_PATH
        classifier_formatter.remove_unnecessary_keys()
        for field in ['brands', 'instanceIds', 'itemVersion', 'locked', 'logicalVersion', 'mapping', 'packID',
                      'system', 'toServerVersion']:
            assert field not in classifier_formatter.data

    def test_set_keyTypeMap(self, classifier_formatter):
        """
        Given
            - A classifier file without a keyTypeMap field
        When
            - Run format on classifier file
        Then
            - Ensure that keyTypeMap field was updated successfully with {} value
        """
        classifier_formatter.set_keyTypeMap()
        assert 'keyTypeMap' in classifier_formatter.data

    def test_set_transformer(self, classifier_formatter):
        """
        Given
            - A classifier file without a transformer field
        When
            - Run format on classifier file
        Then
            - Ensure that keyTypeMap field was updated successfully with {} value
        """
        classifier_formatter.set_transformer()
        assert 'transformer' in classifier_formatter.data

    def test_set_fromVersion(self, classifier_formatter):
        """
        Given
            - A classifier file without a fromVersion field
        When
            - Run format on classifier file
        Then
            - Ensure that fromVersion field was updated successfully with '6.0.0' value
        """
        classifier_formatter.set_fromVersion('6.0.0')
        assert classifier_formatter.data.get('fromVersion') == '6.0.0'


class TestFormattingOldClassifier:

    @pytest.fixture(autouse=True)
    def classifier_5_9_9_copy(self):
        os.makedirs(CLASSIFIER_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_CLASSIFIER_5_9_9, DESTINATION_FORMAT_CLASSIFIER_5_9_9)
        os.remove(DESTINATION_FORMAT_CLASSIFIER_5_9_9)
        os.rmdir(CLASSIFIER_PATH)

    @pytest.fixture(autouse=True)
    def classifier_formatter(self, classifier_5_9_9_copy):
        yield OldClassifierJSONFormat(input=classifier_5_9_9_copy, output=DESTINATION_FORMAT_CLASSIFIER_5_9_9)

    def test_remove_unnecessary_keys(self, classifier_formatter):
        """
        Given
            - A classifier_5_9_9 file with fields that dont exit in classifier schema.
        When
            - Run format on classifier_5_9_9 file
        Then
            - Ensure that unnecessary keys were removed
        """
        classifier_formatter.schema_path = CLASSIFIER_5_9_9_SCHEMA_PATH
        classifier_formatter.remove_unnecessary_keys()
        for field in ['sourceClassifierId', 'locked', 'toServerVersion']:
            assert field not in classifier_formatter.data

    def test_set_toVersion(self, classifier_formatter):
        """
        Given
            - A classifier_5_9_9 file without a toVersion field
        When
            - Run format on classifier_5_9_9 file
        Then
            - Ensure that toVersion field was updated successfully with '5.9.9' value
        """
        classifier_formatter.set_toVersion()
        assert classifier_formatter.data.get('toVersion') == '5.9.9'

    def test_remove_null_fields(self, classifier_formatter):
        """
        Given
            - A classifier_5_9_9 file with values set to null
        When
            - Run format on classifier_5_9_9 file
        Then
            - Ensure that the empty fields were removed successfully
        """
        classifier_formatter.schema_path = CLASSIFIER_5_9_9_SCHEMA_PATH
        classifier_formatter.remove_null_fields()
        for field in ['defaultIncidentType', 'sortValues', 'unclassifiedCases']:
            assert field not in classifier_formatter.data


class TestFormattingMapper:

    @pytest.fixture(autouse=True)
    def mapper_copy(self):
        os.makedirs(MAPPER_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_MAPPER, DESTINATION_FORMAT_MAPPER)
        os.remove(DESTINATION_FORMAT_MAPPER)
        os.rmdir(MAPPER_PATH)

    @pytest.fixture(autouse=True)
    def mapper_formatter(self, mapper_copy):
        yield MapperJSONFormat(input=mapper_copy, output=DESTINATION_FORMAT_MAPPER)

    def test_remove_unnecessary_keys(self, mapper_formatter):
        """
        Given
            - A mapper file with fields that dont exit in mapper schema.
        When
            - Run format on mapper file
        Then
            - Ensure that unnecessary keys were removed
        """
        mapper_formatter.schema_path = MAPPER_SCHEMA_PATH
        mapper_formatter.remove_unnecessary_keys()
        for field in ['locked', 'sourceClassifierId', 'toServerVersion']:
            assert field not in mapper_formatter.data

    def test_set_toVersion(self, mapper_formatter):
        """
        Given
            - A mapper file without a fromVersion field
        When
            - Run format on mapper file
        Then
            - Ensure that fromVersion field was updated successfully with '6.0.0' value
        """
        mapper_formatter.set_fromVersion('6.0.0')
        assert mapper_formatter.data.get('fromVersion') == '6.0.0'


class TestFormattingWidget:

    @pytest.fixture(autouse=True)
    def widget_copy(self):
        os.makedirs(WIDGET_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_WIDGET, DESTINATION_FORMAT_WIDGET)
        os.remove(DESTINATION_FORMAT_WIDGET)
        os.rmdir(WIDGET_PATH)

    @pytest.fixture(autouse=True)
    def widget_formatter(self, widget_copy):
        yield WidgetJSONFormat(input=widget_copy, output=DESTINATION_FORMAT_WIDGET)

    def test_set_description(self, widget_formatter):
        """
        Given
            - A widget file without a description field
        When
            - Run format on widget file
        Then
            - Ensure that a description field was updated successfully with "" value
        """
        widget_formatter.set_description()
        assert 'description' in widget_formatter.data

    def test_set_isPredefined(self, widget_formatter):
        """
        Given
            - A widget file without a isPredefined field
        When
            - Run format on widget file
        Then
            - Ensure that isPredefined field was updated successfully with to True
        """
        widget_formatter.set_isPredefined()
        assert widget_formatter.data.get('isPredefined') is True


class TestFormattingReport:
    @pytest.fixture(autouse=True)
    def report_copy(self):
        os.makedirs(REPORT_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_REPORT, DESTINATION_FORMAT_REPORT)
        os.remove(DESTINATION_FORMAT_REPORT)
        os.rmdir(REPORT_PATH)

    @pytest.fixture(autouse=True)
    def report_formatter(self, report_copy):
        yield ReportJSONFormat(input=report_copy, output=DESTINATION_FORMAT_REPORT)

    def test_set_description(self, report_formatter):
        """
        Given
            - A report file without a description field
        When
            - Run format on report file
        Then
            - Ensure that a description field was updated successfully with "" value
        """
        report_formatter.set_description()
        assert 'description' in report_formatter.data

    def test_set_recipients(self, report_formatter):
        """
        Given
            - A report file without a recipients field
        When
            - Run format on report file
        Then
            - Ensure that a description field was updated successfully with [] value
        """
        report_formatter.set_recipients()
        assert 'recipients' in report_formatter.data

    @patch('builtins.input', lambda *args: 'pdf')
    def test_set_type(self, report_formatter):
        """
        Given
            - A Report file with empty type field
        When
            - Run format on report file
        Then
            - Ensure type field was updated successfully with 'pdf' value
        """
        report_formatter.set_type()
        assert report_formatter.data.get('type') == 'pdf'

    @patch('builtins.input', lambda *args: 'landscape')
    def test_set_orientation(self, report_formatter):
        """
        Given
            - A Report file with empty orientation field
        When
            - Run format on report file
        Then
            - Ensure type field was updated successfully with 'landscape' value
        """
        report_formatter.set_orientation()
        assert report_formatter.data.get('orientation') == 'landscape'
