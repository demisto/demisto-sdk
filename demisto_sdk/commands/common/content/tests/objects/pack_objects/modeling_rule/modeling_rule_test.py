from demisto_sdk.commands.common.constants import MODELING_RULES_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import \
    ModelingRule
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
MODELING_RULE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / MODELING_RULES_DIR / 'modelingrule-sample.yml'
MODELING_RULE_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / MODELING_RULES_DIR / 'sample_bad.yml'
MODELING_RULE_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / MODELING_RULES_DIR / 'modelingrule-sample_bad.yml'


def test_objects_factory():
    obj = path_to_pack_object(MODELING_RULE)
    assert isinstance(obj, ModelingRule)


def test_prefix():
    obj = ModelingRule(MODELING_RULE)
    assert obj.normalize_file_name() == MODELING_RULE.name

    obj = ModelingRule(MODELING_RULE_BAD)
    assert obj.normalize_file_name() == MODELING_RULE_BAD_NORMALIZED.name