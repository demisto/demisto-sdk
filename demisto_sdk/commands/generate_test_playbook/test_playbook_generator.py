import json
import os
from typing import Dict, Optional

from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)
from ruamel.yaml import YAML


class ContentItemType:
    INTEGRATION = 'integration'
    SCRIPT = 'script'


class Playbook:
    def __init__(self, name, fromversion='4.5.0'):
        self.name = name
        self.fromversion = fromversion

        self.tasks = {
            '0': create_start_task(),
            '1': create_automation_task(1, 'DeleteContext', ContentItemType.SCRIPT, {'all': 'yes'})
        }
        self.task_counter = len(self.tasks)

        self.view = json.dumps({
            "linkLabelsPosition": {},
            "paper": {
                "dimensions": {
                    "height": 200,
                    "width": 380,
                    "x": 50,
                    "y": 50
                }
            }
        })

    def add_task(self, task):
        self.tasks[str(self.task_counter)] = task
        self.task_counter += 1

    def to_dict(self):
        return {
            'id': self.name,
            'name': self.name,
            'version': -1,
            'fromversion': self.fromversion,
            'starttaskid': "0",
            'tasks': self.tasks,
            'view': self.view,
            'inputs': [],
            'outputs': []
        }


def create_start_task():
    return {
        'id': "0",
        'taskid': '0',
        'type': 'start',
        'task': {
            'id': '0',
            'version': -1,
            'name': "",
            'iscommand': False,
            'brand': "",
            'description': ""
        },
        'nexttasks': {
            '#none#': [
                "1"
            ]
        },
        'separatecontext': False,
        'view': json.dumps({
            "position": {
                "x": 50,
                "y": 50
            }
        }),
        'note': False,
        'timertriggers': [],
        'ignoreworker': False
    }


def create_end_task(id):
    return {
        "id": str(id),
        "taskid": str(id),
        "type": "title",
        "task": {
            "id": str(id),
            "version": -1,
            "name": "Test Done",
            "type": "title",
            "iscommand": False,
            "brand": "",
            'description': ""
        },
        "separatecontext": False,
        "view": json.dumps({
            'position': {
                'x': 50,
                'y': id * 200
            }
        }),
        "note": False,
        "timertriggers": [],
        "ignoreworker": False,
        "skipunavailable": False
    }


def create_automation_task(_id, automation_name, item_type: str, args: Optional[Dict] = None, brand: str = ""):
    script_args = {}  # type:Dict
    if args and len(args) > 0:
        script_args['all'] = {}
        for arg, val in args.items():
            script_args['all']['simple'] = val

    if item_type == ContentItemType.INTEGRATION:
        """
        when integration_brand is used as prefix, only instances of this brand execute the command.
        to use with more than one integration, pass integration_brand = ""
        """
        script_name = f'{brand}|||{automation_name}'

    elif item_type == ContentItemType.SCRIPT:
        script_name = automation_name

    return {
        "id": _id,
        "taskid": str(_id),
        "type": "regular",
        "task": {
            "id": str(_id),
            "version": -1,
            "name": automation_name,
            "description": "",
            "script": script_name,
            "type": "regular",
            "iscommand": True,
            "brand": ""
        },
        "nexttasks": {
            "#none#": [
                str(_id + 1)
            ]
        },
        "scriptarguments": script_args,
        "separatecontext": False,
        "view": json.dumps({
            'position': {
                'x': 50,
                'y': _id * 200
            }
        }),
        "note": False,
        "timertriggers": [],
        "ignoreworker": False,
        "skipunavailable": False
    }


def create_verify_outputs_task(id_, conditions=[]):
    return {
        "id": str(id_),
        "taskid": str(id_),
        "type": "condition",
        "task": {
            "id": str(id_),
            "version": -1,
            "name": "Verify Outputs",
            "type": "condition",
            "iscommand": False,
            'description': '',
            "brand": ""
        },
        "nexttasks": {
            "yes": [
                str(id_ + 1)
            ]
        },
        "separatecontext": False,
        "conditions": conditions,
        "view": json.dumps({
            'position': {
                'x': 50,
                'y': id_ * 200
            }
        }),
        "note": False,
        "timertriggers": [],
        "ignoreworker": False,
        "skipunavailable": False
    }


def outputs_to_condition(outputs):
    """
    Converts list of automation (script/integration) outputs to condition (for verify outputs task)

    Args:
        outputs: list of dict, contains contextPath for each output

    Returns:
        list of conditions generated from outputs
    """
    conditions = []
    for output in outputs:
        context_output_path = output.get('contextPath')

        conditions.append(
            [
                {
                    "operator": "isNotEmpty",
                    "left": {
                        "value": {
                            "simple": context_output_path
                        },
                        "iscontext": True
                    }
                }
            ]
        )

    condition = [
        {
            'label': 'yes',
            'condition': conditions
        }
    ]
    return condition


def create_automation_task_and_verify_outputs_task(test_playbook, command, item_type, no_outputs,
                                                   brand: str = ""):
    """
    create automation task from command and verify outputs task from automation(script/integration command) outputs.
    both tasks added to test playbook. both of this tasks linked to each other

    Args:
        test_playbook: Test playbook
        command: command/script object - they are similar as they both contain name and outputs
        item_type: content item type - either integration or script
        no_outputs: if True then created empty verify outputs task without all the outputs
        brand: if provided, commands will only be run by instances of the provided brand

    Returns:
        test_playbook is updated
    """
    command_name = command.get('name')
    outputs = command.get('outputs', [])
    conditions = outputs_to_condition(outputs)

    task_command = create_automation_task(test_playbook.task_counter,
                                          command_name,
                                          item_type,
                                          brand=brand)
    test_playbook.add_task(task_command)

    if len(outputs) > 0:
        # add verify output task only if automation have outputs
        if no_outputs:
            task_verify_outputs = create_verify_outputs_task(test_playbook.task_counter, [])
        else:
            task_verify_outputs = create_verify_outputs_task(test_playbook.task_counter, conditions)

        test_playbook.add_task(task_verify_outputs)


class PlaybookTestsGenerator:
    def __init__(self, input: str, output: str, name: str, file_type: str, no_outputs: bool = False,
                 verbose: bool = False, all_brands: bool = False):
        self.integration_yml_path = input
        self.output = output
        if output:
            self.test_playbook_yml_path = os.path.join(output, name + '.yml')
        else:
            self.test_playbook_yml_path = f'{name}.yml'

        self.file_type = file_type
        self.name = name
        self.no_outputs = no_outputs
        self.verbose = verbose
        self.all_brands = all_brands

    def run(self):
        """
        This function will try to load integration/script yml file.
        Creates test playbook, and converts each command to automation task in test playbook and generates verify
        outputs task from command outputs.

        All the tasks eventually will be linked to each other:
        playbook_start_task => delete_context(all) => task1 => verify_outputs_task1 => task2 => verify_outputs_task2
            => task_end

        At the end the functions dumps the new test playbook to the output if set, otherwise file will be created in
        local directory

        """
        if self.output:
            if not os.path.isdir(self.output):
                print_error(f'Directory not exist: {self.output}')
                return

        ryaml = YAML()
        ryaml.preserve_quotes = True
        try:
            with open(self.integration_yml_path, 'r') as yf:
                yaml_obj = ryaml.load(yf)

                yaml_obj.get('name')
        except FileNotFoundError as ex:
            if self.verbose:
                raise

            print_error(str(ex))
            return
        except AttributeError:
            print_error(f'Error - failed to parse: {self.integration_yml_path}.\nProbably invalid yml file')
            return

        test_playbook = Playbook(
            name=self.name,
            fromversion='4.5.0'
        )

        if self.file_type == ContentItemType.INTEGRATION:
            brand = '' if self.all_brands else yaml_obj.get('commonfields', {}).get('id')

            for command in yaml_obj.get('script').get('commands'):
                create_automation_task_and_verify_outputs_task(
                    test_playbook=test_playbook,
                    command=command,
                    item_type=ContentItemType.INTEGRATION,
                    no_outputs=self.no_outputs,
                    brand=brand
                )

        elif self.file_type == ContentItemType.SCRIPT:
            create_automation_task_and_verify_outputs_task(
                test_playbook=test_playbook,
                command=yaml_obj,
                item_type=ContentItemType.INTEGRATION,
                no_outputs=self.no_outputs
            )

        test_playbook.add_task(create_end_task(test_playbook.task_counter))

        with open(self.test_playbook_yml_path, 'w') as yf:
            ryaml.dump(test_playbook.to_dict(), yf)

            print_color(f'Test playbook yml was saved at:\n{self.test_playbook_yml_path}', LOG_COLORS.GREEN)
