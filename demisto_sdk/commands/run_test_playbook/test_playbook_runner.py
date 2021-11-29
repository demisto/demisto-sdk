import os
import time

import demisto_client
from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)


class TestPlaybookRunner:
    """TestPlaybookRunner is a class that's designed to run a test playbook in a given XSOAR instance.

    Attributes:
        test_playbook_id (str): the ID of the test playbook to run
        should_wait (bool): whether to wait until the playbook run is completed or not.
        timeout (int): timeout for the command. The test playbook will continue to run in your xsoar instance.
        demisto_client (DefaultApi): Demisto-SDK client object.
        base_link_to_workplan (str): the base link to see the full test playbook run in your xsoar instance.
    """

    def __init__(self, test_playbook_id: str, url: str, wait: bool, timeout: int, insecure: bool = False):
        self.test_playbook_id = test_playbook_id
        self.should_wait = wait
        self.timeout = timeout
        verify = (not insecure) if insecure else None  # we set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        # if url parameter is not provided, demisto_client will search the DEMISTO_BASE_URL env variable
        self.demisto_client = demisto_client.configure(
            base_url=url,
            verify_ssl=verify)

        self.base_link_to_workplan = self.get_base_link_to_workplan(url)

    def run_test_playbook(self):
        # type: () -> int
        """Run a test playbook in your xsoar instance.

        Returns:
            int. 0 in success, 1 in a failure.
        """
        # create an incident with the given playbook
        try:
            incident_id = self.create_incident_with_test_playbook(
                incident_name=f'inc_{self.test_playbook_id}', test_playbook_id=self.test_playbook_id)
        except ApiException as a:
            print_error(str(a))
            return 1

        work_plan_link = self.base_link_to_workplan + str(incident_id)
        if self.should_wait:
            print(f'Waiting for the test playbook to finish running.. \n'
                  f'To see the test playbook run in real-time please go to : {work_plan_link}',
                  LOG_COLORS.GREEN)

            elasped_time = 0
            start_time = time.time()

            while elasped_time < self.timeout:
                test_playbook_results = self.get_test_playbook_results_dict(incident_id)
                if test_playbook_results["state"] == "inprogress":
                    time.sleep(10)
                    elasped_time = int(time.time() - start_time)
                else:   # the test playbook has finished running
                    break

            # Ended the loop because of timeout
            if elasped_time >= self.timeout:
                print_error(f'The command had timed out while the playbook is in progress.\n'
                            f'To keep tracking the test playbook please go to : {work_plan_link}')
            else:
                if test_playbook_results["state"] == "failed":
                    print_error("The test playbook finished running with status: FAILED")
                else:
                    print_color("The test playbook has completed its run successfully", LOG_COLORS.GREEN)

        # The command does not wait for the test playbook to finish running
        else:
            print(f'To see results please go to : {work_plan_link}')

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
            print_error(f'Failed to create incident with playbook id : "{test_playbook_id}", '
                        'possible reasons are:\n'
                        '1. This playbook name does not exist \n'
                        '2. Schema problems in the playbook \n'
                        '3. Unauthorized api key')
            raise e

        print_color(f'The test playbook: {self.test_playbook_id} was triggered successfully.', LOG_COLORS.GREEN)
        return response.id

    def get_test_playbook_results_dict(self, inc_id):
        test_playbook_results = self.demisto_client.generic_request(method='GET', path=f'/inv-playbook/{inc_id}')
        return eval(test_playbook_results[0])

    def get_base_link_to_workplan(self, url):
        """Create a base link to the workplan in the specified xsoar instance

        Args:
            url(str): URL to a xsoar instance. Could be None if not provided

        Returns:
            str: The link to the workplan
        """

        if url:
            return f'{url}/#/WorkPlan/'

        else:
            base_url = os.environ.get('DEMISTO_BASE_URL')
            return f'{base_url}/#/WorkPlan/'
