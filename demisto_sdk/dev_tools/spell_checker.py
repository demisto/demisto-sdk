import yaml

from spellchecker import SpellChecker
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS
from demisto_sdk.common.constants import DISPLAYABLE_LINES, SCRIPT_ARGS, KNOWN_WORDS


class SpellCheck:
    """
        Attributes:
            path (str): The path to the current file being checked
    """

    def __init__(self, path: str):
        self.path = path
        self.spellchecker = SpellChecker()

    def run_spell_check(self):
        """Runs spell-check on the given file.

        Returns:
            int. 0 if no problematic words found, 1 otherwise.
        """
        unknown_words = set([])
        self.spellchecker.word_frequency.load_words(KNOWN_WORDS)

        if self.path.endswith('.md'):
            with open(self.path, 'r') as md_file:
                md_data = md_file.readlines()

            self.check_md_file(md_data=md_data, unknown_words=unknown_words)
        elif self.path.endswith('.yml'):
            with open(self.path, 'r') as yaml_file:
                yml_info = yaml.safe_load(yaml_file)

            self.check_yaml(yml_info=yml_info, unknown_words=unknown_words)

        else:
            print_error("The file {} is not supported for spell-check command.\n"
                        "Only .yml or .md files are supported.".format(self.path))
            return 1

        if unknown_words:
            print_error(u"Found the problematic words in {}:\n{}".format(self.path, '\n'.join(unknown_words)))
            return 1

        print_color("No problematic words found in {}".format(self.path), LOG_COLORS.GREEN)
        return 0

    def check_md_file(self, md_data, unknown_words):
        """Runs spell check on .md file. Adds unknown words to given unknown_words set.

        Args:
            md_data (list): A line list of the .md file contents
            unknown_words (set): A set of found unknown words

        Returns:
            None.
        """
        for line in md_data:
            for word in line.split():
                if word.isalpha() and self.spellchecker.unknown([word]):
                    unknown_words.add(word)

    def check_yaml(self, yml_info, unknown_words):
        """Runs spell check on .yml file. Adds unknown words to given unknown_words set.

        Args:
            yml_info (Loader): A line list of the .md file contents
            unknown_words (set): A set of found unknown words

        Returns:
            None.
        """
        for key, value in yml_info.items():
            if key in DISPLAYABLE_LINES:
                for word in value.split():
                    if word.isalpha() and self.spellchecker.unknown([word]):
                        unknown_words.add(word)

            else:
                if isinstance(value, dict):
                    if key != SCRIPT_ARGS:
                        self.check_yaml(self.spellchecker, value, unknown_words)
                elif isinstance(value, list):
                    for sub_list in value:
                        if isinstance(sub_list, dict):
                            self.check_yaml(self.spellchecker, sub_list, unknown_words)

    @staticmethod
    def add_sub_parser(subparsers):
        from argparse import ArgumentDefaultsHelpFormatter
        description = """Run spell check on a given yml/md file. """
        parser = subparsers.add_parser('spell-check', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-p", "--path", help="Specify path of yml/md file", required=True)
