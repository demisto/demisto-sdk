from ruamel.yaml import YAML
import argparse
import json
import os
import sys


class Playbook:
    def __init__(self, name, fromversion='4.5.0'):
        self.name = name
        self.fromversion = fromversion

        self.tasks = {
            '0': create_start_task(),
            '1': create_script_task(1, 'DeleteContext', {'all': 'yes'})
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


def create_script_task(id, script_name, args=None):
    scriptargs = {}
    if args and len(args) > 0:
        scriptargs['all'] = {}

        for arg, val in args.items():
            scriptargs['all']['simple'] = val

    return {
        "id": id,
        "taskid": str(id),
        "type": "regular",
        "task": {
            "id": str(id),
            "version": -1,
            "name": script_name,
            "description": "",
            "script": f"{script_name}",
            "type": "regular",
            "iscommand": True,
            "brand": ""
        },
        "nexttasks": {
            "#none#": [
                str(id + 1)
            ]
        },
        "scriptarguments": scriptargs,
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


def create_integration_command_task(id, command_name, args=None):
    scriptargs = {}
    if args and len(args) > 0:
        scriptargs['all'] = {}

        for arg, val in args.items():
            scriptargs['all']['simple'] = val

    return {
        "id": id,
        "taskid": str(id),
        "type": "regular",
        "task": {
            "id": str(id),
            "version": -1,
            "name": command_name,
            "description": "",
            "script": f"|||{command_name}",
            "type": "regular",
            "iscommand": True,
            "brand": ""
        },
        "nexttasks": {
            "#none#": [
                str(id + 1)
            ]
        },
        "scriptarguments": scriptargs,
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


def create_verify_outputs_task(id, conditions=[]):
    return {
        "id": str(id),
        "taskid": str(id),
        "type": "condition",
        "task": {
            "id": str(id),
            "version": -1,
            "name": "Verify Outputs",
            "type": "condition",
            "iscommand": False,
            'description': '',
            "brand": ""
        },
        "nexttasks": {
            "yes": [
                str(id + 1)
            ]
        },
        "separatecontext": False,
        "conditions": conditions,
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


def outputs_to_condition(outputs):
    conditions = []
    condition = {
        'label': 'yes',
        'condition': []
    }
    command_have_outputs = False
    for output in outputs:
        command_have_outputs = True
        context_output_path = output.get('contextPath')

        condition['condition'].append(
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

    conditions.append(condition)

    return conditions, command_have_outputs


class TestPlaybookGenerator:
    def __init__(self, infile, outdir, name, commands, _type='integration'):
        self.integration_yml_path = infile
        if outdir:
            self.test_playbook_yml_path = os.path.join(outdir, name + '.yml')
        else:
            self.test_playbook_yml_path = f'{name}.yml'

        self._type = _type
        self.name = name
        self.commands_file_path = commands

    def run(self):
        ryaml = YAML()
        ryaml.preserve_quotes = True
        with open(self.integration_yml_path, 'r') as yf:
            yaml_obj = ryaml.load(yf)

        commands = None
        if self.commands_file_path:
            with open(self.commands_file_path, 'r') as cf:
                commands = cf.readlines()

        test_playbook_v1 = Playbook(
            name=self.name,
            fromversion='4.5.0'
        )

        if self._type == 'integration':
            for command in yaml_obj.get('script').get('commands'):
                command_name = command.get('name')
                task_command = create_integration_command_task(test_playbook_v1.task_counter, command_name)
                test_playbook_v1.add_task(task_command)

                conditions, command_have_outputs = outputs_to_condition(command.get('outputs', []))
                if command_have_outputs:
                    task_verify_outputs = create_verify_outputs_task(test_playbook_v1.task_counter, conditions)
                    test_playbook_v1.add_task(task_verify_outputs)

        elif self._type == 'script':
            script_name = yaml_obj.get('name')
            task_command = create_script_task(test_playbook_v1.task_counter, script_name)
            test_playbook_v1.add_task(task_command)

            conditions, command_have_outputs = outputs_to_condition(yaml_obj.get('outputs', []))
            if command_have_outputs:
                task_verify_outputs = create_verify_outputs_task(test_playbook_v1.task_counter, conditions)
                test_playbook_v1.add_task(task_verify_outputs)

        test_playbook_v1.add_task(create_end_task(test_playbook_v1.task_counter))
        with open(self.test_playbook_yml_path, 'w') as yf:
            ryaml.dump(test_playbook_v1.to_dict(), yf)

            print(f'Test playbook yml was saved at:\n{self.test_playbook_yml_path}')


def main():
    parser = argparse.ArgumentParser(description='Generate test playbook from integration or script',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-i', '--infile', help='Specify integration/script yml path', required=True)
    parser.add_argument('-o', '--outdir', help='Specify output directory', required=False)
    parser.add_argument('-n', '--name', help='Specify test playbook name', required=True)
    parser.add_argument('-t', '--type', help='Specify integration or script. The default is integration',
                        required=False, default='integration')

    # TODO: can implemented later - if commands provided then generate the test playbook with commands with inputs
    # parser.add_argument('-c', '--commands', help='Full path of file containing commands, if specified those commands '
    #                                              'will appear in the test playbook with the specified arguments',
    #                     required=False)

    args = parser.parse_args()

    if args.outdir and not os.path.isdir(args.outdir):
        print(f'{args.outdir} is not a valid directory')
        sys.exit(1)

    generator = TestPlaybookGenerator(
        infile=args.infile,
        outdir=args.outdir,
        name=args.name,
        _type=args.type
    )

    generator.run()
