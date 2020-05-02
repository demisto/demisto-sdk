import ast
import re

import demisto_client
from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error, print_v,
                                               print_warning)


class DemistoRunTimeError(RuntimeError):
    """Demisto run time error"""
    pass


class Runner:
    """Used to run a command on Demisto and print the results.
        Attributes:
            query (str): The query to execute.
            log_verbose (bool): Whether to output a detailed response.
            debug (str): Holds the path of the debug log file (or '-' if the logs will be printed in stdout).
            debug_path (str): The path in which you will save the debug file.
            client (DefaultApi): Demisto-SDK client object.
        """
    ERROR_ENTRY_TYPE = 4
    DEBUG_FILE_ENTRY_TYPE = 16
    SECTIONS_HEADER_REGEX = re.compile(r'^(Context Outputs|Human Readable section|Raw Response section)')
    FULL_LOG_REGEX = re.compile(r'.*Full Integration Log')

    def __init__(self, query: str, insecure: bool = False, debug: str = None, debug_path: str = None,
                 verbose: bool = False):
        self.query = query if query.startswith('!') else f'!{query}'
        self.log_verbose = verbose
        self.debug = debug
        self.debug_path = debug_path
        self.client = demisto_client.configure(verify_ssl=not insecure)

        if self.debug:
            self.query += ' debug-mode="true"'

    def run(self):
        """Runs an integration command on Demisto and prints the result.
        """
        playground_id = self._get_playground_id()

        try:
            log_ids = self._run_query(playground_id)
        except DemistoRunTimeError as err:
            log_ids = None
            print_error(str(err))

        if self.debug:
            if not log_ids:
                print_warning('Entry with debug log not found')
            else:
                self._export_debug_log(log_ids)

    def _get_playground_id(self):
        """Retrieves Playground ID from the remote Demisto instance.
        """
        playground_filter = {'filter': {'type': [9]}}
        answer = self.client.search_investigations(filter=playground_filter)

        if answer.total != 1:
            raise RuntimeError(
                f'Got unexpected amount of results in getPlaygroundInvestigationID. '
                f'Response was: {answer.total}'
            )

        result = answer.data[0].id

        print_v(f'Playground ID: {result}', self.log_verbose)

        return result

    def _run_query(self, playground_id: str):
        """Runs a query on Demisto instance and prints the output.

        Args:
            playground_id: The investigation ID of the playground.

        Returns:
            list. A list of the log IDs if debug mode is on, otherwise an empty list.
        """
        update_entry = {
            'investigationId': playground_id,
            'data': self.query
        }

        answer = self.client.investigation_add_entries_sync(update_entry=update_entry)
        if not answer:
            raise DemistoRunTimeError('Command did not run, make sure it was written correctly.')

        log_ids = []

        for entry in answer:
            # answer should have entries with `contents` - the readable output of the command
            if entry.parent_content:
                print_color('### Command:', LOG_COLORS.YELLOW)
            if entry.contents:
                print_color('## Readable Output', LOG_COLORS.YELLOW)
                if entry.type == self.ERROR_ENTRY_TYPE:
                    print_error(entry.contents + '\n')
                else:
                    print(entry.contents + '\n')

            # and entries with `file_id`s defined, that is the fileID of the debug log file
            if entry.type == self.DEBUG_FILE_ENTRY_TYPE:
                log_ids.append(entry.id)

        return log_ids

    def _export_debug_log(self, log_ids: list):
        """Retrieve & export debug mode log files

        Args:
            log_ids (list): artifact ids of the log files
        """
        if not self.debug_path:
            print_color('## Detailed Log', LOG_COLORS.YELLOW)
            for log_id in log_ids:
                result = self.client.download_file(log_id)
                with open(result, 'r+') as log_info:
                    for line in log_info:
                        if self.SECTIONS_HEADER_REGEX.match(line):
                            print_color(line, LOG_COLORS.YELLOW)
                        elif self.FULL_LOG_REGEX.match(line):
                            print_color('Full Integration Log:', LOG_COLORS.YELLOW)
                        else:
                            print(line)
        else:
            with open(self.debug_path, 'w+b') as output_file:
                for log_id in log_ids:
                    result = self.client.download_file(log_id)
                    with open(result, 'r+') as log_info:
                        for line in log_info:
                            output_file.write(line.encode('utf-8'))
            print_color(f'Debug Log successfully exported to {self.debug_path}', LOG_COLORS.GREEN)

    def execute_command(self, command: str):
        playground_id = self._get_playground_id()

        # delete context
        update_entry = {
            'investigationId': playground_id,
            'data': '!DeleteContext all=yes'
        }

        self.client.investigation_add_entries_sync(update_entry=update_entry)

        # execute the command in playground
        update_entry = {
            'investigationId': playground_id,
            'data': command
        }
        res = self.client.investigation_add_entries_sync(update_entry=update_entry)

        body = {'query': '${.}'}
        context = self.client.generic_request(f'investigation/{playground_id}/context', 'POST', body)[0]

        context = ast.literal_eval(context)

        return res, context
