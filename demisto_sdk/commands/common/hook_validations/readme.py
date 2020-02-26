import subprocess
import re
import os
from demisto_sdk.commands.common.tools import print_error, get_latest_release_notes_text, \
    get_release_notes_file_path


class ReadMeValidator:
    def __init__(self, file_path):
        self.file_path = file_path

    def is_file_valid(self):
        mdx_parse = f'{os.path.dirname(os.path.abspath(__file__))}/../mdx-parse.js'
        res = subprocess.run(['node', mdx_parse, '-f', self.file_path], text=True, timeout=10, capture_output=True)
        if res.returncode != 0:
            print_error(f'Failed verfiying: {self.file_path}. Error: {res.stderr}')
            return False
        return True



