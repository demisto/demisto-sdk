import pytest

from demisto_sdk.commands.doc_reviewer.rn_checker import ReleaseNotesChecker


@pytest.mark.parametrize(
    "file_content, expected_result",
    [
        (["SaaS Security is now generally available."], True),
        (
            [
                "You can now use double clicks.",
                "Note: The functionality remains the same.",
            ],
            True,
        ),
        (
            [
                "Added support for the *extend-context* argument in the ***ua-parse*** command.",
                "Added the ** reporter ** and ** reporter email ** labels to incidents that are created by direct messages.",
            ],
            True,
        ),
        (["Added 2 commands:", "***command-one***", "***command-two***"], True),
        (
            [
                "Fixed an issue where mirrored investigations contained mismatched user names."
            ],
            True,
        ),
        (["Updated the Docker image to: *demisto/python3:3.9.1.15759*."], True),
        (
            [
                "Deprecated. The playbook uses an unsupported scraping API. Use Proofpoint Protection Server v2 "
                "playbook instead.",
                "Deprecated the *ipname* argument from the ***checkpoint-block-ip*** command.",
            ],
            True,
        ),
        (["Documentation and metadata improvements."], True),
        (["Maintenance and stability enhancements."], False),
        (["Stability and maintenance enhancements."], False),
        (["Blah."], False),
        (["Improved layout for ASN type."], True),
        (["Created a new layout for MITRE Att&ck."], True),
        (["Playbook now supports IPs as well as Emails."], True),
        (["Created a new playbook for CVE-XXXX-XXXX."], True),
        (["Updated the IP type regex."], True),
        (
            [
                "##### New: script",
                "Improved layout for ASN type.",  # Matches template following "##### New:"
                "Documentation and metadata improvements.",
            ],
            True,
        ),
        (
            ["##### New: script", "some string that doesnt match a pattern"],
            True,
        ),  # Not matching template following "##### New:"
        (
            [
                "##### New: script",
                "***command-one***",
                "some string that doesnt match a pattern",
            ],
            False,
        ),  # Not matching template following "*"
        (
            [
                "##### New: script",
                "Blah.",
                "##### script",
                "Improved layout for ASN type.",
            ],
            True,
        ),
        (["##### New: script", "Blah.", "##### script", "Blah."], False),
    ],
)
def test_release_notes_templates(file_content, expected_result):
    """
    Given
        - A release notes file content.

    When
        - Running rn_checker on it.

    Then
        - Ensure the result is as expected.
    """
    rn_checker = ReleaseNotesChecker(rn_file_content=file_content)
    assert expected_result == rn_checker.check_rn()
