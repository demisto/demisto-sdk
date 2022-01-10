import os
import re
import ssl
import string
import sys
from typing import Dict, Set

import click
import nltk
from nltk.corpus import brown, webtext
from spellchecker import SpellChecker

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content import (Integration, Playbook,
                                                 ReleaseNote, Script,
                                                 path_to_pack_object)
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    TextObject
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.doc_reviewer.known_words import KNOWN_WORDS
from demisto_sdk.commands.doc_reviewer.rn_checker import ReleaseNotesChecker


class DocReviewer:
    """Perform a spell check on the given .yml or .md file.
    """

    SUPPORTED_FILE_TYPES = [FileType.INTEGRATION, FileType.SCRIPT, FileType.PLAYBOOK, FileType.README,
                            FileType.DESCRIPTION, FileType.RELEASE_NOTES, FileType.BETA_INTEGRATION,
                            FileType.TEST_PLAYBOOK, FileType.TEST_SCRIPT]

    def __init__(self, file_path: str, known_words_file_path: str = None, no_camel_case: bool = False,
                 no_failure: bool = False, expand_dictionary: bool = False, templates: bool = False,
                 use_git: bool = False, prev_ver: str = None, release_notes_only: bool = False):
        if templates:
            ReleaseNotesChecker(template_examples=True)
            sys.exit(0)

        # if nothing entered will default to use git
        elif not file_path and not use_git:
            use_git = True

        self.file_path = file_path
        self.git_util = None
        self.prev_ver = prev_ver if prev_ver else 'demisto/master'

        if use_git:
            self.git_util = GitUtil()

        if release_notes_only:
            self.SUPPORTED_FILE_TYPES = [FileType.RELEASE_NOTES]

        self.files = set()  # type:Set
        self.spellchecker = SpellChecker()
        self.unknown_words = {}  # type:Dict
        self.no_camel_case = no_camel_case
        self.known_words_file_path = known_words_file_path
        self.found_misspelled = False
        self.no_failure = no_failure
        self.expand_dictionary = expand_dictionary
        self.files_with_misspells = set()  # type:Set
        self.files_without_misspells = set()  # type:Set
        self.malformed_rn_files = set()  # type:Set

    @staticmethod
    def is_camel_case(word):
        """check if a given word is in camel case"""
        return word != word.lower() and word != word.upper() and "_" not in word and word != word.title()

    @staticmethod
    def camel_case_split(camel):
        """split camel case word into sub-words"""
        tokens = re.compile('([A-Z]?[a-z]+)').findall(camel)
        for token in tokens:
            # double space to handle capital words like IP/URL/DNS that not included in the regex
            camel = camel.replace(token, f' {token} ')

        return camel.split()

    def get_all_md_and_yml_files_in_dir(self, dir_name):
        """recursively get all the supported files from a given dictionary"""
        for root, _, files in os.walk(dir_name):
            for file_name in files:
                full_path = (os.path.join(root, file_name))
                if find_type(full_path) in self.SUPPORTED_FILE_TYPES:
                    self.files.add(str(full_path))

    def gather_all_changed_files(self):
        modified = self.git_util.modified_files(prev_ver=self.prev_ver)  # type: ignore[union-attr]
        added = self.git_util.added_files(prev_ver=self.prev_ver)  # type: ignore[union-attr]
        renamed = self.git_util.renamed_files(prev_ver=self.prev_ver, get_only_current_file_names=True)  # type: ignore[union-attr]

        return modified.union(added).union(renamed)  # type: ignore[arg-type]

    def get_files_from_git(self):
        click.secho('Gathering all changed files from git', fg='bright_cyan')
        for file in self.gather_all_changed_files():
            file = str(file)
            if os.path.isfile(file) and find_type(file) in self.SUPPORTED_FILE_TYPES:
                self.files.add(file)

    def get_files_to_run_on(self):
        """Get all the relevant files that the spell-check could work on"""
        if self.git_util:
            self.get_files_from_git()

        elif os.path.isdir(self.file_path):
            self.get_all_md_and_yml_files_in_dir(self.file_path)

        elif find_type(self.file_path) in self.SUPPORTED_FILE_TYPES:
            self.files.add(self.file_path)

    def print_unknown_words(self):
        for word, corrections in self.unknown_words.items():
            click.secho(f'  - {word} - did you mean: {corrections}', fg='bright_red')

    def print_file_report(self):
        if self.files_without_misspells:
            click.secho('\n================= Files Without Misspells =================', fg='green')
            no_misspells_string = '\n'.join(self.files_without_misspells)
            click.secho(no_misspells_string, fg='green')

        if self.files_with_misspells:
            click.secho('\n================= Files With Misspells =================', fg='bright_red')
            misspells_string = '\n'.join(self.files_with_misspells)
            click.secho(misspells_string, fg='bright_red')

        if self.malformed_rn_files:
            click.secho('\n================= Malformed Release Notes =================', fg='bright_red')
            bad_rn = '\n'.join(self.malformed_rn_files)
            click.secho(bad_rn, fg='bright_red')

    def run_doc_review(self):
        """Runs spell-check on the given file and release notes check if relevant.

        Returns:
            bool. True if no problematic words found, False otherwise.
        """
        click.secho('\n================= Starting Doc Review =================', fg='bright_cyan')
        if len(self.SUPPORTED_FILE_TYPES) == 1:
            click.secho('Running only on release notes', fg='bright_cyan')

        self.get_files_to_run_on()

        # no eligible files found
        if not self.files:
            click.secho("Could not find any .md or .yml files - Aborting", fg='bright_red')
            return True

        self.add_known_words()
        for file in self.files:
            click.echo(f'\nChecking spelling on {file}')
            self.unknown_words = {}
            if file.endswith('.md'):
                self.check_md_file(file)

            elif file.endswith('.yml'):
                self.check_yaml(file)

            if self.unknown_words:
                click.secho(f"\n - Words that might be misspelled were found in "
                            f"{file}:", fg='bright_red')
                self.print_unknown_words()
                self.found_misspelled = True
                self.files_with_misspells.add(file)

            else:
                click.secho(f" - No misspelled words found in {file}", fg='green')
                self.files_without_misspells.add(file)

        self.print_file_report()
        if self.found_misspelled and not self.no_failure:
            return False

        return True

    def add_known_words(self):
        """Add known words to the spellchecker from external and internal files"""
        # adding known words file if given - these words will not count as misspelled
        if self.known_words_file_path:
            self.spellchecker.word_frequency.load_text_file(self.known_words_file_path)

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
            click.secho("Downloading expanded dictionary, this may take a minute...", fg='yellow')
            nltk.download('brown')
            nltk.download('webtext')

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
        if not self.no_camel_case and self.is_camel_case(word):
            sub_words = self.camel_case_split(word)
            for sub_word in sub_words:
                sub_word = self.remove_punctuation(sub_word)
                if sub_word.isalpha() and self.spellchecker.unknown([sub_word]):
                    self.unknown_words[word] = list(self.spellchecker.candidates(sub_word))[:5]

        else:
            word = self.remove_punctuation(word)
            if word.isalpha() and self.spellchecker.unknown([word]):
                self.unknown_words[word] = list(self.spellchecker.candidates(word))[:5]

    def check_md_file(self, file_path):
        """Runs spell check on .md file. Adds unknown words to given unknown_words set.
        Also if RN file will review it and add it to malformed RN file set if needed.
        """
        pack_object: TextObject = path_to_pack_object(file_path)
        md_file_lines = pack_object.to_str().split('\n')

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
        self.check_params(yml_file.get('configuration', []))
        self.check_commands(yml_file.get('script', {}).get('commands', []))
        self.check_display_and_description(yml_file.get('display'), yml_file.get('description'))

    def check_params(self, param_list):
        """Check spelling in integration parameters"""
        for param_conf in param_list:
            param_display = param_conf.get('display')
            if param_display:
                for word in param_display.split():
                    self.check_word(word)

            param_toolip = param_conf.get('additionalinfo')
            if param_toolip:
                for word in param_toolip.split():
                    self.check_word(word)

    def check_commands(self, command_list):
        """Check spelling in integration commands"""
        for command in command_list:
            command_arguments = command.get('arguments', [])
            for argument in command_arguments:
                arg_description = argument.get('description')
                if arg_description:
                    for word in arg_description.split():
                        self.check_word(word)

            command_description = command.get('description')
            if command_description:
                for word in command_description.split():
                    self.check_word(word)

            command_outputs = command.get('outputs', [])
            for output in command_outputs:
                output_description = output.get('description')
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
        self.check_comment(yml_file.get('comment'))
        self.check_script_args(yml_file.get('args', []))
        self.check_script_outputs(yml_file.get('outputs', []))

    def check_script_args(self, arg_list):
        """Check spelling in script arguments"""
        for argument in arg_list:
            arg_description = argument.get('description')
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
            output_description = output.get('description')
            if output_description:
                for word in output_description.split():
                    self.check_word(word)

    def check_spelling_in_playbook(self, yml_file):
        """Check spelling in playbook file"""
        self.check_playbook_description_and_name(yml_file.get('description'), yml_file.get('name'))
        self.check_tasks(yml_file.get('tasks', {}))

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
            task_info = task_dict[task_key].get('task')
            if task_info:
                task_description = task_info.get('description')
                if task_description:
                    for word in task_description.split():
                        self.check_word(word)

                task_name = task_info.get('name')
                if task_name:
                    for word in task_name.split():
                        self.check_word(word)
