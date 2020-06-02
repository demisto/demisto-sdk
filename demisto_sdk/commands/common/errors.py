from typing import Any

from demisto_sdk.commands.common.constants import (CONF_PATH,
                                                   INTEGRATION_CATEGORIES,
                                                   PACK_METADATA_DESC,
                                                   PACK_METADATA_NAME)

FOUND_FILES_AND_ERRORS = []

PRESET_ERROR_TO_IGNORE = {
}

PRESET_ERROR_TO_CHECK = {
    "deprecated": ['ST', 'BC', 'BA'],
}

ERROR_CODE = {
    "wrong_version": "BA100",
    "id_should_equal_name": "BA101",
    "file_type_not_supported": "BA102",
    "wrong_display_name": "IN100",
    "wrong_default_parameter_not_empty": "IN101",
    "wrong_required_value": "IN102",
    "wrong_required_type": "IN103",
    "wrong_category": "IN104",
    "wrong_default_argument": "IN105",
    "no_default_arg": "IN106",
    "missing_reputation": "IN107",
    "wrong_subtype": "IN108",
    "beta_in_id": "IN109",
    "beta_in_name": "IN110",
    "beta_field_not_found": "IN111",
    "no_beta_in_display": "IN112",
    "duplicate_arg_in_file": "IN113",
    "duplicate_param": "IN114",
    "invalid_context_output": "IN115",
    "added_required_fields": "IN116",
    "not_used_display_name": "IN117",
    "empty_display_configuration": "IN118",
    "feed_wrong_from_version": "IN119",
    "pwsh_wrong_version": "IN120",
    "parameter_missing_from_yml": "IN121",
    "parameter_missing_for_feed": "IN122",
    "invalid_v2_integration_name": "IN123",
    "found_hidden_param": "IN124",
    "invalid_v2_script_name": "SC100",
    "dbot_invalid_output": "DB100",
    "dbot_invalid_description": "DB101",
    "breaking_backwards_subtype": "BC100",
    "breaking_backwards_context": "BC101",
    "breaking_backwards_command": "BC102",
    "breaking_backwards_arg_changed": "BC103",
    "breaking_backwards_command_arg_changed": "BC104",
    "default_docker_error": "DO100",
    "latest_docker_error": "DO101",
    "not_demisto_docker": "DO102",
    "docker_tag_not_fetched": "DO103",
    "no_docker_tag": "DO104",
    "docker_not_formatted_correctly": "DO105",
    "id_set_conflicts": "ID100",
    "id_set_not_updated": "ID101",
    "duplicated_id": "ID102",
    "remove_field_from_dashboard": "DA100",
    "include_field_in_dashboard": "DA101",
    "remove_field_from_widget": "WD100",
    "include_field_in_widget": "WD101",
    "no_image_given": "IM100",
    "image_too_large": "IM101",
    "image_in_package_and_yml": "IM102",
    "not_an_image_file": "IM103",
    "no_image_field_in_yml": "IM104",
    "image_field_not_in_base64": "IM105",
    "default_image_error": "IM106",
    "description_missing_from_conf_json": "CJ100",
    "test_not_in_conf_json": "CJ101",
    "integration_not_registered": "CJ102",
    "no_test_playbook": "CJ103",
    "test_playbook_not_configured": "CJ104",
    "missing_release_notes": "RN100",
    "no_new_release_notes": "RN101",
    "release_notes_not_formatted_correctly": "RN102",
    "release_notes_not_finished": "RN103",
    "release_notes_file_empty": "RN104",
    "multiple_release_notes_files": "RN105",
    "missing_release_notes_for_pack": "RN106",
    "missing_release_notes_entry": "RN107",
    "playbook_cant_have_rolename": "PB100",
    "playbook_unreachable_condition": "PB101",
    "playbook_unhandled_condition": "PB102",
    "playbook_unconnected_tasks": "PB103",
    "description_missing_in_beta_integration": "DS100",
    "no_beta_disclaimer_in_description": "DS101",
    "no_beta_disclaimer_in_yml": "DS102",
    "description_in_package_and_yml": "DS103",
    "invalid_incident_field_name": "IF100",
    "invalid_incident_field_content_key_value": "IF101",
    "invalid_incident_field_system_key_value": "IF102",
    "invalid_incident_field_type": "IF103",
    "invalid_incident_field_group_value": "IF104",
    "invalid_incident_field_cli_name_regex": "IF105",
    "invalid_incident_field_cli_name_value": "IF106",
    "incident_field_or_type_from_version_5": "IF107",
    "invalid_incident_field_or_type_from_version": "IF108",
    "new_incident_field_required": "IF109",
    "from_version_modified_after_rename": "IF110",
    "incident_field_type_change": "IF111",
    "incident_type_integer_field": "IT100",
    "pack_file_does_not_exist": "PA100",
    "cant_open_pack_file": "PA101",
    "cant_read_pack_file": "PA102",
    "cant_parse_pack_file_to_list": "PA103",
    "pack_file_bad_format": "PA104",
    "pack_metadata_empty": "PA105",
    "pack_metadata_should_be_dict": "PA106",
    "missing_field_iin_pack_metadata": "PA107",
    "pack_metadata_name_not_valid": "PA108",
    "pack_metadata_field_invalid": "PA109",
    "dependencies_field_should_be_dict": "PA110",
    "empty_field_in_pack_metadata": "PA111",
    "pack_metadata_isnt_json": "PA112",
    "readme_error": "RM100",
    "wrong_version_reputations": "RP100",
    "reputation_expiration_should_be_numeric": "RP101",
    "reputation_id_and_details_not_equal": "RP102",
    "structure_doesnt_match_scheme": "ST100",
    "file_id_contains_slashes": "ST101",
    "file_id_changed": "ST102",
    "from_version_modified": "ST103",
    "wrong_file_extension": "ST104",
    "invalid_file_path": "ST105",
    "invalid_package_structure": "ST106",
    "pykwalify_missing_parameter": "ST107",
    "pykwalify_field_undefined": "ST108",
    "pykwalify_missing_in_root": "ST109",
    "pykwalify_general_error": "ST110",
    "invalid_to_version_in_new_classifiers": "CL100",
    "invalid_to_version_in_old_classifiers": "CL101",
    "invalid_from_version_in_new_classifiers": "CL102",
    "invalid_from_version_in_old_classifiers": "CL103",
    "missing_from_version_in_new_classifiers": "CL104",
    "missing_to_version_in_old_classifiers": "CL105",
    "from_version_higher_to_version": "CL106",
    "invalid_type_in_new_classifiers": "CL107",
    "invalid_from_version_in_mapper": "MP100",
    "invalid_to_version_in_mapper": "MP101",
    "invalid_mapper_file_name": "MP102",
    "missing_from_version_in_mapper": "MP103",
    "invalid_type_in_mapper": "MP104"
}


def error_code_decorator(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs), ERROR_CODE[f.__name__]

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
    def wrong_display_name(param_name, param_display):
        return 'The display name of the {} parameter should be \'{}\''.format(param_name, param_display)

    @staticmethod
    @error_code_decorator
    def wrong_default_parameter_not_empty(param_name, default_value):
        return 'The default value of the {} parameter should be {}'.format(param_name, default_value)

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
    def parameter_missing_for_feed(name, correct_format):
        return f'Feed Integration was detected A required ' \
               f'parameter "{name}" is missing or malformed in the YAML file.\n' \
               f'The correct format of the parameter should be as follows:\n{correct_format}'

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
    def invalid_v2_script_name():
        return "The name of this v2 script is incorrect , should be **name**V2." \
               " e.g: DBotTrainTextClassifierV2"

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
    def docker_not_formatted_correctly(docker_image):
        return f'The docker image: {docker_image} is not of format - demisto/image_name:X.X'

    @staticmethod
    @error_code_decorator
    def id_set_conflicts():
        return "You probably merged from master and your id_set.json has " \
               "conflicts. Run `demisto-sdk create-id-set`, it should reindex your id_set.json"

    @staticmethod
    @error_code_decorator
    def id_set_not_updated(file_path):
        return f"You have failed to update id_set.json with the data of {file_path} " \
               f"please run `demisto-sdk create-id-set`"

    @staticmethod
    @error_code_decorator
    def duplicated_id(obj_id):
        return f"The ID {obj_id} already exists, please update the file or update the " \
               f"id_set.json toversion field of this id to match the old occurrence of this id"

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
               f'file {file_path} or run \'demisto-sdk format -p {file_path}\''

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
        return "Please finish filling out the release notes"

    @staticmethod
    @error_code_decorator
    def release_notes_file_empty():
        return "Your release notes file is empty, please complete it."

    @staticmethod
    @error_code_decorator
    def multiple_release_notes_files():
        return "More than one release notes file has been found." \
               "Only one release note file is permitted per release. Please delete the extra release notes."

    @staticmethod
    @error_code_decorator
    def missing_release_notes_for_pack(pack):
        return f"Release notes were not found for. Please run `demisto-sdk " \
               f"update-release-notes -p {pack} -u (major|minor|revision)` to " \
               f"generate release notes according to the new standard."

    @staticmethod
    @error_code_decorator
    def missing_release_notes_entry(file_type, pack_name, entity_name):
        return f"No release note entry was found for the {file_type.lower()} \"{entity_name}\" in the " \
               f"{pack_name} pack. Please rerun the update-release-notes command without -u to " \
               f"generate an updated template."

    @staticmethod
    @error_code_decorator
    def playbook_cant_have_rolename():
        return "Playbook can not have a rolename."

    @staticmethod
    @error_code_decorator
    def playbook_unreachable_condition(task_id, next_task_branch):
        return f'Playbook conditional task with id:{task_id} has task with unreachable ' \
               f'next task condition "{next_task_branch}". Please remove this task or add ' \
               f'this condition to condition task with id:{task_id}.'

    @staticmethod
    @error_code_decorator
    def playbook_unhandled_condition(task_id, task_condition_labels):
        return f'Playbook conditional task with id:{task_id} has unhandled ' \
               f'condition: {",".join(map(lambda x: f"{str(x)}", task_condition_labels))}'

    @staticmethod
    @error_code_decorator
    def playbook_unconnected_tasks(orphan_tasks):
        return f'The following tasks ids have no previous tasks: {orphan_tasks}'

    @staticmethod
    @error_code_decorator
    def description_missing_in_beta_integration():
        return "No detailed description file was found in the package. Please add one, " \
               "and make sure it includes the beta disclaimer note." \
               "It should contain the string in constant\"BETA_INTEGRATION_DISCLAIMER\""

    @staticmethod
    @error_code_decorator
    def no_beta_disclaimer_in_description():
        return "The detailed description in beta integration package " \
               "dose not contain the beta disclaimer note. It should contain the string in constant" \
               "\"BETA_INTEGRATION_DISCLAIMER\"."

    @staticmethod
    @error_code_decorator
    def no_beta_disclaimer_in_yml():
        return "The detailed description field in beta integration " \
               "dose not contain the beta disclaimer note. It should contain the string in constant" \
               " \"BETA_INTEGRATION_DISCLAIMER\"."

    @staticmethod
    @error_code_decorator
    def description_in_package_and_yml():
        return "A description was found both in the " \
               "package and in the yml, please update the package."

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
        return f"Type: `{file_type}` is not one of available type.\n" \
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
    def incident_field_or_type_from_version_5():
        return 'fromVersion must be at least 5.0.0'

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
    def readme_error(stderr):
        return f'Failed verifying README.md Error Message is: {stderr}'

    @staticmethod
    @error_code_decorator
    def wrong_version_reputations(object_id, version):
        return "Reputation object with id {} must have version {}".format(object_id, version)

    @staticmethod
    @error_code_decorator
    def reputation_expiration_should_be_numeric():
        return 'Expiration field should have a numeric value.'

    @staticmethod
    @error_code_decorator
    def reputation_id_and_details_not_equal():
        return 'id and details fields are not equal.'

    @staticmethod
    @error_code_decorator
    def structure_doesnt_match_scheme(pretty_formatted_string_of_regexes):
        return f"The file does not match any scheme we have please, refer to the following list" \
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
        return 'You should update the following files to the package format, for further details please visit ' \
               'https://github.com/demisto/content/tree/master/docs/package_directory_structure. ' \
               'The files are:\n{}'.format('\n'.join(list(invalid_files)))

    @staticmethod
    @error_code_decorator
    def pykwalify_missing_parameter(key_from_error, current_string, path):
        return f'Missing {key_from_error} in \n{current_string}\nPath: {path}'

    @staticmethod
    @error_code_decorator
    def pykwalify_field_undefined(key_from_error):
        return f'The field {key_from_error} was not defined in the scheme'

    @staticmethod
    @error_code_decorator
    def pykwalify_missing_in_root(key_from_error):
        return f'Missing {key_from_error} in root'

    @staticmethod
    @error_code_decorator
    def pykwalify_general_error(error):
        return f'in {error}'

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
        return "ID might have changed, please make sure to check you have the correct one."

    @staticmethod
    def id_changed():
        return "You've changed the ID of the file, please undo."

    @staticmethod
    def might_need_release_notes():
        return "You might need RN in file, please make sure to check that."

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
