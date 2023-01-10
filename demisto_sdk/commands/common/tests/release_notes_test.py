import os

import pytest

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.hook_validations.release_notes import (
    ReleaseNotesValidator,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_dict_from_file
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from TestSuite.pack import Pack


def get_validator(
    file_path="",
    modified_files=None,
    added_files=None,
    pack_name="CortexXDR",
    pack_path="Path/CortexXDR",
):
    release_notes_validator = ReleaseNotesValidator("")
    release_notes_validator.release_notes_file_path = os.path.join(
        FILES_PATH, "CortexXDR"
    )
    release_notes_validator.release_notes_path = file_path
    release_notes_validator.latest_release_notes = file_path
    release_notes_validator.modified_files = modified_files
    release_notes_validator.added_files = added_files
    release_notes_validator.pack_name = pack_name
    release_notes_validator.file_types_that_should_not_appear_in_rn = {
        FileType.TEST_SCRIPT,
        FileType.TEST_PLAYBOOK,
        FileType.README,
        FileType.RELEASE_NOTES,
        None,
    }
    release_notes_validator.ignored_errors = {}
    release_notes_validator.checked_files = set()
    release_notes_validator.json_file_path = ""
    release_notes_validator.pack_path = pack_path
    release_notes_validator.suppress_print = False
    release_notes_validator.specific_validations = None
    release_notes_validator.predefined_by_support_ignored_errors = {}
    release_notes_validator.predefined_deprecated_ignored_errors = {}
    return release_notes_validator


FILES_PATH = os.path.normpath(
    os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files", "Packs")
)
nothing_in_rn = ""
rn_not_filled_out = "%%UPDATE_RN%%"
rn_filled_out = "This are sample release notes"
diff_package = [
    (nothing_in_rn, False),
    (rn_not_filled_out, False),
    (rn_filled_out, True),
]


@pytest.mark.parametrize("release_notes, expected_result", diff_package)
def test_rn_master_diff(release_notes, expected_result, mocker):
    """
    Given
    - Case 1: Empty release notes.
    - Case 2: Not filled out release notes.
    - Case 3: Valid release notes

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should return the prompt "Please complete the release notes found at: {path}" and
              return False
    - Case 2: Should return the prompt "Please finish filling out the release notes found at: {path}" and
              return False
    - Case 3: Should print nothing and return True
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    ReleaseNotesValidator.ignored_errors = []
    validator = get_validator(release_notes)
    assert validator.is_file_valid() == expected_result


def test_init():
    """
    Given
    - Release notes file path

    When
    - Running validation on release notes.

    Then
    - Ensure init returns valid file path and release notes contents.
    """
    filepath = os.path.join(FILES_PATH, "CortexXDR", "ReleaseNotes", "1_1_1.md")
    release_notes_validator = ReleaseNotesValidator(filepath, pack_name="test")
    release_notes_validator.release_notes_file_path = (
        "demisto_sdk/tests/test_files/Packs/CortexXDR/ReleaseNotes/" "1_1_1.md"
    )
    assert release_notes_validator.release_notes_path == filepath
    assert release_notes_validator.latest_release_notes == "### Test"


NOT_FILLED_OUT_RN = """
### Incident Types
#### Cortex XDR Incident
- %%UPDATE_RN%%

### Incident Fields
#### XDR Alerts
- %%UPDATE_RN%%

### Integrations
#### Palo Alto Networks Cortex XDR - Investigation and Response
- %%UPDATE_RN%%

### Scripts
#### EntryWidgetNumberHostsXDR
- %%UPDATE_RN%%
"""
FILLED_OUT_RN = """
### Classifiers
#### dummy classifier
- Test

### Dashboards
#### dashboard-sample_packs_new2.json
-Test

### Incident Types
#### Cortex XDR Incident
- Test

### Incident Fields
#### XDR Alerts
- Test

### Integrations
#### Palo Alto Networks Cortex XDR - Investigation and Response
- Test

### Layouts
#### details-Cortex_XDR_Incident
- Test

### Scripts
#### EntryWidgetNumberHostsXDR
- Test

### Playbooks
#### Cortex XDR Incident Handling
- test
"""

TEST_RELEASE_NOTES_TEST_BANK_1 = [
    ("", False),  # Completely Empty
    (
        "### Integrations\n#### HelloWorld\n- Grammar correction for code "  # Missing Items
        "description.\n\n### Scripts\n#### HelloWorldScript \n- Grammar correction for "
        "code description. ",
        False,
    ),
    (NOT_FILLED_OUT_RN, False),
    (FILLED_OUT_RN, True),
]
MODIFIED_FILES = [
    os.path.join(
        FILES_PATH,
        "CortexXDR",
        "Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml",
    ),
    os.path.join(
        FILES_PATH,
        "CortexXDR",
        "Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR_image.png",
    ),
    os.path.join(FILES_PATH, "CortexXDR", "IncidentTypes/Cortex_XDR_Incident.json"),
    os.path.join(FILES_PATH, "CortexXDR", "IncidentFields/XDR_Alerts.json"),
    os.path.join(
        FILES_PATH,
        "CortexXDR",
        "Scripts/EntryWidgetNumberHostsXDR/EntryWidgetNumberHostsXDR.yml",
    ),
    os.path.join(FILES_PATH, "CortexXDR", "README.md"),
    os.path.join(FILES_PATH, "CortexXDR", "Playbooks/Cortex_XDR_Incident_Handling.yml"),
    os.path.join(FILES_PATH, "CortexXDR", "Layouts/details-Cortex_XDR_Incident.json"),
    os.path.join(FILES_PATH, "CortexXDR", "Classifiers/classifier-to-test.json"),
    os.path.join(
        FILES_PATH, "CortexXDR", "Dashboards/dashboard-sample_packs_new2.json"
    ),
]
ADDED_FILES = [
    os.path.join(FILES_PATH, "CortexXDR", "Playbooks/Cortex_XDR_Incident_Handling.yml"),
    os.path.join(
        FILES_PATH,
        "CortexXDR",
        "Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR_description.md",
    ),
    os.path.join(FILES_PATH, "CortexXDR", "ReleaseNotes/1_0_0.md"),
    os.path.join(FILES_PATH, "CortexXDR", "README.md"),
]


@pytest.mark.parametrize(
    "release_notes, complete_expected_result", TEST_RELEASE_NOTES_TEST_BANK_1
)
def test_are_release_notes_complete(release_notes, complete_expected_result, mocker):
    """
    Given
    - Case 1: Empty release notes.
    - Case 2: Not filled out release notes.
    - Case 3: Valid release notes

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should return the prompt "Please complete the release notes found at: {path}" and
              return False
    - Case 2: Should return the prompt "Please finish filling out the release notes found at: {path}" and
              return False
    - Case 3: Should print nothing and return True
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    mocker.patch.object(
        StructureValidator, "scheme_of_file_by_path", return_value="integration"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    validator = get_validator(release_notes, MODIFIED_FILES)
    assert validator.are_release_notes_complete() == complete_expected_result


MODIFIED_FILES_INVALID = [
    os.path.join(
        FILES_PATH,
        "CortexXDR",
        "Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml",
    ),
    os.path.join(FILES_PATH, "CortexXDR", "IncidentTypes/Cortex_XDR_Incident.json"),
    os.path.join(FILES_PATH, "CortexXDR", "IncidentFields/XDR_Alerts.json"),
    os.path.join(
        FILES_PATH,
        "CortexXDR",
        "Scripts/EntryWidgetNumberHostsXDR/EntryWidgetNumberHostsXDR.yml",
    ),
    os.path.join(FILES_PATH, "CortexXDR", "TestPlaybooks/Cortex_XDR.yml"),
    os.path.join(FILES_PATH, "CortexXDR", ".secrets-ignore"),
    os.path.join(FILES_PATH, "CortexXDR", "Playbooks/Cortex_XDR_Incident_Handling.yml"),
    os.path.join(FILES_PATH, "CortexXDR", "Layouts/details-Cortex_XDR_Incident.json"),
    os.path.join(FILES_PATH, "CortexXDR", "Classifiers/classifier-to-test.json"),
    os.path.join(
        FILES_PATH, "CortexXDR", "Dashboards/dashboard-sample_packs_new2.json"
    ),
]


@pytest.mark.parametrize(
    "release_notes, complete_expected_result", TEST_RELEASE_NOTES_TEST_BANK_1
)
def test_are_release_notes_complete_invalid_file_type(
    release_notes, complete_expected_result, mocker
):
    """
    Given
    - Case 1: Empty release notes.
    - Case 2: Not filled out release notes.
    - Case 3: Valid release notes

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should return the prompt "Please complete the release notes found at: {path}" and
              return False
    - Case 2: Should return the prompt "Please finish filling out the release notes found at: {path}" and
              return False
    - Case 3: Should print nothing and return True
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    mocker.patch.object(
        StructureValidator, "scheme_of_file_by_path", return_value="integration"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    validator = get_validator(release_notes, MODIFIED_FILES_INVALID)
    assert validator.are_release_notes_complete() == complete_expected_result


TEST_RELEASE_NOTES_TEST_BANK_ADDED = [
    ("", False),  # Completely Empty
    (
        "### Integrations\n#### HelloWorld\n- Grammar correction for code "  # Missing Items
        "description.\n\n### Scripts\n#### HelloWorldScript\n- Grammar correction for "
        "code description. ",
        False,
    ),
    (NOT_FILLED_OUT_RN, False),
    (FILLED_OUT_RN, True),
]


@pytest.mark.parametrize(
    "release_notes, complete_expected_result", TEST_RELEASE_NOTES_TEST_BANK_ADDED
)
def test_are_release_notes_complete_added(
    release_notes, complete_expected_result, mocker
):
    """
    Given
    - Case 1: Empty release notes.
    - Case 2: Not filled out release notes.
    - Case 3: Valid release notes

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should return the prompt "Please complete the release notes found at: {path}" and
              return False
    - Case 2: Should return the prompt "Please finish filling out the release notes found at: {path}" and
              return False
    - Case 3: Should print nothing and return True
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    mocker.patch.object(
        StructureValidator, "scheme_of_file_by_path", return_value="integration"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    validator = get_validator(release_notes, MODIFIED_FILES, ADDED_FILES)
    assert validator.are_release_notes_complete() == complete_expected_result


def test_are_release_notes_complete_renamed_file(mocker):
    """
    Given
    -
    When
    - Running validation on release notes.
    Then
    - Ensure validation correctly identifies valid release notes.
    -
    """
    renamed_file = [
        (
            os.path.join(
                FILES_PATH,
                "CortexXDR",
                "Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR_old.yml",
            ),
            os.path.join(
                FILES_PATH,
                "CortexXDR",
                "Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml",
            ),
        )
    ]
    release_notes = """
    ### Integrations
    #### Palo Alto Networks Cortex XDR - Investigation and Response
    - Test
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    mocker.patch.object(
        StructureValidator, "scheme_of_file_by_path", return_value="integration"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    validator = get_validator(release_notes, renamed_file)
    assert validator.are_release_notes_complete()


def test_are_release_notes_complete_file_pack_contained_in_file_name_different_pack(
    mocker, repo
):
    """
    Given:
    - Modified file whose name contains the checked pack name.
        checked pack: CortexXDR.
        modified file pack name: FeedCortexXDR.

    When:
    - Validation CortexXDR pack.

    Then:
    - Ensure validation returns true.
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    mocker.patch.object(
        StructureValidator, "scheme_of_file_by_path", return_value="integration"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    pack = repo.create_pack("FeedCortexXDR")
    integration_outside_pack = pack.create_integration(name="FeedCortexXDR")
    integration_outside_pack.create_default_integration("FeedCortexXDR")
    validator = get_validator("", modified_files=[integration_outside_pack.yml.path])
    assert validator.are_release_notes_complete()


def test_are_release_notes_complete_rn_config(pack):
    """
    Given:
    - Release notes config file.

    When:
    - Checking if it should have an entry in RN.

    Then:
    - Ensure it is not checked and release notes return valid response.
    """
    rn = pack.create_release_notes("1_0_1", is_bc=True)
    validator = ReleaseNotesValidator(
        rn.path,
        modified_files=[rn.path.replace("md", "json")],
        pack_name=os.path.basename(pack.path),
    )
    assert validator.are_release_notes_complete()


def test_are_release_notes_with_author_image(mocker, repo):
    """
    Given:
    - Added/modified author image.

    When:
    - Validating RN are complete.

    Then:
    - Ensure File is skipped from check.
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    mocker.patch.object(
        StructureValidator, "scheme_of_file_by_path", return_value="integration"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    pack = repo.create_pack("CortexXDR")
    integration_outside_pack = pack.create_integration(name="CortexXDR")
    integration_outside_pack.create_default_integration("CortexXDR")
    validator = get_validator("", modified_files=[pack.author_image.path])
    assert validator.are_release_notes_complete()


TEST_RELEASE_NOTES_TEST_BANK_2 = [
    ("", False),  # Completely Empty
    (
        "### Integrations\n#### HelloWorld\n- Grammar correction for code "  # Missing Items
        "description.\n\n### Scripts\n#### HelloWorldScript\n- Grammar correction for "
        "code description. ",
        True,
    ),
    (NOT_FILLED_OUT_RN, False),
    (FILLED_OUT_RN, True),
    ("<!-- Test -->", False),
    ("<!-- Test --> #### Integrations\n##### Some Integration", True),
]


@pytest.mark.parametrize(
    "release_notes, filled_expected_result", TEST_RELEASE_NOTES_TEST_BANK_2
)
def test_has_release_notes_been_filled_out(
    release_notes, filled_expected_result, mocker
):
    """
    Given
    - Case 1: Empty release notes.
    - Case 2: Not filled out release notes.
    - Case 3: Valid release notes
    - Case 4: Release notes with all items excluded.
    - Case 5: Release notes with exclusion, but also with filled out section.

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should return the prompt "Please complete the release notes found at: {path}" and
              return True
    - Case 2: Should return the prompt "Please finish filling out the release notes found at: {path}" and
              return False
    - Case 3: Should print nothing and return True
    - Case 4: Should return the prompt "Your release notes file is empty" and return False
    - Case 5: Should print nothing and return True
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    mocker.patch.object(
        StructureValidator, "scheme_of_file_by_path", return_value="integration"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")
    validator = get_validator(release_notes, MODIFIED_FILES)
    assert validator.has_release_notes_been_filled_out() == filled_expected_result


TEST_RELEASE_NOTES_TEST_BANK_3 = [
    (
        "Integration",
        "#### Integrations\n##### Integration name\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
        {
            "display": "Integration name",
            "script": {"dockerimage": "demisto/python3:3.9.5.21272"},
        },
        True,
    ),
    (
        "Script",
        "\n#### Scripts\n##### Script name\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
        {"name": "Script name", "dockerimage": "demisto/python3:3.9.5.21272"},
        True,
    ),
    (
        "Script",
        "\n#### Scripts\n##### Script name\n- Upgraded the Docker image to: *demisto/python3:3.9.5.2122*.",
        {"name": "Script name", "dockerimage": "demisto/python3:3.9.4.272"},
        False,
    ),
    (
        "Integration",
        "#### Integrations\n##### Integration name\n- Moved the Pack to Cortex XSOAR support instead of community support.",
        {
            "display": "Integration name",
            "script": {"dockerimage": "demisto/python3:3.9.5.21272"},
        },
        True,
    ),
]


@pytest.mark.parametrize(
    "category, release_notes_content, yml_content, filled_expected_result",
    TEST_RELEASE_NOTES_TEST_BANK_3,
)
def test_is_docker_image_same_as_yml(
    category, release_notes_content, yml_content, filled_expected_result, pack: Pack
):
    """
    Given
    - Case 1: RN containing a docker update, integration YML containing a docker update, where docker image equal in both.
    - Case 2: RN containing a docker update, script YML containing a docker update, where docker image equal in both.
    - Case 3: RN containing a docker update, script YML containing a docker update, where docker image ins't equal in both.
    - Case 4: Release notes without a docker update, YML without a docker update.
    When
    - Running validation on release notes.
    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should print nothing and return True.
    - Case 2: Should print nothing and return True.
    - Case 3: Should return the prompt "Release notes dockerimage version does not match yml dockerimage version." and
            return False.
    - Case 4: Should print nothing and return True.
    """
    rn = pack.create_release_notes(version="1_0_1", content=release_notes_content)
    if category == "integration":
        category = pack.create_integration()
    else:
        category = pack.create_script()
    category.yml.update(yml_content)
    validator = ReleaseNotesValidator(
        rn.path,
        modified_files=[category.yml.path],
        pack_name=os.path.basename(pack.path),
    )
    assert validator.is_docker_image_same_as_yml() == filled_expected_result


TEST_RELEASE_NOTES_TEST_BANK_4 = [
    (
        ReleaseNotesValidator.get_categories_from_rn,
        "\n#### Integrations\n##### Integration name\n"
        + "- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.\n"
        + "#### Scripts\n##### Script name\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
        {
            "Integrations": "##### Integration name\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
            "Scripts": "##### Script name\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
        },
    ),
    (
        ReleaseNotesValidator.get_categories_from_rn,
        "\n#### Integrations\n##### Integration name1\n"
        + "- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.\n"
        + "##### Integration name2\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
        {
            "Integrations": "##### Integration name1\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.\n"
            + "##### Integration name2\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*."
        },
    ),
    (
        ReleaseNotesValidator.get_entities_from_category,
        "\n##### Integration name1\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.\n"
        + "##### Integration name2\n- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
        {
            "Integration name1": "- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
            "Integration name2": "- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.",
        },
    ),
]


@pytest.mark.parametrize(
    "method_to_check, release_notes_content, filled_expected_result",
    TEST_RELEASE_NOTES_TEST_BANK_4,
)
def test_get_categories_from_rn(
    method_to_check, release_notes_content, filled_expected_result, pack: Pack
):
    """
    Given
    - Case 1: RN containing notes for one integration and one script where each one of them have one entity
    - Case 2: RN containing notes for one integration with two entities
    - Case 3: RN containing notes for two entities.

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should Create a dict with one value for integration key and one value for script key.
    - Case 2: Should Create a dict with one value for integration key that holds 2 integrations.
    - Case 3: Should Create a dict with two keys of integraition 1 and integration 2.
    """
    assert (
        method_to_check(ReleaseNotesValidator, release_notes_content)
        == filled_expected_result
    )


def update_json(path, key, value):
    import json

    js = get_dict_from_file(path=path)[0]
    js[key] = value
    with open(path, "w") as f:
        json.dump(js, f)


TEST_RELEASE_NOTES_BREAKING_CHANGE = [
    (
        "\n#### Integrations\n##### Integration name\n"
        + "- Upgraded the Docker image to: *demisto/python3:3.9.5.21272*.\n",
        False,
        False,
        True,
    ),
    (
        "\n#### Integrations\n##### Integration name\n" + "- Breaking change test\n",
        False,
        False,
        False,
    ),
    (
        "\n#### Integrations\n##### Integration name\n" + "- Breaking change test\n",
        True,
        True,
        False,
    ),
    (
        "\n#### Integrations\n##### Integration name\n" + "- Breaking change test\n",
        True,
        False,
        True,
    ),
]


@pytest.mark.parametrize(
    "release_notes_content, has_json, change_json, expected_result",
    TEST_RELEASE_NOTES_BREAKING_CHANGE,
)
def test_validate_json_when_breaking_changes(
    release_notes_content, has_json, change_json, expected_result, mocker, repo
):
    """
    Given
    - A release note.
    When
    - Run validate_json_when_breaking_changes validation.
    Then
    - Ensure that if the release note contains 'breaking change', there is also an appropriate json file.
    """
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    validator = get_validator(release_notes_content, MODIFIED_FILES)
    pack = repo.create_pack("test_pack")
    if has_json:
        release_note = pack.create_release_notes(
            version="1.0.0", content=release_notes_content, is_bc=True
        )
    else:
        release_note = pack.create_release_notes(
            version="1.0.0", content=release_notes_content
        )
    if change_json:
        update_json(
            path=release_note.path[:-2] + "json", key="breakingChanges", value=False
        )

    validator.release_notes_file_path = release_note.path
    assert validator.validate_json_when_breaking_changes() == expected_result


def test_validate_headers(mocker, repo):
    """
    Given
    - A valid release notes file.
    When
    - Validating the release notes file headers.
    Then
    - Ensure that the validation passes.
    """
    with open("demisto_sdk/commands/common/tests/test_files/rn_header_test_data") as f:
        content = f.read()
    pack = repo.create_pack("test_pack")
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    validator = get_validator(
        content, MODIFIED_FILES, pack_name=pack.name, pack_path=pack.path
    )

    pack.create_integration("integration-test")
    pack.create_script("script-test")
    pack.create_playbook("playbook-test")
    pack.create_correlation_rule("correlation-rule-test")
    pack.create_dashboard("test")
    pack.create_incident_field("test1")
    pack.create_incident_field("test2")
    pack.create_incident_type("test")
    pack.create_indicator_field("test")
    pack.create_indicator_type("test")
    pack.create_layout("test")
    pack.create_mapper("test")
    pack.create_classifier("test")
    pack.create_widget("test")
    pack.create_xsiam_dashboard("xsiam-dashboard-test")
    pack.create_trigger("trigger-test")
    assert validator.validate_release_notes_headers()


TEST_RELEASE_NOTES_INVALID_HEADERS = [
    (
        """#### Integrations
##### integration-test
- Added x y z""",
        "Integrations",
        {
            "rn_valid_header_format": True,
            "validate_content_type_header": True,
            "validate_content_item_header": False,
        },
    ),
    (
        """#### FakeContentType\n##### Test\n- Added x y z""",
        "FakeContentType",
        {
            "rn_valid_header_format": True,
            "validate_content_type_header": False,
            "validate_content_item_header": False,
        },
    ),
    (
        """#### Incident Fields
                                      ##### Test
                                      - Added x y z""",
        "Incident Fields",
        {
            "rn_valid_header_format": False,
            "validate_content_type_header": True,
            "validate_content_item_header": False,
        },
    ),
    (
        """#### Integrations
                                      - **integration-test**
                                      - Added x y z""",
        "Integrations",
        {
            "rn_valid_header_format": False,
            "validate_content_type_header": True,
            "validate_content_item_header": False,
        },
    ),
    (
        """#### Incident Fields
                                  - *test**
                                  - Added x y z""",
        "Incident Fields",
        {
            "rn_valid_header_format": False,
            "validate_content_type_header": True,
            "validate_content_item_header": False,
        },
    ),
]


@pytest.mark.parametrize(
    "content, content_type, expected_result",
    TEST_RELEASE_NOTES_INVALID_HEADERS,
    ids=[
        "Content item dose not exist",
        "Content type dose not exist",
        "Invalid special forms",
        "Invalid content type format",
        "Invalid special forms missing star",
    ],
)
def test_invalid_headers(mocker, repo, content, content_type, expected_result):
    """
    Given
    - A invalid release notes file.
    When
    - Validating the release notes file headers.
    Then
    - Ensure that the validations return the expected result according to the test case.
    """
    pack = repo.create_pack("test_pack")
    mocker.patch.object(ReleaseNotesValidator, "__init__", lambda a, b: None)
    validator = get_validator(
        content, MODIFIED_FILES, pack_name=pack.name, pack_path=pack.path
    )
    headers = validator.extract_rn_headers()
    for content_type, content_items in headers.items():
        assert expected_result[
            "rn_valid_header_format"
        ] == validator.rn_valid_header_format(content_type, content_items)
        validator.filter_rn_headers(headers=headers)
        assert expected_result[
            "validate_content_type_header"
        ] == validator.validate_content_type_header(content_type=content_type)
        assert expected_result[
            "validate_content_item_header"
        ] == validator.validate_content_item_header(
            content_type=content_type, content_items=content_items
        )
