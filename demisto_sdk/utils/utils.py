import os
from configparser import ConfigParser, MissingSectionHeaderError
from pathlib import Path
from typing import Optional, Union

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
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from demisto_sdk.commands.common.logger import logger

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


def get_integration_params(secret_id: str, project_id: Optional[str] = None) -> dict:
    """This function retrieves the parameters of an integration from Google Secret Manager
    *Note*: This function will not run if the `DEMISTO_SDK_GCP_PROJECT_ID` env variable is not set.

    Args:
        project_id (str): GSM project id
        secret_id (str): The secret id in GSM

    Returns:
        dict: The integration params
    """
    if not project_id:
        project_id = os.getenv("DEMISTO_SDK_GCP_PROJECT_ID")
    if not project_id:
        raise ValueError(
            "Either provide the project id or set the `DEMISTO_SDK_GCP_PROJECT_ID` environment variable"
        )

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
            "Insufficient permissions for gcloud. run `gcloud auth application-default login`"
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
