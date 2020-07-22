base_argument = "$SARGNAME$ = $ARGTYPE$(args.get('$DARGNAME$'"
base_params = """params={$PARAMS$}"""
base_data = """data={$DATAOBJ$}"""
base_headers = """headers=headers"""
base_header = """headers[$HEADERKEY$] = $HEADERVALUE$"""
base_list_functions = "		'$FUNCTIONNAME$': $FUNCTIONCOMMAND$,"
base_credentials = """
    username = params['credentials']['identifier']
    password = params['credentials']['password']
"""
base_basic_auth = """(username, password)"""
base_token = """headers['Authorization'] = [f'Bearer {params["api_key"]}']"""
base_function = """def $FUNCTIONNAME$_command(client, args):
    $ARGUMENTS$
    
    response = client.$FUNCTIONNAME$_request($REQARGS$)
    command_results = CommandResults(
        outputs_prefix='$CONTEXTNAME$$CONTEXTPATH$',
        outputs_key_field='$UNIQUEKEY$',
        outputs=response
    )
    
    return_results(command_results)

"""
base_request_function = """
    def $FUNCTIONNAME$_request(self$REQARGS$):
        $PARAMETERS$
        $DATA$
        
        headers = self.headers
        $HEADERSOBJ$
        
        response = {}
        try:
            response = self._http_request('$METHOD$', $PATH$$NEWPARAMS$$NEWDATA$, headers=headers)
            response.raise_for_status()
        except Exception as e:
            return_error(f'Error in API call: {e}')
        
        return response
    
"""
base_client = """class Client(BaseClient):
    def __init__(self, server_url, verify, proxy, headers, auth):
        super().__init__(base_url=server_url, verify=verify, proxy=proxy, headers=headers, auth=auth)
        
        $REQUESTFUNCS$
"""
base_code = """''' IMPORTS '''
import demistomock as demisto
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
    headers['Accept'] = 'application/json'
    headers['Content-Type'] = 'application/json'
    
    try:
        client = Client(urljoin(url, "$BASEURL$"), verify_certificate, proxy, headers=headers, auth=$BASEAUTH$)
        commands = {
    $COMMANDSLIST$
        }

        if command == 'test-module':
            test_module(client)
        else:
            commands[command](client, args)

    except Exception as e:
        return_error(str(e))


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()"""
