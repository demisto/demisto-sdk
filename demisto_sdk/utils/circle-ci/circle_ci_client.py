import logging
import os
from json.decoder import JSONDecodeError
from types import SimpleNamespace
from typing import Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

API_BASE_URL = "https://circleci.com/api"
PROJECT_SLUG = "github/demisto/demisto-sdk"


logger = logging.getLogger("demisto-sdk")


class CircleCIError(Exception):
    pass


class CircleCIResponse(SimpleNamespace):

    ATTRIBUTES_DEFAULT_MAPPING = {
        "items": [],
        "steps": [],
        "name": "",
        "allocation_id": "",
        "index": "",
        "actions": [],
        "status": "",
        "exit_code": None,
        "job_number": "",
        "classname": "",
        "pipeline_number": "",
        "step": "",
    }

    def __getattr__(self, attr):
        """
        in case a class attribute was not found, will trigger default values to be returned by attribute type.
        """
        logging.debug(f"could not find attribute {attr}, hence returning default value")
        return self.ATTRIBUTES_DEFAULT_MAPPING.get(attr)


def parse_http_response(expected_valid_code: int = 200, response_type: str = "class"):
    """
    Parses the http response.

    Args:
        expected_valid_code (int): the expected http status code of success.
        response_type (str): what kind of response type to parse to, either json/response/class.

    Raises:
        ValueError: in case the response type is not valid.
    """

    # class - return a class where the attributes are the json response (including nested fields).
    # response - return the complete response object.
    # json - return a dict/list containing the response.

    response_types = {"class", "response", "json"}
    if response_type not in response_types:
        raise ValueError(
            f'Invalid response type ({response_type}) - should be one of ({",".join(response_types)})'
        )

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # response type will override the response of the class.
            logger.debug(
                f"Sending HTTP request using function {func.__name__} with args: {args}, kwargs: {kwargs}"
            )
            http_response = func(self, *args, **kwargs)
            if http_response.status_code != expected_valid_code:
                try:
                    response_as_json = http_response.json()
                except JSONDecodeError:
                    raise CircleCIError(f"Error: ({http_response.text})")
                raise CircleCIError(f"Error: ({response_as_json})")
            if response_type == "class":
                return http_response.json(
                    object_hook=lambda response: CircleCIResponse(**response)
                )
            elif response_type == "json":
                return http_response.json()
            else:  # in case the entire response object is needed
                return http_response

        return wrapper

    return decorator


class CircleCIClient:

    API_VERSION_V2 = "v2"
    API_VERSION_V1 = "v1.1"

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        verify: bool = True,
    ):
        self.auth = HTTPBasicAuth(username=token or os.getenv("CCI_TOKEN"), password="")
        self.base_url = base_url or API_BASE_URL
        self.verify = verify

    def get_resource(
        self,
        url: str,
        params: Optional[Dict] = None,
        api_version: str = API_VERSION_V2,
        stream: bool = None,
    ):
        logger.debug(
            f"Sending HTTP request to {self.base_url}/{api_version}/{url} with params: {params}"
        )
        return requests.get(
            url=f"{self.base_url}/{api_version}/{url}",
            verify=self.verify,
            auth=self.auth,
            params=params,
            stream=stream,
        )

    @parse_http_response()
    def get_workflow_jobs(self, workflow_id: str):
        return self.get_resource(url=f"workflow/{workflow_id}/job")

    @parse_http_response()
    def get_workflow_details(self, workflow_id: str):
        return self.get_resource(url=f"workflow/{workflow_id}")

    @parse_http_response()
    def get_job_test_metadata(self, job_number: int):
        return self.get_resource(url=f"project/{PROJECT_SLUG}/{job_number}/tests")

    @parse_http_response()
    def get_job_details_v1(self, job_number: int):
        return self.get_resource(
            url=f"project/{PROJECT_SLUG}/{job_number}", api_version=self.API_VERSION_V1
        )

    @parse_http_response()
    def get_job_artifacts_v1(self, job_number: int):
        return self.get_resource(
            url=f"project/{PROJECT_SLUG}/{job_number}/artifacts",
            api_version=self.API_VERSION_V1,
        )

    @parse_http_response(response_type="response")
    def get_job_output_file_by_step(
        self, job_number: int, step_number: int, index: int, allocation_id: str
    ):
        return self.get_resource(
            url=f"project/{PROJECT_SLUG}/{job_number}/output/{step_number}/{index}",
            api_version=self.API_VERSION_V1,
            params={"file": "true", "allocation-id": allocation_id},
            stream=True,
        )
