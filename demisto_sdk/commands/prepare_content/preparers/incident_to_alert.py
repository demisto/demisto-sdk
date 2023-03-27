import re

from demisto_sdk.commands.common.constants import MarketplaceVersions

INCIDENT_TO_ALERT = {
    fr"(?<!<-){key}(?!->)": value
    for key, value in {
        "incident": "alert",
        "Incident": "Alert",
        "incidents": "alerts",
        "Incidents": "Alerts",
        "INCIDENT": "ALERT",
        "INCIDENTS": "ALERTS",
    }.items()
}

REMOVE_WRAPPER_FROM_INCIDENT = {fr"<-{key}->": key for key in
                                ("incident", "incidents", "Incident", "Incidents", "INCIDENT", "INCIDENTS")}


def prepare_descriptions_and_names_helper(name_or_description_content: str, replace_incident_to_alert: bool):
    if replace_incident_to_alert:
        name_or_description_content = edit_names_and_descriptions_for_playbook(name_or_description_content,
                                                                               replace_incident_to_alert)
    return edit_names_and_descriptions_for_playbook(name_or_description_content, False)  # Here remove the wrapper


def prepare_descriptions_and_names(data: dict, marketplace: MarketplaceVersions) -> dict:
    # Replace incidents to alerts only for XSIAM
    replace_incident_to_alert = marketplace == MarketplaceVersions.MarketplaceV2

    # Descriptions and names for all tasks
    for task_key, task_value in data.get("tasks", {}).items():

        if description := task_value.get("task", {}).get("description", ""):
            data['tasks'][task_key]['task']['description'] = \
                prepare_descriptions_and_names_helper(description, replace_incident_to_alert)

        if name := task_value.get("task", {}).get("name", ""):
            data['tasks'][task_key]['task']['name'] = prepare_descriptions_and_names_helper(name,
                                                                                            replace_incident_to_alert)

    # The external playbook's description
    if description := data.get("description"):
        data['description'] = prepare_descriptions_and_names_helper(description, replace_incident_to_alert)

    # The external playbook's name
    if name := data.get("name"):
        data['name'] = prepare_descriptions_and_names_helper(name, replace_incident_to_alert)

    return data


def edit_names_and_descriptions_for_playbook(name_or_description_field_content: str,
                                             replace_incident_to_alert: bool) -> str:
    if replace_incident_to_alert:
        replacements = INCIDENT_TO_ALERT
    else:
        replacements = REMOVE_WRAPPER_FROM_INCIDENT

    new_content = name_or_description_field_content

    for pattern, replace_with in replacements.items():
        new_content = re.sub(
            pattern, replace_with, new_content
        )

    return new_content
