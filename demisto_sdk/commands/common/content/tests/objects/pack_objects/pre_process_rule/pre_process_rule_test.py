from demisto_sdk.commands.common.constants import (PACKS_DIR,
                                                   PRE_PROCESS_RULES_DIR)
from demisto_sdk.commands.common.content.objects.pack_objects import \
    PreProcessRule
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PRE_PROCESS_RULE_GOOD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PRE_PROCESS_RULES_DIR / 'preprocessrule-Drop.json'
PRE_PROCESS_RULE_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PRE_PROCESS_RULES_DIR / 'sample_bad.json'
PRE_PROCESS_RULE_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PRE_PROCESS_RULES_DIR / 'preprocessrule-sample_bad.json'


def test_objects_factory():
    obj = path_to_pack_object(PRE_PROCESS_RULE_GOOD)
    assert isinstance(obj, PreProcessRule)


def test_prefix():
    obj = PreProcessRule(PRE_PROCESS_RULE_GOOD)
    assert obj.normalize_file_name() == PRE_PROCESS_RULE_GOOD.name

    obj = PreProcessRule(PRE_PROCESS_RULE_BAD)
    assert obj.normalize_file_name() == PRE_PROCESS_RULE_BAD_NORMALIZED.name
