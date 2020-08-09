base_argument = "$SARGNAME$ = $ARGTYPE$args.get('$DARGNAME$'"
base_params = """params = assign_params($PARAMS$)"""
base_data = """data = assign_params($DATAOBJ$)"""
base_props = """assign_params($PROPS$)"""
base_headers = """headers=headers"""
base_header = """headers[$HEADERKEY$] = $HEADERVALUE$"""
base_list_functions = "		'$FUNCTIONNAME$': $FUNCTIONCOMMAND$,"
base_credentials = """
    username = params['credentials']['identifier']
    password = params['credentials']['password']
"""
base_basic_auth = """(username, password)"""
base_token = """headers['Authorization'] = f'{params["api_key"]}'"""
base_function = """def $FUNCTIONNAME$_command(client, args):
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
base_request_function = """
    def $FUNCTIONNAME$_request(self$REQARGS$):
        $PARAMETERS$
        $DATA$

        headers = self._headers
        $HEADERSOBJ$

        response = self._http_request('$METHOD$', $PATH$$NEWPARAMS$$NEWDATA$, headers=headers)

        return response

"""
base_client = """class Client(BaseClient):
    def __init__(self, server_url, verify, proxy, headers, auth):
        super().__init__(base_url=server_url, verify=verify, proxy=proxy, headers=headers, auth=auth)

$REQUESTFUNCS$
"""
base_code = """import demistomock as demisto
from CommonServerPython import *


$CLIENT$

$FUNCTIONS$
def test_module(client):
    # Test functions here
    demisto.results('ok')


def main():

    params = demisto.params()
    args = demisto.args()
    url = params.get('url')
    verify_certificate = not params.get('insecure', False)
    proxy = params.get('proxy', False)
    $BASEAUTHPARAMS$
    headers = {}
    $BEARERAUTHPARAMS$

    command = demisto.command()
    LOG(f'Command being called is {command}')

    try:
        requests.packages.urllib3.disable_warnings()
        client = Client(urljoin(url, "$BASEURL$"), verify_certificate, proxy, headers=headers, auth=$BASEAUTH$)
        commands = {
    $COMMANDSLIST$
        }

        if command == 'test-module':
            test_module(client)
        else:
            return_results(commands[command](client, args))

    except Exception as e:
        return_error(str(e))


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()
"""
