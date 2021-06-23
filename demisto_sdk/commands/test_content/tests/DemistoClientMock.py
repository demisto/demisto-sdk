import re
from typing import List
from unittest.mock import MagicMock

from demisto_sdk.commands.common.constants import PB_Status


class DemistoClientMock:
    INCIDNET_NUMNER = 1
    INCIDENT_SEARCH_PATTERN = re.compile(r'/inv-playbook/[\d]+')
    INVESTIGATION_SEARCH_PATTERN = re.compile(r'/investigation/[\d]+')
    INTEGRATION_SEARCH_PATTERN = re.compile(r'/settings/integration/(.*)')
    INCIDENT_QUERY_PATTERN = re.compile(r'id: ([\d]+)')
    GENERIC_RESPONSE = ("{}", 200, "")
    INSTANCES = []
    CONFIGURATIONS = []
    api_client = MagicMock()
    demisto_api = MagicMock()
    api_client.configuration.host = 'https://1.1.1.1'

    def __init__(self, integrations: List[str] = None):
        """
        Configures the integrations known by the server which will be returned by the search integration request.
        Args:
            integrations: A list of integration names to be returned.
        """
        if integrations:
            for integration in integrations:
                self.add_integration_configuration(integration)

    @staticmethod
    def configure(*_, **__):
        return DemistoClientMock

    @staticmethod
    def create_incident(**_):
        DemistoClientMock.INCIDNET_NUMNER += 1
        return MagicMock(id=DemistoClientMock.INCIDNET_NUMNER,
                         investigation_id=DemistoClientMock.INCIDNET_NUMNER)

    @staticmethod
    def search_incidents(filter):
        incident_id = DemistoClientMock.INCIDENT_QUERY_PATTERN.findall(filter.filter.query)[0]
        return MagicMock(total=1,
                         data=[MagicMock(id=incident_id, investigation_id=incident_id)])
        pass

    @classmethod
    def generic_request_func(cls, self, method, path, **kwargs):
        response_mapper = {
            '/incident/batchDelete': {'POST': cls._delete_incident},
            '/settings/integration/search': {'POST': cls._search_integration_instances},
            '/settings/integration': {'PUT': cls._create_integration_instance},
            '/settings/integration/test': {'POST': cls._test_integration_instance},
            '/containers/reset': {'POST': cls._reset_containers},
            '/system/config': {'GET': cls._get_system_config,
                               'POST': cls._update_system_config}
        }
        if method == 'GET' and cls.INCIDENT_SEARCH_PATTERN.match(path):
            return cls._get_investigation_playbook_state(**kwargs)
        if method == 'POST' and cls.INVESTIGATION_SEARCH_PATTERN.match(path):
            return cls._get_investigation_playbook_state(**kwargs)
        if method == 'DELETE' and cls.INTEGRATION_SEARCH_PATTERN.match(path):
            integration_id = cls.INTEGRATION_SEARCH_PATTERN.findall(path)[0]
            return cls._delete_integration_instance(integration_id)
        mock_function = response_mapper.get(path, {}).get(method)
        if not mock_function:
            return cls.GENERIC_RESPONSE
        return mock_function(**kwargs)

    @staticmethod
    def _delete_incident(*_, **__):
        return DemistoClientMock.GENERIC_RESPONSE

    @staticmethod
    def _search_integration_instances(*_, **__):
        return str({'configurations': DemistoClientMock.CONFIGURATIONS,
                    'instances': DemistoClientMock.INSTANCES}), 200, ""

    @staticmethod
    def _create_integration_instance(*_, **kwargs):
        module_instance = kwargs.get('body')
        module_instance['id'] = module_instance['brand']
        DemistoClientMock.INSTANCES.append(module_instance)
        return str(module_instance), 200, ""

    @staticmethod
    def _delete_integration_instance(integration_id):
        for instance in DemistoClientMock.INSTANCES:
            if instance.get('id') == integration_id:
                DemistoClientMock.INSTANCES.remove(instance)
        return DemistoClientMock.GENERIC_RESPONSE

    @staticmethod
    def _test_integration_instance(*_, **__):
        return str({"success": True, "message": ""}), 200, ""

    @staticmethod
    def _get_investigation_playbook_state(*_, **__):
        return str({'state': PB_Status.COMPLETED}), 200, ""

    @staticmethod
    def _reset_containers(*_, **__):
        return DemistoClientMock.GENERIC_RESPONSE

    @staticmethod
    def _get_system_config(*_, **__):
        return str({'sysConf': {}}), 200, ""

    @staticmethod
    def _update_system_config(*_, **__):
        return DemistoClientMock.GENERIC_RESPONSE

    @staticmethod
    def add_integration_configuration(integration_name):
        DemistoClientMock.CONFIGURATIONS.append({
            'id': integration_name,
            'name': integration_name,
            'category': 'some_category',
            'configuration': [
                {'display': 'proxy',
                 'name': 'proxy',
                 'defaultValue': True},
                {'display': 'insecure',
                 'name': 'insecure',
                 'defaultValue': True}
            ]
        })
