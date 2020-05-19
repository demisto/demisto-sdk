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
        return "BA100 - {}: The version for our files should always " \
               "be {}, please update the file.".format(file_path, expected)

    @staticmethod
    def id_should_equal_name(name, file_id, file_path):
        return "BA101 - The File's name, which is: '{}', should be equal to its ID, which is: '{}'." \
               " please update the file (path to file: {}).".format(name, file_id, file_path)

    @staticmethod
    def no_yml_file(file_path):
        return "BA102 - No yml files were found in {} directory.".format(file_path)

    @staticmethod
    def file_type_not_supported(file_path):
        return f"BA103 - The file type of {file_path} is not supported in validate command\n " \
               f"validate' command supports: Integrations, Scripts, Playbooks, " \
               f"Incident fields, Indicator fields, Images, Release notes, Layouts and Descriptions"

    @staticmethod
    def wrong_display_name(param_name, param_display):
        return 'IN100 - The display name of the {} parameter should be \'{}\''.format(param_name, param_display)

    @staticmethod
    def wrong_default_parameter_not_empty(param_name, default_value):
        return 'IN101 - The default value of the {} parameter should be {}'.format(param_name, default_value)

    @staticmethod
    def wrong_required_value(param_name):
        return 'IN102 - The required field of the {} parameter should be False'.format(param_name)

    @staticmethod
    def wrong_required_type(param_name):
        return 'IN103 - The type field of the {} parameter should be 8'.format(param_name)

    @staticmethod
    def wrong_category(file_path, category):
        return "IN104 - {}: The category '{}' is not in the integration schemas, the valid options are:\n{}" \
            .format(file_path, category, '\n'.join(INTEGRATION_CATEGORIES))

    @staticmethod
    def wrong_default_argument(file_path, arg_name, command_name):
        return "IN105 - {}: The argument '{}' of the command '{}' is not configured as default" \
            .format(file_path, arg_name, command_name)

    @staticmethod
    def no_default_arg(file_path, command_name):
        return "IN106 - {}: Could not find default argument " \
               "{} in command {}".format(file_path, command_name, command_name)

    @staticmethod
    def missing_reputation(file_path, command_name, reputation_output, context_standard):
        return "IN107 - {}: The outputs of the reputation command {} aren't valid. The {} outputs is missing. " \
               "Fix according to context standard {} " \
            .format(file_path, command_name, reputation_output, context_standard)

    @staticmethod
    def wrong_subtype(file_name):
        return "IN108 - {}: The subtype for our yml files should be either python2 or python3, " \
               "please update the file.".format(file_name)

    @classmethod
    def beta_in_id(cls, file_path):
        return "IN109 - " + cls.beta_in_str(file_path, 'id')

    @classmethod
    def beta_in_name(cls, file_path):
        return "IN110 - " + cls.beta_in_str(file_path, 'name')

    @staticmethod
    def beta_field_not_found(file_path):
        return "IN111 - {}: Beta integration yml file should have " \
               "the field \"beta: true\", but was not found in the file.".format(file_path)

    @staticmethod
    def no_beta_in_display(file_path):
        return "IN112 - {} :Field 'display' in Beta integration yml file should include the string \"beta\", " \
               "but was not found in the file.".format(file_path)

    @staticmethod
    def duplicate_arg_in_file(script_path, arg, command_name=None):
        err_msg = "{}: The argument '{}' is duplicated".format(script_path, arg)
        if command_name:
            err_msg += " in '{}'.".format(command_name)
        err_msg += ", please remove one of its appearances."
        return "IN113 - " + err_msg

    @staticmethod
    def duplicate_param(param_name, file_path):
        return "IN114 - {}: The parameter '{}' of the " \
               "file is duplicated, please remove one of its appearances.".format(file_path, param_name)

    @staticmethod
    def invalid_context_output(command_name, output):
        return f'IN115 - Invalid context output for command {command_name}. Output is {output}'

    @staticmethod
    def added_required_fields(file_path, field):
        return "IN116 - You've added required fields in the file '{}', the field is '{}'".format(file_path, field)

    @staticmethod
    def not_used_display_name(file_path, field_name):
        return "IN117 - The display details for {} will not be used " \
               "in the file {} due to the type of the parameter".format(field_name, file_path)

    @staticmethod
    def empty_display_configuration(file_path, field_name):
        return "IN118 - No display details were entered for the field {} in the file {}.".format(field_name, file_path)

    @staticmethod
    def feed_wrong_from_version(file_path, given_fromversion, needed_from_version="5.5.0"):
        return "IN119 - {} is a feed and has wrong fromversion. got `{}` expected `{}`" \
            .format(file_path, given_fromversion, needed_from_version)

    @staticmethod
    def pwsh_wrong_version(file_path, given_fromversion, needed_from_version='5.5.0'):
        return (f'IN120 - {file_path}: detected type: powershell and fromversion less than {needed_from_version}.'
                f' Found version: {given_fromversion}')

    @staticmethod
    def parameter_missing_from_yml(file_path, name, correct_format):
        return f'IN121 - {file_path}: A required parameter "{name}" is missing or malformed ' \
               f'in the YAML file.\nThe correct format of the parameter should be as follows:\n{correct_format}'

    @staticmethod
    def parameter_missing_for_feed(file_path, name, correct_format):
        return f'IN122 - {file_path} Feed Integration was detected A required ' \
               f'parameter "{name}" is missing or malformed in the YAML file.\n' \
               f'The correct format of the parameter should be as follows:\n{correct_format}'

    @staticmethod
    def invalid_v2_integration_name(file_path):
        return f"IN123 - The display name of the v2 integration : {file_path} is incorrect , should be **name** v2.\n" \
               f"e.g: Kenna v2, Jira v2"

    @staticmethod
    def found_hidden_param(parameter_name):
        return f"IN124 - Parameter: \"{parameter_name}\" can't be hidden. Please remove this field."

    @staticmethod
    def invalid_v2_script_name(file_path):
        return f"SC100 - The name of the v2 script : {file_path} is incorrect , should be **name**V2." \
               f" e.g: DBotTrainTextClassifierV2"

    @staticmethod
    def dbot_invalid_output(file_path, command_name, missing_outputs, context_standard):
        return "DB100 - {}: The DBotScore outputs of the reputation command {} aren't valid. Missing: {}. " \
               "Fix according to context standard {} ".format(file_path, command_name, missing_outputs,
                                                              context_standard)

    @staticmethod
    def dbot_invalid_description(file_path, command_name, missing_descriptions, context_standard):
        return "DB101 - {}: The DBotScore description of the reputation command {} aren't valid. Missing: {}. " \
               "Fix according to context standard {} " \
            .format(file_path, command_name, missing_descriptions, context_standard)

    @classmethod
    def breaking_backwards_subtype(cls, file_path):
        return "BC100 - {}: {}, You've changed the subtype, please undo.".format(file_path, cls.BACKWARDS)

    @classmethod
    def breaking_backwards_context(cls, file_path):
        return "BC101 - {}: {}, You've changed the context in the file," \
               " please undo.".format(file_path, cls.BACKWARDS)

    @classmethod
    def breaking_backwards_command(cls, file_path, old_command):
        return "BC102 - {}: {}, You've changed the context in the file,please " \
               "undo. the command is:\n{}".format(file_path, cls.BACKWARDS, old_command)

    @classmethod
    def breaking_backwards_arg_changed(cls, file_path):
        return "BC103 - {}: {}, You've changed the name of an arg in " \
               "the file, please undo.".format(file_path, cls.BACKWARDS)

    @classmethod
    def breaking_backwards_command_arg_changed(cls, file_path, command):
        return "BC104 - {}: {}, You've changed the name of a command or its arg in" \
               " the file, please undo, the command was:\n{}".format(file_path, cls.BACKWARDS, command)

    @staticmethod
    def default_docker_error():
        return 'DO100 - The current docker image in the yml file is the default one: demisto/python:1.3-alpine,\n' \
               'Please create or use another docker image\n'

    @staticmethod
    def latest_docker_error(docker_image_tag, docker_image_name):
        return f'DO101 - "latest" tag is not allowed,\n' \
               f'Please create or update to an updated versioned image\n' \
               f'You can check for the most updated version of {docker_image_tag} ' \
               f'here: https://hub.docker.com/r/{docker_image_name}/tags\n'

    @staticmethod
    def not_demisto_docker():
        return 'DO102 - docker image must be a demisto docker image. When the docker image is ready, ' \
               'please rename it to: demisto/<image>:<tag>'

    @staticmethod
    def docker_tag_not_fetched(docker_image_name):
        return f'DO103 - Failed getting tag for: {docker_image_name}. Please check it exists and of demisto format.'

    @staticmethod
    def no_docker_tag(docker_image):
        return f'DO104 - {docker_image} - The docker image in your integration/script does not have a tag.' \
               f'Please create or update to an updated versioned image\n'

    @staticmethod
    def docker_not_formatted_correctly(docker_image):
        return f'DO105 - The docker image: {docker_image} is not of format - demisto/image_name:X.X'

    @staticmethod
    def id_set_conflicts():
        return "ID100 - You probably merged from master and your id_set.json has " \
               "conflicts. Run `demisto-sdk create-id-set`, it should reindex your id_set.json"

    @staticmethod
    def id_set_not_updated(file_path):
        return f"ID101 - You have failed to update id_set.json with the data of {file_path} " \
               f"please run `demisto-sdk create-id-set`"

    @staticmethod
    def duplicated_id(obj_id):
        return f"ID102 - The ID {obj_id} already exists, please update the file or update the " \
               f"id_set.json toversion field of this id to match the old occurrence of this id"

    @staticmethod
    def remove_field_from_dashboard(file_path, field):
        return f'DA100 - {file_path}: the field {field} needs to be removed.\n'

    @staticmethod
    def include_field_in_dashboard(file_path, field):
        return f'DA101 - {file_path}: the field {field} needs to be included. Please add it.\n'

    @staticmethod
    def remove_field_from_widget(field, widget):
        return f'WD100 - The field {field} needs to be removed from the widget: {widget}.\n'

    @staticmethod
    def include_field_in_widget(field, widget_name):
        return f'WD101 - The field {field} needs to be included in the widget: {widget_name}. Please add it.\n'

    @staticmethod
    def no_image_given(file_path):
        return f"IM100 - You've created/modified a yml or package but failed to provide an image as " \
               f"a .png file for {file_path}, please add an image in order to proceed."

    @staticmethod
    def image_too_large(file_path):
        return f"IM101 - {file_path} has too large logo, please update the logo to be under 10kB"

    @staticmethod
    def image_in_package_and_yml(file_path):
        return f"IM102 - The file {file_path} has image in both yml and package, remove the 'image' key from the yml file"

    @staticmethod
    def not_an_image_file(file_path):
        return f"IM103 - {file_path} isn't an image file or unified integration file."

    @staticmethod
    def no_image_field_in_yml(file_path):
        return f"IM104 - {file_path} is a yml file but has no image field."

    @staticmethod
    def image_field_not_in_base64(file_path):
        return f"IM105 - {file_path}'s image field isn't in base64 encoding."

    @staticmethod
    def default_image_error(file_path):
        return f"IM106 - {file_path} is the default image, please change to the integration image."

    @staticmethod
    def description_missing_from_conf_json(problematic_instances):
        return "CJ100 - Those instances don't have description:\n{}".format('\n'.join(problematic_instances))

    @staticmethod
    def test_not_in_conf_json(file_id):
        return f"CJ101 - You've failed to add the {file_id} to conf.json\n" \
               f"see here: https://xsoar.pan.dev/docs/integrations/test-playbooks#adding-tests-to-confjson"

    @staticmethod
    def integration_not_registered(file_path, missing_test_playbook_configurations, no_tests_key):
        return f'CJ102 - The following integration is not registered in {CONF_PATH} file.\n' \
               f'Please add\n{missing_test_playbook_configurations}\nto {CONF_PATH} ' \
               f'path under \'tests\' key.\n' \
               f'If you don\'t want to add a test playbook for this integration, please add \n{no_tests_key}to the ' \
               f'file {file_path} or run \'demisto-sdk format -p {file_path}\''

    @staticmethod
    def no_test_playbook(file_path, file_type):
        return f'CJ103 - You don\'t have a TestPlaybook for {file_type} {file_path}. ' \
               f'If you have a TestPlaybook for this {file_type}, ' \
               f'please edit the yml file and add the TestPlaybook under the \'tests\' key. ' \
               f'If you don\'t want to create a TestPlaybook for this {file_type}, ' \
               f'edit the yml file and add  \ntests:\n -  No tests\n lines to it or ' \
               f'run \'demisto-sdk format -i {file_path}\''

    @staticmethod
    def test_playbook_not_configured(content_item_id, missing_test_playbook_configurations,
                                     missing_integration_configurations):
        return f'CJ104 - The TestPlaybook {content_item_id} is not registered in {CONF_PATH} file.\n ' \
               f'Please add\n{missing_test_playbook_configurations}\n ' \
               f'or if this test playbook is for an integration\n{missing_integration_configurations}\n ' \
               f'to {CONF_PATH} path under \'tests\' key.'

    @staticmethod
    def missing_release_notes(file_path, rn_path):
        return 'RN100 - {}:  is missing release notes, Please add it under {}'.format(file_path, rn_path)

    @staticmethod
    def no_new_release_notes(release_notes_path):
        return F'RN101 - No new comment has been added in the release notes file: {release_notes_path}'

    @staticmethod
    def release_notes_not_formatted_correctly(release_notes_path, link_to_rn_standard):
        return F'RN102 - File {release_notes_path} is not formatted according to ' \
               F'release notes standards.\nFix according to {link_to_rn_standard}'

    @staticmethod
    def release_notes_not_finished(file_path):
        return f"RN103 - Please finish filling out the release notes found at: {file_path}"

    @staticmethod
    def release_notes_file_empty(file_path):
        return f"RN104 - Your release notes file is empty, please complete it - found at: {file_path}"

    @staticmethod
    def multiple_release_notes_files(pack_name):
        return f"RN105 - More than one release notes file has been found for {pack_name}." \
               f"Only one release note file is permitted per release. Please delete the extra release notes."

    @staticmethod
    def missing_release_notes_for_pack(pack):
        return f"RN106 - Release notes were not found for {pack}. Please run `demisto-sdk " \
               f"update-release-notes -p {pack} -u (major|minor|revision)` to " \
               f"generate release notes according to the new standard."

    @staticmethod
    def playbook_cant_have_rolename(file_path):
        return f"PB100 - {file_path} - Playbook can not have a rolename."

    @staticmethod
    def playbook_unreachable_condition(file_path, task_id, next_task_branch):
        return f'PB101 - {file_path} Playbook conditional task with id:{task_id} has task with unreachable ' \
               f'next task condition "{next_task_branch}". Please remove this task or add ' \
               f'this condition to condition task with id:{task_id}.'

    @staticmethod
    def playbook_unhandled_condition(file_path, task_id, task_condition_labels):
        return f'PB102 - {file_path} Playbook conditional task with id:{task_id} has unhandled ' \
               f'condition: {",".join(map(lambda x: f"{str(x)}", task_condition_labels))}'

    @staticmethod
    def playbook_unconnected_tasks(file_path, orphan_tasks):
        return f'PB103 - {file_path} The following tasks ids have no previous tasks: {orphan_tasks}'

    @staticmethod
    def description_missing_in_beta_integration(package_path):
        return f"DS100 - No detailed description file was found in the package {package_path}. Please add one, " \
               f"and make sure it includes the beta disclaimer note." \
               f"It should contain the string in constant\"BETA_INTEGRATION_DISCLAIMER\""

    @staticmethod
    def no_beta_disclaimer_in_description(package_path):
        return f"DS101 - Detailed description in beta integration package {package_path} " \
               f"dose not contain the beta disclaimer note. It should contain the string in constant" \
               f"\"BETA_INTEGRATION_DISCLAIMER\"."

    @staticmethod
    def no_beta_disclaimer_in_yml(file_path):
        return f"DS102 - Detailed description field in beta integration {file_path} " \
               f"dose not contain the beta disclaimer note. It should contain the string in constant" \
               f" \"BETA_INTEGRATION_DISCLAIMER\"."

    @staticmethod
    def description_in_package_and_yml(package_path):
        return f"DS103 - A description was found both in the " \
               f"package and in the yml, please update the package {package_path}."

    @staticmethod
    def invalid_incident_field_name(word, file_path):
        return f"IF100 - The word {word} cannot be used as a name, please update the file {file_path}."

    @staticmethod
    def invalid_incident_field_content_key_value(content_value, file_path):
        return f"IF101 - The content key must be set to {content_value}, please update the file '{file_path}'"

    @staticmethod
    def invalid_incident_field_system_key_value(system_value, file_path):
        return f"IF102 - The system key must be set to {system_value}, please update the file '{file_path}'"

    @staticmethod
    def invalid_incident_field_type(file_path, file_type, TypeFields):
        return f"IF103 - {file_path}: type: `{file_type}` is not one of available type.\n" \
               f"available types: {[value.value for value in TypeFields]}"

    @staticmethod
    def invalid_incident_field_group_value(file_path, group):
        return f"IF104 - {file_path}: group {group} is not a group field."

    @staticmethod
    def invalid_incident_field_cli_name_regex(file_path, cli_regex):
        return f"IF105 - {file_path}: Field `cliName` contains non-alphanumeric letters. " \
               f"must match regex: {cli_regex}"

    @staticmethod
    def invalid_incident_field_cli_name_value(file_path, cli_name):
        return f"IF106 - {file_path}: cliName field can not be {cli_name} as it's a builtin key."

    @staticmethod
    def incident_field_or_type_from_version_5(file_path):
        return f'IF107 - {file_path}: fromVersion must be at least 5.0.0'

    @staticmethod
    def invalid_incident_field_or_type_from_version(file_path):
        return f'IF108 - {file_path}: "fromVersion" has an invalid value.'

    @staticmethod
    def new_incident_field_required(file_path):
        return f'IF109 - {file_path}: new incident fields can not be required. change to:\nrequired: false.'

    @staticmethod
    def from_version_modified_after_rename():
        return "IF110 - fromversion might have been modified, please make sure it hasn't changed."

    @staticmethod
    def incident_field_type_change(file_path):
        return f'IF111 - {file_path}: Changing incident field type is not allowed.'

    @staticmethod
    def incident_type_integer_field(file_path, field):
        return f'IT100 - {file_path}: the field {field} needs to be a positive integer. Please add it.\n'

    @staticmethod
    def pack_file_does_not_exist(file_name):
        return f'"PA100 - {file_name}" file does not exist, create one in the root of the pack'

    @staticmethod
    def cant_open_pack_file(file_name):
        return f'PA101 - Could not open "{file_name}" file'

    @staticmethod
    def cant_read_pack_file(file_name):
        return f'PA102 - Could not read the contents of "{file_name}" file'

    @staticmethod
    def cant_parse_pack_file_to_list(file_name):
        return f'PA103 - Could not parse the contents of "{file_name}" file into a list'

    @staticmethod
    def pack_file_bad_format(file_name):
        return f'PA104 - Detected none valid regex in {file_name} file'

    @staticmethod
    def pack_metadata_empty():
        return 'PA105 - Pack metadata is empty.'

    @staticmethod
    def pack_metadata_should_be_dict(pack_meta_file):
        return f'PA106 - Pack metadata {pack_meta_file} should be a dictionary.'

    @staticmethod
    def missing_field_iin_pack_metadata(pack_meta_file, missing_fields):
        return f'PA107 - {pack_meta_file} - Missing fields in the pack metadata: {missing_fields}'

    @staticmethod
    def pack_metadata_name_not_valid():
        return f'PA108 - Pack metadata {PACK_METADATA_NAME} field is not valid. Please fill valid pack name.'

    @staticmethod
    def pack_metadata_field_invalid():
        return f'PA109 - Pack metadata {PACK_METADATA_DESC} field is not valid. Please fill valid pack description.'

    @staticmethod
    def dependencies_field_should_be_dict(pack_meta_file):
        return f'PA110 - {pack_meta_file} - The dependencies field in the pack must be a dictionary.'

    @staticmethod
    def empty_field_in_pack_metadata(pack_meta_file, list_field):
        return f'PA111 - {pack_meta_file} - Empty value in the {list_field} field.'

    @staticmethod
    def pack_metadata_isnt_json(pack_meta_file):
        return f'PA112 - Could not parse {pack_meta_file} file contents to json format'

    @staticmethod
    def readme_error(file_path, stderr):
        return f'RM100 - Failed verifying README.md, Path: {file_path}. Error Message is: {stderr}'

    @staticmethod
    def wrong_version_reputations(file_path, object_id, version):
        return "RP100 - {} Reputation object with id {} must have version {}".format(file_path, object_id, version)

    @staticmethod
    def reputation_expiration_should_be_numeric(file_path):
        return f'RP101 - {file_path}: expiration field should have a numeric value.'

    @staticmethod
    def reputation_id_and_details_not_equal(file_path):
        return f'RP102 - {file_path}: id and details fields are not equal.'

    @staticmethod
    def structure_doesnt_match_scheme(file_path, pretty_formatted_string_of_regexes):
        return f"ST100 - The file {file_path} does not match any scheme we have please, refer to the following list" \
               f"for the various file name options we have in our repo {pretty_formatted_string_of_regexes}"

    @staticmethod
    def file_id_contains_slashes():
        return "ST101 - File's ID contains slashes - please remove."

    @staticmethod
    def file_id_changed(file_path, old_version_id, new_file_id):
        return f"ST102 - The file id for {file_path} has changed from {old_version_id} to {new_file_id}"

    @staticmethod
    def from_version_modified(file_path):
        return "ST103 - {}: You've added fromversion to an existing " \
               "file in the system, this is not allowed, please undo.".format(file_path)

    @staticmethod
    def wrong_file_extension(file_extension, accepted_extensions):
        return "ST104 - File extension {} is not valid. accepted {}".format(file_extension, accepted_extensions)

    @staticmethod
    def invalid_file_path(file_path):
        return f"ST105 - Found incompatible file path: {file_path}."

    @staticmethod
    def invalid_package_structure(invalid_files):
        return 'ST106 - You should update the following files to the package format, for further details please visit ' \
               'https://github.com/demisto/content/tree/master/docs/package_directory_structure. ' \
               'The files are:\n{}'.format('\n'.join(list(invalid_files)))

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
