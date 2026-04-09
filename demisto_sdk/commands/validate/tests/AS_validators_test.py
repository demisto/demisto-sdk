import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
    create_playbook_object,
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS101_is_valid_autonomous_trigger import (
    IsValidAutonomousTriggerValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS102_is_valid_quiet_mode_for_autonomous_playbook import (
    IsValidQuietModeForAutonomousPlaybookValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS103_is_valid_autonomous_playbook_headers import (
    IsValidAutonomousPlaybookHeadersValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS104_playbook_must_have_adopted_field import (
    PlaybookMustHaveAdoptedFieldValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS105_no_is_silent_in_autonomous_pack import (
    NoIsSilentInAutonomousPackValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS106_warn_quiet_mode_on_display_label_task import (
    WarnQuietModeOnDisplayLabelTaskValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS107_subplaybook_prefix_consistency import (
    SubplaybookPrefixConsistencyValidator,
)
from demisto_sdk.commands.validate.validators.AS_validators.AS108_subplaybook_must_be_internal import (
    SubplaybookMustBeInternalValidator,
)


@pytest.mark.parametrize(
    "grouping_element, is_auto_enabled, managed, source, expected_result_len",
    [
        # Valid cases - should pass
        (
            "Cortex Autonomous Rules",
            True,
            True,
            "autonomous",
            0,
        ),  # Autonomous pack with all correct fields
        (
            "Other Grouping",
            False,
            False,
            None,
            0,
        ),  # Non-autonomous pack, any fields are fine
        (
            "Other Grouping",
            True,
            True,
            "other",
            0,
        ),  # Non-autonomous pack (wrong source)
        (None, False, False, None, 0),  # Non-autonomous pack, no fields set
        (
            "Cortex Autonomous Rules",
            True,
            False,
            "autonomous",
            0,
        ),  # Non-autonomous pack (missing managed)
        (
            "Cortex Autonomous Rules",
            False,
            True,
            "other",
            0,
        ),  # Non-autonomous pack (wrong source)
        # Invalid cases - should fail (autonomous pack without correct fields)
        (
            "Other Grouping",
            True,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with wrong grouping
        (
            "Cortex Autonomous Rules",
            False,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with is_auto_enabled=False
        (None, True, True, "autonomous", 1),  # Autonomous pack with no grouping element
        (
            "",
            False,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with empty grouping and is_auto_enabled=False
        (
            "Cortex Autonomous Rules",
            None,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with is_auto_enabled missing
        (
            "Other Grouping",
            False,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with both fields wrong
        (
            None,
            None,
            True,
            "autonomous",
            1,
        ),  # Autonomous pack with both fields missing entirely
    ],
)
def test_IsValidAutonomousTriggerValidator(
    grouping_element, is_auto_enabled, managed, source, expected_result_len
):
    """
    Given:
        - Various combinations of triggers with different grouping_element and is_auto_enabled values
          and pack metadata with different managed/source values.

    When:
        - Running IsValidAutonomousTriggerValidator.obtain_invalid_content_items.

    Then:
        - Triggers in autonomous packs (managed: true AND source: 'autonomous')
          must have grouping_element: 'Cortex Autonomous Rules' AND is_auto_enabled: true.
        - Triggers in non-autonomous packs can have any values for these fields.
    """
    # Create pack with specified metadata
    pack_metadata = {}
    if managed is not None:
        pack_metadata["managed"] = managed
    if source is not None:
        pack_metadata["source"] = source

    pack = create_pack_object(
        paths=list(pack_metadata.keys()), values=list(pack_metadata.values())
    )

    # Create trigger with specified fields
    trigger_data = {}
    if grouping_element is not None:
        trigger_data["grouping_element"] = grouping_element
    if is_auto_enabled is not None:
        trigger_data["is_auto_enabled"] = is_auto_enabled

    trigger = create_trigger_object(
        paths=list(trigger_data.keys()) if trigger_data else None,
        values=list(trigger_data.values()) if trigger_data else None,
    )

    # Manually set the pack relationship
    trigger.pack = pack

    # Run validation
    invalid_content_items = (
        IsValidAutonomousTriggerValidator().obtain_invalid_content_items([trigger])
    )

    assert len(invalid_content_items) == expected_result_len


def test_IsValidAutonomousTriggerValidator_fix():
    """
    Given:
        - A trigger in an autonomous pack (managed: true, source: 'autonomous')
          but without the correct grouping_element and is_auto_enabled fields.

    When:
        - Running the fix method.

    Then:
        - The trigger's grouping_element should be set to 'Cortex Autonomous Rules'
          and is_auto_enabled should be set to true.
    """
    # Create autonomous pack
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "autonomous"],
    )

    # Create trigger without correct fields
    trigger = create_trigger_object(
        paths=["grouping_element", "is_auto_enabled"],
        values=["Other Grouping", False],
    )
    trigger.pack = pack

    # Verify it's invalid before fix
    validator = IsValidAutonomousTriggerValidator()
    invalid_items = validator.obtain_invalid_content_items([trigger])
    assert len(invalid_items) == 1

    # Apply fix
    fix_result = validator.fix(trigger)

    # Verify fix was applied
    assert fix_result.message == validator.fix_message
    assert trigger.grouping_element == "Cortex Autonomous Rules"
    assert trigger.is_auto_enabled is True

    # Verify it's now valid
    invalid_items_after_fix = validator.obtain_invalid_content_items([trigger])
    assert len(invalid_items_after_fix) == 0


def _make_tasks(task_overrides):
    """Build a minimal tasks dict.

    Each entry in task_overrides is a tuple of:
        (id, type, quietmode, inner_displayLabel)
    where ``inner_displayLabel`` is set inside the nested ``task:`` sub-object
    (the canonical location for displayLabel in the playbook YAML format).
    The trailing element is optional (default ``None``).
    """
    tasks = {}
    for override in task_overrides:
        tid, ttype, qm = override[0], override[1], override[2]
        inner_dl = override[3] if len(override) > 3 else None

        inner_task: dict = {"id": f"taskid-{tid}", "version": -1, "name": f"task-{tid}"}
        if inner_dl is not None:
            inner_task["displayLabel"] = inner_dl

        entry = {
            "id": tid,
            "taskid": f"taskid-{tid}",
            "type": ttype,
            "task": inner_task,
        }
        if qm is not None:
            entry["quietmode"] = qm
        tasks[tid] = entry
    return tasks


@pytest.mark.parametrize(
    "managed, source, task_overrides, expected_errors",
    [
        # Non-autonomous pack — no errors regardless of quietmode
        (False, "other", [("0", "start", 0), ("1", "regular", 0)], 0),
        # Autonomous pack, task without displayLabel has quietmode=1 — valid
        (True, "autonomous", [("0", "start", 0), ("1", "regular", 1)], 0),
        # Autonomous pack, task has displayLabel inside inner task{} — valid
        (
            True,
            "autonomous",
            [("0", "start", 0), ("1", "regular", 0, "Label")],
            0,
        ),
        # Autonomous pack, task without displayLabel has quietmode=0 — error
        (True, "autonomous", [("0", "start", 0), ("1", "regular", 0)], 1),
        # Autonomous pack, task without displayLabel has quietmode=None — error
        (
            True,
            "autonomous",
            [("0", "start", 0), ("1", "regular", None)],
            1,
        ),
        # Autonomous pack, only start/title tasks with quietmode=0 — no errors (excluded)
        (True, "autonomous", [("0", "start", 0), ("1", "title", 0)], 0),
    ],
)
def test_IsValidQuietModeForAutonomousPlaybookValidator(
    managed, source, task_overrides, expected_errors
):
    """
    Given:
        - Playbooks with various task configurations in autonomous/non-autonomous packs.
    When:
        - Running IsValidQuietModeForAutonomousPlaybookValidator.obtain_invalid_content_items.
    Then:
        - Tasks without displayLabel in autonomous packs must have quietmode=1.
    """
    pack = create_pack_object(paths=["managed", "source"], values=[managed, source])
    playbook = create_playbook_object(
        paths=["tasks"], values=[_make_tasks(task_overrides)]
    )
    playbook.pack = pack

    results = (
        IsValidQuietModeForAutonomousPlaybookValidator().obtain_invalid_content_items(
            [playbook]
        )
    )
    assert len(results) == expected_errors


def test_IsValidQuietModeForAutonomousPlaybookValidator_fix():
    """
    Given:
        - A playbook in an autonomous pack with a regular task (quietmode=0, no displayLabel).
    When:
        - Running the fix method.
    Then:
        - The task's quietmode is set to 1; start task remains unchanged.
    """
    pack = create_pack_object(paths=["managed", "source"], values=[True, "autonomous"])
    tasks = _make_tasks([("0", "start", 0, None), ("1", "regular", 0, None)])
    playbook = create_playbook_object(paths=["tasks"], values=[tasks])
    playbook.pack = pack

    validator = IsValidQuietModeForAutonomousPlaybookValidator()
    assert len(validator.obtain_invalid_content_items([playbook])) == 1

    fix_result = validator.fix(playbook)
    assert fix_result.message == validator.fix_message
    assert playbook.tasks["1"].quietmode == 1
    assert playbook.tasks["0"].quietmode == 0
    assert len(validator.obtain_invalid_content_items([playbook])) == 0


def test_IsValidQuietModeForAutonomousPlaybookValidator_inner_task_display_label():
    """
    Given:
        - A playbook in an autonomous pack where a regular task has quietmode=0 but
          its displayLabel is set inside the inner ``task:`` sub-object (not at the
          top-level TaskConfig).  This is the real-world format that triggered the bug.
    When:
        - Running IsValidQuietModeForAutonomousPlaybookValidator.obtain_invalid_content_items.
    Then:
        - The task must NOT be flagged as invalid because it has a displayLabel
          (even though it is on the inner task object rather than the outer TaskConfig).
    """
    pack = create_pack_object(paths=["managed", "source"], values=[True, "autonomous"])
    # 4-tuple: (id, type, quietmode, inner_displayLabel)
    tasks = _make_tasks(
        [
            ("0", "start", 0),
            ("1", "regular", 0, "Action confirmed on a high-risk host."),
        ]
    )
    playbook = create_playbook_object(paths=["tasks"], values=[tasks])
    playbook.pack = pack

    validator = IsValidQuietModeForAutonomousPlaybookValidator()
    results = validator.obtain_invalid_content_items([playbook])
    assert (
        len(results) == 0
    ), "Task with displayLabel inside inner task{} should not be flagged as invalid"


def _make_header_tasks(sections, starttaskid="0"):
    """Build a playbook task graph with title tasks for the given sections.

    Args:
        sections: list of (task_id, name, description) for title tasks.
                  Non-title tasks are auto-generated to link them.
    Returns:
        tasks_dict
    """
    tasks = {}
    # Build chain: starttaskid -> section[0] -> section[1] -> ...
    task_ids = [starttaskid] + [s[0] for s in sections]
    for i, (tid, name, desc) in enumerate(sections):
        prev_id = task_ids[i]
        # Link previous task to this one
        if prev_id not in tasks:
            tasks[prev_id] = {
                "id": prev_id,
                "taskid": f"taskid-{prev_id}",
                "type": "start" if prev_id == starttaskid else "regular",
                "task": {
                    "id": f"taskid-{prev_id}",
                    "version": -1,
                    "name": f"task-{prev_id}",
                },
                "nexttasks": {"#none#": [tid]},
            }
        else:
            tasks[prev_id].setdefault("nexttasks", {})["#none#"] = [tid]

        # Title task
        task_entry = {
            "id": tid,
            "taskid": f"taskid-{tid}",
            "type": "title",
            "task": {
                "id": f"taskid-{tid}",
                "version": -1,
                "name": name,
            },
            "nexttasks": {},
        }
        if desc is not None:
            task_entry["task"]["description"] = desc
        tasks[tid] = task_entry

    return tasks


@pytest.mark.parametrize(
    "managed, source, sections, expected_errors",
    [
        # 1. Non-autonomous pack — no errors regardless of sections
        (
            False,
            "other",
            [
                ("1", "Data Collection", "desc1"),
                ("2", "Investigation", "desc2"),
            ],
            0,
        ),
        # 2. All 6 sections with descriptions in correct order — valid
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", "Collect data"),
                ("2", "Early Containment", "Contain early"),
                ("3", "Investigation", "Investigate"),
                ("4", "Verdict", "Determine verdict"),
                ("5", "Remediation", "Remediate"),
                ("6", "Playbook Completed", "Playbook done"),
            ],
            0,
        ),
        # 3. 5 mandatory sections (optional omitted) in correct order — valid
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", "Collect data"),
                ("2", "Investigation", "Investigate"),
                ("3", "Verdict", "Determine verdict"),
                ("4", "Remediation", "Remediate"),
                ("5", "Playbook Completed", "Playbook done"),
            ],
            0,
        ),
        # 4. Missing mandatory section "Verdict"
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", "Collect data"),
                ("2", "Investigation", "Investigate"),
                ("3", "Remediation", "Remediate"),
                ("4", "Playbook Completed", "Playbook done"),
            ],
            1,
        ),
        # 5. Unknown section name "Custom Section"
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", "Collect data"),
                ("2", "Custom Section", "Custom desc"),
                ("3", "Investigation", "Investigate"),
                ("4", "Verdict", "Determine verdict"),
                ("5", "Remediation", "Remediate"),
                ("6", "Playbook Completed", "Playbook done"),
            ],
            1,
        ),
        # 6. Empty description on a section
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", ""),
                ("2", "Investigation", "Investigate"),
                ("3", "Verdict", "Determine verdict"),
                ("4", "Remediation", "Remediate"),
                ("5", "Playbook Completed", "Playbook done"),
            ],
            1,
        ),
        # 7. None description on a section
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", None),
                ("2", "Investigation", "Investigate"),
                ("3", "Verdict", "Determine verdict"),
                ("4", "Remediation", "Remediate"),
                ("5", "Playbook Completed", "Playbook done"),
            ],
            1,
        ),
        # 8. Wrong ordering — Investigation before Data Collection
        (
            True,
            "autonomous",
            [
                ("1", "Investigation", "Investigate"),
                ("2", "Data Collection", "Collect data"),
                ("3", "Verdict", "Determine verdict"),
                ("4", "Remediation", "Remediate"),
                ("5", "Playbook Completed", "Playbook done"),
            ],
            1,
        ),
        # 9. Multiple errors: missing section + empty description
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", ""),
                ("2", "Investigation", "Investigate"),
                ("3", "Remediation", "Remediate"),
                ("4", "Playbook Completed", "Playbook done"),
            ],
            1,
        ),
        # 10. No title tasks at all — all mandatory missing
        (
            True,
            "autonomous",
            [],
            1,
        ),
        # 11. "Playbook Completed" appears twice (duplicatable) — valid
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", "Collect data"),
                ("2", "Investigation", "Investigate"),
                ("3", "Verdict", "Determine verdict"),
                ("4", "Remediation", "Remediate"),
                ("5", "Playbook Completed", "Branch A done"),
                ("6", "Playbook Completed", "Branch B done"),
            ],
            0,
        ),
        # 12. Missing "Playbook Completed" — invalid
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", "Collect data"),
                ("2", "Investigation", "Investigate"),
                ("3", "Verdict", "Determine verdict"),
                ("4", "Remediation", "Remediate"),
            ],
            1,
        ),
        # 13. "Playbook Completed" with empty description — invalid
        (
            True,
            "autonomous",
            [
                ("1", "Data Collection", "Collect data"),
                ("2", "Investigation", "Investigate"),
                ("3", "Verdict", "Determine verdict"),
                ("4", "Remediation", "Remediate"),
                ("5", "Playbook Completed", ""),
            ],
            1,
        ),
    ],
)
def test_IsValidAutonomousPlaybookHeadersValidator(
    managed, source, sections, expected_errors
):
    """
    Given:
        - Playbooks with various section header configurations in autonomous/non-autonomous packs.
    When:
        - Running IsValidAutonomousPlaybookHeadersValidator.obtain_invalid_content_items.
    Then:
        - Autonomous playbooks must have correct section headers with valid names,
          non-empty descriptions, and proper ordering.
    """
    pack = create_pack_object(paths=["managed", "source"], values=[managed, source])
    header_tasks = _make_header_tasks(sections)
    playbook = create_playbook_object(
        paths=["starttaskid", "tasks"], values=["0", header_tasks]
    )
    playbook.pack = pack

    results = IsValidAutonomousPlaybookHeadersValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == expected_errors


def test_IsValidAutonomousPlaybookHeadersValidator_ignores_subsections():
    """
    Given:
        - An autonomous playbook with all required section headers in correct order,
          plus an extra title task that has ``isSubSection: true`` inside its inner
          ``task:`` object (e.g. a sub-section like 'User Logoff').
    When:
        - Running IsValidAutonomousPlaybookHeadersValidator.obtain_invalid_content_items.
    Then:
        - The sub-section title task must be ignored; the playbook must be valid (0 errors).
    """
    pack = create_pack_object(paths=["managed", "source"], values=[True, "autonomous"])

    # Build the standard valid sections (including mandatory "Playbook Completed")
    sections = [
        ("1", "Data Collection", "Collect data"),
        ("2", "Investigation", "Investigate"),
        ("3", "Verdict", "Determine verdict"),
        ("4", "Remediation", "Remediate"),
        ("5", "Playbook Completed", "Playbook done"),
    ]
    header_tasks = _make_header_tasks(sections)

    # Inject a sub-section title task (isSubSection: true inside task{})
    header_tasks["404"] = {
        "id": "404",
        "taskid": "taskid-404",
        "type": "title",
        "task": {
            "id": "taskid-404",
            "version": -1,
            "name": "User Logoff",
            "type": "title",
            "iscommand": False,
            "brand": "",
            "description": "",
            "isSubSection": True,
        },
        "nexttasks": {},
    }
    # Link it from the last section so it's reachable in BFS
    header_tasks["5"]["nexttasks"] = {"#none#": ["404"]}

    playbook = create_playbook_object(
        paths=["starttaskid", "tasks"], values=["0", header_tasks]
    )
    playbook.pack = pack

    results = IsValidAutonomousPlaybookHeadersValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert (
        len(results) == 0
    ), "Sub-section title tasks (isSubSection=true) should be ignored by AS103"


@pytest.mark.parametrize(
    "managed, source, adopted, expected_errors",
    [
        # Non-autonomous pack — no errors regardless of adopted value
        (False, "other", None, 0),
        (False, "other", False, 0),
        (False, "other", True, 0),
        # Autonomous pack with adopted=True — valid
        (True, "autonomous", True, 0),
        # Autonomous pack with adopted=False — invalid
        (True, "autonomous", False, 1),
        # Autonomous pack with adopted=None (missing) — invalid
        (True, "autonomous", None, 1),
        # Non-autonomous pack (wrong source) — no errors
        (True, "other", None, 0),
        # Non-autonomous pack (managed=False) — no errors
        (False, "autonomous", None, 0),
    ],
)
def test_PlaybookMustHaveAdoptedFieldValidator(
    managed, source, adopted, expected_errors
):
    """
    Given:
        - Playbooks with various 'adopted' field values in autonomous/non-autonomous packs.
    When:
        - Running PlaybookMustHaveAdoptedFieldValidator.obtain_invalid_content_items.
    Then:
        - Playbooks in autonomous packs (managed: true AND source: 'autonomous')
          must have adopted: true.
        - Playbooks in non-autonomous packs can have any value for 'adopted'.
    """
    pack_metadata = {}
    if managed is not None:
        pack_metadata["managed"] = managed
    if source is not None:
        pack_metadata["source"] = source

    pack = create_pack_object(
        paths=list(pack_metadata.keys()), values=list(pack_metadata.values())
    )

    paths = []
    values = []
    if adopted is not None:
        paths.append("adopted")
        values.append(adopted)

    playbook = create_playbook_object(paths=paths or None, values=values or None)
    playbook.pack = pack

    results = PlaybookMustHaveAdoptedFieldValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == expected_errors


def test_PlaybookMustHaveAdoptedFieldValidator_fix():
    """
    Given:
        - A playbook in an autonomous pack (managed: true, source: 'autonomous')
          without the 'adopted' field set.
    When:
        - Running the fix method.
    Then:
        - The playbook's 'adopted' field should be set to True.
        - The playbook should then pass validation.
    """
    pack = create_pack_object(
        paths=["managed", "source"],
        values=[True, "autonomous"],
    )
    playbook = create_playbook_object()
    playbook.pack = pack

    validator = PlaybookMustHaveAdoptedFieldValidator()

    # Verify it's invalid before fix
    assert len(validator.obtain_invalid_content_items([playbook])) == 1

    # Apply fix
    fix_result = validator.fix(playbook)

    # Verify fix was applied
    assert fix_result.message == validator.fix_message
    assert playbook.adopted is True

    # Verify it's now valid
    assert len(validator.obtain_invalid_content_items([playbook])) == 0


@pytest.mark.parametrize(
    "managed, pack_source, item_is_silent, expected_result_len",
    [
        # Valid cases — should pass (no error)
        (True, "autonomous", False, 0),  # Autonomous pack, not silent
        (False, "other", True, 0),  # Non-autonomous pack, silent
        (True, "other", True, 0),  # managed=true but wrong source, silent
        (False, "autonomous", True, 0),  # source=autonomous but managed=false, silent
        # Invalid cases — should fail
        (True, "autonomous", True, 1),  # Autonomous pack + silent
    ],
)
def test_NoIsSilentInAutonomousPackValidator_playbook(
    managed, pack_source, item_is_silent, expected_result_len
):
    """
    Given:
        - Playbooks with various combinations of pack metadata (managed/source)
          and item-level isSilent field.

    When:
        - Running NoIsSilentInAutonomousPackValidator.obtain_invalid_content_items.

    Then:
        - Playbooks in autonomous packs (managed: true, source: 'autonomous') that have
          isSilent: true must be flagged as invalid.
        - Non-autonomous packs or non-silent items must not be flagged.
    """
    pack_metadata: dict = {}
    if managed is not None:
        pack_metadata["managed"] = managed
    if pack_source is not None:
        pack_metadata["source"] = pack_source

    pack = create_pack_object(
        paths=list(pack_metadata.keys()), values=list(pack_metadata.values())
    )

    playbook = create_playbook_object(paths=["issilent"], values=[item_is_silent])
    playbook.pack = pack

    results = NoIsSilentInAutonomousPackValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == expected_result_len


@pytest.mark.parametrize(
    "managed, pack_source, item_is_silent, expected_result_len",
    [
        # Valid cases — should pass (no error)
        (True, "autonomous", False, 0),  # Autonomous pack, not silent
        (False, "other", True, 0),  # Non-autonomous pack, silent
        (True, "other", True, 0),  # managed=true but wrong source, silent
        (False, "autonomous", True, 0),  # source=autonomous but managed=false, silent
        # Invalid cases — should fail
        (True, "autonomous", True, 1),  # Autonomous pack + silent
    ],
)
def test_NoIsSilentInAutonomousPackValidator_trigger(
    managed, pack_source, item_is_silent, expected_result_len
):
    """
    Given:
        - Triggers with various combinations of pack metadata (managed/source)
          and item-level issilent field.

    When:
        - Running NoIsSilentInAutonomousPackValidator.obtain_invalid_content_items.

    Then:
        - Triggers in autonomous packs (managed: true, source: 'autonomous') that have
          issilent: true must be flagged as invalid.
        - Non-autonomous packs or non-silent items must not be flagged.
    """
    pack_metadata: dict = {}
    if managed is not None:
        pack_metadata["managed"] = managed
    if pack_source is not None:
        pack_metadata["source"] = pack_source

    pack = create_pack_object(
        paths=list(pack_metadata.keys()), values=list(pack_metadata.values())
    )

    trigger = create_trigger_object(paths=["issilent"], values=[item_is_silent])
    trigger.pack = pack

    results = NoIsSilentInAutonomousPackValidator().obtain_invalid_content_items(
        [trigger]
    )
    assert len(results) == expected_result_len


def test_NoIsSilentInAutonomousPackValidator_fix_playbook():
    """
    Given:
        - A playbook in an autonomous pack (managed: true, source: 'autonomous')
          that has isSilent: true.

    When:
        - Running the fix method.

    Then:
        - The isSilent field is removed from the playbook data and is_silent is set to False.
        - The playbook is now valid (no errors).
    """
    pack = create_pack_object(paths=["managed", "source"], values=[True, "autonomous"])
    playbook = create_playbook_object(paths=["issilent"], values=[True])
    playbook.pack = pack

    validator = NoIsSilentInAutonomousPackValidator()
    assert len(validator.obtain_invalid_content_items([playbook])) == 1

    fix_result = validator.fix(playbook)
    assert fix_result.message == validator.fix_message
    assert playbook.is_silent is False
    assert "isSilent" not in playbook.data

    assert len(validator.obtain_invalid_content_items([playbook])) == 0


def test_NoIsSilentInAutonomousPackValidator_fix_trigger():
    """
    Given:
        - A trigger in an autonomous pack (managed: true, source: 'autonomous')
          that has issilent: true.

    When:
        - Running the fix method.

    Then:
        - The isSilent field is removed from the trigger data and is_silent is set to False.
        - The trigger is now valid (no errors).
    """
    pack = create_pack_object(paths=["managed", "source"], values=[True, "autonomous"])
    trigger = create_trigger_object(paths=["issilent"], values=[True])
    trigger.pack = pack

    validator = NoIsSilentInAutonomousPackValidator()
    assert len(validator.obtain_invalid_content_items([trigger])) == 1

    fix_result = validator.fix(trigger)
    assert fix_result.message == validator.fix_message
    assert trigger.is_silent is False
    assert "isSilent" not in trigger.data

    assert len(validator.obtain_invalid_content_items([trigger])) == 0


@pytest.mark.parametrize(
    "managed, source, task_overrides, expected_warnings",
    [
        # Non-autonomous pack — no warnings regardless of quietmode/displayLabel
        (False, "other", [("0", "start", 0, None), ("1", "regular", 1, "My Label")], 0),
        # Autonomous pack, task has displayLabel and quietmode=1 — warning
        (
            True,
            "autonomous",
            [("0", "start", 0, None), ("1", "regular", 1, "My Label")],
            1,
        ),
        # Autonomous pack, task has displayLabel but quietmode=0 — no warning
        (
            True,
            "autonomous",
            [("0", "start", 0, None), ("1", "regular", 0, "My Label")],
            0,
        ),
        # Autonomous pack, task has displayLabel but quietmode=None — no warning
        (
            True,
            "autonomous",
            [("0", "start", 0, None), ("1", "regular", None, "My Label")],
            0,
        ),
        # Autonomous pack, task has no displayLabel and quietmode=1 — no warning (AS102 handles this)
        (True, "autonomous", [("0", "start", 0, None), ("1", "regular", 1, None)], 0),
        # Autonomous pack, start/title tasks excluded even with displayLabel and quietmode=1
        (
            True,
            "autonomous",
            [("0", "start", 1, "Start Label"), ("1", "title", 1, "Title Label")],
            0,
        ),
        # Autonomous pack, multiple tasks with displayLabel and quietmode=1 — multiple warnings in one result
        (
            True,
            "autonomous",
            [
                ("0", "start", 0, None),
                ("1", "regular", 1, "Label One"),
                ("2", "regular", 1, "Label Two"),
            ],
            1,
        ),
    ],
)
def test_WarnQuietModeOnDisplayLabelTaskValidator(
    managed, source, task_overrides, expected_warnings
):
    """
    Given:
        - Playbooks with various task configurations in autonomous/non-autonomous packs.
    When:
        - Running WarnQuietModeOnDisplayLabelTaskValidator.obtain_invalid_content_items.
    Then:
        - Tasks with a displayLabel AND quietmode=1 in autonomous packs should raise a warning.
        - Tasks without a displayLabel, or with quietmode != 1, or in non-autonomous packs
          should not raise a warning.
        - start and title task types are always excluded.
    """
    pack = create_pack_object(paths=["managed", "source"], values=[managed, source])
    playbook = create_playbook_object(
        paths=["tasks"], values=[_make_tasks(task_overrides)]
    )
    playbook.pack = pack

    results = WarnQuietModeOnDisplayLabelTaskValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == expected_warnings


@pytest.mark.parametrize(
    "filename, object_id, name, managed, source, expected_result_len",
    [
        # Valid cases - consistent prefix usage in autonomous pack
        ("subplaybook-test", "subplaybook-test", "subplaybook-test", True, "autonomous", 0),  # All have prefix
        ("regular-playbook", "regular-playbook", "regular-playbook", True, "autonomous", 0),  # None have prefix
        ("MyPlaybook", "MyPlaybook", "MyPlaybook", True, "autonomous", 0),  # None have prefix
        # Valid cases - non-autonomous packs (should not validate)
        ("subplaybook-test", "test", "test", False, "autonomous", 0),  # Not managed
        ("subplaybook-test", "test", "test", True, "other", 0),  # Wrong source
        ("subplaybook-test", "test", "test", False, "other", 0),  # Neither managed nor autonomous
        # Invalid cases - inconsistent prefix usage in autonomous pack
        ("subplaybook-test", "test", "test", True, "autonomous", 1),  # Only filename has prefix
        ("test", "subplaybook-test", "test", True, "autonomous", 1),  # Only id has prefix
        ("test", "test", "subplaybook-test", True, "autonomous", 1),  # Only name has prefix
        ("subplaybook-test", "subplaybook-test", "test", True, "autonomous", 1),  # Filename and id have prefix, name doesn't
        ("subplaybook-test", "test", "subplaybook-test", True, "autonomous", 1),  # Filename and name have prefix, id doesn't
        ("test", "subplaybook-test", "subplaybook-test", True, "autonomous", 1),  # Id and name have prefix, filename doesn't
        # Case insensitive
        ("SubPlaybook-Test", "test", "test", True, "autonomous", 1),  # Uppercase prefix in filename
        ("test", "SUBPLAYBOOK-test", "test", True, "autonomous", 1),  # Uppercase prefix in id
    ],
)
def test_SubplaybookPrefixConsistencyValidator(
    filename, object_id, name, managed, source, expected_result_len
):
    """
    Given:
        - Playbooks with various combinations of 'subplaybook' prefix in filename, id, and name
          in autonomous and non-autonomous packs.

    When:
        - Running SubplaybookPrefixConsistencyValidator.obtain_invalid_content_items.

    Then:
        - Playbooks in autonomous packs with inconsistent prefix usage should fail.
        - Playbooks in autonomous packs with consistent prefix usage should pass.
        - Playbooks in non-autonomous packs should not be validated (always pass).
    """
    from pathlib import Path
    from unittest.mock import MagicMock

    # Create pack with specified metadata
    pack = create_pack_object(paths=["managed", "source"], values=[managed, source])

    playbook = create_playbook_object(paths=["id", "name"], values=[object_id, name])
    playbook.pack = pack

    # Mock the path to set the filename
    mock_path = MagicMock(spec=Path)
    mock_path.stem = filename
    playbook.path = mock_path

    results = SubplaybookPrefixConsistencyValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == expected_result_len


def test_SubplaybookPrefixConsistencyValidator_fix():
    """
    Given:
        - A playbook in an autonomous pack with inconsistent 'subplaybook' prefix (filename has it, id and name don't).

    When:
        - Running SubplaybookPrefixConsistencyValidator.fix.

    Then:
        - The id and name should be updated to include the 'subplaybook' prefix.
    """
    from pathlib import Path
    from unittest.mock import MagicMock

    # Create pack with autonomous metadata
    pack = create_pack_object(paths=["managed", "source"], values=[True, "autonomous"])

    playbook = create_playbook_object(paths=["id", "name"], values=["test", "test"])
    playbook.pack = pack

    # Mock the path to set the filename with subplaybook prefix
    mock_path = MagicMock(spec=Path)
    mock_path.stem = "subplaybook-test"
    playbook.path = mock_path

    # Verify it's invalid before fix
    results = SubplaybookPrefixConsistencyValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == 1

    # Apply fix
    SubplaybookPrefixConsistencyValidator().fix(playbook)

    # Verify id and name now have the prefix
    assert playbook.object_id == "subplaybook-test"
    assert playbook.name == "subplaybook-test"


@pytest.mark.parametrize(
    "filename, object_id, name, internal, managed, source, expected_result_len",
    [
        # Valid cases - subplaybooks with internal=True in autonomous pack
        ("subplaybook-test", "subplaybook-test", "subplaybook-test", True, True, "autonomous", 0),
        ("test", "subplaybook-test", "test", True, True, "autonomous", 0),  # Any field with prefix + internal=True
        ("test", "test", "subplaybook-test", True, True, "autonomous", 0),
        # Valid cases - non-subplaybooks in autonomous pack
        ("regular-playbook", "regular-playbook", "regular-playbook", False, True, "autonomous", 0),
        ("regular-playbook", "regular-playbook", "regular-playbook", True, True, "autonomous", 0),  # internal=True is fine
        # Valid cases - non-autonomous packs (should not validate)
        ("subplaybook-test", "subplaybook-test", "subplaybook-test", False, False, "autonomous", 0),  # Not managed
        ("subplaybook-test", "subplaybook-test", "subplaybook-test", False, True, "other", 0),  # Wrong source
        # Invalid cases - subplaybooks without internal=True in autonomous pack
        ("subplaybook-test", "subplaybook-test", "subplaybook-test", False, True, "autonomous", 1),
        ("subplaybook-test", "test", "test", False, True, "autonomous", 1),  # Filename has prefix
        ("test", "subplaybook-test", "test", False, True, "autonomous", 1),  # Id has prefix
        ("test", "test", "subplaybook-test", False, True, "autonomous", 1),  # Name has prefix
        # Case insensitive
        ("SubPlaybook-Test", "test", "test", False, True, "autonomous", 1),
        ("test", "SUBPLAYBOOK-test", "test", False, True, "autonomous", 1),
    ],
)
def test_SubplaybookMustBeInternalValidator(
    filename, object_id, name, internal, managed, source, expected_result_len
):
    """
    Given:
        - Playbooks with various combinations of 'subplaybook' prefix and internal field values
          in autonomous and non-autonomous packs.

    When:
        - Running SubplaybookMustBeInternalValidator.obtain_invalid_content_items.

    Then:
        - Playbooks in autonomous packs with 'subplaybook' prefix but without internal=True should fail.
        - Playbooks in autonomous packs without 'subplaybook' prefix can have any internal value.
        - Playbooks in autonomous packs with 'subplaybook' prefix and internal=True should pass.
        - Playbooks in non-autonomous packs should not be validated (always pass).
    """
    from pathlib import Path
    from unittest.mock import MagicMock

    # Create pack with specified metadata
    pack = create_pack_object(paths=["managed", "source"], values=[managed, source])

    playbook = create_playbook_object(
        paths=["id", "name", "internal"], values=[object_id, name, internal]
    )
    playbook.pack = pack

    # Mock the path to set the filename
    mock_path = MagicMock(spec=Path)
    mock_path.stem = filename
    playbook.path = mock_path

    results = SubplaybookMustBeInternalValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == expected_result_len


def test_SubplaybookMustBeInternalValidator_fix():
    """
    Given:
        - A subplaybook in an autonomous pack without internal=True.

    When:
        - Running SubplaybookMustBeInternalValidator.fix.

    Then:
        - The internal field should be set to True.
    """
    from pathlib import Path
    from unittest.mock import MagicMock

    # Create pack with autonomous metadata
    pack = create_pack_object(paths=["managed", "source"], values=[True, "autonomous"])

    playbook = create_playbook_object(
        paths=["id", "name", "internal"],
        values=["subplaybook-test", "subplaybook-test", False],
    )
    playbook.pack = pack

    # Mock the path to set the filename
    mock_path = MagicMock(spec=Path)
    mock_path.stem = "subplaybook-test"
    playbook.path = mock_path

    # Verify it's invalid before fix
    results = SubplaybookMustBeInternalValidator().obtain_invalid_content_items(
        [playbook]
    )
    assert len(results) == 1

    # Apply fix
    SubplaybookMustBeInternalValidator().fix(playbook)

    # Verify internal is now True
    assert playbook.internal is True
