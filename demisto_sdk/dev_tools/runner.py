import re

from demisto_sdk.common.configuration import Configuration
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS, print_v, print_warning
from demisto_sdk.common.rest_api import Client, DEMISTO_API_KEY_ENV


SECTIONS_REGEX = re.compile(r'^(Context Outputs|Human Readable section|Raw Response section)')
FULL_LOG_REGEX = re.compile(r'.*Full Integration Log')


class Runner:
    def __init__(self, query: str, url: str, insecure: bool = False, debug_mode: bool = False,
                 verbose: bool = False, configuration: Configuration = Configuration()):
        self.query = query
        self.base_url = url
        self.verify_cert = not insecure
        self.log_verbose = verbose
        self.debug_mode = debug_mode

    def run(self):
        """Do the job. Run the integration command on the remote Demisto instance
        and pretty prints the result.
        """
        playground_id = self._get_playground_id()

        query = self.query
        if self.debug_mode:
            query = self.query + ' debug-mode="true"'

        log_id = self._run_query(playground_id, query)

        if self.debug_mode:
            if log_id is None:
                print_warning('Entry with debug log not found')
                return

            self._pretty_print_log(log_id)

    def _get_playground_id(self):
        """Retrieve Playground ID from the remote Demisto instance.
        """
        client = Client(
            base_url=self.base_url,
            verify_cert=self.verify_cert,
            verbose=self.log_verbose
        )

        ans = client.search_investigations({
            'filter': {
                'type': [9]
            }
        })

        total = ans.get('total', None)
        if total != 1:
            print_error(
                'Got unexpected amount of results. If you are using MT environment, '
                'use the Tenant as Demisto\'s URL instead of the Master.'
            )
            raise RuntimeError(
                f'Got unexpected amount of results in getPlaygroundInvestigationID. '
                f'Response was: {total}'
            )

        data = ans.get('data', None)
        if data is None:
            raise RuntimeError(f'Missing data field in response')

        result = data[0]['id']
        print_v(f'Playground ID: {result}', self.log_verbose)

        return result

    def _run_query(self, playground_id: str, query: str):
        """Run a query on the Playground of the remote Demisto instance.
        Print the readable output and return the id of the debug log file.
        """
        client = Client(
            base_url=self.base_url,
            verify_cert=self.verify_cert,
            verbose=self.log_verbose
        )
        ans = client.run_query(playground_id, query)

        # ans should have an entry with 'contents' - the readable output
        # of the command
        centry = next((entry for entry in ans if entry.get('contents', None)), None)
        if centry:
            print_color('## Readable Output', LOG_COLORS.YELLOW)
            print(centry['contents'])
            print()
        else:
            print_warning('Entry with query output not found')

        # and an entry with a fileID defined, that is the fileID of the
        # debug log file
        lentry = next((entry for entry in ans if entry.get('fileID', None)), None)

        return lentry['id'] if lentry else None

    def _pretty_print_log(self, log_id: str):
        """Retrieve & pretty print debug mode log file
        
        Args:
            log_id (str): artifact id of the log file
        """
        client = Client(
            base_url=self.base_url,
            verify_cert=self.verify_cert,
            verbose=self.log_verbose
        )
        result = client.download_file(log_id)

        print_color('## Detailed Log', LOG_COLORS.YELLOW)
        for l in result.iter_lines():
            dl = l.decode('utf-8')

            if SECTIONS_REGEX.match(dl):
                print_color(dl, LOG_COLORS.YELLOW)
            elif FULL_LOG_REGEX.match(dl):
                print_color('Full Integration Log:', LOG_COLORS.YELLOW)
            else:
                print(dl)

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = f"""Run integration command on remote Demisto instance in the playground.
        {DEMISTO_API_KEY_ENV} environment variable should contain a valid Demisto API Key."""
        parser = subparsers.add_parser('run', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-q", "--query", help="The query to run", required=True)
        parser.add_argument("-u", "--url", help="Base URL of the Demisto instance", required=True)
        parser.add_argument("-k", "--insecure", help="Skip certificate validation", action="store_true")
        parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true')
        parser.add_argument("-D", "--debug-mode", help="Enable debug mode", action='store_true')
