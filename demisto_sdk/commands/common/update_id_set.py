import copy
import glob
import itertools
import json
import os
import re
import time
from collections import OrderedDict
from datetime import datetime
from distutils.version import LooseVersion
from enum import Enum
from functools import partial
from multiprocessing import Pool, cpu_count
from typing import Callable, Dict, Optional, Tuple

import click
import networkx
from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR,
                                                   COMMON_TYPES_PACK,
                                                   DASHBOARDS_DIR,
                                                   DEFAULT_ID_SET_PATH,
                                                   INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR,
                                                   INDICATOR_FIELDS_DIR,
                                                   INDICATOR_TYPES_DIR,
                                                   LAYOUTS_DIR, MAPPERS_DIR,
                                                   REPORTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   WIDGETS_DIR, FileType)
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type, get_json,
                                               get_pack_name, get_yaml,
                                               print_color, print_error,
                                               print_warning)
from demisto_sdk.commands.unify.unifier import Unifier

CONTENT_ENTITIES = ['Integrations', 'Scripts', 'Playbooks', 'TestPlaybooks', 'Classifiers',
                    'Dashboards', 'IncidentFields', 'IncidentTypes', 'IndicatorFields', 'IndicatorTypes',
                    'Layouts', 'Reports', 'Widgets', 'Mappers', 'Packs']

ID_SET_ENTITIES = ['integrations', 'scripts', 'playbooks', 'TestPlaybooks', 'Classifiers',
                   'Dashboards', 'IncidentFields', 'IncidentTypes', 'IndicatorFields', 'IndicatorTypes',
                   'Layouts', 'Reports', 'Widgets', 'Mappers']

BUILT_IN_FIELDS = [
    "name",
    "details",
    "severity",
    "owner",
    "dbotCreatedBy",
    "type",
    "dbotSource",
    "category",
    "dbotStatus",
    "playbookId",
    "dbotCreated",
    "dbotClosed",
    "occurred",
    "dbotDueDate",
    "dbotModified",
    "dbotTotalTime",
    "reason",
    "closeReason",
    "closeNotes",
    "closingUserId",
    "reminder",
    "phase",
    "roles",
    "labels",
    "attachment",
    "runStatus",
    "sourceBrand",
    "sourceInstance",
    "CustomFields",
    "droppedCount",
    "linkedCount",
    "feedBased",
    "id",
    "xsoarReadOnlyRoles",
    "dbotMirrorId",
    "dbotMirrorInstance",
    "dbotMirrorDirection",
    "dbotMirrorTags",
    "dbotMirrorLastSync"
]


def build_tasks_graph(playbook_data):
    """
    Builds tasks flow graph.

    Args:
        playbook_data (dict): playbook yml data.

    Returns:
        DiGraph: all tasks of given playbook.
    """
    initial_task = playbook_data.get('starttaskid', '')
    tasks = playbook_data.get('tasks', {})

    graph = networkx.DiGraph()
    graph.add_node(initial_task, mandatory=True)  # add starting task as root of the direct graph

    found_new_tasks = True
    while found_new_tasks:
        current_number_of_nodes = graph.number_of_nodes()
        leaf_nodes = {node for node in graph.nodes() if graph.out_degree(node) == 0}

        for leaf in leaf_nodes:
            leaf_task = tasks.get(leaf)
            leaf_mandatory = graph.nodes[leaf]['mandatory']

            # In this case the playbook is invalid, starttaskid contains invalid task id.
            if not leaf_task:
                print_warning(f'{playbook_data.get("id")}: No such task {leaf} in playbook')
                continue

            leaf_next_tasks = sum(leaf_task.get('nexttasks', {}).values(), [])  # type: ignore

            for task_id in leaf_next_tasks:
                task = tasks.get(task_id)
                if not task:
                    print_warning(f'{playbook_data.get("id")}: No such task {leaf} in playbook')
                    continue

                # If task can't be skipped and predecessor task is mandatory - set as mandatory.
                mandatory = leaf_mandatory and not task.get('skipunavailable', False)
                if task_id not in graph.nodes():
                    graph.add_node(task_id, mandatory=mandatory)
                else:
                    # If task already in graph, update mandatory field.
                    # If one of the paths to the task is mandatory - set as mandatory.
                    graph.nodes[task_id]['mandatory'] = graph.nodes[task_id]['mandatory'] or mandatory
                graph.add_edge(leaf, task_id)

        found_new_tasks = graph.number_of_nodes() > current_number_of_nodes

    return graph


def get_task_ids_from_playbook(param_to_enrich_by: str, data_dict: dict, graph: networkx.DiGraph) -> tuple:
    implementing_ids = set()
    implementing_ids_skippable = set()
    tasks = data_dict.get('tasks', {})

    for task_id, task in tasks.items():
        task_details = task.get('task', {})

        enriched_id = task_details.get(param_to_enrich_by)
        try:
            skippable = not graph.nodes[task_id]['mandatory']
        except KeyError:
            # if task id not in the graph - the task is unreachable.
            print_error(f'{data_dict["id"]}: task {task_id} is not connected')
            continue
        if enriched_id:
            implementing_ids.add(enriched_id)
            if skippable:
                implementing_ids_skippable.add(enriched_id)

    return list(implementing_ids), list(implementing_ids_skippable)


def get_commands_from_playbook(data_dict: dict) -> tuple:
    command_to_integration = {}
    command_to_integration_skippable = set()
    tasks = data_dict.get('tasks', {})

    for task in tasks.values():
        task_details = task.get('task', {})

        command = task_details.get('script')
        skippable = task.get('skipunavailable', False)
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

    is_unified_integration = data_dictionary.get('script', {}).get('script', '') not in ['-', '']

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
    default_classifier = data_dictionary.get('defaultclassifier')
    default_incident_type = data_dictionary.get('defaultIncidentType')
    is_feed = data_dictionary.get('script', {}).get('feed', False)
    mappers = set()

    deprecated_commands = []
    for command in commands:
        if command.get('deprecated', False):
            deprecated_commands.append(command.get('name'))

    for mapper in ['defaultmapperin', 'defaultmapperout']:
        if data_dictionary.get(mapper):
            mappers.add(data_dictionary.get(mapper))

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
    if default_classifier and default_classifier != '':
        integration_data['classifiers'] = default_classifier
    if mappers:
        integration_data['mappers'] = list(mappers)
    if default_incident_type and default_incident_type != '':
        integration_data['incident_types'] = default_incident_type
    if is_feed:
        # if the integration is a feed it should be dependent on CommonTypes
        integration_data['indicator_fields'] = COMMON_TYPES_PACK
        integration_data['indicator_types'] = COMMON_TYPES_PACK

    return {id_: integration_data}


def get_fields_by_script_argument(task):
    """Iterates over the task script arguments and search for non empty fields

    Args:
        task (dict): A task of the playbook with `script: Builtin|||setIncident`

    Returns:
        set. set of incident fields related to this task

    Example:
        for the task:
            {
                task:
                  id: e80e3f5a-a74f-44a8-8e83-8eee96def1d0
                  name: Save authenticity check result to incident field
                  script: Builtin|||setIncident

                scriptarguments:
                  emailaddress:
                    complex:
                      root: ActiveDirectory
                      accessor: Users.mail
                  duration: {}
            }

        we will return the 'emailaddress` incident field
    """

    dependent_incident_fields = set()
    for field_name, field_value in task.get('scriptarguments', {}).items():
        if field_value and field_name not in BUILT_IN_FIELDS:
            if field_name != "customFields":
                dependent_incident_fields.add(field_name)
            else:
                # the value should be a list of dicts in str format
                custom_field_value = list(field_value.values())[0]
                if isinstance(custom_field_value, str):
                    custom_fields_list = json.loads(custom_field_value)
                    for custom_field in custom_fields_list:
                        field_name = list(custom_field.keys())[0]
                        if field_name not in BUILT_IN_FIELDS:
                            dependent_incident_fields.add(field_name)
    return dependent_incident_fields


def get_incident_fields_by_playbook_input(playbook_input):
    """Searches for incident fields in a playbook input.

    Args:
        playbook_input (dict): An input of the playbook

    Returns:
        set. set of incident fields related to this task
    """
    dependent_incident_fields = set()

    input_type = list(playbook_input.keys())[0]  # type can be `simple` or `complex`
    input_value = list(playbook_input.values())[0]

    # check if it is in the form 'simple: ${incident.field_name}'
    if input_type == 'simple' and str(input_value).startswith('${incident.'):
        field_name = input_value.split('.')[1][:-1]
        if field_name not in BUILT_IN_FIELDS:
            dependent_incident_fields.add(field_name)

    elif input_type == 'complex':
        root_value = str(input_value.get('root', ''))
        accessor_value = str(input_value.get('accessor'))
        combined_value = root_value + '.' + accessor_value  # concatenate the strings

        field_name = re.match(r'incident\.([^.]+)', combined_value)
        if field_name:
            field_name = field_name.groups()[0]
            if field_name not in BUILT_IN_FIELDS:
                dependent_incident_fields.add(field_name)

    return dependent_incident_fields


def get_dependent_incident_and_indicator_fields(data_dictionary):
    """Finds the incident fields and indicator fields dependent on this playbook

    Args:
        data_dictionary (dict): The playbook data dict

    Returns:
        set. set of incident fields related to this playbook
    """
    dependent_incident_fields = set()
    dependent_indicator_fields = set()
    for task in data_dictionary.get('tasks', {}).values():
        # incident fields dependent by field mapping
        related_incident_fields = task.get('fieldMapping')
        if related_incident_fields:
            for incident_field in related_incident_fields:
                if incident_field not in BUILT_IN_FIELDS:
                    dependent_incident_fields.add(incident_field.get('incidentfield'))

        # incident fields dependent by scripts arguments
        if 'setIncident' in task.get('task', {}).get('script', ''):
            dependent_incident_fields.update(get_fields_by_script_argument(task))
            # incident fields dependent by scripts arguments
        if 'setIndicator' in task.get('task', {}).get('script', ''):
            dependent_indicator_fields.update(get_fields_by_script_argument(task))

    # incident fields by playbook inputs
    for playbook_input in data_dictionary.get('inputs', []):
        input_value_dict = playbook_input.get('value', {})
        if input_value_dict and isinstance(input_value_dict, dict):  # deprecated playbooks bug
            dependent_incident_fields.update(get_incident_fields_by_playbook_input(input_value_dict))

    return dependent_incident_fields, dependent_indicator_fields


def get_playbook_data(file_path: str) -> dict:
    data_dictionary = get_yaml(file_path)
    graph = build_tasks_graph(data_dictionary)

    id_ = data_dictionary.get('id', '-')
    name = data_dictionary.get('name', '-')
    deprecated = data_dictionary.get('hidden', False)
    tests = data_dictionary.get('tests')
    toversion = data_dictionary.get('toversion')
    fromversion = data_dictionary.get('fromversion')

    implementing_scripts, implementing_scripts_skippable = get_task_ids_from_playbook('scriptName',
                                                                                      data_dictionary,
                                                                                      graph
                                                                                      )
    implementing_playbooks, implementing_playbooks_skippable = get_task_ids_from_playbook('playbookName',
                                                                                          data_dictionary,
                                                                                          graph
                                                                                          )
    command_to_integration, command_to_integration_skippable = get_commands_from_playbook(data_dictionary)
    skippable_tasks = (implementing_scripts_skippable + implementing_playbooks_skippable +
                       command_to_integration_skippable)
    pack = get_pack_name(file_path)
    dependent_incident_fields, dependent_indicator_fields = get_dependent_incident_and_indicator_fields(data_dictionary)

    playbook_data = create_common_entity_data(path=file_path, name=name, to_version=toversion,
                                              from_version=fromversion, pack=pack)
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
    if skippable_tasks:
        playbook_data['skippable_tasks'] = skippable_tasks
    if dependent_incident_fields:
        playbook_data['incident_fields'] = list(dependent_incident_fields)
    if dependent_indicator_fields:
        playbook_data['indicator_fields'] = list(dependent_indicator_fields)
    return {id_: playbook_data}


def get_script_data(file_path, script_code=None):
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

    script_data = create_common_entity_data(path=file_path, name=name, to_version=toversion, from_version=fromversion,
                                            pack=pack)
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

    return {id_: script_data}


def get_values_for_keys_recursively(json_object: dict, keys_to_search: list) -> dict:
    """Recursively iterates over a dictionary to extract values for a list of keys.

    Args:
        json_object (dict): The dict to iterate on.
        keys_to_search (list): The list of keys to extract values for .

    Returns:
        dict. list of extracted values for each of the keys_to_search.

    Notes:
        only primitive values will be extracted (str/int/float/bool).

    Example:
        for the dict:
            {
                'id': 1,
                'nested': {
                    'x1': 1,
                    'x2': 'x2',
                    'x3': False
                },
                'x2': 4.0
            }

        and the list of keys
            [x1, x2, x3, x4]

        we will get the following dict:
            {
                'x1': [1],
                'x2': ['x2', 4.0],
                'x3': [False]
            }
    """
    values = {key: [] for key in keys_to_search}  # type: dict

    def get_values(current_object):
        if not current_object or not isinstance(current_object, (dict, list)):
            return

        if current_object and isinstance(current_object, list):
            if isinstance(current_object[0], dict):
                for item in current_object:
                    get_values(item)
            return

        if isinstance(current_object, dict):
            for key, value in current_object.items():
                if isinstance(value, (dict, list)):
                    get_values(value)
                elif key in keys_to_search:
                    if isinstance(value, (str, int, float, bool)):
                        values[key].append(value)

    get_values(json_object)
    return values


def get_layout_data(path):
    json_data = get_json(path)

    layout = json_data.get('layout', {})
    name = layout.get('name', '-')
    id_ = json_data.get('id', layout.get('id', '-'))
    type_ = json_data.get('typeId')
    type_name = json_data.get('TypeName')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    kind = json_data.get('kind')
    pack = get_pack_name(path)
    incident_indicator_types_dependency = {id_}
    incident_indicator_fields_dependency = get_values_for_keys_recursively(json_data, ['fieldId'])

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if type_:
        data['typeID'] = type_
    if type_name:
        data['typename'] = type_name
        incident_indicator_types_dependency.add(type_name)
    if kind:
        data['kind'] = kind
    data['incident_and_indicator_types'] = list(incident_indicator_types_dependency)
    if incident_indicator_fields_dependency['fieldId']:
        data['incident_and_indicator_fields'] = incident_indicator_fields_dependency['fieldId']

    return {id_: data}


def get_layoutscontainer_data(path):
    json_data = get_json(path)
    layouts_container_fields = ["group", "edit", "indicatorsDetails", "indicatorsQuickView", "quickView", "close",
                                "details", "detailsV2", "mobile", "name"]
    data = OrderedDict({field: json_data[field] for field in layouts_container_fields if json_data.get(field)})

    id_ = json_data.get('id')
    pack = get_pack_name(path)
    incident_indicator_types_dependency = {id_}
    incident_indicator_fields_dependency = get_values_for_keys_recursively(json_data, ['fieldId'])

    if data.get('name'):
        incident_indicator_types_dependency.add(data['name'])
    if json_data.get('toVersion'):
        data['toversion'] = json_data['toVersion']
    if json_data.get('fromVersion'):
        data['fromversion'] = json_data['fromVersion']
    if pack:
        data['pack'] = pack
    data['file_path'] = path
    data['incident_and_indicator_types'] = list(incident_indicator_types_dependency)
    if incident_indicator_fields_dependency['fieldId']:
        data['incident_and_indicator_fields'] = incident_indicator_fields_dependency['fieldId']

    return {id_: data}


def get_incident_field_data(path, incidents_types_list):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    all_associated_types: set = set()
    all_scripts = set()

    associated_types = json_data.get('associatedTypes')
    if associated_types:
        all_associated_types = set(associated_types)

    system_associated_types = json_data.get('systemAssociatedTypes')
    if system_associated_types:
        all_associated_types = all_associated_types.union(set(system_associated_types))

    if 'all' in all_associated_types:
        all_associated_types = {list(incident_type.keys())[0] for incident_type in incidents_types_list}

    scripts = json_data.get('script')
    if scripts:
        all_scripts = {scripts}

    field_calculations_scripts = json_data.get('fieldCalcScript')
    if field_calculations_scripts:
        all_scripts = all_scripts.union({field_calculations_scripts})

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)

    if all_associated_types:
        data['incident_types'] = list(all_associated_types)
    if all_scripts:
        data['scripts'] = list(all_scripts)

    return {id_: data}


def get_indicator_type_data(path, all_integrations):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('details', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    reputation_command = json_data.get('reputationCommand')
    pack = get_pack_name(path)
    all_scripts: set = set()
    associated_integrations = set()

    for field in ['reputationScriptName', 'enhancementScriptNames']:
        associated_scripts = json_data.get(field)
        if not associated_scripts or associated_scripts == 'null':
            continue

        associated_scripts = [associated_scripts] if not isinstance(associated_scripts, list) else associated_scripts
        if associated_scripts:
            all_scripts = all_scripts.union(set(associated_scripts))

    for integration in all_integrations:
        integration_name = next(iter(integration))
        integration_commands = integration.get(integration_name).get('commands')
        if integration_commands and reputation_command in integration_commands:
            associated_integrations.add(integration_name)

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if associated_integrations:
        data['integrations'] = list(associated_integrations)
    if all_scripts:
        data['scripts'] = list(all_scripts)

    return {id_: data}


def get_incident_type_data(path):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    playbook_id = json_data.get('playbookId')
    pre_processing_script = json_data.get('preProcessingScript')
    pack = get_pack_name(path)

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if playbook_id and playbook_id != '':
        data['playbooks'] = playbook_id
    if pre_processing_script and pre_processing_script != '':
        data['scripts'] = pre_processing_script

    return {id_: data}


def get_classifier_data(path):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    incidents_types = set()

    default_incident_type = json_data.get('defaultIncidentType')
    if default_incident_type and default_incident_type != '':
        incidents_types.add(default_incident_type)
    key_type_map = json_data.get('keyTypeMap', {})
    for key, value in key_type_map.items():
        incidents_types.add(value)

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if incidents_types:
        data['incident_types'] = list(incidents_types)

    return {id_: data}


def create_common_entity_data(path, name, to_version, from_version, pack):
    data = OrderedDict()
    if name:
        data['name'] = name
    data['file_path'] = path
    if to_version:
        data['toversion'] = to_version
    if from_version:
        data['fromversion'] = from_version
    if pack:
        data['pack'] = pack
    return data


def get_pack_metadata_data(file_path, print_logs: bool):
    try:
        if print_logs:
            print(f'adding {file_path} to id_set')

        json_data = get_json(file_path)
        pack_data = {
            "name": json_data.get('name'),
            "current_version": json_data.get('currentVersion'),
            "author": json_data.get('author', ''),
            'certification': 'certified' if json_data.get('support', '').lower() in ['xsoar', 'partner'] else '',
            "tags": json_data.get('tags', []),
            "use_cases": json_data.get('useCases', []),
            "categories": json_data.get('categories', [])
        }

        pack_id = get_pack_name(file_path)
        return {pack_id: pack_data}

    except Exception as exp:  # noqa
        print_error(f'Failed to process {file_path}, Error: {str(exp)}')
        raise


def get_mapper_data(path):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    type_ = json_data.get('type', '')  # can be 'mapping-outgoing' or 'mapping-incoming'
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    incidents_types = set()
    incidents_fields: set = set()

    default_incident_type = json_data.get('defaultIncidentType')
    if default_incident_type and default_incident_type != '':
        incidents_types.add(default_incident_type)
    mapping = json_data.get('mapping', {})
    for key, value in mapping.items():
        incidents_types.add(key)
        internal_mapping = value.get('internalMapping')  # get the mapping
        if type_ == 'mapping-outgoing':
            incident_fields_set = set()
            # incident fields are in the simple key or in complex.root key of each key
            for internal_mapping_key in internal_mapping.keys():
                fields_mapper = internal_mapping.get(internal_mapping_key, {})
                if isinstance(fields_mapper, dict):
                    incident_field_simple = fields_mapper.get('simple')
                    if incident_field_simple:
                        incident_fields_set.add(incident_field_simple)
                    else:
                        incident_field_complex = fields_mapper.get('complex', {})
                        if incident_field_complex and 'root' in incident_field_complex:
                            incident_fields_set.add(incident_field_complex.get('root'))
            incidents_fields = incidents_fields.union(incident_fields_set)
        elif type_ == 'mapping-incoming':
            # all the incident fields are the keys of the mapping
            incidents_fields = incidents_fields.union(set(internal_mapping.keys()))

    incidents_fields = {incident_field for incident_field in incidents_fields if incident_field not in BUILT_IN_FIELDS}
    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if incidents_types:
        data['incident_types'] = list(incidents_types)
    if incidents_fields:
        data['incident_fields'] = list(incidents_fields)

    return {id_: data}


def get_widget_data(path):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    scripts = ''

    # if the widget is script based - add it to the dependencies of the widget
    if json_data.get('dataType') == 'scripts':
        scripts = json_data.get('query')

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if scripts:
        data['scripts'] = [scripts]

    return {id_: data}


def get_dashboard_data(path):
    dashboard_data = get_json(path)
    layouts = dashboard_data.get('layout', {})
    return parse_dashboard_or_report_data(layouts, dashboard_data, path)


def get_report_data(path):
    report_data = get_json(path)
    layouts = report_data.get('dashboard', {}).get('layout')
    return parse_dashboard_or_report_data(layouts, report_data, path)


def parse_dashboard_or_report_data(all_layouts, data_file_json, path):
    id_ = data_file_json.get('id')
    name = data_file_json.get('name', '')
    fromversion = data_file_json.get('fromVersion')
    toversion = data_file_json.get('toVersion')
    pack = get_pack_name(path)
    scripts = set()
    if all_layouts:
        for layout in all_layouts:
            widget_data = layout.get('widget')
            if widget_data.get('dataType') == 'scripts':
                scripts.add(widget_data.get('query'))

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if scripts:
        data['scripts'] = list(scripts)

    return {id_: data}


def get_general_data(path):
    json_data = get_json(path)
    id_ = json_data.get('id')
    brandname = json_data.get('brandName', '')
    name = json_data.get('name', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)

    data = create_common_entity_data(path=path, name=name, to_version=toversion, from_version=fromversion, pack=pack)
    if brandname:  # for classifiers
        data['name'] = brandname
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
    try:
        if os.path.isfile(file_path):
            if find_type(file_path) in (FileType.INTEGRATION, FileType.BETA_INTEGRATION):
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(get_integration_data(file_path))
        else:
            # package integration
            package_name = os.path.basename(file_path)
            file_path = os.path.join(file_path, '{}.yml'.format(package_name))
            if os.path.isfile(file_path):
                # locally, might have leftover dirs without committed files
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(get_integration_data(file_path))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return res


def process_script(file_path: str, print_logs: bool) -> list:
    res = []
    try:
        if os.path.isfile(file_path):
            if find_type(file_path) == FileType.SCRIPT:
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(get_script_data(file_path))
        else:
            # package script
            unifier = Unifier(file_path)
            yml_path, code = unifier.get_script_or_integration_package_data()
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_script_data(yml_path, script_code=code))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return res


def process_incident_fields(file_path: str, print_logs: bool, incidents_types_list: list) -> list:
    """
    Process a incident_fields JSON file
    Args:
        file_path: The file path from incident field folder
        print_logs: Whether to print logs to stdout.
        incidents_types_list: List of all the incident types in the system.

    Returns:
        a list of incident field data.
    """
    res = []
    try:
        if find_type(file_path) == FileType.INCIDENT_FIELD:
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_incident_field_data(file_path, incidents_types_list))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise
    return res


def process_indicator_types(file_path: str, print_logs: bool, all_integrations: list) -> list:
    """
    Process a indicator types JSON file
    Args:
        file_path: The file path from indicator type folder
        print_logs: Whether to print logs to stdout
        all_integrations: The integrations section in the id set

    Returns:
        a list of indicator type data.
    """
    res = []
    try:
        # ignore old reputations.json files
        if not os.path.basename(file_path) == 'reputations.json' and find_type(file_path) == FileType.REPUTATION:
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_indicator_type_data(file_path, all_integrations))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return res


def process_general_items(file_path: str, print_logs: bool, expected_file_types: Tuple[FileType],
                          data_extraction_func: Callable) -> list:
    """
    Process a generic item file.
    expected file in one of the following:
    * classifier
    * incident type
    * indicator field
    * layout
    * layoutscontainer
    * mapper
    * playbook
    * report
    * widget

    Args:
        file_path: The file path from an item folder
        print_logs: Whether to print logs to stdout
        expected_file_types: specific file type to parse, will ignore the rest
        data_extraction_func: a function that given a file path will returns an ID set data dict.

    Returns:
        a list of item data.
    """
    res = []
    try:
        if find_type(file_path) in expected_file_types:
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(data_extraction_func(file_path))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

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
    script = None
    playbook = None
    try:
        if print_logs:
            print(f'adding {file_path} to id_set')
        if find_type(file_path) == FileType.TEST_SCRIPT:
            script = get_script_data(file_path)
        if find_type(file_path) == FileType.TEST_PLAYBOOK:
            playbook = get_playbook_data(file_path)
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return playbook, script


def get_integrations_paths(pack_to_create):
    if pack_to_create:
        path_list = [
            [pack_to_create, 'Integrations', '*']
        ]

    else:
        path_list = [
            ['Packs', '*', 'Integrations', '*']
        ]

    integration_files = list()
    for path in path_list:
        integration_files.extend(glob.glob(os.path.join(*path)))

    return integration_files


def get_playbooks_paths(pack_to_create):
    if pack_to_create:
        path_list = [
            [pack_to_create, 'Playbooks', '*.yml']
        ]

    else:
        path_list = [
            ['Packs', '*', 'Playbooks', '*.yml']
        ]

    playbook_files = list(pack_to_create)
    for path in path_list:
        playbook_files.extend(glob.glob(os.path.join(*path)))

    return playbook_files


def get_pack_metadata_paths(pack_to_create):
    if pack_to_create:
        path_list = [pack_to_create, 'pack_metadata.json']

    else:
        path_list = ['Packs', '*', 'pack_metadata.json']

    return glob.glob(os.path.join(*path_list))


def get_general_paths(path, pack_to_create):
    if pack_to_create:
        path_list = [
            [pack_to_create, path, '*']
        ]

    else:
        path_list = [
            [path, '*'],
            ['Packs', '*', path, '*']
        ]

    files = list()
    for path in path_list:
        files.extend(glob.glob(os.path.join(*path)))

    return files


class IDSetType(Enum):
    PLAYBOOK = 'playbooks'
    INTEGRATION = 'integrations'
    SCRIPT = 'scripts'
    TEST_PLAYBOOK = 'TestPlaybooks'
    WIDGET = 'Widgets'
    CLASSIFIER = 'Classifiers'
    MAPPER = 'Mappers'
    REPORT = 'Reports'
    DASHBOARD = 'Dashboards'
    INCIDENT_FIELD = 'IncidentFields'
    INCIDENT_TYPE = 'IncidentTypes'
    INDICATOR_FIELD = 'IndicatorFields'
    INDICATOR_TYPE = 'IndicatorTypes'
    LAYOUTS = 'Layouts'
    PACKS = 'Packs'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_  # type: ignore


class IDSet:
    def __init__(self, id_set_dict=None):
        self._id_set_dict = id_set_dict if id_set_dict else {}

    def get_dict(self):
        return self._id_set_dict

    def get_list(self, item_type):
        return self._id_set_dict.get(item_type, [])

    def add_to_list(self, object_type: IDSetType, obj):
        if not IDSetType.has_value(object_type):
            raise ValueError(f'Invalid IDSetType {object_type}')

        self._id_set_dict.setdefault(object_type, []).append(obj) if obj not in self._id_set_dict[object_type] else None

    def add_pack_to_id_set_packs(self, object_type: IDSetType, obj_name, obj_value):
        self._id_set_dict.setdefault(object_type, {}).update({obj_name: obj_value})


def merge_id_sets_from_files(first_id_set_path, second_id_set_path, output_id_set_path, print_logs: bool = True):
    """
    Merges two id sets. Loads them from files and saves the merged unified id_set into output_id_set_path.
    """
    with open(first_id_set_path, mode='r') as f1:
        first_id_set = json.load(f1)

    with open(second_id_set_path, mode='r') as f2:
        second_id_set = json.load(f2)

    unified_id_set, duplicates = merge_id_sets(first_id_set, second_id_set, print_logs)

    if unified_id_set:
        with open(output_id_set_path, mode='w', encoding='utf-8') as f:
            json.dump(unified_id_set.get_dict(), f, indent=4)

    return unified_id_set, duplicates


def merge_id_sets(first_id_set_dict: dict, second_id_set_dict: dict, print_logs: bool = True):
    """
    Merged two id_set dictionaries into single id_set. Returns the unified id_set dict.
    """
    duplicates = []
    united_id_set = IDSet(copy.deepcopy(first_id_set_dict))

    first_id_set = IDSet(first_id_set_dict)
    second_id_set = IDSet(second_id_set_dict)

    for object_type, object_list in second_id_set.get_dict().items():
        subset = first_id_set.get_list(object_type)

        if object_type != "Packs":
            for obj in object_list:
                obj_id = list(obj.keys())[0]
                is_duplicate = has_duplicate(subset, obj_id, object_type, print_logs,
                                             external_object=obj)
                if is_duplicate:
                    duplicates.append(obj_id)
                else:
                    united_id_set.add_to_list(object_type, obj)

        else:
            for obj_name, obj_value in object_list.items():
                united_id_set.add_pack_to_id_set_packs(object_type, obj_name, obj_value)

    if duplicates:
        return None, duplicates

    return united_id_set, []


def re_create_id_set(id_set_path: Optional[str] = DEFAULT_ID_SET_PATH, pack_to_create=None,  # noqa : C901
                     objects_to_create: list = None, print_logs: bool = True):
    """Re create the id set

    Args:
        id_set_path (str, optional): If passed an empty string will use default path. Pass in None to avoid saving the id set.
            Defaults to DEFAULT_ID_SET_PATH.
        pack_to_create: The input path. the default is the content repo.
        objects_to_create (list, optional): [description]. Defaults to None.

    Returns: id set object
    """
    if id_set_path == "":
        id_set_path = DEFAULT_ID_SET_PATH
    if id_set_path and os.path.exists(id_set_path):
        try:
            refresh_interval = int(os.getenv('DEMISTO_SDK_ID_SET_REFRESH_INTERVAL', -1))
        except ValueError:
            refresh_interval = -1
            print_color(
                "Re-creating id_set.\n"
                "DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var is set with value: "
                f"{os.getenv('DEMISTO_SDK_ID_SET_REFRESH_INTERVAL')} which is an illegal integer."
                "\nPlease modify or unset env var.", LOG_COLORS.YELLOW
            )
        if refresh_interval > 0:  # if file is newer than refersh interval use it as is
            mtime = os.path.getmtime(id_set_path)
            mtime_dt = datetime.fromtimestamp(mtime)
            target_time = time.time() - (refresh_interval * 60)
            if mtime >= target_time:
                print_color(
                    f"DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var is set and detected that current id_set: {id_set_path}"
                    f" modify time: {mtime_dt} "
                    "doesn't require a refresh. Will use current id set. "
                    "If you want to force an id set referesh unset DEMISTO_SDK_ID_SET_REFRESH_INTERVAL or set to -1.",
                    LOG_COLORS.GREEN)
                with open(id_set_path, mode="r") as f:
                    return json.load(f)
            else:
                print_color(f"DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var is set but current id_set: {id_set_path} "
                            f"modify time: {mtime_dt} is older than refresh interval. "
                            "Will re-generate the id set.", LOG_COLORS.GREEN)
        else:
            print_color("Note: DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var is not enabled. "
                        f"Will re-generate the id set even though file exists: {id_set_path}. "
                        "If you would like to avoid re-generating the id set every run, you can set the env var "
                        "DEMISTO_SDK_ID_SET_REFRESH_INTERVAL to a refresh interval in minutes.", LOG_COLORS.GREEN)
        print("")  # add an empty line for clarity

    if objects_to_create is None:
        objects_to_create = CONTENT_ENTITIES

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
    mappers_list = []
    packs_dict: Dict[str, Dict] = {}

    pool = Pool(processes=int(cpu_count()))

    print_color("Starting the creation of the id_set", LOG_COLORS.GREEN)

    with click.progressbar(length=len(objects_to_create), label="Progress of id set creation") as progress_bar:

        if 'Packs' in objects_to_create:
            print_color("\nStarting iteration over Packs", LOG_COLORS.GREEN)
            for pack_data in pool.map(partial(get_pack_metadata_data,
                                              print_logs=print_logs
                                              ),
                                      get_pack_metadata_paths(pack_to_create)):
                packs_dict.update(pack_data)

        progress_bar.update(1)

        if 'Integrations' in objects_to_create:
            print_color("\nStarting iteration over Integrations", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_integration,
                                        print_logs=print_logs
                                        ),
                                get_integrations_paths(pack_to_create)):
                integration_list.extend(arr)

        progress_bar.update(1)

        if 'Playbooks' in objects_to_create:
            print_color("\nStarting iteration over Playbooks", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.PLAYBOOK,),
                                        data_extraction_func=get_playbook_data,
                                        ),
                                get_playbooks_paths(pack_to_create)):
                playbooks_list.extend(arr)

        progress_bar.update(1)

        if 'Scripts' in objects_to_create:
            print_color("\nStarting iteration over Scripts", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_script,
                                        print_logs=print_logs
                                        ),
                                get_general_paths(SCRIPTS_DIR, pack_to_create)):
                scripts_list.extend(arr)

        progress_bar.update(1)

        if 'TestPlaybooks' in objects_to_create:
            print_color("\nStarting iteration over TestPlaybooks", LOG_COLORS.GREEN)
            for pair in pool.map(partial(process_test_playbook_path,
                                         print_logs=print_logs
                                         ),
                                 get_general_paths(TEST_PLAYBOOKS_DIR, pack_to_create)):
                if pair[0]:
                    testplaybooks_list.append(pair[0])
                if pair[1]:
                    scripts_list.append(pair[1])

        progress_bar.update(1)

        if 'Classifiers' in objects_to_create:
            print_color("\nStarting iteration over Classifiers", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.CLASSIFIER, FileType.OLD_CLASSIFIER),
                                        data_extraction_func=get_classifier_data,
                                        ),
                                get_general_paths(CLASSIFIERS_DIR, pack_to_create)):
                classifiers_list.extend(arr)

        progress_bar.update(1)

        if 'Dashboards' in objects_to_create:
            print_color("\nStarting iteration over Dashboards", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.DASHBOARD,),
                                        data_extraction_func=get_dashboard_data,
                                        ),
                                get_general_paths(DASHBOARDS_DIR, pack_to_create)):
                dashboards_list.extend(arr)

        progress_bar.update(1)

        if 'IncidentTypes' in objects_to_create:
            print_color("\nStarting iteration over Incident Types", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.INCIDENT_TYPE,),
                                        data_extraction_func=get_incident_type_data,
                                        ),
                                get_general_paths(INCIDENT_TYPES_DIR, pack_to_create)):
                incident_type_list.extend(arr)

        progress_bar.update(1)

        # Has to be called after 'IncidentTypes' is called
        if 'IncidentFields' in objects_to_create:
            print_color("\nStarting iteration over Incident Fields", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_incident_fields,
                                        print_logs=print_logs,
                                        incidents_types_list=incident_type_list
                                        ),
                                get_general_paths(INCIDENT_FIELDS_DIR, pack_to_create)):
                incident_fields_list.extend(arr)

        progress_bar.update(1)

        if 'IndicatorFields' in objects_to_create:
            print_color("\nStarting iteration over Indicator Fields", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.INDICATOR_FIELD,),
                                        data_extraction_func=get_general_data,
                                        ),
                                get_general_paths(INDICATOR_FIELDS_DIR, pack_to_create)):
                indicator_fields_list.extend(arr)

        progress_bar.update(1)

        # Has to be called after 'Integrations' is called
        if 'IndicatorTypes' in objects_to_create:
            print_color("\nStarting iteration over Indicator Types", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_indicator_types,
                                        print_logs=print_logs,
                                        all_integrations=integration_list
                                        ),
                                get_general_paths(INDICATOR_TYPES_DIR, pack_to_create)):
                indicator_types_list.extend(arr)

        progress_bar.update(1)

        if 'Layouts' in objects_to_create:
            print_color("\nStarting iteration over Layouts", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.LAYOUT,),
                                        data_extraction_func=get_layout_data,
                                        ),
                                get_general_paths(LAYOUTS_DIR, pack_to_create)):
                layouts_list.extend(arr)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.LAYOUTS_CONTAINER,),
                                        data_extraction_func=get_layoutscontainer_data,
                                        ),
                                get_general_paths(LAYOUTS_DIR, pack_to_create)):
                layouts_list.extend(arr)

        progress_bar.update(1)

        if 'Reports' in objects_to_create:
            print_color("\nStarting iteration over Reports", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.REPORT,),
                                        data_extraction_func=get_report_data,
                                        ),
                                get_general_paths(REPORTS_DIR, pack_to_create)):
                reports_list.extend(arr)

        progress_bar.update(1)

        if 'Widgets' in objects_to_create:
            print_color("\nStarting iteration over Widgets", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.WIDGET,),
                                        data_extraction_func=get_widget_data,
                                        ),
                                get_general_paths(WIDGETS_DIR, pack_to_create)):
                widgets_list.extend(arr)

        progress_bar.update(1)

        if 'Mappers' in objects_to_create:
            print_color("\nStarting iteration over Mappers", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_general_items,
                                        print_logs=print_logs,
                                        expected_file_types=(FileType.MAPPER,),
                                        data_extraction_func=get_mapper_data,
                                        ),
                                get_general_paths(MAPPERS_DIR, pack_to_create)):
                mappers_list.extend(arr)

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
    new_ids_dict['Mappers'] = sort(mappers_list)
    new_ids_dict['Packs'] = packs_dict

    exec_time = time.time() - start_time
    print_color("Finished the creation of the id_set. Total time: {} seconds".format(exec_time), LOG_COLORS.GREEN)
    duplicates = find_duplicates(new_ids_dict, print_logs)
    if any(duplicates) and print_logs:
        # TODO: should probably fail the entire process here
        print_error(
            f'The following ids were found duplicates\n{json.dumps(duplicates, indent=4)}\n'
        )

    return new_ids_dict


def find_duplicates(id_set, print_logs):
    lists_to_return = []

    for object_type in ID_SET_ENTITIES:
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
        print_color("Checking diff for Incident and Indicator Fields", LOG_COLORS.GREEN)

    fields = id_set['IncidentFields'] + id_set['IndicatorFields']
    field_ids = {list(field.keys())[0] for field in fields}

    field_list = []
    for field_to_check in field_ids:
        if has_duplicate(fields, field_to_check, 'Indicator and Incident Fields', print_logs):
            field_list.append(field_to_check)
    lists_to_return.append(field_list)

    return lists_to_return


def has_duplicate(id_set_subset_list, id_to_check, object_type=None, print_logs=True, external_object=None):
    """
    Finds if id_set_subset_list contains a duplicate items with the same id_to_check.

    Pass `external_object` to check if it exists in `id_set_subset_list`.
    Otherwise the function will check if `id_set_subset_list` contains 2 or more items with the id of `id_to_check`

    """
    duplicates = [duplicate for duplicate in id_set_subset_list if duplicate.get(id_to_check)]

    if external_object and len(duplicates) == 0:
        return False

    if not external_object and len(duplicates) == 1:
        return False

    if external_object:
        duplicates.append(external_object)

    for dup1, dup2 in itertools.combinations(duplicates, 2):
        dict1 = list(dup1.values())[0]
        dict2 = list(dup2.values())[0]
        dict1_from_version = LooseVersion(dict1.get('fromversion', '0.0.0'))
        dict2_from_version = LooseVersion(dict2.get('fromversion', '0.0.0'))
        dict1_to_version = LooseVersion(dict1.get('toversion', '99.99.99'))
        dict2_to_version = LooseVersion(dict2.get('toversion', '99.99.99'))

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
            print_warning('The following {} have the same ID ({}) and issues with versions: '
                          '"1.{}-{}", "2.{}-{}".'.format(object_type, id_to_check, dict1_from_version, dict1_to_version,
                                                         dict2_from_version, dict2_to_version))
            return True

        if print_logs and dict1.get('name') != dict2.get('name'):
            print_warning('The following {} have the same ID ({}) but different names: '
                          '"{}", "{}".'.format(object_type, id_to_check, dict1.get('name'), dict2.get('name')))

        # Checks if the Layouts kind is different then they are not duplicates
        if object_type == 'Layouts':
            if dict1.get('kind', '') != dict2.get('kind', ''):
                return False

        # If they have the same pack name they actually the same entity.
        # Added to support merge between two ID sets that contain the same pack.
        if dict1.get('pack') == dict2.get('pack'):
            return False

    return False


def sort(data):
    data.sort(key=lambda r: list(r.keys())[0].lower())  # Sort data by key value
    return data
