from abc import ABC, abstractmethod
import gzip
import json
import logging
import os
from pprint import pformat
from urllib.parse import urljoin
from pathlib import Path
from pydantic import BaseModel, Field, SecretStr, validator, HttpUrl
from pydantic.fields import ModelField
from typing import Any, Dict, List
import requests


class XsiamApiClientConfig(BaseModel):
    xsiam_url: HttpUrl = Field(default=os.getenv('DEMISTO_BASE_URL'), description="XSIAM URL")
    api_key: SecretStr = Field(default=SecretStr(os.getenv('DEMISTO_API_KEY', '')), description="XSIAM API Key")
    auth_id: str = Field(default=os.getenv('XSIAM_AUTH_ID'), description="XSIAM Auth ID")
    xsiam_token: SecretStr = Field(default=SecretStr(os.getenv('XSIAM_TOKEN', '')), description="XSIAM Token")

    @validator('*', always=True)
    def validate_client_config(cls, v, field: ModelField):
        if not v:
            raise ValueError(
                f"XSIAM client configuration is not complete: value was not passed for {field.name} and"
                f" the associated environment variable for {field.name} is not set"
            )
        return v


class XsiamApiInterface(ABC):
    @abstractmethod
    def uninstall_packs(self, pack_ids: List[str]):
        pass

    @abstractmethod
    def upload_packs(self, zip_path: Path):
        pass

    @abstractmethod
    def install_packs(self, packs: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def copy_packs(self, *args, **kwargs):
        pass

    @abstractmethod
    def add_create_dataset(self, *args, **kwargs):
        pass

    @abstractmethod
    def start_xql_query(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_xql_query_result(self, *args, **kwargs):
        pass


class XsiamApiClient(XsiamApiInterface):
    def __init__(self, config: XsiamApiClientConfig):
        self.base_url = config.xsiam_url
        self.api_key = config.api_key.get_secret_value() if isinstance(config.api_key, SecretStr) else config.api_key
        self.auth_id = config.auth_id
        self.xsiam_token = config.xsiam_token.get_secret_value() if isinstance(
            config.xsiam_token, SecretStr) else config.xsiam_token
        self.__session: requests.Session = None  # type: ignore

    @property
    def session(self) -> requests.Session:
        if not self.__session:
            self.session = requests.Session()
            self.session.headers.update({
                'x-xdr-auth-id': self.auth_id,
                'Authorization': self.api_key,
                'Content-Type': 'application/json',
            })
        return self.__session

    @session.setter
    def session(self, value: requests.Session):
        self.__session = value

    @property
    def installed_packs(self) -> List[Dict[str, Any]]:
        endpoint = urljoin(self.base_url, 'xsoar/contentpacks/metadata/installed')
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response.json()

    def search_pack(self, pack_id):
        endpoint = urljoin(self.base_url, f'xsoar/contentpacks/marketplace/{pack_id}')
        response = self.session.get(endpoint)
        response.raise_for_status()
        logging.debug(f'Found pack "{pack_id}" in bucket!')
        data = response.json()
        pack_data = {
            'id': data.get('id'),
            'version': data.get('currentVersion')
        }
        return pack_data

    def uninstall_packs(self, pack_ids: List[str]):
        endpoint = urljoin(self.base_url, 'xsoar/contentpacks/installed/delete')
        body = {"IDs": pack_ids}
        response = self.session.post(endpoint, json=body)
        response.raise_for_status()

    def upload_packs(self, zip_path: Path):
        endpoint = urljoin(self.base_url, 'xsoar/contentpacks/installed/upload')
        header_params = {
            'Content-Type': 'multipart/form-data'
        }
        file_path = os.path.abspath(zip_path)
        files = {'file': file_path}
        response = self.session.post(endpoint, files=files, headers=header_params)
        response.raise_for_status()
        logging.info(f'All packs from file {zip_path} were successfully installed on server {self.base_url}')

    def install_packs(self, packs: List[Dict[str, Any]]):
        endpoint = urljoin(self.base_url, 'xsoar/contentpacks/marketplace/install')
        response = self.session.post(url=endpoint, json={'packs': packs, 'ignoreWarnings': True})
        response.raise_for_status()
        if response.status_code in range(200, 300) and response.status_code != 204:
            response_data = response.json()
            packs_data = [
                {
                    'ID': pack.get('id'),
                    'CurrentVersion': pack.get('currentVersion')
                } for pack in response_data
            ]
            logging.success(f'Packs were successfully installed on server {self.base_url}')
            logging.debug(f'The packs that were successfully installed on server {self.base_url}:\n{packs_data}')
        elif response.status_code == 204:
            logging.success(f'Packs were successfully installed on server {self.base_url}')

    def sync_marketplace(self):
        endpoint = urljoin(self.base_url, 'xsoar/contentpacks/marketplace/sync')
        response = self.session.post(endpoint)
        response.raise_for_status()
        logging.info(f'Marketplace was successfully synced on server {self.base_url}')

    def copy_packs(self, *args, **kwargs):
        pass

    def add_create_dataset(self, data: List[Dict[str, Any]], product: str, vendor: str, data_format: str = 'json'):
        endpoint = urljoin(self.base_url, 'logs/v1/xsiam')
        additional_headers = {
            'authorization': self.xsiam_token,
            'format': data_format,
            'product': 'anar',
            'vendor': 'avidan',
            'content-encoding': 'gzip'
        }
        formatted_data = '\n'.join([json.dumps(d) for d in data])
        compressed_data = gzip.compress(formatted_data.encode('utf-8'))
        response = self.session.post(endpoint, data=compressed_data, headers=additional_headers)
        response.raise_for_status()
        try:
            res = response.json()
            error = response.reason
            if res.get('error').lower() == 'false':
                xsiam_server_err_msg = res.get('error')
                error += ": " + xsiam_server_err_msg

        except ValueError:
            error = '\n{}'.format(response.text)
        return response.json()

    def start_xql_query(self, query: str):
        body = {
            "request_data": {
                "query": query
            }
        }
        endpoint = urljoin(self.base_url, 'public_api/v1/xql/start_xql_query/')
        logging.info(f'Starting xql query:\nendpoint={endpoint}\n{query=}')
        response = self.session.post(endpoint, json=body)
        data = response.json()

        if 200 <= response.status_code < 300:
            execution_id: str = data.get('reply', '')
            return execution_id
        else:
            logging.error(
                f'Failed to start xql query "{query}" - with status code {response.status_code}\n{pformat(data)}'
            )
            response.raise_for_status()

    def get_xql_query_result(self, execution_id: str):
        payload = json.dumps({
            "request_data": {
                "query_id": execution_id,
                "pending_flag": False,
                "limit": 1000,
                "format": "json"
            }
        })
        endpoint = urljoin(self.base_url, 'public_api/v1/xql/get_query_results/')
        logging.info(f'Getting xql query results: endpoint={endpoint}')
        response = self.session.post(endpoint, data=payload)
        data = response.json()
        logging.debug(pformat(data))

        if 200 <= response.status_code < 300 and data.get('reply', {}).get('status', '') == 'SUCCESS':
            reply_results_data = data.get('reply', {}).get('results', {}).get('data', [])
            return reply_results_data
        else:
            err_msg = (f'Failed to get xql query results for execution_id "{execution_id}"'
                       f' - with status code {response.status_code}\n{pformat(data)}')
            logging.error(err_msg)
            response.raise_for_status()
