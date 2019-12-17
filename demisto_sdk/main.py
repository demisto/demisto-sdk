import sys
from demisto_sdk.core import DemistoSDK



import click

#
# def get_colors(ctx, args, incomplete):
#     raise Exception(ctx.__dict__)
#     colors = [('-red', 'red'),
#               ('-blue', 'blue'),
#               ('-green', 'green')]
#     return [c for c in colors if incomplete in c[0]]
#
#
# def get_colors2(ctx, args, incomplete):
#     colors = [('red', 'adfa'),
#               ('blue', 'asdf'),
#               ('green', 'sadf')]
#     return [c for c in colors if incomplete in c[0]]
#
#
#
# def get_colors3(ctx, args, incomplete):
#     colors = [('validate', 'adfa'),
#               ('build', 'asdf'),
#               ('green', 'sadf')]
#     return [c for c in colors if incomplete in c[0]]
#
#
# @click.command()
# @click.option("-validate")
# @click.option("-kaki")
# def cmd1(validate):
#     click.echo('Chosen color is %s' % validate)
#
#
# @click.command()
# @click.argument("kaka", type=click.STRING, autocompletion=get_colors2)
# def cmd2(kaka):
#     click.echo('Chosen color is %s' % kaka)
#
# @click.command()
# @click.argument("command_name", type=click.STRING, autocompletion=get_colors3, allow_interspersed_args=True,
#                 context=click.Context(command=command_nameallow_interspersed_args=True))
# # @click.option('-validate', type=click.Choice(['circle', 'bla']))
# def main(command_name):
#     # TODO: Typings and docstrings
#     # sdk = DemistoSDK()
#     # return sdk.parse_args()
#     if command_name == "validate":
#         cmd1()
#     else:
#         cmd2()
#     return 0

@click.group()
def main():
   pass


@main.command(name="current")
@click.argument('location')
@click.option(
    '--api-key', '-a',
    help='your API key for the OpenWeatherMap API',
)
def kak(location, api_key):
    print("Asdfsf")


@main.command(name="somethine")
@click.argument('location')
@click.option(
    '--sdf', '-s',
    help='your API key for the OpenWeatherMap API',
)
@click.option(
    '--fuck', '-f',
    help='your API key for the OpenWeatherMap API',
)
def kak(location, api_key):
    print("Asdfsf")


if __name__ == '__main__':
    sys.exit(main())
