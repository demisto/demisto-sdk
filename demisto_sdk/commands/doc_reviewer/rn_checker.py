import pprint
from typing import List

from demisto_sdk.commands.common.constants import (
    XPANSE_INLINE_PREFIX_TAG,
    XPANSE_INLINE_SUFFIX_TAG,
    XPANSE_PREFIX_TAG,
    XPANSE_SUFFIX_TAG,
    XSIAM_INLINE_PREFIX_TAG,
    XSIAM_INLINE_SUFFIX_TAG,
    XSIAM_PREFIX_TAG,
    XSIAM_SUFFIX_TAG,
    XSOAR_INLINE_PREFIX_TAG,
    XSOAR_INLINE_SUFFIX_TAG,
    XSOAR_PREFIX_TAG,
    XSOAR_SAAS_INLINE_PREFIX_TAG,
    XSOAR_SAAS_INLINE_SUFFIX_TAG,
    XSOAR_SAAS_PREFIX_TAG,
    XSOAR_SAAS_SUFFIX_TAG,
    XSOAR_SUFFIX_TAG,
)
from demisto_sdk.commands.common.logger import logger


def print_template_examples():
    logger.info("\n[cyan]General Pointers About Release Notes:[/cyan]")
    logger.info(
        " - The release notes need to be in simple language and informative. "
        "Think about what is the impact on the user and what they should know about this version."
    )
    logger.info(
        " - Command names - should be wrapped with three stars - ***command-name***"
    )
    logger.info(
        " - Packs/Integrations/scripts/playbooks and other content "
        "entities (incident fields, dashboards...) - should be wrapped with two stars - **entity_name**"
    )
    logger.info(
        " - Parameters/arguments/functions/outputs names - "
        "should be wrapped with one star - *entity_name*"
    )
    logger.info("\n[cyan]Enhancements examples:[/cyan]")
    logger.info("\n - You can now filter an event by attribute data fields.")
    logger.info(
        "\n - Added support for the *extend-context* argument in the ***ua-parse*** command."
    )
    logger.info("\n - Added 2 commands:\n  - ***command-one***\n  - ***command-two***")
    logger.info(
        "\n - Added the **reporter** and **reporter email** "
        "labels to incidents that are created by direct messages."
    )
    logger.info(
        "\n - Improved implementation of the default value for the *fetch_time* parameter."
    )
    logger.info("\n\n[cyan]Bug fixes examples:[/cyan]")
    logger.info(
        "\n - Fixed an issue where mirrored investigations contained mismatched user names."
    )
    logger.info(
        "\n - Fixed an issue with ***fetch-incidents***, which caused incident duplication."
    )
    logger.info(
        "\n - Fixed an issue in which the ***qradar-delete-reference-set-value*** command failed to "
        'delete reference sets with the "\\" character in their names.'
    )
    logger.info("\n\n[cyan]Docker Updates:[/cyan]")
    logger.info("\n - Updated the Docker image to: *demisto/python3:3.9.1.15759*.")
    logger.info("\n\n[cyan]General Changes:[/cyan]")
    logger.info(
        "[yellow]Note: Use these if the change has no visible impact on the user, "
        "but please try to refrain from using these if possible![/yellow]"
    )
    logger.info("\n - Documentation and metadata improvements.")
    logger.info("\n\n[cyan]Deprecation examples:[/cyan]")
    logger.info(
        "\n - Deprecated. The playbook uses an unsupported scraping API. Use Proofpoint Protection Server "
        "v2 playbook instead."
    )
    logger.info(
        "\n - Deprecated the *ipname* argument from the ***checkpoint-block-ip*** command."
    )
    logger.info("\n\n[cyan]Out of beta examples:[/cyan]")
    logger.info("\n - SaaS Security is now generally available.")
    logger.info("\n\n[cyan]The available template prefixes are:[/cyan]\n")
    logger.info(
        f"[green] {pprint.pformat(ReleaseNotesChecker.RN_PREFIX_TEMPLATES)[1:-1]}[/green]"
    )
    logger.info("\n\n[cyan]The available template suffixes are:[/cyan]\n")
    logger.info(
        f"[green] {pprint.pformat(ReleaseNotesChecker.RN_SUFFIX_TEMPLATES)[1:-1]}[/green]"
    )
    logger.info("\n\n[cyan]The available full line templates are:[/cyan]\n")
    logger.info(
        f"[green] {pprint.pformat(ReleaseNotesChecker.RN_FULL_LINE_TEMPLATES)[1:-1]}[/green]"
    )
    logger.info("\n\n[cyan]The BANNED line templates are:[/cyan]\n")
    logger.info(
        f"[red] {pprint.pformat(ReleaseNotesChecker.BANNED_TEMPLATES)[1:-1]}[/red]"
    )
    logger.info(
        "\n\nFor additional information see: https://xsoar.pan.dev/docs/documentation/release-notes"
    )


class ReleaseNotesChecker:
    RN_PREFIX_TEMPLATES = {
        "Added support for",
        "Added the",
        "Added a ",
        "Added an ",
        "Fixed an issue",
        "Improved implementation",
        "Updated the Docker image to",
        "You can now",
        "Deprecated. ",
        "Deprecated the ",
        "Note: ",
        "Started adoption process.",
        "Completed adoption process.",
        "Improved layout",
        "Created a new layout",
        "Playbook now supports",
        "Created a new playbook",
        "Updated the",
    }

    RN_FULL_LINE_TEMPLATES = {"Documentation and metadata improvements."}

    RN_SUFFIX_TEMPLATES = {"now generally available."}

    BANNED_TEMPLATES = {
        "maintenance and stability enhancements.",
        "stability and maintenance enhancements.",
    }

    MP_TAGS = {
        XSOAR_PREFIX_TAG,
        XSOAR_SUFFIX_TAG,
        XSOAR_INLINE_PREFIX_TAG,
        XSOAR_INLINE_SUFFIX_TAG,
        XSOAR_SAAS_PREFIX_TAG,
        XSOAR_SAAS_SUFFIX_TAG,
        XSOAR_SAAS_INLINE_PREFIX_TAG,
        XSOAR_SAAS_INLINE_SUFFIX_TAG,
        XSIAM_PREFIX_TAG,
        XSIAM_SUFFIX_TAG,
        XSIAM_INLINE_PREFIX_TAG,
        XSIAM_INLINE_SUFFIX_TAG,
        XPANSE_PREFIX_TAG,
        XPANSE_SUFFIX_TAG,
        XPANSE_INLINE_PREFIX_TAG,
        XPANSE_INLINE_SUFFIX_TAG,
    }

    def __init__(
        self,
        rn_file_path: str = None,
        rn_file_content: List = [],
        template_examples: bool = False,
    ):
        if template_examples:
            print_template_examples()

        else:
            self.file_path = rn_file_path
            self.file_content = rn_file_content
            self.notes: dict = {}

    def add_note(self, line, note):
        """Add note about a release notes line"""
        if line in self.notes:
            self.notes[line].append(note)
        else:
            self.notes[line] = [note]

    def check_templates(self, line):
        """Check that the given line fits one of our templates"""
        if line.lower().startswith("added") and (
            line.lower().endswith("command:") or line.endswith("commands:")
        ):
            return True

        for template in self.RN_PREFIX_TEMPLATES:
            if line.lower().startswith(template.lower()):
                return True

        for template in self.RN_SUFFIX_TEMPLATES:
            if line.lower().endswith(template.lower()):
                return True

        for template in self.RN_FULL_LINE_TEMPLATES:
            if line.lower() == template.lower():
                return True

        return False

    def check_if_using_banned_template(self, line):
        line = line.lstrip(" -")
        line = line.rstrip()
        for temp in self.BANNED_TEMPLATES:
            if line.lower() == temp:
                return True
        return False

    def print_notes(self):
        """Print the review about the RN"""
        for line in self.notes:
            logger.info(f'\n[red] - Notes for the line: "{line}"[/red]')
            for note in self.notes[line]:
                logger.info(f"[red]   - {note}[/red]")

    def check_rn(self) -> bool:
        """Check if an RN file is up to our standards"""
        show_template_message = False
        is_new_content_item = False

        line: str
        for line_number, line in enumerate(self.file_content, start=1):
            for tag in self.MP_TAGS:
                line = line.replace(tag, "")

            line = line.lstrip(" -")
            line = line.rstrip()

            if line.startswith(("##### New:", "New:")):
                is_new_content_item = True
                continue

            # skip headers
            if line.startswith(("#", "*")):
                is_new_content_item = False
                continue

            if is_new_content_item or not line or line.isspace():
                # The description of new content items, or empty lines do not need to conform to templates
                continue

            if not self.check_templates(line):
                show_template_message = True
                self.add_note(
                    line,
                    f"Line #{line_number} is not using one of our templates, consider "
                    "changing it to fit our standard.",
                )

            if self.check_if_using_banned_template(line):
                show_template_message = True
                self.add_note(
                    line,
                    f"Line #{line_number} is using one of our banned templates, please change it to fit our standard.",
                )

            if line[0].isalpha() and not line[0].isupper():
                self.add_note(
                    line, f"Line #{line_number} should start with capital letter."
                )

            if line[-1] not in [".", ":"]:
                self.add_note(line, f"Line #{line_number} should end with a period (.)")

            if "bug" in line.lower():
                self.add_note(
                    line, 'Refrain from using the word "bug", use "issue" instead.'
                )

        if self.notes:
            self.print_notes()
            if show_template_message:
                logger.info(
                    "\n[red] For more information about templates run: `demisto-sdk doc-review --templates` "
                    "or view our documentation at: https://xsoar.pan.dev/docs/documentation/release-notes[/red]"
                )
            return False
        else:
            logger.info(
                f"[green] - Release notes {self.file_path} match a known template.[/green]"
            )
            return True
