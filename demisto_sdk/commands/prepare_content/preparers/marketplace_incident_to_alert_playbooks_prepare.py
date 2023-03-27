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
        # Replace incidents to alerts only for XSIAM
        if marketplace == MarketplaceVersions.MarketplaceV2:
            MarketplaceIncidentToAlertPlaybooksPreparer.prepare_descriptions_and_names(
                data, True
            )

        # For all Marketplaces
        MarketplaceIncidentToAlertPlaybooksPreparer.prepare_descriptions_and_names(
            data, False
        )

        return data

    @staticmethod
    def prepare_descriptions_and_names(data: dict, replace_incident_to_alert: bool):

        for k, v in data.get("tasks", {}).items():
            if description := v.get("task", {}).get("description", ""):
                if replace_incident_to_alert:
                    MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(
                        data, "description", description, k
                    )
                else:
                    MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(
                        data, "description", description, k
                    )
            if name := v.get("task", {}).get("name", ""):
                if replace_incident_to_alert:
                    MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(
                        data, "name", name, k
                    )
                else:
                    MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(
                        data, "name", name, k
                    )

        # The external description
        if description := data.get("description"):
            if replace_incident_to_alert:
                MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(
                    data, "description", description
                )
            else:
                MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(
                    data, "description", description
                )

        # The external name
        if name := data.get("name"):
            if replace_incident_to_alert:
                MarketplaceIncidentToAlertPlaybooksPreparer.replace_incident_to_alert(
                    data, "name", name
                )
            else:
                MarketplaceIncidentToAlertPlaybooksPreparer.remove_wrapper_from_incident(
                    data, "name", name
                )

    @staticmethod
    def replace_incident_to_alert(
        data: dict,
        name_or_description_field: str,
        name_or_description_field_content: str,
        key: str = None,
    ):
        replacements = {r"(?<!<-)incident(?!->)": "alert",
                   r"(?<!<-)Incident(?!->)": "Alert",
                   r"(?<!<-)incidents(?!->)": "alerts",
                   r"(?<!<-)Incidents(?!->)": "Alerts"}

        new_content = name_or_description_field_content

            for pattern, replace_with in replacements.items():
            new_content = re.sub(
                pattern, replace_with, new_content
            )

        if key:
            data["tasks"][key]["task"][name_or_description_field] = new_content
        else:
            data[name_or_description_field] = new_content

    @staticmethod
    def remove_wrapper_from_incident(
        data: dict,
        name_or_description_field: str,
        name_or_description_field_content: str,
        key: str = None,
    ):
        mapping = {r"<-incident->": "incident",
                   r"<-Incident->": "Incident",
                   r"<-incidents->": "incidents",
                   r"<-Incidents->": "Incidents"}
        new_content = name_or_description_field_content
        for pattern in mapping:
            new_content = re.sub(
                pattern, mapping[pattern], new_content
            )

        if key:
            data["tasks"][key]["task"][name_or_description_field] = new_content
        else:
            data[name_or_description_field] = new_content
