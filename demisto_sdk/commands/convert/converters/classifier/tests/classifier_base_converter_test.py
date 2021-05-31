import os
from typing import Dict

import pytest

from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from de


class TestLayoutBaseConverter:
    TEST_PACK_PATH = os.path.join(__file__,
                                  f'{git_path()}/demisto_sdk/commands/convert/converters/classifier/tests/test_data/Packs'
                                  f'/ExtraHop')
    SCHEMA_PATH = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data',
                     'layoutscontainer.yml'))

    def setup(self):
        self.classifier_converter = LayoutBaseConverter(Pack(self.TEST_PACK_PATH))

