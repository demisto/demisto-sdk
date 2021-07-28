import ast
import logging
from copy import deepcopy
from pprint import pformat
from subprocess import STDOUT, CalledProcessError, check_output

import demisto_client

from demisto_sdk.commands.test_content.constants import SSH_USER


def update_server_configuration(client, server_configuration,
                                error_msg, logging_manager=logging, config_keys_to_delete=None):
    """updates server configuration

    Args:
        client (demisto_client): The configured client to use.
        server_configuration (dict): The server configuration to be added
        error_msg (str): The error message
        logging_manager (logging.Logger): Logging manager object
        config_keys_to_delete (set): The server configuration keys to be deleted

    Returns:
        response_data: The response data
        status_code: The response status code
        prev_system_conf: Previous stored system conf
    """
    system_conf_response = demisto_client.generic_request_func(
        self=client,
        path='/system/config',
        method='GET'
    )
    system_conf = ast.literal_eval(system_conf_response[0]).get('sysConf', {})
    logging_manager.debug(f'Current server configurations are {pformat(system_conf)}')

    prev_system_conf = deepcopy(system_conf)

    if config_keys_to_delete:
        for key in config_keys_to_delete:
            system_conf.pop(key, None)

    if server_configuration:
        system_conf.update(server_configuration)

    data = {
        'data': system_conf,
        'version': -1
    }
    response_data, status_code, _ = demisto_client.generic_request_func(self=client, path='/system/config',
                                                                        method='POST', body=data)

    logging_manager.debug(f'Updating server configurations with {pformat(system_conf)}')

    try:
        result_object = ast.literal_eval(response_data)
        logging_manager.debug(f'Updated server configurations with response: {pformat(result_object)}')
    except ValueError as err:
        logging_manager.exception(f'failed to parse response from demisto. response is {response_data}.\nError:\n{err}')
        return

    if status_code >= 300 or status_code < 200:
        message = result_object.get('message', '')
        logging_manager.error(f'{error_msg} {status_code}\n{message}')
    return response_data, status_code, prev_system_conf


def is_redhat_instance(instance_ip: str) -> bool:
    """
    As part of the AMI creation - in case the AMI is RHEL a file named '/home/ec2-user/rhel_ami' is created as
    an indication.
    If not
    Args:
        instance_ip: The instance IP to check.

    Returns:
        True if the file '/home/ec2-user/rhel_ami' exists on the instance, else False
    """
    try:
        check_output(f'ssh {SSH_USER}@{instance_ip} ls -l /home/ec2-user/rhel_ami'.split(),
                     stderr=STDOUT)
        return True
    except CalledProcessError:
        return False
