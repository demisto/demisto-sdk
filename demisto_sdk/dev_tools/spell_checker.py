import yaml
from typing import Set
from spellchecker import SpellChecker

from argparse import ArgumentDefaultsHelpFormatter
from demisto_sdk.common.constants import KNOWN_WORDS
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS


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
            path (str): The path to the current file being checked.
            known_words (str): The path to a file containing known words.
            spellchecker (SpellChecker): The spell-checking object.
            unknown_words (set): A set of unknown words found in the given file.
    """

    def __init__(self, checked_file_path: str, known_words: str):
        self.checked_file_path = checked_file_path
        self.spellchecker = SpellChecker()
        self.unknown_words = set([])  # type:Set
        self.known_words = known_words

    def run_spell_check(self):
        """Runs spell-check on the given file.

        Returns:
            bool. True if no problematic words found, False otherwise.
        """
        # adding known words file if given - these words will not count as misspelled
        if self.known_words:
            known_words_file = open(self.known_words, 'r')
            self.spellchecker.word_frequency.load_text_file(known_words_file)

        # adding the KNOWN_WORDS to the spellchecker recognized words.
        self.spellchecker.word_frequency.load_words(KNOWN_WORDS)
        if self.checked_file_path.endswith('.md'):
            self.check_md_file()

        elif self.checked_file_path.endswith('.yml'):
            with open(self.checked_file_path, 'r') as yaml_file:
                yml_info = yaml.safe_load(yaml_file)

            self.check_yaml(yml_info=yml_info)

        else:
            print_error("The file {} is not supported for spell-check command.\n"
                        "Only .yml or .md files are supported.".format(self.checked_file_path))
            return False

        if self.unknown_words:
            print_error(u"Words that might be misspelled were found in {}:\n\n{}".format(
                self.checked_file_path, '\n'.join(self.unknown_words)))
            return False

        print_color("No misspelled words found in {}".format(self.checked_file_path), LOG_COLORS.GREEN)
        return True

    def check_md_file(self):
        """Runs spell check on .md file. Adds unknown words to given unknown_words set.
        """
        with open(self.checked_file_path, 'r') as md_file:
            md_file_lines = md_file.readlines()

        for line in md_file_lines:
            for word in line.split():
                if word.isalpha() and self.spellchecker.unknown([word]):
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
                    # ignore command arguments in playbooks - no need to check these.
                    if key != 'scriptarguments':
                        self.check_yaml(value)

                # case 3: a list of dictionaries
                elif isinstance(value, list):
                    for sub_dict in value:
                        if isinstance(sub_dict, dict):
                            self.check_yaml(sub_dict)

    @staticmethod
    def add_sub_parser(subparsers):
        description = """Run spell check on a given yml/md file. """
        parser = subparsers.add_parser('spell-check', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-p", "--path", help="Specify path of yml/md file", required=True)
        parser.add_argument("--known_words", help="A file path to a txt file with known words")
