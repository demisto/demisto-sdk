from demisto_sdk.commands.common.content.objects.pack_objects import \
    ParsingRule
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object


def get_parsing_rule(pack, name):
    return pack.create_parsing_rule(name, {"id": "parsing_rule_id", "rules": "", "name": "parsing_rule_name"})


def test_objects_factory(pack):
    parsing_rule = get_parsing_rule(pack, 'parsing_rule_name')
    obj = path_to_pack_object(parsing_rule.parsing_rule_tmp_path)
    assert isinstance(obj, ParsingRule)


def test_prefix(pack):
    parsing_rule = get_parsing_rule(pack, 'parsingrule-parsing_rule_name')

    obj = ParsingRule(parsing_rule.parsing_rule_tmp_path)
    assert obj.normalize_file_name() == parsing_rule.parsing_rule_tmp_path.name

    parsing_rule = get_parsing_rule(pack, 'parsing_rule_name')

    obj = ParsingRule(parsing_rule.parsing_rule_tmp_path)
    assert obj.normalize_file_name() == f"parsingrule-{parsing_rule.parsing_rule_tmp_path.name}"
