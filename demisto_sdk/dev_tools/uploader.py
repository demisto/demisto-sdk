from demisto_sdk.common.tools import print_color, LOG_COLORS
from demisto_sdk.common.tools import print_v
import demisto_client
import json
import os


class Uploader:
    DEMISTO_API_KEY_ENV = 'DEMISTO_API_KEY'

    def __init__(self, infile: str, url: str, verbose: bool = False):
        self.infile = infile
        self.base_url = url
        self.log_verbose = verbose
        self.client = demisto_client.configure(base_url=self.base_url, api_key=self.get_api_key(), verify_ssl=False)

    def get_api_key(self):
        """Retrieve the API Key

        Raises:
            RuntimeError: if the API Key environment variable is not found

        Returns:
            str: API Key
        """
        ans = os.environ.get(self.DEMISTO_API_KEY_ENV, None)
        if ans is None:
            raise RuntimeError(f'Error: Environment variable {self.DEMISTO_API_KEY_ENV} not found')

        return ans

    def upload(self):
        """Upload the integration specified in self.infile to the remote Demisto instance.
        """

        with open(self.infile, 'r') as yml_file:
            module_configuration = {'file': yml_file}
            result = self.client.integration_upload(module_configuration)

            if self.log_verbose:
                full_result = result.json()
                print_v(
                    f'Result: {json.dumps(full_result, indent=4)}',
                    self.log_verbose
                )

            result.close()

        print_color(f'Uploaded \'{self.infile}\' successfully', LOG_COLORS.GREEN)

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = f"""Upload integration to Demisto instance.
        {Uploader.DEMISTO_API_KEY_ENV} environment variable should contain a valid Demisto API Key."""
        parser = subparsers.add_parser('upload', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-i", "--infile", help="The yml file to with the integration to upload", required=True)
        parser.add_argument("-u", "--url", help="Base URL of the Demisto instance", required=True)
        parser.add_argument("-k", "--insecure", help="Skip certificate validation", action="store_true")
        parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true')
