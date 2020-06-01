import glob
import itertools
import json
import os
import re
import time
from collections import OrderedDict
from distutils.version import LooseVersion
from functools import partial
from multiprocessing import Pool, cpu_count

import click
from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR, DASHBOARDS_DIR, INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR, INDICATOR_TYPES_DIR,
    INDICATOR_TYPES_REPUTATIONS_REGEX, LAYOUTS_DIR,
    PACKS_CLASSIFIER_JSON_REGEX, PACKS_DASHBOARD_JSON_REGEX,
    PACKS_INCIDENT_FIELD_JSON_REGEX, PACKS_INCIDENT_TYPE_JSON_REGEX,
    PACKS_INDICATOR_FIELD_JSON_REGEX, PACKS_INDICATOR_TYPE_JSON_REGEX,
    PACKS_INDICATOR_TYPES_REPUTATIONS_REGEX,
    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, PACKS_INTEGRATION_YML_REGEX,
    PACKS_LAYOUT_JSON_REGEX, PACKS_REPORT_JSON_REGEX,
    PACKS_SCRIPT_NON_SPLIT_YML_REGEX, PACKS_SCRIPT_YML_REGEX,
    PACKS_WIDGET_JSON_REGEX, PLAYBOOK_REGEX, PLAYBOOK_YML_REGEX, REPORTS_DIR,
    SCRIPTS_DIR, SCRIPTS_REGEX_LIST, TEST_PLAYBOOK_REGEX,
    TEST_PLAYBOOK_YML_REGEX, TEST_PLAYBOOKS_DIR, TEST_SCRIPT_REGEX,
    WIDGETS_DIR)
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_from_version,
                                               get_json, get_pack_name,
                                               get_to_version, get_yaml,
                                               print_color, print_error,
                                               print_warning, run_command)
from demisto_sdk.commands.unify.unifier import Unifier

CHECKED_TYPES_REGEXES = (
    # Integrations
    PACKS_INTEGRATION_YML_REGEX,
    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX,
    # Scripts
    PACKS_SCRIPT_YML_REGEX,
    PACKS_SCRIPT_NON_SPLIT_YML_REGEX,
    # Playbooks
    PLAYBOOK_YML_REGEX,
    # Classifiers
    PACKS_CLASSIFIER_JSON_REGEX
)


def checked_type(file_path, regex_list=CHECKED_TYPES_REGEXES):
    for regex in regex_list:
        if re.match(regex, file_path, re.IGNORECASE):
            return True
    return False


def get_changed_files(files_string):
    all_files = files_string.split('\n')
    deleted_files = set()
    added_files_list = set()
    added_script_list = set()
    modified_script_list = set()
    modified_files_list = set()
    for f in all_files:
        file_data = f.split()
        if not file_data:
            continue

        file_status = file_data[0]
        file_path = file_data[1]

        if file_status.lower() == 'a' and checked_type(file_path) and not file_path.startswith('.'):
            added_files_list.add(file_path)
        elif file_status.lower() == 'm' and checked_type(file_path) and not file_path.startswith('.'):
            modified_files_list.add(file_path)
        elif file_status.lower() == 'a' and checked_type(file_path, SCRIPTS_REGEX_LIST):
            added_script_list.add(os.path.join(os.path.dirname(file_path), ''))
        elif file_status.lower() == 'm' and checked_type(file_path, SCRIPTS_REGEX_LIST):
            modified_script_list.add(os.path.join(os.path.dirname(file_path), ''))
        elif file_status.lower() == 'd' and checked_type(file_path, SCRIPTS_REGEX_LIST):
            deleted_files.add(os.path.join(os.path.dirname(file_path), ''))
        elif file_status.lower() == 'd' and checked_type(file_path):
            deleted_files.add(file_path)

    for deleted_file in deleted_files:
        added_files_list = added_files_list - {deleted_file}
        modified_files_list = modified_files_list - {deleted_file}
        added_script_list = added_script_list - {deleted_file}
        modified_script_list = modified_script_list - {deleted_file}

    return added_files_list, modified_files_list, added_script_list, modified_script_list


def get_integration_commands(file_path):
    cmd_list = []
    data_dictionary = get_yaml(file_path)
    commands = data_dictionary.get('script', {}).get('commands', [])
    for command in commands:
        cmd_list.append(command.get('name'))

    return cmd_list


def get_task_ids_from_playbook(param_to_enrich_by: str, data_dict: dict) -> tuple:
    implementing_ids = set()
    implementing_ids_skippable = set()
    tasks = data_dict.get('tasks', {})

    for task in tasks.values():
        task_details = task.get('task', {})

        enriched_id = task_details.get(param_to_enrich_by)
        skippable = task_details.get('skipunavailable', False)
        if enriched_id:
            implementing_ids.add(enriched_id)
            if skippable:
                implementing_ids_skippable.add(enriched_id)

    return list(implementing_ids), list(implementing_ids_skippable)


def get_commmands_from_playbook(data_dict: dict) -> tuple:
    command_to_integration = {}
    command_to_integration_skippable = set()
    tasks = data_dict.get('tasks', [])

    for task in tasks.values():
        task_details = task.get('task', {})

        command = task_details.get('script')
        skippable = task_details.get('skipunavailable', False)
        if command:
            splitted_cmd = command.split('|')

            if 'Builtin' not in command:
                command_to_integration[splitted_cmd[-1]] = splitted_cmd[0]
                if skippable:
                    command_to_integration_skippable.add(splitted_cmd[-1])

    return command_to_integration, list(command_to_integration_skippable)


def get_integration_api_modules(file_path, data_dictionary, is_unified_integration):
    unifier = Unifier(os.path.dirname(file_path))
    if is_unified_integration:
        integration_script_code = data_dictionary.get('script', {}).get('script', '')
    else:
        _, integration_script_code = unifier.get_script_or_integration_package_data()

    return unifier.check_api_module_imports(integration_script_code)[1]


def get_integration_data(file_path):
    integration_data = OrderedDict()
    data_dictionary = get_yaml(file_path)

    is_unified_integration = data_dictionary.get('script', {}).get('script', '') != '-'

    id_ = data_dictionary.get('commonfields', {}).get('id', '-')
    name = data_dictionary.get('name', '-')

    deprecated = data_dictionary.get('deprecated', False)
    tests = data_dictionary.get('tests')
    toversion = data_dictionary.get('toversion')
    fromversion = data_dictionary.get('fromversion')
    commands = data_dictionary.get('script', {}).get('commands', [])
    cmd_list = [command.get('name') for command in commands]
    pack = get_pack_name(file_path)
    integration_api_modules = get_integration_api_modules(file_path, data_dictionary, is_unified_integration)

    deprecated_commands = []
    for command in commands:
        if command.get('deprecated', False):
            deprecated_commands.append(command.get('name'))

    integration_data['name'] = name
    integration_data['file_path'] = file_path
    if toversion:
        integration_data['toversion'] = toversion
    if fromversion:
        integration_data['fromversion'] = fromversion
    if cmd_list:
        integration_data['commands'] = cmd_list
    if tests:
        integration_data['tests'] = tests
    if deprecated:
        integration_data['deprecated'] = deprecated
    if deprecated_commands:
        integration_data['deprecated_commands'] = deprecated_commands
    if pack:
        integration_data['pack'] = pack
    if integration_api_modules:
        integration_data['api_modules'] = integration_api_modules
    return {id_: integration_data}


def get_playbook_data(file_path: str) -> dict:
    playbook_data = OrderedDict()
    data_dictionary = get_yaml(file_path)
    id_ = data_dictionary.get('id', '-')
    name = data_dictionary.get('name', '-')

    deprecated = data_dictionary.get('deprecated', False)
    tests = data_dictionary.get('tests')
    toversion = data_dictionary.get('toversion')
    fromversion = data_dictionary.get('fromversion')
    implementing_scripts, implementing_scripts_skippable = get_task_ids_from_playbook('scriptName', data_dictionary)
    implementing_playbooks, implementing_playbooks_skippable = get_task_ids_from_playbook('playbookName',
                                                                                          data_dictionary)
    command_to_integration, command_to_integration_skippable = get_commmands_from_playbook(data_dictionary)
    skippable_tasks = (implementing_scripts_skippable + implementing_playbooks_skippable +
                       command_to_integration_skippable)
    pack = get_pack_name(file_path)

    playbook_data['name'] = name
    playbook_data['file_path'] = file_path
    if toversion:
        playbook_data['toversion'] = toversion
    if fromversion:
        playbook_data['fromversion'] = fromversion

    if implementing_scripts:
        playbook_data['implementing_scripts'] = implementing_scripts
    if implementing_playbooks:
        playbook_data['implementing_playbooks'] = implementing_playbooks
    if command_to_integration:
        playbook_data['command_to_integration'] = command_to_integration
    if tests:
        playbook_data['tests'] = tests
    if deprecated:
        playbook_data['deprecated'] = deprecated
    if pack:
        playbook_data['pack'] = pack
    if skippable_tasks:
        playbook_data['skippable_tasks'] = skippable_tasks

    return {id_: playbook_data}


def get_script_data(file_path, script_code=None):
    script_data = OrderedDict()
    data_dictionary = get_yaml(file_path)
    id_ = data_dictionary.get('commonfields', {}).get('id', '-')
    if script_code is None:
        script_code = data_dictionary.get('script', '')

    name = data_dictionary.get('name', '-')

    tests = data_dictionary.get('tests')
    toversion = data_dictionary.get('toversion')
    deprecated = data_dictionary.get('deprecated', False)
    fromversion = data_dictionary.get('fromversion')
    depends_on, command_to_integration = get_depends_on(data_dictionary)
    script_executions = sorted(list(set(re.findall(r"demisto.executeCommand\(['\"](\w+)['\"].*", script_code))))
    pack = get_pack_name(file_path)

    script_data['name'] = name
    script_data['file_path'] = file_path
    if toversion:
        script_data['toversion'] = toversion
    if fromversion:
        script_data['fromversion'] = fromversion
    if deprecated:
        script_data['deprecated'] = deprecated
    if depends_on:
        script_data['depends_on'] = depends_on
    if script_executions:
        script_data['script_executions'] = script_executions
    if command_to_integration:
        script_data['command_to_integration'] = command_to_integration
    if tests:
        script_data['tests'] = tests
    if pack:
        script_data['pack'] = pack

    return {id_: script_data}


def get_layout_data(path):
    data = OrderedDict()
    json_data = get_json(path)
    layout = json_data.get('layout')
    name = layout.get('name', '-')
    id_ = json_data.get('id', layout.get('id', '-'))
    type_ = json_data.get('typeId')
    type_name = json_data.get('TypeName')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    kind = json_data.get('kind')
    pack = get_pack_name(path)

    if type_:
        data['typeID'] = type_
    if type_name:
        data['typename'] = type_name
    data['name'] = name
    if toversion:
        data['toversion'] = toversion
    if fromversion:
        data['fromversion'] = fromversion
    if pack:
        data['pack'] = pack
    if kind:
        data['kind'] = kind
    data['path'] = path

    return {id_: data}


def get_general_data(path):
    data = OrderedDict()
    json_data = get_json(path)

    id_ = json_data.get('id')
    brandname = json_data.get('brandName', '')
    name = json_data.get('name', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    if brandname:  # for classifiers
        data['name'] = brandname
    if name:  # for the rest
        data['name'] = name
    if toversion:
        data['toversion'] = toversion
    if fromversion:
        data['fromversion'] = fromversion
    if pack:
        data['pack'] = pack

    return {id_: data}


def get_depends_on(data_dict):
    depends_on = data_dict.get('dependson', {}).get('must', [])
    depends_on_list = list({cmd.split('|')[-1] for cmd in depends_on})
    command_to_integration = {}
    for cmd in depends_on:
        splitted_cmd = cmd.split('|')
        if splitted_cmd[0] and '|' in cmd:
            command_to_integration[splitted_cmd[-1]] = splitted_cmd[0]

    return depends_on_list, command_to_integration


def update_object_in_id_set(obj_id, obj_data, file_path, instances_set):
    change_string = run_command("git diff HEAD {}".format(file_path))
    is_added_from_version = True if re.search(r'\+fromversion: .*', change_string) else False
    is_added_to_version = True if re.search(r'\+toversion: .*', change_string) else False

    file_to_version = get_to_version(file_path)
    file_from_version = get_from_version(file_path)

    updated = False
    for instance in instances_set:
        instance_id = list(instance.keys())[0]
        integration_to_version = instance[instance_id].get('toversion', '99.99.99')
        integration_from_version = instance[instance_id].get('fromversion', '0.0.0')

        if obj_id == instance_id:
            if is_added_from_version or (not is_added_from_version and file_from_version == integration_from_version):
                if is_added_to_version or (not is_added_to_version and file_to_version == integration_to_version):
                    instance[obj_id] = obj_data[obj_id]
                    updated = True
                    break

    if not updated:
        # in case we didn't found then we need to create one
        add_new_object_to_id_set(obj_id, obj_data, instances_set)


def add_new_object_to_id_set(obj_id, obj_data, instances_set):
    obj_in_set = False

    dict_value = obj_data.values()[0]
    file_to_version = dict_value.get('toversion', '99.99.99')
    file_from_version = dict_value.get('fromversion', '0.0.0')

    for instance in instances_set:
        instance_id = instance.keys()[0]
        integration_to_version = instance[instance_id].get('toversion', '99.99.99')
        integration_from_version = instance[instance_id].get('fromversion', '0.0.0')
        if obj_id == instance_id and file_from_version == integration_from_version and \
                file_to_version == integration_to_version:
            instance[obj_id] = obj_data[obj_id]
            obj_in_set = True

    if not obj_in_set:
        instances_set.append(obj_data)


def process_integration(file_path: str, print_logs: bool) -> list:
    """
    Process integration dir or file

    Arguments:
        file_path {string} -- file path to integration file
        print_logs {bool} -- whether to print logs to stdout

    Returns:
        list -- integration data list (may be empty)
    """
    res = []
    if os.path.isfile(file_path):
        if checked_type(file_path, [PACKS_INTEGRATION_NON_SPLIT_YML_REGEX]):
            if print_logs:
                print("adding {} to id_set".format(file_path))
            res.append(get_integration_data(file_path))
    else:
        # package integration
        package_name = os.path.basename(file_path)
        file_path = os.path.join(file_path, '{}.yml'.format(package_name))
        if os.path.isfile(file_path):
            # locally, might have leftover dirs without committed files
            if print_logs:
                print("adding {} to id_set".format(file_path))
            res.append(get_integration_data(file_path))

    return res


def process_script(file_path: str, print_logs: bool) -> list:
    res = []
    if os.path.isfile(file_path):
        if checked_type(file_path, (PACKS_SCRIPT_YML_REGEX, PACKS_SCRIPT_NON_SPLIT_YML_REGEX)):
            if print_logs:
                print("adding {} to id_set".format(file_path))
            res.append(get_script_data(file_path))
    else:
        # package script
        unifier = Unifier(file_path)
        yml_path, code = unifier.get_script_or_integration_package_data()
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_script_data(yml_path, script_code=code))

    return res


def process_playbook(file_path: str, print_logs: bool) -> list:
    res = []
    if checked_type(file_path, (PLAYBOOK_YML_REGEX, PLAYBOOK_REGEX)):
        if print_logs:
            print('adding {} to id_set'.format(file_path))
        res.append(get_playbook_data(file_path))
    return res


def process_classifier(file_path: str, print_logs: bool) -> list:
    """
    Process a classifier JSON file
    Args:
        file_path: The file path from Classifiers folder
        print_logs: Whether to print logs to stdout
    Returns:
        a list of classifier data.
    """
    res = []
    if checked_type(file_path, [PACKS_CLASSIFIER_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_dashboards(file_path: str, print_logs: bool) -> list:
    """
    Process a dashboard JSON file
    Args:
        file_path: The file path from Dashboard folder
        print_logs: Whether to print logs to stdout

    Returns:
        a list of dashboard data.
    """
    res = []
    if checked_type(file_path, [PACKS_DASHBOARD_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_incident_fields(file_path: str, print_logs: bool) -> list:
    """
    Process a incident_fields JSON file
    Args:
        file_path: The file path from incident field folder
        print_logs: Whether to print logs to stdout.

    Returns:
        a list of incident field data.
    """
    res = []
    if checked_type(file_path, [PACKS_INCIDENT_FIELD_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_incident_types(file_path: str, print_logs: bool) -> list:
    """
    Process a incident_fields JSON file
    Args:
        file_path: The file path from incident field folder
        print_logs: Whether to print logs to stdout

    Returns:
        a list of incident field data.
    """
    res = []
    if checked_type(file_path, [PACKS_INCIDENT_TYPE_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_indicator_fields(file_path: str, print_logs: bool) -> list:
    """
    Process a indicator fields JSON file
    Args:
        file_path: The file path from indicator field folder
        print_logs: Whether to print logs to stdout

    Returns:
        a list of indicator field data.
    """
    res = []
    if checked_type(file_path, [PACKS_INDICATOR_FIELD_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_indicator_types(file_path: str, print_logs: bool) -> list:
    """
    Process a indicator types JSON file
    Args:
        file_path: The file path from indicator type folder
        print_logs: Whether to print logs to stdout

    Returns:
        a list of indicator type data.
    """
    res = []
    if (checked_type(file_path, [PACKS_INDICATOR_TYPE_JSON_REGEX]) and
            # ignore reputations.json
            not checked_type(file_path, [INDICATOR_TYPES_REPUTATIONS_REGEX, PACKS_INDICATOR_TYPES_REPUTATIONS_REGEX])):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_layouts(file_path: str, print_logs: bool) -> list:
    """
    Process a Layouts JSON file
    Args:
        file_path: The file path from layout folder
        print_logs: Whether to print logs to stdout

    Returns:
        a list of layout data.
    """
    res = []
    if checked_type(file_path, [PACKS_LAYOUT_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_layout_data(file_path))
    return res


def process_reports(file_path: str, print_logs: bool) -> list:
    """
    Process a report JSON file
    Args:
        file_path: The file path from report folder
        print_logs: Whether to print logs to stdout

    Returns:
        a list of report data.
    """
    res = []
    if checked_type(file_path, [PACKS_REPORT_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_widgets(file_path: str, print_logs: bool) -> list:
    """
    Process a widgets JSON file
    Args:
        file_path: The file path from widgets folder
        print_logs: Whether to print logs to stdout

    Returns:
        a list of widgets data.
    """
    res = []
    if checked_type(file_path, [PACKS_WIDGET_JSON_REGEX]):
        if print_logs:
            print("adding {} to id_set".format(file_path))
        res.append(get_general_data(file_path))
    return res


def process_test_playbook_path(file_path: str, print_logs: bool) -> tuple:
    """
    Process a yml file in the testplyabook dir. Maybe either a script or playbook

    Arguments:
        file_path {string} -- path to yaml file
        print_logs {bool} -- whether to print logs to stdoud

    Returns:
        pair -- first element is a playbook second is a script. each may be None
    """
    if print_logs:
        print("adding {} to id_set".format(file_path))
    script = None
    playbook = None
    if checked_type(file_path, (TEST_SCRIPT_REGEX, TEST_PLAYBOOK_YML_REGEX, TEST_PLAYBOOK_REGEX)):
        yml_data = get_yaml(file_path)
        if 'commonfields' in yml_data:
            # script files contain this key
            script = get_script_data(file_path)
        else:
            playbook = get_playbook_data(file_path)

    return playbook, script


def get_integrations_paths():
    path_list = [
        ['Packs', '*', 'Integrations', '*']
    ]
    integration_files = list()
    for path in path_list:
        integration_files.extend(glob.glob(os.path.join(*path)))

    return integration_files


def get_playbooks_paths():
    path_list = [
        ['Packs', '*', 'Playbooks', '*.yml']
    ]

    playbook_files = list()
    for path in path_list:
        playbook_files.extend(glob.glob(os.path.join(*path)))

    return playbook_files


def get_general_paths(path):
    path_list = [
        [path, '*'],
        ['Packs', '*', path, '*']
    ]
    files = list()
    for path in path_list:
        files.extend(glob.glob(os.path.join(*path)))

    return files


def re_create_id_set(id_set_path: str = "./Tests/id_set.json", objects_to_create: list = None, print_logs: bool = True):  # noqa: C901
    if objects_to_create is None:
        objects_to_create = ['Integrations', 'Scripts', 'Playbooks', 'TestPlaybooks', 'Classifiers',
                             'Dashboards', 'IncidentFields', 'IndicatorFields', 'IndicatorTypes',
                             'Layouts', 'Reports', 'Widgets']
    start_time = time.time()
    scripts_list = []
    playbooks_list = []
    integration_list = []
    testplaybooks_list = []

    classifiers_list = []
    dashboards_list = []
    incident_fields_list = []
    incident_type_list = []
    indicator_fields_list = []
    indicator_types_list = []
    layouts_list = []
    reports_list = []
    widgets_list = []

    pool = Pool(processes=cpu_count() * 2)

    print_color("Starting the creation of the id_set", LOG_COLORS.GREEN)

    with click.progressbar(length=12, label="Progress of id set creation") as progress_bar:
        if 'Integrations' in objects_to_create:
            print_color("\nStarting iteration over Integrations", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_integration, print_logs=print_logs), get_integrations_paths()):
                integration_list.extend(arr)

        progress_bar.update(1)

        if 'Playbooks' in objects_to_create:
            print_color("\nStarting iteration over Playbooks", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_playbook, print_logs=print_logs), get_playbooks_paths()):
                playbooks_list.extend(arr)

        progress_bar.update(1)

        if 'Scripts' in objects_to_create:
            print_color("\nStarting iteration over Scripts", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_script, print_logs=print_logs), get_general_paths(SCRIPTS_DIR)):
                scripts_list.extend(arr)

        progress_bar.update(1)

        if 'TestPlaybooks' in objects_to_create:
            print_color("\nStarting iteration over TestPlaybooks", LOG_COLORS.GREEN)
            for pair in pool.map(partial(process_test_playbook_path, print_logs=print_logs),
                                 get_general_paths(TEST_PLAYBOOKS_DIR)):
                if pair[0]:
                    testplaybooks_list.append(pair[0])
                if pair[1]:
                    scripts_list.append(pair[1])

        progress_bar.update(1)

        if 'Classifiers' in objects_to_create:
            print_color("\nStarting iteration over Classifiers", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_classifier, print_logs=print_logs), get_general_paths(CLASSIFIERS_DIR)):
                classifiers_list.extend(arr)

        progress_bar.update(1)

        if 'Dashboards' in objects_to_create:
            print_color("\nStarting iteration over Dashboards", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_dashboards, print_logs=print_logs), get_general_paths(DASHBOARDS_DIR)):
                dashboards_list.extend(arr)

        progress_bar.update(1)

        if 'IncidentFields' in objects_to_create:
            print_color("\nStarting iteration over Incident Fields", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_incident_fields, print_logs=print_logs),
                                get_general_paths(INCIDENT_FIELDS_DIR)):
                incident_fields_list.extend(arr)

        progress_bar.update(1)

        if 'IncidentTypes' in objects_to_create:
            print_color("\nStarting iteration over Incident Types", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_incident_types, print_logs=print_logs),
                                get_general_paths(INCIDENT_TYPES_DIR)):
                incident_type_list.extend(arr)

        progress_bar.update(1)

        if 'IndicatorFields' in objects_to_create:
            print_color("\nStarting iteration over Indicator Fields", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_indicator_fields, print_logs=print_logs),
                                get_general_paths(INDICATOR_FIELDS_DIR)):
                indicator_fields_list.extend(arr)

        progress_bar.update(1)

        if 'IndicatorTypes' in objects_to_create:
            print_color("\nStarting iteration over Indicator Types", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_indicator_types, print_logs=print_logs),
                                get_general_paths(INDICATOR_TYPES_DIR)):
                indicator_types_list.extend(arr)

        progress_bar.update(1)

        if 'Layouts' in objects_to_create:
            print_color("\nStarting iteration over Layouts", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_layouts, print_logs=print_logs), get_general_paths(LAYOUTS_DIR)):
                layouts_list.extend(arr)

        progress_bar.update(1)

        if 'Reports' in objects_to_create:
            print_color("\nStarting iteration over Reports", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_reports, print_logs=print_logs), get_general_paths(REPORTS_DIR)):
                reports_list.extend(arr)

        progress_bar.update(1)

        if 'Widgets' in objects_to_create:
            print_color("\nStarting iteration over Widgets", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_widgets, print_logs=print_logs), get_general_paths(WIDGETS_DIR)):
                widgets_list.extend(arr)

        progress_bar.update(1)

    new_ids_dict = OrderedDict()
    # we sort each time the whole set in case someone manually changed something
    # it shouldn't take too much time
    new_ids_dict['scripts'] = sort(scripts_list)
    new_ids_dict['playbooks'] = sort(playbooks_list)
    new_ids_dict['integrations'] = sort(integration_list)
    new_ids_dict['TestPlaybooks'] = sort(testplaybooks_list)
    new_ids_dict['Classifiers'] = sort(classifiers_list)
    new_ids_dict['Dashboards'] = sort(dashboards_list)
    new_ids_dict['IncidentFields'] = sort(incident_fields_list)
    new_ids_dict['IncidentTypes'] = sort(incident_type_list)
    new_ids_dict['IndicatorFields'] = sort(indicator_fields_list)

    new_ids_dict['IndicatorTypes'] = sort(indicator_types_list)
    new_ids_dict['Layouts'] = sort(layouts_list)
    new_ids_dict['Reports'] = sort(reports_list)
    new_ids_dict['Widgets'] = sort(widgets_list)

    if id_set_path:
        with open(id_set_path, 'w+') as id_set_file:
            json.dump(new_ids_dict, id_set_file, indent=4)
    exec_time = time.time() - start_time
    print_color("Finished the creation of the id_set. Total time: {} seconds".format(exec_time), LOG_COLORS.GREEN)

    duplicates = find_duplicates(new_ids_dict, print_logs)
    if any(duplicates) and print_logs:
        print_error('The following duplicates were found: {}'.format(duplicates))

    return new_ids_dict


def find_duplicates(id_set, print_logs):
    lists_to_return = []

    objects_to_check = ['integrations', 'scripts', 'playbooks', 'TestPlaybooks', 'Classifiers', 'Dashboards',
                        'Layouts', 'Reports', 'Widgets']
    for object_type in objects_to_check:
        if print_logs:
            print_color("Checking diff for {}".format(object_type), LOG_COLORS.GREEN)
        objects = id_set.get(object_type)
        ids = {list(specific_item.keys())[0] for specific_item in objects}

        dup_list = []
        for id_to_check in ids:
            if has_duplicate(objects, id_to_check, object_type, print_logs):
                dup_list.append(id_to_check)
        lists_to_return.append(dup_list)

    if print_logs:
        print_color("Checking diff for Incident and Idicator Fields", LOG_COLORS.GREEN)

    fields = id_set['IncidentFields'] + id_set['IndicatorFields']
    field_ids = {list(field.keys())[0] for field in fields}

    field_list = []
    for field_to_check in field_ids:
        if has_duplicate(fields, field_to_check, 'Indicator and Incident Fields', print_logs):
            field_list.append(field_to_check)
    lists_to_return.append(field_list)

    return lists_to_return


def has_duplicate(id_set, id_to_check, object_type=None, print_logs=True):
    duplicates = [duplicate for duplicate in id_set if duplicate.get(id_to_check)]

    if len(duplicates) < 2:
        return False

    for dup1, dup2 in itertools.combinations(duplicates, 2):
        dict1 = list(dup1.values())[0]
        dict2 = list(dup2.values())[0]
        dict1_from_version = LooseVersion(dict1.get('fromversion', '0.0.0'))
        dict2_from_version = LooseVersion(dict2.get('fromversion', '0.0.0'))
        dict1_to_version = LooseVersion(dict1.get('toversion', '99.99.99'))
        dict2_to_version = LooseVersion(dict2.get('toversion', '99.99.99'))

        if print_logs and dict1['name'] != dict2['name']:
            print_warning('The following {} have the same ID ({}) but different names: '
                          '"{}", "{}".'.format(object_type, id_to_check, dict1['name'], dict2['name']))

        # Checks if the Layouts kind is different then they are not duplicates
        if object_type == 'Layouts':
            if dict1.get('kind', '') != dict2.get('kind', ''):
                return False

        # A: 3.0.0 - 3.6.0
        # B: 3.5.0 - 4.5.0
        # C: 3.5.2 - 3.5.4
        # D: 4.5.0 - 99.99.99
        if any([
            dict1_from_version <= dict2_from_version < dict1_to_version,  # will catch (B, C), (A, B), (A, C)
            dict1_from_version < dict2_to_version <= dict1_to_version,  # will catch (B, C), (A, C)
            dict2_from_version <= dict1_from_version < dict2_to_version,  # will catch (C, B), (B, A), (C, A)
            dict2_from_version < dict1_to_version <= dict2_to_version,  # will catch (C, B), (C, A)
        ]):
            return True

    return False


def sort(data):
    data.sort(key=lambda r: list(r.keys())[0].lower())  # Sort data by key value
    return data
