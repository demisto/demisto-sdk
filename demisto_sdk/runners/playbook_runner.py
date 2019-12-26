import time
import demisto_client
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS


class PlaybookRunner:
    """PlaybookRunner is a class that's designed to run a playbook in a given Demisto instance.
    It will decide whether to wait for the playbook to finish its run or just trigger it, according to the 'wait' flag.

    Attributes:
        base_link_to_workplan (str): the base link to the workplan of the created incident.
        demisto_client (demisto_client): object for creating an incident in Demisto.
    """

    def __init__(self, playbook_name: str, url: str, api: str, wait: bool, timeout: int):
        self.playbook_name = playbook_name
        self.should_wait = wait
        self.timeout = timeout
        self.base_link_to_workplan = f'{url}/#/WorkPlan/'
        self.demisto_client = demisto_client.configure(
            base_url=url,
            api_key=api,
            verify_ssl=False)

    def run_playbook(self):
        # type: () -> int
        """Run a playbook in Demisto.

        Returns:
            int. 0 in success, 1 in a failure.
        """
        # create an incident with the given playbook
        incident_id = self.create_incident_with_playbook(
            incident_name=f'inc_{self.playbook_name}', playbook_name=self.playbook_name)
        if incident_id == -1:
            return 1

        work_plan_link = self.base_link_to_workplan + str(incident_id)
        if self.should_wait:
            print(f'Waiting for the playbook to finish running.. \n'
                  f'To see the playbook run in real-time please go to : {work_plan_link}',
                  LOG_COLORS.GREEN)

            elasped_time = 0
            start_time = time.time()

            while elasped_time < self.timeout:
                playbook_results = self.get_playbook_results_dict(incident_id)
                if playbook_results["state"] == "inprogress":
                    time.sleep(10)
                    elasped_time = int(time.time() - start_time)
                else:   # the playbook has finished running
                    break

            # Ended the loop because of timeout
            if elasped_time >= self.timeout:
                print_error(f'The command had timed out while the playbook is in progress.\n'
                            f'To keep tracking the playbook please go to : {work_plan_link}')
            else:
                if playbook_results["state"] == "failed":
                    print_error("The playbook finished running with status: FAILED")
                else:
                    print_color("The playbook finished running with status: COMPLETED", LOG_COLORS.GREEN)

        # The command does not wait for the playbook to finish running
        else:
            print(f'To see results please go to : {work_plan_link}')

        return 0

    def create_incident_with_playbook(self, incident_name, playbook_name):
        # type: (str, str) -> int
        """Create an incident in Demisto with the given incident_name and the given playbook_id

        Args:
            incident_name (str): The name of the incident
            playbook_name (str): The id of the playbook

        Returns:
            int. The new incident's ID. Returns 1 in a case of creation error.
        """

        incident_request = self.create_incident_request(playbook_name, incident_name)
        print_error(str(type(incident_request)))
        try:
            response = self.demisto_client.create_incident(create_incident_request=incident_request)
        except RuntimeError as err:
            print_error(str(err))
            return -1
        except ApiException:
            print_error(f'Failed to create incident with playbook id : "{playbook_name}", '
                        'possible reasons are:\n'
                        '1. This playbook id does not exist \n'
                        '2. Schema problems in the playbook \n'
                        '3. Unauthorized api key')
            return -1

        print_color(f'The playbook: {self.playbook_name} was triggered successfully.', LOG_COLORS.GREEN)
        return response.id

    def get_playbook_results_dict(self, inc_id):
        playbook_results = self.demisto_client.generic_request(method='GET', path=f'/inv-playbook/{inc_id}')
        return eval(playbook_results[0])

    def create_incident_request(self, playbook_name, incident_name):
        """

        Args:
            playbook_name:
            incident_name:

        Returns:

        """
        create_incident_request = demisto_client.demisto_api.CreateIncidentRequest()
        create_incident_request.create_investigation = True
        create_incident_request.playbook_id = playbook_name
        create_incident_request.name = incident_name
        return create_incident_request
