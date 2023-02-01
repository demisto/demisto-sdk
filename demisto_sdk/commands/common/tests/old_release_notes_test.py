import pytest

from demisto_sdk.commands.common.hook_validations.old_release_notes import (
    OldReleaseNotesValidator,
)


def get_validator(file_path="", diff=""):
    release_notes_validator = OldReleaseNotesValidator("")
    release_notes_validator.file_path = file_path
    release_notes_validator.release_notes_path = file_path
    release_notes_validator.release_notes = file_path
    release_notes_validator.master_diff = diff
    release_notes_validator.ignored_errors = {}
    release_notes_validator.checked_files = set()
    release_notes_validator.json_file_path = ""
    release_notes_validator.specific_validations = None
    release_notes_validator.predefined_by_support_ignored_errors = {}
    release_notes_validator.predefined_deprecated_ignored_errors = {}
    return release_notes_validator


diff_nothing = ""

diff_changed_the_same_line = (
    "diff --git a/Integrations/integration-VirusTotal_CHANGELOG.md b/Integrations/"
    "integration-VirusTotal_CHANGELOG.md\n"
    "\nindex cbf564679..cffab9e90 100644"
    "\n--- a/Integrations/integration-VirusTotal_CHANGELOG.md"
    "\n+++ b/Integrations/integration-VirusTotal_CHANGELOG.md"
    "\n@@ -1,15 +1,15 @@"
    "\n ## [Unreleased]"
    "\n-  - Added batch support for the **ip** and **url** and **domain** commands."
    "\n+  - Added batch support for the **ip** and **url** and **domain** commands1."
    "\n   - Fixed an issue where the DBotScore would create duplications in the "
    "incident context. This effects Demisto version 5.5 and higher."
    "\n ## [19.8.2] - 2019-08-22"
    "\n   - Added the Virus Total permanent link to the context of the following commands: "
    "\n     - url"
    "\n     - file"
    "\n     - url-scan"
    "\n     - file-scan"
    "\n     - file-rescan"
    "\n ## [19.8.0] - 2019-08-06"
    "\n   - Updated outputs with new indicator fields."
)

diff_removed_line = (
    "diff --git a/Integrations/integration-VirusTotal_CHANGELOG.md b/Integrations/"
    "integration-VirusTotal_CHANGELOG.md"
    "\nindex cbf564679..c49498c58 100644"
    "\n--- a/Integrations/integration-VirusTotal_CHANGELOG.md"
    "\n+++ b/Integrations/integration-VirusTotal_CHANGELOG.md"
    "\n@@ -1,15 +1,14 @@"
    "\n ## [Unreleased]"
    "\n-  - Added batch support for the **ip** and **url** and **domain** commands."
    "\n-  - Fixed an issue where the DBotScore would create duplications in the incident context. "
    "This effects Demisto version 5.5 and higher."
    "\n+"
    "\n ## [19.8.2] - 2019-08-22"
    "\n   - Added the Virus Total permanent link to the context of the following commands: "
    "\n     - url"
    "\n     - file"
    "\n     - url-scan"
    "\n     - file-scan"
    "\n     - file-rescan"
    "\n ## [19.8.0] - 2019-08-06"
    "\n   - Updated outputs with new indicator fields."
)

diff_added_line = (
    "diff --git a/Integrations/integration-VirusTotal_CHANGELOG.md b/Integrations/i"
    "ntegration-VirusTotal_CHANGELOG.md\n"
    "\nindex cbf564679..cffab9e90 100644"
    "\n--- a/Integrations/integration-VirusTotal_CHANGELOG.md"
    "\n+++ b/Integrations/integration-VirusTotal_CHANGELOG.md"
    "\n@@ -1,15 +1,15 @@"
    "\n ## [Unreleased]"
    "\n-  - Added batch support for the **ip** and **url** and **domain** commands."
    "\n+  - Added batch support for the **ip** and **url** and **domain** commands1."
    "\n+ "
    "\n   - Fixed an issue where the DBotScore would create duplications in the incident context. "
    "This effects Demisto version 5.5 and higher."
    "\n ## [19.8.2] - 2019-08-22"
    "\n   - Added the Virus Total permanent link to the context of the following commands: "
    "\n     - url"
    "\n     - file"
    "\n     - url-scan"
    "\n     - file-scan"
    "\n     - file-rescan"
    "\n ## [19.8.0] - 2019-08-06"
    "\n   - Updated outputs with new indicator fields."
)

diff_package = [
    (diff_nothing, False),
    (diff_changed_the_same_line, False),
    (diff_removed_line, False),
    (diff_added_line, True),
]


@pytest.mark.parametrize("release_notes_diff, expected_result", diff_package)
def test_rn_master_diff(release_notes_diff, expected_result, mocker):
    mocker.patch.object(OldReleaseNotesValidator, "__init__", lambda a, b: None)
    validator = get_validator(diff=release_notes_diff)
    validator.suppress_print = False
    assert validator.is_release_notes_changed() == expected_result
