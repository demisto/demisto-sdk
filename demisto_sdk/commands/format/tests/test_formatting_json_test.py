import os
import shutil
from typing import Optional
from unittest.mock import patch

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.format import (
    update_dashboard,
    update_incidenttype,
    update_indicatortype,
)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.format.update_classifier import (
    ClassifierJSONFormat,
    OldClassifierJSONFormat,
)
from demisto_sdk.commands.format.update_connection import ConnectionJSONFormat
from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
from demisto_sdk.commands.format.update_generic import BaseUpdate
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.format.update_genericfield import GenericFieldJSONFormat
from demisto_sdk.commands.format.update_incidentfields import IncidentFieldJSONFormat
from demisto_sdk.commands.format.update_incidenttype import IncidentTypesJSONFormat
from demisto_sdk.commands.format.update_indicatorfields import IndicatorFieldJSONFormat
from demisto_sdk.commands.format.update_indicatortype import IndicatorTypeJSONFormat
from demisto_sdk.commands.format.update_layout import LayoutBaseFormat
from demisto_sdk.commands.format.update_lists import ListsFormat
from demisto_sdk.commands.format.update_mapper import MapperJSONFormat
from demisto_sdk.commands.format.update_pack_metadata import PackMetadataJsonFormat
from demisto_sdk.commands.format.update_pre_process_rules import PreProcessRulesFormat
from demisto_sdk.commands.format.update_report import ReportJSONFormat
from demisto_sdk.commands.format.update_widget import WidgetJSONFormat
from demisto_sdk.tests.constants_test import (
    CLASSIFIER_5_9_9_SCHEMA_PATH,
    CLASSIFIER_PATH,
    CLASSIFIER_SCHEMA_PATH,
    CONNECTION_SCHEMA_PATH,
    DASHBOARD_PATH,
    DESTINATION_FORMAT_CLASSIFIER,
    DESTINATION_FORMAT_CLASSIFIER_5_9_9,
    DESTINATION_FORMAT_DASHBOARD_COPY,
    DESTINATION_FORMAT_INCIDENTFIELD_COPY,
    DESTINATION_FORMAT_INCIDENTTYPE_COPY,
    DESTINATION_FORMAT_INDICATORFIELD_COPY,
    DESTINATION_FORMAT_INDICATORTYPE_COPY,
    DESTINATION_FORMAT_LAYOUT_COPY,
    DESTINATION_FORMAT_LAYOUT_INVALID_NAME_COPY,
    DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY,
    DESTINATION_FORMAT_LISTS_COPY,
    DESTINATION_FORMAT_MAPPER,
    DESTINATION_FORMAT_PRE_PROCESS_RULES_COPY,
    DESTINATION_FORMAT_PRE_PROCESS_RULES_INVALID_NAME_COPY,
    DESTINATION_FORMAT_REPORT,
    DESTINATION_FORMAT_WIDGET,
    GENERICFIELD_SCHEMA_PATH,
    INCIDENTFIELD_PATH,
    INCIDENTFIELD_SCHEMA_PATH,
    INCIDENTTYPE_PATH,
    INCIDENTTYPE_SCHEMA_PATH,
    INDICATORFIELD_PATH,
    INDICATORFIELD_SCHEMA_PATH,
    INDICATORTYPE_PATH,
    INDICATORTYPE_SCHEMA_PATH,
    INVALID_OUTPUT_PATH,
    LAYOUT_PATH,
    LAYOUT_SCHEMA_PATH,
    LAYOUTS_CONTAINER_PATH,
    LAYOUTS_CONTAINER_SCHEMA_PATH,
    LISTS_PATH,
    LISTS_SCHEMA_PATH,
    MAPPER_PATH,
    MAPPER_SCHEMA_PATH,
    PRE_PROCESS_RULES_PATH,
    PRE_PROCESS_RULES_SCHEMA_PATH,
    REPORT_PATH,
    REPORT_SCHEMA_PATH,
    SOURCE_FORMAT_CLASSIFIER,
    SOURCE_FORMAT_CLASSIFIER_5_9_9,
    SOURCE_FORMAT_DASHBOARD_COPY,
    SOURCE_FORMAT_INCIDENTFIELD_COPY,
    SOURCE_FORMAT_INCIDENTTYPE_COPY,
    SOURCE_FORMAT_INDICATORFIELD_COPY,
    SOURCE_FORMAT_INDICATORTYPE_COPY,
    SOURCE_FORMAT_LAYOUT_COPY,
    SOURCE_FORMAT_LAYOUTS_CONTAINER,
    SOURCE_FORMAT_LAYOUTS_CONTAINER_COPY,
    SOURCE_FORMAT_LISTS_COPY,
    SOURCE_FORMAT_MAPPER,
    SOURCE_FORMAT_PRE_PROCESS_RULES_COPY,
    SOURCE_FORMAT_REPORT,
    SOURCE_FORMAT_WIDGET,
    WIDGET_PATH,
    WIDGET_SCHEMA_PATH,
)
from TestSuite.json_based import JSONBased

json = JSON_Handler()


@pytest.fixture()
def id_set_file_mock(tmp_path):
    """
    Mock the id set file with incident/indicator fields.
    """
    id_set_file = JSONBased(dir_path=tmp_path, name="id_set_file", prefix="")
    id_set_file.write_json(
        {
            "IncidentFields": [
                {"incident_incident-field-1": {"name": "Incident-Field-1"}},
                {"incident_incident-field-2": {"name": "Incident-Field-2"}},
            ],
            "IndicatorFields": [
                {"indicator_indicator-field-1": {"name": "Indicator Field"}},
                {"indicator_indicator-field-2": {"name": "Indicator Field"}},
            ],
        }
    )
    return id_set_file


class TestFormattingJson:
    FORMAT_FILES = [
        (
            SOURCE_FORMAT_INDICATORTYPE_COPY,
            DESTINATION_FORMAT_INDICATORTYPE_COPY,
            INDICATORTYPE_PATH,
            0,
        ),
        (SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY, LAYOUT_PATH, 0),
        (
            SOURCE_FORMAT_LAYOUTS_CONTAINER_COPY,
            DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY,
            LAYOUTS_CONTAINER_PATH,
            0,
        ),
        (SOURCE_FORMAT_MAPPER, DESTINATION_FORMAT_MAPPER, MAPPER_PATH, 0),
        (SOURCE_FORMAT_CLASSIFIER, DESTINATION_FORMAT_CLASSIFIER, CLASSIFIER_PATH, 0),
        (SOURCE_FORMAT_WIDGET, DESTINATION_FORMAT_WIDGET, WIDGET_PATH, 0),
    ]
    FORMAT_FILES_OLD_FROMVERSION = [
        (
            SOURCE_FORMAT_INCIDENTFIELD_COPY,
            DESTINATION_FORMAT_INCIDENTFIELD_COPY,
            INCIDENTFIELD_PATH,
            0,
        ),
        (
            SOURCE_FORMAT_INCIDENTTYPE_COPY,
            DESTINATION_FORMAT_INCIDENTTYPE_COPY,
            INCIDENTTYPE_PATH,
            0,
        ),
        (
            SOURCE_FORMAT_INDICATORFIELD_COPY,
            DESTINATION_FORMAT_INDICATORFIELD_COPY,
            INDICATORFIELD_PATH,
            0,
        ),
        (
            SOURCE_FORMAT_CLASSIFIER_5_9_9,
            DESTINATION_FORMAT_CLASSIFIER_5_9_9,
            CLASSIFIER_PATH,
            0,
        ),
        (
            SOURCE_FORMAT_DASHBOARD_COPY,
            DESTINATION_FORMAT_DASHBOARD_COPY,
            DASHBOARD_PATH,
            0,
        ),
    ]

    @pytest.mark.parametrize("source, target, path, answer", FORMAT_FILES)
    def test_format_file(self, source, target, path, answer):
        os.makedirs(path, exist_ok=True)
        shutil.copyfile(source, target)
        res = format_manager(input=target, output=target, verbose=True)
        shutil.rmtree(target, ignore_errors=True)
        shutil.rmtree(path, ignore_errors=True)

        assert res is answer

    @pytest.mark.parametrize(
        "source, target, path, answer", FORMAT_FILES_OLD_FROMVERSION
    )
    def test_format_file_old_fromversion(
        self, source, target, path, answer, monkeypatch
    ):
        """
        Given
            - Incident field json file, Incident type json file, Indicator type json and classifier
        When
            - Run format_manager on files
        Then
            - Ensure that format finished without errors
        """
        os.makedirs(path, exist_ok=True)
        shutil.copyfile(source, target)

        monkeypatch.setattr("builtins.input", lambda _: "N")

        res = format_manager(input=target, output=target, verbose=True)
        shutil.rmtree(target, ignore_errors=True)
        shutil.rmtree(path, ignore_errors=True)

        assert res is answer

    @pytest.mark.parametrize("invalid_output", [INVALID_OUTPUT_PATH])
    def test_output_file(self, invalid_output):
        try:
            res_invalid = format_manager(
                input=invalid_output, output=invalid_output, verbose=True
            )
            assert res_invalid
        except Exception as e:
            assert (
                str(e)
                == "The given output path is not a specific file path.\nOnly file path can be a output path."
                "  Please specify a correct output."
            )

    @pytest.mark.parametrize(
        "formatter",
        [
            GenericFieldJSONFormat,
            IncidentFieldJSONFormat,
            IndicatorFieldJSONFormat,
        ],
    )
    def test_update_unsearchable_key(self, formatter):
        """
        Given
            - A dictionary of file that the unsearchable is false
        When
            - Run format on file
        Then
            - Ensure unsearchable updated successfully
        """

        fields_formatter = formatter(input="test")
        fields_formatter.data = {"unsearchable": False}
        fields_formatter.set_default_values_as_needed()
        assert fields_formatter.data["unsearchable"]

    @pytest.mark.parametrize("from_version", [None, "5.5.0", "6.2.0"])
    def test_indicator_field_format_html_type(self, pack, from_version: Optional[str]):
        """
        Given
        - Indicator field of type HTML.
        When
        - Running format.
        Then
        - Ensure the indicator field from version is set to 6.1.0.
        """
        indicator_field = pack.create_indicator_field(
            "IndicatorTestField", {"type": "html"}
        )
        if from_version:
            indicator_field.update({"fromVersion": from_version})
        fields_formatter = IndicatorFieldJSONFormat(input=indicator_field.path)
        fields_formatter.update_from_version()
        assert fields_formatter.data["fromVersion"] == "6.1.0"


class TestFormattingIncidentTypes:
    EXTRACTION_MODE_VARIATIONS = [
        ("All", "", "All"),
        ("Specific", "", "Specific"),
        ("", "Specific", "Specific"),
        ("specific", "Specific", "Specific"),
    ]

    @pytest.mark.parametrize(
        "existing_extract_mode, user_answer, expected", EXTRACTION_MODE_VARIATIONS
    )
    def test_format_autoextract_mode(
        self, mocker, existing_extract_mode, user_answer, expected
    ):
        """
        Given
        - An incident type without auto extract mode or with a valid/invalid auto extract mode.

        When
        - Running format_auto_extract_mode on it.

        Then
        - If the auto extract mode is valid, then no format is needed.
        - If the auto extract mode is invalid or doesn't exist, the user will choose between the two options.
        """
        mock_dict = {
            "extractSettings": {
                "mode": existing_extract_mode,
                "fieldCliNameToExtractSettings": {
                    "incident_field": {
                        "extractAsIsIndicatorTypeId": "",
                        "isExtractingAllIndicatorTypes": False,
                        "extractIndicatorTypesIDs": [],
                    }
                },
            }
        }
        mocker.patch(
            "demisto_sdk.commands.format.update_generic.get_dict_from_file",
            return_value=(mock_dict, "mock_type"),
        )
        mocker.patch(
            "demisto_sdk.commands.format.update_incidenttype.click.prompt",
            return_value=user_answer,
        )
        formatter = IncidentTypesJSONFormat("test")
        formatter.format_auto_extract_mode()
        current_mode = formatter.data.get("extractSettings", {}).get("mode")
        assert current_mode == expected

    def test_format_autoextract_mode_bad_user_input(self, mocker):
        """
        Given
        - An incident type without auto extract mode.

        When
        - Running format_auto_extract_mode on it.

        Then
        - If user's input is invalid, prompt will keep on asking for a valid input.
        """
        mock_dict = {
            "extractSettings": {
                "fieldCliNameToExtractSettings": {
                    "incident_field": {
                        "extractAsIsIndicatorTypeId": "",
                        "isExtractingAllIndicatorTypes": False,
                        "extractIndicatorTypesIDs": [],
                    }
                }
            }
        }
        mocker.patch(
            "demisto_sdk.commands.format.update_generic.get_dict_from_file",
            return_value=(mock_dict, "mock_type"),
        )
        mock_func = mocker.patch(
            "demisto_sdk.commands.format.update_incidenttype.click.prompt"
        )
        mock_func.side_effect = ["all", "a", "g", "Specific"]

        formatter = IncidentTypesJSONFormat("test")
        formatter.format_auto_extract_mode()
        current_mode = formatter.data.get("extractSettings", {}).get("mode")
        assert mock_func.call_count == 4
        assert current_mode == "Specific"

    EXTRACTION_MODE_ALL_CONFLICT = [
        ("All", None),
        ("Specific", "Specific"),
    ]

    @pytest.mark.parametrize("user_answer, expected", EXTRACTION_MODE_ALL_CONFLICT)
    def test_format_autoextract_all_mode_conflict(
        self, mocker, user_answer, expected, capsys
    ):
        """
        Given
        - An incident type without auto extract mode with specific types under fieldCliNameToExtractSettings.

        When
        - Running format_auto_extract_mode on it.

        Then
        - If the user selected 'All', he will get an warning message and the mode will not be changed.
        - If the user selected 'Specific', the mode will be changed.
        """
        mock_dict = {
            "extractSettings": {
                "mode": None,
                "fieldCliNameToExtractSettings": {
                    "incident_field": {
                        "extractAsIsIndicatorTypeId": "",
                        "isExtractingAllIndicatorTypes": False,
                        "extractIndicatorTypesIDs": [],
                    }
                },
            }
        }
        mocker.patch(
            "demisto_sdk.commands.format.update_generic.get_dict_from_file",
            return_value=(mock_dict, "mock_type"),
        )
        mocker.patch(
            "demisto_sdk.commands.format.update_incidenttype.click.prompt",
            return_value=user_answer,
        )
        formatter = IncidentTypesJSONFormat("test")
        formatter.format_auto_extract_mode()
        stdout, _ = capsys.readouterr()
        current_mode = formatter.data.get("extractSettings", {}).get("mode")
        assert current_mode == expected
        if user_answer == "All":
            assert 'Cannot set mode to "All" since there are specific types' in stdout

    EXTRACTION_MODE_SPECIFIC_CONFLICT = [
        ("All", "All"),
        ("Specific", "Specific"),
    ]

    @pytest.mark.parametrize("user_answer, expected", EXTRACTION_MODE_SPECIFIC_CONFLICT)
    def test_format_autoextract_specific_mode_conflict(
        self, mocker, user_answer, expected, capsys
    ):
        """
        Given
        - An incident type without auto extract mode and without specific types under fieldCliNameToExtractSettings.

        When
        - Running format_auto_extract_mode on it.

        Then
        - If the user selected 'Specific', the mode will be changed but he will get a warning that no specific types were found.
        - If the user selected 'All', the mode will be changed.
        """
        mock_dict = {
            "extractSettings": {"mode": None, "fieldCliNameToExtractSettings": {}}
        }
        mocker.patch(
            "demisto_sdk.commands.format.update_generic.get_dict_from_file",
            return_value=(mock_dict, "mock_type"),
        )
        mocker.patch(
            "demisto_sdk.commands.format.update_incidenttype.click.prompt",
            return_value=user_answer,
        )
        formatter = IncidentTypesJSONFormat("test")
        formatter.format_auto_extract_mode()
        stdout, _ = capsys.readouterr()
        current_mode = formatter.data.get("extractSettings", {}).get("mode")
        assert current_mode == expected
        if user_answer == "Specific":
            assert (
                'Please notice that mode was set to "Specific" but there are no specific types'
                in stdout
            )


def test_update_connection_removes_unnecessary_keys(tmpdir, monkeypatch):
    """
    Given
        - A connection json file with a key that's not exist in the schema
    When
        - Run format on it
    Then
        - Ensure the key is deleted from the connection file
    """
    connection_file_path = f"{tmpdir}canvas-context-connections.json"
    connection_file_content = {
        "canvasContextConnections": [
            {
                "contextKey1": "MD5",
                "contextKey2": "SHA256",
                "connectionDescription": "Belongs to the same file",
                "parentContextKey": "File",
                "not_needed key": "not needed value",
            }
        ],
        "fromVersion": "5.0.0",
    }
    with open(connection_file_path, "w") as file:
        json.dump(connection_file_content, file)
    connection_formatter = ConnectionJSONFormat(
        input=connection_file_path,
        output=connection_file_path,
        path=CONNECTION_SCHEMA_PATH,
    )
    connection_formatter.assume_yes = True
    monkeypatch.setattr("builtins.input", lambda _: "N")
    connection_formatter.format_file()
    with open(connection_file_path) as file:
        formatted_connection = json.load(file)
    for connection in formatted_connection["canvasContextConnections"]:
        assert "not_needed key" not in connection


def test_update_connection_updates_from_version(tmpdir):
    """
    Given
        - A connection json file
    When
        - Run format on it with from version parameter
    Then
        - Ensure fromVersion is updated accordingly
    """
    connection_file_path = f"{tmpdir}canvas-context-connections.json"
    connection_file_content = {
        "canvasContextConnections": [
            {
                "contextKey1": "MD5",
                "contextKey2": "SHA256",
                "connectionDescription": "Belongs to the same file",
                "parentContextKey": "File",
            }
        ],
        "fromVersion": "5.0.0",
    }
    with open(connection_file_path, "w") as file:
        json.dump(connection_file_content, file)
    connection_formatter = ConnectionJSONFormat(
        input=connection_file_path,
        output=connection_file_path,
        from_version="6.0.0",
        path=CONNECTION_SCHEMA_PATH,
    )
    connection_formatter.format_file()
    with open(connection_file_path) as file:
        formatted_connection = json.load(file)
    assert formatted_connection["fromVersion"] == "6.0.0"


def test_update_id_indicatortype_positive(mocker, tmpdir):
    """
    Given
        - A dictionary of indicatortype file that the id is not equal to the details
    When
        - Run format on indicatortype file
    Then
        - Ensure id updated successfully
    """
    mocker.patch.object(update_indicatortype, "IndicatorTypeJSONFormat")

    indicator_formater = IndicatorTypeJSONFormat(input="test", output=tmpdir)
    indicator_formater.data = {"id": "1234", "details": "12345"}
    indicator_formater.update_id(field="details")
    assert indicator_formater.data["id"] == indicator_formater.data["details"]


def test_update_id_indicatortype_negative(mocker, tmpdir):
    """
    Given
        - A dictionary of indicator-type file that the details field is missing
    When
        - Run format on indicator-type file
    Then
        - Ensure the return Exception is 'Missing "details" field in file test - add this field manually'
    """
    mocker.patch.object(update_indicatortype, "IndicatorTypeJSONFormat")
    indicator_formater = IndicatorTypeJSONFormat(input="test", output=tmpdir)
    indicator_formater.data = {"id": "1234"}
    try:
        indicator_formater.update_id()
    except Exception as error:
        assert (
            error.args[0]
            == 'Missing "details" field in file test - add this field manually'
        )


def test_update_id_incidenttype_positive(mocker, tmpdir):
    """
    Given
        - A dictionary of incident-type file that the id is not equal to the name
    When
        - Run format on incident-type file
    Then
        - Ensure id updated successfully
    """
    mocker.patch.object(update_incidenttype, "IncidentTypesJSONFormat")

    incident_formater = IncidentTypesJSONFormat(input="test", output=tmpdir)
    incident_formater.data = {"id": "1234", "name": "12345"}
    incident_formater.update_id()
    assert incident_formater.data["id"] == incident_formater.data["name"]


def test_update_id_incidenttype_negative(mocker, tmpdir):
    """
    Given
        - A dictionary of incident-type file that the name field is missing
    When
        - Run format on incident-type file
    Then
        - Ensure the return Exception is 'Missing "name" field in file test - add this field manually'
    """
    mocker.patch.object(update_incidenttype, "IncidentTypesJSONFormat")
    incident_formater = IncidentTypesJSONFormat(input="test", output=tmpdir)
    incident_formater.data = {"id": "1234"}
    try:
        incident_formater.update_id()
    except Exception as error:
        assert (
            error.args[0]
            == 'Missing "name" field in file test - add this field manually'
        )


def test_update_id_dashboard_positive(mocker, tmpdir):
    """
    Given
        - A dictionary of dashboard file that the id is not equal to the name
    When
        - Run format on dashboard file
    Then
        - Ensure id updated successfully
    """
    mocker.patch.object(update_dashboard, "DashboardJSONFormat")

    dashboard_formater = DashboardJSONFormat(input="test", output=tmpdir)
    dashboard_formater.data = {"id": "1234", "name": "12345"}
    dashboard_formater.update_id()
    assert dashboard_formater.data["id"] == dashboard_formater.data["name"]


def test_update_id_dashboard_negative(mocker, tmpdir):
    """
    Given
        - A dictionary of dashboard file that the name field is missing
    When
        - Run format on dashboard file
    Then
        - Ensure the return Exception is 'Missing "name" field in file test - add this field manually'
    """
    mocker.patch.object(update_dashboard, "DashboardJSONFormat")
    dashboard_formater = DashboardJSONFormat(input="test", output=tmpdir)
    dashboard_formater.data = {"id": "1234"}
    try:
        dashboard_formater.update_id()
    except Exception as error:
        assert (
            error.args[0]
            == 'Missing "name" field in file test - add this field manually'
        )


@pytest.mark.parametrize("name", ["MyDashboard", "MyDashboard ", " MyDashboard "])
def test_remove_spaces_end_of_id_and_name(pack, name):
    """
    Given
        - An dashboard which id doesn't ends with whitespaces.
        - An dashboard which id ends with spaces.
    When
        - Running format.
    Then
        - Ensure that the json fields (name, id) that need to be changed are changed.
    """
    dashboard = pack.create_dashboard(name)
    dashboard.write_json({"id": name, "name": name})
    base_update_json = BaseUpdateJSON(input=dashboard.path)
    base_update_json.remove_spaces_end_of_id_and_name()
    assert base_update_json.data["name"] == "MyDashboard"


@pytest.mark.parametrize(
    argnames="marketplaces",
    argvalues=[
        [MarketplaceVersions.MarketplaceV2.value],
        [MarketplaceVersions.XSOAR.value, MarketplaceVersions.MarketplaceV2.value],
    ],
)
def test_set_marketplaces_xsoar_only_for_aliased_fields(mocker, pack, marketplaces):
    """
    Given
        - An incident filed with aliases
    When
        - Run format command
    Then
        - Ensure that the marketplaces value in the aliased filed contain only the `xsoar` marketplace
    """
    mocked_field = {"marketplaces": marketplaces}

    def mock_field_generator():
        yield mocked_field, ""

    mocker.patch.object(IncidentFieldJSONFormat, "_save_alias_field_file")
    mocker.patch.object(
        IncidentFieldJSONFormat,
        "_get_incident_fields_by_aliases",
        return_value=mock_field_generator(),
    )

    tested_filed = pack.create_incident_field(
        name="tested_filed", content={"Aliases": [{"cliName": "aliased_field"}]}
    )

    incident_field_formatter = IncidentFieldJSONFormat(
        input=tested_filed.path, id_set_path="mocked_path"
    )
    incident_field_formatter.format_marketplaces_field_of_aliases()
    updated_marketplaces = incident_field_formatter._save_alias_field_file.call_args[1][
        "field_data"
    ]["marketplaces"]

    assert len(updated_marketplaces) == 1
    assert updated_marketplaces[0] == "xsoar"


class TestFormattingLayoutscontainer:
    @pytest.fixture()
    def layoutscontainer_copy(self):
        os.makedirs(LAYOUTS_CONTAINER_PATH, exist_ok=True)
        yield shutil.copyfile(
            SOURCE_FORMAT_LAYOUTS_CONTAINER, DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY
        )
        if os.path.exists(DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY):
            os.remove(DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY)
        shutil.rmtree(LAYOUTS_CONTAINER_PATH, ignore_errors=True)

    @pytest.fixture()
    def layoutscontainer_formatter(self, layoutscontainer_copy):
        layoutscontainer_formatter = LayoutBaseFormat(
            input=layoutscontainer_copy,
            output=DESTINATION_FORMAT_LAYOUTS_CONTAINER_COPY,
            clear_cache=True,
            path=LAYOUTS_CONTAINER_SCHEMA_PATH,
        )
        yield layoutscontainer_formatter

    @pytest.mark.parametrize(
        "layout_key_field_1, layout_key_field_2",
        [("detailsV2", "details"), ("close", "quickView")],
    )
    def test_remove_non_existent_fields(
        self, layout_key_field_1, layout_key_field_2, pack, id_set_file_mock
    ):
        """
        Given
            - a layout container json file content

        When
            - removing in-existent fields from the container-layout.

        Then
            - Ensure incident fields which are not in the id set file are removed from the container-layout.
        """
        container_layout_content = {}
        for layout_key in (layout_key_field_1, layout_key_field_2):
            container_layout_content[layout_key] = {
                "tabs": [
                    {
                        "sections": [
                            {
                                "items": [
                                    {"fieldId": "incident-field-1"},
                                    {"fieldId": "incident-field-3"},
                                    {"fieldId": "incident-field-2"},
                                ]
                            }
                        ]
                    }
                ]
            }

        formatter = LayoutBaseFormat(
            input=pack.create_layoutcontainer(
                name="layoutscontainer-in-existent-fields-test",
                content=container_layout_content,
            ).path,
            id_set_path=id_set_file_mock.path,
        )

        # remove the original container layout
        for layout_key in (layout_key_field_1, layout_key_field_2):
            container_layout_content[layout_key]["tabs"][0]["sections"][0]["items"] = [
                {"fieldId": "incident-field-1"},
                {"fieldId": "incident-field-2"},
            ]

        formatter.remove_non_existent_fields_container_layout()
        assert formatter.data == container_layout_content

    @patch("builtins.input", lambda *args: "incident")
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
        assert layoutscontainer_formatter.data.get("group") == "incident"

    def test_update_id(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file with non matching name and id.
        When
            - Run format on layout file
        Then
            - Ensure that name and id are  matching
        """
        layoutscontainer_formatter.data["name"] = "name"
        layoutscontainer_formatter.data["id"] = "id"
        layoutscontainer_formatter.update_id()
        assert (
            layoutscontainer_formatter.data["name"]
            == layoutscontainer_formatter.data["id"]
        )

    def test_remove_copy_and_dev_suffixes_from_layoutcontainer(
        self, layoutscontainer_formatter
    ):
        """
        Given
            - A layoutscontainer file with _copy suffix in the layout name ans sub script
        When
            - Run format on layout file
        Then
            - Ensure that name and sub script does not include the _copy suffix
        """
        assert layoutscontainer_formatter.data["name"] == "IP hadas_copy"
        assert (
            layoutscontainer_formatter.data.get("indicatorsDetails")
            .get("tabs")[0]
            .get("sections")[9]
            .get("query")
            == "script_test_dev"
        )
        assert (
            layoutscontainer_formatter.data.get("indicatorsDetails")
            .get("tabs")[0]
            .get("sections")[9]
            .get("name")
            == "testing_copy"
        )
        layoutscontainer_formatter.remove_copy_and_dev_suffixes_from_layoutscontainer()
        assert layoutscontainer_formatter.data["name"] == "IP hadas"
        assert (
            layoutscontainer_formatter.data.get("indicatorsDetails")
            .get("tabs")[0]
            .get("sections")[9]
            .get("query")
            == "script_test"
        )
        assert (
            layoutscontainer_formatter.data.get("indicatorsDetails")
            .get("tabs")[0]
            .get("sections")[9]
            .get("name")
            == "testing"
        )

    @pytest.mark.parametrize(
        "schema",
        [
            GENERICFIELD_SCHEMA_PATH,
            INCIDENTFIELD_SCHEMA_PATH,
            INDICATORFIELD_SCHEMA_PATH,
        ],
    )
    def test_remove_null_doesnt_remove_defaultrows_type_grid(self, schema):
        """
        Given
            - Generic, indicator and incident fields schemes with 'defaultrows' key of type "grid"
        When
            - Run remove_null_fields on Generic, indicator and incident fields files
        Then
            - Ensure defaultRows key remains the same
        """
        incident_formater = BaseUpdateJSON(input="test", output="")
        incident_formater.schema_path = schema
        incident_formater.data = {"defaultRows": [], "type": "grid"}
        incident_formater.remove_null_fields()
        assert incident_formater.data["defaultRows"] == []

    @pytest.mark.parametrize(
        "schema",
        [
            GENERICFIELD_SCHEMA_PATH,
            INCIDENTFIELD_SCHEMA_PATH,
            INDICATORFIELD_SCHEMA_PATH,
        ],
    )
    def test_remove_null_remove_defaultrows_non_grid(self, schema):
        """
        Given
            - Generic, indicator and incident fields schemes with 'defaultrows' key of type "grid"
        When
            - Run remove_null_fields on Generic, indicator and incident fields files
        Then
            - Ensure defaultRows key updated successfully
        """
        incident_formater = BaseUpdateJSON(input="test", output="", path=schema)
        incident_formater.data = {"defaultRows": [], "type": "shortText"}
        incident_formater.remove_null_fields()
        assert "defaultRows" not in incident_formater.data

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
        for kind in [
            "close",
            "details",
            "detailsV2",
            "edit",
            "indicatorsQuickView",
            "mobile",
        ]:
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
        for field in ["fromServerVersion", "quickView", "sortValues"]:
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
        assert "description" in layoutscontainer_formatter.data

    def test_set_fromVersion(self, layoutscontainer_formatter):
        """
        Given
            - A layoutscontainer file without a fromVersion field
        When
            - Run format on layout file
        Then
            - Ensure that fromVersion field was updated successfully with GENERAL_DEFAULT_FROMVERSION value
        """
        from demisto_sdk.commands.common.constants import GENERAL_DEFAULT_FROMVERSION

        layoutscontainer_formatter.from_version = GENERAL_DEFAULT_FROMVERSION
        layoutscontainer_formatter.set_fromVersion()
        assert (
            layoutscontainer_formatter.data.get("fromVersion")
            == GENERAL_DEFAULT_FROMVERSION
        )

    def test_set_output_path(self, layoutscontainer_formatter):
        """
        Given
            - A layout file without an invalid output path
            - The input is the same as the output
        When
            - Run format on layout file
        Then
            - Ensure that the output file path was updated with the correct path
            - Ensure the original file was renamed
        """
        expected_path = "Layouts/layoutscontainer-formatted_layoutscontainer-test.json"
        invalid_output_path = layoutscontainer_formatter.output_file
        layoutscontainer_formatter.layoutscontainer__set_output_path()
        assert invalid_output_path != layoutscontainer_formatter.output_file
        assert expected_path == layoutscontainer_formatter.output_file

        # since we are renaming the file, we need to clean it here
        os.remove(layoutscontainer_formatter.output_file)


class TestFormattingLayout:
    @pytest.fixture()
    def layouts_copy(self):
        os.makedirs(LAYOUT_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_LAYOUT_COPY, DESTINATION_FORMAT_LAYOUT_COPY)
        os.remove(DESTINATION_FORMAT_LAYOUT_COPY)
        os.rmdir(LAYOUT_PATH)

    @pytest.fixture()
    def layouts_formatter(self, layouts_copy):
        yield LayoutBaseFormat(
            input=layouts_copy,
            output=DESTINATION_FORMAT_LAYOUT_COPY,
            path=LAYOUT_SCHEMA_PATH,
        )

    @pytest.fixture()
    def invalid_path_layouts_formatter(self, layouts_copy):
        yield LayoutBaseFormat(
            input=layouts_copy,
            output=DESTINATION_FORMAT_LAYOUT_INVALID_NAME_COPY,
            path=LAYOUT_SCHEMA_PATH,
        )

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
        for field in ["fromServerVersion", "quickView", "sortValues", "locked"]:
            assert field not in layouts_formatter.data

    def test_remove_non_existent_fields(self, pack, id_set_file_mock):
        """
        Given
            - a layout json file content.

        When
            - removing in-existent fields from the layout.

        Then
            - Ensure incident fields which are not in the id set file are removed from the layout.
        """
        layout_content = {
            "layout": {
                "sections": [
                    {
                        "fields": [
                            {"fieldId": "incident-field-4"},
                            {"fieldId": "incident-field-2"},
                            {"fieldId": "incident-field-5"},
                        ]
                    }
                ]
            }
        }

        formatter = LayoutBaseFormat(
            input=pack.create_layout(
                name="layout-non-existent-fields-test", content=layout_content
            ).path,
            id_set_path=id_set_file_mock.path,
        )

        # remove the original container layout
        layout_content["layout"]["sections"][0]["fields"] = [
            {"fieldId": "incident-field-2"}
        ]

        formatter.remove_non_existent_fields_layout()
        assert formatter.data == layout_content

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
        assert "description" in layouts_formatter.data

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
        assert layouts_formatter.data.get("toVersion") == "5.9.9"

    def test_remove_copy_and_dev_suffixes_from_layout(self, layouts_formatter):
        """
        Given
            - A layout file with _copy suffix in one of the script in a dynamic section
        When
            - Run format on layout file
        Then
            - Ensure that the script name does not include the _copy suffix
        """
        assert layouts_formatter.data.get("typeId") == "ExtraHop Detection_dev"
        assert (
            layouts_formatter.data.get("layout").get("sections")[1].get("query")
            == "scriptName_copy"
        )
        assert (
            layouts_formatter.data.get("layout").get("sections")[1].get("name")
            == "test_copy"
        )

        layouts_formatter.remove_copy_and_dev_suffixes_from_layout()
        assert layouts_formatter.data.get("typeId") == "ExtraHop Detection"
        assert (
            layouts_formatter.data.get("layout").get("sections")[1].get("query")
            == "scriptName"
        )
        assert (
            layouts_formatter.data.get("layout").get("sections")[1].get("name")
            == "test"
        )

    def test_set_output_path(self, invalid_path_layouts_formatter):
        """
        Given
            - A layout file without an invalid output path
        When
            - Run format on layout file
        Then
            - Ensure that the output file path was updated with the correct path
        """
        expected_path = "Layouts/layout-layoutt-copy.json"
        invalid_output_path = invalid_path_layouts_formatter.output_file
        invalid_path_layouts_formatter.layout__set_output_path()
        assert invalid_output_path != invalid_path_layouts_formatter.output_file
        assert expected_path == invalid_path_layouts_formatter.output_file


class TestFormattingPreProcessRule:
    @pytest.fixture(autouse=True)
    def pre_process_rules_copy(self):
        os.makedirs(PRE_PROCESS_RULES_PATH, exist_ok=True)
        yield shutil.copyfile(
            SOURCE_FORMAT_PRE_PROCESS_RULES_COPY,
            DESTINATION_FORMAT_PRE_PROCESS_RULES_COPY,
        )
        os.remove(DESTINATION_FORMAT_PRE_PROCESS_RULES_COPY)
        os.rmdir(PRE_PROCESS_RULES_PATH)

    @pytest.fixture(autouse=True)
    def pre_process_rules_formatter(self, pre_process_rules_copy):
        yield PreProcessRulesFormat(
            input=pre_process_rules_copy,
            output=DESTINATION_FORMAT_PRE_PROCESS_RULES_COPY,
            path=PRE_PROCESS_RULES_SCHEMA_PATH,
        )

    @pytest.fixture(autouse=True)
    def invalid_path_pre_process_rules_formatter(self, pre_process_rules_copy):
        yield PreProcessRulesFormat(
            input=pre_process_rules_copy,
            output=DESTINATION_FORMAT_PRE_PROCESS_RULES_INVALID_NAME_COPY,
            path=PRE_PROCESS_RULES_SCHEMA_PATH,
        )

    def test_remove_unnecessary_keys(self, pre_process_rules_formatter):
        """
        Given
            - A pre_process_rule file with fields that dont exit in pre_process_rule schema.
        When
            - Run format on pre_process_rule file
        Then
            - Ensure that unnecessary keys were removed
        """
        pre_process_rules_formatter.schema_path = PRE_PROCESS_RULES_SCHEMA_PATH
        pre_process_rules_formatter.remove_unnecessary_keys()
        for field in ["quickView", "sortValues", "someFieldName"]:
            assert field not in pre_process_rules_formatter.data

    def test_set_description(self, pre_process_rules_formatter):
        """
        Given
            - A pre_process_rule file without a description field
        When
            - Run format on pre_process_rule file
        Then
            - Ensure that description field was updated successfully with '' value
        """
        pre_process_rules_formatter.set_description()
        assert "description" in pre_process_rules_formatter.data


class TestFormattingList:
    @pytest.fixture(autouse=True)
    def lists_copy(self):
        os.makedirs(LISTS_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_LISTS_COPY, DESTINATION_FORMAT_LISTS_COPY)
        os.remove(DESTINATION_FORMAT_LISTS_COPY)
        os.rmdir(LISTS_PATH)

    @pytest.fixture(autouse=True)
    def lists_formatter(self, lists_copy):
        yield ListsFormat(
            input=lists_copy,
            output=DESTINATION_FORMAT_LISTS_COPY,
            path=LISTS_SCHEMA_PATH,
        )

    def test_remove_unnecessary_keys(self, lists_formatter):
        """
        Given
            - A list file with fields that don't exit in list's schema.
        When
            - Run format on list file
        Then
            - Ensure that unnecessary keys were removed
        """
        lists_formatter.schema_path = LISTS_SCHEMA_PATH
        lists_formatter.remove_unnecessary_keys()
        for field in ["quickView", "sortValues"]:
            assert field not in lists_formatter.data

    def test_set_description(self, lists_formatter):
        """
        Given
            - A list file without a description field
        When
            - Run format on list file
        Then
            - Ensure that description field was updated successfully with '' value
        """
        lists_formatter.set_description()
        assert "description" in lists_formatter.data


class TestFormattingClassifier:
    @pytest.fixture(autouse=True)
    def classifier_copy(self):
        os.makedirs(CLASSIFIER_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_CLASSIFIER, DESTINATION_FORMAT_CLASSIFIER)
        os.remove(DESTINATION_FORMAT_CLASSIFIER)
        os.rmdir(CLASSIFIER_PATH)

    @pytest.fixture(autouse=True)
    def classifier_formatter(self, classifier_copy):
        yield ClassifierJSONFormat(
            input=classifier_copy,
            output=DESTINATION_FORMAT_CLASSIFIER,
            clear_cache=True,
            path=CLASSIFIER_SCHEMA_PATH,
        )

    def test_arguments_to_remove(self, classifier_formatter):
        """
        Given
            - A classifier file with fields that dont exit in classifier schema.
        When
            - Run the arguments_to_remove function.
        Then
            - Ensure the keys that should be removed are identified correctly.
        """
        classifier_formatter.schema_path = CLASSIFIER_SCHEMA_PATH
        args_to_remove = classifier_formatter.arguments_to_remove()
        expected_args = [
            "brands",
            "instanceIds",
            "itemVersion",
            "locked",
            "logicalVersion",
            "mapping",
            "packID",
            "system",
            "toServerVersion",
            "sourceClassifierId",
            "fromServerVersion",
            "nameRaw",
        ]
        assert set(expected_args) == args_to_remove

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
        for field in [
            "brands",
            "instanceIds",
            "itemVersion",
            "locked",
            "logicalVersion",
            "mapping",
            "packID",
            "system",
            "toServerVersion",
        ]:
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
        assert "keyTypeMap" in classifier_formatter.data

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
        assert "transformer" in classifier_formatter.data

    def test_set_fromVersion(self, classifier_formatter):
        """
        Given
            - A classifier file without a fromVersion field
        When
            - Run format on classifier file
        Then
            - Ensure that fromVersion field was updated successfully with '6.0.0' value
        """
        from demisto_sdk.commands.common.constants import GENERAL_DEFAULT_FROMVERSION

        classifier_formatter.from_version = GENERAL_DEFAULT_FROMVERSION
        classifier_formatter.set_fromVersion()
        assert (
            classifier_formatter.data.get("fromVersion") == GENERAL_DEFAULT_FROMVERSION
        )


class TestFormattingOldClassifier:
    @pytest.fixture(autouse=True)
    def classifier_5_9_9_copy(self):
        os.makedirs(CLASSIFIER_PATH, exist_ok=True)
        yield shutil.copyfile(
            SOURCE_FORMAT_CLASSIFIER_5_9_9, DESTINATION_FORMAT_CLASSIFIER_5_9_9
        )
        os.remove(DESTINATION_FORMAT_CLASSIFIER_5_9_9)
        os.rmdir(CLASSIFIER_PATH)

    @pytest.fixture(autouse=True)
    def classifier_formatter(self, classifier_5_9_9_copy):
        yield OldClassifierJSONFormat(
            input=classifier_5_9_9_copy,
            output=DESTINATION_FORMAT_CLASSIFIER_5_9_9,
            path=CLASSIFIER_5_9_9_SCHEMA_PATH,
        )

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
        for field in ["sourceClassifierId", "locked", "toServerVersion"]:
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
        assert classifier_formatter.data.get("toVersion") == "5.9.9"

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
        for field in ["defaultIncidentType", "sortValues", "unclassifiedCases"]:
            assert field not in classifier_formatter.data


class TestFormattingPackMetaData:
    @pytest.mark.parametrize(
        "deprecated_integration, pack_name, pack_description, new_pack_name_to_use",
        [
            (True, "pack name", "pack description", "pack v2"),
            (
                True,
                "pack name (Deprecated)",
                "Deprecated. Use pack v2 instead.",
                "pack v2",
            ),
            (True, "pack name", "pack description", ""),
            (False, "pack name", "pack description", ""),
        ],
    )
    def test_deprecate_pack(
        self,
        mocker,
        pack,
        deprecated_integration,
        pack_name,
        pack_description,
        new_pack_name_to_use,
    ):
        """
        Given
          - Case 1: a deprecated integration and a pack that its description/name doesn't state its deprecated.
          - Case 2: a deprecated integration and a pack that its description/name states its deprecated.
          - Case 3: a deprecated integration and a pack that its description/name doesn't state its deprecated.
          - Case 4: a non-deprecated integration and a pack that its description/name doesn't state its deprecated.

        When
          - running trying to run the deprecate pack format.

        Then
          - Case 1: pack name should be: pack name (Deprecated),
                    pack description should be: Deprecated. Use pack v2 instead.
          - Case 2: pack name should be: pack name (Deprecated),
                    pack description should be: Deprecated. Use pack v2 instead.
                    (nothing should change as pack is already deprecated).
          - Case 3: pack name should be: pack name (Deprecated),
                    pack description should be: Deprecated. no available replacement.
          - Case 4: pack name should be: pack name, pack description should be: pack description.
        """
        pack.create_integration(name="integration-1").yml.update(
            {"deprecated": deprecated_integration}
        )
        pack.pack_metadata.update({"name": pack_name, "description": pack_description})

        pack_metadata_formatter = PackMetadataJsonFormat(input=pack.pack_metadata.path)
        mocker.patch.object(
            pack_metadata_formatter, "get_answer", return_value=new_pack_name_to_use
        )

        pack_metadata_formatter.deprecate_pack()
        if deprecated_integration:
            expected_pack_name = "pack name (Deprecated)"
            if new_pack_name_to_use:
                expected_pack_description = (
                    f"Deprecated. Use {new_pack_name_to_use} instead."
                )
            else:
                expected_pack_description = "Deprecated. No available replacement."
        else:
            expected_pack_name = "pack name"
            expected_pack_description = "pack description"
        assert pack_metadata_formatter.data["name"] == expected_pack_name
        assert pack_metadata_formatter.data["description"] == expected_pack_description


class TestFormattingMapper:
    @pytest.fixture()
    def mapper_copy(self):
        os.makedirs(MAPPER_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_MAPPER, DESTINATION_FORMAT_MAPPER)
        os.remove(DESTINATION_FORMAT_MAPPER)
        os.rmdir(MAPPER_PATH)

    @pytest.fixture()
    def mapper_formatter(self, mapper_copy):
        yield MapperJSONFormat(
            input=mapper_copy, output=DESTINATION_FORMAT_MAPPER, path=MAPPER_SCHEMA_PATH
        )

    @pytest.mark.parametrize("mapper_type", ["mapping-outgoing", "mapping-incoming"])
    def test_remove_non_existent_fields(self, mapper_type, id_set_file_mock, pack):
        """
        Given
            - outgoing json file content.
            - incoming json file content.

        When
            - removing in-existent fields from the mapper.

        Then
            - Ensure incident fields which are not in the id set file are removed from the mapper.
        """
        mapper_content = {"mapping": {}, "type": mapper_type}
        for i in range(1, 3):
            mapper_content["mapping"][f"test-case-{i}"] = {
                "internalMapping": {
                    "Incident-Field-1": {"simple": "incident-field-1"},
                    "Incident-Field-2": {"simple": "incident-field-2.dueDate"},
                    f"not-existing-field-{i}": {"simple": "incident-field-3"},
                }
            }

        formatter = MapperJSONFormat(
            input=pack.create_classifier(
                name=f"{mapper_type}-non-existent-fields-test", content=mapper_content
            ).path,
            id_set_path=id_set_file_mock.path,
        )

        formatter.remove_non_existent_fields()

        for i in range(1, 3):
            mapper_content["mapping"][f"test-case-{i}"]["internalMapping"].pop(
                f"not-existing-field-{i}"
            )

        assert formatter.data == mapper_content

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
        for field in ["locked", "sourceClassifierId", "toServerVersion"]:
            assert field not in mapper_formatter.data

    def test_set_fromVersion(self, mapper_formatter):
        """
        Given
            - A mapper file without a fromVersion field
        When
            - Run format on mapper file
        Then
            - Ensure that fromVersion field was updated successfully with GENERAL_DEFAULT_FROMVERSION value
        """
        from demisto_sdk.commands.common.constants import GENERAL_DEFAULT_FROMVERSION

        mapper_formatter.from_version = GENERAL_DEFAULT_FROMVERSION
        mapper_formatter.set_fromVersion()
        assert mapper_formatter.data.get("fromVersion") == GENERAL_DEFAULT_FROMVERSION

    def test_update_id(self, mapper_formatter):
        """
        Given
            - A layoutscontainer file with non matching name and id.
        When
            - Run format on layout file
        Then
            - Ensure that name and id are  matching
        """
        mapper_formatter.data["name"] = "name"
        mapper_formatter.data["id"] = "id"
        mapper_formatter.update_id()
        assert mapper_formatter.data["name"] == mapper_formatter.data["id"]


class TestFormattingWidget:
    @pytest.fixture(autouse=True)
    def widget_copy(self):
        os.makedirs(WIDGET_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_WIDGET, DESTINATION_FORMAT_WIDGET)
        os.remove(DESTINATION_FORMAT_WIDGET)
        os.rmdir(WIDGET_PATH)

    @pytest.fixture(autouse=True)
    def widget_formatter(self, widget_copy):
        yield WidgetJSONFormat(
            input=widget_copy, output=DESTINATION_FORMAT_WIDGET, path=WIDGET_SCHEMA_PATH
        )

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
        assert "description" in widget_formatter.data

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
        assert widget_formatter.data.get("isPredefined") is True

    @pytest.mark.parametrize(
        "widget_data",
        [
            {"dataType": "metrics", "fromVersion": "6.2.0"},
            {"dataType": "metrics", "fromVersion": "5.5.0"},
            {"dataType": "incidents", "fromVersion": "5.5.0"},
            {"dataType": "incidents", "fromVersion": "6.2.0"},
        ],
    )
    def test_set_from_version_for_type_metrics(self, widget_formatter, widget_data):
        """
        Given
            - A widget file with dataType and fromVersion fields.
        When
            - Run format on widget file.
        Then
            - Ensure that fromVersion field was updated to minimum 6.2.0 if dataType is 'metrics'.
        """

        widget_formatter.data = widget_data
        widget_formatter.set_from_version_for_type_metrics()

        if widget_formatter.data.get("dataType") == "metrics":
            assert (
                widget_formatter.data.get("fromVersion")
                == widget_formatter.WIDGET_TYPE_METRICS_MIN_VERSION
            )

        else:
            assert widget_formatter.data.get("fromVersion") == widget_data.get(
                "fromVersion"
            )


class TestFormattingReport:
    @pytest.fixture(autouse=True)
    def report_copy(self):
        os.makedirs(REPORT_PATH, exist_ok=True)
        yield shutil.copyfile(SOURCE_FORMAT_REPORT, DESTINATION_FORMAT_REPORT)
        os.remove(DESTINATION_FORMAT_REPORT)
        os.rmdir(REPORT_PATH)

    @pytest.fixture(autouse=True)
    def report_formatter(self, report_copy):
        yield ReportJSONFormat(
            input=report_copy, output=DESTINATION_FORMAT_REPORT, path=REPORT_SCHEMA_PATH
        )

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
        assert "description" in report_formatter.data

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
        assert "recipients" in report_formatter.data

    @patch("builtins.input", lambda *args: "pdf")
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
        assert report_formatter.data.get("type") == "pdf"

    @patch("builtins.input", lambda *args: "landscape")
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
        assert report_formatter.data.get("orientation") == "landscape"

    @staticmethod
    def exception_raise(
        default_from_version: str = "", file_type: Optional[str] = None
    ):
        raise ValueError("MY ERROR")

    FORMAT_OBJECT = [
        ClassifierJSONFormat,
        OldClassifierJSONFormat,
        DashboardJSONFormat,
        IncidentFieldJSONFormat,
        IncidentTypesJSONFormat,
        IndicatorFieldJSONFormat,
        IndicatorTypeJSONFormat,
        MapperJSONFormat,
        LayoutBaseFormat,
        ReportJSONFormat,
        WidgetJSONFormat,
        ConnectionJSONFormat,
        ListsFormat,
        PreProcessRulesFormat,
    ]

    @pytest.mark.parametrize(argnames="format_object", argvalues=FORMAT_OBJECT)
    def test_json_run_format_exception_handling(self, format_object, mocker, capsys):
        """
        Given
            - A JSON object formatter
        When
            - Run run_format command and exception is raised.
        Then
            - Ensure the error is printed.
        """
        formatter = format_object(verbose=True, input="my_file_path")
        mocker.patch.object(
            BaseUpdateJSON, "update_json", side_effect=self.exception_raise
        )
        mocker.patch.object(
            BaseUpdateJSON, "set_fromVersion", side_effect=self.exception_raise
        )
        mocker.patch.object(
            BaseUpdateJSON, "remove_unnecessary_keys", side_effect=self.exception_raise
        )
        mocker.patch.object(
            LayoutBaseFormat, "set_layout_key", side_effect=self.exception_raise
        )

        formatter.run_format()
        stdout, _ = capsys.readouterr()
        assert "Failed to update file my_file_path. Error: MY ERROR" in stdout

    def test_set_fromversion_six_new_contributor_pack_no_fromversion(self, pack):
        """
        Given
            - A new contributed pack with no fromversion key at incident_type json
        When
            - Run format command
        Then
            - Ensure that the integration fromversion is set to GENERAL_DEFAULT_FROMVERSION
        """
        from demisto_sdk.commands.common.constants import GENERAL_DEFAULT_FROMVERSION

        pack.pack_metadata.update({"support": "partner", "currentVersion": "1.0.0"})
        incident_type = pack.create_incident_type(name="TestType", content={})
        bs = BaseUpdate(
            input=incident_type.path, assume_yes=True, path=INCIDENTTYPE_SCHEMA_PATH
        )
        bs.set_fromVersion()
        assert bs.data["fromVersion"] == GENERAL_DEFAULT_FROMVERSION

    def test_set_fromversion_six_new_contributor_pack(self, pack):
        """
        Given
            - A new contributed pack with - incident types, incident field, indicator field, indicator type,
            classifier and layout s
        When
            - Run format command
        Then
            - Ensure that the integration fromversion is set to GENERAL_DEFAULT_FROMVERSION
        """
        from demisto_sdk.commands.common.constants import GENERAL_DEFAULT_FROMVERSION

        pack.pack_metadata.update({"support": "partner", "currentVersion": "1.0.0"})
        incident_type = pack.create_incident_type(name="TestType")
        incident_field = pack.create_incident_field(name="TestField")
        indicator_field = pack.create_indicator_field(name="TestField")
        indicator_type = pack.create_indicator_type(name="TestType")
        classifier = pack.create_classifier(name="TestClassifier")
        layout = pack.create_layout(name="TestLayout")
        for path, schema_path in zip(
            [
                incident_type.path,
                incident_field.path,
                indicator_field.path,
                indicator_type.path,
                classifier.path,
                layout.path,
            ],
            [
                INCIDENTTYPE_SCHEMA_PATH,
                INCIDENTFIELD_SCHEMA_PATH,
                INDICATORFIELD_SCHEMA_PATH,
                INDICATORTYPE_SCHEMA_PATH,
                CLASSIFIER_SCHEMA_PATH,
                LAYOUTS_CONTAINER_SCHEMA_PATH,
            ],
        ):
            bs = BaseUpdate(input=path, assume_yes=True, path=schema_path)
            bs.set_fromVersion()
            assert bs.data["fromVersion"] == GENERAL_DEFAULT_FROMVERSION

    def test_json_run_format_old_layout(self, mocker, pack):
        """
        Given
            - A new (old) layout.
        When
            - Run format command.
        Then
            - Ensure that the fromversion is set to 5.5.0.
        """
        from demisto_sdk.commands.common.constants import VERSION_5_5_0

        mocker.patch.object(BaseUpdateJSON, "remove_null_fields")
        mocker.patch.object(LayoutBaseFormat, "remove_unnecessary_keys")
        mocker.patch.object(BaseUpdate, "sync_data_to_master")

        layout = pack.create_layout(name="TestType", content={})
        bs = LayoutBaseFormat(
            input=layout.path, assume_yes=True, path=LAYOUTS_CONTAINER_SCHEMA_PATH
        )
        bs.run_format()
        assert bs.data["fromVersion"] == VERSION_5_5_0

    def test_none_tabs_do_not_throw_exception(self, mocker, pack):
        """
        Given
            - An indicator file with None indicatorsDetails tabs.
        When
            - Run format command.
        Then
            - Ensure command will not throw an exception.
        """

        layout = pack.create_layout(
            name="TestType",
            content={
                "name": "SHA256_Indicator_dev",
                "cacheVersn": 0,
                "close": None,
                "definitionId": "",
                "description": "",
                "detached": False,
                "details": None,
                "detailsV2": None,
                "edit": None,
                "fromServerVersion": "",
                "group": "indicator",
                "id": "SHA256 Indicator",
                "indicatorsDetails": {"TypeName": "", "tabs": None},
                "fromVersion": "",
            },
        )
        bs = LayoutBaseFormat(input=layout.path, assume_yes=True)
        bs.remove_copy_and_dev_suffixes_from_layoutscontainer()
        assert bs.data["name"] == "SHA256_Indicator"

    def test_json_run_format_old_classifier(self, mocker, pack):
        """
        Given
            - A new old_classifier.
        When
            - Run format command.
        Then
            - Ensure that the fromversion is set to 5.5.0.
        """
        from demisto_sdk.commands.common.constants import VERSION_5_5_0

        mocker.patch.object(BaseUpdateJSON, "remove_null_fields")
        mocker.patch.object(BaseUpdate, "remove_unnecessary_keys")
        mocker.patch.object(BaseUpdate, "sync_data_to_master")

        classifier = pack.create_classifier(name="TestType", content={})
        bs = OldClassifierJSONFormat(
            input=classifier.path, assume_yes=True, path=CLASSIFIER_5_9_9_SCHEMA_PATH
        )
        bs.run_format()
        assert bs.data["fromVersion"] == VERSION_5_5_0


def test_not_updating_id_in_old_json_file(repo):
    """
    Given
        - An old json file with non matching name and id.
    When
        - Run format on file
    Then
        - Ensure that name and id are still not matching
    """
    pack = repo.create_pack()
    json_incident_type = pack.create_incident_type(name="some_name")

    json_object = BaseUpdateJSON(input=json_incident_type.path)
    json_object.data["name"] = "name"
    json_object.data["id"] = "not_name"
    json_object.old_file = json_object.data.copy()
    json_object.update_id()
    assert json_object.data["id"] == "not_name"
    assert json_object.data["name"] == "name"


def test_not_updating_modified_id_in_old_json_file(repo):
    """
    Given
        - An old json file with non matching name and id.
        - New id modification.
    When
        - Run format on file.
    Then
        - Ensure that id was not updated.
    """
    pack = repo.create_pack()
    json_incident_type = pack.create_incident_type(name="some_name")

    json_object = BaseUpdateJSON(input=json_incident_type.path)
    json_object.data["name"] = "name"
    json_object.data["id"] = "old_name"
    json_object.old_file = json_object.data.copy()
    json_object.data["id"] = "new_name"
    json_object.update_id()
    assert json_object.data["id"] == "old_name"
