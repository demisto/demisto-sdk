from demisto_sdk.commands.common.constants import (CORRELATION_RULES_DIR,
                                                   PACKS_DIR)
from demisto_sdk.commands.common.content.objects.pack_objects import \
    CorrelationRule
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
CORRELATION_RULE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CORRELATION_RULES_DIR / 'correlationrule-sample.yml'
CORRELATION_RULE_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CORRELATION_RULES_DIR / 'sample_bad.yml'
CORRELATION_RULE_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CORRELATION_RULES_DIR / 'correlationrule-sample_bad.yml'


def test_objects_factory():
    obj = path_to_pack_object(CORRELATION_RULE)
    assert isinstance(obj, CorrelationRule)


def test_prefix():
    obj = CorrelationRule(CORRELATION_RULE)
    assert obj.normalize_file_name() == CORRELATION_RULE.name

    obj = CorrelationRule(CORRELATION_RULE_BAD)
    assert obj.normalize_file_name() == CORRELATION_RULE_BAD_NORMALIZED.name
