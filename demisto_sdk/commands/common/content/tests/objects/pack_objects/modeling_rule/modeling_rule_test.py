from demisto_sdk.commands.common.content.objects.pack_objects import \
    ModelingRule
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object


def get_modeling_rule(pack, name):
    return pack.create_modeling_rule(name, {"id": "modeling_rule_id", "rules": "", "name": "modeling_rule_name"})


def test_objects_factory(pack):
    modeling_rule = get_modeling_rule(pack, 'modeling_rule_name')
    obj = path_to_pack_object(modeling_rule.modeling_rule_tmp_path)
    assert isinstance(obj, ModelingRule)


def test_prefix(pack):
    modeling_rule = get_modeling_rule(pack, 'modelingrule-modeling_rule_name')

    obj = ModelingRule(modeling_rule.modeling_rule_tmp_path)
    assert obj.normalize_file_name() == modeling_rule.modeling_rule_tmp_path.name

    modeling_rule = get_modeling_rule(pack, 'modeling_rule_name')

    obj = ModelingRule(modeling_rule.modeling_rule_tmp_path)
    assert obj.normalize_file_name() == f"modelingrule-{modeling_rule.modeling_rule_tmp_path.name}"
