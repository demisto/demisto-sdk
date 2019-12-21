import re
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS, print_v, print_warning
import demisto_client
import os


class Runner:
    """Class for run command. Runs a command on a remote Demisto instance and pretty
    prints the result.
    """
    SECTIONS_HEADER_REGEX = re.compile(r'^(Context Outputs|Human Readable section|Raw Response section)')
    FULL_LOG_REGEX = re.compile(r'.*Full Integration Log')

    DEMISTO_API_KEY_ENV = 'DEMISTO_API_KEY'

    def __init__(self, query: str, url: str, debug_mode: bool = False, verbose: bool = False):
        self.query = query
        self.base_url = url
        self.log_verbose = verbose
        self.debug_mode = debug_mode
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

    def run(self):
        """Run the integration command on the remote Demisto instance
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

            self._export_debug_log(log_id)

    def _get_playground_id(self):
        """Retrieve Playground ID from the remote Demisto instance.
        """
        ans = self.client.search_investigations({
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
        update_entry = {
            'investigationId': playground_id,
            'data': query
        }

        ans = self.client.investigation_add_entry_handler(update_entry)

        # ans should have an entry with 'contents' - the readable output
        # of the command
        contents_entry = next((entry for entry in ans if entry.get('contents', None)), None)
        if contents_entry:
            print_color('## Readable Output', LOG_COLORS.YELLOW)
            print(contents_entry['contents'])
            print()
        else:
            print_warning('Entry with query output not found')

        # and an entry with a fileID defined, that is the fileID of the
        # debug log file
        log_entry = next((entry for entry in ans if entry.get('fileID', None)), None)

        return log_entry['id'] if log_entry else None

    def _export_debug_log(self, log_id: str):
        """Retrieve & rexport debug mode log file

        Args:
            log_id (str): artifact id of the log file
        """

        result = self.client.download_file(log_id)

        if self.debug_mode == '-':
            print_color('## Detailed Log', LOG_COLORS.YELLOW)
            for line in result.iter_lines():
                decoded_line = line.decode('utf-8')

                if self.SECTIONS_HEADER_REGEX.match(decoded_line):
                    print_color(decoded_line, LOG_COLORS.YELLOW)
                elif self.FULL_LOG_REGEX.match(decoded_line):
                    print_color('Full Integration Log:', LOG_COLORS.YELLOW)
                else:
                    print(decoded_line)
        else:
            with open(self.debug_mode, 'w+b') as fout:
                for chunk in result.iter_content(chunk_size=1024 * 1024):
                    fout.write(chunk)
            print_color(f'Debug Log successfully exported to {self.debug_mode}', LOG_COLORS.GREEN)

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = f"""Run integration command on remote Demisto instance in the playground.
        {Runner.DEMISTO_API_KEY_ENV} environment variable should contain a valid Demisto API Key."""
        parser = subparsers.add_parser('run', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-q", "--query", help="The query to run", required=True)
        parser.add_argument("-u", "--url", help="Base URL of the Demisto instance", required=True)
        parser.add_argument("-k", "--insecure", help="Skip certificate validation", action="store_true")
        parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true')
        parser.add_argument(
            "-D", "--debug-mode", metavar="DEBUG_LOG",
            help="Enable debug mode and write it to DEBUG_LOG. If DEBUG_LOG is not specified stdout is used",
            nargs='?', const='-', default=False
        )
