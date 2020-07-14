base_argument = "$SARGNAME$ = $ARGTYPE$(args.get('$DARGNAME$'"
base_params = """params={$PARAMS$}"""
base_data = """data={$DATAOBJ$}"""
base_list_functions = "		'$FUNCTIONNAME$': $FUNCTIONCOMMAND$,"
base_function = """def $FUNCTIONNAME$_command(client, args):
    $ARGUMENTS$
    $PARAMETERS$
    $DATA$

    response = client.http_request('$METHOD$', $PATH$$NEWPARAMS$$NEWDATA$)

    if isinstance(response, dict):
        command_results = CommandResults(
            outputs_prefix='$CONTEXTNAME$',
            outputs_key_field='$CONTEXTCONTEXT$',
            outputs=response
        )
        return_results(command_results)
    else:
        return_error(f'Error in API call {response.status_code} - {response.text}')

"""
base_code = """''' IMPORTS '''
import json

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
    # TODO: add headers
    headers = {}
    try:
        client = Client(urljoin(url, "$BASEURL$"), verify_certificate, proxy)
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
