import ast
import json
import re
import tempfile

import demisto_client
from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error, print_v,
                                               print_warning)
from demisto_sdk.commands.json_to_outputs.json_to_outputs import \
    json_to_outputs


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
    RAW_RESPONSE_HEADER = re.compile(r'^Raw Response section')
    CONTEXT_HEADER = re.compile(r'Context Outputs:')
    HUMAN_READABLE_HEADER = re.compile(r'Human Readable section')
    FULL_LOG_REGEX = re.compile(r'.*Full Integration Log')

    def __init__(self, query: str, insecure: bool = False, debug: str = None, debug_path: str = None,
                 verbose: bool = False, json_to_outputs: bool = False, prefix: str = '', raw_response: bool = False):
        self.query = query if query.startswith('!') else f'!{query}'
        self.log_verbose = verbose
        self.debug = debug
        self.debug_path = debug_path
        verify = (not insecure) if insecure else None  # set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        self.client = demisto_client.configure(verify_ssl=verify)
        self.json2outputs = json_to_outputs
        self.prefix = prefix
        self.raw_response = raw_response

        if self.debug or self.json2outputs:
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

        if self.json2outputs:
            if not self.prefix:
                print_error("A prefix for the outputs is needed for this command. Please provide one")
                return 1
            else:
                raw_output_json = self._return_context_dict_from_log(log_ids)
                if raw_output_json:
                    with tempfile.NamedTemporaryFile(mode='w+') as f:
                        if isinstance(raw_output_json, dict):
                            f.write(json.dumps(raw_output_json))
                        if isinstance(raw_output_json, list):
                            f.write(json.dumps(raw_output_json[0]))
                        f.seek(0)
                        file_path = f.name
                        command = self.query.split(' ')[0]
                        json_to_outputs(command, file_path, self.prefix)
                else:
                    print_error("Could not extract raw output as JSON from command")
                    return 1

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
        if self.debug_path:
            with open(self.debug_path, 'w+b') as output_file:
                for log_id in log_ids:
                    result = self.client.download_file(log_id)
                    with open(result, 'r+') as log_info:
                        for line in log_info:
                            output_file.write(line.encode('utf-8'))
            print_color(f'Debug Log successfully exported to {self.debug_path}', LOG_COLORS.GREEN)
        else:
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

    def _return_context_dict_from_log(self, log_ids: list) -> dict:
        """
            retrieves the context section from the debug_log. If context is empty ({}) or doesn't exist, returns
            the raw output section.
        Args:
            log_ids (list): artifact ids of the log files

        Returns:
            the context of the executed query
        """
        if not self.debug_path:
            for log_id in log_ids:
                result = self.client.download_file(log_id)
                with open(result, 'r+') as log_info:
                    for line in log_info:
                        if self.RAW_RESPONSE_HEADER.match(line):
                            try:
                                return json.loads(log_info.readline())
                            except Exception:
                                pass
                        if self.CONTEXT_HEADER.match(line) and not self.raw_response:
                            context = ''
                            line = log_info.readline()
                            while not self.HUMAN_READABLE_HEADER.match(line):
                                context = context + line
                                line = log_info.readline()
                            context = re.sub(r"\(val\..+\)", "", context)  # noqa: W605
                            try:
                                temp_dict = json.loads(context)
                                if temp_dict:
                                    return temp_dict
                            except Exception:
                                pass
            return dict()
        else:
            temp_dict = dict()
            with open(self.debug_path, 'w+b') as output_file:
                for log_id in log_ids:
                    result = self.client.download_file(log_id)
                    with open(result, 'r+') as log_info:
                        for line in log_info:
                            if self.RAW_RESPONSE_HEADER.match(line) and not temp_dict:
                                output_file.write(line.encode('utf-8'))
                                line = log_info.readline()
                                try:
                                    temp_dict = json.loads(line)
                                except Exception:
                                    pass
                            if self.CONTEXT_HEADER.match(line) and not self.raw_response:
                                context = ''
                                output_file.write(line.encode('utf-8'))
                                line = log_info.readline()
                                while not self.HUMAN_READABLE_HEADER.match(line):
                                    output_file.write(line.encode('utf-8'))
                                    context = context + line
                                    line = log_info.readline()
                                context = re.sub(r'\(val\..+\)', '', context)
                                try:
                                    temp_dict = json.loads(context)
                                except Exception:
                                    pass
                            output_file.write(line.encode('utf-8'))
            print_color(f'Debug Log successfully exported to {self.debug_path}', LOG_COLORS.GREEN)
            return temp_dict

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
