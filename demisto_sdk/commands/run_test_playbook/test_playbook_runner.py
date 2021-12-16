import os
import re
import time

import click
import demisto_client
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.tools import LOG_COLORS, get_yaml, print_color
from demisto_sdk.commands.upload.uploader import Uploader

SUCCESS_RETURN_CODE = 0
ERROR_RETURN_CODE = 1
ENTRY_TYPE_ERROR = 4


class TestPlaybookRunner:
    """TestPlaybookRunner is a class that's designed to run a test playbook in a given XSOAR instance.

    Attributes:
        test_playbook_path (str): the input of the test playbook to run
        all (bool): whether to wait until the playbook run is completed or not.
        should_wait (bool): whether to wait until the test playbook run is completed or not.
        timeout (int): timeout for the command. The test playbook will continue to run in your xsoar instance.
        demisto_client (DefaultApi): Demisto-SDK client object.
        base_link_to_workplan (str): the base link to see the full test playbook run in your xsoar instance.
    """

    def __init__(self, test_playbook_path: str = '', all: bool = False, wait: bool = True, timeout: int = 90,
                 insecure: bool = False):
        self.test_playbook_path = test_playbook_path
        self.all_test_playbooks = all
        self.should_wait = wait
        self.timeout = timeout

        # we set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        self.verify = (not insecure) if insecure else None
        self.demisto_client = demisto_client.configure(verify_ssl=self.verify)
        self.base_link_to_workplan = self.get_base_link_to_workplan()

    def manage_and_run_test_playbooks(self):
        """
        Manages all ru-test-playbook command flows
        return The exit code of each flow
        """
        status_code = SUCCESS_RETURN_CODE
        test_playbooks: list = []

        if not self.validate_tpb_path():
            status_code = ERROR_RETURN_CODE

        test_playbooks.extend(self.collect_all_tpb_files_paths())

        for tpb in test_playbooks:
            self.upload_tpb(tpb_file=tpb)
            test_playbook_id = self.get_test_playbook_id(tpb)
            status_code = self.run_test_playbook_by_id(test_playbook_id)

        return status_code

    def collect_all_tpb_files_paths(self):
        test_playbooks: list = []
        # Run all repo test playbooks
        if self.all_test_playbooks:
            test_playbooks.extend(self.get_all_test_playbooks())

        # Run all pack test playbooks
        elif os.path.isdir(self.test_playbook_path):
            test_playbooks.extend(self.get_test_playbooks_from_folder(self.test_playbook_path))

        # Run specific test playbook
        elif os.path.isfile(self.test_playbook_path):
            test_playbooks.append(self.test_playbook_path)

        return test_playbooks

    def validate_tpb_path(self) -> bool:
        """
        Verifies that the input path configuration given by the user is correct
        :return: The verification result
        """
        is_path_valid = True
        if not self.all_test_playbooks:
            if not self.test_playbook_path:
                print_color("Error: Missing option '-tpb' / '--test-playbook-path'.", LOG_COLORS.RED)
                is_path_valid = False

            elif not os.path.exists(self.test_playbook_path):
                print_color(f'Error: Given input path: {self.test_playbook_path} does not exist', LOG_COLORS.RED)
                is_path_valid = False

        return is_path_valid

    def get_test_playbook_id(self, file_path):
        """
        Get test playbook ID from test playbook file name
        """
        test_playbook_data = get_yaml(file_path=file_path)
        return test_playbook_data.get('id')

    def get_test_playbooks_from_folder(self, folder_path):
        """
        Get all pack test playbooks
        """
        full_path = f'{folder_path}/TestPlaybooks'
        list_test_playbooks_files = os.listdir(full_path)
        list_test_playbooks_files = [f'{full_path}/{tpb}' for tpb in list_test_playbooks_files]
        return list_test_playbooks_files

    def get_all_test_playbooks(self):
        """
        Get all the repo test playbooks
        """
        tpb_list: list = []
        packs_list = os.listdir('Packs')
        for pack in packs_list:
            if os.path.isdir(f'Packs/{pack}'):
                tpb_list.extend(self.get_test_playbooks_from_folder(f'Packs/{pack}'))
        return tpb_list

    def run_test_playbook_by_id(self, test_playbook_id):
        """Run a test playbook in your xsoar instance.

        Returns:
            int. 0 in success, 1 in a failure.
        """
        status_code: int = SUCCESS_RETURN_CODE
        # create an incident with the given playbook
        try:
            incident_id = self.create_incident_with_test_playbook(
                incident_name=f'inc_{test_playbook_id}', test_playbook_id=test_playbook_id)
        except ApiException as a:
            print_color(str(a), LOG_COLORS.RED)
            status_code = ERROR_RETURN_CODE

        work_plan_link = self.base_link_to_workplan + str(incident_id)
        if self.should_wait:
            status_code = self.run_and_check_tpb_status(test_playbook_id, work_plan_link, incident_id)

        else:
            print_color(f'To see results please go to : {work_plan_link}', LOG_COLORS.NATIVE)

        return status_code

    def run_and_check_tpb_status(self, test_playbook_id, work_plan_link, incident_id):
        status_code = SUCCESS_RETURN_CODE
        print_color(f'Waiting for the test playbook to finish running.. \n'
                    f'To see the test playbook run in real-time please go to : {work_plan_link}', LOG_COLORS.GREEN)

        elapsed_time = 0
        start_time = time.time()

        while elapsed_time < self.timeout:
            test_playbook_result = self.get_test_playbook_results_dict(incident_id)
            if test_playbook_result['state'] == "inprogress":
                time.sleep(10)
                elapsed_time = int(time.time() - start_time)
            else:  # the test playbook has finished running
                break

        # Ended the loop because of timeout
        if elapsed_time >= self.timeout:
            print_color(f'The command had timed out while the playbook is in progress.\n'
                        f'To keep tracking the test playbook please go to : {work_plan_link}', LOG_COLORS.RED)
        else:
            if test_playbook_result['state'] == "failed":
                self.print_tpb_error_details(test_playbook_result, test_playbook_id)
                print_color("The test playbook finished running with status: FAILED", LOG_COLORS.RED)
                status_code = ERROR_RETURN_CODE
            else:
                print_color("The test playbook has completed its run successfully", LOG_COLORS.GREEN)

        return status_code

    def create_incident_with_test_playbook(self, incident_name, test_playbook_id):
        # type: (str, str) -> int
        """Create an incident in your xsoar instance with the given incident_name and the given test_playbook_id

        Args:
            incident_name (str): The name of the incident
            test_playbook_id (str): The id of the playbook

        Raises:
            ApiException: if the client has failed to create an incident

        Returns:
            int. The new incident's ID.
        """

        create_incident_request = demisto_client.demisto_api.CreateIncidentRequest()
        create_incident_request.create_investigation = True
        create_incident_request.playbook_id = test_playbook_id
        create_incident_request.name = incident_name

        try:
            response = self.demisto_client.create_incident(create_incident_request=create_incident_request)
        except ApiException as e:
            print_color(f'Failed to create incident with playbook id : "{test_playbook_id}", '
                        'possible reasons are:\n'
                        '1. This playbook name does not exist \n'
                        '2. Schema problems in the playbook \n'
                        '3. Unauthorized api key', LOG_COLORS.RED)
            raise e

        print_color(f'The test playbook: {self.test_playbook_path} was triggered successfully.', LOG_COLORS.GREEN)
        return response.id

    def get_test_playbook_results_dict(self, inc_id):
        test_playbook_results = self.demisto_client.generic_request(method='GET', path=f'/inv-playbook/{inc_id}')
        return eval(test_playbook_results[0])

    def print_tpb_error_details(self, tpb_res, tpb_id):
        entries = tpb_res['entries']
        print_color(f'Test Playbook {tpb_id} has failed:', LOG_COLORS.RED)
        for entry in entries:
            if entry['type'] == ENTRY_TYPE_ERROR and entry['parentContent']:
                print_color(f'- Task ID: {entry["taskId"]}', LOG_COLORS.RED)
                # Checks for passwords and replaces them with "******"
                parent_content = re.sub(r' (P|p)assword="[^";]*"', ' password=******', entry['parentContent'])
                print_color(f'  Command: {parent_content}', LOG_COLORS.RED)
                print_color(f'  Body:\n{entry["contents"]}', LOG_COLORS.RED)

    def get_base_link_to_workplan(self):
        """Create a base link to the workplan in the specified xsoar instance
        Returns:
            str: The link to the workplan
        """

        base_url = os.environ.get('DEMISTO_BASE_URL')
        return f'{base_url}/#/WorkPlan/'

    def upload_tpb(self, tpb_file):
        uploader = Uploader(input=tpb_file, insecure=self.verify)  # type: ignore
        uploader.upload()
