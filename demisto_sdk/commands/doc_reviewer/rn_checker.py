import pprint
from typing import List

import click


def print_template_examples():
    click.secho("\nGeneral Pointers About Release Notes:", fg="bright_cyan")
    click.echo(
        " - The release notes need to be in simple language and informative. "
        "Think about what is the impact on the user and what they should know about this version."
    )
    click.echo(
        " - Command names - should be wrapped with three stars - ***command-name***"
    )
    click.echo(
        " - Packs/Integrations/scripts/playbooks and other content "
        "entities (incident fields, dashboards...) - should be wrapped with two stars - **entity_name**"
    )
    click.echo(
        " - Parameters/arguments/functions/outputs names - "
        "should be wrapped with one star - *entity_name*"
    )
    click.secho("\nEnhancements examples:", fg="bright_cyan")
    click.echo("\n - You can now filter an event by attribute data fields.")
    click.echo(
        "\n - Added support for the *extend-context* argument in the ***ua-parse*** command."
    )
    click.echo("\n - Added 2 commands:\n  - ***command-one***\n  - ***command-two***")
    click.echo(
        "\n - Added the **reporter** and **reporter email** "
        "labels to incidents that are created by direct messages."
    )
    click.echo(
        "\n - Improved implementation of the default value for the *fetch_time* parameter."
    )
    click.secho("\n\nBug fixes examples:", fg="bright_cyan")
    click.echo(
        "\n - Fixed an issue where mirrored investigations contained mismatched user names."
    )
    click.echo(
        "\n - Fixed an issue with ***fetch-incidents***, which caused incident duplication."
    )
    click.echo(
        "\n - Fixed an issue in which the ***qradar-delete-reference-set-value*** command failed to "
        'delete reference sets with the "\\" character in their names.'
    )
    click.secho("\n\nDocker Updates:", fg="bright_cyan")
    click.echo("\n - Updated the Docker image to: *demisto/python3:3.9.1.15759*.")
    click.secho("\n\nGeneral Changes:", fg="bright_cyan")
    click.secho(
        "Note: Use these if the change has no visible impact on the user, "
        "but please try to refrain from using these if possible!",
        fg="yellow",
    )
    click.echo("\n - Documentation and metadata improvements.")
    click.secho("\n\nDeprecation examples:", fg="bright_cyan")
    click.echo(
        "\n - Deprecated. The playbook uses an unsupported scraping API. Use Proofpoint Protection Server "
        "v2 playbook instead."
    )
    click.echo(
        "\n - Deprecated the *ipname* argument from the ***checkpoint-block-ip*** command."
    )
    click.secho("\n\nOut of beta examples:", fg="bright_cyan")
    click.echo("\n - SaaS Security is now generally available.")
    click.secho("\n\nThe available template prefixes are:\n", fg="cyan")
    click.secho(
        f" {pprint.pformat(ReleaseNotesChecker.RN_PREFIX_TEMPLATES)[1:-1]}",
        fg="bright_green",
    )
    click.secho("\n\nThe available template suffixes are:\n", fg="cyan")
    click.secho(
        f" {pprint.pformat(ReleaseNotesChecker.RN_SUFFIX_TEMPLATES)[1:-1]}",
        fg="bright_green",
    )
    click.secho("\n\nThe available full line templates are:\n", fg="cyan")
    click.secho(
        f" {pprint.pformat(ReleaseNotesChecker.RN_FULL_LINE_TEMPLATES)[1:-1]}",
        fg="bright_green",
    )
    click.secho("\n\nThe BANNED line templates are:\n", fg="cyan")
    click.secho(
        f" {pprint.pformat(ReleaseNotesChecker.BANNED_TEMPLATES)[1:-1]}",
        fg="bright_red",
    )
    click.echo(
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
            click.secho(f'\n - Notes for the line: "{line}"', fg="bright_red")
            for note in self.notes[line]:
                click.secho(f"   - {note}", fg="bright_red")

    def check_rn(self) -> bool:
        """Check if an RN file is up to our standards"""
        show_template_message = False
        is_new_content_item = False

        for line in self.file_content:
            line = line.lstrip(" -")
            line = line.rstrip()

            if line.startswith("##### New:"):
                is_new_content_item = True
                continue

            # skip headers
            if line.startswith(("#", "*")) or line.isspace() or not line:
                is_new_content_item = False
                continue

            if is_new_content_item:
                # The description of new content items does not need to conform to templates
                continue

            if not self.check_templates(line):
                show_template_message = True
                self.add_note(
                    line,
                    "Line is not using one of our templates, consider "
                    "changing it to fit our standard.",
                )

            if self.check_if_using_banned_template(line):
                show_template_message = True
                self.add_note(
                    line,
                    "Line is using one of our banned templates, please change it to fit our standard.",
                )

            if line[0].isalpha() and not line[0].isupper():
                self.add_note(line, "Line should start with capital letter.")

            if line[-1] not in [".", ":"]:
                self.add_note(line, "Line should end with a period (.)")

            if "bug" in line.lower():
                self.add_note(
                    line, 'Refrain from using the word "bug", use "issue" instead.'
                )

        if self.notes:
            self.print_notes()
            if show_template_message:
                click.secho(
                    "\n For more information about templates run: `demisto-sdk doc-review --templates` "
                    "or view our documentation at: https://xsoar.pan.dev/docs/documentation/release-notes",
                    fg="bright_red",
                )
            return False
        else:
            click.secho(
                f" - Release notes {self.file_path} match a known template.", fg="green"
            )
            return True
