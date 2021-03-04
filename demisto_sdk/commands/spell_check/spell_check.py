import os
import ssl
from typing import Set

import click
import nltk
import yaml
from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.known_words import KNOWN_WORDS
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type,
                                               print_color, print_error)
from nltk.corpus import words
from spellchecker import SpellChecker

# These are keys in a Demisto yml file which indicate that their values are visible to the user and
# thus their spelling should be checked.
USER_VISIBLE_LINE_KEYS = [
    "description",
    "display",
    "name",
    "comment"
]


class SpellCheck:
    """Perform a spell check on the given .yml or .md file.
        Attributes:
            checked_file_path (str): The path to the current file being checked.
            known_words_file_path (str): The path to a file containing known words.
            spellchecker (SpellChecker): The spell-checking object.
            unknown_words (set): A set of unknown words found in the given file.
    """

    SUPPORTED_FILE_TYPES = [FileType.INTEGRATION, FileType.SCRIPT, FileType.PLAYBOOK, FileType.README,
                            FileType.DESCRIPTION, FileType.RELEASE_NOTES]

    def __init__(self, file_path: str, known_words_file_path: str = None, no_camel_case: bool = False):
        self.file_path = file_path
        self.files = set()
        self.spellchecker = SpellChecker()
        self.unknown_words = set()  # type:Set
        self.no_camel_case = no_camel_case
        self.known_words_file_path = known_words_file_path
        self.found_misspelled = False

    @staticmethod
    def is_camel_case(word):
        return word != word.lower() and word != word.upper() and "_" not in word

    @staticmethod
    def camel_case_split(camel):
        words = [[camel[0]]]

        for char in camel[1:]:
            if words[-1][-1].islower() and char.isupper():
                words.append(list(char))
            else:
                words[-1].append(char)

        return [''.join(word) for word in words]

    def get_all_md_and_yml_files_in_dir(self, dir_name):
        for rest_of_path in os.listdir(dir_name):
            full_path = os.path.join(dir_name, rest_of_path)
            if os.path.isdir(full_path):
                self.get_all_md_and_yml_files_in_dir(full_path)

            elif find_type(full_path) in self.SUPPORTED_FILE_TYPES:
                self.files.add(str(full_path))

    def get_files_to_run_on(self):
        if os.path.isdir(self.file_path):
            self.get_all_md_and_yml_files_in_dir(self.file_path)

        elif find_type(self.file_path) in self.SUPPORTED_FILE_TYPES:
            self.files.add(self.file_path)

    def run_spell_check(self):
        """Runs spell-check on the given file.

        Returns:
            bool. True if no problematic words found, False otherwise.
        """
        self.get_files_to_run_on()

        # no eligible files found
        if not self.files:
            click.secho(f"The path {self.file_path} does not contain any .md or .yml files", fg='bright_red')
            return True

        self.add_known_words()
        for file in self.files:
            self.unknown_words = set()
            if file.endswith('.md'):
                self.check_md_file()

            elif file.endswith('.yml'):
                with open(file, 'r') as yaml_file:
                    yml_info = yaml.safe_load(yaml_file)

                self.check_yaml(yml_info=yml_info)

            if len(self.unknown_words) > 0:
                print_error(u"\nWords that might be misspelled were found in {}:\n\n{}".format(
                    file, '\n'.join(self.unknown_words)))
                self.found_misspelled = True

            else:
                print_color("\nNo misspelled words found in {}".format(file), LOG_COLORS.GREEN)

        if self.found_misspelled:
            return False

        return True

    def add_known_words(self):
        # adding known words file if given - these words will not count as misspelled
        if self.known_words_file_path:
            with open(self.known_words_file_path, 'r') as known_words_file:
                self.spellchecker.word_frequency.load_text_file(known_words_file)

        # adding the KNOWN_WORDS to the spellchecker recognized words.
        self.spellchecker.word_frequency.load_words(KNOWN_WORDS)

        # # nltk - natural language tool kit - is a large package containing several dictionaries.
        # # to use it we need to download one of it's dictionaries - we will use the reasonably sized "words" dict.
        # # to avoid SSL download error  we disable SSL connection.
        # try:
        #     _create_unverified_https_context = ssl._create_unverified_context
        # except AttributeError:
        #     pass
        # else:
        #     ssl._create_default_https_context = _create_unverified_https_context
        #
        # # downloading "words" set from nltk.
        # print_color("Downloading dictionary, this may take a minute...", LOG_COLORS.YELLOW)
        # nltk.download('words')
        #
        # # adding nltk's word set to spellchecker.
        # self.spellchecker.word_frequency.load_words(words.words())

    def check_md_file(self, file_path):
        """Runs spell check on .md file. Adds unknown words to given unknown_words set.
        """
        with open(file_path, 'r') as md_file:
            md_file_lines = md_file.readlines()

        for line in md_file_lines:
            for word in line.split():

                # check camel cases
                if not self.no_camel_case and self.is_camel_case(word):
                    sub_words = self.camel_case_split(word)
                    for sub_word in sub_words:
                        if sub_word.isalpha() and self.spellchecker.unknown([sub_word]):
                            self.unknown_words.add(word)

                elif word.isalpha() and self.spellchecker.unknown([word]):
                    self.unknown_words.add(word)

    def check_yaml(self, yml_info):
        """Runs spell check on .yml file. Adds unknown words to given unknown_words set.

        Args:
            yml_info (Loader): A line list of the .md file contents
        """
        # yml file is parsed as a large dictionary. Each key in the large dictionary
        # has a value which can be comprised of a string, a sub-dictionary or a list of dictionaries.
        # The following code separates the spell check to these cases.
        for key, value in yml_info.items():
            # case 1: the value is a user visible string.
            if key in USER_VISIBLE_LINE_KEYS:

                # separate the string to individual words
                for word in value.split():

                    # Drop commas, full-stops and brackets.
                    if word.endswith(',') or word.endswith('.') or word.endswith(')') or word.endswith(':'):
                        word = word[:-1]

                    if word.startswith('('):
                        word = word[1:]

                    # if a word is comprised of only letters (no punctuation ia checked!)
                    if word.isalpha() and self.spellchecker.unknown([word]):
                        self.unknown_words.add(word)

            else:
                # case 2: a sub-dictionary
                if isinstance(value, dict):
                    # 'scriptarguments' is the field name for command arguments in  playbooks.
                    if key != 'scriptarguments':
                        self.check_yaml(value)

                # case 3: a list of dictionaries
                elif isinstance(value, list):
                    for sub_dict in value:
                        if isinstance(sub_dict, dict):
                            self.check_yaml(sub_dict)
