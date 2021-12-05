import os
import time

import click
import demisto_client
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.tools import LOG_COLORS, get_yaml, print_color

SUCCESS_RETURN_CODE = 0
ERROR_RETURN_CODE = 1


class TestPlaybookRunner:
    """TestPlaybookRunner is a class that's designed to run a test playbook in a given XSOAR instance.

    Attributes:
        input (str): the input of the test playbook to run
        all (bool): whether to wait until the playbook run is completed or not.
        should_wait (bool): whether to wait until the test playbook run is completed or not.
        timeout (int): timeout for the command. The test playbook will continue to run in your xsoar instance.
        demisto_client (DefaultApi): Demisto-SDK client object.
        base_link_to_workplan (str): the base link to see the full test playbook run in your xsoar instance.
    """

    def __init__(self, input: str = '', all: bool = False, wait: bool = True, timeout: int = 90, insecure: bool = False):
        self.test_playbook_input = input
        self.all_test_playbooks = all
        self.should_wait = wait
        self.timeout = timeout
        verify = (not insecure) if insecure else None
        self.demisto_client = demisto_client.configure(verify_ssl=verify)
        self.base_link_to_workplan = self.get_base_link_to_workplan()

    def run_test_playbooks(self) -> int:
        """
        Run test playbooks on your XSOAR machine.
        :return: The exit code
        """
        exit_code: int = self.run_test_playbooks_manager()
        return exit_code

    def run_test_playbooks_manager(self):
        """
        Manages all ru-test-playbook command flows
        return The exit code of each flow
        """
        status_code = SUCCESS_RETURN_CODE

        if not self.verify_flags():
            status_code = ERROR_RETURN_CODE

        elif (self.test_playbook_input is None or not os.path.exists(self.test_playbook_input)) and \
                not self.all_test_playbooks:
            click.secho(f'Error: Given input path: {self.test_playbook_input} does not exist', fg='bright_red')
            status_code = ERROR_RETURN_CODE

        # Run specific test playbook
        elif os.path.isfile(self.test_playbook_input):
            test_playbook_id = self.get_test_playbook_id(self.test_playbook_input)
            status_code = self.run_test_playbook_by_id(test_playbook_id)

        # Run all pack test playbooks
        elif os.path.isdir(self.test_playbook_input):
            status_code = self.run_test_playbooks_folder(self.test_playbook_input)

        # Run all repo test playbooks
        elif self.all_test_playbooks:
            status_code = self.run_all_test_playbooks()

        return status_code

    def verify_flags(self) -> bool:
        """
        Verifies that the flags configuration given by the user is correct
        :return: The verification result
        """
        is_flags_valid = True
        if not self.all_test_playbooks:
            if not self.test_playbook_input:
                is_flags_valid = False
                print_color("Error: Missing option '-i' / '--input'.", LOG_COLORS.RED)
        return is_flags_valid

    def get_test_playbook_id(self, file_path):
        """
        Get test playbook ID from test playbook file name
        """
        test_playbook_data = get_yaml(file_path=file_path)
        return test_playbook_data.get('id')

    def run_test_playbooks_folder(self, folder_path):
        """
        Run all pack test playbooks
        """
        status_code = 0
        full_path = f'{folder_path}/TestPlaybooks'
        list_test_playbooks_files = os.listdir(full_path)
        for test_playbook in list_test_playbooks_files:
            test_playbook_id = self.get_test_playbook_id(os.path.join(full_path, test_playbook))
            res = self.run_test_playbook_by_id(test_playbook_id)
            if res == 1:
                status_code = 1
        return status_code

    def run_all_test_playbooks(self):
        """
        Run all the repo test playbooks
        """
        status_code = 0
        packs_list = os.listdir('Packs')
        for pack in packs_list:
            if os.path.isdir(f'Packs/{pack}'):
                res = self.run_test_playbooks_folder(f'Packs/{pack}')
                if res == 1:
                    status_code = 1
        return status_code

    def run_test_playbook_by_id(self, test_playbook_id):
        """Run a test playbook in your xsoar instance.

        Returns:
            int. 0 in success, 1 in a failure.
        """
        # create an incident with the given playbook
        try:
            incident_id = self.create_incident_with_test_playbook(
                incident_name=f'inc_{test_playbook_id}', test_playbook_id=test_playbook_id)
        except ApiException as a:
            print_color(str(a), LOG_COLORS.RED)
            return 1

        work_plan_link = self.base_link_to_workplan + str(incident_id)
        if self.should_wait:
            print_color(f'Waiting for the test playbook to finish running.. \n'
                        f'To see the test playbook run in real-time please go to : {work_plan_link}',
                        LOG_COLORS.GREEN)

            elapsed_time = 0
            start_time = time.time()

            while elapsed_time < self.timeout:
                test_playbook_results = self.get_test_playbook_results_dict(incident_id)
                if test_playbook_results["state"] == "inprogress":
                    time.sleep(10)
                    elapsed_time = int(time.time() - start_time)
                else:   # the test playbook has finished running
                    break

            # Ended the loop because of timeout
            if elapsed_time >= self.timeout:
                print_color(f'The command had timed out while the playbook is in progress.\n'
                            f'To keep tracking the test playbook please go to : {work_plan_link}', LOG_COLORS.RED)
            else:
                if test_playbook_results["state"] == "failed":
                    print_color("The test playbook finished running with status: FAILED", LOG_COLORS.RED)
                    return 1
                else:
                    print_color("The test playbook has completed its run successfully", LOG_COLORS.GREEN)

        else:
            print_color(f'To see results please go to : {work_plan_link}', LOG_COLORS.NATIVE)

        return 0

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

        print_color(f'The test playbook: {self.test_playbook_input} was triggered successfully.', LOG_COLORS.GREEN)
        return response.id

    def get_test_playbook_results_dict(self, inc_id):
        test_playbook_results = self.demisto_client.generic_request(method='GET', path=f'/inv-playbook/{inc_id}')
        return eval(test_playbook_results[0])

    def get_base_link_to_workplan(self):
        """Create a base link to the workplan in the specified xsoar instance
        Returns:
            str: The link to the workplan
        """

        base_url = os.environ.get('DEMISTO_BASE_URL')
        return f'{base_url}/#/WorkPlan/'
