import inspect
import types
from dataclasses import fields
from docstring_parser import parse
from typing import Union
from enum import EnumMeta


class DocStringFlags:
    IGNORE_ARG = "!no-auto-argument"


def docstring_to_descriptions(o):
    docstring = parse(o.__doc__)
    docstring_params = {}
    for param in docstring.params:
        docstring_params[param.arg_name] = param.description

    return docstring_params


def get_classes(module):
    classes = []
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            classes.append(obj)


def get_command_register(module):
    command_register = module.COMMANDS
    return command_register


def grid_fields_from_class(cls):
    """
    Builds n number of fields from a result class object
    """
    if type(cls) is types.GenericAlias:
        cls = cls.__args__[0]

    return_fields = []
    name = f"{cls._title}"
    d = {
        "associatedToAll": True,
        "caseInsensitive": True,
        "version": -1,
        "sla": 0,
        "shouldCommit": True,
        "threshold": 72,
        "propagationLabels": [
            "all"
        ],
        "name": name,
        "isReadOnly": False,
        "editForm": True,
        "commitMessage": "Field edited",
        "type": "grid",
        "defaultRows": [
            {}
        ],
        "unsearchable": False,
        "breachScript": "",
        "shouldPublish": True,
        "description": "Auto Generated",
        "columns": [],
        "group": 0,
        "required": False
    }
    if hasattr(cls, "_summary_cls"):
        summary_d = d.copy()
        summary_d["name"] = name
        summary_cls = getattr(cls, "_summary_cls")
        columns = []
        for field in fields(summary_cls):
            field_d = {
                "displayName": field.name,
                "isReadOnly": False,
                "required": False,
                "isDefault": True,
                "type": "shortText",
                "width": 150,
                "script": "",
                "fieldCalcScript": "",
                "key": field.name.replace("_", "")
            }
            columns.append(field_d)

        summary_d["columns"] = columns
        return_fields.append(summary_d)

    if hasattr(cls, "_result_cls"):
        result_d = d.copy()
        result_d["name"] = name + " Result"
        result_cls = getattr(cls, "_result_cls")
        columns = []

        for field in fields(result_cls):
            field_d = {
                "displayName": field.name,
                "isReadOnly": False,
                "required": False,
                "isDefault": True,
                "type": "shortText",
                "width": 150,
                "script": "",
                "fieldCalcScript": "",
                "key": field.name.replace("_", "")
            }
            columns.append(field_d)

        result_d["columns"] = columns
        return_fields.append(result_d)

    if not hasattr(cls, "_result_cls") and not hasattr(cls, "_summary_cls"):
        result_d = d.copy()
        result_d["name"] = name
        columns = []

        for field in fields(cls):
            field_d = {
                "displayName": field.name,
                "isReadOnly": False,
                "required": False,
                "isDefault": True,
                "type": "shortText",
                "width": 150,
                "script": "",
                "fieldCalcScript": "",
                "key": field.name.replace("_", "")
            }
            columns.append(field_d)

        result_d["columns"] = columns
        return_fields.append(result_d)

    return return_fields


def outputs_from_class(cls):
    """Note; must be dataclass or list of dataclass"""
    outputs = []
    if not cls:
        return
    # If the passed cls is GenericAlias, then we're returning a bare list of objects.
    if type(cls) is types.GenericAlias:
        cls = cls.__args__[0]

    if not hasattr(cls, "_summary_cls") and not hasattr(cls, "_result_cls"):
        docstring_params = docstring_to_descriptions(cls)
        for field in fields(cls):
            d = {
                "contextPath": cls._output_prefix + "." + field.name,
                "type": "Unknown"
            }
            description = docstring_params.get(field.name)
            if description:
                d["description"] = description

            outputs.append(d)

    if hasattr(cls, "_summary_cls"):
        summary_cls = getattr(cls, "_summary_cls")
        docstring_params = docstring_to_descriptions(summary_cls)
        for field in fields(summary_cls):
            d = {
                "contextPath": cls._output_prefix + "." + "Summary." + field.name,
                "type": "Unknown"
            }
            description = docstring_params.get(field.name)
            if description:
                d["description"] = description

            outputs.append(d)

    if hasattr(cls, "_result_cls"):
        summary_cls = getattr(cls, "_result_cls")
        docstring_params = docstring_to_descriptions(summary_cls)
        for field in fields(summary_cls):
            d = {
                "contextPath": cls._output_prefix + "." + "Result." + field.name,
                "type": "Unknown"
            }
            description = docstring_params.get(field.name)
            if description:
                d["description"] = description

            outputs.append(d)

    return outputs


def script_command_from_function(command_name, func):
    docstring = parse(func.__doc__)

    command = {
        "comment": docstring.short_description,
        "name": command_name,
        "args": [],
        "outputs": [],
        "commonfields": {
            "id": command_name,
            "version": -1
        }
    }

    annotations = func.__annotations__
    return_class = annotations.get("return")
    args = inspect.signature(func).parameters
    docstring = parse(func.__doc__)
    docstring_params = {}
    for param in docstring.params:
        docstring_params[param.arg_name] = param.description

    command_args = []
    for arg_name, param in args.items():
        d = {
            "name": arg_name,
            "isArray": False,
            "description": arg_name,
            "required": False,
        }
        if arg_name in docstring_params:
            description = docstring_params.get(arg_name)
            if DocStringFlags.IGNORE_ARG in description:
                # If we've ignored this argument
                continue

            d["description"] = docstring_params.get(arg_name)

        if param.default is not inspect.Parameter.empty:
            d["defaultValue"] = param.default
        else:
            d["required"] = True
        if type(param.annotation) in [list, Union[list, dict]]:
            d["isArray"] = True
        if param.annotation in [list, Union[list, dict]]:
            d["isArray"] = True
        if type(param.annotation) is EnumMeta:
            d["predefined"] = handle_enum(param.annotation)
            d["auto"] = "PREDEFINED"

        command_args.append(d)

    command["args"] = command_args
    command["outputs"] = outputs_from_class(return_class)
    return command


def handle_enum(e):
    result = []
    for attribute in list(e):
        result.append(attribute.value)
    return result


def command_from_function(command_name, func):
    docstring = parse(func.__doc__)

    command = {
        "deprecated": False,
        "description": docstring.short_description,
        "name": command_name,
        "arguments": [],
        "outputs": []
    }

    annotations = func.__annotations__
    return_class = annotations.get("return")
    args = inspect.signature(func).parameters
    docstring = parse(func.__doc__)
    docstring_params = {}
    for param in docstring.params:
        docstring_params[param.arg_name] = param.description

    command_args = []
    for arg_name, param in args.items():
        d = {
            "name": arg_name,
            "isArray": False,
            "description": arg_name,
            "required": False,
            "secret": False,
            "default": False
        }
        if arg_name in docstring_params:
            description = docstring_params.get(arg_name)
            if DocStringFlags.IGNORE_ARG in description:
                # If we've ignored this argument
                continue

            d["description"] = docstring_params.get(arg_name)

        if param.default is not inspect.Parameter.empty:
            d["required"] = False
            d["defaultValue"] = param.default
        else:
            d["required"] = True
        if type(param.annotation) is list:
            d["isArray"] = True
        if param.annotation in [list, Union[list, dict]]:
            d["isArray"] = True
        if type(param.annotation) is EnumMeta:
            d["predefined"] = handle_enum(param.annotation)
            d["auto"] = "PREDEFINED"

        command_args.append(d)

    command["arguments"] = command_args
    command["outputs"] = outputs_from_class(return_class)
    return command


def build_script_commands_from_register(command_register):
    commands = []
    for command_name, func in command_register.commands.items():
        if command_name == "test-module":
            continue
        commands.append(command_from_function(command_name, func))

    for command_name, func in command_register.file_commands.items():
        commands.append(command_from_function(command_name, func))

    return commands


def build_incident_fields_from_register(command_register):
    grid_fields = []
    for command_name, func in command_register.commands.items():
        if command_name == "test-module":
            continue
        annotations = func.__annotations__
        return_class = annotations.get("return")
        grid_fields = grid_fields + grid_fields_from_class(return_class)

    return {
        "incidentFields": grid_fields
    }


def build_configuration_from_param_class(demisto_param_class):
    r = []
    docstring = parse(demisto_param_class.__doc__)
    docstring_params = {}
    for param in docstring.params:
        docstring_params[param.arg_name] = param.description

    for field in fields(demisto_param_class):
        if field.name == "credentials":
            d = {
                "name": field.name,
                "type": 9
            }
            if field.name in docstring_params:
                d["display"] = docstring_params.get(field.name)
            r.append(d)
        else:
            d = {
                "name": field.name,
                "type": 0
            }
            if field.name in docstring_params:
                d["display"] = docstring_params.get(field.name)
            r.append(d)

    return r


def rename(integration_dict: dict, new_integration_name: str):
    integration_dict["name"] = new_integration_name
    integration_dict["commonfields"]["id"] = new_integration_name

    return integration_dict