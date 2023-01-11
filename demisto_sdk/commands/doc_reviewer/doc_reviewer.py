import os
import re
import ssl
import string
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import List, Optional, Tuple

import click
import nltk
from nltk.corpus import brown, webtext
from spellchecker import SpellChecker

from demisto_sdk.commands.common.constants import PACKS_PACK_IGNORE_FILE_NAME, FileType
from demisto_sdk.commands.common.content import (
    Content,
    Integration,
    Playbook,
    ReleaseNote,
    Script,
    path_to_pack_object,
)
from demisto_sdk.commands.common.content.objects.abstract_objects import TextObject
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import (
    YAMLContentObject,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.tools import (
    add_default_pack_known_words,
    find_type,
    is_xsoar_supported_pack,
)
from demisto_sdk.commands.doc_reviewer.known_words import KNOWN_WORDS
from demisto_sdk.commands.doc_reviewer.rn_checker import ReleaseNotesChecker


class DocReviewer:
    """Perform a spell check on the given .yml or .md file."""

    SUPPORTED_FILE_TYPES = [
        FileType.INTEGRATION,
        FileType.SCRIPT,
        FileType.PLAYBOOK,
        FileType.README,
        FileType.DESCRIPTION,
        FileType.RELEASE_NOTES,
        FileType.BETA_INTEGRATION,
        FileType.TEST_PLAYBOOK,
        FileType.TEST_SCRIPT,
    ]

    def __init__(
        self,
        file_paths: Optional[List] = None,
        known_words_file_paths: Optional[List] = None,
        no_camel_case: bool = False,
        no_failure: bool = False,
        expand_dictionary: bool = False,
        templates: bool = False,
        use_git: bool = False,
        prev_ver: str = None,
        release_notes_only: bool = False,
        xsoar_only: bool = False,
        load_known_words_from_pack: bool = False,
    ):
        if templates:
            ReleaseNotesChecker(template_examples=True)
            sys.exit(0)

        # if nothing entered will default to use git
        elif not file_paths and not use_git:
            use_git = True

        self.file_paths = file_paths if file_paths else []
        self.git_util = None

        if use_git:
            self.git_util = GitUtil(repo=Content.git())
            self.prev_ver = self.git_util.handle_prev_ver()[1]
        else:
            self.prev_ver = prev_ver if prev_ver else "demisto/master"

        if release_notes_only:
            self.SUPPORTED_FILE_TYPES = [FileType.RELEASE_NOTES]
            # if running doc-review --release-notes there is no need to consider invalid schema files of yml/json
            self.ignore_invalid_schema_file = True
        else:
            self.ignore_invalid_schema_file = False

        self.known_words_file_paths = (
            known_words_file_paths if known_words_file_paths else []
        )
        self.load_known_words_from_pack = load_known_words_from_pack
        self.known_pack_words_file_path = ""

        self.is_xsoar_supported_rn_only: bool = xsoar_only
        self.current_pack = None
        self.files: List[str] = []
        self.spellchecker = SpellChecker()
        self.unknown_words: dict = {}
        self.no_camel_case = no_camel_case
        self.found_misspelled = False
        self.no_failure = no_failure
        self.expand_dictionary = expand_dictionary
        self.files_with_misspells: set = set()
        self.files_without_misspells: set = set()
        self.malformed_rn_files: set = set()

    @staticmethod
    def find_known_words_from_pack(file_path: str) -> Tuple[str, list]:
        """Find known words in file_path's pack.

        Args:
            file_path: The path of the file within the pack

        Return (the known words file path or '' if it was not found, list of known words)
        """
        file_path_obj = Path(file_path)
        if "Packs" in file_path_obj.parts:
            pack_name = file_path_obj.parts[file_path_obj.parts.index("Packs") + 1]
            packs_ignore_path = os.path.join(
                "Packs", pack_name, PACKS_PACK_IGNORE_FILE_NAME
            )
            default_pack_known_words = add_default_pack_known_words(file_path)
            if os.path.isfile(packs_ignore_path):
                config = ConfigParser(allow_no_value=True)
                config.read(packs_ignore_path)
                if "known_words" in config.sections():
                    packs_known_words = default_pack_known_words + list(
                        config["known_words"]
                    )
                    return packs_ignore_path, packs_known_words
                else:
                    click.secho(
                        f"\nNo [known_words] section was found within: {packs_ignore_path}",
                        fg="yellow",
                    )
                    return packs_ignore_path, default_pack_known_words

            click.secho(
                f"\nNo .pack-ignore file was found within pack: {packs_ignore_path}",
                fg="yellow",
            )
            return "", default_pack_known_words

        click.secho(
            f"\nCould not load pack's known words file since no pack structure was found for {file_path}"
            f"\nMake sure you are running from the content directory.",
            fg="bright_red",
        )
        return "", []

    @staticmethod
    def is_upper_case_word_plural(word):
        """check if a given word is an upper case word in plural, like: URLs, IPs, etc"""
        if len(word) > 2 and word[-1] == "s":
            singular_word = word[:-1]
            return singular_word == singular_word.upper()
        return False

    def is_camel_case(self, word):
        """check if a given word is in camel case"""
        if (
            word != word.lower()
            and word != word.upper()
            and "_" not in word
            and word != word.title()
        ):
            # check if word is an upper case plural, like IPs. If it is, then the word is not in camel case
            return not self.is_upper_case_word_plural(word)
        return False

    @staticmethod
    def camel_case_split(camel):
        """split camel case word into sub-words"""
        tokens = re.compile("([A-Z]?[a-z]+)").findall(camel)
        for token in tokens:
            # double space to handle capital words like IP/URL/DNS that not included in the regex
            camel = camel.replace(token, f" {token} ")

        return camel.split()

    def get_all_md_and_yml_files_in_dir(self, dir_name):
        """recursively get all the supported files from a given dictionary"""
        for root, _, files in os.walk(dir_name):
            for file_name in files:
                full_path = os.path.join(root, file_name)
                if (
                    find_type(
                        full_path,
                        ignore_invalid_schema_file=self.ignore_invalid_schema_file,
                    )
                    in self.SUPPORTED_FILE_TYPES
                ):
                    self.files.append(str(full_path))

    def gather_all_changed_files(self):
        modified = self.git_util.modified_files(prev_ver=self.prev_ver)  # type: ignore[union-attr]
        added = self.git_util.added_files(prev_ver=self.prev_ver)  # type: ignore[union-attr]
        renamed = self.git_util.renamed_files(prev_ver=self.prev_ver, get_only_current_file_names=True)  # type: ignore[union-attr]

        return modified.union(added).union(renamed)  # type: ignore[arg-type]

    def get_files_from_git(self):
        click.secho("Gathering all changed files from git", fg="bright_cyan")
        for file in self.gather_all_changed_files():
            file = str(file)
            if (
                os.path.isfile(file)
                and find_type(
                    file, ignore_invalid_schema_file=self.ignore_invalid_schema_file
                )
                in self.SUPPORTED_FILE_TYPES
            ):
                self.files.append(file)

    def get_files_to_run_on(self, file_path=None):
        """Get all the relevant files that the spell-check could work on"""
        if self.git_util:
            self.get_files_from_git()

        elif os.path.isdir(file_path):
            self.get_all_md_and_yml_files_in_dir(file_path)

        elif (
            find_type(
                file_path, ignore_invalid_schema_file=self.ignore_invalid_schema_file
            )
            in self.SUPPORTED_FILE_TYPES
        ):
            self.files.append(file_path)

    @staticmethod
    def print_unknown_words(unknown_words):
        for word, corrections in unknown_words.items():
            if corrections:
                click.secho(
                    f"  - {word} - did you mean: {corrections}", fg="bright_red"
                )
            else:
                click.secho(f"  - {word}", fg="bright_red")
        click.secho(
            "If these are not misspelled consider adding them to a known_words file:\n"
            "  Pack related words: content/Packs/<PackName>/.pack-ignore under the [known_words] section.\n"
            "  Not pack specific words: content/Tests/known_words.txt\n"
            "To test locally add --use-packs-known-words or --known-words flags.",
            fg="yellow",
        )

    def print_file_report(self):
        if self.files_without_misspells:
            click.secho(
                "\n================= Files Without Misspells =================",
                fg="green",
            )
            no_misspells_string = "\n".join(self.files_without_misspells)
            click.secho(no_misspells_string, fg="green")

        if self.files_with_misspells:
            click.secho(
                "\n================= Files With Misspells =================",
                fg="bright_red",
            )
            misspells_string = "\n".join(self.files_with_misspells)
            click.secho(misspells_string, fg="bright_red")

        if self.malformed_rn_files:
            click.secho(
                "\n================= Malformed Release Notes =================",
                fg="bright_red",
            )
            bad_rn = "\n".join(self.malformed_rn_files)
            click.secho(bad_rn, fg="bright_red")

    def run_doc_review(self):
        """Runs spell-check on the given file and release notes check if relevant.

        Returns:
            bool. True if no problematic words found, False otherwise.
        """
        click.secho(
            "\n================= Starting Doc Review =================",
            fg="bright_cyan",
        )
        if len(self.SUPPORTED_FILE_TYPES) == 1:
            click.secho("Running only on release notes", fg="bright_cyan")

        if self.file_paths:
            for file_path in self.file_paths:
                self.get_files_to_run_on(file_path)
        else:
            self.get_files_to_run_on()

        # no eligible files found
        if not self.files:
            click.secho("Could not find any relevant files - Aborting.")
            return True

        self.add_known_words()

        for file in self.files:
            click.echo(f"\nChecking file {file}")

            # --xsoar-only flag is specified.
            if self.is_xsoar_supported_rn_only and not is_xsoar_supported_pack(file):
                click.secho(
                    f"File '{file}' was skipped because it does not belong to an XSOAR-supported Pack",
                    fg="yellow",
                )
                continue

            restarted_spellchecker = self.update_known_words_from_pack(file)
            if restarted_spellchecker:
                self.add_known_words()
            self.unknown_words = {}
            if file.endswith(".md"):
                self.check_md_file(file)

            elif file.endswith(".yml"):
                self.check_yaml(file)

            if self.unknown_words:
                click.secho(
                    f"\n - Words that might be misspelled were found in " f"{file}:",
                    fg="bright_red",
                )
                self.print_unknown_words(unknown_words=self.unknown_words)
                self.found_misspelled = True
                self.files_with_misspells.add(file)

            else:
                click.secho(f" - No misspelled words found in {file}", fg="green")
                self.files_without_misspells.add(file)

        self.print_file_report()
        if (self.found_misspelled or self.malformed_rn_files) and not self.no_failure:
            return False

        return True

    def update_known_words_from_pack(self, file_path: str) -> bool:
        """Update spellchecker with the file's pack's known words.

        Args:
            file_path: The path of the file to update the spellchecker with the packs known words.

        Return True if spellchecker was restarted, False otherwise
        """
        restarted_spellchecker = False
        if self.load_known_words_from_pack:
            known_pack_words_file_path, known_words = self.find_known_words_from_pack(
                file_path
            )
            if self.known_pack_words_file_path != known_pack_words_file_path:
                click.secho(
                    f"\nUsing known words file found within pack: {known_pack_words_file_path}",
                    fg="yellow",
                )
                if self.known_pack_words_file_path:
                    # Restart Spellchecker to remove old known_words packs file
                    self.spellchecker = SpellChecker()
                    self.known_pack_words_file_path = ""
                    restarted_spellchecker = True

            if known_pack_words_file_path:
                self.known_pack_words_file_path = known_pack_words_file_path
                if known_words:
                    # Add the new known_words packs file
                    self.spellchecker.word_frequency.load_words(known_words)

        return restarted_spellchecker

    def add_known_words(self):
        """Add known words to the spellchecker from external and internal files"""
        # adding known words file if given - these words will not count as misspelled
        if self.known_words_file_paths:
            for known_words_file_path in self.known_words_file_paths:
                self.spellchecker.word_frequency.load_text_file(known_words_file_path)

        # adding the KNOWN_WORDS to the spellchecker recognized words.
        self.spellchecker.word_frequency.load_words(KNOWN_WORDS)

        if self.expand_dictionary:
            # nltk - natural language tool kit - is a large package containing several dictionaries.
            # to use it we need to download one of it's dictionaries - we will use the
            # reasonably sized "brown" and "webtext" dicts.
            # to avoid SSL download error we disable SSL connection.
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                pass
            else:
                ssl._create_default_https_context = _create_unverified_https_context

            # downloading "brown" and "webtext" sets from nltk.
            click.secho(
                "Downloading expanded dictionary, this may take a minute...",
                fg="yellow",
            )
            nltk.download("brown")
            nltk.download("webtext")

            # adding nltk's word set to spellchecker.
            self.spellchecker.word_frequency.load_words(brown.words())
            self.spellchecker.word_frequency.load_words(webtext.words())

    @staticmethod
    def remove_punctuation(word):
        """remove leading and trailing punctuation"""
        return word.strip(string.punctuation)

    def check_word(self, word):
        """Check if a word is legal"""
        # check camel cases
        word = self.remove_punctuation(word)
        sub_words = []
        if "-" in word:
            if not self.spellchecker.unknown([word]):
                return
            sub_words.extend(word.split("-"))
        elif not self.no_camel_case and self.is_camel_case(word):
            sub_words.extend(self.camel_case_split(word))
        else:
            sub_words.append(word)

        self.unknown_words[word] = set()
        for sub_word in sub_words:
            sub_word = self.remove_punctuation(sub_word)
            if sub_word.isalpha() and self.spellchecker.unknown([sub_word]):
                self.unknown_words[word].update(
                    list(self.spellchecker.candidates(sub_word))[:5]
                )

        if not self.unknown_words[word]:
            del self.unknown_words[word]
        elif word in self.unknown_words[word]:
            # Do not suggest the same word as a correction.
            self.unknown_words[word].remove(word)

    def check_md_file(self, file_path):
        """Runs spell check on .md file. Adds unknown words to given unknown_words set.
        Also if RN file will review it and add it to malformed RN file set if needed.
        """
        pack_object: TextObject = path_to_pack_object(file_path)
        md_file_lines = pack_object.to_str().split("\n")

        if isinstance(pack_object, ReleaseNote):
            good_rn = ReleaseNotesChecker(file_path, md_file_lines).check_rn()
            if not good_rn:
                self.malformed_rn_files.add(file_path)

        for line in md_file_lines:
            for word in line.split():
                self.check_word(word)

    def check_yaml(self, file_path):
        """Runs spell check on .yml file. Adds unknown words to given unknown_words set.

        Args:
            file_path (str): The file path to the yml file.
        """
        pack_object: YAMLContentObject = path_to_pack_object(file_path)
        yml_info = pack_object.to_dict()

        if isinstance(pack_object, Integration):
            self.check_spelling_in_integration(yml_info)

        elif isinstance(pack_object, Script):
            self.check_spelling_in_script(yml_info)

        elif isinstance(pack_object, Playbook):
            self.check_spelling_in_playbook(yml_info)

    def check_spelling_in_integration(self, yml_file):
        """Check spelling on an integration file"""
        self.check_params(yml_file.get("configuration", []))
        self.check_commands(yml_file.get("script", {}).get("commands", []))
        self.check_display_and_description(
            yml_file.get("display"), yml_file.get("description")
        )

    def check_params(self, param_list):
        """Check spelling in integration parameters"""
        for param_conf in param_list:
            param_display = param_conf.get("display")
            if param_display:
                for word in param_display.split():
                    self.check_word(word)

            param_toolip = param_conf.get("additionalinfo")
            if param_toolip:
                for word in param_toolip.split():
                    self.check_word(word)

    def check_commands(self, command_list):
        """Check spelling in integration commands"""
        for command in command_list:
            command_arguments = command.get("arguments", [])
            for argument in command_arguments:
                arg_description = argument.get("description")
                if arg_description:
                    for word in arg_description.split():
                        self.check_word(word)

            command_description = command.get("description")
            if command_description:
                for word in command_description.split():
                    self.check_word(word)

            command_outputs = command.get("outputs", [])
            for output in command_outputs:
                output_description = output.get("description")
                if output_description:
                    for word in output_description.split():
                        self.check_word(word)

    def check_display_and_description(self, display, description):
        """check integration display name and description"""
        if display:
            for word in display.split():
                self.check_word(word)

        if description:
            for word in description.split():
                self.check_word(word)

    def check_spelling_in_script(self, yml_file):
        """Check spelling in script file"""
        self.check_comment(yml_file.get("comment"))
        self.check_script_args(yml_file.get("args", []))
        self.check_script_outputs(yml_file.get("outputs", []))

    def check_script_args(self, arg_list):
        """Check spelling in script arguments"""
        for argument in arg_list:
            arg_description = argument.get("description")
            if arg_description:
                for word in arg_description.split():
                    self.check_word(word)

    def check_comment(self, comment):
        """Check spelling in script comment"""
        if comment:
            for word in comment.split():
                self.check_word(word)

    def check_script_outputs(self, outputs_list):
        """Check spelling in script outputs"""
        for output in outputs_list:
            output_description = output.get("description")
            if output_description:
                for word in output_description.split():
                    self.check_word(word)

    def check_spelling_in_playbook(self, yml_file):
        """Check spelling in playbook file"""
        self.check_playbook_description_and_name(
            yml_file.get("description"), yml_file.get("name")
        )
        self.check_tasks(yml_file.get("tasks", {}))

    def check_playbook_description_and_name(self, description, name):
        """Check spelling in playbook description and name"""
        if name:
            for word in name.split():
                self.check_word(word)

        if description:
            for word in description.split():
                self.check_word(word)

    def check_tasks(self, task_dict):
        """Check spelling in playbook tasks"""
        for task_key in task_dict.keys():
            task_info = task_dict[task_key].get("task")
            if task_info:
                task_description = task_info.get("description")
                if task_description:
                    for word in task_description.split():
                        self.check_word(word)

                task_name = task_info.get("name")
                if task_name:
                    for word in task_name.split():
                        self.check_word(word)
