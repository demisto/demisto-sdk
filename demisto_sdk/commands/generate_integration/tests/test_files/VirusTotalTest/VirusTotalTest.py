import demistomock as demisto
from CommonServerPython import *


class Client(BaseClient):
    def __init__(self, server_url, verify, proxy, headers, auth):
        super().__init__(base_url=server_url, verify=verify, proxy=proxy, headers=headers, auth=auth)

    def url_report_request(self, resource):
        params = assign_params(resource=resource, apikey=self.api_key)
        headers = self._headers

        response = self._http_request('GET', 'vtapi/v2/url/report', params=params, headers=headers)

        return response

    def domain_report_request(self, domain):
        params = assign_params(domain=domain, apikey=self.api_key)
        headers = self._headers
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'

        response = self._http_request('GET', 'vtapi/v2/domain/report', params=params, headers=headers)

        return response

    def file_scan_request(self):
        params = assign_params(apikey=self.api_key)
        headers = self._headers

        response = self._http_request('POST', 'vtapi/v2/file/scan', params=params, headers=headers)

        return response

    def file_download_request(self, hash):
        params = assign_params(hash=hash, apikey=self.api_key)
        headers = self._headers

        response = self._http_request('GET', 'vtapi/v2/file/download', params=params, headers=headers)

        return response


def url_report_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    resource = args.get('resource')

    response = client.url_report_request(resource)
    command_results = CommandResults(
        outputs_prefix='VirusTotalTest.UrlReport',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def domain_report_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    domain = args.get('domain')

    response = client.domain_report_request(domain)
    command_results = CommandResults(
        outputs_prefix='VirusTotalTest.DomainReport',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def file_scan_command(client: Client, args: Dict[str, Any]) -> CommandResults:

    response = client.file_scan_request()
    command_results = CommandResults(
        outputs_prefix='VirusTotalTest.FileScan',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def file_download_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    hash = args.get('hash')

    response = client.file_download_request(hash)
    command_results = CommandResults(
        outputs_prefix='VirusTotalTest.FileDownload',
        outputs_key_field='',
        outputs=response,
        raw_response=response
    )

    return command_results


def test_module(client: Client) -> None:
    # Test functions here
    return_results('ok')


def main():

    params: Dict[str, Any] = demisto.params()
    args: Dict[str, Any] = demisto.args()
    url = params.get('url')
    verify_certificate: bool = not params.get('insecure', False)
    proxy = params.get('proxy', False)

    headers = {}

    command = demisto.command()
    demisto.debug(f'Command being called is {command}')

    try:
        requests.packages.urllib3.disable_warnings()
        client: Client = Client(urljoin(url, ''), verify_certificate, proxy, headers=headers, auth=None)
        client.api_key = params['api_key']
        commands = {
            'vt-test-url-report': url_report_command,
            'vt-test-domain-report': domain_report_command,
            'vt-test-file-scan': file_scan_command,
            'vt-test-file-download': file_download_command,
        }

        if command == 'test-module':
            test_module(client)
        elif command in commands:
            return_results(commands[command](client, args))
        else:
            raise NotImplementedError(f'{command} command is not implemented.')

    except Exception as e:
        return_error(str(e))


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()
