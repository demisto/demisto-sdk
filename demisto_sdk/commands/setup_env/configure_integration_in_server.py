from __future__ import print_function

import ast
import time
import urllib.parse
from pprint import pformat

import demisto_client
import urllib3
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.logger import logger

# Disable insecure warnings

urllib3.disable_warnings()

# ----- Constants ----- #
DEFAULT_TIMEOUT = 60
DEFAULT_INTERVAL = 20
ENTRY_TYPE_ERROR = 4


# ----- Functions ----- #

# get integration configuration
def __get_integration_config(client, integration_name):
    body = {"page": 0, "size": 100, "query": "name:" + integration_name}
    try:
        res = demisto_client.generic_request_func(
            self=client,
            path="/settings/integration/search",
            method="POST",
            body=body,
            response_type="object",
        )
    except ApiException:
        logger.exception(f"failed to get integration {integration_name} configuration")
        return None

    TIMEOUT = 180
    SLEEP_INTERVAL = 5
    total_sleep = 0
    while "configurations" not in res:
        if total_sleep == TIMEOUT:
            logger.error(
                f"Timeout - failed to get integration {integration_name} configuration. Error: {res}"
            )
            return None

        time.sleep(SLEEP_INTERVAL)
        total_sleep += SLEEP_INTERVAL

    all_configurations = res["configurations"]
    match_configurations = [
        x for x in all_configurations if x["name"] == integration_name
    ]

    if not match_configurations or len(match_configurations) == 0:
        logger.error("integration was not found")
        return None

    return match_configurations[0]


def __test_integration_instance(client, module_instance):
    connection_retries = 5
    response_code = 0
    integration_of_instance = module_instance.get("brand", "")
    instance_name = module_instance.get("name", "")
    logger.info(
        f'Running "test-module" for instance "{instance_name}" of integration "{integration_of_instance}".'
    )
    for i in range(connection_retries):
        try:
            response_data, response_code, _ = demisto_client.generic_request_func(
                self=client,
                method="POST",
                path="/settings/integration/test",
                body=module_instance,
                _request_timeout=240,
            )
            break
        except ApiException:
            logger.exception(
                "Failed to test integration instance, error trying to communicate with demisto server"
            )
            return False, None
        except urllib3.exceptions.ReadTimeoutError:
            logger.warning(
                f"Could not connect to demisto server. Trying to connect for the {i + 1} time"
            )

    if int(response_code) != 200:
        logger.error(
            f'Integration-instance test ("Test" button) failed. Bad status code: {response_code}'
        )
        return False, None

    result_object = ast.literal_eval(response_data)
    success, failure_message = bool(result_object.get("success")), result_object.get(
        "message"
    )
    if not success:
        server_url = client.api_client.configuration.host
        test_failed_msg = f"Test integration failed - server: {server_url}."
        test_failed_msg += (
            f"\nFailure message: {failure_message}"
            if failure_message
            else " No failure message."
        )
        logger.error(test_failed_msg)
    return success, failure_message


# return True if delete-integration-instance succeeded, False otherwise
def __delete_integration_instance(client, instance_id):
    try:
        res = demisto_client.generic_request_func(
            self=client,
            method="DELETE",
            path=f"/settings/integration/{urllib.parse.quote(instance_id)}",
        )
    except ApiException:
        logger.exception(
            "Failed to delete integration instance, error trying to communicate with demisto."
        )
        return False
    if int(res[1]) != 200:
        logger.error(f"delete integration instance failed\nStatus code {res[1]}")
        logger.error(pformat(res))
        return False
    return True


def __delete_integration_instance_if_determined_by_name(client, instance_name):
    """Deletes integration instance by it's name.

    Args:
        client (demisto_client): The configured client to use.
        instance_name (str): The name of the instance to delete.

    Notes:
        This function is needed when the name of the instance is pre-defined in the tests configuration, and the test
        itself depends on the instance to be called as the `instance name`.
        In case we need to configure another instance with the same name, the client will throw an error, so we
        will call this function first, to delete the instance with this name.

    """
    try:
        int_instances = demisto_client.generic_request_func(
            self=client,
            method="POST",
            path="/settings/integration/search",
            body={"size": 1000},
            response_type="object",
        )
    except ApiException:
        logger.exception(
            "Failed to delete integrations instance, error trying to communicate with demisto server"
        )
        return
    if int(int_instances[1]) != 200:
        logger.error(
            f"Get integration instance failed with status code: {int_instances[1]}"
        )
        return
    if "instances" not in int_instances:
        logger.info("No integrations instances found to delete")
        return

    for instance in int_instances["instances"]:
        if instance.get("name") == instance_name:
            logger.info(
                f"Deleting integration instance {instance_name} since it is defined by name"
            )
            __delete_integration_instance(client, instance.get("id"))


def __disable_integrations_instances(client, module_instances):
    for configured_instance in module_instances:
        # tested with POSTMAN, this is the minimum required fields for the request.
        module_instance = {
            key: configured_instance[key]
            for key in [
                "id",
                "brand",
                "name",
                "data",
                "isIntegrationScript",
            ]
        }
        module_instance["enable"] = "false"
        module_instance["version"] = -1
        logger.debug(f'Disabling integration {module_instance.get("name")}')
        try:
            res = demisto_client.generic_request_func(
                self=client,
                method="PUT",
                path="/settings/integration",
                body=module_instance,
            )
        except ApiException:
            logger.exception("Failed to disable integration instance")
            return

        if res[1] != 200:
            logger.error(f"disable instance failed, Error: {pformat(res)}")


# return instance name if succeed, None otherwise


def create_integration_instance(
    integration_name,
    integration_instance_name,
    integration_params,
    is_byoi,
    validate_test=True,
):
    failure_message = ""
    # get configuration config (used for later rest api
    integration_conf_client = demisto_client.configure()
    configuration = __get_integration_config(integration_conf_client, integration_name)
    if not configuration:
        return None, "No configuration"

    module_configuration = configuration["configuration"]
    if not module_configuration:
        module_configuration = []

    __delete_integration_instance_if_determined_by_name(
        integration_conf_client, integration_instance_name
    )

    logger.info(
        f'Configuring instance for {integration_name} (instance name: {integration_instance_name}, validate "Test": {validate_test})'
    )
    # define module instance
    module_instance = {
        "brand": configuration["name"],
        "category": configuration["category"],
        "configuration": configuration,
        "data": [],
        "enabled": "true",
        "engine": "",
        "id": "",
        "isIntegrationScript": is_byoi,
        "name": integration_instance_name,
        "passwordProtected": False,
        "version": 0,
    }
    # set module params
    for param_conf in module_configuration:
        if (
            param_conf["display"] in integration_params
            or param_conf["name"] in integration_params
        ):
            # param defined in conf
            key = (
                param_conf["display"]
                if param_conf["display"] in integration_params
                else param_conf["name"]
            )
            if key == "credentials":
                credentials = integration_params[key]
                param_value = {
                    "credential": "",
                    "identifier": credentials["identifier"],
                    "password": credentials["password"],
                    "passwordChanged": False,
                }
            else:
                param_value = integration_params[key]

            param_conf["value"] = param_value
            param_conf["hasvalue"] = True
        elif param_conf["defaultValue"]:
            # param is required - take default value
            param_conf["value"] = param_conf["defaultValue"]
        module_instance["data"].append(param_conf)
    try:
        res = demisto_client.generic_request_func(
            self=integration_conf_client,
            method="PUT",
            path="/settings/integration",
            body=module_instance,
            response_type="object",
        )
    except ApiException:
        error_message = (
            f"Error trying to create instance for integration: {integration_name}"
        )
        logger.exception(error_message)
        return None, error_message

    if res[1] != 200:
        error_message = f"create instance failed with status code  {res[1]}"
        logger.error(error_message)
        logger.error(pformat(res[0]))
        return None, error_message

    integration_config = res[0]
    module_instance["id"] = integration_config["id"]

    # test integration
    refreshed_client = demisto_client.configure()
    if validate_test:
        test_succeed, failure_message = __test_integration_instance(
            refreshed_client, module_instance
        )
    else:
        logger.debug(
            f"Skipping test validation for integration: {integration_name} (it has test_validate set to false)"
        )
        test_succeed = True

    if not test_succeed:
        __disable_integrations_instances(refreshed_client, [module_instance])
        return None, failure_message

    return module_instance, ""
