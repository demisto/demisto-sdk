import time
from configparser import ConfigParser, MissingSectionHeaderError
from functools import wraps
from pathlib import Path
from typing import Callable, Tuple, Type, Union

import google
from google.cloud import secretmanager

from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import (
    YAMLContentObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import (
    YAMLContentUnifiedObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.handlers.json.json5_handler import JSON5_Handler
from demisto_sdk.commands.common.logger import logger

json5 = JSON5_Handler()
ContentEntity = Union[YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject]


class SecretManagerException(Exception):
    pass


def get_containing_pack(content_entity: ContentEntity) -> Pack:
    """Get pack object that contains the content entity.

    Args:
        content_entity: Content entity object.

    Returns:
        Pack: Pack object that contains the content entity.
    """
    pack_path = content_entity.path
    while pack_path.parent.name.casefold() != "packs":
        pack_path = pack_path.parent
    return Pack(pack_path)


def check_configuration_file(command, args):
    config_file_path = ".demisto-sdk-conf"
    true_synonyms = ["true", "True", "t", "1"]
    if Path(config_file_path).is_file():
        try:
            config = ConfigParser(allow_no_value=True)
            config.read(config_file_path)

            if command in config.sections():
                for key in config[command]:
                    if key in args:
                        # if the key exists in the args we will run it over if it is either:
                        # a - a flag currently not set and is defined in the conf file
                        # b - not a flag but an arg that is currently None and there is a value for it in the conf file
                        if args[key] is False and config[command][key] in true_synonyms:
                            args[key] = True

                        elif args[key] is None and config[command][key] is not None:
                            args[key] = config[command][key]

                    # if the key does not exist in the current args, add it
                    else:
                        if config[command][key] in true_synonyms:
                            args[key] = True

                        else:
                            args[key] = config[command][key]

        except MissingSectionHeaderError:
            pass


def retry(
    times: int = 3,
    delay: int = 1,
    exceptions: Union[Tuple[Type[Exception]], Type[Exception]] = Exception,
):
    """
    retries to execute a function until an exception isn't raised anymore.

    Args:
        times: the amount of times to try and execute the function
        delay: the number of seconds to wait between each time
        exceptions: the exceptions that should be caught when executing the function

    Returns:
        Any: the decorated function result
    """

    def _retry(func: Callable):

        func_name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, times + 1):
                logger.debug(f"trying to run func {func_name} for the {i} time")
                try:
                    return func(*args, **kwargs)
                except exceptions as error:
                    logger.debug(
                        f"error when executing func {func_name}, error: {error}, time {i}"
                    )
                    if i == times:
                        raise
                    time.sleep(delay)

        return wrapper

    return _retry


def get_integration_params(project_id: str, secret_id: str) -> dict:
    """This function retrieves the parameters of an integration from Google Secret Manager
    *Note*: This function will not run if the `DEMISTO_SDK_GCP_PROJECT_ID` env variable is not set.

    Args:
        project_id (str): GSM project id
        secret_id (str): The secret id in GSM

    Returns:
        dict: The integration params
    """
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    # Access the secret version.
    try:
        response = client.access_secret_version(name=name)
    except google.api_core.exceptions.NotFound:
        logger.warning("The secret is not found in the secret manager")
        raise SecretManagerException
    except google.api_core.exceptions.PermissionDenied:
        logger.warning(
            "Insufficient permissions for gcloud. , run `gcloud auth application-default login`"
        )
        raise SecretManagerException
    except Exception:
        logger.warning(f"Failed to get secret {secret_id} from Secret Manager.")
        raise SecretManagerException
    # Return the decoded payload.
    payload = json5.loads(response.payload.data.decode("UTF-8"))
    if "params" not in payload:
        logger.warning(f"Parameters are not found in {secret_id} from Secret Manager.")

        raise SecretManagerException
    return payload["params"]
