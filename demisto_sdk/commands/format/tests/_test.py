# import os
# import pytest
# from shutil import copyfile
#
#
# from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
# from demisto_sdk.commands.format.update_incidentfields import IncidentFieldJSONFormat
# from demisto_sdk.commands.format.update_incidenttypes import IncidentTypesJSONFormat
# from demisto_sdk.commands.format.update_indicatorfields import IndicatorFieldJSONFormat
# from demisto_sdk.commands.format.update_incidenttypes import IncidentTypesJSONFormat
# from demisto_sdk.commands.format.update_incidenttypes import IncidentTypesJSONFormat
#
# from demisto_sdk.commands.format.format_module import format_manager
#
#
# class TestMergeScriptPackageToYMLIntegration:
#     def setup(self):
#         self.test_dir_path = os.path.join('tests', 'test_files', 'Unifier', 'Testing')
#         os.makedirs(self.test_dir_path)
#         self.package_name = 'SampleIntegPackage'
#         self.export_dir_path = os.path.join(self.test_dir_path, self.package_name)
#         self.expected_yml_path = os.path.join(self.test_dir_path, 'integration-SampleIntegPackage.yml')
#
#     def teardown(self):
#         if self.test_dir_path:
#             shutil.rmtree(self.test_dir_path)
#
#     INPUTS_IS_VALID_VERSION = [
#         (VALID_LAYOUT_PATH, LAYOUT_TARGET, True, LayoutValidator),
#         (INVALID_LAYOUT_PATH, LAYOUT_TARGET, False, LayoutValidator),
#         (VALID_WIDGET_PATH, WIDGET_TARGET, True, WidgetValidator),
#         (INVALID_WIDGET_PATH, WIDGET_TARGET, False, WidgetValidator),
#         (VALID_DASHBOARD_PATH, DASHBOARD_TARGET, True, DashboardValidator),
#         (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
#         (VALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, True, IncidentFieldValidator),
#         (INVALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, False, IncidentFieldValidator),
#         (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
#         (VALID_SCRIPT_PATH, SCRIPT_TARGET, True, ScriptValidator),
#         (INVALID_SCRIPT_PATH, SCRIPT_TARGET, False, ScriptValidator),
#         (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, True, PlaybookValidator),
#         (INVALID_PLAYBOOK_PATH, PLAYBOOK_TARGET, False, PlaybookValidator)
#     ]
#
#     @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_VALID_VERSION)
#     def test_format_file(self, source, target, answer, validator):
#         # type: (str, str, Any, Type[BaseValidator]) -> None
#         res = []
#         try:
#             copyfile(source, target)
#             res = format_manager(False, source)
#             assert validator.is_valid_version() is answer
#         finally:
#             os.remove(target)
