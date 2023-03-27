import re

from demisto_sdk.commands.common.constants import MarketplaceVersions


def prepare_descriptions_and_names(data: dict, marketplace: MarketplaceVersions) -> dict:
    # Replace incidents to alerts only for XSIAM
    replace_incident_to_alert = marketplace == MarketplaceVersions.MarketplaceV2

    for k, v in data.get("tasks", {}).items():
        if description := v.get("task", {}).get("description", ""):
            if replace_incident_to_alert:
                description = name_or_description_incident_to_alert(description)

            remove_wrapper_from_incident(data, "description", description, k)

        if name := v.get("task", {}).get("name", ""):
            if replace_incident_to_alert:
                name = name_or_description_incident_to_alert(name)

            remove_wrapper_from_incident(data, "name", name, k)

    if description := data.get("description"):
        if replace_incident_to_alert:
            description = name_or_description_incident_to_alert(description)

        remove_wrapper_from_incident(data, "description", description)

    if name := data.get("name"):
        if replace_incident_to_alert:
            name = name_or_description_incident_to_alert(name)

        remove_wrapper_from_incident(data, "name", name)

    return data


def name_or_description_incident_to_alert(name_or_description_field_content: str) -> str:
    replacements = {r"(?<!<-)incident(?!->)": "alert",
                    r"(?<!<-)Incident(?!->)": "Alert",
                    r"(?<!<-)incidents(?!->)": "alerts",
                    r"(?<!<-)Incidents(?!->)": "Alerts"}

    new_content = name_or_description_field_content

    for pattern, replace_with in replacements.items():
        new_content = re.sub(
            pattern, replace_with, new_content
        )

    return new_content


def remove_wrapper_from_incident(
        data: dict,
        name_or_description_field: str,
        name_or_description_field_content: str,
        task_key: str = None,
):
    replacements = {r"<-incident->": "incident",
                    r"<-Incident->": "Incident",
                    r"<-incidents->": "incidents",
                    r"<-Incidents->": "Incidents"}
    new_content = name_or_description_field_content
    for pattern, replace_with in replacements.items():
        new_content = re.sub(
            pattern, replace_with, new_content
        )

    if task_key:
        data["tasks"][task_key]["task"][name_or_description_field] = new_content
    else:
        data[name_or_description_field] = new_content