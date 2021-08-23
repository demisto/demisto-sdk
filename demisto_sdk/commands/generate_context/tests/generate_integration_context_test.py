import json
import os
from typing import Dict, List

import pytest


def test_generate_context_from_outputs():
    """
    Given
        - A string representing an example output json
    When
        - generating context objects
    Then
        - Ensure the outputs are correct
    """
    from demisto_sdk.commands.generate_context.generate_integration_context import \
        generate_context_from_outputs

    EXAMPLE_INT_OUTPUTS = '''{'Guardicore': {'Endpoint': {'asset_id': '1-2-3-4-5',
'ip_addresses': ['1.1.1.1',
              'ffe::fef:fefe:fefee:fefe'],
'last_seen': 1629200550561,
'name': 'Accounting-web-1',
'status': 'on',
'tenant_name': 'esx10/lab_a/Apps/Accounting'}}}'''

    assert generate_context_from_outputs('!some-test-command=172.16.1.111',
                                         EXAMPLE_INT_OUTPUTS) == \
           {
               'arguments': [],
               'name': 'some-test-command=172.16.1.111',
               'outputs': [{'contextPath': 'Guardicore.Endpoint.asset_id',
                            'description': '',
                            'type': 'String'},
                           {'contextPath': 'Guardicore.Endpoint.ip_addresses',
                            'description': '',
                            'type': 'String'},
                           {'contextPath': 'Guardicore.Endpoint.last_seen',
                            'description': '',
                            'type': 'Date'},
                           {'contextPath': 'Guardicore.Endpoint.name',
                            'description': '',
                            'type': 'String'},
                           {'contextPath': 'Guardicore.Endpoint.status',
                            'description': '',
                            'type': 'String'},
                           {'contextPath': 'Guardicore.Endpoint.tenant_name',
                            'description': '',
                            'type': 'String'}]}


def test_generate_example_dict():
    """
    Given
       - An exmaples file path
    When
       - generating examples outputs
    Then
       - Ensure the outputs are correct
    """
    pass
