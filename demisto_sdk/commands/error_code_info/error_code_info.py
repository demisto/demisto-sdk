from inspect import signature

import click
from colorama import Fore
from demisto_sdk.commands.common import errors

TEMPLATE = '''
Error Code: {code}
Function: {func}
Ignorable: {ignorable}
Message:
{msg}
'''


def print_error_information(func_name, error_data, func, sig):
    click.secho(f'{Fore.GREEN}## Error Code Info ##{Fore.RESET}')
    click.secho(TEMPLATE.format(
        code=error_data['code'],
        func=f'{func_name}{sig}',
        ignorable=error_data['code'] in errors.ALLOWED_IGNORE_ERRORS,
        msg=func(**{a: f'<{a}>' for a in list(sig.parameters)})[0],
    ))


def find_error(error_code):
    for func_name, error_data in errors.ERROR_CODE.items():
        if error_data['code'] == error_code:
            return func_name, error_data

    return '', {}


def generate_error_code_information(error_code):
    func_name, error_data = find_error(error_code)
    if not func_name:
        click.secho(f'{Fore.RED}No such error')
        return 1

    func = getattr(errors.Errors, func_name)
    sig = signature(func)

    print_error_information(func_name, error_data, func, sig)
    return 0
