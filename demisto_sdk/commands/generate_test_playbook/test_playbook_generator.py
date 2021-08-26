import json
from pathlib import Path
from typing import Dict, Optional

import click
from ruamel.yaml import YAML

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.upload.uploader import Uploader


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
        for arg, val in args.items():
            script_args[arg] = {
                "simple": val
            }

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

        operator = 'isExists' if output.get('type', '') == 'Boolean' else 'isNotEmpty'

        conditions.append(
            [
                {
                    "operator": operator,
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


def create_automation_task_and_verify_outputs_task(test_playbook, command, args, item_type, no_outputs,
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
                                          args=args,
                                          brand=brand)
    test_playbook.add_task(task_command)

    if len(outputs) > 0:
        # add verify output task only if automation have outputs
        if no_outputs:
            task_verify_outputs = create_verify_outputs_task(test_playbook.task_counter, [])
        else:
            task_verify_outputs = create_verify_outputs_task(test_playbook.task_counter, conditions)

        test_playbook.add_task(task_verify_outputs)


def get_command_examples(commands_file_path, entity_type) -> dict:
    """
    Gets the command examples from command file with their arguments.

    Args:
        commands_file_path: command file or the content of such file.
        entity_type: The entity type to generate test playbook for.

    Return:
        dict. Arguments separated by the commands.
    """
    command_examples = []  # type: list

    if entity_type == FileType.INTEGRATION.value:
        with open(commands_file_path, 'r') as examples_file:
            command_examples = examples_file.read().splitlines()
    else:
        command_examples = commands_file_path.split('\n')

    # Split the command example to dictionary of arguments for each command
    result_commands = {}
    for command in command_examples:
        command = command.split(' ', 1)
        result_commands[command[0].strip('!')] = dict(arg.split('=') for arg in command[1].split(' ')) \
            if len(command) > 1 else {}

    return result_commands


class PlaybookTestsGenerator:
    def __init__(self, input: str, output: str, name: str, file_type: str, no_outputs: bool = False,
                 verbose: bool = False, use_all_brands: bool = False, commands: str = None, examples: str = None,
                 upload: bool = False):
        self.integration_yml_path = input
        self.output = output

        generated_test_playbook_file_name = f'playbook-{name}_Test.yml'

        if output:
            """ if an output folder path is provided, save it there"""
            output_path = Path(output)
            if output_path.is_dir():
                self.test_playbook_yml_path = str(output_path / generated_test_playbook_file_name)
            else:
                """ if a destination path is specified for the playbook, and it's of a yml file, use it"""
                if not output_path.suffix.lower() == '.yml':
                    raise PlaybookTestsGenerator.InvalidOutputPathError(output)
                self.test_playbook_yml_path = output
        else:
            input_folder = Path(input)

            """
            if input yml is under standard Packs/<Pack>/<...>/<Integration> path,
            save the test-playbook under   Packs/<Pack>/TestPlaybooks
            """
            pack_path = None
            for p in input_folder.parents:
                if p.parent.name == "Packs":
                    pack_path = p
                    break

            if pack_path:
                folder = (pack_path / 'TestPlaybooks')
                folder.mkdir(exist_ok=True, parents=True)
            else:
                """ otherwise, save the generated test-playbook in the folder from which SDK is called."""
                folder = Path()

            self.test_playbook_yml_path = str(folder / generated_test_playbook_file_name)

        self.file_type = file_type
        self.name = name
        self.no_outputs = no_outputs
        self.verbose = verbose
        self.use_all_brands = use_all_brands
        self.commands = commands
        self.examples = examples
        self.upload = upload

    class InvalidOutputPathError(BaseException):
        def __init__(self, output: str):
            super().__init__(f'The output path provided ({output}) is neither a path to folder, nor to a yml file. '
                             f'Please check the help section or documentation for possible values, '
                             f'or call without the -o flag.')

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
        ryaml = YAML()
        ryaml.preserve_quotes = True
        try:
            with open(self.integration_yml_path, 'r') as yf:
                yaml_obj = ryaml.load(yf)

                yaml_obj.get('name')
        except FileNotFoundError as ex:
            if self.verbose:
                raise

            click.secho(str(ex), fg='bright_red')
            return
        except AttributeError:
            click.secho(f'Error - failed to parse: {self.integration_yml_path}.\nProbably invalid yml file',
                        fg='bright_red')
            return

        test_playbook = Playbook(
            name=self.name,
            fromversion='4.5.0'
        )

        command_examples_args = get_command_examples(self.examples, self.file_type) if self.examples else {}

        if self.file_type == ContentItemType.INTEGRATION:
            brand = '' if self.use_all_brands else yaml_obj.get('commonfields', {}).get('id', '')

            for command in yaml_obj.get('script').get('commands'):

                # Skip the commands that not specified in the `commands` argument
                if self.commands and command.get('name') not in self.commands.split(','):
                    continue

                # Skip the commands that not specified in the command examples file if exist
                if self.examples and command.get('name') not in command_examples_args:
                    continue

                create_automation_task_and_verify_outputs_task(
                    test_playbook=test_playbook,
                    command=command,
                    args=command_examples_args.get(command.get('name'), {}),
                    item_type=ContentItemType.INTEGRATION,
                    no_outputs=self.no_outputs,
                    brand=brand
                )

        elif self.file_type == ContentItemType.SCRIPT:
            create_automation_task_and_verify_outputs_task(
                test_playbook=test_playbook,
                command=yaml_obj,
                args=command_examples_args.get(yaml_obj.get('name'), {}),
                item_type=ContentItemType.SCRIPT,
                no_outputs=self.no_outputs
            )

        test_playbook.add_task(create_end_task(test_playbook.task_counter))

        if Path(self.test_playbook_yml_path).exists():
            click.secho(f'Warning: There already exists a test playbook at {self.test_playbook_yml_path}, '
                        f'it will be overwritten.', fg='yellow')

        with open(self.test_playbook_yml_path, 'w') as yf:
            ryaml.dump(test_playbook.to_dict(), yf)

            click.secho(f'Test playbook yml was saved at:\n{self.test_playbook_yml_path}\n', fg='green')

        if self.upload:
            return Uploader(input=self.test_playbook_yml_path).upload()

        return True
