from demisto_sdk.commands.common.constants import PACKS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.base_pack_objects.yaml_pack_object import \
    YAMLPackObject
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_YAML_NO_FROM_VERSION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / SCRIPTS_DIR / 'script-sample_new.yml'
TEST_YAML_NO_TO_VERSION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / SCRIPTS_DIR / 'script-sample_packs.yml'


def test_from_version_no_to_version(datadir):
    from packaging.version import parse
    obj = YAMLPackObject(TEST_YAML_NO_TO_VERSION, "script")
    assert obj.from_version == parse("6.0.0")
    assert obj.to_version == parse("99.99.99")


def test_to_version_no_from_version(datadir):
    from packaging.version import parse
    obj = YAMLPackObject(TEST_YAML_NO_FROM_VERSION, "script")
    assert obj.from_version == parse("0.0.0")
    assert obj.to_version == parse("5.0.0")


class TestFileWithStem:
    def test_with_readme_change_log(self):
        obj = YAMLPackObject(TEST_YAML_NO_FROM_VERSION, "script")

        assert obj.readme is not None

    def test_without_readme_changelog(self):
        obj = YAMLPackObject(TEST_YAML_NO_TO_VERSION, "script")

        assert obj.readme is None
