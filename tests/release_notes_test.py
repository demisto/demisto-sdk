import mock
import pytest
from demisto_sdk.common.tools import run_command
from demisto_sdk.common.hook_validations.release_notes import ReleaseNotesValidator


def get_validator(file_path=""):
    with mock.patch.object(ReleaseNotesValidator, '__init__', lambda a, b: None) as init, \
            mock.patch('demisto_sdk.common.tools.run_command', lambda a: a.split('master ')[1]) as rc:
        release_notes_validator = ReleaseNotesValidator("")
        release_notes_validator.file_path = file_path
        release_notes_validator.release_notes_path = file_path
        release_notes_validator.release_notes = file_path
    return release_notes_validator


single_line_good_rn = 'Some rn.'
single_line_bad_rn_1 = '  - Some rn.'
single_line_bad_rn_2 = 'Some rn'
single_line_list_good_rn = 'List rn.\n' \
                           '  - item #1.\n' \
                           '\t- item #2.'
single_line_list_bad_rn_1 = 'List rn.\n' \
                            '  -item #1.\n' \
                            '\t- item #2.'
single_line_list_bad_rn_2 = 'List rn.\n' \
                            '  item #1.\n' \
                            '\t- item #2.'
multi_line_good_rn = '  - comment 1.\n' \
                     '\t- comment 2..'
multi_line_bad_rn_1 = ' - comment 1\n' \
                      '  - comment 2.'
multi_line_bad_rn_2 = 'comment 1.\n' \
                      'comment 2.'
rn_structure_test_package = [(single_line_good_rn, True),
                             (single_line_bad_rn_1, False),
                             (single_line_bad_rn_2, False),
                             (single_line_list_good_rn, True),
                             (single_line_list_bad_rn_1, False),
                             (single_line_list_bad_rn_2, False),
                             (multi_line_good_rn, True),
                             (multi_line_bad_rn_1, False),
                             (multi_line_bad_rn_2, False)]


@pytest.mark.parametrize('release_notes_test, expected_result', rn_structure_test_package)
def test_rn_structure(release_notes_test, expected_result):
    validator = get_validator("")
    assert validator.is_valid_rn_structure(release_notes_test) == expected_result


diff_nothing = ''

diff_changed_the_same_line = 'diff --git a/Integrations/integration-VirusTotal_CHANGELOG.md b/Integrations/' \
                             'integration-VirusTotal_CHANGELOG.md\n' \
                             '\nindex cbf564679..cffab9e90 100644' \
                             '\n--- a/Integrations/integration-VirusTotal_CHANGELOG.md' \
                             '\n+++ b/Integrations/integration-VirusTotal_CHANGELOG.md' \
                             '\n@@ -1,15 +1,15 @@' \
                             '\n ## [Unreleased]' \
                             '\n-  - Added batch support for the **ip** and **url** and **domain** commands.' \
                             '\n+  - Added batch support for the **ip** and **url** and **domain** commands1.' \
                             '\n   - Fixed an issue where the DBotScore would create duplications in the ' \
                             'incident context. This effects Demisto version 5.5 and higher.' \
                             '\n ## [19.8.2] - 2019-08-22' \
                             '\n   - Added the Virus Total permanent link to the context of the following commands: ' \
                             '\n     - url' \
                             '\n     - file' \
                             '\n     - url-scan' \
                             '\n     - file-scan' \
                             '\n     - file-rescan' \
                             '\n ## [19.8.0] - 2019-08-06' \
                             '\n   - Updated outputs with new indicator fields.'

diff_removed_line = 'diff --git a/Integrations/integration-VirusTotal_CHANGELOG.md b/Integrations/' \
                    'integration-VirusTotal_CHANGELOG.md' \
                    '\nindex cbf564679..c49498c58 100644' \
                    '\n--- a/Integrations/integration-VirusTotal_CHANGELOG.md' \
                    '\n+++ b/Integrations/integration-VirusTotal_CHANGELOG.md' \
                    '\n@@ -1,15 +1,14 @@' \
                    '\n ## [Unreleased]' \
                    '\n-  - Added batch support for the **ip** and **url** and **domain** commands.' \
                    '\n-  - Fixed an issue where the DBotScore would create duplications in the incident context. ' \
                    'This effects Demisto version 5.5 and higher.' \
                    '\n+' \
                    '\n ## [19.8.2] - 2019-08-22' \
                    '\n   - Added the Virus Total permanent link to the context of the following commands: ' \
                    '\n     - url' \
                    '\n     - file' \
                    '\n     - url-scan' \
                    '\n     - file-scan' \
                    '\n     - file-rescan' \
                    '\n ## [19.8.0] - 2019-08-06' \
                    '\n   - Updated outputs with new indicator fields.'

diff_added_line = 'diff --git a/Integrations/integration-VirusTotal_CHANGELOG.md b/Integrations/i' \
                  'ntegration-VirusTotal_CHANGELOG.md\n' \
                  '\nindex cbf564679..cffab9e90 100644' \
                  '\n--- a/Integrations/integration-VirusTotal_CHANGELOG.md' \
                  '\n+++ b/Integrations/integration-VirusTotal_CHANGELOG.md' \
                  '\n@@ -1,15 +1,15 @@' \
                  '\n ## [Unreleased]' \
                  '\n-  - Added batch support for the **ip** and **url** and **domain** commands.' \
                  '\n+  - Added batch support for the **ip** and **url** and **domain** commands1.' \
                  '\n+ ' \
                  '\n   - Fixed an issue where the DBotScore would create duplications in the incident context. ' \
                  'This effects Demisto version 5.5 and higher.' \
                  '\n ## [19.8.2] - 2019-08-22' \
                  '\n   - Added the Virus Total permanent link to the context of the following commands: ' \
                  '\n     - url' \
                  '\n     - file' \
                  '\n     - url-scan' \
                  '\n     - file-scan' \
                  '\n     - file-rescan' \
                  '\n ## [19.8.0] - 2019-08-06' \
                  '\n   - Updated outputs with new indicator fields.'

diff_package = [(diff_nothing, False),
                (diff_changed_the_same_line, False),
                (diff_removed_line, False),
                (diff_added_line, True)]


@pytest.mark.parametrize('release_notes_diff, expected_result', diff_package)
def test_rn_master_diff(release_notes_diff, expected_result):
    validator = get_validator(release_notes_diff)
    assert validator.is_release_notes_changed() == expected_result
