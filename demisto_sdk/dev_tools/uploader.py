from demisto_sdk.common.tools import print_color, LOG_COLORS, print_v
from demisto_sdk.common.demisto_client import Client


class Uploader(Client):
    """Upload the integration specified in self.infile to the remote Demisto instance.
        Attributes:
            infile (str): The path of the file to be uploaded.
            log_verbose (bool): Whether to output a detailed response.
        """

    def __init__(self, infile: str, url: str, insecure: bool = False, verbose: bool = False):
        self.infile = infile
        self.log_verbose = verbose
        Client.__init__(self, url, insecure)

    def upload(self):
        """Upload the integration specified in self.infile to the remote Demisto instance.
        """
        result = self.client.integration_upload(file=self.infile)

        print_v(f'Result:\n{result.to_str()}', self.log_verbose)
        print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = f"""Upload integration to Demisto instance.
        {Client.DEMISTO_API_KEY_ENV} environment variable should contain a valid Demisto API Key."""
        parser = subparsers.add_parser('upload', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-i", "--infile", help="The yml file to with the integration to upload", required=True)
        parser.add_argument("-u", "--url", help="Base URL of the Demisto instance", required=True)
        parser.add_argument("-k", "--insecure", help="Skip certificate validation", action="store_true")
        parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true')
