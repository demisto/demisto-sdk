from typing import Any

from demisto_sdk.commands.common.constants import (CONF_PATH,
                                                   INTEGRATION_CATEGORIES,
                                                   PACK_METADATA_DESC,
                                                   PACK_METADATA_NAME)


class Errors:
    BACKWARDS = "Possible backwards compatibility break"

    @staticmethod
    def suggest_fix(file_path: str, *args: Any, cmd: str = 'format') -> str:
        return f'To fix the problem, try running `demisto-sdk {cmd} -i {file_path} {" ".join(args)}`'

    @staticmethod
    def wrong_version(file_path, expected="-1"):
        return "{}: The version for our files should always " \
               "be {}, please update the file.".format(file_path, expected), "BA100"

    @staticmethod
    def id_should_equal_name(name, file_id, file_path):
        return "The File's name, which is: '{}', should be equal to its ID, which is: '{}'." \
               " please update the file (path to file: {}).".format(name, file_id, file_path), "BA101"

    @staticmethod
    def file_type_not_supported(file_path):
        return f"The file type of {file_path} is not supported in validate command\n " \
               f"validate' command supports: Integrations, Scripts, Playbooks, " \
               f"Incident fields, Indicator fields, Images, Release notes, Layouts and Descriptions", "BA102"

    @staticmethod
    def wrong_display_name(param_name, param_display):
        return 'The display name of the {} parameter should be \'{}\''.format(param_name, param_display), \
               "IN100"

    @staticmethod
    def wrong_default_parameter_not_empty(param_name, default_value):
        return 'The default value of the {} parameter should be {}'.format(param_name, default_value), "IN101"

    @staticmethod
    def wrong_required_value(param_name):
        return 'The required field of the {} parameter should be False'.format(param_name), "IN102"

    @staticmethod
    def wrong_required_type(param_name):
        return 'The type field of the {} parameter should be 8'.format(param_name), "IN103"

    @staticmethod
    def wrong_category(file_path, category):
        return "{}: The category '{}' is not in the integration schemas, the valid options are:\n{}" \
            .format(file_path, category, '\n'.join(INTEGRATION_CATEGORIES)), "IN104"

    @staticmethod
    def wrong_default_argument(file_path, arg_name, command_name):
        return "{}: The argument '{}' of the command '{}' is not configured as default" \
            .format(file_path, arg_name, command_name), "IN105"

    @staticmethod
    def no_default_arg(file_path, command_name):
        return "{}: Could not find default argument " \
               "{} in command {}".format(file_path, command_name, command_name), "IN106"

    @staticmethod
    def missing_reputation(file_path, command_name, reputation_output, context_standard):
        return "{}: The outputs of the reputation command {} aren't valid. The {} outputs is missing. " \
               "Fix according to context standard {} " \
            .format(file_path, command_name, reputation_output, context_standard), "IN107"

    @staticmethod
    def wrong_subtype(file_name):
        return "{}: The subtype for our yml files should be either python2 or python3, " \
               "please update the file.".format(file_name), "IN108"

    @classmethod
    def beta_in_id(cls, file_path):
        return cls.beta_in_str(file_path, 'id'), "IN109"

    @classmethod
    def beta_in_name(cls, file_path):
        return cls.beta_in_str(file_path, 'name'), "IN110"

    @staticmethod
    def beta_field_not_found(file_path):
        return "{}: Beta integration yml file should have " \
               "the field \"beta: true\", but was not found in the file.".format(file_path), "IN111"

    @staticmethod
    def no_beta_in_display(file_path):
        return "{} :Field 'display' in Beta integration yml file should include the string \"beta\", " \
               "but was not found in the file.".format(file_path), "IN112"

    @staticmethod
    def duplicate_arg_in_file(script_path, arg, command_name=None):
        err_msg = "{}: The argument '{}' is duplicated".format(script_path, arg)
        if command_name:
            err_msg += " in '{}'.".format(command_name)
        err_msg += ", please remove one of its appearances."
        return err_msg, "IN113"

    @staticmethod
    def duplicate_param(param_name, file_path):
        return "{}: The parameter '{}' of the " \
               "file is duplicated, please remove one of its appearances.".format(file_path, param_name), "IN114"

    @staticmethod
    def invalid_context_output(command_name, output):
        return f'Invalid context output for command {command_name}. Output is {output}', "IN115"

    @staticmethod
    def added_required_fields(file_path, field):
        return "You've added required fields in the file '{}', the field is '{}'".format(file_path, field), \
               "IN116"

    @staticmethod
    def not_used_display_name(file_path, field_name):
        return "The display details for {} will not be used " \
               "in the file {} due to the type of the parameter".format(field_name, file_path), "IN117"

    @staticmethod
    def empty_display_configuration(file_path, field_name):
        return "No display details were entered for the field {} " \
               "in the file {}.".format(field_name, file_path), "IN118"

    @staticmethod
    def feed_wrong_from_version(file_path, given_fromversion, needed_from_version="5.5.0"):
        return "{} is a feed and has wrong fromversion. got `{}` expected `{}`" \
            .format(file_path, given_fromversion, needed_from_version), "IN119"

    @staticmethod
    def pwsh_wrong_version(file_path, given_fromversion, needed_from_version='5.5.0'):
        return f'{file_path}: detected type: powershell and fromversion less than {needed_from_version}.' \
               f' Found version: {given_fromversion}', "IN120"

    @staticmethod
    def parameter_missing_from_yml(file_path, name, correct_format):
        return f'{file_path}: A required parameter "{name}" is missing or malformed ' \
               f'in the YAML file.\nThe correct format of the parameter should ' \
               f'be as follows:\n{correct_format}', "IN121"

    @staticmethod
    def parameter_missing_for_feed(file_path, name, correct_format):
        return f'{file_path} Feed Integration was detected A required ' \
               f'parameter "{name}" is missing or malformed in the YAML file.\n' \
               f'The correct format of the parameter should be as follows:\n{correct_format}', "IN122"

    @staticmethod
    def invalid_v2_integration_name(file_path):
        return f"The display name of the v2 integration : {file_path} is incorrect , should be **name** v2.\n" \
               f"e.g: Kenna v2, Jira v2", "IN123"

    @staticmethod
    def found_hidden_param(parameter_name):
        return f"Parameter: \"{parameter_name}\" can't be hidden. Please remove this field.", "IN124"

    @staticmethod
    def invalid_v2_script_name(file_path):
        return f"The name of the v2 script : {file_path} is incorrect , should be **name**V2." \
               f" e.g: DBotTrainTextClassifierV2", "SC100"

    @staticmethod
    def dbot_invalid_output(file_path, command_name, missing_outputs, context_standard):
        return "{}: The DBotScore outputs of the reputation command {} aren't valid. Missing: {}. " \
               "Fix according to context standard {} ".format(file_path, command_name, missing_outputs,
                                                              context_standard), "DB100"

    @staticmethod
    def dbot_invalid_description(file_path, command_name, missing_descriptions, context_standard):
        return "{}: The DBotScore description of the reputation command {} aren't valid. Missing: {}. " \
               "Fix according to context standard {} " \
            .format(file_path, command_name, missing_descriptions, context_standard), "DB101"

    @classmethod
    def breaking_backwards_subtype(cls, file_path):
        return "{}: {}, You've changed the subtype, please undo.".format(file_path, cls.BACKWARDS), "BC100"

    @classmethod
    def breaking_backwards_context(cls, file_path):
        return "{}: {}, You've changed the context in the file," \
               " please undo.".format(file_path, cls.BACKWARDS), "BC101"

    @classmethod
    def breaking_backwards_command(cls, file_path, old_command):
        return "{}: {}, You've changed the context in the file,please " \
               "undo. the command is:\n{}".format(file_path, cls.BACKWARDS, old_command), "BC102"

    @classmethod
    def breaking_backwards_arg_changed(cls, file_path):
        return "{}: {}, You've changed the name of an arg in " \
               "the file, please undo.".format(file_path, cls.BACKWARDS), "BC103"

    @classmethod
    def breaking_backwards_command_arg_changed(cls, file_path, command):
        return "{}: {}, You've changed the name of a command or its arg in" \
               " the file, please undo, the command was:\n{}".format(file_path, cls.BACKWARDS, command), "BC104"

    @staticmethod
    def default_docker_error():
        return 'The current docker image in the yml file is the default one: demisto/python:1.3-alpine,\n' \
               'Please create or use another docker image\n', "DO100"

    @staticmethod
    def latest_docker_error(docker_image_tag, docker_image_name):
        return f'"latest" tag is not allowed,\n' \
               f'Please create or update to an updated versioned image\n' \
               f'You can check for the most updated version of {docker_image_tag} ' \
               f'here: https://hub.docker.com/r/{docker_image_name}/tags\n', "DO101"

    @staticmethod
    def not_demisto_docker():
        return 'docker image must be a demisto docker image. When the docker image is ready, ' \
               'please rename it to: demisto/<image>:<tag>', "DO102"

    @staticmethod
    def docker_tag_not_fetched(docker_image_name):
        return f'Failed getting tag for: {docker_image_name}. Please check it exists and of demisto format.', \
               "DO103"

    @staticmethod
    def no_docker_tag(docker_image):
        return f'{docker_image} - The docker image in your integration/script does not have a tag.' \
               f'Please create or update to an updated versioned image\n', "DO104"

    @staticmethod
    def docker_not_formatted_correctly(docker_image):
        return f'The docker image: {docker_image} is not of format - demisto/image_name:X.X', "DO105"

    @staticmethod
    def id_set_conflicts():
        return "You probably merged from master and your id_set.json has " \
               "conflicts. Run `demisto-sdk create-id-set`, it should reindex your id_set.json", "ID100"

    @staticmethod
    def id_set_not_updated(file_path):
        return f"You have failed to update id_set.json with the data of {file_path} " \
               f"please run `demisto-sdk create-id-set`", "ID101"

    @staticmethod
    def duplicated_id(obj_id):
        return f"The ID {obj_id} already exists, please update the file or update the " \
               f"id_set.json toversion field of this id to match the old occurrence of this id", "ID102"

    @staticmethod
    def remove_field_from_dashboard(file_path, field):
        return f'{file_path}: the field {field} needs to be removed.\n', "DA100"

    @staticmethod
    def include_field_in_dashboard(file_path, field):
        return f'{file_path}: the field {field} needs to be included. Please add it.\n', "DA101"

    @staticmethod
    def remove_field_from_widget(field, widget):
        return f'The field {field} needs to be removed from the widget: {widget}.\n', "WD100"

    @staticmethod
    def include_field_in_widget(field, widget_name):
        return f'The field {field} needs to be included in the widget: {widget_name}. Please add it.\n', "WD101"

    @staticmethod
    def no_image_given(file_path):
        return f"You've created/modified a yml or package but failed to provide an image as " \
               f"a .png file for {file_path}, please add an image in order to proceed.", "IM100"

    @staticmethod
    def image_too_large(file_path):
        return f"{file_path} has too large logo, please update the logo to be under 10kB", "IM101"

    @staticmethod
    def image_in_package_and_yml(file_path):
        return f"The file {file_path} has image in both yml and package, remove the 'image' " \
               f"key from the yml file", "IM102"

    @staticmethod
    def not_an_image_file(file_path):
        return f"{file_path} isn't an image file or unified integration file.", "IM103"

    @staticmethod
    def no_image_field_in_yml(file_path):
        return f"{file_path} is a yml file but has no image field.", "IM104"

    @staticmethod
    def image_field_not_in_base64(file_path):
        return f"{file_path}'s image field isn't in base64 encoding.", "IM105"

    @staticmethod
    def default_image_error(file_path):
        return f"{file_path} is the default image, please change to the integration image.", "IM106"

    @staticmethod
    def description_missing_from_conf_json(problematic_instances):
        return "Those instances don't have description:\n{}".format('\n'.join(problematic_instances)), "CJ100"

    @staticmethod
    def test_not_in_conf_json(file_id):
        return f"You've failed to add the {file_id} to conf.json\n" \
               f"see here: https://xsoar.pan.dev/docs/integrations/test-playbooks#adding-tests-to-confjson", "CJ101"

    @staticmethod
    def integration_not_registered(file_path, missing_test_playbook_configurations, no_tests_key):
        return f'The following integration is not registered in {CONF_PATH} file.\n' \
               f'Please add\n{missing_test_playbook_configurations}\nto {CONF_PATH} ' \
               f'path under \'tests\' key.\n' \
               f'If you don\'t want to add a test playbook for this integration, please add \n{no_tests_key}to the ' \
               f'file {file_path} or run \'demisto-sdk format -p {file_path}\'', "CJ102"

    @staticmethod
    def no_test_playbook(file_path, file_type):
        return f'You don\'t have a TestPlaybook for {file_type} {file_path}. ' \
               f'If you have a TestPlaybook for this {file_type}, ' \
               f'please edit the yml file and add the TestPlaybook under the \'tests\' key. ' \
               f'If you don\'t want to create a TestPlaybook for this {file_type}, ' \
               f'edit the yml file and add  \ntests:\n -  No tests\n lines to it or ' \
               f'run \'demisto-sdk format -i {file_path}\'', "CJ103"

    @staticmethod
    def test_playbook_not_configured(content_item_id, missing_test_playbook_configurations,
                                     missing_integration_configurations):
        return f'The TestPlaybook {content_item_id} is not registered in {CONF_PATH} file.\n ' \
               f'Please add\n{missing_test_playbook_configurations}\n ' \
               f'or if this test playbook is for an integration\n{missing_integration_configurations}\n ' \
               f'to {CONF_PATH} path under \'tests\' key.', "CJ104"

    @staticmethod
    def missing_release_notes(file_path, rn_path):
        return '{}:  is missing release notes, Please add it under {}'.format(file_path, rn_path), "RN100"

    @staticmethod
    def no_new_release_notes(release_notes_path):
        return F'No new comment has been added in the release notes file: {release_notes_path}', "RN101"

    @staticmethod
    def release_notes_not_formatted_correctly(release_notes_path, link_to_rn_standard):
        return F'File {release_notes_path} is not formatted according to ' \
               F'release notes standards.\nFix according to {link_to_rn_standard}', "RN102"

    @staticmethod
    def release_notes_not_finished(file_path):
        return f"Please finish filling out the release notes found at: {file_path}", "RN103"

    @staticmethod
    def release_notes_file_empty(file_path):
        return f"Your release notes file is empty, please complete it - found at: {file_path}", "RN104"

    @staticmethod
    def multiple_release_notes_files(pack_name):
        return f"More than one release notes file has been found for {pack_name}." \
               f"Only one release note file is permitted per release. Please delete the extra release notes.", "RN105"

    @staticmethod
    def missing_release_notes_for_pack(pack):
        return f"Release notes were not found for {pack}. Please run `demisto-sdk " \
               f"update-release-notes -p {pack} -u (major|minor|revision)` to " \
               f"generate release notes according to the new standard.", "RN106"

    @staticmethod
    def playbook_cant_have_rolename(file_path):
        return f"{file_path} - Playbook can not have a rolename.", "PB100"

    @staticmethod
    def playbook_unreachable_condition(file_path, task_id, next_task_branch):
        return f'{file_path} Playbook conditional task with id:{task_id} has task with unreachable ' \
               f'next task condition "{next_task_branch}". Please remove this task or add ' \
               f'this condition to condition task with id:{task_id}.', "PB101"

    @staticmethod
    def playbook_unhandled_condition(file_path, task_id, task_condition_labels):
        return f'{file_path} Playbook conditional task with id:{task_id} has unhandled ' \
               f'condition: {",".join(map(lambda x: f"{str(x)}", task_condition_labels))}', "PB102"

    @staticmethod
    def playbook_unconnected_tasks(file_path, orphan_tasks):
        return f'{file_path} The following tasks ids have no previous tasks: {orphan_tasks}', "PB103"

    @staticmethod
    def description_missing_in_beta_integration(package_path):
        return f"No detailed description file was found in the package {package_path}. Please add one, " \
               f"and make sure it includes the beta disclaimer note." \
               f"It should contain the string in constant\"BETA_INTEGRATION_DISCLAIMER\"", "DS100"

    @staticmethod
    def no_beta_disclaimer_in_description(package_path):
        return f"Detailed description in beta integration package {package_path} " \
               f"dose not contain the beta disclaimer note. It should contain the string in constant" \
               f"\"BETA_INTEGRATION_DISCLAIMER\".", "DS101"

    @staticmethod
    def no_beta_disclaimer_in_yml(file_path):
        return f"Detailed description field in beta integration {file_path} " \
               f"dose not contain the beta disclaimer note. It should contain the string in constant" \
               f" \"BETA_INTEGRATION_DISCLAIMER\".", "DS102"

    @staticmethod
    def description_in_package_and_yml(package_path):
        return f"A description was found both in the " \
               f"package and in the yml, please update the package {package_path}.", "DS103"

    @staticmethod
    def invalid_incident_field_name(word, file_path):
        return f"The word {word} cannot be used as a name, please update the file {file_path}.", "IF100"

    @staticmethod
    def invalid_incident_field_content_key_value(content_value, file_path):
        return f"The content key must be set to {content_value}, please update the file '{file_path}'", "IF101"

    @staticmethod
    def invalid_incident_field_system_key_value(system_value, file_path):
        return f"The system key must be set to {system_value}, please update the file '{file_path}'", "IF102"

    @staticmethod
    def invalid_incident_field_type(file_path, file_type, TypeFields):
        return f"{file_path}: type: `{file_type}` is not one of available type.\n" \
               f"available types: {[value.value for value in TypeFields]}", "IF103"

    @staticmethod
    def invalid_incident_field_group_value(file_path, group):
        return f"{file_path}: group {group} is not a group field.", "IF104"

    @staticmethod
    def invalid_incident_field_cli_name_regex(file_path, cli_regex):
        return f"{file_path}: Field `cliName` contains non-alphanumeric letters. " \
               f"must match regex: {cli_regex}", "IF105"

    @staticmethod
    def invalid_incident_field_cli_name_value(file_path, cli_name):
        return f"{file_path}: cliName field can not be {cli_name} as it's a builtin key.", "IF106"

    @staticmethod
    def incident_field_or_type_from_version_5(file_path):
        return f'{file_path}: fromVersion must be at least 5.0.0', "IF107"

    @staticmethod
    def invalid_incident_field_or_type_from_version(file_path):
        return f'{file_path}: "fromVersion" has an invalid value.', "IF108"

    @staticmethod
    def new_incident_field_required(file_path):
        return f'{file_path}: new incident fields can not be required. change to:\nrequired: false.', "IF109"

    @staticmethod
    def from_version_modified_after_rename():
        return "fromversion might have been modified, please make sure it hasn't changed.", "IF110"

    @staticmethod
    def incident_field_type_change(file_path):
        return f'{file_path}: Changing incident field type is not allowed.', "IF111"

    @staticmethod
    def incident_type_integer_field(file_path, field):
        return f'{file_path}: the field {field} needs to be a positive integer. Please add it.\n', "IT100"

    @staticmethod
    def pack_file_does_not_exist(file_name):
        return f'"{file_name}" file does not exist, create one in the root of the pack', "PA100"

    @staticmethod
    def cant_open_pack_file(file_name):
        return f'Could not open "{file_name}" file', "PA101"

    @staticmethod
    def cant_read_pack_file(file_name):
        return f'Could not read the contents of "{file_name}" file', "PA102"

    @staticmethod
    def cant_parse_pack_file_to_list(file_name):
        return f'Could not parse the contents of "{file_name}" file into a list', "PA103"

    @staticmethod
    def pack_file_bad_format(file_name):
        return f'Detected none valid regex in {file_name} file', "PA104"

    @staticmethod
    def pack_metadata_empty():
        return 'Pack metadata is empty.', "PA105"

    @staticmethod
    def pack_metadata_should_be_dict(pack_meta_file):
        return f'Pack metadata {pack_meta_file} should be a dictionary.', "PA106"

    @staticmethod
    def missing_field_iin_pack_metadata(pack_meta_file, missing_fields):
        return f'{pack_meta_file} - Missing fields in the pack metadata: {missing_fields}', "PA107"

    @staticmethod
    def pack_metadata_name_not_valid():
        return f'Pack metadata {PACK_METADATA_NAME} field is not valid. Please fill valid pack name.', "PA108"

    @staticmethod
    def pack_metadata_field_invalid():
        return f'Pack metadata {PACK_METADATA_DESC} field is not valid. Please fill valid pack description.', \
               "PA109"

    @staticmethod
    def dependencies_field_should_be_dict(pack_meta_file):
        return f'{pack_meta_file} - The dependencies field in the pack must be a dictionary.', "PA110"

    @staticmethod
    def empty_field_in_pack_metadata(pack_meta_file, list_field):
        return f'{pack_meta_file} - Empty value in the {list_field} field.', "PA111"

    @staticmethod
    def pack_metadata_isnt_json(pack_meta_file):
        return f'Could not parse {pack_meta_file} file contents to json format', "PA112"

    @staticmethod
    def readme_error(file_path, stderr):
        return f'Failed verifying README.md, Path: {file_path}. Error Message is: {stderr}', "RM100"

    @staticmethod
    def wrong_version_reputations(file_path, object_id, version):
        return "{} Reputation object with id {} must have version {}".format(file_path, object_id, version), \
               "RP100"

    @staticmethod
    def reputation_expiration_should_be_numeric(file_path):
        return f'{file_path}: expiration field should have a numeric value.', "RP101"

    @staticmethod
    def reputation_id_and_details_not_equal(file_path):
        return f'{file_path}: id and details fields are not equal.', "RP102"

    @staticmethod
    def structure_doesnt_match_scheme(file_path, pretty_formatted_string_of_regexes):
        return f"The file {file_path} does not match any scheme we have please, refer to the following list" \
               f"for the various file name options we have in our repo {pretty_formatted_string_of_regexes}", "ST100"

    @staticmethod
    def file_id_contains_slashes():
        return "File's ID contains slashes - please remove.", "ST101"

    @staticmethod
    def file_id_changed(file_path, old_version_id, new_file_id):
        return f"The file id for {file_path} has changed from {old_version_id} to {new_file_id}", "ST102"

    @staticmethod
    def from_version_modified(file_path):
        return "{}: You've added fromversion to an existing " \
               "file in the system, this is not allowed, please undo.".format(file_path), "ST103"

    @staticmethod
    def wrong_file_extension(file_extension, accepted_extensions):
        return "File extension {} is not valid. accepted {}".format(file_extension, accepted_extensions), \
               "ST104"

    @staticmethod
    def invalid_file_path(file_path):
        return f"Found incompatible file path: {file_path}.", "ST105"

    @staticmethod
    def invalid_package_structure(invalid_files):
        return 'You should update the following files to the package format, for further details please visit ' \
               'https://github.com/demisto/content/tree/master/docs/package_directory_structure. ' \
               'The files are:\n{}'.format('\n'.join(list(invalid_files))), "ST106"

    @staticmethod
    def wrong_filename(filepath, file_type):
        return '{} is not a valid {} filename.'.format(filepath, file_type)

    @staticmethod
    def wrong_path(filepath):
        return "{} is not a valid filepath.".format(filepath)

    @staticmethod
    def beta_in_str(file_path, field):
        return "{}: Field '{}' should NOT contain the substring \"beta\" in a new beta integration. " \
               "please change the id in the file.".format(field, file_path)

    @classmethod
    def breaking_backwards_no_old_script(cls, e):
        return "{}\n{}, Could not find the old file.".format(cls.BACKWARDS, str(e))

    @staticmethod
    def id_might_changed():
        return "ID might have changed, please make sure to check you have the correct one."

    @staticmethod
    def id_changed(file_path):
        return "{}: You've changed the ID of the file, please undo.".format(file_path)

    @staticmethod
    def might_need_release_notes(file_path):
        return "{}: You might need RN in file, please make sure to check that.".format(file_path)

    @staticmethod
    def unknown_file(file_path):
        return "{}:  File type is unknown, check it out.".format(file_path)

    @staticmethod
    def wrong_default_parameter(param_name):
        return Errors.wrong_default_parameter_not_empty(param_name, "''")

    @staticmethod
    def no_common_server_python(path):
        return "Could not get CommonServerPythonScript.py file. Please download it manually from {} and " \
               "add it to the root of the repository.".format(path)

    @staticmethod
    def no_yml_file(file_path):
        return "No yml files were found in {} directory.".format(file_path)
