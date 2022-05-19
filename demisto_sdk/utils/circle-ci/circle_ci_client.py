import requests
import os
import logging
from json.decoder import JSONDecodeError
from requests.auth import HTTPBasicAuth
from types import SimpleNamespace


API_BASE_URL = "https://circleci.com/api"
PROJECT_SLUG = "github/demisto/demisto-sdk"


logger = logging.getLogger('circle-ci-demisto-sdk')


class CircleCIError(Exception):
    pass


class CircleCIResponse(SimpleNamespace):

    ATTRIBUTES_DEFAULT_MAPPING = {
        'items': [],
        'steps': [],
        'name': '',
        'allocation_id': '',
        'index': '',
        'actions': [],
        'status': '',
        'exit_code': None,
        'job_number': '',
        'classname': '',
        'pipeline_number': '',
        'step': '',
    }

    def __getattr__(self, attr):
        """
        in case a class attribute was not found, will trigger default values to be returned by attribute type.
        """
        logging.debug(f'could not find attribute {attr}, hence returning default value')
        return self.ATTRIBUTES_DEFAULT_MAPPING.get(attr)


def parse_http_response(expected_valid_code=200, response_type=None):
    # response type will override the response of the class.
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            _response_type = response_type if response_type else self.response_type
            logger.debug(f'Sending HTTP request using function {func.__name__} with args: {args}, kwargs: {kwargs}')
            http_response = func(self, *args, **kwargs)
            if http_response.status_code != expected_valid_code:
                try:
                    response_as_json = http_response.json()
                except JSONDecodeError:
                    raise CircleCIError(f'Error: ({http_response.content})')
                raise CircleCIError(f'Error: ({response_as_json})')
            if _response_type == 'class':
                return http_response.json(object_hook=lambda response: CircleCIResponse(**response))
            elif _response_type == 'json':
                return http_response.json()
            else:  # in case the entire response object is needed
                return http_response
        return wrapper
    return decorator


class CircleCIClient:

    RESPONSE_TYPES = {'class', 'response', 'json'}
    API_VERSION_V2 = "v2"
    API_VERSION_V1 = "v1.1"

    def __init__(self, token=None, base_url=None, verify=True, response_type='class'):
        if response_type not in self.RESPONSE_TYPES:
            raise ValueError(
                f'Invalid response type as {response_type} - should be one of {"/".join(self.RESPONSE_TYPES)}'
            )
        self.auth = HTTPBasicAuth(username=token or os.getenv("CIRCLE_TOKEN"), password='')
        self.base_url = base_url or API_BASE_URL
        self.verify = verify
        self.response_type = response_type

    def get_resource(self, url, params=None, api_version=API_VERSION_V2, stream=None):
        logger.debug(f'Sending HTTP request to {self.base_url}/{api_version}/{url} with params: {params}')
        return requests.get(
            url=f'{self.base_url}/{api_version}/{url}', verify=self.verify, auth=self.auth, params=params, stream=stream
        )

    @parse_http_response()
    def get_workflow_jobs(self, workflow_id: str):
        return self.get_resource(url=f'workflow/{workflow_id}/job')

    @parse_http_response()
    def get_workflow_details(self, workflow_id: str):
        return self.get_resource(url=f'workflow/{workflow_id}')

    @parse_http_response()
    def get_job_test_metadata(self, job_number: int):
        return self.get_resource(url=f'project/{PROJECT_SLUG}/{job_number}/tests')

    @parse_http_response()
    def get_job_details_v1(self, job_number: int):
        return self.get_resource(url=f'project/{PROJECT_SLUG}/{job_number}', api_version=self.API_VERSION_V1)

    @parse_http_response()
    def get_job_artifacts_v1(self, job_number: int):
        return self.get_resource(
            url=f'project/{PROJECT_SLUG}/{job_number}/artifacts',
            api_version=self.API_VERSION_V1
        )

    @parse_http_response(response_type='response')
    def get_job_output_file_by_step(self, job_number: int, step_number: int, index: int, allocation_id: str):
        return self.get_resource(
            url=f'project/{PROJECT_SLUG}/{job_number}/output/{step_number}/{index}',
            api_version=self.API_VERSION_V1,
            params={'file': 'true', 'allocation-id': allocation_id},
            stream=True
        )