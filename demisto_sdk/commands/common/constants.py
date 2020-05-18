import re
from typing import Any, List


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
    def no_docker_tag():
        return f'DO104 - The docker image in your integration/script does not have a tag.' \
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
        return f'"PU100 - {file_name}" file does not exist, create one in the root of the pack'

    @staticmethod
    def cant_open_pack_file(file_name):
        return f'PU101 - Could not open "{file_name}" file'

    @staticmethod
    def cant_read_pack_file(file_name):
        return f'PU102 - Could not read the contents of "{file_name}" file'

    @staticmethod
    def cant_parse_pack_file_to_list(file_name):
        return f'PU103 - Could not parse the contents of "{file_name}" file into a list'

    @staticmethod
    def pack_file_bad_format(file_name):
        return f'PU104 - Detected none valid regex in {file_name} file'

    @staticmethod
    def pack_metadata_empty():
        return 'PU105 - Pack metadata is empty.'

    @staticmethod
    def pack_metadata_should_be_dict(pack_meta_file):
        return f'PU106 - Pack metadata {pack_meta_file} should be a dictionary.'

    @staticmethod
    def missing_field_iin_pack_metadata(pack_meta_file, missing_fields):
        return f'PU107 - {pack_meta_file} - Missing fields in the pack metadata: {missing_fields}'

    @staticmethod
    def pack_metadata_name_not_valid():
        return f'PU108 - Pack metadata {PACK_METADATA_NAME} field is not valid. Please fill valid pack name.'

    @staticmethod
    def pack_metadata_field_invalid():
        return f'PU109 - Pack metadata {PACK_METADATA_DESC} field is not valid. Please fill valid pack description.'

    @staticmethod
    def dependencies_field_should_be_dict(pack_meta_file):
        return f'PU110 - {pack_meta_file} - The dependencies field in the pack must be a dictionary.'

    @staticmethod
    def empty_field_in_pack_metadata(pack_meta_file, list_field):
        return f'PU111 - {pack_meta_file} - Empty value in the {list_field} field.'

    @staticmethod
    def pack_metadata_isnt_json(pack_meta_file):
        return f'PU112 - Could not parse {pack_meta_file} file contents to json format'

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
    def no_yml_file(file_path):
        return "No yml files were found in {} directory.".format(file_path)

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


# dirs
CAN_START_WITH_DOT_SLASH = '(?:./)?'
NOT_TEST = '(?!Test)'
INTEGRATIONS_DIR = 'Integrations'
SCRIPTS_DIR = 'Scripts'
PLAYBOOKS_DIR = 'Playbooks'
TEST_PLAYBOOKS_DIR = 'TestPlaybooks'
REPORTS_DIR = 'Reports'
DASHBOARDS_DIR = 'Dashboards'
WIDGETS_DIR = 'Widgets'
INCIDENT_FIELDS_DIR = 'IncidentFields'
INCIDENT_TYPES_DIR = 'IncidentTypes'
INDICATOR_FIELDS_DIR = 'IndicatorFields'
INDICATOR_TYPES_DIR = 'IndicatorTypes'
LAYOUTS_DIR = 'Layouts'
CLASSIFIERS_DIR = 'Classifiers'
CONNECTIONS_DIR = 'Connections'
BETA_INTEGRATIONS_DIR = 'Beta_Integrations'
PACKS_DIR = 'Packs'
TOOLS_DIR = 'Tools'
RELEASE_NOTES_DIR = 'ReleaseNotes'
TESTS_DIR = 'Tests'

SCRIPT = 'script'
INTEGRATION = 'integration'
PLAYBOOK = 'playbook'
LAYOUT = 'layout'
INCIDENT_TYPE = 'incidenttype'
INCIDENT_FIELD = 'incidentfield'
INDICATOR_FIELD = 'indicatorfield'
CONNECTION = 'connection'
CLASSIFIER = 'classifier'
DASHBOARD = 'dashboard'
REPORT = 'report'
INDICATOR_TYPE = 'reputation'
WIDGET = 'widget'

ENTITY_TYPE_TO_DIR = {
    INTEGRATION: INTEGRATIONS_DIR,
    PLAYBOOK: PLAYBOOKS_DIR,
    SCRIPT: SCRIPTS_DIR,
    LAYOUT: LAYOUTS_DIR,
    INCIDENT_FIELD: INCIDENT_FIELDS_DIR,
    INCIDENT_TYPE: INCIDENT_TYPES_DIR,
    INDICATOR_FIELD: INDICATOR_FIELDS_DIR,
    CONNECTION: CONNECTIONS_DIR,
    CLASSIFIER: CLASSIFIERS_DIR,
    DASHBOARD: DASHBOARDS_DIR,
    INDICATOR_TYPE: INDICATOR_TYPES_DIR,
    REPORT: REPORTS_DIR,
    WIDGET: WIDGETS_DIR
}

CONTENT_FILE_ENDINGS = ['py', 'yml', 'png', 'json', 'md']

CUSTOM_CONTENT_FILE_ENDINGS = ['yml', 'json']

CONTENT_ENTITIES_DIRS = [
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PLAYBOOKS_DIR,
    TEST_PLAYBOOKS_DIR,
    REPORTS_DIR,
    DASHBOARDS_DIR,
    WIDGETS_DIR,
    INCIDENT_FIELDS_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INCIDENT_TYPES_DIR,
    LAYOUTS_DIR,
    CLASSIFIERS_DIR,
    CONNECTIONS_DIR,
    BETA_INTEGRATIONS_DIR
]

CONTENT_ENTITY_UPLOAD_ORDER = [
    INTEGRATIONS_DIR,
    BETA_INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PLAYBOOKS_DIR,
    TEST_PLAYBOOKS_DIR,
    INCIDENT_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    CLASSIFIERS_DIR,
    WIDGETS_DIR,
    LAYOUTS_DIR,
    DASHBOARDS_DIR
]

DEFAULT_IMAGE_PREFIX = 'data:image/png;base64,'
DEFAULT_IMAGE_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAMAAAC5zwKfAAACYVBMVEVHcEwAT4UAT4UAT4YAf/8A//8AT4UAf78AT4U' \
                       'AT4UAT4UAUYcAT4YAT4YAT48AXIsAT4UAT4UAUIUAUIUAT4UAT4UAVaoAW5EAUIYAWYwAT4UAT4UAT4UAUIgAT4YAUo' \
                       'UAUIYAUIUAT4YAVY0AUIUAT4UAUIUAUocAUYUAT4UAT4UAT4UAUIYAT4UAUIUAT4cAUYUAUIUAUIYAUocAT4UAUIUAT' \
                       '4YAUY4AUIUAUIYAT4UAVYgAT4UAT4UAT4YAVYUAT4UAT4UAT4YAT4cAT4UAT4UAUYYAZpkAWIUAT4UAT4gAbZEAT4UA' \
                       'UIYAT4UAUIUAT4cAUYgAT4UAZpkAT4UAT4UAT4UAVaoAUIUAT4UAWIkAT4UAU4kAUIUAUIUAU4gAT4UAT4UAT4UAVYg' \
                       'AUIUAT4YAVYkAUYUAT4UAU4cAUIYAUIUAT4gAUIYAVYsAT4YAUocAUYUAUIYAUYgAT4UAT4UAT4UAT4UAUYUAU4UAUY' \
                       'gAT4UAVY0AUIUAUIUAT4UAT4cAT4oAVY0AUYcAUIcAUIUAUIYAUIcAUYcAUIUAT4UAT4UAUIUAT4UAX58AT4UAUIUAU' \
                       'IYAT4UAUIYAUIgAT4UAT4UAUIUAT4UAUIUAT4YAT4UAUIYAT4YAUYkAT4UAUYYAUIUAT4UAT4YAT4YAT4YAT4cAUokA' \
                       'T4UAT4YAUIUAT4UAT4YAUIUAT4UAUIoAT4YAT4UAT4UAT4UAT4UAUIUAT4UAT4YAT4UAUYYAT4YAUYUAT4UAT4YAT4U' \
                       'AUoUAT4UAT4UAUIYAT4YAUIcAYokAT4UAT4UA65kA0ZYAu5PCXoiOAAAAx3RSTlMA+nO6AgG5BP799i9wShAL9/uVzN' \
                       'rxAw6JFLv08EmWKLyPmhI/x88+ccjz4WjtmU1F76VEoFbXGdKMrh71+K0qoZODIMuzSAoXni0H4HnjfnccQwXDjT0Gi' \
                       '/wa5zSCaSvBsWMPb9EnLMoxe3hHOSG+Ilh/S1BnzvJULjimCayy6UAwG1VPta91UVLNgJvZCNBcRuVsPIbb37BllNjC' \
                       'fTLsbrjukKejYCVtqb/5aqiXI9W0tnad4utdt2HEa1ro5EHWpBOBYg3JeEoS2QAAA5lJREFUGBmtwQN7Y0sABuAvbZK' \
                       'T1Ha3tt2ubdu2vXu517Zt27a+TH/VbXgmaTIz53nyvtDaV1+JdDrxHVvzkD43D5BsyUe6bKxmUP0qJNM2Y/Pxud9bMH' \
                       'd5DsNmlmGa/E8ZsvgumHqikFHzPUhgVTGipBxmun20LUCCw4zZAiPtjPMs4r3MmGvbYGA9E6yD7CwlN0FvPac5CckDl' \
                       'LRBK4dJPAxbDiXvQ+c9H5OZQMwW2lZDJ7eQyQ1vQsR+2j6ARnYnU6nKQ8gdtA1Co6mLqXX1AXBf72GUa6EbGmuotCvT' \
                       'u4tRBcOfQ+sATQ2cqoSBF2go6xiMtNNQA8zkH6GZ0zBU/mLFYEcBtbbCiVtrM6lxEA6NVFOpHk6d9lPpbjjVSKWCvXB' \
                       'oHzUyFyG1vuFzM3Yi3rfUqL5/E5Jzv8spz+chjpdao7VIag9D3kAcLw14szHd7h0MGfVAVkITvj/PI4H1OCNyITlPQ6' \
                       '7eDYjTzqirFmy9NDZnwRhsy0sZsw4xzX46kDVRiahHaPNleBD2+wDJSSGZpNK1v8sRstJP2StDFoDsXh+niIBEUOM/h' \
                       'NzLBDWtD/UwTAQkghr/IGgrFURAIqg2WoagzVQQAYmg2nUELaWKCEgEla56EFRMFRGQCCpdQtBlKomARFClA0GecSqJ' \
                       'gERQZSOCLlBNBCSCCucQZJVQTQQkggpnEHSFGiIgEQx76nhrDRPch5BiaoiARHCKv6gOgNW/n7LCOoT8e7GUSpNCMkm' \
                       'y5xmEeTJ8tBUh6q+K2XTA34yYPYx5qxK25Q0FNFYEmzXOqJ8RZ2eRi2Z8syDpY8RiNxIsmu+niSOQuR9liCsb0638ig' \
                       'a+RJwMhpxCUv1fUGsJ4jSt5ZRGpGBldFKjBPHOznjzmyGkNusHahyFQ1eyqPQZnHqQSv4n4VQVlTovwKGD1Mi89Bica' \
                       'KZWVsstFd35MLSUZoqXwcxLNJQBI699TENzYWDs4mya+hBadYOFjFp9YMlaKuVAw5rYwagb93gA1HYxtefKoeaeyRjf' \
                       'GYTkeZlK6TxofE2bFxHWCibn6oeG+zfatiOmgsn4foHOPEqehu1VJrEXWkOU5EKyhtPkQO9OSjZAdpIJDsOAVcOYccR' \
                       'bSJnvExjZzphuJGigzf8jzBz6gxG3u5HAs4JRrhGYGmthkK9xFaYpu41hWbkwVzbyTsdHb59AMtsyGVTahnRZ9hPJ13' \
                       'cjfQ4V89djSKcm71Ho/A9KDXs8/9v7cAAAAABJRU5ErkJggg=='
DEFAULT_DBOT_IMAGE_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAEIAAABlCAYAAAD5/TVmAAAfJElEQVR4nNWceZxUxbX4v1X39jLdPQszI8uwCI' \
                            'iAiEuICyIxqHHFLT41MeLPZ4zRaDT5PWPM+vxEf3n56UtiTJTkPde4xaiJcU/QoA9QEYEgAUTWYWT2raf3vkvV' \
                            '+6N7hu6e7p4ehLzf73w+d+7tulV1zzl16tSpc06N4H8Ifrnq5LmNoWm/agwcvlBpu6s9uvFnu7bv/eWdl693Ku' \
                            'xCAupA4WMeqI5GA/euXFBvmOLJOv+hR0+qOR5XpZu6Ex/9+/hpgQ7gqQq7OWBMgH2MkKNsp9g3IsXu5dpgmPIE' \
                            'BHObB1awN7IGhYurLAlcdfQpDU9vXNE7rE2J36XKRg2DjNgf7qoR7qXaZJDWoNHYOjn0Umshx4zzFvZf7rlcGQ' \
                            'wfpJLlMuc6mJA3qgMRuTaVklu1zhRoIG0J1dsnf/dfz7YrRia8sM9SUGpwhpUPcuSAzrcyCAHI75+1oqerR17V' \
                            '2Wmu7+w06Wg3+7q6zR81f5h8IgevQig2JQ4YiAPZWQ6U0+gSUNIQnH/pRQu0I1cieKx2XvM1j393nSrTvpROGg' \
                            '0OuWV5/ZgMV0aVdDwSMmUQEJx73ue9SjPFSciZ2feNyc2zjv7hvQt7phzu6/jq4n9XWutCvEaL20hMy50e8mBJ' \
                            'RB48818/lEJ46l//w+7T2ppjF0opFpmGUaM1Xsu2vYYhldfjsTTaCtR5wtNm1q499jMT/hKq8fzZVXrvOUfeer' \
                            'CnbtGpMaKGLVM3t5zDZjep//zT/55umsaN776x97J3l7VO8nk8eDyZxUophe24SCnxmAYAWoNl20yaEeSCq2aF' \
                            'DUO8nHK496G7X1z/zMNvFVtOC3HMfTfSkj5U76BJxPKtPw0ZprwBuAUY+9rvd7Dtb/1U+X0AaK3RQM4fhNiHjv' \
                            'QqvnzbMRimBIi5micsl9u/uvj/drXs7Drg+BqD3yUjHTr7rIvULVc+2JZQTRXLNt09QxriceA6IAjQNDVIf6SH' \
                            'gf40ibhD2rJJW1b2nrks28bVDrWTExy32EtNvR9T+BBCeKXgOI9k8TmXL9y47e979rbu6RFl8ClGR265yMUZDv' \
                            'CqUVcf4oX37jgWwbPADABXp+lPtRBO7SHtxEglINLhIdZjkopKXFsgDfAEFKEGh5pxDlW1LtLQCGHgM0KM8U2l' \
                            'zj8ZQ3gB+lKuuObt19a9eMc3nzhgukOwb/7kzjdyymSJ58G6CmDM4Yfy7Ms3H+sxxAvAFKVd+tPN9CS2Y6tEzu' \
                            'eKDeIIGGrwGAHGVs2mzj8ZgRGxXX3Vv97y+xffeXlNLm4j0VBYd+h+oCRCLt/287FC8rqEuZYboy22gZjTndF+' \
                            'BwwE1d5xNAWPxWMEejSctWjGv6w/ED3LgudC7TqS+S0BXlhzh6mFuFfC3Jjdxa6BlcTsroqYMDo2aaJWB7sHVh' \
                            'C3exq15qFn199VP6ouioMcyWgZyZBRk2dNpHpM9UWm0BdFrQ72RtfgqGSZJvmwPyJpqQQfR98j4XQd3VDtufWG' \
                            'X3zlE++XKsGjrCm7fPvP66TgvYTdPbMlshpX2wXdlx5z1xa4lkApgZAa06sxPHrEdoNgCi+Tak6K+Y0xJ54+81' \
                            'tbRsC5UL/lvSvmmClmrpYmRotLlI7PbI2tL2ACZPfaaMCKSyJdHuLdHhJ9XpIDHpykiXYlOssIYSo8VQ6BeotA' \
                            'g0XtBItQo4Nh6qJD5miL9tj60PjQ/G8s/sap171y75uDr0azVQdQn0hZ/nHt3f4xteL9j6PvzY1aHRnSlSDaZd' \
                            'LX4ife4yUdNUlliZbCQFaonzWgXAWGQ/CQNKGxaYINNtXjLKoPsRE5EyHoGReu9cw55vNH39myv7TkeqhGvSaH' \
                            'qj0nDKT3zIxanQC4jmDrX2vo3VaLgSfPUjSNUr0UBwEYhgS8pLq9pLqr6dYahUPtoQPMOWsA05eZPgmnuy7lbj' \
                            'gPWDpaGgah3LwpC6dedAKC+IXdyQ+9g/O5fbOfrs21mMKLEAIpJE0TJuD3+ZgwYQJer5cJE8YTCARobGwY1mcw' \
                            'GKShoYG6ujpqaqqprx9DKBRi3Lix+Hw+hBAYwkP/zjp2vRccaqe1wlX9n//VOwv32wdbbJxKmdJ5cM9TX/dH1c' \
                            '7bY1bnxMGyPeuDWP2hIfGvravlttu+xcBAhGuv/TItLR9zw9euI5VOcc7ZZ/HOu6vz+ly06BROP/1UZhw2nYkT' \
                            'J3LCCcfRUF/PxRdfRE9PLx0dmeknpcCyHCYemcqdInVC8PCrD7bER0PHYL1iHKzI5+Cae+qj6dY5ud8SEhKpFB' \
                            '7TxGMaRAYiPPrbx2lubmZgYICdu3bz8CO/paO9g927m4d9eN26v7Fjx05s28a2Hfw+L4lkkm3bd9Da2obWGqU1' \
                            'tu0gVebLORqnXmvmAIM7skqkvKTPMve5cCueB12JrVNtNxHKRaV2go2rFKm0RTSeBMPg8su/wOEzZ3LllVcwaf' \
                            'Ikliy5nLlHHcn55y1GKZ25tEZrzbHHHs2555zNaact4sQTj+dznzudeZ/6FF/4wqVMmjSJWCJJLJ4klbaonWAj' \
                            'jfwBF4KjKyA+F4Zo3O9V4/7VC/8ZeCS3zE5L1j1TR9/HQ55ovF4vjmNjmia27eAxTVzlIqWBbduIQZNBgJSZVU' \
                            'XrzDZdCoHSGiklruugVIbwuiabT18SxhdyC9FaeuP8VTfuDz2jUS55U0Qpxmfs0kFeajw+xbyLwzSvC9K900u0' \
                            'y4NlWQBYVsbGsOzM3c0SNWSFa3BdF3eINoFLxn5wXRchINTgMGFOikM/ncAbGC75WjN+FPTkwWgYkfdl2xGmz6' \
                            'sp1EfeoGLmKVFmnCywEpKBdg/hVg8DHR7ivQZOWuLYZbYhAgxDY/oUwQaH2iabugk2NeMc/NVu1vIsDrYr9nvV' \
                            '2G+JSKSElWFEicqGxl/t4q92GTczBWRM6lTUIBWRmXtM4loCrQXS1Hj9Cl9IUVXrUlXrFh31cmBbIlUC55Hu+y' \
                            '8RkZjsqAlqDKPy/aPh0QTrHYIHYr9YCBoicVnow6s4GicL7oXPJSGRFJv6I/LAepeLqW5R/F1h1WhCEomLv+UU' \
                            'lVsRh7kbii2VFRHnOHprd7+xuqPHxLLF6PwvpeoWK9fF3w36fB1X0Bs2aOs2O1yHZTlViklBSQnJdd7qIs+5kF' \
                            'dn7Z+areM/P219Mi0WhKPGuERS4DgC0wRjpH2FKL9u9+/1EqgpPR6uKwhHJT1hg64+k2hctmnN9csf2Pp+z55Y' \
                            'btVcJ26ek7mQtkriGmXfXf/bRfWGKc8DLgUW+H267tAJjszTHZW6KrP1/vZ8HUeeHcFbpYa900Brp6kiMRkDNq' \
                            'D1C66jn3vlZxtbPv57XyGugzCSW2GIEfu1+8wFf8jDl3+9sEZIcWsoqH4wcayDUUTbuLZACJDmcM7EekxaN1Xx' \
                            '8YYq6qdYzD41RnCMs292aOjqM+gbMJ5zLHXT2uebu9a+0FzMcVsuIDUIeY7ekSzLUe9Or390UcDwykdCVeqypr' \
                            'EuZsGq4tqCPesC2ElJVW3GekpGDAbaTFJRg4apFlM+lcD0aYQAf42bZYKgs0fSHzXWa83i+69Y3lEB7qUidlDA' \
                            'rIMS6brxydNrQD/i9eiLxze6hIrYA4mwwUCbBzslMbyaQJ1D7XinqKSk0oKOHoNESq4XcOl9VyzfdaBxrkQiRh' \
                            't6B+D6RxfVSI+8yxB8pTqkzMY6l3IGWDFwHEHvgCQcNXBdlmnNNUuXLN87ii4qxv+gRsOvvn+hDNR5nwcuEEAw' \
                            'oKgJKQJ+jWnofRoqe9c6Q3zKEkTjkkhcojJkNGulj1h65ZuFluMBg9z8iJH0gATUuKY6AsEg/T1JtMpsijweL+' \
                            'lUUnp9fqVcl2QqIQH++L3NasnSealMthTEEpJYQmJIME2NaYCUGgEolbEJHFfgusMWGWfDy61OIBCUpsej6sbU' \
                            '093ZIaVhgNZUBYIKIJGIy0DIq0I1Hpq3d5ZzQg9TqBVLxILTZ/OjpV86VsN16aTb2NueYteWCHs+itLblUKXYG' \
                            'P1NGt+3WHuJE+1izZcEBothnJGhoMGtERogVASN2EQbTFi/Vt8y3SJwaqt9zJ5RojD5tYyblIVVSEjIYR4cs+O' \
                            '7je+svhXFSn63OVzEIrFOHlt8+31HtNYqWFObgfJmEPn3iQ7N0do3hohGi506YPhgcAYQfV4CDSA4dMZGREFbn' \
                            'otEFqgHEGyH2IdgniPxk4P1y3+gMGUw6s5bG4NTVODhGo9iHzGhrXSnznziNu3UHwZzdt8lUovHMZFw5RzbJWe' \
                            'o7QNSKQwMIRJVchk6uxqps6uRrlN9HSk+Hh7jLbmBL2dSRJRF9tyiXZpol0Zd543KPAFJaZ/nxWqXHAssOKadE' \
                            'xndIMenHqSqpBJXaOXCYcGmDwjxPgpAUzPvvHTKBxlo7WLRiGEUWcI3+eATcO4WMTELmlQ/X7Vt80xjaF5oENS' \
                            'SAbSbSf0pLb9xFFW1kNtYgoffrOWgFlPlaceU2Q9U1kr0LYU/R02nS020X6bRNwmnXKwLBfXVrhKZ/QMmSQRaQ' \
                            'gMQ+D1Gfj8JlUBD8EaD2Mne2ho8uAP5NvuSjsknTAJp4+UE8ZWSZR20FohhUGtb/KjDb4Zj4uMVnYi4eT6fzrx' \
                            'JzGK2BRFGbHwjCO4/b7L7wVuGKwct3toja0vsTMVCCQ+M0TArMdv1uEzghjCixAGWgmSEYj3a5w0gytB3kZN5D' \
                            'wIAaYXArUQqBNIQ6NRuNrCUcks8f2knIGsBBRflhuqZqgG//QhvgEr+ntjZ1224O5h+d5FleUb2+7wJ51Ie3+q' \
                            'uU7pTBtXWaTcSAk2DN9KSGFgykzGi8eowpR+DLwo24OTMnFSEmXLTNwTQGoMU2P4XDx+F+m1UcLCUWlslcBRaR' \
                            'yVwtWV5qyDRwbwGoEsjpIaX5MTNA85/szZt2+gYPCLOmYc1x3fEd8UsNxYRRumYq+VdrHcOBZxGMI905kwBVST' \
                            '3USJbKnORsZ0ZgVKleo5r6uy5bZK5CSpQMLpl03BY6YAGyhQBUUZ0Z3cguXGS1NZMVaFkHXYDm4j9/3KPI3GqT' \
                            'Ean0YWlHboSnxYdHoXLYxY7XJ0KRwHMivmYILGcmNFcymKSkRPv6EaxwyLGewXKAXhqIHlsF/8Mk2oq1b7drH7' \
                            'kYaVCylLOhQxD4oyorNXquqgGvUmqRA00Nc5Bk/HUdS4gUwcpwwhWmRsrAxkKrrSpnfMhxxyaFvGsfgJUFJK0N' \
                            '5tOFQqEckOs6evRlsTxjreYu8r/rBjEOo8Dk96eOR7NODrCeGOex0ZSIxcuQxEYlL17fHGKOPFzoOuFbXz2z/y' \
                            '+ePJT5SWhFRePG4wr0wAUsqilxDFtz6G8mEW9DNasB1Be4vH7FpVc+ERRx49skScdsa5Eri2f3OV+fF4m8mTHI' \
                            'JVFe1bhkExsqprazj99FMzcySbhjw4W1LJFBs/2EhbW3tFfZcJluW9S1uC1g6T7o1VaJdLpk+fedeHmzfmxUCG' \
                            'McLvr5oKfC7db9K1NogmTm2tor7WxevJ+hBG5cUQeYh5PB4mTsqkVOzd28qkSRPzak+aNJGnf/cMsVgsJ6o6/I' \
                            'PlVIUmk8JkuxCOSsIDBr1bqoi3+ACmIDgTeCK3TS4jMk5MIS4G0YjWxHb7cBMS+4REVzgmGz2Glg11GaaMQHte' \
                            '8kIe0tkfWmveWfUuU6cdimmaGIbBUUfPxV/lp2liE9s+2lac2JFWDZHxe3R0G9iOwHVER//6QH10t8+b0+7aw2' \
                            'bMemrnjo8gJz9iENRZ514kgatyv5Ts9IR71gTOR3OF7Yg/JdPCKs+FHGKVxnGc/L2AGLwJUqkka957n3feeZeV' \
                            'K1eRTqeBbO5UDhMzKQEqr+9y37YsoSxbrNCaG52YPD66y7e2oN38WUfMnU0pE9s0zYXk+BuyzH9r08oda//wwO' \
                            'Y1wNPf/uOiD6CyhIy0bfPumvepMuqoq62htqYGf5U/i6/OSwkYjFwBpFJpenr7iESihCMRBiIDfHpKlDG1lXwV' \
                            'bJuIcvXnf/2/3gwDavEFlzwkYEEOL7xCiKura2pvjUYGIDfP8vBZcyRwJTlSkm34yEdbNw9xznZEs1IcLStYUD' \
                            'IuOEVfNExfOAzAQGxfJGrdBxvp7c2c8dQarvrnJVRRxa7mPazf8PchSRKjXLzStgj37IlF2DfiL2roA3LDzxd8' \
                            '5rOf+8mrL/2hD1BDnzh81hFNwLkFfTa7jvNGboGrxBbLrjxXshCUUkPLZDyRJBKNEYnGiMZiQ3sNpXXJrfVIml' \
                            'opsGyx7dkfvj80eLt3busD/lhQdYZALBr8McQIgTgThmWcPLN50wd5nmPX5e9pqzJGFNNrSmni8TiJRAKt8pfl' \
                            '/D1XqW+UVxKWLXBdsYmc+b9l80YF/A6w9p1ZERLBFYN1TICjjvm0BK4t6DMG+smPW3YXGhHrEylp1VariqzOQn' \
                            'I6elq49e4vAqDEWM44/VQgk2sVDGZ8BxnJyCW4crs6kRK4ircp8Lsq5b4jpbEJ9Lyc6uede/7Fk1596Y97TYBz' \
                            'zz5nXjqdPq6qqor+cJi2jk5c111r286Wgu/gOrotmRbNSjFzJD0xJN45ouGrdpl7bhg0tP/1SG6+6Wv5bbRmz5' \
                            '7CTOLKp2IiJRMU8Te89vLzqcUXXPJ7r9czb/LEiYypqyWVSnsj0egXJzZN/Kn5y1/ctyAUCj0//bBpZqAqwK7d' \
                            'u9m2bTubPvzo8WeefmyYO8hJu5GUx1ydtsTMKv/IHpvc1QAyTtpE2AAtSKdtOjo7h+qm02lefW0ZO3ftrojwQl' \
                            'CuIJkSW9C6aFx0+qFTXp0wftxddbW1fGresWitaWtt++HcI2ZvMoGfjJ8wbmwgECAWjTEQHqCutpaTTzy+7pmn' \
                            'HxvW2YNfXcGNT572eiQul1T53bIyIaQodLGT6DNZ9WBjFvG93PzNbw+9cxwH2x4eDhAVWrPxpMB2xFvP3b52UK' \
                            '/lue0PP2z6BZDJ0uvq7GLc+HFMaJpQ09fXf6cJLNi9czctzS3ZND6R/bg4Gfh5sQ9qxRvRuAwfMkbVS1laKgJB' \
                            'L7VjgnTFcv8jADhDylaRTI58yCUQ9FFXFwDK23LhmLSAlzp3RkplxnwaMh7z1r2ttLa2IRDYjj3PBPpcpcZqYN' \
                            'r0aQhgx46dAD2UCKK+8ZstHWfeOGdFLCEuqgmVZoQSac665HBWvthBuC9esl45qAr4OPmsQ3FqVmCVsezTliCZ' \
                            'lM3JAWtNTnFhIKcNoLa2lslTJrFj+04SiQRAmwn8BviB1lp2dXaRTCZxlcK27ScpEWLb9nYHZ9ww56H+iHFBdV' \
                            'DJErtntFbEqt/lgutOwisqNAsLwNFJ2hNrSVjlGdkfMXAVjz98w6pBsckdxOzKoR8A/dVwOOy1bXswGdYB7jGB' \
                            'u2Kx+HSvz7tERSLEE0l27m6ms7vbX/CtPOmwU+6KhDC2xJJybnWZfMi0E2VHOJvj9QndbKXAsgUDURlWrn6K4d' \
                            'MBskvpsjff6jukoYHpU6dgWRaWbRMeGFjm93iWmjd/8+uJ8y685H7TNL8kpZSO4+Jm8oDPgWFZakPMeO/ZXZGF' \
                            'Vx7+H919xr1Bv5bldMUQHCQfb3efgat4bqAr2VyiSibiLcRpPX193r5wGENKlNa4rvvCKy8+l5IAqVRqvW07Pe' \
                            'm0NcgEgNPOPPeCQqkY4vIHf/4YAU+k02JHX0T+j/mxYwlJNC4jwD1PfWt1SdE878JLARYD2cP5Dq7rOsAbkBWZ' \
                            'N/7yskX+6APMMA3PHMrAg9evDGu4szdsqFT6H/IfGPLAcTIpRUrz4Pt/2l1o/MmCqxGYX1Bn657mXc0UnPt8pa' \
                            'BSQAhx2qFTp1MKUlEbrXjOdVnW1mViO/84ZigF7T0Gli22oblrzbPDjDCVd2mOA5oK6ry8aeN6Re7uU2u9msyS' \
                            'mQvnT51+eNl87aVXLk9pzS1pS3S0dZk5xwwOHmgNnb0m0bhMALe8es/Gsv9HYcbMI6RGn0++/8VB69cGfwwxwr' \
                            'LSe4G1BX3MD4WqC7k4DJYuWb4FuCmeFKm9nQdXMpSCjh6TbB74XS0bel/eva5w/PJh1uw5fuC8guJdSquNgz+G' \
                            'Eg527dzGzFlzQsB5vpBi1skORyzwGdNP7p944U1Nm/o70z17t5Vey2eePG6rP+RxbEcsSiSl9Ps0ngP8f89sR9' \
                            'DW5SESkwp4zEo43/vdd9aUDI9PnhXixy8d3zTtuNT3m6YFzm6YLIj1u1iZMMWz772z8vlkMqEh/5SfnjlrTlug' \
                            'zr1x8TWHmGcsXMysqcfgeHuPjNvdXzrmlMa3XnmwpbXUR/++bK844rMT3vYFTMtxxSkDsUwujN+ri2bgloNCeV' \
                            'IKBqKS1k6TlCUV8Ggyat/80HUrcyM+w/LJ/8+fjp9imOJNr8+z+LNHLuGo2ccwda7J7h0dKhkR3/lgw9rBfM38' \
                            'jfSWTR+0zT0nsmbSxIko7dIe+4C+5A6Aeo2+/bq7jyhHknrsG++ovr3xnwJf05pwd5/B7lYP3WFjVNNlkBpXZZ' \
                            'LP97R5aO8xcVxhgb7bsdRND1+/MlbQrPCEgTQ84hvADKVsdvYvJ2H3cUh9E8ec5XSh9arc+sOwu3/1wpXAQoHA' \
                            'kD5M6SXlRFCKloGImPWDs1dWlOt4w5OnHi0Q9wKnAFIICPgVwSpNZtpopAQhMn5/rUFpcBxIW5J4UhBPDuVZAm' \
                            'xCc+vqZ3ctW5fJvx4J5C/f+cybhtSnmNKHKf2knQgI0Fp33Th/1bjcyoN5lrkdtwEY0sOcxvOJWd3sCr9Ff8To' \
                            '273Drjhd5eHrV228+r6Tz5emvAi4TWvmxJNSxrObTSkyTlmBzka9MozYR/iQPb4XuFcp/ejTt73X099WcfxT9f' \
                            'TLjrH1LkFPI7MazmZb7zLC6Y8BhvkrhkvEuwsXIXgJRMhjVJG2k4SjkmRa/GLiWOevwK7WHbGt/7ZkQ8VxwCvv' \
                            'OckMNfoXSCkuBRYAU4A6hkfaFBAhMxhr0foP6aT7xoPXrqiY+ruXzfcGq82FCOb1R+RE1xXfHFOj8Hl8KG2jtW' \
                            'tpzdduPGnVw2UZcdsjx8jGqbUXJNPix0oz22tq6fNqfD5tCfACYeC+dMK9819Oe3fkYE8BXPfIIr/hkeOBsULQ' \
                            'iBAhAVKjEyh6gC7l6o7lD3wY+2jVSAn4+fCrt0+ukYb4GbAE8EMmm9eyIZWWKE2L36vvchOpB7933hqLkTJv/d' \
                            'Uefrps/iUC/R8ISh1Fe1kprr3trNUdiWjlCV45sL9nRIa1mzN/DF//xZHTNTxORuLQSmSO7ezbDFpa892l39r6' \
                            '8y1vD7c7ijLi3hULAqZXbgeaNBCNSQZiEinhkDGZYHAW1iqlr7hpwdvbDgRB+9vuvtULjxPwJDATMi67rr6MlV' \
                            'sdVBxSr5CZDJSeVMKddstp7xauOMXzI0yvnAmMBegfMGjtMnuicXnHQERe3dJuPpNIycGV4zgpxV/vX71w0c+X' \
                            'nzTaZIr9PTE01O4HT31K3v/uwosE/IUsEyJx2dfaaX4/kRRHWpY4ozdsrO/uG0Ktxuc3phTrtBTyocGH/ohMob' \
                            'n21Z9t/NH9S5Y/Gh1wr+jsNa5LpsWgApsE/MFXZXxx/uKxlTCj1JHDUu+GHU0EuPSW6XLCtODXETxJNpQXT4qe' \
                            '7j7jn9p2xv5t6ZLlW39z9VtvaM3VkZgRzmlbGI+RpZAhd8a4LpscS728e32PAnjw2hXO3u2Jx7r7jOssWwyKWD' \
                            '2Ch6784czrb77vqJGYUcyDVO7dsDzxxiY/iy5tugzB7UAAIG2Jrp5+4wvP3vHBW89+/30A5dqKrSvaN2n0+pwz' \
                            '7EXzzouOjhAMGU1Ssuk3V7+Vpw2f/s57NG+NPxWJyRuVIgFsBX6ilX6jfVfJ/Ujht8pJxOBzbirg0LuethR7Nk' \
                            'efA04H7lZabIgl5BXP//TDt3JO+kmA5f/5oTIkO7IJGwpEqti3i2bna62HGGEaDFMsAL//7vvqsjvmPXHiZ4Nr' \
                            'TOnufeyO7Yl1r3eXm/elXOyFdQaVYd4pvML6d1/zgQNsWHztlI0nXdD0o2fuaUlsf6cT8pWpBJTHHKRHozXFLO' \
                            'Oi/34J0FaGe+D16pK2wjP/ul49k5GGSqDcMcTcOhTUKatUX3mgRb3yQEuuwTWsnS+HBq1VMXpUUUZohTOYk+Av' \
                            'w4j9hEqk5oBClW+IBoUWRRNOSynLIZ0Q8Kv9i8wMh4NCZCVQ5dPbyYbJhCyOR3FGZBRsDFjqNfVvDg56ZeGTJX' \
                            'gWQH974gngLGCNLmU7FcVCEtGaM1a/0rX+8Tv3x2j8xHBApedHl61zgLfufn3+GdFee7/6LjcyRQ2d/axfaqks' \
                            'VVbYxyd99/80/H+BZCGMBumi5yUq6G+0EliufaEE/sNgJBEv1WY0v0eLT959NAGIYYbQxIkTefXPf5ZVPr/0+r' \
                            'ym3+evkdJodJVbL6WsEUKEyOwFAhq8IuMsMQFPtgszeznsO/llZ58tMie7EkBCaRVDE9FKhTX0KNcNt7a1OR3t' \
                            '7eorX7lGdXd3V4x3MRCUMGFHgvnz5/PiSy+fCdxEJlt3fJboAxb+H6GbFBmX3jbg12MPaXyx4H0xBhRat0N3s0' \
                            'jliiBUXY1lWWs9Hs+PgZlCMAXNBIRoRFMH1JDZzgeyl5/MFthk+FY4FyyyEqEzxKbI2DQxMv7MMJnQZDvovVqz' \
                            'A1HUzK9kdzt0/2+exnQr4g2hrAAAAABJRU5ErkJggg=='
# file types regexes
PIPFILE_REGEX = r'.*/Pipfile(\.lock)?'
TEST_DATA_REGEX = r'.*test_data.*'
TEST_FILES_REGEX = r'.*test_files.*'
DOCS_REGEX = r'.*docs.*'
IMAGE_REGEX = r'.*\.png$'
DESCRIPTION_REGEX = r'.*\.md'
SCHEMA_REGEX = 'Tests/schemas/.*.yml'
CONF_PATH = 'Tests/conf.json'

SCRIPT_TYPE_REGEX = '.*script-.*.yml'
SCRIPT_PY_REGEX = r'{}{}/([^\\/]+)/\1.py$'.format(CAN_START_WITH_DOT_SLASH, SCRIPTS_DIR)
SCRIPT_TEST_PY_REGEX = r'{}{}/([^\\/]+)/\1_test.py$'.format(CAN_START_WITH_DOT_SLASH, SCRIPTS_DIR)
SCRIPT_JS_REGEX = r'{}{}/([^\\/]+)/\1.js$'.format(CAN_START_WITH_DOT_SLASH, SCRIPTS_DIR)
SCRIPT_PS_REGEX = r'{}{}/([^\\/]+)/\1.ps1$'.format(CAN_START_WITH_DOT_SLASH, SCRIPTS_DIR)
SCRIPT_YML_REGEX = r'{}{}/([^\\/]+)/([^\\/]+).yml$'.format(CAN_START_WITH_DOT_SLASH, SCRIPTS_DIR)
TEST_SCRIPT_REGEX = r'{}{}.*script-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, TEST_PLAYBOOKS_DIR)
SCRIPT_REGEX = r'{}{}/(script-[^\\/]+)\.yml$'.format(CAN_START_WITH_DOT_SLASH, SCRIPTS_DIR)

INTEGRATION_PY_REGEX = r'{}{}/([^\\/]+)/\1.py$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)
INTEGRATION_TEST_PY_REGEX = r'{}{}/([^\\/]+)/\1_test.py$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)
INTEGRATION_JS_REGEX = r'{}{}/([^\\/]+)/\1.js$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)
INTEGRATION_PS_REGEX = r'{}{}/([^\\/]+)/\1.ps1$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)
INTEGRATION_YML_REGEX = r'{}{}/([^\\/]+)/([^\\/]+).yml$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)
INTEGRATION_REGEX = r'{}{}/(integration-[^\\/]+)\.yml$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)
INTEGRATION_README_REGEX = r'{}{}/([^\\/]+)/README.md$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)
INTEGRATION_OLD_README_REGEX = r'{}{}/integration-([^\\/]+_README.md)$'.format(CAN_START_WITH_DOT_SLASH,
                                                                               INTEGRATIONS_DIR)

INTEGRATION_CHANGELOG_REGEX = r'{}{}/([^\\/]+)/CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, INTEGRATIONS_DIR)

PACKS_DIR_REGEX = r'^{}{}/'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR)
PACKS_INTEGRATION_JS_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/\2\.js'.format(
    CAN_START_WITH_DOT_SLASH, PACKS_DIR, INTEGRATIONS_DIR)
PACKS_SCRIPT_JS_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/\2\.js'.format(
    CAN_START_WITH_DOT_SLASH, PACKS_DIR, SCRIPTS_DIR)
PACKS_INTEGRATION_PY_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/\2\.py'.format(
    CAN_START_WITH_DOT_SLASH, PACKS_DIR, INTEGRATIONS_DIR)
PACKS_INTEGRATION_TEST_PY_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/\2_test\.py'.format(
    CAN_START_WITH_DOT_SLASH, PACKS_DIR, INTEGRATIONS_DIR)
PACKS_INTEGRATION_YML_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/([^.]+)\.yml'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                             INTEGRATIONS_DIR)
PACKS_INTEGRATION_REGEX = r'{}{}/([^/]+)/{}/([^/]+)\.yml$'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, INTEGRATIONS_DIR)
PACKS_SCRIPT_NON_SPLIT_YML_REGEX = r'{}{}/([^/]+)/{}/script-([^/]+)\.yml'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                                 SCRIPTS_DIR)
PACKS_SCRIPT_YML_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/\2\.yml'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, SCRIPTS_DIR)
PACKS_SCRIPT_PY_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/\2\.py'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, SCRIPTS_DIR)
PACKS_SCRIPT_TEST_PY_REGEX = r'{}{}/([^/]+)/{}/([^/]+)/\2_test\.py'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                           SCRIPTS_DIR)
PACKS_PLAYBOOK_YML_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.yml'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, PLAYBOOKS_DIR)
PACKS_TEST_PLAYBOOKS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.yml'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                    TEST_PLAYBOOKS_DIR)
PACKS_CLASSIFIERS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, CLASSIFIERS_DIR)
PACKS_DASHBOARDS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, DASHBOARDS_DIR)
PACKS_INCIDENT_TYPES_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                     INCIDENT_TYPES_DIR)
PACKS_INCIDENT_FIELDS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                      INCIDENT_FIELDS_DIR)
PACKS_INDICATOR_FIELDS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                       INDICATOR_FIELDS_DIR)
PACKS_INDICATOR_TYPES_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                      INDICATOR_TYPES_DIR)
PACKS_INDICATOR_TYPES_REPUTATIONS_REGEX = r'{}{}/([^/]+)/{}/reputations.json'.format(CAN_START_WITH_DOT_SLASH,
                                                                                     PACKS_DIR,
                                                                                     INDICATOR_TYPES_DIR)
PACKS_LAYOUTS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, LAYOUTS_DIR)
PACKS_WIDGETS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, WIDGETS_DIR)
PACKS_REPORTS_REGEX = r'{}/([^/]+)/{}/([^.]+)\.json'.format(PACKS_DIR, REPORTS_DIR)
PACKS_CHANGELOG_REGEX = r'{}{}/([^/]+)/CHANGELOG\.md$'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR)
PACKS_RELEASE_NOTES_REGEX = r'{}{}/([^/]+)/{}/([^/]+)\.md$'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                   RELEASE_NOTES_DIR)
PACKS_README_REGEX = r'{}{}/([^/]+)/README\.md'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR)
PACKS_README_REGEX_INNER = r'{}{}/([^/]+)/([^/]+)/([^/]+)/README\.md'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR)

PACKS_PACKAGE_META_REGEX = r'{}{}/([^/]+)/package-meta\.json'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR)

BETA_SCRIPT_REGEX = r'{}{}/(script-[^\\/]+)\.yml$'.format(CAN_START_WITH_DOT_SLASH, BETA_INTEGRATIONS_DIR)
BETA_INTEGRATION_REGEX = r'{}{}/(integration-[^\\/]+)\.yml$'.format(CAN_START_WITH_DOT_SLASH, BETA_INTEGRATIONS_DIR)
BETA_INTEGRATION_YML_REGEX = r'{}{}/([^\\/]+)/\1.yml$'.format(CAN_START_WITH_DOT_SLASH, BETA_INTEGRATIONS_DIR)
BETA_PLAYBOOK_REGEX = r'{}{}.*playbook-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, BETA_INTEGRATIONS_DIR)

PLAYBOOK_REGEX = r'{}(?!Test){}/playbook-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, PLAYBOOKS_DIR)
PLAYBOOK_CHANGELOG_REGEX = r'{}(?!Test){}/*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, PLAYBOOKS_DIR)

TEST_PLAYBOOK_REGEX = r'{}{}/playbook-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, TEST_PLAYBOOKS_DIR)
TEST_NOT_PLAYBOOK_REGEX = r'{}{}/(?!playbook).*-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, TEST_PLAYBOOKS_DIR)

INCIDENT_TYPE_REGEX = r'{}{}/incidenttype-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, INCIDENT_TYPES_DIR)
INCIDENT_TYPE_CHANGELOG_REGEX = r'{}{}/*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, INCIDENT_TYPES_DIR)

INDICATOR_FIELDS_REGEX = r'{}{}/incidentfield-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, INDICATOR_FIELDS_DIR)
INDICATOR_FIELD_CHANGELOG_REGEX = r'{}{}/*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, INDICATOR_FIELDS_DIR)
INCIDENT_FIELD_REGEX = r'{}{}/incidentfield-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, INCIDENT_FIELDS_DIR)
INCIDENT_FIELD_CHANGELOG_REGEX = r'{}{}/*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, INCIDENT_FIELDS_DIR)

WIDGETS_REGEX = r'{}{}/widget-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, WIDGETS_DIR)
WIDGETS_CHANGELOG_REGEX = r'{}{}/*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, WIDGETS_DIR)

DASHBOARD_REGEX = r'{}{}.*dashboard-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, DASHBOARDS_DIR)
DASHBOARD_CHANGELOG_REGEX = r'{}{}.*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, DASHBOARD_REGEX)

CONNECTIONS_REGEX = r'{}{}.*canvas-context-connections.*\.json$'.format(CAN_START_WITH_DOT_SLASH, CONNECTIONS_DIR)

CLASSIFIER_REGEX = r'{}{}.*classifier-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, CLASSIFIERS_DIR)
CLASSIFIER_CHANGELOG_REGEX = r'{}{}.*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, CLASSIFIERS_DIR)

LAYOUT_REGEX = r'{}{}.*layout-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, LAYOUTS_DIR)
LAYOUT_CHANGELOG_REGEX = r'{}{}.*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, LAYOUTS_DIR)

REPORT_REGEX = r'{}{}.*report-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, REPORTS_DIR)
REPORT_CHANGELOG_REGEX = r'{}{}.*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, REPORTS_DIR)

INDICATOR_TYPES_REGEX = r'{}{}/reputation-.*\.json$'.format(CAN_START_WITH_DOT_SLASH, INDICATOR_TYPES_DIR)
INDICATOR_TYPES_CHANGELOG_REGEX = r'{}{}/*_CHANGELOG.md$'.format(CAN_START_WITH_DOT_SLASH, INDICATOR_TYPES_DIR)
INDICATOR_TYPES_REPUTATIONS_REGEX = r'{}{}.reputations.json$'.format(CAN_START_WITH_DOT_SLASH, INDICATOR_TYPES_DIR)

PACK_METADATA_NAME = 'name'
PACK_METADATA_DESC = 'description'
PACK_METADATA_SUPPORT = 'support'
PACK_METADATA_MIN_VERSION = 'serverMinVersion'
PACK_METADATA_CURR_VERSION = 'currentVersion'
PACK_METADATA_AUTHOR = 'author'
PACK_METADATA_URL = 'url'
PACK_METADATA_EMAIL = 'email'
PACK_METADATA_CATEGORIES = 'categories'
PACK_METADATA_TAGS = 'tags'
PACK_METADATA_CREATED = 'created'
PACK_METADATA_CERTIFICATION = 'certification'
PACK_METADATA_USE_CASES = 'useCases'
PACK_METADATA_KEYWORDS = 'keywords'
PACK_METADATA_PRICE = 'price'
PACK_METADATA_DEPENDENCIES = 'dependencies'

PACK_METADATA_FIELDS = (PACK_METADATA_NAME, PACK_METADATA_DESC, PACK_METADATA_SUPPORT,
                        PACK_METADATA_CURR_VERSION, PACK_METADATA_AUTHOR, PACK_METADATA_URL, PACK_METADATA_CATEGORIES,
                        PACK_METADATA_TAGS, PACK_METADATA_CREATED, PACK_METADATA_USE_CASES, PACK_METADATA_KEYWORDS)
API_MODULES_PACK = 'ApiModules'

ID_IN_COMMONFIELDS = [  # entities in which 'id' key is under 'commonfields'
    'integration',
    'script'
]
ID_IN_ROOT = [  # entities in which 'id' key is in the root
    'playbook',
    'dashboard',
    'incident_type'
]

INTEGRATION_PREFIX = 'integration'
SCRIPT_PREFIX = 'script'

# Pack Unique Files
PACKS_WHITELIST_FILE_NAME = '.secrets-ignore'
PACKS_PACK_IGNORE_FILE_NAME = '.pack-ignore'
PACKS_PACK_META_FILE_NAME = 'pack_metadata.json'
PACKS_README_FILE_NAME = 'README.md'

PYTHON_TEST_REGEXES = [
    PACKS_SCRIPT_TEST_PY_REGEX,
    PACKS_INTEGRATION_TEST_PY_REGEX,
    INTEGRATION_TEST_PY_REGEX,
    SCRIPT_TEST_PY_REGEX
]

PYTHON_INTEGRATION_REGEXES = [
    INTEGRATION_PY_REGEX,
    PACKS_INTEGRATION_PY_REGEX,
]

PLAYBOOKS_REGEXES_LIST = [
    PLAYBOOK_REGEX,
    TEST_PLAYBOOK_REGEX
]

PYTHON_SCRIPT_REGEXES = [
    SCRIPT_PY_REGEX,
    PACKS_SCRIPT_PY_REGEX
]

PYTHON_ALL_REGEXES: List[str] = sum(
    [
        PYTHON_SCRIPT_REGEXES,
        PYTHON_INTEGRATION_REGEXES,
        PYTHON_TEST_REGEXES
    ], []
)

INTEGRATION_REGXES: List[str] = [
    INTEGRATION_REGEX,
    PACKS_INTEGRATION_REGEX,
    BETA_INTEGRATION_REGEX
]

YML_INTEGRATION_REGEXES: List[str] = [
    INTEGRATION_REGEX,
    PACKS_INTEGRATION_YML_REGEX,
    INTEGRATION_YML_REGEX,
    BETA_INTEGRATION_YML_REGEX
]

YML_BETA_INTEGRATIONS_REGEXES: List[str] = [
    BETA_INTEGRATION_REGEX,
    BETA_INTEGRATION_YML_REGEX,
]

YML_ALL_INTEGRATION_REGEXES: List[str] = sum(
    [
        YML_INTEGRATION_REGEXES,
        YML_BETA_INTEGRATIONS_REGEXES,
    ], []
)

YML_BETA_SCRIPTS_REGEXES: List[str] = [
    BETA_SCRIPT_REGEX,
]
YML_SCRIPT_REGEXES: List[str] = [
    SCRIPT_REGEX,
    PACKS_SCRIPT_YML_REGEX,
    SCRIPT_YML_REGEX
]

YML_ALL_SCRIPTS_REGEXES: List[str] = sum(
    [
        YML_BETA_SCRIPTS_REGEXES,
        YML_SCRIPT_REGEXES
    ], []
)

YML_PLAYBOOKS_NO_TESTS_REGEXES: List[str] = [
    PLAYBOOK_REGEX,
    PACKS_PLAYBOOK_YML_REGEX,
    PLAYBOOK_REGEX,
]

YML_TEST_PLAYBOOKS_REGEXES: List[str] = [
    TEST_PLAYBOOK_REGEX,
    PACKS_TEST_PLAYBOOKS_REGEX,
    TEST_PLAYBOOK_REGEX
]

YML_ALL_PLAYBOOKS_REGEX: List[str] = sum(
    [
        YML_PLAYBOOKS_NO_TESTS_REGEXES,
        YML_TEST_PLAYBOOKS_REGEXES,
    ], []
)

YML_ALL_REGEXES: List[str] = sum(
    [
        YML_INTEGRATION_REGEXES,
        YML_SCRIPT_REGEXES,
        YML_PLAYBOOKS_NO_TESTS_REGEXES,
        YML_TEST_PLAYBOOKS_REGEXES
    ], []
)

JSON_INDICATOR_AND_INCIDENT_FIELDS = [
    INCIDENT_FIELD_REGEX,
    INDICATOR_FIELDS_REGEX,
    PACKS_INCIDENT_FIELDS_REGEX,
    PACKS_INDICATOR_FIELDS_REGEX
]

JSON_ALL_WIDGETS_REGEXES = [
    WIDGETS_REGEX,
    PACKS_WIDGETS_REGEX,
]

JSON_ALL_DASHBOARDS_REGEXES = [
    DASHBOARD_REGEX,
    PACKS_DASHBOARDS_REGEX,
]

JSON_ALL_CLASSIFIER_REGEXES = [
    CLASSIFIER_REGEX,
    PACKS_CLASSIFIERS_REGEX,
]

JSON_ALL_LAYOUT_REGEXES = [
    LAYOUT_REGEX,
    PACKS_LAYOUTS_REGEX,
]

JSON_ALL_INCIDENT_FIELD_REGEXES = [
    INCIDENT_FIELD_REGEX,
    PACKS_INCIDENT_FIELDS_REGEX,
]

JSON_ALL_INCIDENT_TYPES_REGEXES = [
    INCIDENT_TYPE_REGEX,
    PACKS_INCIDENT_TYPES_REGEX,
]

JSON_ALL_INDICATOR_FIELDS_REGEXES = [
    INDICATOR_FIELDS_REGEX,
    PACKS_INDICATOR_FIELDS_REGEX
]

JSON_ALL_INDICATOR_TYPES_REGEXES = [
    INDICATOR_TYPES_REGEX,
    PACKS_INDICATOR_TYPES_REGEX
]

JSON_ALL_REPUTATIONS_INDICATOR_TYPES_REGEXES = [
    INDICATOR_TYPES_REPUTATIONS_REGEX,
    PACKS_INDICATOR_TYPES_REPUTATIONS_REGEX
]

JSON_ALL_CONNECTIONS_REGEXES = [
    CONNECTIONS_REGEX,
]

JSON_ALL_REPORTS_REGEXES = [
    REPORT_REGEX,
]

BETA_REGEXES = [
    BETA_SCRIPT_REGEX,
    BETA_INTEGRATION_YML_REGEX,
    BETA_PLAYBOOK_REGEX,
]
CHECKED_TYPES_REGEXES = [
    # Playbooks
    PLAYBOOK_REGEX,
    PACKS_PLAYBOOK_YML_REGEX,
    BETA_PLAYBOOK_REGEX,
    # Integrations yaml
    INTEGRATION_YML_REGEX,
    BETA_INTEGRATION_YML_REGEX,
    PACKS_INTEGRATION_YML_REGEX,
    # Integrations unified
    INTEGRATION_REGEX,
    # Integrations Code
    BETA_INTEGRATION_REGEX,
    PACKS_INTEGRATION_PY_REGEX,
    # Integrations Tests
    PACKS_INTEGRATION_TEST_PY_REGEX,
    # Scripts yaml
    SCRIPT_YML_REGEX,
    SCRIPT_REGEX,
    PACKS_SCRIPT_YML_REGEX,
    # Widgets
    WIDGETS_REGEX,
    PACKS_WIDGETS_REGEX,
    DASHBOARD_REGEX,
    CONNECTIONS_REGEX,
    CLASSIFIER_REGEX,
    # Layouts
    LAYOUT_REGEX,
    PACKS_LAYOUTS_REGEX,
    INCIDENT_FIELD_REGEX,
    INDICATOR_FIELDS_REGEX,
    INCIDENT_TYPE_REGEX,
    INDICATOR_TYPES_REGEX,
    REPORT_REGEX,
    # changelog
    PACKS_CHANGELOG_REGEX,
    # ReadMe,
    INTEGRATION_README_REGEX,
    PACKS_README_REGEX,
    PACKS_README_REGEX_INNER,
    INTEGRATION_OLD_README_REGEX,
    # Pack Misc
    PACKS_CLASSIFIERS_REGEX,
    PACKS_DASHBOARDS_REGEX,
    PACKS_INCIDENT_TYPES_REGEX,
    PACKS_INCIDENT_FIELDS_REGEX,
    PACKS_INDICATOR_FIELDS_REGEX,
    PACKS_INDICATOR_TYPES_REGEX,
    PACKS_LAYOUTS_REGEX,
    PACKS_WIDGETS_REGEX,
    PACKS_REPORTS_REGEX,
    PACKS_RELEASE_NOTES_REGEX
]

CHECKED_TYPES_NO_REGEX = [item.replace(CAN_START_WITH_DOT_SLASH, "").replace(NOT_TEST, "") for item in
                          CHECKED_TYPES_REGEXES]

PATHS_TO_VALIDATE: List[str] = sum(
    [
        PYTHON_ALL_REGEXES,
        JSON_ALL_REPORTS_REGEXES,
        BETA_REGEXES
    ], []
)

PACKAGE_SCRIPTS_REGEXES = [
    SCRIPT_YML_REGEX,
    SCRIPT_PY_REGEX,
    SCRIPT_JS_REGEX,
    PACKS_SCRIPT_PY_REGEX,
    PACKS_SCRIPT_JS_REGEX,
    PACKS_SCRIPT_YML_REGEX
]

PACKAGE_SUPPORTING_DIRECTORIES = [INTEGRATIONS_DIR, SCRIPTS_DIR, BETA_INTEGRATIONS_DIR]

IGNORED_TYPES_REGEXES = [DESCRIPTION_REGEX, IMAGE_REGEX, PIPFILE_REGEX, SCHEMA_REGEX]

PACKAGE_YML_FILE_REGEX = r'(?:\./)?(?:Packs/[^/]+/)?(?:Integrations|Scripts|Beta_Integrations)/([^\\/]+)/([^\\/]+).yml'

OLD_YML_FORMAT_FILE = [INTEGRATION_REGEX, SCRIPT_REGEX]

DIR_LIST = [
    INTEGRATIONS_DIR,
    BETA_INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PLAYBOOKS_DIR,
    REPORTS_DIR,
    DASHBOARDS_DIR,
    WIDGETS_DIR,
    INCIDENT_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    LAYOUTS_DIR,
    CLASSIFIERS_DIR,
    INDICATOR_TYPES_DIR,
    CONNECTIONS_DIR,
    INDICATOR_FIELDS_DIR,
    TESTS_DIR
]
DIR_LIST_FOR_REGULAR_ENTETIES = [
    PLAYBOOKS_DIR,
    REPORTS_DIR,
    DASHBOARDS_DIR,
    WIDGETS_DIR,
    INCIDENT_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    LAYOUTS_DIR,
    CLASSIFIERS_DIR,
    INDICATOR_TYPES_DIR,
    CONNECTIONS_DIR,
    INDICATOR_FIELDS_DIR,
]
PACKS_DIRECTORIES = [
    SCRIPTS_DIR,
    INTEGRATIONS_DIR,
    DASHBOARDS_DIR,
    WIDGETS_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR
]
SPELLCHECK_FILE_TYPES = [
    INTEGRATION_REGEX,
    INTEGRATION_YML_REGEX,
    PLAYBOOK_REGEX,
    SCRIPT_REGEX,
    SCRIPT_YML_REGEX
]

KNOWN_FILE_STATUSES = ['a', 'm', 'd', 'r'] + ['r{:03}'.format(i) for i in range(101)]

CODE_FILES_REGEX = [
    INTEGRATION_JS_REGEX,
    INTEGRATION_PY_REGEX,
    SCRIPT_PY_REGEX,
    SCRIPT_JS_REGEX,
    PACKS_INTEGRATION_PY_REGEX,
    PACKS_INTEGRATION_JS_REGEX,
    PACKS_SCRIPT_PY_REGEX,
    PACKS_SCRIPT_JS_REGEX
]

SCRIPTS_REGEX_LIST = [SCRIPT_YML_REGEX, SCRIPT_PY_REGEX, SCRIPT_JS_REGEX, SCRIPT_PS_REGEX]

# All files that have related yml file
REQUIRED_YML_FILE_TYPES = [SCRIPT_PY_REGEX, INTEGRATION_PY_REGEX, PACKS_INTEGRATION_PY_REGEX, PACKS_SCRIPT_PY_REGEX,
                           SCRIPT_JS_REGEX, INTEGRATION_JS_REGEX, PACKS_SCRIPT_JS_REGEX, PACKS_INTEGRATION_JS_REGEX,
                           PACKS_README_REGEX, INTEGRATION_README_REGEX, INTEGRATION_CHANGELOG_REGEX,
                           PACKS_CHANGELOG_REGEX]

TYPE_PWSH = 'powershell'
TYPE_PYTHON = 'python'
TYPE_JS = 'javascript'

TYPE_TO_EXTENSION = {
    TYPE_PYTHON: '.py',
    TYPE_JS: '.js',
    TYPE_PWSH: '.ps1'
}

TESTS_DIRECTORIES = [
    'testdata',
    'test_data',
    'data_test'
]

FILE_TYPES_FOR_TESTING = [
    '.py',
    '.js',
    '.yml',
    '.ps1'
]

# python subtypes
PYTHON_SUBTYPES = {'python3', 'python2'}

# github repository url
CONTENT_GITHUB_LINK = r'https://raw.githubusercontent.com/demisto/content'
CONTENT_GITHUB_MASTER_LINK = CONTENT_GITHUB_LINK + '/master'
SDK_API_GITHUB_RELEASES = r'https://api.github.com/repos/demisto/demisto-sdk/releases'

# Run all test signal
RUN_ALL_TESTS_FORMAT = 'Run all tests'
FILTER_CONF = './Tests/filter_file.txt'


class PB_Status:
    NOT_SUPPORTED_VERSION = 'Not supported version'
    COMPLETED = 'completed'
    FAILED = 'failed'
    IN_PROGRESS = 'inprogress'
    FAILED_DOCKER_TEST = 'failed_docker_test'


# change log regexes
UNRELEASE_HEADER = '## [Unreleased]\n'  # lgtm[py/regex/duplicate-in-character-class]
CONTENT_RELEASE_TAG_REGEX = r'^\d{2}\.\d{1,2}\.\d'
RELEASE_NOTES_REGEX = re.escape(UNRELEASE_HEADER) + r'([\s\S]+?)## \[\d{2}\.\d{1,2}\.\d\] - \d{4}-\d{2}-\d{2}'

# Beta integration disclaimer
BETA_INTEGRATION_DISCLAIMER = 'Note: This is a beta Integration,' \
                              ' which lets you implement and test pre-release software. ' \
                              'Since the integration is beta, it might contain bugs. ' \
                              'Updates to the integration during the beta phase might include ' \
                              'non-backward compatible features. We appreciate your feedback on ' \
                              'the quality and usability of the integration to help us identify issues, ' \
                              'fix them, and continually improve.'

# Integration categories according to the schema
INTEGRATION_CATEGORIES = ['Analytics & SIEM', 'Utilities', 'Messaging', 'Endpoint', 'Network Security',
                          'Vulnerability Management', 'Case Management', 'Forensics & Malware Analysis',
                          'IT Services', 'Data Enrichment & Threat Intelligence', 'Authentication', 'Database',
                          'Deception', 'Email Gateway']

EXTERNAL_PR_REGEX = r'^pull/(\d+)$'

SCHEMA_TO_REGEX = {
    'integration': YML_INTEGRATION_REGEXES,
    'playbook': YML_ALL_PLAYBOOKS_REGEX,
    'script': YML_SCRIPT_REGEXES,
    'widget': JSON_ALL_WIDGETS_REGEXES,
    'dashboard': JSON_ALL_DASHBOARDS_REGEXES,
    'canvas-context-connections': JSON_ALL_CONNECTIONS_REGEXES,
    'classifier': JSON_ALL_CLASSIFIER_REGEXES,
    'layout': JSON_ALL_LAYOUT_REGEXES,
    'incidentfield': JSON_ALL_INCIDENT_FIELD_REGEXES + JSON_ALL_INDICATOR_FIELDS_REGEXES,
    'incidenttype': JSON_ALL_INCIDENT_TYPES_REGEXES,
    'image': [IMAGE_REGEX],
    'reputation': JSON_ALL_INDICATOR_TYPES_REGEXES,
    'reputations': JSON_ALL_REPUTATIONS_INDICATOR_TYPES_REGEXES,
    'changelog': [INTEGRATION_CHANGELOG_REGEX, PACKS_CHANGELOG_REGEX, INDICATOR_TYPES_CHANGELOG_REGEX,
                  INCIDENT_TYPE_CHANGELOG_REGEX, INCIDENT_FIELD_CHANGELOG_REGEX, INDICATOR_FIELD_CHANGELOG_REGEX,
                  DASHBOARD_CHANGELOG_REGEX, CLASSIFIER_CHANGELOG_REGEX, LAYOUT_CHANGELOG_REGEX,
                  REPORT_CHANGELOG_REGEX, WIDGETS_CHANGELOG_REGEX, PLAYBOOK_CHANGELOG_REGEX,
                  PACKS_RELEASE_NOTES_REGEX],
    'readme': [INTEGRATION_README_REGEX, PACKS_README_REGEX, PACKS_README_REGEX_INNER]
}

FILE_TYPES_PATHS_TO_VALIDATE = {
    'reports': JSON_ALL_REPORTS_REGEXES
}

DEF_DOCKER = 'demisto/python:1.3-alpine'
DEF_DOCKER_PWSH = 'demisto/powershell:6.2.3.5563'

DIR_TO_PREFIX = {
    'Integrations': INTEGRATION_PREFIX,
    'Beta_Integrations': INTEGRATION_PREFIX,
    'Scripts': SCRIPT_PREFIX
}

ENTITY_NAME_SEPARATORS = [' ', '_', '-']

DELETED_YML_FIELDS_BY_DEMISTO = ['fromversion', 'toversion', 'alt_dockerimages', 'script.dockerimage45', 'tests']

DELETED_JSON_FIELDS_BY_DEMISTO = ['fromVersion', 'toVersion']

FILE_EXIST_REASON = 'File already exist'
FILE_NOT_IN_CC_REASON = 'File does not exist in Demisto instance'

ACCEPTED_FILE_EXTENSIONS = [
    '.yml', '.json', '.md', '.py', '.js', '.ps1', '.png', '', '.lock'
]

BANG_COMMAND_NAMES = {'file', 'email', 'domain', 'url', 'ip'}

DBOT_SCORES_DICT = {
    'DBotScore.Indicator': 'The indicator that was tested.',
    'DBotScore.Type': 'The indicator type.',
    'DBotScore.Vendor': 'The vendor used to calculate the score.',
    'DBotScore.Score': 'The actual score.'
}

IOC_OUTPUTS_DICT = {
    'domain': {'Domain.Name'},
    'file': {'File.MD5', 'File.SHA1', 'File.SHA256'},
    'ip': {'IP.Address'},
    'url': {'URL.Data'}
}

PACK_INITIAL_VERSION = '1.0.0'
PACK_SUPPORT_OPTIONS = ['xsoar', 'partner', 'developer', 'community', 'nonsupported']
XSOAR_SUPPORT = "xsoar"
XSOAR_AUTHOR = "Cortex XSOAR"
XSOAR_SUPPORT_URL = "https://www.paloaltonetworks.com/cortex"

BASE_PACK = "Base"
NON_SUPPORTED_PACK = "NonSupported"
DEPRECATED_CONTENT_PACK = "DeprecatedContent"
IGNORED_DEPENDENCY_CALCULATION = {BASE_PACK, NON_SUPPORTED_PACK, DEPRECATED_CONTENT_PACK}

FEED_REQUIRED_PARAMS = [
    {
        'display': 'Fetch indicators',
        'name': 'feed',
        'type': 8,
        'required': False
    },
    {
        'display': 'Indicator Reputation',
        'name': 'feedReputation',
        'type': 18,
        'required': False,
        'options': ['None', 'Good', 'Suspicious', 'Bad'],
        'additionalinfo': 'Indicators from this integration instance will be marked with this reputation'
    },
    {
        'display': 'Source Reliability',
        'name': 'feedReliability',
        'type': 15,
        'required': True,
        'options': [
            'A - Completely reliable', 'B - Usually reliable', 'C - Fairly reliable', 'D - Not usually reliable',
            'E - Unreliable', 'F - Reliability cannot be judged'],
        'additionalinfo': 'Reliability of the source providing the intelligence data'
    },
    {
        'display': "",
        'name': 'feedExpirationPolicy',
        'type': 17,
        'required': False,
        'options': ['never', 'interval', 'indicatorType', 'suddenDeath']
    },
    {
        'display': "",
        'name': 'feedExpirationInterval',
        'type': 1,
        'required': False
    },
    {
        'display': 'Feed Fetch Interval',
        'name': 'feedFetchInterval',
        'type': 19,
        'required': False
    },
    {
        'display': 'Bypass exclusion list',
        'name': 'feedBypassExclusionList',
        'type': 8,
        'required': False,
        'additionalinfo': 'When selected, the exclusion list is ignored for indicators from this feed.'
                          ' This means that if an indicator from this feed is on the exclusion list,'
                          ' the indicator might still be added to the system.'
    }
]

FETCH_REQUIRED_PARAMS = [
    {
        'display': 'Incident type',
        'name': 'incidentType',
        'required': False,
        'type': 13
    },
    {
        'display': 'Fetch incidents',
        'name': 'isFetch',
        'required': False,
        'type': 8
    }
]

DOCS_COMMAND_SECTION_REGEX = r'(?:###\s{}).+?(?:(?=(?:\n###\s))|(?=(?:\n##\s))|\Z)'
# Ignore list for all 'run_all_validations_on_file' method
ALL_FILES_VALIDATION_IGNORE_WHITELIST = [
    'pack_metadata.json',  # this file is validated under 'validate_pack_unique_files' method
    'testdata',
    'test_data',
    'data_test',
    'testcommandsfunctions',
    'testhelperfunctions',
    'stixdecodetest',
    'testcommands',
    'setgridfield_test',
    'ipnetwork_test',
    'test-data',
    'testplaybook'
]
