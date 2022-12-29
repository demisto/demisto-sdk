from demisto_sdk.commands.common.content.objects.pack_objects import CorrelationRule
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object


def get_correlation_rule(pack, name):
    return pack.create_correlation_rule(
        name,
        {
            "global_rule_id": "correlation_rule_id",
            "rules": "",
            "name": "correlation_rule_name",
        },
    )


def test_objects_factory(pack):
    correlation_rule = get_correlation_rule(pack, "correlation_rule_name")
    obj = path_to_pack_object(correlation_rule.correlation_rule_tmp_path)
    assert isinstance(obj, CorrelationRule)


def test_prefix(pack):
    correlation_rule = get_correlation_rule(
        pack, "external-correlationrule-correlation_rule_name"
    )

    obj = CorrelationRule(correlation_rule.correlation_rule_tmp_path)
    assert obj.normalize_file_name() == correlation_rule.correlation_rule_tmp_path.name

    correlation_rule = get_correlation_rule(pack, "correlation_rule_name")

    obj = CorrelationRule(correlation_rule.correlation_rule_tmp_path)
    assert (
        obj.normalize_file_name()
        == f"external-correlationrule-{correlation_rule.correlation_rule_tmp_path.name}"
    )
