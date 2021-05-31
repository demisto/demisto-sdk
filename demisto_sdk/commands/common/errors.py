from typing import Any, Dict, List

from demisto_sdk.commands.common.constants import (BETA_INTEGRATION_DISCLAIMER,
                                                   CONF_PATH,
                                                   INTEGRATION_CATEGORIES,
                                                   PACK_METADATA_DESC,
                                                   PACK_METADATA_NAME)

FOUND_FILES_AND_ERRORS: list = []
FOUND_FILES_AND_IGNORED_ERRORS: list = []

ALLOWED_IGNORE_ERRORS = ['BA101', 'BA106', 'RP102', 'RP104', 'SC100', 'IF106', 'PA113', 'PA116', 'PB105', 'PB106',
                         'BA108', 'BA109', 'IN109', 'IN110', 'IN122', 'IN126', 'IN128', 'IN135', 'IN136',
                         'MP106', 'RM102', 'PB110', 'PB111', 'SC105', 'IN139', 'PA124', 'PA125', 'RM100', 'RM104']

PRESET_ERROR_TO_IGNORE = {
    'community': ['BC', 'CJ', 'DS100', 'DS101', 'DS102', 'DS103', 'DS104', 'IN125', 'IN126'],
    'partner': ['CJ']
}

PRESET_ERROR_TO_CHECK = {
    "deprecated": ['ST', 'BC', 'BA', 'IN127', 'IN128', 'PB104', 'SC101'],
}

ERROR_CODE = {
    "wrong_version": {'code': "BA100", 'ui_applicable': False, 'related_field': 'version'},
    "id_should_equal_name": {'code': "BA101", 'ui_applicable': False, 'related_field': 'id'},
    "file_type_not_supported": {'code': "BA102", 'ui_applicable': False, 'related_field': ''},
    "file_name_include_spaces_error": {'code': "BA103", 'ui_applicable': False, 'related_field': ''},
    "changes_may_fail_validation": {'code': "BA104", 'ui_applicable': False, 'related_field': ''},
    "invalid_id_set": {'code': "BA105", 'ui_applicable': False, 'related_field': ''},
    "no_minimal_fromversion_in_file": {'code': "BA106", 'ui_applicable': False, 'related_field': 'fromversion'},
    "running_on_master_with_git": {'code': "BA107", 'ui_applicable': False, 'related_field': ''},
    "folder_name_has_separators": {'code': "BA108", 'ui_applicable': False, 'related_field': ''},
    "file_name_has_separators": {'code': "BA109", 'ui_applicable': False, 'related_field': ''},
    "wrong_display_name": {'code': "IN100", 'ui_applicable': True, 'related_field': '<parameter-name>.display'},
    "wrong_default_parameter_not_empty": {'code': "IN101", 'ui_applicable': True,
                                          'related_field': '<parameter-name>.default'},
    "wrong_required_value": {'code': "IN102", 'ui_applicable': True, 'related_field': '<parameter-name>.required'},
    "wrong_required_type": {'code': "IN103", 'ui_applicable': True, 'related_field': '<parameter-name>.type'},
    "wrong_category": {'code': "IN104", 'ui_applicable': True, 'related_field': 'category'},
    "wrong_default_argument": {'code': "IN105", 'ui_applicable': True, 'related_field': '<argument-name>.default'},
    "no_default_arg": {'code': "IN106", 'ui_applicable': True, 'related_field': '<argument-name>.default'},
    "missing_reputation": {'code': "IN107", 'ui_applicable': True, 'related_field': 'outputs'},
    "wrong_subtype": {'code': "IN108", 'ui_applicable': False, 'related_field': 'subtype'},
    "beta_in_id": {'code': "IN109", 'ui_applicable': False, 'related_field': 'id'},
    "beta_in_name": {'code': "IN110", 'ui_applicable': False, 'related_field': 'name'},
    "beta_field_not_found": {'code': "IN111", 'ui_applicable': False, 'related_field': 'beta'},
    "no_beta_in_display": {'code': "IN112", 'ui_applicable': False, 'related_field': 'display'},
    "duplicate_arg_in_file": {'code': "IN113", 'ui_applicable': True, 'related_field': 'arguments'},
    "duplicate_param": {'code': "IN114", 'ui_applicable': True, 'related_field': 'configuration'},
    "invalid_context_output": {'code': "IN115", 'ui_applicable': True, 'related_field': 'outputs'},
    "added_required_fields": {'code': "IN116", 'ui_applicable': False, 'related_field': '<parameter-name>.required'},
    "not_used_display_name": {'code': "IN117", 'ui_applicable': True, 'related_field': '<parameter-name>.display'},
    "empty_display_configuration": {'code': "IN118", 'ui_applicable': True,
                                    'related_field': '<parameter-name>.display'},
    "feed_wrong_from_version": {'code': "IN119", 'ui_applicable': False, 'related_field': 'fromversion'},
    "pwsh_wrong_version": {'code': "IN120", 'ui_applicable': False, 'related_field': 'fromversion'},
    "parameter_missing_from_yml": {'code': "IN121", 'ui_applicable': True, 'related_field': 'configuration'},
    "parameter_missing_for_feed": {'code': "IN122", 'ui_applicable': True, 'related_field': 'configuration'},
    "invalid_v2_integration_name": {'code': "IN123", 'ui_applicable': True, 'related_field': 'display'},
    "found_hidden_param": {'code': "IN124", 'ui_applicable': False, 'related_field': '<parameter-name>.hidden'},
    "no_default_value_in_parameter": {'code': "IN125", 'ui_applicable': False,
                                      'related_field': '<parameter-name>.default'},
    "parameter_missing_from_yml_not_community_contributor": {'code': "IN126", 'ui_applicable': False,
                                                             'related_field': 'configuration'},
    "invalid_deprecated_integration_display_name": {'code': "IN127", 'ui_applicable': False,
                                                    'related_field': 'display'},
    "invalid_deprecated_integration_description": {'code': "IN128", 'ui_applicable': False, 'related_field': ''},
    "removed_integration_parameters": {'code': "IN129", 'ui_applicable': False, 'related_field': 'configuration'},
    "integration_not_runnable": {'code': "IN130", 'ui_applicable': False, 'related_field': 'configuration'},
    "missing_get_mapping_fields_command": {'code': "IN131", 'ui_applicable': False, 'related_field': 'ismappable'},
    "integration_non_existent_classifier": {'code': "IN132", 'ui_applicable': False, 'related_field': 'classifiers'},
    "integration_non_existent_mapper": {'code': "IN133", 'ui_applicable': False, 'related_field': 'mappers'},
    "multiple_default_arg": {'code': "IN134", "ui_applicable": True, 'related_field': "arguments"},
    "invalid_integration_parameters_display_name": {'code': "IN135", 'ui_applicable': True, 'related_field': 'display'},
    "missing_output_context": {'code': "IN136", 'ui_applicable': True, 'related_field': 'contextOutput'},
    "is_valid_integration_file_path_in_folder": {'code': "IN137", 'ui_applicable': False, 'related_field': ''},
    "is_valid_integration_file_path_in_integrations_folder": {'code': "IN138", 'ui_applicable': False,
                                                              'related_field': ''},
    "changed_integration_yml_fields": {'code': "IN138", "ui_applicable": False, 'related_field': 'script'},
    "incident_in_command_name_or_args": {'code': "IN139", "ui_applicable": False,
                                         'related_field': 'script.commands.name'},
    "invalid_v2_script_name": {'code': "SC100", 'ui_applicable': True, 'related_field': 'name'},
    "invalid_deprecated_script": {'code': "SC101", 'ui_applicable': False, 'related_field': 'comment'},
    "invalid_command_name_in_script": {'code': "SC102", 'ui_applicable': False, 'related_field': ''},
    "is_valid_script_file_path_in_folder": {'code': "SC103", 'ui_applicable': False, 'related_field': ''},
    "is_valid_script_file_path_in_scripts_folder": {'code': "SC104", 'ui_applicable': False, 'related_field': ''},
    "incident_in_script_arg": {'code': "SC105", 'ui_applicable': True, 'related_field': 'args.name'},
    "dbot_invalid_output": {'code': "DB100", 'ui_applicable': True, 'related_field': 'contextPath'},
    "dbot_invalid_description": {'code': "DB101", 'ui_applicable': True, 'related_field': 'description'},
    "breaking_backwards_subtype": {'code': "BC100", 'ui_applicable': False, 'related_field': 'subtype'},
    "breaking_backwards_context": {'code': "BC101", 'ui_applicable': False, 'related_field': 'contextPath'},
    "breaking_backwards_command": {'code': "BC102", 'ui_applicable': False, 'related_field': 'contextPath'},
    "breaking_backwards_arg_changed": {'code': "BC103", 'ui_applicable': False, 'related_field': 'name'},
    "breaking_backwards_command_arg_changed": {'code': "BC104", 'ui_applicable': False, 'related_field': 'args'},
    "default_docker_error": {'code': "DO100", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "latest_docker_error": {'code': "DO101", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "not_demisto_docker": {'code': "DO102", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "docker_tag_not_fetched": {'code': "DO103", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "no_docker_tag": {'code': "DO104", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "docker_not_formatted_correctly": {'code': "DO105", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "docker_not_on_the_latest_tag": {'code': "DO106", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "non_existing_docker": {'code': "DO107", 'ui_applicable': True, 'related_field': 'dockerimage'},
    "id_set_conflicts": {'code': "ID100", 'ui_applicable': False, 'related_field': ''},
    "duplicated_id": {'code': "ID102", 'ui_applicable': False, 'related_field': ''},
    "no_id_set_file": {'code': "ID103", 'ui_applicable': False, 'related_field': ''},
    "remove_field_from_dashboard": {'code': "DA100", 'ui_applicable': False, 'related_field': ''},
    "include_field_in_dashboard": {'code': "DA101", 'ui_applicable': False, 'related_field': ''},
    "remove_field_from_widget": {'code': "WD100", 'ui_applicable': False, 'related_field': ''},
    "include_field_in_widget": {'code': "WD101", 'ui_applicable': False, 'related_field': ''},
    "no_image_given": {'code': "IM100", 'ui_applicable': True, 'related_field': 'image'},
    "image_too_large": {'code': "IM101", 'ui_applicable': True, 'related_field': 'image'},
    "image_in_package_and_yml": {'code': "IM102", 'ui_applicable': False, 'related_field': 'image'},
    "not_an_image_file": {'code': "IM103", 'ui_applicable': False, 'related_field': 'image'},
    "no_image_field_in_yml": {'code': "IM104", 'ui_applicable': True, 'related_field': 'image'},
    "image_field_not_in_base64": {'code': "IM105", 'ui_applicable': True, 'related_field': 'image'},
    "default_image_error": {'code': "IM106", 'ui_applicable': True, 'related_field': 'image'},
    "invalid_image_name": {'code': "IM107", 'ui_applicable': False, 'related_field': 'image'},
    "description_missing_from_conf_json": {'code': "CJ100", 'ui_applicable': False, 'related_field': ''},
    "test_not_in_conf_json": {'code': "CJ101", 'ui_applicable': False, 'related_field': ''},
    "integration_not_registered": {'code': "CJ102", 'ui_applicable': False, 'related_field': ''},
    "no_test_playbook": {'code': "CJ103", 'ui_applicable': False, 'related_field': ''},
    "test_playbook_not_configured": {'code': "CJ104", 'ui_applicable': False, 'related_field': ''},
    "missing_release_notes": {'code': "RN100", 'ui_applicable': False, 'related_field': ''},
    "no_new_release_notes": {'code': "RN101", 'ui_applicable': False, 'related_field': ''},
    "release_notes_not_formatted_correctly": {'code': "RN102", 'ui_applicable': False, 'related_field': ''},
    "release_notes_not_finished": {'code': "RN103", 'ui_applicable': False, 'related_field': ''},
    "release_notes_file_empty": {'code': "RN104", 'ui_applicable': False, 'related_field': ''},
    "multiple_release_notes_files": {'code': "RN105", 'ui_applicable': False, 'related_field': ''},
    "missing_release_notes_for_pack": {'code': "RN106", 'ui_applicable': False, 'related_field': ''},
    "missing_release_notes_entry": {'code': "RN107", 'ui_applicable': False, 'related_field': ''},
    "added_release_notes_for_new_pack": {'code': "RN108", 'ui_applicable': False, 'related_field': ''},
    "modified_existing_release_notes": {'code': "RN109", 'ui_applicable': False, 'related_field': ''},
    "playbook_cant_have_rolename": {'code': "PB100", 'ui_applicable': True, 'related_field': 'rolename'},
    "playbook_unreachable_condition": {'code': "PB101", 'ui_applicable': True, 'related_field': 'tasks'},
    "playbook_unhandled_condition": {'code': "PB102", 'ui_applicable': True, 'related_field': 'conditions'},
    "playbook_unconnected_tasks": {'code': "PB103", 'ui_applicable': True, 'related_field': 'tasks'},
    "invalid_deprecated_playbook": {'code': "PB104", 'ui_applicable': False, 'related_field': 'description'},
    "playbook_cant_have_deletecontext_all": {'code': "PB105", 'ui_applicable': True, 'related_field': 'tasks'},
    "using_instance_in_playbook": {'code': "PB106", 'ui_applicable': True, 'related_field': 'tasks'},
    "invalid_script_id": {'code': "PB107", 'ui_applicable': False, 'related_field': 'tasks'},
    "invalid_uuid": {'code': "PB108", 'ui_applicable': False, 'related_field': 'taskid'},
    "taskid_different_from_id": {'code': "PB109", 'ui_applicable': False, 'related_field': 'taskid'},
    "content_entity_version_not_match_playbook_version": {'code': "PB110", 'ui_applicable': False,
                                                          'related_field': 'toVersion'},
    "integration_version_not_match_playbook_version": {'code': "PB111", 'ui_applicable': False,
                                                       'related_field': 'toVersion'},
    "description_missing_in_beta_integration": {'code': "DS100", 'ui_applicable': False, 'related_field': ''},
    "no_beta_disclaimer_in_description": {'code': "DS101", 'ui_applicable': False, 'related_field': ''},
    "no_beta_disclaimer_in_yml": {'code': "DS102", 'ui_applicable': False, 'related_field': ''},
    "description_in_package_and_yml": {'code': "DS103", 'ui_applicable': False, 'related_field': ''},
    "no_description_file_warning": {'code': "DS104", 'ui_applicable': False, 'related_field': ''},
    "description_contains_contrib_details": {'code': "DS105", 'ui_applicable': False,
                                             'related_field': 'detaileddescription'},
    "invalid_description_name": {'code': "DS106", 'ui_applicable': False, 'related_field': ''},
    "invalid_incident_field_name": {'code': "IF100", 'ui_applicable': True, 'related_field': 'name'},
    "invalid_incident_field_content_key_value": {'code': "IF101", 'ui_applicable': False, 'related_field': 'content'},
    "invalid_incident_field_system_key_value": {'code': "IF102", 'ui_applicable': False, 'related_field': 'system'},
    "invalid_incident_field_type": {'code': "IF103", 'ui_applicable': True, 'related_field': 'type'},
    "invalid_incident_field_group_value": {'code': "IF104", 'ui_applicable': False, 'related_field': 'group'},
    "invalid_incident_field_cli_name_regex": {'code': "IF105", 'ui_applicable': False, 'related_field': 'cliName'},
    "invalid_incident_field_cli_name_value": {'code': "IF106", 'ui_applicable': True, 'related_field': 'cliName'},
    "incident_field_or_type_from_version_5": {'code': "IF107", 'ui_applicable': True, 'related_field': 'fromVersion'},
    "invalid_incident_field_or_type_from_version": {'code': "IF108", 'ui_applicable': False,
                                                    'related_field': 'fromVersion'},
    "new_incident_field_required": {'code': "IF109", 'ui_applicable': True, 'related_field': 'required'},
    "from_version_modified_after_rename": {'code': "IF110", 'ui_applicable': False, 'related_field': 'fromVersion'},
    "incident_field_type_change": {'code': "IF111", 'ui_applicable': False, 'related_field': 'type'},
    "indicator_field_type_grid_minimal_version": {'code': "IF112", 'ui_applicable': False,
                                                  'related_field': 'fromVersion'},
    "incident_type_integer_field": {'code': "IT100", 'ui_applicable': True, 'related_field': ''},
    "incident_type_invalid_playbook_id_field": {'code': "IT101", 'ui_applicable': False, 'related_field': 'playbookId'},
    "incident_type_auto_extract_fields_invalid": {'code': "IT102", 'ui_applicable': False,
                                                  'related_field': 'extractSettings'},
    "incident_type_invalid_auto_extract_mode": {'code': "IT103", 'ui_applicable': True, 'related_field': 'mode'},
    "incident_type_non_existent_playbook_id": {'code': "IT104", 'ui_applicable': False, 'related_field': ''},
    "pack_file_does_not_exist": {'code': "PA100", 'ui_applicable': False, 'related_field': ''},
    "cant_open_pack_file": {'code': "PA101", 'ui_applicable': False, 'related_field': ''},
    "cant_read_pack_file": {'code': "PA102", 'ui_applicable': False, 'related_field': ''},
    "cant_parse_pack_file_to_list": {'code': "PA103", 'ui_applicable': False, 'related_field': ''},
    "pack_file_bad_format": {'code': "PA104", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_empty": {'code': "PA105", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_should_be_dict": {'code': "PA106", 'ui_applicable': False, 'related_field': ''},
    "missing_field_iin_pack_metadata": {'code': "PA107", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_name_not_valid": {'code': "PA108", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_field_invalid": {'code': "PA109", 'ui_applicable': False, 'related_field': ''},
    "dependencies_field_should_be_dict": {'code': "PA110", 'ui_applicable': False, 'related_field': ''},
    "empty_field_in_pack_metadata": {'code': "PA111", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_isnt_json": {'code': "PA112", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_missing_url_and_email": {'code': "PA113", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_version_should_be_raised": {'code': "PA114", 'ui_applicable': False, 'related_field': ''},
    "pack_timestamp_field_not_in_iso_format": {'code': "PA115", 'ui_applicable': False, 'related_field': ''},
    "invalid_package_dependencies": {'code': "PA116", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_invalid_support_type": {'code': "PA117", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_certification_is_invalid": {'code': "PA118", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_non_approved_usecases": {'code': "PA119", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_non_approved_tags": {'code': "PA120", 'ui_applicable': False, 'related_field': ''},
    "pack_metadata_price_change": {'code': "PA121", 'ui_applicable': False, 'related_field': ''},
    "pack_name_already_exists": {'code': "PA122", 'ui_applicable': False, 'related_field': ''},
    "is_wrong_usage_of_usecase_tag": {'code': "PA123", 'ui_applicable': False, 'related_field': ''},
    "invalid_core_pack_dependencies": {'code': "PA124", 'ui_applicable': True, 'related_field': ''},
    "pack_name_is_not_in_xsoar_standards": {'code': "PA125", 'ui_applicable': False, 'related_field': ''},
    "readme_error": {'code': "RM100", 'ui_applicable': False, 'related_field': ''},
    "image_path_error": {'code': "RM101", 'ui_applicable': False, 'related_field': ''},
    "readme_missing_output_context": {'code': "RM102", 'ui_applicable': False, 'related_field': ''},
    "error_starting_mdx_server": {'code': "RM103", 'ui_applicable': False, 'related_field': ''},
    "empty_readme_error": {'code': "RM104", 'ui_applicable': False, 'related_field': ''},
    "readme_equal_description_error": {'code': "RM105", 'ui_applicable': False, 'related_field': ''},

    "wrong_version_reputations": {'code': "RP100", 'ui_applicable': False, 'related_field': 'version'},
    "reputation_expiration_should_be_numeric": {'code': "RP101", 'ui_applicable': True, 'related_field': 'expiration'},
    "reputation_id_and_details_not_equal": {'code': "RP102", 'ui_applicable': False, 'related_field': 'id'},
    "reputation_invalid_indicator_type_id": {'code': "RP103", 'ui_applicable': False, 'related_field': 'id'},
    "reputation_empty_required_fields": {'code': "RP104", 'ui_applicable': False, 'related_field': 'id'},
    "structure_doesnt_match_scheme": {'code': "ST100", 'ui_applicable': False, 'related_field': ''},
    "file_id_contains_slashes": {'code': "ST101", 'ui_applicable': False, 'related_field': 'id'},
    "file_id_changed": {'code': "ST102", 'ui_applicable': False, 'related_field': 'id'},
    "from_version_modified": {'code': "ST103", 'ui_applicable': False, 'related_field': 'fromversion'},
    "wrong_file_extension": {'code': "ST104", 'ui_applicable': False, 'related_field': ''},
    "invalid_file_path": {'code': "ST105", 'ui_applicable': False, 'related_field': ''},
    "invalid_package_structure": {'code': "ST106", 'ui_applicable': False, 'related_field': ''},
    "pykwalify_missing_parameter": {'code': "ST107", 'ui_applicable': False, 'related_field': ''},
    "pykwalify_field_undefined": {'code': "ST108", 'ui_applicable': False, 'related_field': ''},
    "pykwalify_missing_in_root": {'code': "ST109", 'ui_applicable': False, 'related_field': ''},
    "pykwalify_general_error": {'code': "ST110", 'ui_applicable': False, 'related_field': ''},
    "pykwalify_field_undefined_with_path": {'code': "ST111", 'ui_applicable': False, 'related_field': ''},
    "pykwalify_incorrect_enum": {'code': "ST112", 'ui_applicable': False, 'related_field': ''},
    "invalid_to_version_in_new_classifiers": {'code': "CL100", 'ui_applicable': False, 'related_field': 'toVersion'},
    "invalid_to_version_in_old_classifiers": {'code': "CL101", 'ui_applicable': False, 'related_field': 'toVersion'},
    "invalid_from_version_in_new_classifiers": {'code': "CL102", 'ui_applicable': False,
                                                'related_field': 'fromVersion'},
    "invalid_from_version_in_old_classifiers": {'code': "CL103", 'ui_applicable': False,
                                                'related_field': 'fromVersion'},
    "missing_from_version_in_new_classifiers": {'code': "CL104", 'ui_applicable': False,
                                                'related_field': 'fromVersion'},
    "missing_to_version_in_old_classifiers": {'code': "CL105", 'ui_applicable': False, 'related_field': 'toVersion'},
    "from_version_higher_to_version": {'code': "CL106", 'ui_applicable': False, 'related_field': 'fromVersion'},
    "invalid_type_in_new_classifiers": {'code': "CL107", 'ui_applicable': False, 'related_field': 'type'},
    "classifier_non_existent_incident_types": {'code': "CL108", 'ui_applicable': False,
                                               'related_field': 'incident_types'},
    "invalid_from_version_in_mapper": {'code': "MP100", 'ui_applicable': False, 'related_field': 'fromVersion'},
    "invalid_to_version_in_mapper": {'code': "MP101", 'ui_applicable': False, 'related_field': 'toVersion'},
    "invalid_mapper_file_name": {'code': "MP102", 'ui_applicable': False, 'related_field': ''},
    "missing_from_version_in_mapper": {'code': "MP103", 'ui_applicable': False, 'related_field': 'fromVersion'},
    "invalid_type_in_mapper": {'code': "MP104", 'ui_applicable': False, 'related_field': 'type'},
    "mapper_non_existent_incident_types": {'code': "MP105", 'ui_applicable': False, 'related_field': 'incident_types'},
    "invalid_incident_field_in_mapper": {'code': "MP106", 'ui_applicable': False, 'related_field': 'mapping'},
    "changed_incident_field_in_mapper": {'code': "MP107", 'ui_applicable': True, 'related_field': 'mapping'},
    "removed_incident_types": {'code': "MP108", 'ui_applicable': True, 'related_field': 'mapping'},
    "invalid_version_in_layout": {'code': "LO100", 'ui_applicable': False, 'related_field': 'version'},
    "invalid_version_in_layoutscontainer": {'code': "LO101", 'ui_applicable': False, 'related_field': 'version'},
    "invalid_file_path_layout": {'code': "LO102", 'ui_applicable': False, 'related_field': ''},
    "invalid_file_path_layoutscontainer": {'code': "LO103", 'ui_applicable': False, 'related_field': ''},
    "invalid_incident_field_in_layout": {'code': "LO104", 'ui_applicable': False, 'related_field': ''}
}


def get_all_error_codes() -> List:
    error_codes = []
    for error in ERROR_CODE:
        error_codes.append(ERROR_CODE[error].get('code'))

    return error_codes


def get_error_object(error_code: str) -> Dict:
    for error in ERROR_CODE:
        if error_code == ERROR_CODE[error].get('code'):
            return ERROR_CODE[error]
    return {}


def error_code_decorator(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs), ERROR_CODE[f.__name__].get('code')

    return wrapper


class Errors:
    BACKWARDS = "Possible backwards compatibility break"

    @staticmethod
    def suggest_fix(file_path: str, *args: Any, cmd: str = 'format') -> str:
        return f'To fix the problem, try running `demisto-sdk {cmd} -i {file_path} {" ".join(args)}`'

    @staticmethod
    @error_code_decorator
    def wrong_version(expected="-1"):
        return "The version for our files should always " \
               "be {}, please update the file.".format(expected)

    @staticmethod
    @error_code_decorator
    def id_should_equal_name(name, file_id):
        return "The File's name, which is: '{}', should be equal to its ID, which is: '{}'." \
               " please update the file.".format(name, file_id)

    @staticmethod
    @error_code_decorator
    def file_type_not_supported():
        return "The file type is not supported in validate command\n " \
               "validate' command supports: Integrations, Scripts, Playbooks, " \
               "Incident fields, Indicator fields, Images, Release notes, Layouts and Descriptions"

    @staticmethod
    @error_code_decorator
    def file_name_include_spaces_error(file_name):
        return "Please remove spaces from the file's name: '{}'.".format(file_name)

    @staticmethod
    @error_code_decorator
    def changes_may_fail_validation():
        return "Warning: The changes may fail validation once submitted via a " \
               "PR. To validate your changes, please make sure you have a git remote setup" \
               " and pointing to github.com/demisto/content.\nYou can do this by running " \
               "the following commands:\n\ngit remote add upstream https://github.com/" \
               "demisto/content.git\ngit fetch upstream\n\nMore info about configuring " \
               "a remote for a fork is available here: https://help.github.com/en/" \
               "github/collaborating-with-issues-and-pull-requests/configuring-a-remote-for-a-fork"

    @staticmethod
    @error_code_decorator
    def invalid_id_set():
        return "id_set.json file is invalid - delete it and re-run `validate`.\n" \
               "From content repository root run the following: `rm -rf Tests/id_set.json`\n" \
               "Then re-run the `validate` command."

    @staticmethod
    @error_code_decorator
    def no_minimal_fromversion_in_file(fromversion, oldest_supported_version):
        if fromversion == 'fromversion':
            return f"{fromversion} field is invalid.\nAdd `{fromversion}: " \
                   f"{oldest_supported_version}` to the file."
        else:
            return f'{fromversion} field is invalid.\nAdd `"{fromversion}": "{oldest_supported_version}"` ' \
                   f'to the file.'

    @staticmethod
    @error_code_decorator
    def running_on_master_with_git():
        return "Running on master branch while using git is ill advised." \
               "\nrun: 'git checkout -b NEW_BRANCH_NAME' and rerun the command."

    @staticmethod
    @error_code_decorator
    def folder_name_has_separators(entity_type, invalid_name, valid_name):
        return f"The {entity_type} folder name '{invalid_name}' should be named '{valid_name}' without any separator."

    @staticmethod
    @error_code_decorator
    def file_name_has_separators(entity_type, invalid_files, valid_files):
        return f"The {entity_type} files {invalid_files} should be named {valid_files} " \
               f"without any separator in the base name."

    @staticmethod
    @error_code_decorator
    def indicator_field_type_grid_minimal_version(fromversion):
        return f"The indicator field has a fromVersion of: {fromversion} but the minimal fromVersion is 5.5.0."

    @staticmethod
    @error_code_decorator
    def wrong_display_name(param_name, param_display):
        return 'The display name of the {} parameter should be \'{}\''.format(param_name, param_display)

    @staticmethod
    @error_code_decorator
    def wrong_default_parameter_not_empty(param_name, default_value):
        return 'The default value of the {} parameter should be {}'.format(param_name, default_value)

    @staticmethod
    @error_code_decorator
    def no_default_value_in_parameter(param_name):
        return 'The {} parameter should have a default value'.format(param_name)

    @staticmethod
    @error_code_decorator
    def wrong_required_value(param_name):
        return 'The required field of the {} parameter should be False'.format(param_name)

    @staticmethod
    @error_code_decorator
    def wrong_required_type(param_name):
        return 'The type field of the {} parameter should be 8'.format(param_name)

    @staticmethod
    @error_code_decorator
    def wrong_category(category):
        return "The category '{}' is not in the integration schemas, the valid options are:\n{}" \
            .format(category, '\n'.join(INTEGRATION_CATEGORIES))

    @staticmethod
    @error_code_decorator
    def wrong_default_argument(arg_name, command_name):
        return "The argument '{}' of the command '{}' is not configured as default" \
            .format(arg_name, command_name)

    @staticmethod
    @error_code_decorator
    def no_default_arg(command_name):
        return "Could not find default argument " \
               "{} in command {}".format(command_name, command_name)

    @staticmethod
    @error_code_decorator
    def missing_reputation(command_name, reputation_output, context_standard):
        return "The outputs of the reputation command {} aren't valid. The {} outputs is missing. " \
               "Fix according to context standard {} " \
            .format(command_name, reputation_output, context_standard)

    @staticmethod
    @error_code_decorator
    def wrong_subtype():
        return "The subtype for our yml files should be either python2 or python3, " \
               "please update the file."

    @classmethod
    @error_code_decorator
    def beta_in_id(cls):
        return cls.beta_in_str('id')

    @classmethod
    @error_code_decorator
    def beta_in_name(cls):
        return cls.beta_in_str('name')

    @staticmethod
    @error_code_decorator
    def beta_field_not_found():
        return "Beta integration yml file should have " \
               "the field \"beta: true\", but was not found in the file."

    @staticmethod
    @error_code_decorator
    def no_beta_in_display():
        return "Field 'display' in Beta integration yml file should include the string \"beta\", " \
               "but was not found in the file."

    @staticmethod
    @error_code_decorator
    def duplicate_arg_in_file(arg, command_name=None):
        err_msg = "The argument '{}' is duplicated".format(arg)
        if command_name:
            err_msg += " in '{}'.".format(command_name)
        err_msg += ", please remove one of its appearances."
        return err_msg

    @staticmethod
    @error_code_decorator
    def duplicate_param(param_name):
        return "The parameter '{}' of the " \
               "file is duplicated, please remove one of its appearances.".format(param_name)

    @staticmethod
    @error_code_decorator
    def invalid_context_output(command_name, output):
        return f'Invalid context output for command {command_name}. Output is {output}'

    @staticmethod
    @error_code_decorator
    def added_required_fields(field):
        return "You've added required, the field is '{}'".format(field)

    @staticmethod
    @error_code_decorator
    def removed_integration_parameters(field):
        return "You've removed integration parameters, the removed parameters are '{}'".format(field)

    @staticmethod
    @error_code_decorator
    def changed_integration_yml_fields(removed, changed):
        return f"You've made some changes to some fields in the yml file, \n" \
               f" the changed fields are: {changed} \n" \
               f"the removed fields are: {removed} "

    @staticmethod
    @error_code_decorator
    def incident_in_command_name_or_args(commands, args):
        return f"This is a core pack with an integration that contains the word incident in the following commands'" \
               f" name or argument:\ncommand's name: {commands} \ncommand's argument: {args}\n" \
               f"To fix the problem, remove the word incident, " \
               f"or add them to the whitelist named argsExceptionsList in:\n" \
               f"https://github.com/demisto/server/blob/57fbe417ae420c41ee12a9beb850ff4672209af8/services/" \
               f"servicemodule_test.go#L8273"

    @staticmethod
    @error_code_decorator
    def not_used_display_name(field_name):
        return "The display details for {} will not be used " \
               "due to the type of the parameter".format(field_name)

    @staticmethod
    @error_code_decorator
    def empty_display_configuration(field_name):
        return "No display details were entered for the field {}".format(field_name)

    @staticmethod
    @error_code_decorator
    def feed_wrong_from_version(given_fromversion, needed_from_version="5.5.0"):
        return "This is a feed and has wrong fromversion. got `{}` expected `{}`" \
            .format(given_fromversion, needed_from_version)

    @staticmethod
    @error_code_decorator
    def pwsh_wrong_version(given_fromversion, needed_from_version='5.5.0'):
        return f'Detected type: powershell and fromversion less than {needed_from_version}.' \
               f' Found version: {given_fromversion}'

    @staticmethod
    @error_code_decorator
    def parameter_missing_from_yml(name, correct_format):
        return f'A required parameter "{name}" is missing or malformed ' \
               f'in the YAML file.\nThe correct format of the parameter should ' \
               f'be as follows:\n{correct_format}'

    @staticmethod
    @error_code_decorator
    def parameter_missing_from_yml_not_community_contributor(name, correct_format):
        """
            This error is ignored if the contributor is community
        """
        return f'A required parameter "{name}" is missing or malformed ' \
               f'in the YAML file.\nThe correct format of the parameter should ' \
               f'be as follows:\n{correct_format}'

    @staticmethod
    @error_code_decorator
    def parameter_missing_for_feed(name, correct_format):
        return f'Feed Integration was detected A required ' \
               f'parameter "{name}" is missing or malformed in the YAML file.\n' \
               f'The correct format of the parameter should be as follows:\n{correct_format}'

    @staticmethod
    @error_code_decorator
    def missing_get_mapping_fields_command():
        return 'The command "get-mapping-fields" is missing from the YML file and is required as the ismappable ' \
               'field is set to true.'

    @staticmethod
    @error_code_decorator
    def readme_missing_output_context(command, context_paths):
        return f'The Following context paths for command {command} are found in YML file ' \
               f'but are missing from the README file: {context_paths}'

    @staticmethod
    @error_code_decorator
    def error_starting_mdx_server(line):
        return f'Failed starting mdx server. stdout: {line}.\n' \
               f'Try running the following command: `npm install`'

    @staticmethod
    @error_code_decorator
    def missing_output_context(command, context_paths):
        return f'The Following context paths for command {command} are found in the README file ' \
               f'but are missing from the YML file: {context_paths}'

    @staticmethod
    @error_code_decorator
    def integration_non_existent_classifier(integration_classifier):
        return f"The integration has a classifier {integration_classifier} which does not exist."

    @staticmethod
    @error_code_decorator
    def integration_non_existent_mapper(integration_mapper):
        return f"The integration has a mapper {integration_mapper} which does not exist."

    @staticmethod
    @error_code_decorator
    def multiple_default_arg(command_name, default_args):
        return f"The integration command: {command_name} has multiple default arguments: {default_args}."

    @staticmethod
    @error_code_decorator
    def invalid_integration_parameters_display_name(invalid_display_names):
        return f"The integration display names: {invalid_display_names} are invalid, " \
               "Integration parameters display name should be capitalized and spaced using whitespaces " \
               "and not underscores ( _ )."

    @staticmethod
    @error_code_decorator
    def is_valid_integration_file_path_in_folder(integration_file):
        return f"The integration file name: {integration_file} is invalid, " \
               f"The integration file name should be the same as the name of the folder that contains it."

    @staticmethod
    @error_code_decorator
    def is_valid_integration_file_path_in_integrations_folder(integration_file):
        return f"The integration file name: {integration_file} is invalid, " \
               f"The integration file name should start with 'integration-'."

    @staticmethod
    @error_code_decorator
    def invalid_v2_integration_name():
        return "The display name of this v2 integration is incorrect , should be **name** v2.\n" \
               "e.g: Kenna v2, Jira v2"

    @staticmethod
    @error_code_decorator
    def found_hidden_param(parameter_name):
        return f"Parameter: \"{parameter_name}\" can't be hidden. Please remove this field."

    @staticmethod
    @error_code_decorator
    def invalid_deprecated_integration_display_name():
        return 'The display_name (display) of all deprecated integrations should end with (Deprecated)".'

    @staticmethod
    @error_code_decorator
    def invalid_deprecated_integration_description():
        return 'The description of all deprecated integrations should follow one of the formats:' \
               '1. "Deprecated. Use <INTEGRATION_DISPLAY_NAME> instead."' \
               '2. "Deprecated. <REASON> No available replacement."'

    @staticmethod
    @error_code_decorator
    def invalid_v2_script_name():
        return "The name of this v2 script is incorrect , should be **name**V2." \
               " e.g: DBotTrainTextClassifierV2"

    @staticmethod
    @error_code_decorator
    def invalid_deprecated_script():
        return "Every deprecated script's comment has to start with 'Deprecated.'"

    @staticmethod
    @error_code_decorator
    def dbot_invalid_output(command_name, missing_outputs, context_standard):
        return "The DBotScore outputs of the reputation command {} aren't valid. Missing: {}. " \
               "Fix according to context standard {} ".format(command_name, missing_outputs,
                                                              context_standard)

    @staticmethod
    @error_code_decorator
    def dbot_invalid_description(command_name, missing_descriptions, context_standard):
        return "The DBotScore description of the reputation command {} aren't valid. Missing: {}. " \
               "Fix according to context standard {} " \
            .format(command_name, missing_descriptions, context_standard)

    @classmethod
    @error_code_decorator
    def breaking_backwards_subtype(cls):
        return "{}, You've changed the subtype, please undo.".format(cls.BACKWARDS)

    @classmethod
    @error_code_decorator
    def breaking_backwards_context(cls):
        return "{}, You've changed the context in the file," \
               " please undo.".format(cls.BACKWARDS)

    @classmethod
    @error_code_decorator
    def breaking_backwards_command(cls, old_command):
        return "{}, You've changed the context in the file,please " \
               "undo. the command is:\n{}".format(cls.BACKWARDS, old_command)

    @classmethod
    @error_code_decorator
    def breaking_backwards_arg_changed(cls):
        return "{}, You've changed the name of an arg in " \
               "the file, please undo.".format(cls.BACKWARDS)

    @classmethod
    @error_code_decorator
    def breaking_backwards_command_arg_changed(cls, command):
        return "{}, You've changed the name of a command or its arg in" \
               " the file, please undo, the command was:\n{}".format(cls.BACKWARDS, command)

    @staticmethod
    @error_code_decorator
    def default_docker_error():
        return 'The current docker image in the yml file is the default one: demisto/python:1.3-alpine,\n' \
               'Please create or use another docker image'

    @staticmethod
    @error_code_decorator
    def latest_docker_error(docker_image_tag, docker_image_name):
        return f'"latest" tag is not allowed,\n' \
               f'Please create or update to an updated versioned image\n' \
               f'You can check for the most updated version of {docker_image_tag} ' \
               f'here: https://hub.docker.com/r/{docker_image_name}/tags'

    @staticmethod
    @error_code_decorator
    def not_demisto_docker():
        return 'docker image must be a demisto docker image. When the docker image is ready, ' \
               'please rename it to: demisto/<image>:<tag>'

    @staticmethod
    @error_code_decorator
    def docker_tag_not_fetched(docker_image_name):
        return f'Failed getting tag for: {docker_image_name}. Please check it exists and of demisto format.'

    @staticmethod
    @error_code_decorator
    def no_docker_tag(docker_image):
        return f'{docker_image} - The docker image in your integration/script does not have a tag.' \
               f' Please create or update to an updated versioned image\n'

    @staticmethod
    @error_code_decorator
    def non_existing_docker(docker_image):
        return f'{docker_image} - Could not find the docker image. Check if it exists in ' \
               f'DockerHub: https://hub.docker.com/u/demisto/.'

    @staticmethod
    @error_code_decorator
    def docker_not_formatted_correctly(docker_image):
        return f'The docker image: {docker_image} is not of format - demisto/image_name:X.X'

    @staticmethod
    def suggest_docker_fix(docker_image_name: str, file_path: str) -> str:
        return f'You can check for the most updated version of {docker_image_name} ' \
               f'here: https://hub.docker.com/r/{docker_image_name}/tags\n' \
               f'To update the docker image run: demisto-sdk format -ud -i {file_path}\n'

    @staticmethod
    @error_code_decorator
    def docker_not_on_the_latest_tag(docker_image_tag, docker_image_latest_tag, docker_image_name, file_path) -> str:
        return f'The docker image tag is not the latest numeric tag, please update it.\n' \
               f'The docker image tag in the yml file is: {docker_image_tag}\n' \
               f'The latest docker image tag in docker hub is: {docker_image_latest_tag}\n'

    @staticmethod
    @error_code_decorator
    def id_set_conflicts():
        return "You probably merged from master and your id_set.json has " \
               "conflicts. Run `demisto-sdk create-id-set`, it should reindex your id_set.json"

    @staticmethod
    @error_code_decorator
    def duplicated_id(obj_id):
        return f"The ID {obj_id} already exists, please update the file or update the " \
               f"id_set.json toversion field of this id to match the old occurrence of this id"

    @staticmethod
    @error_code_decorator
    def no_id_set_file():
        return "Unable to find id_set.json file in path - rerun the command with --create-id-set flag"

    @staticmethod
    @error_code_decorator
    def remove_field_from_dashboard(field):
        return f'the field {field} needs to be removed.'

    @staticmethod
    @error_code_decorator
    def include_field_in_dashboard(field):
        return f'The field {field} needs to be included. Please add it.'

    @staticmethod
    @error_code_decorator
    def remove_field_from_widget(field, widget):
        return f'The field {field} needs to be removed from the widget: {widget}.'

    @staticmethod
    @error_code_decorator
    def include_field_in_widget(field, widget_name):
        return f'The field {field} needs to be included in the widget: {widget_name}. Please add it.'

    @staticmethod
    @error_code_decorator
    def no_image_given():
        return "You've created/modified a yml or package but failed to provide an image as " \
               "a .png file for it, please add an image in order to proceed."

    @staticmethod
    @error_code_decorator
    def image_too_large():
        return "Too large logo, please update the logo to be under 10kB"

    @staticmethod
    @error_code_decorator
    def image_in_package_and_yml():
        return "Image in both yml and package, remove the 'image' " \
               "key from the yml file"

    @staticmethod
    @error_code_decorator
    def not_an_image_file():
        return "This isn't an image file or unified integration file."

    @staticmethod
    @error_code_decorator
    def no_image_field_in_yml():
        return "This is a yml file but has no image field."

    @staticmethod
    @error_code_decorator
    def image_field_not_in_base64():
        return "The image field isn't in base64 encoding."

    @staticmethod
    @error_code_decorator
    def default_image_error():
        return "This is the default image, please change to the integration image."

    @staticmethod
    @error_code_decorator
    def invalid_image_name():
        return "The image's file name is invalid - " \
               "make sure the name looks like the following: <integration_name>_image.png"

    @staticmethod
    @error_code_decorator
    def description_missing_from_conf_json(problematic_instances):
        return "Those instances don't have description:\n{}".format('\n'.join(problematic_instances))

    @staticmethod
    @error_code_decorator
    def test_not_in_conf_json(file_id):
        return "You've failed to add the {file_id} to conf.json\n" \
               "see here: https://xsoar.pan.dev/docs/integrations/test-playbooks#adding-tests-to-confjson"

    @staticmethod
    @error_code_decorator
    def integration_not_registered(file_path, missing_test_playbook_configurations, no_tests_key):
        return f'The following integration is not registered in {CONF_PATH} file.\n' \
               f'Please add:\n{missing_test_playbook_configurations}\nto {CONF_PATH} ' \
               f'path under \'tests\' key.\n' \
               f'If you don\'t want to add a test playbook for this integration, please add: \n{no_tests_key}to the ' \
               f'file {file_path} or run \'demisto-sdk format -i {file_path}\''

    @staticmethod
    @error_code_decorator
    def no_test_playbook(file_path, file_type):
        return f'You don\'t have a TestPlaybook for {file_type} {file_path}. ' \
               f'If you have a TestPlaybook for this {file_type}, ' \
               f'please edit the yml file and add the TestPlaybook under the \'tests\' key. ' \
               f'If you don\'t want to create a TestPlaybook for this {file_type}, ' \
               f'edit the yml file and add  \ntests:\n -  No tests\n lines to it or ' \
               f'run \'demisto-sdk format -i {file_path}\''

    @staticmethod
    @error_code_decorator
    def test_playbook_not_configured(content_item_id, missing_test_playbook_configurations,
                                     missing_integration_configurations):
        return f'The TestPlaybook {content_item_id} is not registered in {CONF_PATH} file.\n ' \
               f'Please add\n{missing_test_playbook_configurations}\n ' \
               f'or if this test playbook is for an integration\n{missing_integration_configurations}\n ' \
               f'to {CONF_PATH} path under \'tests\' key.'

    @staticmethod
    @error_code_decorator
    def missing_release_notes(rn_path):
        return 'Missing release notes, Please add it under {}'.format(rn_path)

    @staticmethod
    @error_code_decorator
    def no_new_release_notes(release_notes_path):
        return F'No new comment has been added in the release notes file: {release_notes_path}'

    @staticmethod
    @error_code_decorator
    def release_notes_not_formatted_correctly(link_to_rn_standard):
        return F'Not formatted according to ' \
               F'release notes standards.\nFix according to {link_to_rn_standard}'

    @staticmethod
    @error_code_decorator
    def release_notes_not_finished():
        return "Please finish filling out the release notes. For common troubleshooting steps, please " \
               "review the documentation found here: " \
               "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"

    @staticmethod
    @error_code_decorator
    def release_notes_file_empty():
        return "Your release notes file is empty, please complete it\nHaving empty release notes " \
               "looks bad in the product UI.\nIf the change you made was minor, please use " \
               "\"Maintenance and stability enhancements.\" for general changes, or use " \
               "\"Documentation and metadata improvements.\" for changes to documentation."

    @staticmethod
    @error_code_decorator
    def multiple_release_notes_files():
        return "More than one release notes file has been found." \
               "Only one release note file is permitted per release. Please delete the extra release notes."

    @staticmethod
    @error_code_decorator
    def missing_release_notes_for_pack(pack):
        return f"Release notes were not found. Please run `demisto-sdk " \
               f"update-release-notes -i Packs/{pack} -u (major|minor|revision)` to " \
               f"generate release notes according to the new standard. You can refer to the documentation " \
               f"found here: https://xsoar.pan.dev/docs/integrations/changelog for more information."

    @staticmethod
    @error_code_decorator
    def missing_release_notes_entry(file_type, pack_name, entity_name):
        return f"No release note entry was found for the {file_type.value.lower()} \"{entity_name}\" in the " \
               f"{pack_name} pack. Please rerun the update-release-notes command without -u to " \
               f"generate an updated template. If you are trying to exclude an item from the release " \
               f"notes, please refer to the documentation found here - " \
               f"https://xsoar.pan.dev/docs/integrations/changelog#excluding-items"

    @staticmethod
    @error_code_decorator
    def added_release_notes_for_new_pack(pack_name):
        return f"ReleaseNotes were added for the newly created pack \"{pack_name}\" - remove them"

    @staticmethod
    @error_code_decorator
    def modified_existing_release_notes(pack_name):
        return f"Modified existing release notes for \"{pack_name}\" - revert the change and add new release notes " \
               f"if needed by running:\n`demisto-sdk update-release-notes -i Packs/{pack_name} -u " \
               f"(major|minor|revision)`\n" \
               f"You can refer to the documentation found here: " \
               f"https://xsoar.pan.dev/docs/integrations/changelog for more information."

    @staticmethod
    @error_code_decorator
    def playbook_cant_have_rolename():
        return "Playbook can not have a rolename."

    @staticmethod
    @error_code_decorator
    def using_instance_in_playbook():
        return "Playbook should not use specific instance."

    @staticmethod
    @error_code_decorator
    def playbook_unreachable_condition(task_id, next_task_branch):
        return f'Playbook conditional task with id:{task_id} has task with unreachable ' \
               f'next task condition "{next_task_branch}". Please remove this task or add ' \
               f'this condition to condition task with id:{task_id}.'

    @staticmethod
    @error_code_decorator
    def playbook_unhandled_condition(task_id, task_condition_labels):
        return f'Playbook conditional task with id:{task_id} has an unhandled ' \
               f'condition: {",".join(map(lambda x: f"{str(x)}", task_condition_labels))}'

    @staticmethod
    @error_code_decorator
    def playbook_unconnected_tasks(orphan_tasks):
        return f'The following tasks ids have no previous tasks: {orphan_tasks}'

    @staticmethod
    @error_code_decorator
    def playbook_cant_have_deletecontext_all():
        return 'Playbook can not have DeleteContext script with arg all set to yes.'

    @staticmethod
    @error_code_decorator
    def invalid_deprecated_playbook():
        return 'The playbook description has to start with "Deprecated."'

    @staticmethod
    @error_code_decorator
    def invalid_script_id(script_entry_to_check, pb_task):
        return f"in task {pb_task} the script {script_entry_to_check} was not found in the id_set.json file. " \
               f"Please make sure:\n" \
               f"1 - The right script id is set and the spelling is correct.\n" \
               f"2 - The id_set.json file is up to date. Delete the file by running: rm -rf Tests/id_set.json and" \
               f" rerun the command."

    @staticmethod
    @error_code_decorator
    def content_entity_version_not_match_playbook_version(main_playbook, entities_names, main_playbook_version):
        return f"Playbook {main_playbook} with version {main_playbook_version} uses {entities_names} " \
               f"with a version that does not match the main playbook version. The from version of" \
               f" {entities_names} should be at least {main_playbook_version}."

    @staticmethod
    @error_code_decorator
    def integration_version_not_match_playbook_version(main_playbook, command, main_playbook_version):
        return f"Playbook {main_playbook} with version {main_playbook_version} uses the command {command} " \
               f"that not implemented in integration that match the main playbook version. This command should be " \
               f"implemented in an integration with a from version of at least {main_playbook_version}."

    @staticmethod
    @error_code_decorator
    def invalid_command_name_in_script(script_name, command):
        return f"in script {script_name} the command {command} has an invalid name. " \
               f"Please make sure:\n" \
               f"1 - The right command name is set and the spelling is correct." \
               f" Do not use 'dev' in it or suffix it with 'copy'\n" \
               f"2 - The id_set.json file is up to date. Delete the file by running: rm -rf Tests/id_set.json and" \
               f" rerun the command."

    @staticmethod
    @error_code_decorator
    def is_valid_script_file_path_in_folder(script_file):
        return f"The script file name: {script_file} is invalid, " \
               f"The script file name should be the same as the name of the folder that contains it."

    @staticmethod
    @error_code_decorator
    def is_valid_script_file_path_in_scripts_folder(script_file):
        return f"The script file name: {script_file} is invalid, " \
               f"The script file name should start with 'script-'."

    @staticmethod
    @error_code_decorator
    def incident_in_script_arg(arguments):
        return f"The script is part of a core pack. Therefore, the use of the word `incident` in argument names is" \
               f" forbidden. problematic argument" \
               f" names:\n {arguments}. \n, To fix the problem, remove the word incident, " \
               f"or add the argument name to the allowlist named argsExceptionsList in:\n" \
               f"https://github.com/demisto/server/blob/57fbe417ae420c41ee12a9beb850ff4672209af8/services/" \
               f"servicemodule_test.go#L8273"

    @staticmethod
    @error_code_decorator
    def description_missing_in_beta_integration():
        return f"No detailed description file was found in the package. Please add one, " \
               f"and make sure it includes the beta disclaimer note." \
               f"Add the following to the detailed description:\n{BETA_INTEGRATION_DISCLAIMER}"

    @staticmethod
    @error_code_decorator
    def description_contains_contrib_details():
        return "Description file contains contribution/partner details that will be generated automatically " \
               "when the upload command is performed.\nDelete any details related to contribution/partner "

    @staticmethod
    @error_code_decorator
    def invalid_description_name():
        return "The description's file name is invalid - " \
               "make sure the name looks like the following: <integration_name>_description.md"

    @staticmethod
    @error_code_decorator
    def no_beta_disclaimer_in_description():
        return f"The detailed description in beta integration package " \
               f"does not contain the beta disclaimer note. Add the following to the description:\n" \
               f"{BETA_INTEGRATION_DISCLAIMER}"

    @staticmethod
    @error_code_decorator
    def no_beta_disclaimer_in_yml():
        return f"The detailed description field in beta integration " \
               f"does not contain the beta disclaimer note. Add the following to the detailed description:\n" \
               f"{BETA_INTEGRATION_DISCLAIMER}"

    @staticmethod
    @error_code_decorator
    def description_in_package_and_yml():
        return "A description was found both in the " \
               "package and in the yml, please update the package."

    @staticmethod
    @error_code_decorator
    def no_description_file_warning():
        return "No detailed description file was found. Consider adding one."

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_name(word):
        return f"The word {word} cannot be used as a name, please update the file."

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_content_key_value(content_value):
        return f"The content key must be set to {content_value}."

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_system_key_value(system_value):
        return f"The system key must be set to {system_value}"

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_type(file_type, TypeFields):
        return f"Type: `{file_type}` is not one of available types.\n" \
               f"available types: {[value.value for value in TypeFields]}"

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_group_value(group):
        return f"Group {group} is not a group field."

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_cli_name_regex(cli_regex):
        return f"Field `cliName` contains non-alphanumeric letters. " \
               f"must match regex: {cli_regex}"

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_cli_name_value(cli_name):
        return f"cliName field can not be {cli_name} as it's a builtin key."

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_or_type_from_version():
        return '"fromVersion" has an invalid value.'

    @staticmethod
    @error_code_decorator
    def new_incident_field_required():
        return 'New incident fields can not be required. change to:\nrequired: false.'

    @staticmethod
    @error_code_decorator
    def from_version_modified_after_rename():
        return "fromversion might have been modified, please make sure it hasn't changed."

    @staticmethod
    @error_code_decorator
    def incident_field_type_change():
        return 'Changing incident field type is not allowed.'

    @staticmethod
    @error_code_decorator
    def incident_type_integer_field(field):
        return f'The field {field} needs to be a positive integer. Please add it.\n'

    @staticmethod
    @error_code_decorator
    def incident_type_invalid_playbook_id_field():
        return 'The "playbookId" field is not valid - please enter a non-UUID playbook ID.'

    @staticmethod
    @error_code_decorator
    def incident_type_auto_extract_fields_invalid(incident_fields):
        return f"The following incident fields are not formatted correctly under " \
               f"`fieldCliNameToExtractSettings`: {incident_fields}\n" \
               f"Please format them in one of the following ways:\n" \
               f"1. To extract all indicators from the field: \n" \
               f"isExtractingAllIndicatorTypes: true, extractAsIsIndicatorTypeId: \"\", " \
               f"extractIndicatorTypesIDs: []\n" \
               f"2. To extract the incident field to a specific indicator without using regex: \n" \
               f"isExtractingAllIndicatorTypes: false, extractAsIsIndicatorTypeId: \"<INDICATOR_TYPE>\", " \
               f"extractIndicatorTypesIDs: []\n" \
               f"3. To extract indicators from the field using regex: \n" \
               f"isExtractingAllIndicatorTypes: false, extractAsIsIndicatorTypeId: \"\", " \
               f"extractIndicatorTypesIDs: [\"<INDICATOR_TYPE1>\", \"<INDICATOR_TYPE2>\"]"

    @staticmethod
    @error_code_decorator
    def incident_type_invalid_auto_extract_mode():
        return 'The `mode` field under `extractSettings` should be one of the following:\n' \
               ' - \"All\" - To extract all indicator types regardless of auto-extraction settings.\n' \
               ' - \"Specific\" - To extract only the specific indicator types set in the auto-extraction settings.'

    @staticmethod
    @error_code_decorator
    def incident_type_non_existent_playbook_id(incident_type, playbook):
        return f"in incident type {incident_type} the playbook {playbook} was not found in the id_set.json file. " \
               f"Please make sure:\n" \
               f"1 - The right playbook name is set and the spelling is correct.\n" \
               f"2 - The id_set.json file is up to date. Delete the file by running: rm -rf Tests/id_set.json and" \
               f" rerun the command."

    @staticmethod
    @error_code_decorator
    def pack_file_does_not_exist(file_name):
        return f'"{file_name}" file does not exist, create one in the root of the pack'

    @staticmethod
    @error_code_decorator
    def cant_open_pack_file(file_name):
        return f'Could not open "{file_name}" file'

    @staticmethod
    @error_code_decorator
    def cant_read_pack_file(file_name):
        return f'Could not read the contents of "{file_name}" file'

    @staticmethod
    @error_code_decorator
    def cant_parse_pack_file_to_list(file_name):
        return f'Could not parse the contents of "{file_name}" file into a list'

    @staticmethod
    @error_code_decorator
    def pack_file_bad_format(file_name):
        return f'Detected invalid {file_name} file'

    @staticmethod
    @error_code_decorator
    def pack_metadata_empty():
        return 'Pack metadata is empty.'

    @staticmethod
    @error_code_decorator
    def pack_metadata_should_be_dict(pack_meta_file):
        return f'Pack metadata {pack_meta_file} should be a dictionary.'

    @staticmethod
    @error_code_decorator
    def pack_metadata_certification_is_invalid(pack_meta_file):
        return f'Pack metadata {pack_meta_file} - certification field should be \'certified\' or \'verified\'.'

    @staticmethod
    @error_code_decorator
    def missing_field_iin_pack_metadata(pack_meta_file, missing_fields):
        return f'{pack_meta_file} - Missing fields in the pack metadata: {missing_fields}'

    @staticmethod
    @error_code_decorator
    def pack_metadata_name_not_valid():
        return f'Pack metadata {PACK_METADATA_NAME} field is not valid. Please fill valid pack name.'

    @staticmethod
    @error_code_decorator
    def pack_metadata_field_invalid():
        return f'Pack metadata {PACK_METADATA_DESC} field is not valid. Please fill valid pack description.'

    @staticmethod
    @error_code_decorator
    def dependencies_field_should_be_dict(pack_meta_file):
        return f'{pack_meta_file} - The dependencies field in the pack must be a dictionary.'

    @staticmethod
    @error_code_decorator
    def empty_field_in_pack_metadata(pack_meta_file, list_field):
        return f'{pack_meta_file} - Empty value in the {list_field} field.'

    @staticmethod
    @error_code_decorator
    def pack_metadata_isnt_json(pack_meta_file):
        return f'Could not parse {pack_meta_file} file contents to json format'

    @staticmethod
    @error_code_decorator
    def pack_metadata_missing_url_and_email():
        return 'Contributed packs must include email or url.'

    @staticmethod
    @error_code_decorator
    def pack_metadata_invalid_support_type(pack_meta_file):
        return 'Support field should be one of the following: xsoar, partner, developer or community.'

    @staticmethod
    @error_code_decorator
    def pack_metadata_version_should_be_raised(pack, old_version):
        return f"The pack version (currently: {old_version}) needs to be raised - " \
               f"make sure you are merged from master and " \
               f"update the \"currentVersion\" field in the " \
               f"pack_metadata.json or in case release notes are required run:\n" \
               f"`demisto-sdk update-release-notes -i Packs/{pack} -u (major|minor|revision)` to " \
               f"generate them according to the new standard."

    @staticmethod
    @error_code_decorator
    def pack_metadata_non_approved_usecases(non_approved_usecases: set) -> str:
        return f'The pack metadata contains non approved usecases: {", ".join(non_approved_usecases)}'

    @staticmethod
    @error_code_decorator
    def pack_metadata_non_approved_tags(non_approved_tags: set) -> str:
        return f'The pack metadata contains non approved tags: {", ".join(non_approved_tags)}'

    @staticmethod
    @error_code_decorator
    def pack_metadata_price_change(old_price, new_price) -> str:
        return f"The pack price was changed from {old_price} to {new_price} - revert the change"

    @staticmethod
    @error_code_decorator
    def pack_name_already_exists(new_pack_name) -> str:
        return f"A pack named: {new_pack_name} already exists in content repository, " \
               f"change the pack's name in the metadata file."

    @staticmethod
    @error_code_decorator
    def is_wrong_usage_of_usecase_tag():
        return "pack_metadata.json file contains the Use Case tag, without having any PB, incidents Types or Layouts"

    @staticmethod
    @error_code_decorator
    def pack_name_is_not_in_xsoar_standards(reason):
        if reason == "short":
            return f'Pack metadata {PACK_METADATA_NAME} field is not valid. The pack name must be at least 3 ' \
                   f'characters long.'
        if reason == "capital":
            return f'Pack metadata {PACK_METADATA_NAME} field is not valid. The pack name must start with a capital ' \
                   f'letter.'
        if reason == "wrong_word":
            return f'Pack metadata {PACK_METADATA_NAME} field is not valid. The pack name must not contain the words: ' \
                   f'["Pack", "Playbook", "Integration", "Script"]'

    @staticmethod
    @error_code_decorator
    def pack_timestamp_field_not_in_iso_format(field_name, value, changed_value):
        return f"The field \"{field_name}\" should be in the following format: YYYY-MM-DDThh:mm:ssZ, found {value}.\n" \
               f"Suggested change: {changed_value}"

    @staticmethod
    @error_code_decorator
    def readme_error(stderr):
        return f'Failed verifying README.md Error Message is: {stderr}'

    @staticmethod
    @error_code_decorator
    def empty_readme_error():
        return 'README.md is empty'

    @staticmethod
    @error_code_decorator
    def readme_equal_description_error():
        return 'README.md content is equal to pack description. ' \
               'Please remove the duplicate description from README.md file.'

    @staticmethod
    @error_code_decorator
    def image_path_error(path, alternative_path):
        return f'Detected following image url:\n{path}\n' \
               f'Which is not the raw link. You probably want to use the following raw image url:\n{alternative_path}'

    @staticmethod
    @error_code_decorator
    def wrong_version_reputations(object_id, version):
        return "Reputation object with id {} must have version {}".format(object_id, version)

    @staticmethod
    @error_code_decorator
    def reputation_expiration_should_be_numeric():
        return 'Expiration field should have a positive numeric value.'

    @staticmethod
    @error_code_decorator
    def reputation_id_and_details_not_equal():
        return 'id and details fields are not equal.'

    @staticmethod
    @error_code_decorator
    def reputation_invalid_indicator_type_id():
        return 'Indicator type "id" field can not include spaces or special characters.'

    @staticmethod
    @error_code_decorator
    def reputation_empty_required_fields():
        return 'id and details fields can not be empty.'

    @staticmethod
    @error_code_decorator
    def structure_doesnt_match_scheme(pretty_formatted_string_of_regexes):
        return f"The file does not match any scheme we have, please refer to the following list " \
               f"for the various file name options we have in our repo {pretty_formatted_string_of_regexes}"

    @staticmethod
    @error_code_decorator
    def file_id_contains_slashes():
        return "File's ID contains slashes - please remove."

    @staticmethod
    @error_code_decorator
    def file_id_changed(old_version_id, new_file_id):
        return f"The file id has changed from {old_version_id} to {new_file_id}"

    @staticmethod
    @error_code_decorator
    def from_version_modified():
        return "You've added fromversion to an existing " \
               "file in the system, this is not allowed, please undo."

    @staticmethod
    @error_code_decorator
    def wrong_file_extension(file_extension, accepted_extensions):
        return "File extension {} is not valid. accepted {}".format(file_extension, accepted_extensions)

    @staticmethod
    @error_code_decorator
    def invalid_file_path():
        return "Found incompatible file path."

    @staticmethod
    @error_code_decorator
    def invalid_package_structure(invalid_files):
        return 'You should update the following file to the package format, for further details please visit ' \
               'https://xsoar.pan.dev/docs/integrations/package-dir.'

    @staticmethod
    @error_code_decorator
    def invalid_package_dependencies(pack_name):
        return f'{pack_name} depends on NonSupported / DeprecatedContent packs.'

    @staticmethod
    @error_code_decorator
    def invalid_core_pack_dependencies(core_pack, dependencies_packs):
        return f'The core pack {core_pack} cannot depend on non-core packs: {dependencies_packs} - ' \
               f'revert this change.'

    @staticmethod
    @error_code_decorator
    def pykwalify_missing_parameter(key_from_error, path):
        return f'Missing the field "{key_from_error}" in Path: {path}'

    @staticmethod
    @error_code_decorator
    def pykwalify_field_undefined(key_from_error):
        return f'The field "{key_from_error}" was not defined in the scheme'

    @staticmethod
    @error_code_decorator
    def pykwalify_field_undefined_with_path(key_from_error, path):
        return f'The field "{key_from_error}" in path {path} was not defined in the scheme'

    @staticmethod
    @error_code_decorator
    def pykwalify_missing_in_root(key_from_error):
        return f'Missing the field "{key_from_error}" in root'

    @staticmethod
    @error_code_decorator
    def pykwalify_general_error(error):
        return f'in {error}'

    @staticmethod
    @error_code_decorator
    def pykwalify_incorrect_enum(path_to_wrong_enum, wrong_enum, enum_values):
        return f'The value "{wrong_enum}" in {path_to_wrong_enum} is invalid - legal values include: {enum_values}'

    @staticmethod
    @error_code_decorator
    def invalid_version_in_layout(version_field):
        return f'{version_field} field in layout needs to be lower than 6.0.0'

    @staticmethod
    @error_code_decorator
    def invalid_version_in_layoutscontainer(version_field):
        return f'{version_field} field in layoutscontainer needs to be higher or equal to 6.0.0'

    @staticmethod
    @error_code_decorator
    def invalid_file_path_layout(file_name):
        return f'Invalid file name - {file_name}. layout file name should start with "layout-" prefix.'

    @staticmethod
    @error_code_decorator
    def invalid_file_path_layoutscontainer(file_name):
        return f'Invalid file name - {file_name}. layoutscontainer file name should start with ' \
               '"layoutscontainer-" prefix.'

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_in_layout(invalid_inc_fields_list):
        return f"The layout contains incident fields that do not exist in the content: {invalid_inc_fields_list}.\n" \
               "Please make sure:\n" \
               "1 - The right incident field is set and the spelling is correct.\n" \
               "2 - The id_set.json file is up to date. Delete the file by running: rm -rf Tests/id_set.json and" \
               " rerun the command."

    @staticmethod
    @error_code_decorator
    def invalid_to_version_in_new_classifiers():
        return 'toVersion field in new classifiers needs to be higher than 6.0.0'

    @staticmethod
    @error_code_decorator
    def invalid_to_version_in_old_classifiers():
        return 'toVersion field in old classifiers needs to be lower than 6.0.0'

    @staticmethod
    @error_code_decorator
    def invalid_from_version_in_new_classifiers():
        return 'fromVersion field in new classifiers needs to be higher or equal to 6.0.0'

    @staticmethod
    @error_code_decorator
    def invalid_from_version_in_old_classifiers():
        return 'fromVersion field in old classifiers needs to be lower than 6.0.0'

    @staticmethod
    @error_code_decorator
    def missing_from_version_in_new_classifiers():
        return 'Must have fromVersion field in new classifiers'

    @staticmethod
    @error_code_decorator
    def missing_to_version_in_old_classifiers():
        return 'Must have toVersion field in old classifiers'

    @staticmethod
    @error_code_decorator
    def from_version_higher_to_version():
        return 'fromVersion field can not be higher than toVersion field'

    @staticmethod
    @error_code_decorator
    def invalid_type_in_new_classifiers():
        return 'Classifiers type must be classification'

    @staticmethod
    @error_code_decorator
    def classifier_non_existent_incident_types(incident_types):
        return f"The Classifiers related incident types: {incident_types} where not found."

    @staticmethod
    @error_code_decorator
    def invalid_from_version_in_mapper():
        return 'fromVersion field in mapper needs to be higher or equal to 6.0.0'

    @staticmethod
    @error_code_decorator
    def invalid_to_version_in_mapper():
        return 'toVersion field in mapper needs to be higher than 6.0.0'

    @staticmethod
    @error_code_decorator
    def invalid_mapper_file_name():
        return 'Invalid file name for mapper. Need to change to classifier-mapper-NAME.json'

    @staticmethod
    @error_code_decorator
    def missing_from_version_in_mapper():
        return 'Must have fromVersion field in mapper'

    @staticmethod
    @error_code_decorator
    def invalid_type_in_mapper():
        return 'Mappers type must be mapping-incoming or mapping-outgoing'

    @staticmethod
    @error_code_decorator
    def mapper_non_existent_incident_types(incident_types):
        return f"The Mapper related incident types: {incident_types} where not found."

    @staticmethod
    @error_code_decorator
    def invalid_incident_field_in_mapper(invalid_inc_fields_list):
        return f"Your mapper contains incident fields that do not exist in the content: {invalid_inc_fields_list}.\n" \
               "Please make sure:\n" \
               "1 - The right incident field is set and the spelling is correct.\n" \
               "2 - The id_set.json file is up to date. Delete the file by running: rm -rf Tests/id_set.json and" \
               " rerun the command."

    @staticmethod
    @error_code_decorator
    def changed_incident_field_in_mapper(changed_inc_fields):
        return f"Some incident fields were removed from the mapper, The removed fields: {changed_inc_fields}."

    @staticmethod
    @error_code_decorator
    def removed_incident_types(removed_inc_types):
        return f"Some Incidents types were removed from the mapper, the removed types are: {removed_inc_types}."

    @staticmethod
    @error_code_decorator
    def integration_not_runnable():
        return "Could not find any runnable command in the integration." \
               "Must have at least one command, `isFetch: true`, `feed: true`, `longRunning: true`"

    @staticmethod
    @error_code_decorator
    def invalid_uuid(task_key, id, taskid):
        return f"On task: {task_key},  the field 'taskid': {taskid} and the 'id' under the 'task' field: {id}, " \
               f"must be from uuid format."

    @staticmethod
    @error_code_decorator
    def taskid_different_from_id(task_key, id, taskid):
        return f"On task: {task_key},  the field 'taskid': {taskid} and the 'id' under the 'task' field: {id}, " \
               f"must be with equal value. "

    @staticmethod
    def wrong_filename(file_type):
        return 'This is not a valid {} filename.'.format(file_type)

    @staticmethod
    def wrong_path():
        return "This is not a valid filepath."

    @staticmethod
    def beta_in_str(field):
        return "Field '{}' should NOT contain the substring \"beta\" in a new beta integration. " \
               "please change the id in the file.".format(field)

    @classmethod
    def breaking_backwards_no_old_script(cls, e):
        return "{}\n{}, Could not find the old file.".format(cls.BACKWARDS, str(e))

    @staticmethod
    def id_might_changed():
        return "ID may have changed, please make sure to check you have the correct one."

    @staticmethod
    def id_changed():
        return "You've changed the ID of the file, please undo this change."

    @staticmethod
    def might_need_release_notes():
        return "You may need RN in this file, please verify if they are required."

    @staticmethod
    def unknown_file():
        return "File type is unknown, check it out."

    @staticmethod
    def no_common_server_python(path):
        return "Could not get CommonServerPythonScript.py file. Please download it manually from {} and " \
               "add it to the root of the repository.".format(path)

    @staticmethod
    def no_yml_file(file_path):
        return "No yml files were found in {} directory.".format(file_path)
