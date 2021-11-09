import json
import logging
import re
from collections import defaultdict
from typing import Dict, List, Union

import demisto_sdk.commands.common.tools as tools
from demisto_sdk.commands.common.constants import DemistoException
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.generate_integration.code_generator import (
    IntegrationGeneratorArg, IntegrationGeneratorCommand,
    IntegrationGeneratorConfig, IntegrationGeneratorOutput,
    IntegrationGeneratorParam, ParameterType)
from demisto_sdk.commands.generate_outputs.json_to_outputs.json_to_outputs import (
    determine_type, flatten_json)

logger: logging.Logger = logging.getLogger('demisto-sdk')


def postman_headers_to_conf_headers(postman_headers, skip_authorization_header: bool = False):
    """
    postman_headers = [
        {
            "key": "Content-Type",
            "value": "application/json",
            "type": "text"
        },
        {
            "key": "Accept",
            "value": "application/json",
            "type": "text"
        }
    ]

    to =>
    [{'Content-Type': 'application/json'}, {'Accept': 'application/json'}]

    """
    if not postman_headers:
        return None

    headers = []
    for ph in postman_headers:
        if skip_authorization_header and ph['key'] == 'Authorization':
            continue

        headers.append({
            ph['key']: ph['value']
        })

    return headers


def create_body_format(body: Union[dict, list]):
    """
    {
        "key1": "val1",
        "key2": {
            "key3": "val3"
        },
        "key4": [
            {
                "key5": "val5"
            },
            {
                "key5": "val51"
            },
        ],
        "key7": [
            "a",
            "b",
            "c"
        ]
    }

    ==>
    {
        "key1": "{key1}",
        "key2": {
            "key3": "{key3}"
        },
        "key4": [
            {
                "key5": "{key5}"
            }
        ],
        "key7": "{key7}"
    }
    """
    def format_value(d, o):
        for k, v in d.items():
            if isinstance(v, dict):
                o[k] = {}
                o[k] = format_value(v, o[k])
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                o[k] = [{}]
                o[k][0] = format_value(v[0], o[k][0])
            else:
                o[k] = '{' + k + '}'
        return o

    if isinstance(body, dict):
        return format_value(body, {})
    if isinstance(body, list) and len(body) > 0 and isinstance(body[0], dict):
        return [format_value(body[0], {})]

    return None


def flatten_collections(items: list) -> list:
    """When creating nested collections, will flatten all the requests to a list of dicts."""
    lst = list()
    for item in items:
        if isinstance(item, list):  # A list of collections
            lst += flatten_collections(item)
        elif isinstance(item, dict) and 'item' in item:  # Get requests from collection
            lst += flatten_collections(item['item'])
        else:  # Request itself is a dict.
            lst.append(item)
    return lst


def postman_to_autogen_configuration(
        collection: dict,
        name,
        command_prefix,
        context_path_prefix,
        category=None
) -> IntegrationGeneratorConfig:
    info = collection.get('info', {})
    items = collection.get('item', [])
    postman_auth = collection.get('auth', {})
    variable = collection.get('variable', [])

    logger.debug('trying to find the default base url')
    for v in variable:
        if v['key'] in ('url', 'server'):
            host = v['value']
            logger.debug(f'base url found: {host}')
            break
    else:
        host = ''

    docker_image = get_docker_image()

    description = ''

    commands = []
    items = flatten_collections(items)  # in case of nested collections
    commands_names = build_commands_names_dict(items)
    duplicate_requests_check(commands_names)

    for item in items:
        command = convert_request_to_command(item)

        if command is None:
            # skip command in case is None
            # probably something was wrong with the request and command is not created
            continue

        commands.append(command)

    params = [
        IntegrationGeneratorParam(
            name='url',
            display='Server URL',
            type_=ParameterType.STRING,
            required=True,
            defaultvalue=host or 'https://www.example.com'
        ),
        IntegrationGeneratorParam(
            name='proxy',
            display='Use system proxy',
            type_=ParameterType.BOOLEAN,
            required=False
        ),
        IntegrationGeneratorParam(
            name='insecure',
            display='Trust any certificate',
            type_=ParameterType.BOOLEAN,
            required=False
        )
    ]

    if postman_auth:
        if postman_auth['type'] == 'apikey':
            params.append(IntegrationGeneratorParam(
                name='api_key',
                display='API Key',
                type_=ParameterType.ENCRYPTED,
                required=True
            ))
        elif postman_auth['type'] == 'bearer':
            params.append(IntegrationGeneratorParam(
                name='token',
                display='API Token',
                type_=ParameterType.ENCRYPTED,
                required=True
            ))
        elif postman_auth['type'] == 'basic':
            params.append(IntegrationGeneratorParam(
                name='credentials',
                display='Username',
                type_=ParameterType.AUTH,
                required=True
            ))
    else:
        # look for apikey in headers
        logger.debug('trying to find apikey in request headers')
        auth_header_found = False
        for item in items:
            if auth_header_found:
                break

            request = item.get('request', {})
            for header in request.get('header', []):
                if header.get('key') == 'Authorization':
                    params.append(IntegrationGeneratorParam(
                        name='api_key',
                        display='API Key',
                        type_=ParameterType.ENCRYPTED,
                        required=True
                    ))
                    logger.debug('found Authorization header')

                    if '{{' in header.get('value'):
                        # if header value contains {{ means it has a format like 'Authorization': 'SWSS {{apikey}}'
                        # header_format will be f'SWSS {api_key}'
                        header_format = "f'" + re.sub(r'\{\{.*\}\}', '{params["api_key"]}', header.get('value')) + "'"
                    else:
                        header_format = 'params[\'api_key\']'

                    postman_auth = {
                        'type': 'apikey',
                        'apikey': [
                            {
                                "key": "format",
                                "value": header_format,
                                "type": "string"
                            },
                            {
                                "key": "in",
                                "value": "header",
                                "type": "string"
                            },
                            {
                                "key": "key",
                                "value": "Authorization",
                                "type": "string"
                            }
                        ]
                    }

                    auth_header_found = True
                    break

    if name:
        display_name = name
        id_ = ''.join(e for e in name if e.isalnum())
    elif info.get('name'):
        display_name = info.get('name')
        id_ = ''.join(e for e in info.get('name') if e.isalnum())
    else:
        display_name = 'Generated Name Replace It'
        id_ = 'GeneratedNameReplaceIt'

    config = IntegrationGeneratorConfig(
        name=id_,
        display_name=display_name,
        description=description or info.get('description', 'Generated description - REPLACE THIS'),
        params=params,
        category=category or 'Utilities',
        command_prefix=command_prefix or tools.to_kebab_case(id_),
        commands=commands,
        docker_image=docker_image,
        context_path=context_path_prefix or id_,
        url=host,
        base_url_path='',
        auth=postman_auth,
    )

    return config


def get_docker_image():
    try:
        latest_tag = DockerImageValidator.get_docker_image_latest_tag_request('demisto/python3')
        docker_image = f'demisto/python3:{latest_tag}'
        logger.debug(f'docker image set to: {docker_image}')
    except Exception as e:
        # set default docker image
        docker_image = 'demisto/python3:3.9.1.14969'
        logger.warning(f'Failed getting latest docker image for demisto/python3: {e}')
    return docker_image


def convert_request_to_command(item: dict):
    logger.debug(f'converting request to command: {item.get("name")}')
    name = item.get('name')
    assert isinstance(name, str), 'Could not find name. Is this a valid postman 2.1 collection?'
    command_name = tools.to_kebab_case(name)
    context_prefix = tools.to_pascal_case(name)

    request = item.get('request')
    if request is None:
        raise DemistoException('Could not find request in the collection. Is it a valid postman collection?')

    logger.debug(f'converting postman headers of request: {name}')
    headers = postman_headers_to_conf_headers(request.get('header'), skip_authorization_header=True)

    args = []
    outputs = []
    returns_file = False

    logger.debug(f'creating url arguments of request: {name}')
    request_url_object = request.get('url')

    if not request_url_object:
        logger.error(f'failed to get item.request.url.path object of request {name}. '
                     f'Go to Postman, Save the request and try again with the updated collection.')
        return None

    url_path = '/'.join(request_url_object.get('path')).replace('{{', '{').replace('}}', '}')
    for url_path_item in request_url_object.get('path'):
        if re.match(r'\{\{.*\}\}', url_path_item):
            arg = IntegrationGeneratorArg(
                name=url_path_item.replace('{{', '').replace('}}', ''),
                description='',
                in_='url'
            )
            args.append(arg)

    for url_path_variable in request_url_object.get('variable', []):
        variable_name = url_path_variable.get('key')
        if not variable_name:
            continue
        arg = IntegrationGeneratorArg(
            name=variable_name,
            description='',
            in_='url'
        )
        args.append(arg)
        url_path = url_path.replace(f'/:{variable_name}', f'/{{{variable_name}}}')

    logger.debug(f'creating query arguments of request: {name}')
    for q in request_url_object.get('query', []):
        arg = IntegrationGeneratorArg(
            name=q.get('key'),
            description='',
            in_='query'
        )
        args.append(arg)

    logger.debug(f'creating arguments which will be passed to the request body of request: {name}')
    request_body = request.get('body')
    body_format = None
    if request_body:
        if request_body.get('mode') == 'raw':
            try:
                body_obj = json.loads(request_body.get('raw'))
                body_format = create_body_format(body_obj)

                for key, value in flatten_json(body_obj).items():
                    path_split = key.split('.')
                    json_path = path_split[:-1]
                    arg_name = path_split[-1]
                    arg = IntegrationGeneratorArg(
                        name=arg_name,
                        description='',
                        in_='body',
                        in_object=json_path
                    )
                    args.append(arg)

            except Exception:
                logger.exception(f'Failed to parse {name} request body as JSON.')

    if not item.get('response') or item.get('response') == 0:
        logger.error(f'[{name}] request is missing response. Make sure to save at least one successful '
                     f'response in Postman')
    else:
        try:
            response = item.get('response')[0]  # type: ignore[index]  # It will be catched in the except
            if response.get('_postman_previewlanguage') == 'json':
                outputs = generate_command_outputs(json.loads(response.get('body')))
            elif response.get('_postman_previewlanguage') == 'raw':
                returns_file = True

        except (ValueError, IndexError, TypeError):
            logger.exception(f'Failed to parse to JSON response body of {name} request.')

    command = IntegrationGeneratorCommand(
        name=command_name,
        url_path=url_path,
        http_method=request.get('method'),
        headers=headers,
        description=request.get('description') or '',
        arguments=args,
        outputs=outputs,
        context_path=context_prefix,
        root_object='',
        unique_key='',
        returns_file=returns_file,
        body_format=body_format
    )

    return command


def generate_command_outputs(body: Union[Dict, List]) -> List[IntegrationGeneratorOutput]:
    """
    Parses postman body to list of command outputs.
    Args:
        body (Union[Dict, List]): Body returned from HTTP request.

    Returns:
        (List[IntegrationGeneratorOutput]): List of outputs returned from the HTTP request.
    """
    flattened_body = flatten_json(body)
    # If body is list, remove first item of every key as it generates additional not needed dot.
    if isinstance(body, list):
        flattened_body = {k[1:]: v for k, v in flattened_body.items()}
    return [IntegrationGeneratorOutput(
        name=key,
        description='',
        type_=determine_type(value)
    ) for key, value in flattened_body.items()]


def build_commands_names_dict(items: list) -> dict:
    names_dict = defaultdict(list)
    for item in items:
        request_name = item.get('name', None)
        if request_name:
            command_name = tools.to_kebab_case(request_name)
            names_dict[command_name].append(request_name)
    return names_dict


def duplicate_requests_check(commands_names_dict: dict) -> None:
    duplicates_list = []
    for key in commands_names_dict:
        if len(commands_names_dict[key]) > 1:
            duplicates_list.extend(commands_names_dict[key])

    assert len(duplicates_list) == 0, f'There are requests with non-unique names: {duplicates_list}.\n' \
                                      f'You should give a unique name to each request.\n' \
                                      f'Names are case-insensitive and whitespaces are ignored.'
