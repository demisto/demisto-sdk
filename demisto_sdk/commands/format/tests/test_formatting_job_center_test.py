import os

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    FileType,
)
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.format.format_constants import (
    SCHEMAS_PATH,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_agentix import GenericAgentixFormat
from TestSuite.test_tools import ChangeCWD

JOB_CENTER_SCHEMA_PATH = os.path.normpath(
    os.path.join(
        __file__, "..", "..", "..", "common", SCHEMAS_PATH, f"{FileType.JOB_CENTER}.yml"
    )
)


def test_format_job_center_round_trip(repo):
    """
    Given
            A JobCenter file with a non-default commonfields.version and an unknown key.
    When
            Running GenericAgentixFormat (the 'jobcenter' formatter) on it.
    Then
            Ensure commonfields.id is kept and commonfields.version is reset to -1.
            Ensure metadata and triggerSpec are kept as-is.
            Ensure the unknown key is removed, and fromversion stays 8.10.0.
    """
    pack = repo.create_pack()
    with ChangeCWD(repo.path):
        job_center = pack.create_job_center("jobcenter-followup")
        data_before = get_file(job_center.path)
        data_before["commonfields"]["version"] = 3
        data_before["unknownKey"] = "x"
        job_center.write_dict(data_before)

        formatter = GenericAgentixFormat(
            input=job_center.path,
            path=JOB_CENTER_SCHEMA_PATH,
            from_version=FILETYPE_TO_DEFAULT_FROMVERSION[FileType.JOB_CENTER],
        )
        assert formatter.run_format() == SUCCESS_RETURN_CODE

        data_after = get_file(job_center.path, clear_cache=True)

    assert data_after["commonfields"] == {"id": "job-case-followup", "version": -1}
    assert data_after["metadata"] == {
        "agent_id": "followup-agent",
        "prompt_id": "followup-prompt",
    }
    assert data_after["triggerSpec"] == {"intervalMinutes": 30, "count": 6}
    assert "unknownKey" not in data_after
    assert data_after["fromversion"] == "8.10.0"
