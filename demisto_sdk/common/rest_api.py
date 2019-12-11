import os
import json
from urllib.parse import urljoin

import requests

from demisto_sdk.common.tools import print_v


DEMISTO_API_KEY_ENV = 'DEMISTO_API_KEY'
INTEGRATION_UPLOAD_PATH = "/settings/integration-conf/upload"
ENTRY_EXECUTE_PATH = "/entry/execute/sync"
ENTRY_DOWNLOAD_PATH = "/entry/download/"
INVESTIGATION_SEARCH_PATH = "/investigations/search"


class Client:
    """Demisto REST API Client
    
    Args:
        base_url (str): URL of Demisto instance
        verify_cert (bool, optional): Verify remote certificate. Defaults to True.
        verbose (bool, optional): Verbose logging.
    """
    def __init__(self, base_url: str, verify_cert: bool = True, verbose: bool = False):
        self.base_url = base_url
        self.verify_cert = verify_cert
        self.log_verbose = verbose

    def get_api_key(self):
        """Retrieve the API Key
        
        Raises:
            RuntimeError: if the API Key environment variable is not found
        
        Returns:
            str: API Key
        """
        ans = os.environ.get(DEMISTO_API_KEY_ENV, None)
        if ans is None:
            raise RuntimeError(f'Error: Environment variable {DEMISTO_API_KEY_ENV} not found')

        return ans

    def upload_integration(self, ymlf):
        """Upload an integration YML file to a remote Demisto instance.

        Args:
            ymlf (stream): The open file object to be uploaded
        """
        api_key = self.get_api_key()

        api_url = urljoin(self.base_url, INTEGRATION_UPLOAD_PATH)
        files = {'file': ymlf}

        print_v(f'Uploading integration to {api_url}', self.log_verbose)

        result = requests.post(
            url=api_url,
            verify=self.verify_cert,
            files=files,
            headers={
                'Accept': 'application/json',
                'Authorization': api_key
            }
        )

        result.raise_for_status()

        if self.log_verbose:
            full_result = result.json()
            print_v(
                f'Result: {json.dumps(full_result, indent=4)}',
                self.log_verbose
            )

        result.close()

    def search_investigations(self, sfilter):
        """Search investigations.
        
        Args:
            sfilter (dict): Filter for the search

        Returns:
            dict: API Response
        """
        api_key = self.get_api_key()

        api_url = urljoin(self.base_url, INVESTIGATION_SEARCH_PATH)

        print_v(
            f'Searching investigations on {api_url} with filter {json.dumps(sfilter, indent=4)}',
            self.log_verbose
        )

        result = requests.post(
            url=api_url,
            verify=self.verify_cert,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': api_key
            },
            json=sfilter
        )

        result.raise_for_status()

        ans = result.json()

        print_v(f'Result: {json.dumps(ans, indent=4)}', self.log_verbose)

        return ans

    def run_query(self, investigation_id: str, query: str):
        """[summary]
        
        Args:
            investigation_id (str): [description]
            query (str): [description]

        Returns:
            dict: query result
        """
        api_key = self.get_api_key()

        api_url = urljoin(self.base_url, ENTRY_EXECUTE_PATH)

        print_v(
            f'Executing query {query} on investigation with the ID: '{investigation_id}' via {api_url}',
            self.log_verbose
        )

        result = requests.post(
            url=api_url,
            verify=self.verify_cert,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': api_key
            },
            json={
                'investigationId': investigation_id,
                'version': 0,
                'id': '',
                'args': {},
                'data': query
            }
        )

        result.raise_for_status()

        ans = result.json()

        print_v(f'Result: {json.dumps(ans, indent=4)}', self.log_verbose)

        return ans

    def download_file(self, file_id: str):
        """Download file artifact from remote Demisto instance in
        stream mode.
        
        Args:
            file_id (str): artifact id of the file

        Returns:
            requests.Response: API server response
        """
        api_key = self.get_api_key()

        api_url = urljoin(self.base_url, ENTRY_DOWNLOAD_PATH)
        download_path = urljoin(api_url, file_id)

        print_v(f'Downloading {file_id} via {api_url}', self.log_verbose)

        result = requests.get(
            url=download_path,
            verify=self.verify_cert,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': api_key
            },
            stream=True
        )

        result.raise_for_status()

        print_v(f'Server returned OK', self.log_verbose)

        return result
