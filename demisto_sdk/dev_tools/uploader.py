from demisto_sdk.common.configuration import Configuration
from demisto_sdk.common.tools import print_color, LOG_COLORS
from demisto_sdk.common.rest_api import Client, DEMISTO_API_KEY_ENV


class Uploader:
    def __init__(self, infile: str, url: str, insecure: bool = False,
                 verbose: bool = False, configuration: Configuration = Configuration()):
        self.infile = infile
        self.base_url = url
        self.verify_cert = not insecure
        self.log_verbose = verbose

    def upload(self):
        """Do the job. Upload the integration YML to the remote Demisto instance.
        """

        with open(self.infile, 'r') as f:
            client = Client(
                base_url=self.base_url,
                verify_cert=self.verify_cert,
                verbose=self.log_verbose
            )
            client.upload_integration(f)

        print_color(f'Uploaded '{self.infile}' successfully', LOG_COLORS.GREEN)

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = f"""Upload integration to Demisto instance.
        {DEMISTO_API_KEY_ENV} environment variable should contain a valid Demisto API Key."""
        parser = subparsers.add_parser('upload', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-i", "--infile", help="The yml file to with the integration to upload", required=True)
        parser.add_argument("-u", "--url", help="Base URL of the Demisto instance", required=True)
        parser.add_argument("-k", "--insecure", help="Skip certificate validation", action="store_true")
        parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true')
