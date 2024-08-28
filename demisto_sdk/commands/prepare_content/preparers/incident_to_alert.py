import copy
import re
from typing import Any, List

from demisto_sdk.commands.common.constants import (
    TABLE_INCIDENT_TO_ALERT,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

NOT_WRAPPED_RE_MAPPING = {
    rf"(?<!<-){key}(?!->)": value for key, value in TABLE_INCIDENT_TO_ALERT.items()
}

WRAPPED_MAPPING = {rf"<-{key}->": key for key in TABLE_INCIDENT_TO_ALERT.keys()}

WRAPPER_SCRIPT = {
    "python": "register_module_line('script_name', 'start', __line__())\n\n"
    "return_results(demisto.executeCommand('<original_script_name>', demisto.args()))\n\n"
    "register_module_line('script_name', 'end', __line__())",
    "javascript": "return executeCommand('<original_script_name>', args)\n",
}


def prepare_descriptions_and_names_classifier(
    name_or_description_content: str, replace_incident_to_alert: bool
):
    if replace_incident_to_alert:
        name_or_description_content = edit_names_and_descriptions_for_playbook(
            name_or_description_content, replace_incident_to_alert
        )
    return edit_names_and_descriptions_for_playbook(
        name_or_description_content, False
    )  # Here remove the wrapper


def prepare_descriptions_and_names(
    data: dict, marketplace: MarketplaceVersions
) -> dict:
    # Replace incidents to alerts only for XSIAM
    replace_incident_to_alert = marketplace == MarketplaceVersions.MarketplaceV2

    # Descriptions and names for all tasks
    for task_key, task_value in data.get("tasks", {}).items():
        if description := task_value.get("task", {}).get("description", ""):
            if description != "commands.local.cmd.set.incident":
                # Since it is a server key, we do not want to change it
                data["tasks"][task_key]["task"]["description"] = (
                    prepare_descriptions_and_names_classifier(
                        description, replace_incident_to_alert
                    )
                )

        if name := task_value.get("task", {}).get("name", ""):
            data["tasks"][task_key]["task"]["name"] = (
                prepare_descriptions_and_names_classifier(
                    name, replace_incident_to_alert
                )
            )

    # The external playbook's description
    if description := data.get("description"):
        data["description"] = prepare_descriptions_and_names_classifier(
            description, replace_incident_to_alert
        )

    # The external playbook's name
    if name := data.get("name"):
        data["name"] = prepare_descriptions_and_names_classifier(
            name, replace_incident_to_alert
        )

    return data


def edit_names_and_descriptions_for_playbook(
    name_or_description_field_content: str, replace_incident_to_alert: bool
) -> str:
    if replace_incident_to_alert:
        replacements = NOT_WRAPPED_RE_MAPPING
    else:
        replacements = WRAPPED_MAPPING

    new_content = name_or_description_field_content

    for pattern, replace_with in replacements.items():
        new_content = re.sub(pattern, replace_with, new_content)

    return new_content


def replace_playbook_access_fields_recursively(
    datum: Any, replaceable_scripts: List[str]
) -> Any:
    if isinstance(datum, list):
        return [
            replace_playbook_access_fields_recursively(item, replaceable_scripts)
            for item in datum
        ]

    elif isinstance(datum, dict):
        for key, val in datum.items():
            if isinstance(val, str):
                if key in {"root", "simple"} and "incident" in val:
                    val = re.sub(
                        r"(?<!\.)\bincident\b", "alert", val
                    )  # values like 'X.incident' should not be replaced

                if key == "script" and val == "Builtin|||setIncident":
                    val = val.replace("setIncident", "setAlert")

                elif key == "scriptName" and val in replaceable_scripts:
                    val = edit_ids_names_and_descriptions_for_script(val, True)
                datum[key] = val

            else:
                datum[key] = replace_playbook_access_fields_recursively(
                    val, replaceable_scripts
                )

    return datum


def get_script_names_from_playbooks_intended_preparation(
    playbook: ContentItem,
) -> List[str]:
    """
    Extracts all scripts of the Playbook and filters only those intended
    for special preparation of `incident to alert`.
    """
    # Import inside the function to avoiding circular import
    from demisto_sdk.commands.content_graph.objects.script import Script

    return [
        name.object_id
        for name in [
            content_item.content_item_to
            for content_item in playbook.uses
            if isinstance(content_item.content_item_to, Script)
            and content_item.content_item_to.is_incident_to_alert(
                MarketplaceVersions.MarketplaceV2
            )
        ]
    ]


def prepare_playbook_access_fields(data: dict, playbook: ContentItem) -> dict:
    script_intended_prepare = get_script_names_from_playbooks_intended_preparation(
        playbook
    )
    return replace_playbook_access_fields_recursively(data, script_intended_prepare)


def edit_ids_names_and_descriptions_for_script(
    data: str, incident_to_alert: bool = False
):
    """
    In any case:
        When the word incident appears with a wrapper like this: <-incident-> the wrapper is removed.
    If `incident_to_alert` is true:
        Replace the word incident with alert when it does not have a wrapper (<-incident->).
    """
    if incident_to_alert:
        for pattern, replace_with in NOT_WRAPPED_RE_MAPPING.items():
            data = re.sub(pattern, replace_with, data)

    for pattern, replace_with in WRAPPED_MAPPING.items():
        data = re.sub(pattern, replace_with, data)
    return data


def create_wrapper_script(data: dict) -> dict:
    copy_data = copy.deepcopy(data)
    try:
        copy_data["script"] = (
            WRAPPER_SCRIPT[copy_data["type"]]
            .replace(
                "<original_script_name>",
                edit_ids_names_and_descriptions_for_script(copy_data["name"], True),
            )
            .replace("script_name", copy_data["name"])
        )
    except Exception:
        logger.exception("Failed to create the wrapper script")

    copy_data = set_deprecated_for_scripts(copy_data, old_script=True)
    logger.debug(
        f"Created {copy_data['name']} script, "
        f"wrapping {data['name']}, as part of incidents-to-alerts preparation"
    )

    return replace_script_access_fields_recursively(copy_data)


def replace_script_access_fields_recursively(
    data: Any, incident_to_alert: bool = False
) -> Any:
    if isinstance(data, list):
        return [
            replace_script_access_fields_recursively(item, incident_to_alert)
            for item in data
        ]
    if isinstance(data, dict):
        for key in tuple(data.keys()):
            value = data[key]
            if isinstance(value, str):
                if key in {"id", "comment", "description"} or (
                    # To avoid replacing the name of the arguments
                    key == "name" and "commonfields" in data
                ):
                    data[key] = edit_ids_names_and_descriptions_for_script(
                        value, incident_to_alert
                    )
            else:
                data[key] = replace_script_access_fields_recursively(
                    value, incident_to_alert
                )
    return data


def replace_register_module_line_for_script(data: dict):
    new_name = edit_ids_names_and_descriptions_for_script(
        data["name"], incident_to_alert=True
    )
    for state in ("start", "end"):
        data["script"] = data["script"].replace(
            f"register_module_line('{data['name']}', '{state}', __line__())",
            f"register_module_line('{new_name}', '{state}', __line__())",
        )

    return data


def set_deprecated_for_scripts(data: dict, old_script: bool):
    if old_script:
        data["deprecated"] = True
    elif "deprecated" not in data:
        data["deprecated"] = False
    return data


def prepare_script_access_fields(data: dict, incident_to_alert: bool) -> dict:
    if incident_to_alert:
        data = replace_register_module_line_for_script(data)
        data = set_deprecated_for_scripts(data, old_script=False)
    return replace_script_access_fields_recursively(data, incident_to_alert)
