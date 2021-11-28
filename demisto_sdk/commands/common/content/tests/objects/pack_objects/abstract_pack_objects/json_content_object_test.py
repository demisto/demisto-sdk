from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR, DEFAULT_CONTENT_ITEM_FROM_VERSION, PACKS_DIR)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_JSON_NO_FROM_VERSION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CLASSIFIERS_DIR / 'classifier-sample_new.json'


def test_to_version_no_from_version(datadir):
    from packaging.version import parse
    obj = JSONContentObject(TEST_JSON_NO_FROM_VERSION, "classifier")
    assert obj.from_version == parse(DEFAULT_CONTENT_ITEM_FROM_VERSION)
    assert obj.to_version == parse("4.0.0")


class TestFileWithStem:
    def test_with_readme_change_log(self):
        obj = JSONContentObject(TEST_JSON_NO_FROM_VERSION, "classifier")

        assert obj.readme is not None
        assert obj.changelog is not None
