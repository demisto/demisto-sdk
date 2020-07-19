base_argument = "$SARGNAME$ = $ARGTYPE$(args.get('$DARGNAME$'"
base_params = """params={$PARAMS$}"""
base_data = """data={$DATAOBJ$}"""
base_headers = """headers={$HEADERSOBJ$}"""
base_list_functions = "		'$FUNCTIONNAME$': $FUNCTIONCOMMAND$,"
base_function = """def $FUNCTIONNAME$_command(client, args):
    $ARGUMENTS$
    $PARAMETERS$
    $DATA$

    response = client.http_request('$METHOD$', $PATH$$NEWPARAMS$$NEWDATA$$HEADERS$)

    if isinstance(response, dict):
        command_results = CommandResults(
            outputs_prefix='$CONTEXTNAME$$CONTEXTPATH$',
            outputs_key_field='$UNIQUEKEY$',
            outputs=response
        )
        return_results(command_results)
    else:
        return_error(f'Error in API call {response.status_code} - {response.text}')

"""
base_code = """''' IMPORTS '''
import json
import demistomock as demisto
from CommonServerPython import *

class Client(BaseClient):
    def http_request(self, *args, **kwargs):
        return self._http_request(*args, **kwargs)


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

    command = demisto.command()
    LOG(f'Command being called is {command}')
    headers={'Accept': 'application/json', 'Content-Type': 'application/json'}
    try:
        client = Client(urljoin(url, "$BASEURL$"), verify_certificate, proxy, headers=headers)
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
