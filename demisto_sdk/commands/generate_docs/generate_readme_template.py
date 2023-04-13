import logging
from demisto_sdk.commands.generate_docs.readme_templates import SYSLOG, HTTP_COLLECTOR, XDRC

logger = logging.getLogger("demisto-sdk")


def generate_readme_template(
    input_path: str,
    readme_template: str
):
    file_object = open(input_path, 'a')
    if readme_template == 'syslog':
        template = SYSLOG
    elif readme_template == 'http-collector':
        template = HTTP_COLLECTOR
    elif readme_template == 'xdrc':
        template = XDRC
    else:
        logger.info(f"[red]Template type {readme_template} is not supported.[/red]")
        return 1

    file_object.write(template)
