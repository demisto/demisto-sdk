import copy
import glob
import itertools
import os
import re
import time
from collections import OrderedDict
from datetime import datetime
from distutils.version import LooseVersion
from enum import Enum
from functools import partial
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import click
import networkx

from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR, COMMON_TYPES_PACK, CORRELATION_RULES_DIR,
                                                   DASHBOARDS_DIR, DEFAULT_CONTENT_ITEM_FROM_VERSION,
                                                   DEFAULT_CONTENT_ITEM_TO_VERSION, GENERIC_DEFINITIONS_DIR,
                                                   GENERIC_FIELDS_DIR, GENERIC_MODULES_DIR, GENERIC_TYPES_DIR,
                                                   INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR,
                                                   INDICATOR_TYPES_DIR, JOBS_DIR, LAYOUTS_DIR, LISTS_DIR, MAPPERS_DIR,
                                                   MODELING_RULES_DIR, PARSING_RULES_DIR, REPORTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR, TRIGGER_DIR, WIDGETS_DIR, WIZARDS_DIR,
                                                   XDRC_TEMPLATE_DIR, XSIAM_DASHBOARDS_DIR, XSIAM_REPORTS_DIR, FileType,
                                                   MarketplaceVersions)
from demisto_sdk.commands.common.content_constant_paths import (DEFAULT_ID_SET_PATH, MP_V2_ID_SET_PATH,
                                                                XPANSE_ID_SET_PATH)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type, get_current_repo, get_display_name, get_file,
                                               get_item_marketplaces, get_json, get_pack_name, get_yaml, print_color,
                                               print_error, print_warning)
from demisto_sdk.commands.unify.integration_script_unifier import IntegrationScriptUnifier

json = JSON_Handler()


CONTENT_ENTITIES = ['Packs', 'Integrations', 'Scripts', 'Playbooks', 'TestPlaybooks', 'Classifiers',
                    'Dashboards', 'IncidentFields', 'IncidentTypes', 'IndicatorFields', 'IndicatorTypes',
                    'Layouts', 'Reports', 'Widgets', 'Mappers', 'GenericTypes',
                    'GenericFields', 'GenericModules', 'GenericDefinitions', 'Lists', 'Jobs', 'Wizards']

ID_SET_ENTITIES = ['integrations', 'scripts', 'playbooks', 'TestPlaybooks', 'Classifiers',
                   'Dashboards', 'IncidentFields', 'IncidentTypes', 'IndicatorFields', 'IndicatorTypes',
                   'Layouts', 'Reports', 'Widgets', 'Mappers', 'GenericTypes', 'GenericFields', 'GenericModules',
                   'GenericDefinitions', 'Lists', 'Jobs', 'ParsingRules', 'ModelingRules',
                   'CorrelationRules', 'XSIAMDashboards', 'XSIAMReports', 'Triggers', 'Wizards', 'XDRCTemplates']

CONTENT_MP_V2_ENTITIES = ['Integrations', 'Scripts', 'Playbooks', 'TestPlaybooks', 'Classifiers',
                          'IncidentFields', 'IncidentTypes', 'IndicatorFields', 'IndicatorTypes',
                          'Layouts', 'Mappers', 'Packs', 'Lists', 'ParsingRules', 'ModelingRules',
                          'CorrelationRules', 'XSIAMDashboards', 'XSIAMReports', 'Triggers', 'XDRCTemplates']

ID_SET_MP_V2_ENTITIES = ['integrations', 'scripts', 'playbooks', 'TestPlaybooks', 'Classifiers',
                         'IncidentFields', 'IncidentTypes', 'IndicatorFields', 'IndicatorTypes',
                         'Layouts', 'Mappers', 'Lists', 'ParsingRules', 'ModelingRules',
                         'CorrelationRules', 'XSIAMDashboards', 'XSIAMReports', 'Triggers', 'XDRCTemplates']

CONTENT_XPANSE_ENTITIES = ['Packs', 'Integrations', 'Scripts', 'Playbooks', 'IncidentFields', 'IncidentTypes']

ID_SET_XPANSE_ENTITIES = ['integrations', 'scripts', 'playbooks', 'IncidentFields', 'IncidentTypes']


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


def add_item_to_exclusion_dict(excluded_items_from_id_set: dict, file_path: str, item_id: str) -> None:
    """
    Adds an item to the exclusion dict

    Args:
        excluded_items_from_id_set: the dict that holds the excluded items, aggregated by packs
        file_path: the file path of the item
        item_id: the ID of the item

    """
    pack_name = get_pack_name(file_path)
    item_type = find_type(file_path, ignore_sub_categories=True).value

    item_type = "classifier" if item_type == "classifier_5_9_9" else item_type
    excluded_items_from_id_set[pack_name] = {(item_type, item_id)}  # set of tuples


def does_dict_have_alternative_key(data: dict) -> bool:
    """
        Check if a key that ends with "_x2" exists in the dict (including inner levels)
        Args:
            data (dict): the data dict to search in

        Returns: True if found such a key, else False

    """

    # start searching in the first level keys
    for key in data:
        if isinstance(key, str) and key.endswith('_x2'):
            return True

    for key, value in data.items():
        if isinstance(value, dict):
            if does_dict_have_alternative_key(value):
                return True

    return False


def should_skip_item_by_mp(file_path: str, marketplace: str, excluded_items_from_id_set: dict,
                           packs: Dict[str, Dict] = None, print_logs: bool = False, item_type: str = None):
    """
    Checks if the item given (as path) should be part of the current generated id set.
     The checks are in this order:
     1. Check if the given item has the right marketplaces under the 'marketplaces' in the item's file,
     2. Otherwise, we check if the item is inside a pack that it's pack metadata 'marketplaces' field does not include
     the current marketplace we are creating this id set for.
     If there are no 'marketplaces' fields in the the item's file and the metadata, the item is set as xsoar only.

    Args:
        file_path: path to content item
        marketplace: the marketplace this current generated id set is for
        excluded_items_from_id_set: the dict that holds the excluded items, aggregated by packs
        packs: the pack mapping from the ID set.
        print_logs: whether to pring logs
        item_type: The item type.

    Returns: True if should be skipped, else False

    """

    if not marketplace:
        return False

    # first check, check field 'marketplaces' in the item's file
    file_type = Path(file_path).suffix
    try:
        item_data = get_file(file_path, file_type)
    except (ValueError, FileNotFoundError, IsADirectoryError):
        return True

    item_marketplaces = get_item_marketplaces(file_path, item_data=item_data, packs=packs, item_type=item_type)
    if marketplace not in item_marketplaces:
        if print_logs:
            print(f'Skipping {file_path} due to mismatch with the given marketplace')

        if "pack_metadata" not in file_path:  # only add pack items to the exclusion dict, not whole packs
            add_item_to_exclusion_dict(excluded_items_from_id_set, file_path,
                                       item_data.get("id", item_data.get('commonfields', {}).get('id', '')))
        return True

    return False


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


def get_lists_names_from_playbook(data_dictionary: dict, graph: networkx.DiGraph) -> tuple:
    lists_names = set()
    lists_names_skippable = set()
    tasks = data_dictionary.get('tasks', {})
    lists_tasks_scripts = ['Builtin|||setList', 'Builtin|||getList']
    for task_id, task in tasks.items():
        script = task.get('task', {}).get('script')
        if script in lists_tasks_scripts:
            list_name = task.get('scriptarguments', {}).get('listName', {}).get('simple')

            try:
                skippable = not graph.nodes[task_id]['mandatory']
            except KeyError:
                # if task id not in the graph - the task is unreachable.
                print_error(f'{data_dictionary["id"]}: task {task_id} is not connected')
                continue
            if list_name:
                lists_names.add(list_name)
                if skippable:
                    lists_names_skippable.add(list_name)

    return list(lists_names), list(lists_names_skippable)


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


def get_filters_and_transformers_from_complex_value(complex_value: dict) -> Tuple[list, list]:
    all_filters = set()
    all_transformers = set()

    # add the filters to all_filters set
    filters = complex_value.get('filters', [])
    for tmp_filter in filters:
        if tmp_filter:
            operator = tmp_filter[0].get('operator')
            all_filters.add(operator)

    # add the transformers to all_transformers set
    transformers = complex_value.get('transformers', [])
    for tmp_transformer in transformers:
        if tmp_transformer:
            operator = tmp_transformer.get('operator')
            all_transformers.add(operator)

    return list(all_transformers), list(all_filters)


def get_filters_and_transformers_from_playbook(data_dict: dict) -> Tuple[list, list]:
    all_filters = set()
    all_transformers = set()

    # collect complex values from playbook inputs
    inputs = data_dict.get('inputs', [])
    complex_values = [_input.get('value', {}).get('complex', {}) for _input in inputs]

    # gets the playbook tasks
    tasks = data_dict.get('tasks', {})

    # collect complex values from playbook tasks
    for task in tasks.values():
        # gets the task value
        if task.get('type') == 'condition':
            for condition_entry in task.get('conditions', []):
                for inner_condition in condition_entry.get('condition', []):
                    if inner_condition:
                        for condition in inner_condition:
                            complex_values.append(condition.get('left', {}).get('value', {}).get('complex', {}))
                            complex_values.append(condition.get('right', {}).get('value', {}).get('complex', {}))
        else:
            complex_values.append(task.get('scriptarguments', {}).get('value', {}).get('complex', {}))

    # get transformers and filters from the values
    for complex_value in complex_values:
        if complex_value:
            transformers, filters = get_filters_and_transformers_from_complex_value(complex_value)
            all_transformers.update(transformers)
            all_filters.update(filters)

    return list(all_transformers), list(all_filters)


def get_integration_api_modules(file_path, data_dictionary, is_unified_integration):
    unifier = IntegrationScriptUnifier(os.path.dirname(file_path))
    if is_unified_integration:
        integration_script_code = data_dictionary.get('script', {}).get('script', '')
    else:
        _, integration_script_code = unifier.get_script_or_integration_package_data()

    return list(unifier.check_api_module_imports(integration_script_code).values())


def get_integration_data(file_path, packs: Dict[str, Dict] = None):
    data_dictionary = get_yaml(file_path)

    is_unified_integration = data_dictionary.get('script', {}).get('script', '') not in ['-', '']

    id_ = data_dictionary.get('commonfields', {}).get('id', '-')
    name = data_dictionary.get('name', '-')
    display_name = get_display_name(file_path, data_dictionary)
    script = data_dictionary.get('script', {})

    type_ = script.get('type', '')
    if type_ == 'python':
        type_ = script.get('subtype', type_)
    deprecated = data_dictionary.get('deprecated', False)
    tests = data_dictionary.get('tests')
    toversion = data_dictionary.get('toversion')
    fromversion = data_dictionary.get('fromversion')
    docker_image = script.get('dockerimage')
    commands = script.get('commands', [])
    cmd_list = [command.get('name') for command in commands]
    pack = get_pack_name(file_path)
    integration_api_modules = get_integration_api_modules(file_path, data_dictionary, is_unified_integration)
    default_classifier = data_dictionary.get('defaultclassifier')
    default_incident_type = data_dictionary.get('defaultIncidentType')
    is_fetch = script.get('isfetch', False)
    is_feed = script.get('feed', False)
    marketplaces = get_item_marketplaces(file_path, item_data=data_dictionary, packs=packs)
    mappers = set()

    deprecated_commands = []
    for command in commands:
        if command.get('deprecated', False):
            deprecated_commands.append(command.get('name'))

    for mapper in ['defaultmapperin', 'defaultmapperout']:
        if data_dictionary.get(mapper):
            mappers.add(data_dictionary.get(mapper))
    integration_data = create_common_entity_data(path=file_path,
                                                 name=name,
                                                 display_name=display_name,
                                                 to_version=toversion,
                                                 from_version=fromversion,
                                                 pack=pack,
                                                 marketplaces=marketplaces,
                                                 )
    if type_:
        integration_data['type'] = type_
    if docker_image:
        integration_data['docker_image'] = docker_image
    if cmd_list:
        integration_data['commands'] = cmd_list
    if tests:
        integration_data['tests'] = tests
    if deprecated:
        integration_data['deprecated'] = deprecated
    if deprecated_commands:
        integration_data['deprecated_commands'] = deprecated_commands
    if integration_api_modules:
        integration_data['api_modules'] = integration_api_modules
    if default_classifier and default_classifier != '':
        integration_data['classifiers'] = default_classifier
    if mappers:
        integration_data['mappers'] = list(mappers)
    if default_incident_type and default_incident_type != '':
        integration_data['incident_types'] = default_incident_type
    if is_fetch:
        integration_data['is_fetch'] = is_fetch
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


def get_playbook_data(file_path: str, packs: Dict[str, Dict] = None) -> dict:
    data_dictionary = get_yaml(file_path)
    graph = build_tasks_graph(data_dictionary)

    id_ = data_dictionary.get('id', '-')
    name = data_dictionary.get('name', '-')
    display_name = get_display_name(file_path, data_dictionary)
    deprecated = data_dictionary.get('hidden', False)
    tests = data_dictionary.get('tests')
    toversion = data_dictionary.get('toversion')
    fromversion = data_dictionary.get('fromversion')
    marketplaces = get_item_marketplaces(file_path, item_data=data_dictionary, packs=packs)

    implementing_scripts, implementing_scripts_skippable = get_task_ids_from_playbook('scriptName',
                                                                                      data_dictionary,
                                                                                      graph
                                                                                      )
    implementing_playbooks, implementing_playbooks_skippable = get_task_ids_from_playbook('playbookName',
                                                                                          data_dictionary,
                                                                                          graph
                                                                                          )
    implementing_lists, implementing_lists_skippable = get_lists_names_from_playbook(data_dictionary, graph)
    command_to_integration, command_to_integration_skippable = get_commands_from_playbook(data_dictionary)
    skippable_tasks = (implementing_scripts_skippable + implementing_playbooks_skippable +
                       command_to_integration_skippable + implementing_lists_skippable)
    pack = get_pack_name(file_path)
    dependent_incident_fields, dependent_indicator_fields = get_dependent_incident_and_indicator_fields(data_dictionary)

    playbook_data = create_common_entity_data(path=file_path, name=name, display_name=display_name, to_version=toversion,
                                              from_version=fromversion, pack=pack, marketplaces=marketplaces)

    transformers, filters = get_filters_and_transformers_from_playbook(data_dictionary)

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
    if filters:
        playbook_data['filters'] = filters
    if transformers:
        playbook_data['transformers'] = transformers
    if implementing_lists:
        playbook_data['lists'] = implementing_lists
    if does_dict_have_alternative_key(data_dictionary):
        playbook_data['has_alternative_meta'] = True

    return {id_: playbook_data}


def get_script_data(file_path, script_code=None, packs: Dict[str, Dict] = None):
    data_dictionary = get_yaml(file_path)
    id_ = data_dictionary.get('commonfields', {}).get('id', '-')
    if script_code is None:
        script_code = data_dictionary.get('script', '')

    name = data_dictionary.get('name', '-')
    display_name = get_display_name(file_path, data_dictionary)
    type_ = data_dictionary.get('type', '')
    if type_ == 'python':
        type_ = data_dictionary.get('subtype', type_)
    tests = data_dictionary.get('tests')
    toversion = data_dictionary.get('toversion')
    deprecated = data_dictionary.get('deprecated', False)
    fromversion = data_dictionary.get('fromversion')
    docker_image = data_dictionary.get('dockerimage')
    depends_on, command_to_integration = get_depends_on(data_dictionary)
    script_executions = sorted(list(set(re.findall(r"execute_?command\(['\"](\w+)['\"].*", script_code, re.IGNORECASE))))
    pack = get_pack_name(file_path)
    marketplaces = get_item_marketplaces(file_path, item_data=data_dictionary, packs=packs)

    if 'Packs' in file_path and not file_path.startswith('Packs'):
        file_path = file_path[file_path.index('Packs'):]

    script_data = create_common_entity_data(path=file_path, name=name, display_name=display_name, to_version=toversion,
                                            from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if type_:
        script_data['type'] = type_
    if deprecated:
        script_data['deprecated'] = deprecated
    if depends_on:
        script_data['depends_on'] = depends_on
    if script_executions:
        script_data['script_executions'] = script_executions
    if command_to_integration:
        script_data['command_to_integration'] = command_to_integration
    if docker_image:
        script_data['docker_image'] = docker_image
    if tests:
        script_data['tests'] = tests
    if does_dict_have_alternative_key(data_dictionary):
        script_data['has_alternative_meta'] = True

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


def get_layout_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    layout = json_data.get('layout', {})
    name = layout.get('name', '-')
    display_name = get_display_name(path, json_data)
    id_ = json_data.get('id', layout.get('id', '-'))
    type_ = json_data.get('typeId')
    type_name = json_data.get('TypeName')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    kind = json_data.get('kind')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    incident_indicator_types_dependency = {id_}
    incident_indicator_fields_dependency = get_values_for_keys_recursively(json_data, ['fieldId'])
    definition_id = json_data.get('definitionId')
    tabs = layout.get('tabs', [])
    scripts = get_layouts_scripts_ids(tabs)

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
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
    if definition_id:
        data['definitionId'] = definition_id
    if scripts:
        data['scripts'] = scripts

    return {id_: data}


def get_layouts_scripts_ids(layout_tabs):
    """
    Finds all scripts IDs of a certain layout or layouts container.

    Args:
        layout_tabs: (List) Tabs list of a layout or a layouts container

    Returns:
        A list of all scripts IDs in a certain layout or layouts container
    """
    scripts = []

    for tab in layout_tabs:
        if isinstance(tab, dict):
            tab_sections = tab.get('sections', [])
            for section in tab_sections:

                # Find dynamic sections scripts:
                query_type = section.get('queryType')
                if query_type == 'script':
                    script_id = section.get('query')
                    if script_id:
                        scripts.append(script_id)

                # Find Buttons scripts:
                items = section.get('items', [])
                if items:
                    for item in items:
                        script_id = item.get('scriptId')
                        if script_id:
                            scripts.append(script_id)

    return scripts


def get_layoutscontainer_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)
    layouts_container_fields = ["group", "edit", "indicatorsDetails", "indicatorsQuickView", "quickView", "close",
                                "details", "detailsV2", "mobile"]
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    data = create_common_entity_data(path=path, name=json_data.get('name'),
                                     display_name=get_display_name(path, json_data),
                                     to_version=json_data.get('toVersion'),
                                     from_version=json_data.get('fromVersion'),
                                     pack=pack,
                                     marketplaces=marketplaces,
                                     )
    data.update(OrderedDict({field: json_data[field] for field in layouts_container_fields if json_data.get(field)}))

    id_ = json_data.get('id')
    incident_indicator_types_dependency = {id_}
    incident_indicator_fields_dependency = get_values_for_keys_recursively(json_data, ['fieldId'])
    definition_id = json_data.get('definitionId')
    if data.get('name'):
        incident_indicator_types_dependency.add(data['name'])
    data['incident_and_indicator_types'] = list(incident_indicator_types_dependency)
    if incident_indicator_fields_dependency['fieldId']:
        data['incident_and_indicator_fields'] = incident_indicator_fields_dependency['fieldId']
    if definition_id:
        data['definitionId'] = definition_id

    return {id_: data}


def get_incident_field_data(path: str, incident_types: List, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    all_associated_types: set = set()
    all_scripts = set()

    associated_types = json_data.get('associatedTypes')
    if associated_types:
        all_associated_types = set(associated_types)

    system_associated_types = json_data.get('systemAssociatedTypes')
    if system_associated_types:
        all_associated_types = all_associated_types.union(set(system_associated_types))

    if 'all' in all_associated_types:
        all_associated_types = {list(incident_type.keys())[0] for incident_type in incident_types}

    scripts = json_data.get('script')
    if scripts:
        all_scripts = {scripts}

    field_calculations_scripts = json_data.get('fieldCalcScript')
    if field_calculations_scripts:
        all_scripts = all_scripts.union({field_calculations_scripts})

    # save cliName and name of all aliases fields in a single list
    aliases: List[str] = sum(([field['cliName'], field['name']] for field in json_data.get('Aliases', [])), [])
    cli_name = json_data.get('cliName')

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)

    if all_associated_types:
        data['incident_types'] = list(all_associated_types)
    if all_scripts:
        data['scripts'] = list(all_scripts)
    if aliases:
        data['aliases'] = aliases
    if cli_name:
        data['cliname'] = cli_name
    if does_dict_have_alternative_key(json_data):
        data['has_alternative_meta'] = True

    return {id_: data}


def get_indicator_type_data(path: str, all_integrations: List, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('details', '')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    reputation_command = json_data.get('reputationCommand')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
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

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if associated_integrations:
        data['integrations'] = list(associated_integrations)
    if all_scripts:
        data['scripts'] = list(all_scripts)

    return {id_: data}


def get_incident_type_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    playbook_id = json_data.get('playbookId')
    pre_processing_script = json_data.get('preProcessingScript')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if playbook_id and playbook_id != '':
        data['playbooks'] = playbook_id
    if pre_processing_script and pre_processing_script != '':
        data['scripts'] = pre_processing_script

    return {id_: data}


def get_classifier_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    incidents_types = set()
    transformers: List[str] = []
    filters: List[str] = []
    definition_id = json_data.get('definitionId')

    default_incident_type = json_data.get('defaultIncidentType')
    if default_incident_type and default_incident_type != '':
        incidents_types.add(default_incident_type)
    key_type_map = json_data.get('keyTypeMap', {})
    for key, value in key_type_map.items():
        incidents_types.add(value)

    transformer = json_data.get('transformer', {})
    if transformer is dict:
        complex_value = transformer.get('complex', {})
        if complex_value:
            transformers, filters = get_filters_and_transformers_from_complex_value(complex_value)

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if incidents_types:
        data['incident_types'] = list(incidents_types)
    if filters:
        data['filters'] = filters
    if transformers:
        data['transformers'] = transformers
    if definition_id:
        data['definitionId'] = definition_id

    return {id_: data}


def create_common_entity_data(path, name, display_name, to_version, from_version, pack, marketplaces):
    data = OrderedDict()
    if name:
        data['name'] = name
    if display_name:
        data['display_name'] = display_name
    data['file_path'] = path
    data['source'] = list(get_current_repo())
    if to_version:
        data['toversion'] = to_version
    if from_version:
        data['fromversion'] = from_version
    if pack:
        data['pack'] = pack
    data['marketplaces'] = marketplaces

    return data


def get_pack_metadata_data(file_path, print_logs: bool, marketplace: str = ''):
    try:
        if print_logs:
            print(f'adding {file_path} to id_set')

        if should_skip_item_by_mp(file_path, marketplace, {}, print_logs=print_logs):
            return {}

        json_data = get_json(file_path)
        pack_data = {
            "name": json_data.get('name'),
            "current_version": json_data.get('currentVersion'),
            'source': get_current_repo(),
            "author": json_data.get('author', ''),
            'certification': 'certified' if json_data.get('support', '').lower() in ['xsoar', 'partner'] else '',
            "tags": json_data.get('tags', []),
            "use_cases": json_data.get('useCases', []),
            "categories": json_data.get('categories', []),
            "marketplaces": json_data.get('marketplaces', [MarketplaceVersions.XSOAR.value]),
        }

        pack_id = get_pack_name(file_path)
        return {pack_id: pack_data}

    except Exception as exp:  # noqa
        print_error(f'Failed to process {file_path}, Error: {str(exp)}')
        raise


def get_mapper_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    type_ = json_data.get('type', '')  # can be 'mapping-outgoing' or 'mapping-incoming'
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    incidents_types = set()
    incidents_fields: set = set()
    all_transformers = set()
    all_filters = set()
    definition_id = json_data.get('definitionId')

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

        # get_filters_and_transformers_from_complex_value(list(value.get('internalMapping', {}).values())[0]['complex'])
        for internal_mapping in internal_mapping.values():
            incident_field_complex = internal_mapping.get('complex', {})
            if incident_field_complex:
                transformers, filters = get_filters_and_transformers_from_complex_value(incident_field_complex)
                all_transformers.update(transformers)
                all_filters.update(filters)

    incidents_fields = {incident_field for incident_field in incidents_fields if incident_field not in BUILT_IN_FIELDS}
    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if incidents_types:
        data['incident_types'] = list(incidents_types)
    if incidents_fields:
        data['incident_fields'] = list(incidents_fields)
    if all_filters:
        data['filters'] = list(all_filters)
    if all_transformers:
        data['transformers'] = list(all_transformers)
    if definition_id:
        data['definitionId'] = definition_id
    if does_dict_have_alternative_key(json_data):
        data['has_alternative_meta'] = True

    return {id_: data}


def get_widget_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    scripts = ''

    # if the widget is script based - add it to the dependencies of the widget
    if json_data.get('dataType') == 'scripts':
        scripts = json_data.get('query')

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if scripts:
        data['scripts'] = [scripts]

    return {id_: data}


def get_dashboard_data(path: str, packs: Dict[str, Dict] = None):
    dashboard_data = get_json(path)
    layouts = dashboard_data.get('layout', {})
    return parse_dashboard_or_report_data(path, dashboard_data, layouts, packs)


def get_report_data(path: str, packs: Dict[str, Dict] = None):
    report_data = get_json(path)
    layouts = report_data.get('dashboard', {}).get('layout')
    return parse_dashboard_or_report_data(path, report_data, layouts, packs)


def parse_dashboard_or_report_data(path: str, data_file_json: Dict, all_layouts: List, packs: Dict[str, Dict] = None):
    id_ = data_file_json.get('id')
    name = data_file_json.get('name', '')
    display_name = get_display_name(path, data_file_json)
    fromversion = data_file_json.get('fromVersion')
    toversion = data_file_json.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=data_file_json, packs=packs)

    scripts = set()
    if all_layouts:
        for layout in all_layouts:
            widget_data = layout.get('widget')
            if widget_data.get('dataType') == 'scripts':
                scripts.add(widget_data.get('query'))

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if scripts:
        data['scripts'] = list(scripts)

    return {id_: data}


def get_general_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)
    id_ = json_data.get('id')
    display_name = get_display_name(path, json_data)

    if find_type(path) in [FileType.XSIAM_DASHBOARD, FileType.XSIAM_REPORT]:
        json_data = json_data.get('dashboards_data', [{}])[0] if 'dashboards_data' in json_data else json_data.get('templates_data', [{}])[0]
        id_ = json_data.get('global_id')

    brandname = json_data.get('brandName', '')
    name = json_data.get('name', '')
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if brandname:  # for classifiers
        data['name'] = brandname
    return {id_: data}


def get_xsiam_dashboard_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path).get('dashboards_data', [{}])[0]

    id_ = json_data.get('global_id')
    name = json_data.get('name')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = [MarketplaceVersions.MarketplaceV2.value]

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)

    return {id_: data}


def get_xsiam_report_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path).get('templates_data', [{}])[0]

    id_ = json_data.get('global_id')
    name = json_data.get('report_name')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = [MarketplaceVersions.MarketplaceV2.value]

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)

    return {id_: data}


def get_trigger_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('trigger_id')
    name = json_data.get('trigger_name')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = [MarketplaceVersions.MarketplaceV2.value]

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)

    return {id_: data}


def get_parsing_rule_data(path: str, packs: Dict[str, Dict] = None):
    yaml_data = get_yaml(path)

    id_ = yaml_data.get('id')  # TODO: Need to change to the correct id field
    name = yaml_data.get('name')
    display_name = get_display_name(path, yaml_data)
    fromversion = yaml_data.get('fromversion')
    toversion = yaml_data.get('toversion')
    pack = get_pack_name(path)
    marketplaces = [MarketplaceVersions.MarketplaceV2.value]

    if not id_ and 'marketplacev2' in marketplaces:  # TODO: Should be removed after we have an agreed id field for parsing rule
        id_ = f"{pack}-{os.path.basename(path).split('.')[0]}"

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    return {id_: data}


def get_modeling_rule_data(path: str, packs: Dict[str, Dict] = None):
    yaml_data = get_yaml(path)

    id_ = yaml_data.get('id')  # TODO: Need to change to the correct id field
    name = yaml_data.get('name')
    display_name = get_display_name(path, yaml_data)
    fromversion = yaml_data.get('fromversion')
    toversion = yaml_data.get('toversion')
    pack = get_pack_name(path)
    marketplaces = [MarketplaceVersions.MarketplaceV2.value]

    if not id_ and 'marketplacev2' in marketplaces:  # TODO: Should be removed after we have an agreed id field for modeling rule
        id_ = f"{pack}-{os.path.basename(path).split('.')[0]}"

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    return {id_: data}


def get_correlation_rule_data(path: str, packs: Dict[str, Dict] = None):
    yaml_data = get_yaml(path)

    id_ = yaml_data.get('global_rule_id')
    name = yaml_data.get('name')
    display_name = get_display_name(path, yaml_data)
    fromversion = yaml_data.get('fromversion')
    toversion = yaml_data.get('toversion')
    pack = get_pack_name(path)
    marketplaces = [MarketplaceVersions.MarketplaceV2.value]

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    return {id_: data}


def get_xdrc_template_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('content_global_id')
    name = json_data.get('name')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('from_xdr_version')
    toversion = json_data.get('to_xdr_version')
    pack = get_pack_name(path)
    marketplaces = [MarketplaceVersions.MarketplaceV2.value]

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)

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


def process_integration(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool) -> Tuple[list, dict]:
    """
    Process integration dir or file

    Arguments:
        file_path: The file path to integration file.
        packs: The pack mapping from the ID set.
        marketplace: The marketplace this id set is designated for.
        print_logs: Whether to print logs to stdout.

    Returns:
        integration data list (may be empty), a dict of excluded items from the id set
    """
    res = []
    excluded_items_from_id_set: dict = {}
    try:
        if os.path.isfile(file_path):
            if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
                return [], excluded_items_from_id_set
            if find_type(file_path) in (FileType.INTEGRATION, FileType.BETA_INTEGRATION):
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(get_integration_data(file_path, packs=packs))
        else:
            # package integration
            package_name = os.path.basename(file_path)
            file_path = os.path.join(file_path, '{}.yml'.format(package_name))
            if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
                return [], excluded_items_from_id_set
            if os.path.isfile(file_path):
                # locally, might have leftover dirs without committed files
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(get_integration_data(file_path, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return res, excluded_items_from_id_set


def process_script(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool) -> Tuple[list, dict]:
    """
    Process script dir or file

    Arguments:
        file_path: the file path to script file.
        packs: The pack mapping from the ID set.
        marketplace: The marketplace this id set is designated for.
        print_logs: Whether to print logs to stdout.

    Returns:
        script data list (may be empty), a dict of excluded items from the id set
    """
    res = []
    excluded_items_from_id_set: dict = {}
    try:
        if os.path.isfile(file_path):
            if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
                return [], excluded_items_from_id_set
            if find_type(file_path) == FileType.SCRIPT:
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(get_script_data(file_path, packs=packs))
        else:
            # package script
            unifier = IntegrationScriptUnifier(file_path)
            yml_path, code = unifier.get_script_or_integration_package_data()
            if should_skip_item_by_mp(yml_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
                return [], excluded_items_from_id_set
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_script_data(yml_path, script_code=code, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return res, excluded_items_from_id_set


def process_incident_fields(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool, incident_types: List) -> \
        Tuple[list, dict]:
    """
    Process a incident_fields JSON file
    Args:
        file_path: The file path from incident field folder.
        packs: The pack mapping from the ID set.
        marketplace: The marketplace this id set is designated for.
        print_logs: Whether to print logs to stdout.
        incident_types: List of all the incident types in the system.

    Returns:
        a list of incident field data, a dict of excluded items from the id set
    """
    res = []
    excluded_items_from_id_set: dict = {}
    try:
        if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
            return [], excluded_items_from_id_set
        if find_type(file_path) == FileType.INCIDENT_FIELD:
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_incident_field_data(file_path, incident_types, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise
    return res, excluded_items_from_id_set


def process_indicator_types(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool, all_integrations: list) -> \
        Tuple[list, dict]:
    """
    Process a indicator types JSON file
    Args:
        file_path: The file path from indicator type folder
        packs: The pack mapping from the ID set.
        marketplace: The marketplace this id set is designated for.
        print_logs: Whether to print logs to stdout.
        all_integrations: The integrations section in the id-set.

    Returns:
        a list of indicator type data, a dict of excluded items from the id set
    """
    res = []
    excluded_items_from_id_set: dict = {}

    try:
        if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
            if print_logs:
                print(f'Skipping {file_path} due to mismatch with the marketplace this id set is generated for.')
            return [], excluded_items_from_id_set
        # ignore old reputations.json files
        if not os.path.basename(file_path) == 'reputations.json' and find_type(file_path) == FileType.REPUTATION:
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_indicator_type_data(file_path, all_integrations, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return res, excluded_items_from_id_set


def process_generic_items(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool,
                          generic_types_list: list = None) -> Tuple[list, dict]:
    """
    Process a generic field JSON file
    Args:
        file_path: The file path from object field folder.
        packs: The pack mapping from the ID set.
        marketplace: The marketplace this id set is designated for.
        print_logs: Whether to print logs to stdout.
        generic_types_list: List of all the generic types in the system.

    Returns:
        a list of generic items data: fields or types, a dict of excluded items from the id set
    """
    res = []
    excluded_items_from_id_set: dict = {}

    try:
        if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
            return [], excluded_items_from_id_set
        if find_type(file_path) == FileType.GENERIC_FIELD:
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_generic_field_data(file_path, generic_types_list, packs=packs))
        elif find_type(file_path) == FileType.GENERIC_TYPE:
            if print_logs:
                print(f'adding {file_path} to id_set')
            res.append(get_generic_type_data(file_path, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise
    return res, excluded_items_from_id_set


def process_jobs(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool) -> list:
    """
    Process a JSON file representing a Job object.
    Args:
        file_path: The file path from object field folder.
        packs: The pack mapping from the ID set.
        marketplace: The marketplace that this ID set is designated for.
        print_logs: Whether to print logs to stdout.

    Returns:
        a list of Job data.
    """
    result: List = []
    try:
        if should_skip_item_by_mp(file_path, marketplace, {}, packs=packs, print_logs=print_logs):
            return []
        if find_type(file_path) == FileType.JOB:
            if print_logs:
                print(f'adding {file_path} to id_set')
            result.append(get_job_data(file_path, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process job {file_path}, Error: {str(exp)}')
        raise
    return result


def process_wizards(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool) -> list:
    """
    Process a JSON file representing a Wizard object.
    Args:
        file_path: The file path from object field folder.
        packs: The pack mapping from the ID set.
        marketplace: The marketplace that this ID set is designated for.
        print_logs: Whether to print logs to stdout.

    Returns:
        a list of Wizard data.
    """
    result: List = []
    try:
        if should_skip_item_by_mp(file_path, marketplace, {}, packs=packs, print_logs=print_logs):
            return []
        if find_type(file_path) == FileType.WIZARD:
            if print_logs:
                print(f'adding {file_path} to id_set')
            result.append(get_wizard_data(file_path, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process wizard {file_path}, Error: {str(exp)}')
        raise
    return result


def process_layoutscontainers(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool) -> Tuple[List, Dict]:
    """
    Process a JSON file representing a Layoutcontainer object.
    Args:
        file_path: The file path from object field folder.
        packs: The pack mapping from the ID set.
        marketplace: The marketplace this id set is designated for.
        print_logs: Whether to print logs to stdout.

    Returns:
        a list of Layoutcontainer data.
    """

    result: List = []
    excluded_items_from_id_set: Dict = {}

    try:
        if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs):
            return result, excluded_items_from_id_set

        if find_type(file_path) != FileType.LAYOUTS_CONTAINER:
            if print_logs:
                print(f'Recieved an invalid layoutcontainer file: {file_path}, Ignoring.')
            return result, excluded_items_from_id_set

        layout_data = get_layoutscontainer_data(file_path, packs=packs)

        # only indicator layouts are supported in marketplace v2.
        layout_group = list(layout_data.values())[0].get('group')
        if marketplace == MarketplaceVersions.MarketplaceV2.value and layout_group == 'incident':
            print(f'incident layoutcontainer "{file_path}" is not supported in marketplace v2, excluding.')
            add_item_to_exclusion_dict(excluded_items_from_id_set, file_path, list(layout_data.keys())[0])
            return result, excluded_items_from_id_set

        if print_logs:
            print(f'adding {file_path} to id_set')
        result.append(layout_data)

    except Exception as exp:  # noqa
        print_error(f'failed to process layoutcontainer {file_path}, Error: {str(exp)}')
        raise

    return result, excluded_items_from_id_set


def process_general_items(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool,
                          expected_file_types: Tuple[FileType], data_extraction_func: Callable, suffix: str = 'yml') -> Tuple[list, dict]:
    """
    Process a general item file.
    expected file in one of the following:
    * classifier
    * incident type
    * indicator field
    * layout
    * mapper
    * playbook
    * report
    * widget
    * list
    * ParsingRules
    * ModelingRules
    * CorrelationRules
    * XSIAMDashboards
    * XSIAMReports
    * Triggers
    * XDRCTemplates

    Args:
        file_path: The file path from an item folder
        packs: the pack mapping from the ID set.
        marketplace: the marketplace this id set is designated for.
        print_logs: Whether to print logs to stdout
        expected_file_types: specific file type to parse, will ignore the rest
        data_extraction_func: a function that given a file path will return an id-set data dict.
        suffix: specific suffix of the desired file.

    Returns:
        a list of item data, a dict of excluded items from the id set
    """
    res = []
    excluded_items_from_id_set: dict = {}
    try:
        if os.path.isfile(file_path):
            item_type = find_type(file_path)
            if item_type in expected_file_types:
                if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs, item_type=item_type):
                    return [], excluded_items_from_id_set
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(data_extraction_func(file_path, packs=packs))
        else:
            package_name = os.path.basename(file_path)
            file_path = os.path.join(file_path, f'{package_name}.{suffix}')
            item_type = find_type(file_path)
            if os.path.isfile(file_path) and item_type in expected_file_types:
                if should_skip_item_by_mp(file_path, marketplace, excluded_items_from_id_set, packs=packs, print_logs=print_logs, item_type=item_type):
                    return [], excluded_items_from_id_set
                if print_logs:
                    print(f'adding {file_path} to id_set')
                res.append(data_extraction_func(file_path, packs=packs))
    except Exception as exp:  # noqa
        print_error(f'failed to process {file_path}, Error: {str(exp)}')
        raise

    return res, excluded_items_from_id_set


def process_test_playbook_path(file_path: str, packs: Dict[str, Dict], marketplace: str, print_logs: bool) -> tuple:
    """
    Process a yml file in the test playbook dir. Maybe either a script or playbook

    Arguments:
        file_path: path to yaml file
        packs: the pack mapping from the ID set.
        marketplace: the marketplace this id set is designated for.
        print_logs: whether to print logs to stdout

    Returns:
        pair -- first element is a playbook second is a script. each may be None
    """
    script = None
    playbook = None
    try:
        if print_logs:
            print(f'adding {file_path} to id_set')
        if should_skip_item_by_mp(file_path, marketplace, {}, packs=packs, print_logs=print_logs):
            return None, None
        if find_type(file_path) == FileType.TEST_SCRIPT:
            script = get_script_data(file_path, packs=packs)
        if find_type(file_path) == FileType.TEST_PLAYBOOK:
            playbook = get_playbook_data(file_path, packs=packs)
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

    playbook_files = list(pack_to_create) if pack_to_create else []
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


def get_generic_entities_paths(path, pack_to_create):
    """
    get paths of genericTypes, genericFields

    """
    if pack_to_create:
        path_list = [
            [pack_to_create, path, '*', '*.json']
        ]

    else:
        path_list = [
            [path, '*'],
            ['Packs', '*', path, '*', '*.json']
        ]

    files = list()
    for path in path_list:
        files.extend(glob.glob(os.path.join(*path)))

    return files


def get_generic_type_data(path, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    playbook_id = json_data.get('playbookId')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    definitionId = json_data.get('definitionId')
    layout = json_data.get('layout')

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if playbook_id and playbook_id != '':
        data['playbooks'] = playbook_id
    if definitionId:
        data['definitionId'] = definitionId
    if layout:
        data['layout'] = layout
    return {id_: data}


def get_module_id_from_definition_id(definition_id: str, generic_modules_list: list):
    for module in generic_modules_list:
        module_id = list(module.keys())[0]
        if definition_id in module.get(module_id, {}).get('definitionIds', []):
            return module_id


def get_generic_field_data(path, generic_types_list, packs: Dict[str, Dict] = None):
    json_data = get_json(path)

    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    all_associated_types: set = set()
    all_scripts = set()
    definitionId = json_data.get('definitionId')

    associated_types = json_data.get('associatedTypes')
    if associated_types:
        all_associated_types = set(associated_types)

    system_associated_types = json_data.get('systemAssociatedTypes')
    if system_associated_types:
        all_associated_types = all_associated_types.union(set(system_associated_types))

    if 'all' in all_associated_types:
        all_associated_types = {list(generic_type.keys())[0] for generic_type in generic_types_list}

    scripts = json_data.get('script')
    if scripts:
        all_scripts = {scripts}

    field_calculations_scripts = json_data.get('fieldCalcScript')
    if field_calculations_scripts:
        all_scripts = all_scripts.union({field_calculations_scripts})

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)

    if all_associated_types:
        data['generic_types'] = list(all_associated_types)
    if all_scripts:
        data['scripts'] = list(all_scripts)
    if definitionId:
        data['definitionId'] = definitionId

    return {id_: data}


def get_job_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)

    data = create_common_entity_data(path=path,
                                     name=json_data.get('name'),
                                     display_name=get_display_name(path, json_data),
                                     to_version=json_data.get('toVersion'),
                                     from_version=json_data.get('fromVersion'),
                                     pack=get_pack_name(path),
                                     marketplaces=marketplaces
                                     )
    data['playbookId'] = json_data.get('playbookId')
    data['selectedFeeds'] = json_data.get('selectedFeeds', [])
    data['details'] = json_data.get('details', [])

    return {json_data.get('id'): data}


def get_generic_module_data(path, packs: Dict[str, Dict] = None):
    json_data = get_json(path)
    id_ = json_data.get('id')
    name = json_data.get('name', '')
    display_name = get_display_name(path, json_data)
    pack = get_pack_name(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    fromversion = json_data.get('fromVersion')
    toversion = json_data.get('toVersion')
    definitionIds = json_data.get('definitionIds', [])
    views = json_data.get('views', [])
    views = {view.get('name'): {
        'title': view.get('title'),
        'dashboards': [tab.get('dashboard', {}).get('id') for tab in view.get('tabs', [])]} for view in views}

    data = create_common_entity_data(path=path, name=name, display_name=display_name, to_version=toversion,
                                     from_version=fromversion, pack=pack, marketplaces=marketplaces)
    if definitionIds:
        data['definitionIds'] = definitionIds
    if views:
        data['views'] = views

    return {id_: data}


def get_list_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    data = create_common_entity_data(path=path,
                                     name=json_data.get('name'),
                                     display_name=get_display_name(path, json_data),
                                     to_version=json_data.get('toVersion'),
                                     from_version=json_data.get('fromVersion'),
                                     pack=get_pack_name(path),
                                     marketplaces=marketplaces,
                                     )

    return {json_data.get('id'): data}


def get_wizard_data(path: str, packs: Dict[str, Dict] = None):
    json_data = get_json(path)
    marketplaces = get_item_marketplaces(path, item_data=json_data, packs=packs)
    data = create_common_entity_data(path=path,
                                     name=json_data.get('name'),
                                     display_name=get_display_name(path, json_data),
                                     to_version=json_data.get('toVersion'),
                                     from_version=json_data.get('fromVersion'),
                                     pack=get_pack_name(path),
                                     marketplaces=marketplaces,
                                     )
    dependency_packs: List[str] = []
    for dep_packs in json_data.get('dependency_packs', []):
        dependency_packs.extend({pack['name'] for pack in dep_packs['packs']})
    data['dependency_packs'] = dependency_packs
    return {json_data.get('id'): data}


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
    GENERIC_TYPE = 'GenericTypes'
    GENERIC_FIELD = 'GenericFields'
    GENERIC_MODULE = 'GenericModules'
    GENERIC_DEFINITION = 'GenericDefinitions'
    JOBS = 'Jobs'
    LISTS = 'Lists'
    WIZARDS = 'Wizards'

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

        if obj not in self._id_set_dict.get(object_type, {}):
            self._id_set_dict.setdefault(object_type, []).append(obj)

    def add_pack_to_id_set_packs(self, object_type: IDSetType, obj_name, obj_value):
        self._id_set_dict.setdefault(object_type, {}).update({obj_name: obj_value})


def merge_id_sets_from_files(first_id_set_path, second_id_set_path, output_id_set_path, print_logs: bool = True):
    """
    Merges two id-sets. Loads them from files and saves the merged unified id_set into output_id_set_path.
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
                                             external_object=obj, is_create_new=False)
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


def re_create_id_set(id_set_path: Optional[Path] = DEFAULT_ID_SET_PATH, pack_to_create=None,  # noqa : C901
                     objects_to_create: list = None, print_logs: bool = True, fail_on_duplicates: bool = False,
                     marketplace: str = ''):
    """Re create the id-set

    Args:
        id_set_path: If passed an empty string will use default path (dependeing on mp type).
            Pass in None to avoid saving the id-set.
        pack_to_create: The input path. the default is the content repo.
        objects_to_create: The content items this id set will contain. Defaults are set
            depending on the mp type.
        print_logs: Whether to print logs or not
        fail_on_duplicates: If value is True an error will be raised if duplicates are found
        marketplace: The marketplace the id set is created for.

    Returns: id-set object
    """
    if id_set_path == "":
        id_set_path = {
            MarketplaceVersions.MarketplaceV2.value: MP_V2_ID_SET_PATH,
            MarketplaceVersions.XPANSE.value: XPANSE_ID_SET_PATH,
        }.get(marketplace, DEFAULT_ID_SET_PATH)

    if not objects_to_create:
        if marketplace == MarketplaceVersions.MarketplaceV2.value:
            objects_to_create = CONTENT_MP_V2_ENTITIES
        elif marketplace == MarketplaceVersions.XPANSE.value:
            objects_to_create = CONTENT_XPANSE_ENTITIES
        else:
            objects_to_create = CONTENT_ENTITIES

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
        if refresh_interval > 0:  # if the file is newer than the refresh interval, use it as is
            mtime = os.path.getmtime(id_set_path)
            mtime_dt = datetime.fromtimestamp(mtime)
            target_time = time.time() - (refresh_interval * 60)
            if mtime >= target_time:
                print_color(
                    f"DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var is set and detected that current id_set: {id_set_path}"
                    f" modify time: {mtime_dt} "
                    "doesn't require a refresh. Will use current id-set. "
                    "If you rather force an id-set refresh, unset DEMISTO_SDK_ID_SET_REFRESH_INTERVAL or set it to -1.",
                    LOG_COLORS.GREEN)
                with open(id_set_path, mode="r") as f:
                    return json.load(f)
            else:
                print_color(
                    f"The DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var is set, but current id_set: {id_set_path} "
                    f"modify time: {mtime_dt} is older than the refresh interval. "
                    "Re-generating id-set.", LOG_COLORS.GREEN)
        else:
            print_color("Note: DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var is not enabled. "
                        f"Will re-generate the id-set and overwrite the existing file: {id_set_path}. "
                        "To avoid re-generating the id-set on every run, you can set the "
                        "DEMISTO_SDK_ID_SET_REFRESH_INTERVAL env var to any refresh interval (in minutes).",
                        LOG_COLORS.GREEN)
        print("")  # add an empty line for clarity

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
    generic_types_list = []
    generic_fields_list = []
    generic_modules_list = []
    generic_definitions_list = []
    lists_list = []
    jobs_list = []
    parsing_rules_list = []
    modeling_rules_list = []
    correlation_rules_list = []
    xsiam_dashboards_list = []
    xsiam_reports_list = []
    triggers_list = []
    wizards_list = []
    xdrc_templates_list = []
    packs_dict: Dict[str, Dict] = {}
    excluded_items_by_pack: Dict[str, set] = {}
    excluded_items_by_type: Dict[str, set] = {}

    pool = Pool(processes=int(cpu_count()))

    print_color("Starting the creation of the id_set", LOG_COLORS.GREEN)

    with click.progressbar(length=len(objects_to_create), label="Creating id-set") as progress_bar:

        if 'Packs' in objects_to_create:
            print_color("\nStarting iteration over Packs", LOG_COLORS.GREEN)
            for pack_data in pool.map(partial(get_pack_metadata_data,
                                              print_logs=print_logs,
                                              marketplace=marketplace,
                                              ),
                                      get_pack_metadata_paths(pack_to_create)):
                packs_dict.update(pack_data)

        progress_bar.update(1)

        if 'Integrations' in objects_to_create:
            print_color("\nStarting iteration over Integrations", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_integration,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       ),
                                                               get_integrations_paths(pack_to_create)):

                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('integrations',
                                                                                               []).append(_id)
                integration_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Playbooks' in objects_to_create:
            print_color("\nStarting iteration over Playbooks", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.PLAYBOOK,),
                                                                       data_extraction_func=get_playbook_data,
                                                                       ),
                                                               get_playbooks_paths(pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('playbooks', []).append(
                            _id)
                playbooks_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Scripts' in objects_to_create:
            print_color("\nStarting iteration over Scripts", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_script,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       ),
                                                               get_general_paths(SCRIPTS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('scripts', []).append(
                            _id)
                scripts_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'TestPlaybooks' in objects_to_create:
            print_color("\nStarting iteration over TestPlaybooks", LOG_COLORS.GREEN)
            for pair in pool.map(partial(process_test_playbook_path,
                                         packs=packs_dict,
                                         marketplace=marketplace,
                                         print_logs=print_logs,
                                         ),
                                 get_general_paths(TEST_PLAYBOOKS_DIR, pack_to_create)):
                if pair[0]:
                    testplaybooks_list.append(pair[0])
                if pair[1]:
                    scripts_list.append(pair[1])

        progress_bar.update(1)

        if 'Classifiers' in objects_to_create:
            print_color("\nStarting iteration over Classifiers", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.CLASSIFIER,
                                                                           FileType.OLD_CLASSIFIER),
                                                                       data_extraction_func=get_classifier_data,
                                                                       ),
                                                               get_general_paths(CLASSIFIERS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('classifiers',
                                                                                               []).append(_id)
                classifiers_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Dashboards' in objects_to_create:
            print_color("\nStarting iteration over Dashboards", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.DASHBOARD,),
                                                                       data_extraction_func=get_dashboard_data,
                                                                       ),
                                                               get_general_paths(DASHBOARDS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('dashboards', []).append(
                            _id)
                dashboards_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'IncidentTypes' in objects_to_create:
            print_color("\nStarting iteration over Incident Types", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.INCIDENT_TYPE,),
                                                                       data_extraction_func=get_incident_type_data,
                                                                       ),
                                                               get_general_paths(INCIDENT_TYPES_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('incidentTypes',
                                                                                               []).append(_id)
                incident_type_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        # Has to be called after 'IncidentTypes' is called
        if 'IncidentFields' in objects_to_create:
            print_color("\nStarting iteration over Incident Fields", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_incident_fields,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       incident_types=incident_type_list,
                                                                       ),
                                                               get_general_paths(INCIDENT_FIELDS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('incidentFields',
                                                                                               []).append(_id)
                incident_fields_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'IndicatorFields' in objects_to_create:
            print_color("\nStarting iteration over Indicator Fields", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.INDICATOR_FIELD,),
                                                                       data_extraction_func=get_general_data,
                                                                       ),
                                                               get_general_paths(INDICATOR_FIELDS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('indicatorFields',
                                                                                               []).append(_id)
                indicator_fields_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        # Has to be called after 'Integrations' is called
        if 'IndicatorTypes' in objects_to_create:
            print_color("\nStarting iteration over Indicator Types", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_indicator_types,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       all_integrations=integration_list,
                                                                       ),
                                                               get_general_paths(INDICATOR_TYPES_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('indicatorTypes',
                                                                                               []).append(_id)
                indicator_types_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Layouts' in objects_to_create:
            print_color("\nStarting iteration over Layouts", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.LAYOUT,),
                                                                       data_extraction_func=get_layout_data,
                                                                       ),
                                                               get_general_paths(LAYOUTS_DIR, pack_to_create)):
                layouts_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

            for arr, excluded_items_from_iteration in pool.map(partial(process_layoutscontainers,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       ),
                                                               get_general_paths(LAYOUTS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('layouts', []).append(
                            _id)
                layouts_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Reports' in objects_to_create:
            print_color("\nStarting iteration over Reports", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.REPORT,),
                                                                       data_extraction_func=get_report_data,
                                                                       ),
                                                               get_general_paths(REPORTS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('reports', []).append(
                            _id)
                reports_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Widgets' in objects_to_create:
            print_color("\nStarting iteration over Widgets", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.WIDGET,),
                                                                       data_extraction_func=get_widget_data,
                                                                       ),
                                                               get_general_paths(WIDGETS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('widgets', []).append(
                            _id)
                widgets_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Mappers' in objects_to_create:
            print_color("\nStarting iteration over Mappers", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.MAPPER,),
                                                                       data_extraction_func=get_mapper_data,
                                                                       ),
                                                               get_general_paths(MAPPERS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('mappers', []).append(
                            _id)
                mappers_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Lists' in objects_to_create:
            print_color("\nStarting iteration over Lists", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.LISTS,),
                                                                       data_extraction_func=get_list_data,
                                                                       ),
                                                               get_general_paths(LISTS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('lists', []).append(_id)
                lists_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'GenericDefinitions' in objects_to_create:
            print_color("\nStarting iteration over Generic Definitions", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.GENERIC_DEFINITION,),
                                                                       data_extraction_func=get_general_data,
                                                                       ),
                                                               get_general_paths(GENERIC_DEFINITIONS_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('genericDefinitions',
                                                                                               []).append(_id)
                generic_definitions_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'GenericModules' in objects_to_create:
            print_color("\nStarting iteration over Generic Modules", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(FileType.GENERIC_MODULE,),
                                                                       data_extraction_func=get_generic_module_data,
                                                                       ),
                                                               get_general_paths(GENERIC_MODULES_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('genericModules',
                                                                                               []).append(_id)
                generic_modules_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'GenericTypes' in objects_to_create:
            print_color("\nStarting iteration over Generic Types", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_generic_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       ),
                                                               get_generic_entities_paths(GENERIC_TYPES_DIR,
                                                                                          pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('genericTypes',
                                                                                               []).append(_id)
                generic_types_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        # Has to be called after 'GenericTypes' is called
        if 'GenericFields' in objects_to_create:
            print_color("\nStarting iteration over Generic Fields", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_generic_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       generic_types_list=generic_types_list,
                                                                       ),
                                                               get_generic_entities_paths(GENERIC_FIELDS_DIR,
                                                                                          pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('genericFields',
                                                                                               []).append(_id)
                generic_fields_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Jobs' in objects_to_create:
            print_color("\nStarting iteration over Jobs", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_jobs,
                                        packs=packs_dict,
                                        marketplace=marketplace,
                                        print_logs=print_logs,
                                        ),
                                get_general_paths(JOBS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('jobs', []).append(_id)
                jobs_list.extend(arr)

        progress_bar.update(1)

        if 'ParsingRules' in objects_to_create:
            print_color("\nStarting iteration over Parsing Rules", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.PARSING_RULE,),
                                                                       data_extraction_func=get_parsing_rule_data,
                                                                       ),
                                                               get_general_paths(PARSING_RULES_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('parsingRules',
                                                                                               []).append(_id)
                parsing_rules_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'ModelingRules' in objects_to_create:
            print_color("\nStarting iteration over Modeling Rules", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.MODELING_RULE,),
                                                                       data_extraction_func=get_modeling_rule_data,
                                                                       ),
                                                               get_general_paths(MODELING_RULES_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('modelingRules',
                                                                                               []).append(_id)
                modeling_rules_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'CorrelationRules' in objects_to_create:
            print_color("\nStarting iteration over Correlation Rules", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.CORRELATION_RULE,),
                                                                       data_extraction_func=get_correlation_rule_data,
                                                                       ),
                                                               get_general_paths(CORRELATION_RULES_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('correlationRules',
                                                                                               []).append(_id)
                correlation_rules_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'XSIAMDashboards' in objects_to_create:
            print_color("\nStarting iteration over XSIAMDashboards", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.XSIAM_DASHBOARD,),
                                                                       data_extraction_func=get_xsiam_dashboard_data,
                                                                       ),
                                                               get_general_paths(XSIAM_DASHBOARDS_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('xsiamdashboards',
                                                                                               []).append(_id)
                xsiam_dashboards_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'XSIAMReports' in objects_to_create:
            print_color("\nStarting iteration over XSIAMReports", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.XSIAM_REPORT,),
                                                                       data_extraction_func=get_xsiam_report_data,
                                                                       ),
                                                               get_general_paths(XSIAM_REPORTS_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('xsiamreports',
                                                                                               []).append(_id)
                xsiam_reports_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Triggers' in objects_to_create:
            print_color("\nStarting iteration over Triggers", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.TRIGGER,),
                                                                       data_extraction_func=get_trigger_data,
                                                                       ),
                                                               get_general_paths(TRIGGER_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('triggers',
                                                                                               []).append(_id)
                triggers_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

        if 'Wizards' in objects_to_create:
            print_color("\nStarting iteration over Wizards", LOG_COLORS.GREEN)
            for arr in pool.map(partial(process_wizards,
                                        packs=packs_dict,
                                        marketplace=marketplace,
                                        print_logs=print_logs,
                                        ),
                                get_general_paths(WIZARDS_DIR, pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('wizards', []).append(_id)
                wizards_list.extend(arr)

        progress_bar.update(1)

        if 'XDRCTemplates' in objects_to_create:
            print_color("\nStarting iteration over XDRCTemplates", LOG_COLORS.GREEN)
            for arr, excluded_items_from_iteration in pool.map(partial(process_general_items,
                                                                       packs=packs_dict,
                                                                       marketplace=marketplace,
                                                                       print_logs=print_logs,
                                                                       expected_file_types=(
                                                                           FileType.XDRC_TEMPLATE),
                                                                       data_extraction_func=get_xdrc_template_data,
                                                                       suffix='json'
                                                                       ),
                                                               get_general_paths(XDRC_TEMPLATE_DIR,
                                                                                 pack_to_create)):
                for _id, data in (arr[0].items() if arr and isinstance(arr, list) else {}):
                    if data.get('pack'):
                        packs_dict[data.get('pack')].setdefault('ContentItems', {}).setdefault('XDRCTemplates',
                                                                                               []).append(_id)
                xdrc_templates_list.extend(arr)
                update_excluded_items_dict(excluded_items_by_pack, excluded_items_by_type,
                                           excluded_items_from_iteration)

        progress_bar.update(1)

    new_ids_dict = OrderedDict()
    # we sort each time the whole set in case someone manually changed something
    # it shouldn't take too much time
    new_ids_dict['scripts'] = sort(scripts_list)
    new_ids_dict['playbooks'] = sort(playbooks_list)
    new_ids_dict['integrations'] = sort(integration_list)
    new_ids_dict['TestPlaybooks'] = sort(testplaybooks_list)
    new_ids_dict['Classifiers'] = sort(classifiers_list)
    new_ids_dict['IncidentFields'] = sort(incident_fields_list)
    new_ids_dict['IncidentTypes'] = sort(incident_type_list)
    new_ids_dict['IndicatorFields'] = sort(indicator_fields_list)
    new_ids_dict['IndicatorTypes'] = sort(indicator_types_list)
    new_ids_dict['Layouts'] = sort(layouts_list)
    new_ids_dict['Lists'] = sort(lists_list)
    new_ids_dict['Jobs'] = sort(jobs_list)
    new_ids_dict['Mappers'] = sort(mappers_list)
    new_ids_dict['ParsingRules'] = sort(parsing_rules_list)
    new_ids_dict['ModelingRules'] = sort(modeling_rules_list)
    new_ids_dict['CorrelationRules'] = sort(correlation_rules_list)
    new_ids_dict['XSIAMDashboards'] = sort(xsiam_dashboards_list)
    new_ids_dict['XSIAMReports'] = sort(xsiam_reports_list)
    new_ids_dict['Triggers'] = sort(triggers_list)
    new_ids_dict['Wizards'] = sort(wizards_list)
    new_ids_dict['Packs'] = packs_dict
    new_ids_dict['XDRCTemplates'] = sort(xdrc_templates_list)

    if marketplace != MarketplaceVersions.MarketplaceV2.value:
        new_ids_dict['GenericTypes'] = sort(generic_types_list)
        new_ids_dict['GenericFields'] = sort(generic_fields_list)
        new_ids_dict['GenericModules'] = sort(generic_modules_list)
        new_ids_dict['GenericDefinitions'] = sort(generic_definitions_list)
        new_ids_dict['Reports'] = sort(reports_list)
        new_ids_dict['Widgets'] = sort(widgets_list)
        new_ids_dict['Dashboards'] = sort(dashboards_list)
    else:
        # a workaround for find-dependencies check (PackDependencies._collect_pack_items)
        new_ids_dict['GenericTypes'] = []
        new_ids_dict['GenericFields'] = []
        new_ids_dict['GenericModules'] = []
        new_ids_dict['GenericDefinitions'] = []
        new_ids_dict['Reports'] = []
        new_ids_dict['Widgets'] = []
        new_ids_dict['Dashboards'] = []

    exec_time = time.time() - start_time
    print_color("Finished the creation of the id_set. Total time: {} seconds".format(exec_time), LOG_COLORS.GREEN)

    duplicates = find_duplicates(new_ids_dict, print_logs, marketplace)
    if any(duplicates) and fail_on_duplicates:
        raise Exception(f'The following ids were found duplicates\n{json.dumps(duplicates, indent=4)}\n')

    return new_ids_dict, excluded_items_by_pack, excluded_items_by_type


def find_duplicates(id_set, print_logs, marketplace):
    lists_to_return = []
    entities = {MarketplaceVersions.MarketplaceV2.value: ID_SET_MP_V2_ENTITIES,
                MarketplaceVersions.XPANSE.value: ID_SET_XPANSE_ENTITIES}.get(marketplace, ID_SET_ENTITIES)

    for object_type in entities:
        if print_logs:
            print_color("Checking diff for {}".format(object_type), LOG_COLORS.GREEN)
        objects = id_set.get(object_type)
        ids = {list(specific_item.keys())[0] for specific_item in objects}

        dup_list = []
        for id_to_check in ids:
            if has_duplicate(objects, id_to_check, object_type, print_logs, is_create_new=True):
                dup_list.append(id_to_check)
        lists_to_return.append(dup_list)

    if print_logs:
        print_color("Checking diff for Incident and Indicator Fields", LOG_COLORS.GREEN)

    fields = id_set['IncidentFields'] + id_set['IndicatorFields']
    field_ids = {list(field.keys())[0] for field in fields}

    field_list = []
    for field_to_check in field_ids:
        if has_duplicate(fields, field_to_check, 'Indicator and Incident Fields', print_logs, is_create_new=True):
            field_list.append(field_to_check)
    lists_to_return.append(field_list)

    return lists_to_return


def has_duplicate(id_set_subset_list, id_to_check, object_type, print_logs=True, external_object=None,
                  is_create_new=False):
    """
    Finds if id_set_subset_list contains a duplicate items with the same id_to_check.

    Pass `external_object` to check if it exists in `id_set_subset_list`.
    Otherwise the function will check if `id_set_subset_list` contains 2 or more items with the id of `id_to_check`

    Pass `is_create_new` if searching for duplicate while creating a new id-set.

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
        dict1_from_version = LooseVersion(dict1.get('fromversion', DEFAULT_CONTENT_ITEM_FROM_VERSION))
        dict2_from_version = LooseVersion(dict2.get('fromversion', DEFAULT_CONTENT_ITEM_FROM_VERSION))
        dict1_to_version = LooseVersion(dict1.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION))
        dict2_to_version = LooseVersion(dict2.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION))

        # Check whether the items belong to the same marketplaces
        if not set(dict1.get('marketplaces', [])).intersection(set(dict2.get('marketplaces', []))):
            continue

        # Checks if the Layouts kind is different then they are not duplicates
        if object_type == 'Layouts':
            if dict1.get('kind', '') != dict2.get('kind', ''):
                return False
            if dict1.get('typeID', '') != dict2.get('typeID', ''):
                return False

        # If they have the same pack name and the same source they actually the same entity.
        # Added to support merge between two id-sets that contain the same pack.
        if not is_create_new and \
                dict1.get('pack') == dict2.get('pack') and \
                is_same_source(dict1.get('source'), dict2.get('source')):
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
            print_warning(f'There are several {object_type} with the same ID ({id_to_check}) and their versions overlap: '
                          f'1) "{dict1_from_version}-{dict1_to_version}", '
                          f'2) "{dict2_from_version}-{dict2_to_version}".')
            return True

        if print_logs and dict1.get('name') != dict2.get('name'):
            print_warning(f'The following {object_type} have the same ID ({id_to_check}) but different names: '
                          f'"{dict1.get("name")}", "{dict2.get("name")}".')

    return False


def is_same_source(source1, source2) -> bool:
    """
    Two sources will considered the same if they are exactly the same repo, or they are the XSOAR repos, one in github
    and another in gitlab
    github.com, demisto, content == code,pan.run, xsoar, content
    """
    if source1 == source2:
        return True
    host1, owner1, repo1 = source1
    host2, owner2, repo2 = source2
    if host1 in {'github.com', 'code.pan.run'} and owner1 in {'demisto', 'xsoar'} \
            and host2 in {'github.com', 'code.pan.run'} and owner2 in {'demisto', 'xsoar'}:
        return repo1 == repo2
    return False


def sort(data):
    data.sort(key=lambda r: list(r.keys())[0].lower())  # Sort data by key value
    return data


def update_excluded_items_dict(excluded_items_by_pack: dict, excluded_items_by_type: dict,
                               excluded_items_to_add: dict):
    """
    Adds the items from 'excluded_items_to_add' to the exclusion dicts.

    Args:
        excluded_items_by_pack: the current dictionary of items to exclude from the id_set, aggregated by packs
        excluded_items_by_type: a dictionary of items to exclude from the id_set, aggregated by type
        excluded_items_to_add: a dictionary of items to add to the exclusion dict, aggregated by packs

    Example of excluded_items_by_pack:
    {
        'Expanse': {('integration', 'Expanse')},
        'ExpanseV2': {('script', 'ExpanseEvidenceDynamicSection'), ('indicatorfield', 'indicator_expansedomain')}
        ...
    }

    Example of excluded_items_by_type:
    {
        'integration': {'integration1', 'integration2' ...}
        'script' : {'script1' ...},
        'playbook' : {...}
        ...
    }
    """
    for key, val in excluded_items_to_add.items():
        excluded_items_by_pack.setdefault(key, set()).update(val)
        for tuple_item in val:
            excluded_items_by_type.setdefault(tuple_item[0], set()).update([tuple_item[1]])
