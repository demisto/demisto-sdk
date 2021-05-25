from typing import Dict, Optional, Tuple, Callable, Any, Union

import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
import json
import requests
import dateparser
import time

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()


def main():
    """
        PARSE AND VALIDATE INTEGRATION PARAMS
    """
    params = demisto.params()
    username = params.get('credentials').get("identifier")
    password = params.get('credentials').get('password')
    base_url = params.get('url')
    proxy = demisto.params().get('proxy', False)
    verify_certificate = not params.get('insecure', False)

    # fetch incidents params
    fetch_limit = params.get('fetch_limit', 10)
    fetch_time = params.get('fetch_time', '1 day')
    fetch_shaping = params.get('fetch_shaping')
    fetch_filter = params.get('fetch_filter')
    fetch_queue_id = argToList(params.get('fetch_queue_id'))
    client = Client(
        url=base_url,
        username=username,
        password=password,
        verify=verify_certificate,
        proxy=proxy)
    command = demisto.command()
    LOG(f'Command being called is {command}')
    # Commands dict
    commands: Dict[str, Callable[[Client, Dict[str, str]], Tuple[str, dict, dict]]] = {
        'kace-machines-list': get_machines_list_command,
        'kace-assets-list': get_assets_list_command,
        'kace-queues-list': get_queues_list_command,
        'kace-tickets-list': get_tickets_list_command,
        'kace-ticket-create': create_ticket_command,
        'kace-ticket-update': update_ticket_command,
        'kace-ticket-delete': delete_ticket_command,
    }
    if command in commands:
        return_outputs(*commands[command](client, demisto.args()))
    elif command == 'fetch-incidents':
        incidents = fetch_incidents(client, fetch_time=fetch_time, fetch_shaping=fetch_shaping,
                                    fetch_filter=fetch_filter, fetch_limit=fetch_limit,
                                    fetch_queue_id=fetch_queue_id, last_run=demisto.getLastRun())
        demisto.incidents(incidents)
        demisto.results(incidents)
    else:
        raise NotImplementedError(f'{command} is not an existing QuestKace command')
