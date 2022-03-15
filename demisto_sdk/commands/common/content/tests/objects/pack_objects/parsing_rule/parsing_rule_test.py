from demisto_sdk.commands.common.constants import PACKS_DIR, PARSING_RULES_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import \
    ParsingRule
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PARSING_RULE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PARSING_RULES_DIR / 'parsingrule-sample.yml'
PARSING_RULE_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PARSING_RULES_DIR / 'sample_bad.yml'
PARSING_RULE_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PARSING_RULES_DIR / 'parsingrule-sample_bad.yml'


def test_objects_factory():
    obj = path_to_pack_object(PARSING_RULE)
    assert isinstance(obj, ParsingRule)


def test_prefix():
    obj = ParsingRule(PARSING_RULE)
    assert obj.normalize_file_name() == PARSING_RULE.name

    obj = ParsingRule(PARSING_RULE_BAD)
    assert obj.normalize_file_name() == PARSING_RULE_BAD_NORMALIZED.name
