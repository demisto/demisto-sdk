import logging

from demisto_sdk.commands.common.constants import MarketplaceVersions

logger = logging.getLogger("demisto-sdk")


class MarketplaceIncidentToAlertPlaybooksPreparer:

    @staticmethod
    def prepare(
            data: dict,
            marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
    ) -> dict:
        """
        Iterate over all the given content item description fields and if a description field contains the word
        incident / incidents, then replace it with alert / alerts.
        Args:
            data: content item data
            marketplace: Marketplace. Replace just for XSIAM Marketplace.

        Returns: A (possibly) modified content item data

        """
        # Replace incidents to alerts only for XSIAM
        if marketplace != MarketplaceVersions.MarketplaceV2:
            return data

        # the task's description
        for k, v in data.get('tasks', {}).items():
            if description := v.get('task', {}).get('description', ''):
                data[k]['task']['description'] =\
                        MarketplaceIncidentToAlertPreparer.replace_incident_to_alert(description)

        # the external description
        if description := data.get('description'):
            data['description'] = MarketplaceIncidentToAlertPreparer.replace_incident_to_alert(description)

    @staticmethod
    def replace_incident_to_alert(description: str) -> str:
        new_description = ''
        if '<-incident->' or '<-incidents->' in description:
            new_description = description.replace('<-incident->', 'incident')
            new_description = new_description.replace('<-incidents->', 'incidents')
        elif 'incident' or 'incidents' in description:
            new_description = description.replace('incident', 'alert')
            new_description = new_description.replace('incidents', 'alerts')

        return new_description or description



