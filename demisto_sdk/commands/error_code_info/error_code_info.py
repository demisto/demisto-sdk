from colorama import Fore
from inspect import signature

from demisto_sdk.commands.common import errors

TEMPLATE = '''
Error Code: {code}
Function: {func}
Message:
{msg}
'''


def print_error_information(func_name, error_data, func, sig):
    print(f'{Fore.GREEN}## Error Code Info ##{Fore.WHITE}')
    print(TEMPLATE.format(
        code=error_data['code'],
        func=f'{func_name}{sig}',
        msg=func(**{a: f'<{a}>' for a in list(sig.parameters)}),
    ))


def find_error(error_code):
    for func_name, error_data in errors.ERROR_CODE.items():
        if error_data['code'] == error_code:
            return func_name, error_data

    return '', {}


def generate_error_code_information(error_code):
    func_name, error_data = find_error(error_code)
    if not func_name:
        print('No such error')
        return

    func = getattr(errors.Errors, func_name)
    sig = signature(func)

    print_error_information(func_name, error_data, func, sig)


# @click.command(
#     name='error-code-info',
#     help='',
#     hidden=True,
# )
# @click.help_option(
#     '-h', '--help'
# )
# @click.option(
#     '-i', '--input', required=True,
#     help='The error code to search for.',
# )
# def error_code_info(config, **kwargs):
#     check_configuration_file('error-code-info', kwargs)
#     sys.path.append(config.configuration.env_dir)
#
#     generate_error_code_information(kwargs.get('input'))
#
#     sys.exit(0)
#
