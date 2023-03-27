import logging
import re

from demisto_sdk.commands.common.constants import MarketplaceVersions

logger = logging.getLogger("demisto-sdk")


class MarketplaceIncidentToAlertPlaybooksPreparer:
    @staticmethod
    def prepare(
        data: dict,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    ) -> dict:
        """
        Iterate over all the given content item descriptions and name fields and if a description or name field contains
        the word incident / incidents, then replace it with alert / alerts in case of XSIAM Marketplace.
        In any case (for all Marketplaces) remove wrapper (<-incident-> to incident, <-incidents-> to incidents).
        Args:
            data: content item data
            marketplace: Marketplace.

        Returns: A (possibly) modified content item data

        """

        MarketplaceIncidentToAlertPlaybooksPreparer.prepare_descriptions_and_names(
            data, marketplace
        )

        return data

    @staticmethod
    def prepare_descriptions_and_names(data: dict, marketplace: MarketplaceVersions):
        # Replace incidents to alerts only for XSIAM
        replace_incident_to_alert = marketplace == MarketplaceVersions.MarketplaceV2

        for k, v in data.get("tasks", {}).items():
            if description := v.get("task", {}).get("description", ""):
                if replace_incident_to_alert:
                    description = MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(description)

                MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(
                    data, "description", description, k
                )

            if name := v.get("task", {}).get("name", ""):
                if replace_incident_to_alert:
                    name = MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(name)

                MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(data, "name", name, k)

        if description := data.get("description"):
            if replace_incident_to_alert:
                description = MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(description)

            MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(data, "description", description)

        if name := data.get("name"):
            if replace_incident_to_alert:
                name = MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(name)

            MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(data, "name", name)

    @staticmethod
    def replace_incident_to_alert(name_or_description_field_content: str) -> str:
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

    @staticmethod
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
