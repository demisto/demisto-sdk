import os

from demisto_client.demisto_api.rest import ApiException

from demisto_sdk.commands.common.clients import get_client_from_server_type
from demisto_sdk.commands.common.constants import (
    DEMISTO_BASE_URL,
    InvestigationPlaybookState,
)
from demisto_sdk.commands.common.logger import logger


class PlaybookRunner:
    """PlaybookRunner is a class that's designed to run a playbook in a given Demisto instance.

    Attributes:
        playbook_id (str): the ID of the playbook to run
        should_wait (bool): whether to wait until the playbook run is completed or not.
        timeout (int): timeout for the command. The playbook will continue to run in Demisto
        instance_api_client (XsoarClient): Demisto-SDK client object.
    """

    def __init__(
        self,
        playbook_id: str,
        url: str,
        wait: bool,
        timeout: int,
        insecure: bool = False,
    ):
        self.playbook_id = playbook_id
        self.should_wait = wait
        self.timeout = timeout
        verify = (
            (not insecure) if insecure else None
        )  # we set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        # if url parameter is not provided, demisto_client will search the DEMISTO_BASE_URL env variable

        self.instance_api_client = get_client_from_server_type(
            url or os.getenv(DEMISTO_BASE_URL), verify_ssl=verify
        )

    def run_playbook(self) -> int:
        """Run a playbook in Demisto.

        Returns:
            int. 0 in success, 1 in a failure.
        """
        # create an incident with the given playbook
        try:
            incident = self.instance_api_client.create_incident(
                name=f"incident-test-{self.playbook_id}-playbook",
                attached_playbook_id=self.playbook_id,
            )
        except ApiException as error:
            logger.error(
                f"Could not create incident in {self.instance_api_client.base_url} to test playbook {self.playbook_id}, error\n{error})"
            )
            return 1

        logger.info(
            f"<green>The playbook: {self.playbook_id} was triggered successfully.</green>"
        )

        incident_id = incident.id
        work_plan_link = self.instance_api_client.get_incident_work_plan_url(
            incident_id
        )

        if self.should_wait:
            logger.info(
                f"Waiting for the playbook to finish running.. \n"
                f"To see the playbook run in real-time, visit: {work_plan_link}"
            )
            try:
                playbook_state_raw_response = (
                    self.instance_api_client.poll_playbook_state(
                        incident_id,
                        expected_states=(
                            InvestigationPlaybookState.COMPLETED,
                            InvestigationPlaybookState.FAILED,
                        ),
                        timeout=self.timeout,
                    )
                )
            except RuntimeError:
                logger.error(
                    f"playbook {self.playbook_id} could not complete in {self.timeout} seconds"
                )
                return 1

            playbook_state = playbook_state_raw_response.get("state")
            if playbook_state == InvestigationPlaybookState.FAILED:
                logger.error(
                    f"<red>The playbook finished running with status: {InvestigationPlaybookState.FAILED}"
                )
            else:
                logger.info(
                    f"<green>The playbook {self.playbook_id} has completed its run successfully</green>"
                )

        else:
            logger.info(
                f"<green>playbook execution results can be found in {work_plan_link}</green>"
            )

        return 0
