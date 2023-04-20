import re
from typing import Any

from demisto_sdk.commands.common.constants import MarketplaceVersions

NOT_WRAPPED_RE_MAPPING = {
    rf"(?<!<-){key}(?!->)": value
    for key, value in {
        "incident": "alert",
        "Incident": "Alert",
        "incidents": "alerts",
        "Incidents": "Alerts",
        "INCIDENT": "ALERT",
        "INCIDENTS": "ALERTS",
    }.items()
}

WRAPPED_MAPPING = {
    rf"<-{key}->": key
    for key in (
        "incident",
        "incidents",
        "Incident",
        "Incidents",
        "INCIDENT",
        "INCIDENTS",
    )
}


def prepare_descriptions_and_names_helper(
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
            # Since it is a server key, we do not want to change it
            if description != "commands.local.cmd.set.incident":
                data["tasks"][task_key]["task"][
                    "description"
                ] = prepare_descriptions_and_names_helper(
                    description, replace_incident_to_alert
                )

        if name := task_value.get("task", {}).get("name", ""):
            data["tasks"][task_key]["task"][
                "name"
            ] = prepare_descriptions_and_names_helper(name, replace_incident_to_alert)

    # The external playbook's description
    if description := data.get("description"):
        data["description"] = prepare_descriptions_and_names_helper(
            description, replace_incident_to_alert
        )

    # The external playbook's name
    if name := data.get("name"):
        data["name"] = prepare_descriptions_and_names_helper(
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


def replace_playbook_access_fields_recursively(datum: Any) -> Any:

    if isinstance(datum, list):
        return [replace_playbook_access_fields_recursively(item) for item in datum]

    elif isinstance(datum, dict):
        for key, val in datum.items():
            if isinstance(val, str):
                if key in {"root", "simple"} and "incident" in val:
                    val = re.sub(
                        r"(?<!\.)\bincident\b", "alert", val
                    )  # values like 'X.incident' should not be replaced

                if key == "script" and val == "Builtin|||setIncident":
                    val = val.replace("setIncident", "setAlert")

                datum[key] = val

            else:
                datum[key] = replace_playbook_access_fields_recursively(val)

    return datum


def prepare_playbook_access_fields(data: dict) -> dict:
    data = replace_playbook_access_fields_recursively(data)
    return data
