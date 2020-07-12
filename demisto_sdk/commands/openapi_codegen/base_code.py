base_argument = "$SARGNAME$ = $ARGTYPE$(args.get('$DARGNAME$'"
base_params = """params={$PARAMS$}"""
base_data = """data={$DATAOBJ$}"""
base_list_functions = "		'$FUNCTIONNAME$': $FUNCTIONCOMMAND$,"
# TODO: return_results()
base_function = """def $FUNCTIONNAME$_command(client, args):
    $ARGUMENTS$
    $PARAMETERS$
    $DATA$

    response = client.http_request('$METHOD$', $PATH$$NEWPARAMS$$NEWDATA$)

    if isinstance(response, dict):
        return_results('$CONTEXTNAME$', response, '$CONTEXTCONTEXT$')
    else:
        return_error(f'Error in API call {response.status_code} - {response.text}')

"""
base_code = """''' IMPORTS '''
import json


def return_results(table_name, in_data, context_path):
    raw = in_data
    data = in_data if isinstance(in_data,  list) else [in_data]
    md_data = list()
    for item in data:
        new_item = dict()
        for k, v in item.items():
            try:
                new_item[k] = json.dumps(v)
            except ValueError:
                new_item[k] = v
        md_data.append(new_item)
    md = tableToMarkdown(table_name, md_data)
    return_outputs(md, {context_path: data}, raw)

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
        demisto.results(e)
        return_error(str(e))


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()"""
