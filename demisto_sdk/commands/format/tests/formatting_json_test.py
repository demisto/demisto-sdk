#
# import os
# import pytest
#
#
# from demisto_sdk.commands.format.update_dashboard import DashboardJSONFormat
# from demisto_sdk.commands.format.update_incidentfields import IncidentFieldJSONFormat
# from demisto_sdk.commands.format.update_incidenttypes import IncidentTypesJSONFormat
# from demisto_sdk.commands.format.update_indicatorfields import IndicatorFieldJSONFormat
# from demisto_sdk.commands.format.update_incidenttypes import IncidentTypesJSONFormat
#
# CREATED_DIRS = list()
# #
# #
# # @classmethod
# # def setup_class(cls):
# #     print("Setups class")
# #     for dir_to_create in DIR_LIST:
# #         if not os.path.exists(dir_to_create):
# #             cls.CREATED_DIRS.append(dir_to_create)
# #             os.mkdir(dir_to_create)
# #
# #
# # @classmethod
# # def teardown_class(cls):
# #     print("Tearing down class")
# #     for dir_to_delete in cls.CREATED_DIRS:
# #         if os.path.exists(dir_to_delete):
# #             os.rmdir(dir_to_delete)
# #
# #
# # INPUTS_IS_VALID_VERSION = [
# #     (VALID_LAYOUT_PATH, LAYOUT_TARGET, True, LayoutValidator),
# #     (INVALID_LAYOUT_PATH, LAYOUT_TARGET, False, LayoutValidator),
# #     (VALID_WIDGET_PATH, WIDGET_TARGET, True, WidgetValidator),
# #     (INVALID_WIDGET_PATH, WIDGET_TARGET, False, WidgetValidator),
# #     (VALID_DASHBOARD_PATH, DASHBOARD_TARGET, True, DashboardValidator),
# #     (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
# #     (VALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, True, IncidentFieldValidator),
# #     (INVALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, False, IncidentFieldValidator),
# #     (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
# #     (VALID_SCRIPT_PATH, SCRIPT_TARGET, True, ScriptValidator),
# #     (INVALID_SCRIPT_PATH, SCRIPT_TARGET, False, ScriptValidator),
# #     (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, True, PlaybookValidator),
# #     (INVALID_PLAYBOOK_PATH, PLAYBOOK_TARGET, False, PlaybookValidator)
# # ]
# #
# #
# # @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_VALID_VERSION)
# # def test_format_file(self, source, target, answer, validator):
# #     # type: (str, str, Any, Type[BaseValidator]) -> None
# #     try:
# #         copyfile(source, target)
# #         structure = StructureValidator(source)
# #         validator = validator(structure)
# #         assert validator.is_valid_version() is answer
# #     finally:
# #         os.remove(target)
