from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from pydantic import ValidationError

from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.content_graph.strict_objects.job_center import (
    StrictJobCenter,
)

VALID_JOB_PATH = Path(__file__).parents[1] / "tests" / "test_data" / "job_center.yml"


def valid_job() -> Dict[str, Any]:
    """Return a fresh copy of a valid Job Center job."""
    with open(VALID_JOB_PATH) as f:
        return deepcopy(dict(yaml.load(f)))


def build(
    common_fields: Optional[Dict[str, Any]] = None, **overrides: Any
) -> Dict[str, Any]:
    """Return a valid job with overrides; a value of ``...`` removes the key.

    ``overrides`` apply to the top level, ``common_fields`` to ``commonfields``.
    """
    data = valid_job()
    for target, changes in (
        (data["commonfields"], common_fields or {}),
        (data, overrides),
    ):
        for key, value in changes.items():
            if value is ...:
                target.pop(key, None)
            else:
                target[key] = value
    return data


def parse(data: Dict[str, Any]) -> None:
    """Instantiate the strict model (raises ``ValidationError`` when invalid)."""
    StrictJobCenter(**data)  # type:ignore[operator]


class TestStrictJobCenterValid:
    def test_valid_sample(self):
        """
        Given:
            - The valid Job Center sample.
        When:
            - Parsing it with StrictJobCenter.
        Then:
            - No error is raised.
        """
        parse(valid_job())

    def test_onetime_without_trigger_spec(self):
        """
        Given:
            - A onetime job without triggerSpec.
        When:
            - Parsing it with StrictJobCenter.
        Then:
            - No error is raised (triggerSpec is optional for onetime).
        """
        parse(build(triggerType="onetime", triggerSpec=...))

    def test_minimal_job_without_optional_fields(self):
        """
        Given:
            - An interval job without entity fields, status, uniquenessKey and assignee
              (queuePolicy kept, since it is required for interval jobs).
        When:
            - Parsing it with StrictJobCenter.
        Then:
            - No error is raised.
        """
        parse(
            build(
                entityType=...,
                entityId=...,
                status=...,
                uniquenessKey=...,
                assignee=...,
            )
        )

    def test_onetime_without_queue_policy(self):
        """
        Given:
            - A onetime job without queuePolicy (and without triggerSpec).
        When:
            - Parsing it with StrictJobCenter.
        Then:
            - No error is raised (queuePolicy is only required for interval jobs).
        """
        parse(build(triggerType="onetime", triggerSpec=..., queuePolicy=...))

    def test_commonfields_id_and_version(self):
        """
        Given:
            - The valid Job Center sample, which carries id and version under commonfields.
        When:
            - Parsing it with StrictJobCenter.
        Then:
            - No error is raised, and id/version are read from commonfields.
        """
        parsed = StrictJobCenter(**valid_job())  # type:ignore[operator]
        assert parsed.common_fields.id == "job-case-followup"
        assert parsed.common_fields.version == -1

    def test_valid_sample_includes_queue_policy(self):
        """
        Given:
            - The valid interval Job Center sample.
        When:
            - Reading its triggerType and queuePolicy.
        Then:
            - It is an interval job carrying a queuePolicy (guards fixture drift).
        """
        data = valid_job()
        assert data["triggerType"] == "interval"
        assert data["queuePolicy"] == "skip"


def test_top_level_id_and_version_are_rejected():
    """
    Given:
        - A job carrying its id/version at the top level instead of under commonfields.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A ValidationError is raised for the missing commonfields and for the
          top-level id/version, which are unknown keys.
    """
    data = build(commonfields=..., id="job-case-followup", version=-1)
    with pytest.raises(ValidationError) as exc_info:
        parse(data)
    errors = {(error["loc"], error["type"]) for error in exc_info.value.errors()}
    assert (("commonfields",), "value_error.missing") in errors
    assert (("id",), "value_error.extra") in errors
    assert (("version",), "value_error.extra") in errors


def test_interval_without_queue_policy():
    """
    Given:
        - An interval job without a queuePolicy key.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A ValidationError is raised with the 'queuePolicy is required' message.
    """
    with pytest.raises(
        ValidationError,
        match="queuePolicy is required when triggerType is 'interval'",
    ):
        parse(build(queuePolicy=...))


@pytest.mark.parametrize(
    "queue_policy", [pytest.param(None, id="null"), pytest.param("", id="empty")]
)
def test_interval_with_null_or_empty_queue_policy(queue_policy: Any):
    """
    Given:
        - An interval job whose queuePolicy is null or an empty string.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A ValidationError is raised (null by the base no-None-values rule, empty
          string by the queuePolicy enum check).
    """
    with pytest.raises(ValidationError):
        parse(build(queuePolicy=queue_policy))


@pytest.mark.parametrize(
    "unknown_key",
    [
        pytest.param("someFutureField", id="unknown field"),
        pytest.param("triggerSpecs", id="typo of triggerSpec"),
    ],
)
def test_unknown_top_level_field_is_rejected(unknown_key: str):
    """
    Given:
        - A job with an unknown top-level key.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A ValidationError (the ST110 source) reports the extra field.
    """
    with pytest.raises(ValidationError) as exc_info:
        parse(build(**{unknown_key: "x"}))
    assert {
        "loc": (unknown_key,),
        "msg": "extra fields not permitted",
        "type": "value_error.extra",
    } in exc_info.value.errors()


def test_unknown_commonfields_key_is_rejected():
    """
    Given:
        - A job with an unknown key under commonfields.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A ValidationError reports the extra field.
    """
    with pytest.raises(ValidationError, match="extra fields not permitted"):
        parse(build(common_fields={"unknownKey": "x"}))


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"jobName": " Case"}, id="jobName leading space"),
        pytest.param({"jobName": "Case "}, id="jobName trailing space"),
        pytest.param({"jobName": "a" * 129}, id="jobName too long"),
        pytest.param({"jobName": "Case/Followup"}, id="jobName illegal char"),
        pytest.param({"jobName": ""}, id="jobName empty"),
        pytest.param({"jobName": ...}, id="jobName missing"),
        pytest.param({"jobType": "agent_to_case"}, id="unknown jobType"),
        pytest.param({"jobType": ...}, id="jobType missing"),
        pytest.param({"metadata": {"prompt_id": "p"}}, id="metadata missing agent_id"),
        pytest.param({"metadata": {"agent_id": "a"}}, id="metadata missing prompt_id"),
        pytest.param(
            {"metadata": {"agent_id": "", "prompt_id": "p"}},
            id="metadata empty agent_id",
        ),
        pytest.param({"metadata": ...}, id="metadata missing"),
        pytest.param({"entityId": ...}, id="entityType without entityId"),
        pytest.param({"entityType": ...}, id="entityId without entityType"),
        pytest.param({"entityType": "issue"}, id="entityType not case"),
        pytest.param({"triggerSpec": ...}, id="interval without triggerSpec"),
        pytest.param({"triggerType": "cron"}, id="unknown triggerType"),
        pytest.param({"triggerType": ...}, id="triggerType missing"),
        pytest.param(
            {"triggerSpec": {"intervalMinutes": 5, "count": 6}}, id="intervalMinutes 5"
        ),
        pytest.param(
            {"triggerSpec": {"intervalMinutes": 121, "count": 6}},
            id="intervalMinutes 121",
        ),
        pytest.param(
            {"triggerSpec": {"intervalMinutes": "30", "count": 6}},
            id="intervalMinutes not int",
        ),
        pytest.param({"triggerSpec": {"count": 6}}, id="intervalMinutes missing"),
        pytest.param(
            {"triggerSpec": {"intervalMinutes": 30, "count": 0}}, id="count 0"
        ),
        pytest.param(
            {"triggerSpec": {"intervalMinutes": 30, "count": 13}}, id="count 13"
        ),
        pytest.param({"triggerSpec": {"intervalMinutes": 30}}, id="count missing"),
        pytest.param({"status": "RUNNING"}, id="bad status"),
        pytest.param({"queuePolicy": "drop"}, id="bad queuePolicy"),
        pytest.param({"uniquenessKey": ""}, id="uniquenessKey empty"),
        pytest.param({"uniquenessKey": "k" * 257}, id="uniquenessKey 257 chars"),
        pytest.param({"name": ...}, id="name missing"),
        pytest.param({"commonfields": ...}, id="commonfields missing"),
        pytest.param({"commonfields": "x"}, id="commonfields not a mapping"),
        pytest.param({"system": "maybe"}, id="system not bool"),
        # RE2 parity for jobName
        pytest.param({"jobName": "Case Followup\n"}, id="jobName trailing newline"),
        pytest.param({"jobName": "a\vb"}, id="jobName vertical tab"),
        pytest.param({"jobName": "a\u00a0b"}, id="jobName non-breaking space"),
        pytest.param({"entityType": "case", "entityId": ""}, id="entityId empty"),
        pytest.param({"entityType": "", "entityId": "x"}, id="entityType empty"),
        pytest.param(
            {"metadata": {"agent_id": 5, "prompt_id": "p"}}, id="metadata agent_id int"
        ),
        pytest.param(
            {"metadata": {"agent_id": "a", "prompt_id": 9}}, id="metadata prompt_id int"
        ),
        pytest.param({"metadata": ["a"]}, id="metadata not a mapping"),
        pytest.param({"triggerSpec": "soon"}, id="interval triggerSpec not a mapping"),
    ],
)
def test_invalid_job_center(overrides: Dict[str, Any]):
    """
    Given:
        - A Job Center job violating one of the server-side rules.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A pydantic ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        parse(build(**overrides))


@pytest.mark.parametrize(
    "common_fields, expected_message",
    [
        pytest.param({"id": ""}, "commonfields.id must be", id="empty id"),
        pytest.param({"id": "   "}, "commonfields.id must be", id="whitespace-only id"),
        pytest.param({"id": ...}, "commonfields.id must be", id="id missing"),
        pytest.param({"version": ...}, "field required", id="version missing"),
        pytest.param(
            {"version": "latest"}, "not a valid integer", id="version not int"
        ),
    ],
)
def test_invalid_job_center_commonfields(
    common_fields: Dict[str, Any], expected_message: str
):
    """
    Given:
        - A Job Center job with an invalid or missing commonfields.id/version.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A ValidationError located under commonfields is raised.
    """
    with pytest.raises(ValidationError) as exc_info:
        parse(build(common_fields=common_fields))
    assert all(error["loc"][0] == "commonfields" for error in exc_info.value.errors())
    assert expected_message in str(exc_info.value)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"jobName": "a" * 128}, id="jobName 128 chars"),
        pytest.param({"jobName": "x"}, id="jobName single char"),
        pytest.param({"jobName": "Job (v1) [a].b_c-d"}, id="jobName allowed chars"),
        pytest.param({"jobName": "a\tb\nc\rd\fe"}, id="jobName inner ASCII whitespace"),
        pytest.param(
            {"triggerSpec": {"intervalMinutes": 10, "count": 1}}, id="interval lower"
        ),
        pytest.param(
            {"triggerSpec": {"intervalMinutes": 120, "count": 12}}, id="interval upper"
        ),
        pytest.param({"uniquenessKey": "k" * 256}, id="uniquenessKey 256 chars"),
        pytest.param({"queuePolicy": "cancel_prev"}, id="queuePolicy cancel_prev"),
        pytest.param({"queuePolicy": "concurrent"}, id="queuePolicy concurrent"),
        pytest.param({"status": "DONE_MANUALLY"}, id="status DONE_MANUALLY"),
        pytest.param(
            {"triggerType": "onetime", "triggerSpec": {"runAt": "2026-01-01"}},
            id="onetime with dict triggerSpec",
        ),
    ],
)
def test_valid_job_center_boundaries(overrides: Dict[str, Any]):
    """
    Given:
        - A Job Center job at the edge of an allowed range.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - No error is raised.
    """
    parse(build(**overrides))


@pytest.mark.parametrize(
    "field, attribute, value, expected",
    [
        pytest.param("jobName", "job_name", 123, "123", id="jobName int"),
        pytest.param("entityId", "entity_id", 1234, "1234", id="entityId int"),
        pytest.param(
            "uniquenessKey", "uniqueness_key", 42, "42", id="uniquenessKey int"
        ),
        pytest.param("assignee", "assignee", 7, "7", id="assignee int"),
    ],
)
def test_numeric_text_fields_are_coerced_to_str(
    field: str, attribute: str, value: int, expected: str
):
    """
    Given:
        - A Job Center job whose jobName, entityId, uniquenessKey or assignee is a
          YAML integer.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - No error is raised and the value is coerced to a string, consistent with
          the other strict content models.
    """
    parsed = StrictJobCenter(**build(**{field: value}))  # type:ignore[operator]
    assert getattr(parsed, attribute) == expected


def test_onetime_with_non_dict_trigger_spec():
    """
    Given:
        - A onetime job whose triggerSpec is not a dict.
    When:
        - Parsing it with StrictJobCenter.
    Then:
        - A pydantic ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        parse(build(triggerType="onetime", triggerSpec="soon"))
