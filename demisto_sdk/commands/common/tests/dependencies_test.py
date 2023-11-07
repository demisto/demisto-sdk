import inspect
import itertools
import os
from typing import List

import pytest

from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.find_dependencies.find_dependencies import PackDependencies
from TestSuite.integration import Integration
from TestSuite.json_based import JSONBased
from TestSuite.playbook import Playbook
from TestSuite.script import Script
from TestSuite.test_tools import ChangeCWD

# TODO: Remove this test file when CIAC-3905 is completed.
# Currently this test uses the older dependencies creation, the content repo uses the newer graph method of creating
# dependencies, but some other repos do not. We will remove this test when the other repos have been migrated to graph.


def update_id_set(repo):
    with ChangeCWD(repo.path):
        id_set_creator = IDSetCreator(repo.id_set.path, print_logs=False)
        id_set_creator.create_id_set()


class IntegrationDependencies:
    @staticmethod
    def make_integration_depend_on_classifier(
        integration: Integration, classifier: JSONBased
    ):
        classifier_id = classifier.read_json_as_dict().get("id")
        integration.yml.update({"defaultclassifier": classifier_id})

    @staticmethod
    def make_integration_depend_on_mapper_in(
        integration: Integration, mapper: JSONBased
    ):
        mapper_id = mapper.read_json_as_dict().get("id")
        integration.yml.update({"defaultmapperin": mapper_id})

    @staticmethod
    def make_integration_depend_on_mapper_out(
        integration: Integration, mapper: JSONBased
    ):
        mapper_id = mapper.read_json_as_dict().get("id")
        integration.yml.update({"defaultmapperout": mapper_id})

    @staticmethod
    def make_integration_depend_on_incident_type(
        integration: Integration, incident_type: JSONBased
    ):
        incident_type_id = incident_type.read_json_as_dict().get("id")
        integration.yml.update({"defaultIncidentType": incident_type_id})

    @staticmethod
    def make_integration_feed(integration: Integration):
        yml_dict = integration.yml.read_dict()
        if "script" not in yml_dict:
            yml_dict["script"] = {}
        yml_dict["script"]["feed"] = True
        integration.yml.write_dict(yml_dict)


class WidgetDependencies:
    @staticmethod
    def make_widget_depend_on_script(widget: JSONBased, script: Script):
        script_id = script.yml.read_dict().get("commonfields").get("id")
        widget.update({"dataType": "scripts", "query": script_id})


# Playbook class helper function
def get_new_task_number(playbook: Playbook):
    try:
        playbook_tasks = list(playbook.yml.read_dict().get("tasks").keys())

        if playbook_tasks:
            return max(int(task_num) for task_num in playbook_tasks) + 1

        playbook.yml.update({"starttaskid": "0"})
        return 0

    except AttributeError:
        playbook.yml.update({"starttaskid": "0"})
        return 0


def update_tasks_in_playbook(playbook: Playbook, task_num: int, task: dict):
    tasks = playbook.yml.read_dict().get("tasks", {})

    # Connects the new task added to the last task in the playbook, so the whole playbook will be connected
    if task_num > 0:
        try:
            tasks.get(str(task_num - 1)).get("nexttasks").get("#none#").append(
                str(task_num)
            )
        except AttributeError:
            tasks.get(str(task_num - 1)).update(
                {"nexttasks": {"#none#": [str(task_num)]}}
            )

    tasks.update(task)

    playbook.yml.update({"tasks": tasks})


class PlaybookDependencies:
    @staticmethod
    def make_playbook_depend_on_script_skippable(playbook: Playbook, script: Script):
        script_name = script.yml.read_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "cfcc9ea0-eb0e-4efa-80ad-606909350e2a",
                "type": "regular",
                "task": {
                    "id": "cfcc9ea0-eb0e-4efa-80ad-606909350e2a",
                    "version": -1,
                    "name": script_name,
                    "description": "Description",
                    "scriptName": script_name,
                    "type": "regular",
                    "iscommand": False,
                    "brand": "",
                },
                "scriptarguments": {
                    "entryID": {"complex": {"root": "InfoFile", "accessor": "EntryID"}},
                    "fileName": {},
                    "lastZipFileInWarroom": {},
                    "password": {},
                },
                "separatecontext": False,
                "view": """| -
                {
                    "position": {
                        "x": 450,
                        "y": 350
                    }
                }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
                "skipunavailable": True,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)

    @staticmethod
    def make_playbook_depend_on_script_not_skippable(
        playbook: Playbook, script: Script
    ):
        script_name = script.yml.read_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "cfcc9ea0-eb0e-4efa-80ad-606909350e2a",
                "type": "regular",
                "task": {
                    "id": "cfcc9ea0-eb0e-4efa-80ad-606909350e2a",
                    "version": -1,
                    "name": script_name,
                    "description": "Description",
                    "scriptName": script_name,
                    "type": "regular",
                    "iscommand": False,
                    "brand": "",
                },
                "scriptarguments": {
                    "entryID": {"complex": {"root": "InfoFile", "accessor": "EntryID"}},
                    "fileName": {},
                    "lastZipFileInWarroom": {},
                    "password": {},
                },
                "separatecontext": False,
                "view": """| -
                {
                    "position": {
                        "x": 450,
                        "y": 350
                    }
                }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)

    @staticmethod
    def make_playbook_depend_on_playbook_skippable(
        playbook: Playbook, playbook__1: Playbook
    ):
        other_playbook_name = playbook__1.yml.read_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "fa3391b8-020e-4f53-8576-7445bf741452",
                "type": "playbook",
                "task": {
                    "id": "fa3391b8-020e-4f53-8576-7445bf741452",
                    "version": -1,
                    "name": other_playbook_name,
                    "playbookName": other_playbook_name,
                    "type": "playbook",
                    "iscommand": False,
                    "brand": "",
                    "description": "",
                },
                "separatecontext": True,
                "loop": {"iscommand": False, "exitCondition": "", "wait": 1, "max": 0},
                "view": """| -
                            {
                                "position": {
                                    "x": -800,
                                    "y": 980
                                }
                            }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
                "skipunavailable": True,
                "quietmode": 0,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)

    @staticmethod
    def make_playbook_depend_on_playbook_not_skippable(
        playbook: Playbook, playbook__1: Playbook
    ):
        other_playbook_name = playbook__1.yml.read_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "fa3391b8-020e-4f53-8576-7445bf741452",
                "type": "regular",
                "task": {
                    "id": "fa3391b8-020e-4f53-8576-7445bf741452",
                    "version": -1,
                    "name": other_playbook_name,
                    "playbookName": other_playbook_name,
                    "type": "regular",
                    "iscommand": False,
                    "brand": "",
                    "description": "",
                },
                "separatecontext": True,
                "loop": {"iscommand": False, "exitCondition": "", "wait": 1, "max": 0},
                "view": """| -
                            {
                                "position": {
                                    "x": -800,
                                    "y": 980
                                }
                            }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
                "quietmode": 0,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)

    @staticmethod
    def make_playbook_depend_on_integration_skippable(
        playbook: Playbook, integration: Integration
    ):
        integration_name = integration.yml.read_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "fa3391b8-020e-4f53-8576-7445bf741452",
                "type": "regular",
                "task": {
                    "id": "fa3391b8-020e-4f53-8576-7445bf741452",
                    "version": -1,
                    "name": integration_name,
                    "script": f"{integration_name}|||command_{integration_name}",
                    "type": "regular",
                    "iscommand": True,
                    "brand": integration_name,
                    "description": "",
                },
                "scriptarguments": {
                    "env_bitness": {},
                    "env_type": {},
                    "env_version": {},
                    "file": {},
                    "obj_type": {"simple": "download"},
                    "obj_url": {"complex": {"root": "inputs.URL", "accessor": "Data"}},
                    "opt_kernel_heavyevasion": {},
                    "opt_network_connect": {},
                    "opt_privacy_type": {},
                },
                "separatecontext": True,
                "view": """| -
                            {
                                "position": {
                                    "x": -800,
                                    "y": 980
                                }
                            }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
                "skipunavailable": True,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)

    @staticmethod
    def make_playbook_depend_on_integration_not_skippable(
        playbook: Playbook, integration: Integration
    ):
        integration_name = integration.yml.read_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "fa3391b8-020e-4f53-8576-7445bf741452",
                "type": "regular",
                "task": {
                    "id": "fa3391b8-020e-4f53-8576-7445bf741452",
                    "version": -1,
                    "name": integration_name,
                    "script": f"{integration_name}|||command_{integration_name}",
                    "type": "regular",
                    "iscommand": True,
                    "brand": integration_name,
                    "description": "",
                },
                "scriptarguments": {
                    "env_bitness": {},
                    "env_type": {},
                    "env_version": {},
                    "file": {},
                    "obj_type": {"simple": "download"},
                    "obj_url": {"complex": {"root": "inputs.URL", "accessor": "Data"}},
                    "opt_kernel_heavyevasion": {},
                    "opt_network_connect": {},
                    "opt_privacy_type": {},
                },
                "separatecontext": True,
                "view": """| -
                                {
                                    "position": {
                                        "x": -800,
                                        "y": 980
                                    }
                                }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)

    @staticmethod
    def make_playbook_depend_on_incident_field(
        playbook: Playbook, incident_field: JSONBased
    ):
        incident_field_name = incident_field.read_json_as_dict().get("name")

        mapping = {
            "fieldMapping": [
                {
                    "incidentfield": incident_field_name,
                    "output": {
                        "complex": {
                            "root": "root",
                            "filters": {
                                "operator": "lessThan",
                                "left": {
                                    "value": {
                                        "simple": "context.path",
                                        "iscontext": True,
                                    }
                                },
                                "right": {
                                    "value": {
                                        "simple": "49151",
                                    },
                                    "accessor": "DestPort",
                                },
                            },
                        }
                    },
                }
            ]
        }

        task_num = get_new_task_number(playbook)
        task_num_to_associate = task_num - 2

        task = playbook.yml.read_dict().get("tasks").get(str(task_num_to_associate))
        task.update(mapping)

        task.update({"id": str(task_num)})
        new_task = {str(task_num): task}

        update_tasks_in_playbook(playbook, task_num, new_task)

    @staticmethod
    def make_playbook_depend_on_incident_field_builtin_command(
        playbook: Playbook, incident_field: JSONBased
    ):
        incident_field_name = incident_field.read_json_as_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "fa3391b8-020e-4f53-8576-7445bf741452",
                "type": "regular",
                "task": {
                    "id": "fa3391b8-020e-4f53-8576-7445bf741452",
                    "version": -1,
                    "name": "Set incident field",
                    "script": "Builtin|||setIncident",
                    "type": "regular",
                    "iscommand": True,
                    "brand": "Builtin",
                    "description": "",
                },
                "scriptarguments": {incident_field_name: "value"},
                "separatecontext": False,
                "view": """| -
                            {
                                "position": {
                                    "x": -800,
                                    "y": 980
                                }
                            }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)

    @staticmethod
    def make_playbook_depend_on_incident_field_input_simple(
        playbook: Playbook, incident_field: JSONBased
    ):
        incident_field_name = incident_field.read_json_as_dict().get("name")

        new_input = {
            "key": "input",
            "value": {"simple": "${incident." + incident_field_name + "}"},
            "required": False,
            "description": "description",
            "playbookInputQuery": None,
        }

        playbook_content = playbook.yml.read_dict()

        if "inputs" in playbook_content:
            playbook_content.get("inputs").append(new_input)
        else:
            playbook_content.update({"inputs": [new_input]})

        playbook.yml.write_dict(playbook_content)

    @staticmethod
    def make_playbook_depend_on_incident_field_input_complex(
        playbook: Playbook, incident_field: JSONBased
    ):
        incident_field_name = incident_field.read_json_as_dict().get("name")

        new_input = {
            "key": "input",
            "value": {"complex": {"root": "incident", "accessor": incident_field_name}},
            "required": False,
            "description": "description",
            "playbookInputQuery": None,
        }

        playbook_content = playbook.yml.read_dict()

        if "inputs" in playbook_content:
            playbook_content.get("inputs").append(new_input)
        else:
            playbook_content.update({"inputs": [new_input]})

        playbook.yml.write_dict(playbook_content)

    @staticmethod
    def make_playbook_depend_on_indicator_field_builtin_command(
        playbook: Playbook, indicator_field: JSONBased
    ):
        indicator_field_name = indicator_field.read_json_as_dict().get("name")
        task_num = get_new_task_number(playbook)

        task = {
            str(task_num): {
                "id": str(task_num),
                "taskid": "fa3391b8-020e-4f53-8576-7445bf741452",
                "type": "regular",
                "task": {
                    "id": "fa3391b8-020e-4f53-8576-7445bf741452",
                    "version": -1,
                    "name": "Set incident field",
                    "script": "Builtin|||setIndicator",
                    "type": "regular",
                    "iscommand": True,
                    "brand": "Builtin",
                    "description": "",
                },
                "scriptarguments": {indicator_field_name: "value"},
                "separatecontext": False,
                "view": """| -
                                {
                                    "position": {
                                        "x": -800,
                                        "y": 980
                                    }
                                }""",
                "note": False,
                "timertriggers": [],
                "ignoreworker": False,
            }
        }

        update_tasks_in_playbook(playbook, task_num, task)


class ScriptDependencies:
    @staticmethod
    def make_script_depend_on_integration(script: Script, integration: Integration):
        integration_name = integration.yml.read_dict().get("name")
        script_content = script.yml.read_dict()

        if script_content.get("dependson"):
            script_content["dependson"]["must"].append(
                f"{integration_name}|||command_{integration_name}"
            )
            script.yml.write_dict(script_content)
        else:
            script.yml.update(
                {
                    "dependson": {
                        "must": [f"{integration_name}|||command_{integration_name}"]
                    }
                }
            )

    @staticmethod
    def make_script_depend_on_script(script: Script, script__1: Script):
        other_script_name = script__1.yml.read_dict().get("name")
        script_content = script.yml.read_dict()

        if script_content.get("dependson"):
            script_content["dependson"]["must"].append(other_script_name)
            script.yml.write_dict(script_content)
        else:
            script.yml.update({"dependson": {"must": [other_script_name]}})


class ClassifierDependencies:
    @staticmethod
    def make_classifier_depend_on_incident_type_default(
        classifier: JSONBased, incident_type: JSONBased
    ):
        incident_type_id = incident_type.read_json_as_dict().get("id")
        classifier.update({"defaultIncidentType": incident_type_id})

    @staticmethod
    def make_classifier_depend_on_incident_type_key_type_map(
        classifier: JSONBased, incident_type: JSONBased
    ):
        incident_type_id = incident_type.read_json_as_dict().get("id")
        key_type_map = classifier.read_json_as_dict().get("keyTypeMap", {})
        key_type_map.update({"key": incident_type_id})
        classifier.update({"keyTypeMap": key_type_map})


class MapperDependencies:
    @staticmethod
    def make_mapper_depend_on_incident_type_default(
        mapper: JSONBased, incident_type: JSONBased
    ):
        incident_type_id = incident_type.read_json_as_dict().get("id")
        mapper.update({"defaultIncidentType": incident_type_id})

    @staticmethod
    def make_classifier_depend_on_incident_type_and_fields(
        mapper: JSONBased, incident_type: JSONBased, incidents_fields: List[JSONBased]
    ):
        incident_type_id = incident_type.read_json_as_dict().get("id")
        incidents_fields_ids = [
            incident_field.read_json_as_dict().get("id")
            for incident_field in incidents_fields
        ]
        mapping = mapper.read_json_as_dict().get("mapping", {})

        updates_to_map = {
            incident_type_id: {
                "internalMapping": {
                    incident_field_id: {"simple": "simple"}
                    for incident_field_id in incidents_fields_ids
                }
            }
        }

        mapping.update(updates_to_map)
        mapper.update({"mapping": mapping})


class IncidentTypeDependencies:
    @staticmethod
    def make_incident_type_depend_on_playbook(
        incident_type: JSONBased, playbook: Playbook
    ):
        playbook_id = playbook.yml.read_dict().get("id")
        incident_type.update({"playbookId": playbook_id})

    @staticmethod
    def make_incident_type_depend_on_script_pre_processing(
        incident_type: JSONBased, script: Script
    ):
        script_id = script.yml.read_dict().get("commonfields").get("id")
        incident_type.update({"preProcessingScript": script_id})


class IndicatorTypeDependencies:
    @staticmethod
    def make_indicator_type_depend_on_script_reputation(
        indicator_type: JSONBased, script: Script
    ):
        script_id = script.yml.read_dict().get("commonfields").get("id")
        indicator_type.update({"reputationScriptName": script_id})

    @staticmethod
    def make_indicator_type_depend_on_script_enhancement(
        indicator_type: JSONBased, script: Script
    ):
        script_id = script.yml.read_dict().get("commonfields").get("id")
        indicator_type.update({"enhancementScriptNames": [script_id]})


class LayoutDependencies:
    @staticmethod
    def make_layout_depend_on_incident_indicator_type(
        layout: JSONBased, incident_type: JSONBased
    ):
        incident_type_id = incident_type.read_json_as_dict().get("id")
        layout.update({"TypeName": incident_type_id})

    @staticmethod
    def make_layout_depend_on_incident_indicator_field(
        layout: JSONBased,
        indicators_fields: List[JSONBased],
        incidents_fields: List[JSONBased],
    ):
        indicators_fields_ids = [
            indicator_field.read_json_as_dict().get("id")
            for indicator_field in indicators_fields
        ]
        incidents_fields_ids = [
            incident_field.read_json_as_dict().get("id")
            for incident_field in incidents_fields
        ]

        layout_data = layout.read_json_as_dict().get("layout", {})
        updates_to_layout = {
            "tabs": {
                "sections": [
                    {
                        "displayType": "ROW",
                        "h": 2,
                        "i": "uuid",
                        "isVisible": True,
                        "items": [
                            {
                                "endCol": 2,
                                "fieldId": indicator_field_id,
                                "height": 24,
                                "id": "id",
                                "index": 0,
                                "startCol": 0,
                            }
                            for indicator_field_id in indicators_fields_ids
                        ],
                    },
                    {
                        "displayType": "ROW",
                        "h": 2,
                        "i": "uuid",
                        "isVisible": True,
                        "items": [
                            {
                                "endCol": 2,
                                "fieldId": incident_field_id,
                                "height": 24,
                                "id": "id",
                                "index": 0,
                                "startCol": 0,
                            }
                            for incident_field_id in incidents_fields_ids
                        ],
                    },
                ]
            }
        }

        layout_data.update(updates_to_layout)
        layout.update({"layout": layout_data})


class LayoutcontainerDependencies:
    @staticmethod
    def make_layoutcontainer_depend_on_incident_indicator_type(
        layoutcontainer: JSONBased, incident_type: JSONBased
    ):
        incident_type_id = incident_type.read_json_as_dict().get("id")
        layoutcontainer.update({"name": incident_type_id})

    @staticmethod
    def make_layout_depend_on_incident_indicator_field(
        layout: JSONBased,
        indicators_fields: List[JSONBased],
        incidents_fields: List[JSONBased],
    ):
        indicators_fields_ids = [
            indicator_field.read_json_as_dict().get("id")
            for indicator_field in indicators_fields
        ]
        incidents_fields_ids = [
            incident_field.read_json_as_dict().get("id")
            for incident_field in incidents_fields
        ]

        layout_data = layout.read_json_as_dict().get("layout", {})
        updates_to_layout = {
            "tabs": {
                "sections": [
                    {
                        "displayType": "ROW",
                        "h": 2,
                        "i": "uuid",
                        "isVisible": True,
                        "items": [
                            {
                                "endCol": 2,
                                "fieldId": indicator_field_id,
                                "height": 24,
                                "id": "id",
                                "index": 0,
                                "startCol": 0,
                            }
                            for indicator_field_id in indicators_fields_ids
                        ],
                    },
                    {
                        "displayType": "ROW",
                        "h": 2,
                        "i": "uuid",
                        "isVisible": True,
                        "items": [
                            {
                                "endCol": 2,
                                "fieldId": incident_field_id,
                                "height": 24,
                                "id": "id",
                                "index": 0,
                                "startCol": 0,
                            }
                            for incident_field_id in incidents_fields_ids
                        ],
                    },
                ]
            }
        }

        layout_data.update(updates_to_layout)
        layout.update({"detailsV2": layout_data})


class IncidentFieldDependencies:
    # Ignored by yaakovi
    # @staticmethod
    # def make_incident_field_depend_on_incident_type_associated(incident_field: JSONBased, incident_type: JSONBased):
    #     incident_type_id = incident_type.read_json_as_dict().get('id')
    #     incident_field.update({'associatedTypes': [incident_type_id]})
    #
    # @staticmethod
    # def make_incident_field_depend_on_incident_type_system_associated(incident_field: JSONBased,
    #                                                                   incident_type: JSONBased):
    #     incident_type_id = incident_type.read_json_as_dict().get('id')
    #     incident_field.update({'systemAssociatedTypes': [incident_type_id]})

    @staticmethod
    def make_incident_field_depend_on_script(incident_field: JSONBased, script: Script):
        script_id = script.yml.read_dict().get("commonfields").get("id")
        incident_field.update({"script": script_id})

    @staticmethod
    def make_incident_field_depend_on_script_field_calc(
        incident_field: JSONBased, script: Script
    ):
        script_id = script.yml.read_dict().get("commonfields").get("id")
        incident_field.update({"fieldCalcScript": script_id})


CLASSES = [
    IntegrationDependencies,
    PlaybookDependencies,
    ScriptDependencies,
    ClassifierDependencies,
    MapperDependencies,
    IncidentTypeDependencies,
    WidgetDependencies,
    IndicatorTypeDependencies,
    LayoutDependencies,
    LayoutcontainerDependencies,
    IncidentFieldDependencies,
]
METHODS_POOL: list = [
    (method_name, entity_class)
    for entity_class in CLASSES
    for method_name in list(entity_class.__dict__.keys())
    if "_" != method_name[0]
]


def get_entity_by_pack_number_and_entity_type(repo, pack_number, entity_type):
    if entity_type == "integration":
        return repo.packs[pack_number].integrations[0]

    if entity_type == "script":
        return repo.packs[pack_number].scripts[0]

    if entity_type == "playbook":
        return repo.packs[pack_number].playbooks[0]

    if entity_type == "classifier":
        return repo.packs[pack_number].classifiers[0]

    if entity_type == "mapper":
        return repo.packs[pack_number].mappers[0]

    if entity_type == "layout":
        return repo.packs[pack_number].layouts[0]

    if entity_type == "layoutcontainer":
        return repo.packs[pack_number].layoutcontainers[0]

    if entity_type == "incident_type":
        return repo.packs[pack_number].incident_types[0]

    if entity_type == "incident_field":
        return repo.packs[pack_number].incident_fields[0]

    if entity_type == "indicator_type":
        return repo.packs[pack_number].indicator_types[0]

    if entity_type == "indicator_field":
        return repo.packs[pack_number].indicator_fields[0]

    if entity_type == "widget":
        return repo.packs[pack_number].widgets[0]


LIST_ARGUMENTS_TO_METHODS = {
    "indicators_fields": "indicator_field",
    "incidents_fields": "incident_field",
}


def create_inputs_for_method(repo, current_pack, inputs_arguments):
    """Creates an `argument: object` dict of inputs for a method according to inputs_arguments.

    Args:
        repo (Repo): Content repo object.
        current_pack (int): ID of the pack that its objects will depend on other packs.
        inputs_arguments (list): List of entity types that  are needed as arguments to the method.

    Returns:
        Tuple(Dict, set):
            inputs_values (Dict): An `argument: object` dict of inputs for a method.
            dependencies (Set): All the packs' names that `current_pack` should depend on.
    """
    dependencies = set()

    inputs_values = {
        inputs_arguments[0]: get_entity_by_pack_number_and_entity_type(
            repo, current_pack, inputs_arguments[0]
        )
    }

    inputs_arguments = inputs_arguments[1:]
    # Ignores the `CommonTypes` pack in the flow, so only numeric packs will be chosen
    number_of_packs = len(repo.packs) - 1

    pack_numbers = range(1, number_of_packs)
    pack_number_cycle = itertools.cycle(pack_numbers)
    number_of_items_in_list = 0

    for arg in inputs_arguments:
        arg_type = arg.split("__")[0]
        if arg_type in LIST_ARGUMENTS_TO_METHODS.keys():
            number_of_items_in_list += 1

            if number_of_items_in_list > 5:
                number_of_items_in_list = 1

            pack_to_take_entity_from = next(pack_number_cycle)

            input_argument = []
            for _ in range(number_of_items_in_list):
                input_argument.append(
                    get_entity_by_pack_number_and_entity_type(
                        repo,
                        pack_to_take_entity_from,
                        LIST_ARGUMENTS_TO_METHODS[arg_type],
                    )
                )

                # The pack is not depend on packs with indicator_field because the Layout is of type incident
                if arg_type == "indicators_fields":
                    continue
                dependencies.add(f"pack_{pack_to_take_entity_from}")

        else:
            pack_to_take_entity_from = next(pack_number_cycle)
            input_argument = get_entity_by_pack_number_and_entity_type(
                repo, pack_to_take_entity_from, arg_type
            )

            # The pack is not depend on packs with indicator_type because the Layout is of type incident
            if arg_type == "indicator_type":
                continue
            dependencies.add(f"pack_{pack_to_take_entity_from}")

        inputs_values[arg] = input_argument

    return inputs_values, dependencies


def run_defined_methods(
    repo, current_pack, current_methods_pool, number_of_methods_to_choose
):
    """Runs over a set of methods with size number_of_methods_to_choose
        out of the current_methods_pool.

    Args:
        repo (Repo): Content repo object.
        current_pack (int): ID of the pack that its objects will depend on other packs.
        current_methods_pool (list): The pool of methods to run.
        number_of_methods_to_choose (int): Amount of methods to choose.

    Returns:
        Set. All the packs' names that `current_pack` should depend on.
    """
    all_dependencies = set()

    for i in range(number_of_methods_to_choose):
        chosen_method = current_methods_pool[i]
        method = getattr(chosen_method[1], chosen_method[0])
        inputs_arguments = inspect.getfullargspec(method)[0]

        args, dependencies = create_inputs_for_method(
            repo, current_pack, inputs_arguments
        )

        if chosen_method[0] == "make_integration_feed":
            all_dependencies.add("CommonTypes")

        all_dependencies = all_dependencies.union(dependencies)
        method(**args)

    return all_dependencies


def run_find_dependencies(mocker, repo_path, pack_name):
    with ChangeCWD(repo_path):
        # Circle froze on 3.7 dut to high usage of processing power.
        # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
        # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
        # and not the maximum amount.
        import demisto_sdk.commands.common.update_id_set as uis

        mocker.patch.object(uis, "cpu_count", return_value=1)
        PackDependencies.find_dependencies(
            pack_name, silent_mode=True, update_pack_metadata=True
        )


@pytest.mark.parametrize("test_number", range(5))
def test_dependencies(mocker, repo, test_number):
    """This test will run 5 times, when each time it will randomly generate dependencies in the repo and verify that
    the expected dependencies has been updated in the pack metadata correctly.

    Given
    - Content repository
    When
    - Running find_dependencies
    Then
    - Update packs dependencies in pack metadata
    """
    # Note: if DEMISTO_SDK_ID_SET_REFRESH_INTERVAL is set it can fail the test
    mock_is_external_repo(mocker, False)
    mocker.patch.dict(os.environ, {"DEMISTO_SDK_ID_SET_REFRESH_INTERVAL": "-1"})
    assert os.getenv("DEMISTO_SDK_ID_SET_REFRESH_INTERVAL") == "-1"
    number_of_packs = 10
    repo.setup_content_repo(number_of_packs)
    repo.setup_one_pack("CommonTypes")

    # Define fixed values or sequences
    pack_to_verify = 3  # Choose a specific pack to verify

    number_of_methods_to_choose = 2  # Choose a fixed number of methods to run
    dependencies = run_defined_methods(
        repo, pack_to_verify, METHODS_POOL.copy(), number_of_methods_to_choose
    )

    run_find_dependencies(mocker, repo.path, f"pack_{pack_to_verify}")

    dependencies_from_pack_metadata = (
        repo.packs[pack_to_verify]
        .pack_metadata.read_json_as_dict()
        .get("dependencies")
        .keys()
    )

    if f"pack_{pack_to_verify}" in dependencies:
        dependencies.remove(f"pack_{pack_to_verify}")

    assert dependencies == dependencies_from_pack_metadata


def mock_is_external_repo(mocker, is_external_repo_return):
    return mocker.patch(
        "demisto_sdk.commands.find_dependencies.find_dependencies.is_external_repository",
        return_value=is_external_repo_return,
    )


def test_dependencies_case_1(mocker, repo):
    """
    Given
        - Content repo with the following items:
            -"foo" pack containing:
              - playbook_foo
              - integration_foo
            - "bar" pack containing:
              - script_bar
            - "CommonTypes" pack containing:
              - incident field Email

            - playbook_foo using:
              - integration_foo is not skippable
              - script_bar is skippable
              - incident field Email as an input

    When
        - running find_dependencies

    Then
        - foo pack's pack_metadata should include the following dependencies:
          - bar
          - CommonTypes

    """
    mock_is_external_repo(mocker, False)
    # setup the packs
    pack_foo = repo.create_pack("foo")
    pack_bar = repo.create_pack("bar")
    pack_common_types = repo.create_pack("CommonTypes")

    playbook_foo = pack_foo.create_playbook("playbook_foo")
    integration_foo = pack_foo.create_integration(
        "integration_foo",
        yml={"name": "=integration_foo", "category": "", "script": {"type": "python"}},
    )
    script_bar = pack_bar.create_script(
        "script_bar", yml={"script": "", "type": "python", "name": "script_bar"}
    )
    incident_field_email = pack_common_types.create_incident_field(
        name="incident_Email",
        content={"id": "incident_Email", "name": "incident_Email"},
    )

    # make playbook_foo depend on integration_foo
    PlaybookDependencies.make_playbook_depend_on_integration_not_skippable(
        playbook_foo, integration_foo
    )

    # make playbook_foo depend on script_bar
    PlaybookDependencies.make_playbook_depend_on_script_skippable(
        playbook_foo, script_bar
    )

    # make playbook_foo depend on incident field Email
    PlaybookDependencies.make_playbook_depend_on_incident_field_input_complex(
        playbook_foo, incident_field_email
    )

    run_find_dependencies(mocker, repo.path, "foo")

    expected_dependencies = {"bar", "CommonTypes"}
    dependencies_from_pack_metadata = (
        pack_foo.pack_metadata.read_json_as_dict().get("dependencies").keys()
    )

    assert expected_dependencies == set(dependencies_from_pack_metadata)


def test_dependencies_case_2(mocker, repo):
    """
    Given
        - Content repo with the following items:
            -"foo" pack containing:
              - integration_foo which is a feed integration
            - "bar" pack containing:
              - mapper_in_bar

            - integration_foo using:
              - mapper_in_bar

    When
        - running find_dependencies

    Then
        - foo pack's pack_metadata should include the following dependencies:
          - bar
          - CommonTypes

    """
    mock_is_external_repo(mocker, False)
    # setup the packs
    pack_foo = repo.create_pack("foo")
    pack_bar = repo.create_pack("bar")
    pack_common_types = repo.create_pack("CommonTypes")

    integration_foo = pack_foo.create_integration(
        "integration_foo",
        yml={"name": "integration_foo", "category": "", "script": {"type": "python"}},
    )
    mapper_in_bar = pack_bar.create_mapper(
        name="mapper_in_bar",
        content={
            "id": "mapper_in_bar",
            "name": "mapper_in_bar",
            "mapping": {},
            "type": "mapping",
        },
    )
    # Pack can not be empty
    pack_common_types.create_integration(
        "integration_common_types",
        yml={
            "name": "integration_common_types",
            "category": "",
            "script": {"type": "python"},
        },
    )

    # make integration_foo feed
    IntegrationDependencies.make_integration_feed(integration_foo)

    # make integration_foo depend on mapper_in_bar
    IntegrationDependencies.make_integration_depend_on_mapper_in(
        integration_foo, mapper_in_bar
    )

    run_find_dependencies(mocker, repo.path, "foo")

    expected_dependencies = {"bar", "CommonTypes"}
    dependencies_from_pack_metadata = (
        repo.packs[0].pack_metadata.read_json_as_dict().get("dependencies").keys()
    )

    assert expected_dependencies == set(dependencies_from_pack_metadata)
