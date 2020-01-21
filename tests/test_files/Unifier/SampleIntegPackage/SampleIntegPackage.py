import demistomock as demisto
from CommonServerPython import *  # noqa: E402

# CONSTANTS
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class Client:
    """
    Client will implement the service API, and should not contain any Demisto logic.
    Should only do requests and return data.
    """

    @staticmethod
    def say_hello(name):
        return f'Hello {name}'

    def say_hello_http_request(self, name):
        """
        initiates a http request to a test url
        """
        data = self.say_hello(
            name=name
        )
        return data


def test_module(client):
    """
    Returning 'ok' indicates that the integration works like it is supposed to. Connection to the service is successful.

    Args:
        client: HelloWorld client

    Returns:
        'ok' if test passed, anything else will fail the test.
    """

    result = client.say_hello('DBot')
    if 'Hello DBot' == result:
        return 'ok'
    else:
        return 'Test failed because ......'


def say_hello_command(client, args):
    """
    Returns Hello {somename}

    Args:
        client (Client): HelloWorld client.
        args (dict): all command arguments.

    Returns:
        Hello {someone}

        readable_output (str): This will be presented in the war room - should be in markdown syntax - human readable
        outputs (dict): Dictionary/JSON - saved in the incident context in order to be used as inputs
                        for other tasks in the playbook
        raw_response (dict): Used for debugging/troubleshooting purposes -
                            will be shown only if the command executed with raw-response=true
    """
    name = args.get('name')

    result = client.say_hello(name)

    # readable output will be in markdown format - https://www.markdownguide.org/basic-syntax/
    readable_output = f'## {result}'
    outputs = {
        'hello': result
    }

    return (
        readable_output,
        outputs,
        result  # raw response - the original response
    )


def say_hello_over_http_command(client, args):
    name = args.get('name')

    result = client.say_hello_http_request(name)

    # readable output will be in markdown format - https://www.markdownguide.org/basic-syntax/
    readable_output = f'## {result}'
    outputs = {
        'hello': result
    }

    return (
        readable_output,
        outputs,
        result  # raw response - the original response
    )


def main():
    """
        PARSE AND VALIDATE INTEGRATION PARAMS
    """

    try:
        client = Client()

        if demisto.command() == 'test-module':
            # This is the call made when pressing the integration Test button.
            result = test_module(client)
            demisto.results(result)

        elif demisto.command() == 'helloworld-say-hello':
            return say_hello_over_http_command(client, demisto.args())

    # Log exceptions
    except Exception as e:
        return f'Failed to execute {demisto.command()} command. Error: {str(e)}'


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
