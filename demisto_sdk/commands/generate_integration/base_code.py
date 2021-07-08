BASE_ARGUMENT = "$SARGNAME$ = $ARGTYPE$args.get('$DARGNAME$'"
BASE_PARAMS = """params = assign_params($PARAMS$)"""
BASE_DATA = """data = assign_params($DATAOBJ$)"""
BASE_PROPS = """assign_params($PROPS$)"""
BASE_HEADERS = """headers=headers"""
BASE_HEADER = """headers[$HEADERKEY$] = $HEADERVALUE$"""
BASE_LIST_FUNCTIONS = "		'$FUNCTIONNAME$': $FUNCTIONCOMMAND$,"
BASE_CREDENTIALS = """
    username = params['credentials']['identifier']
    password = params['credentials']['password']
"""
BASE_BASIC_AUTH = """(username, password)"""
BASE_TOKEN = """headers['Authorization'] = params['api_key']"""
BASE_HEADER_API_KEY = """headers['$HEADER_API_KEY$'] = params['api_key']"""
BASE_HEADER_FORMATTED = """headers['$HEADER_NAME$'] = $HEADER_FORMAT$"""
BASE_CLIENT_API_KEY = """client.api_key = params['api_key']"""
BASE_BEARER_TOKEN = """headers['Authorization'] = f'Bearer {params["token"]}'"""
BASE_FUNCTION = """def $FUNCTIONNAME$_command(client: Client, args: Dict[str, Any]) -> CommandResults:
    $ARGUMENTS$

    response = client.$FUNCTIONNAME$_request($REQARGS$)
    command_results = CommandResults(
        outputs_prefix='$CONTEXTNAME$$CONTEXTPATH$',
        outputs_key_field='$UNIQUEKEY$',
        outputs=$OUTPUTS$,
        raw_response=response
    )

    return command_results

"""
BASE_REQUEST_FUNCTION = """
    def $FUNCTIONNAME$_request(self$REQARGS$):
        $PARAMETERS$
        $DATA$

        headers = self._headers
        $HEADERSOBJ$

        response = self._http_request('$METHOD$', $PATH$$NEWPARAMS$$NEWDATA$, headers=headers)

        return response

"""
BASE_CLIENT = """class Client(BaseClient):
    def __init__(self, server_url, verify, proxy, headers, auth):
        super().__init__(base_url=server_url, verify=verify, proxy=proxy, headers=headers, auth=auth)

$REQUESTFUNCS$
"""

CLIENT_API_KEY = """client.api_key = params['api_key']"""

BASE_CODE_TEMPLATE = """import demistomock as demisto
from CommonServerPython import *


$CLIENT$

$FUNCTIONS$
def test_module(client: Client) -> None:
    # Test functions here
    return_results('ok')


def main():

    params: Dict[str, Any] = demisto.params()
    args: Dict[str, Any] = demisto.args()
    url = params.get('url')
    verify_certificate: bool = not params.get('insecure', False)
    proxy: bool = params.get('proxy', False)
    $BASEAUTHPARAMS$
    headers = {}
    $BEARERAUTHPARAMS$

    command = demisto.command()
    demisto.debug(f'Command being called is {command}')

    try:
        requests.packages.urllib3.disable_warnings()
        client: Client = Client(urljoin(url, '$BASEURL$'), verify_certificate, proxy, headers=headers, auth=$BASEAUTH$)
        $CLIENT_API_KEY$
        commands = {
    $COMMANDSLIST$
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
"""
