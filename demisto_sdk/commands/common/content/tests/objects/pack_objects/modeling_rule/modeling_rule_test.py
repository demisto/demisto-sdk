from demisto_sdk.commands.common.content.objects.pack_objects import ModelingRule
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import get_yaml

PRE_UNIFIED_MODELING_RULE_XIF_TEXT = """
[MODEL: dataset=fake_fake_raw, model=Network]
alter XDM.Network.original_event_type=action,
      XDM.Network.Destination.host.os_family=device,
      XDM.Network.Destination.host.hostname=coalesce(dsthost, hostname),
      XDM.Network.Destination.ipv4=dstip,
      XDM.Network.Destination.port=dstport,
      XDM.Network.duration=session_duration,
      XDM.Network.Source.ipv4=srcip,
      XDM.Network.Source.port=srcport,
      XDM.Network.event_timestamp=to_timestamp(to_integer(timestamp), "SECONDS"),
      XDM.Network.Source.packets=total_packets,
      XDM.Network.Destination.user.username=user,
      XDM.Network.Destination.user.identifier=userkey,
      XDM.Network.http.user_agent = useragent;

[MODEL: dataset=fake_fake_raw, model=Audit]
alter XDM.Audit.threat.severity=severity_level,
      XDM.Audit.event_timestamp=to_timestamp(to_integer(timestamp), "SECONDS"),
      XDM.Audit.TriggeredBy.identity.name=user,
      XDM.Audit.original_event_description=audit_log_event,
      XDM.Audit.original_event_type=type
| filter activity not in ("SignInEvent","Logout","Login Attempt","Login Successful","Login Failed")
| alter XDM.Audit.original_event_type=activity,
        XDM.Audit.reason=alert,
        XDM.Audit.threat.original_alert_id=to_string(incident_id),
        XDM.Audit.TriggeredBy.location.country=src_country,
        XDM.Audit.TriggeredBy.location.city=src_location,
        XDM.Audit.TriggeredBy.location.region=src_region,
        XDM.Audit.TriggeredBy.ipv4=coalesce(srcip, userip),
        //XDM.Audit.event_timestamp=to_timestamp(to_integer(timestamp), "SECONDS"),
        XDM.Audit.TriggeredBy.identity.name=user,
        XDM.Audit.TriggeredBy.user_agent = useragent;

[MODEL: dataset=fake_fake_raw, model=Auth]
filter activity in ("SignInEvent","Logout","Login Attempt","Login Successful","Login Failed")
| alter XDM.Auth.auth_method=access_method,
        XDM.Auth.original_event_type=activity,
        XDM.Auth.Target.application.name=coalesce(app, managed_app),
        XDM.Auth.Client.host.hostname=device,
        XDM.Auth.Client.location.country=dst_country,
        XDM.Auth.Client.location.region=dst_region,
        XDM.Auth.threat.severity=severity,
        XDM.Auth.Client.process.executable.sha256=coalesce(_sha256, sha256),
        XDM.Auth.kerberos.padata_type=data_type,
        XDM.Auth.Client.user_agent = useragent;
"""
PRE_UNIFIED_RULE1_FIELDS = {
    "_time",
    "xdm.network.original_event_type",
    "xdm.network.destination.host.os_family",
    "xdm.network.destination.host.hostname",
    "xdm.network.destination.ipv4",
    "xdm.network.destination.port",
    "xdm.network.duration",
    "xdm.network.source.ipv4",
    "xdm.network.source.port",
    "xdm.network.event_timestamp",
    "xdm.network.source.packets",
    "xdm.network.destination.user.username",
    "xdm.network.destination.user.identifier",
    "xdm.network.http.user_agent",
}
PRE_UNIFIED_RULE2_FIELDS = {
    "_time",
    "xdm.audit.threat.severity",
    "xdm.audit.event_timestamp",
    "xdm.audit.triggeredby.identity.name",
    "xdm.audit.original_event_description",
    "xdm.audit.original_event_type",
    "xdm.audit.original_event_type",
    "xdm.audit.reason",
    "xdm.audit.threat.original_alert_id",
    "xdm.audit.triggeredby.location.country",
    "xdm.audit.triggeredby.location.city",
    "xdm.audit.triggeredby.location.region",
    "xdm.audit.triggeredby.ipv4",
    "xdm.audit.triggeredby.identity.name",
    "xdm.audit.triggeredby.user_agent",
}
PRE_UNIFIED_RULE3_FIELDS = {
    "_time",
    "xdm.auth.auth_method",
    "xdm.auth.original_event_type",
    "xdm.auth.target.application.name",
    "xdm.auth.client.host.hostname",
    "xdm.auth.client.location.country",
    "xdm.auth.client.location.region",
    "xdm.auth.threat.severity",
    "xdm.auth.client.process.executable.sha256",
    "xdm.auth.kerberos.padata_type",
    "xdm.auth.client.user_agent",
}
UNIFIED_RULE_XIF = """
[MODEL: dataset="fake_faker_raw"]
filter
    user = null
| alter
    xdm.event.description = comments,
    xdm.event.outcome = json_extract_scalar(kind, "$.value"),
    xdm.target.resource.id = to_string(json_extract(assigned_object, "$.id")),
    xdm.target.resource.name = json_extract_scalar(assigned_object, "$.name"),
    xdm.target.resource.type = assigned_object_type,
    xdm.network.source.ipv4 = "8.8.8.8";
filter
    user != null
| alter
    xdm.event.id = request_id,
    xdm.event.description = display,
    xdm.event.operation = json_extract_scalar(action, "$.value"),
    xdm.target.resource.id = to_string(changed_object_id),
    xdm.target.resource.name = json_extract_scalar(changed_object, "$.display"),
    xdm.target.resource.type = changed_object_type,
    xdm.target.resource_before.name = json_extract_scalar(prechange_data, "$.name"),
    xdm.source.user.username = user_name;
"""
UNIFIED_RULE_XIF_WITH_ARBITRARY_WHITESPACE = """
[MODEL: dataset="fake_faker_raw"]
filter
    user = null
| alter
    xdm.event.description = comments,
    xdm.event.outcome = json_extract_scalar(kind, "$.value"),
    xdm.target.resource.id = to_string(json_extract(assigned_object, "$.id")),
    xdm.target.resource.name = json_extract_scalar(assigned_object, "$.name"),
    xdm.target.resource.type = assigned_object_type;


filter
    user != null

| alter
    xdm.event.id = request_id,
    xdm.event.description = display,
    xdm.event.operation = json_extract_scalar(action, "$.value"),
    xdm.target.resource.id = to_string(changed_object_id),
    xdm.target.resource.name = json_extract_scalar(changed_object, "$.display"),
    xdm.target.resource.type = changed_object_type,
    xdm.target.resource_before.name = json_extract_scalar(prechange_data, "$.name"),
    xdm.source.user.username = user_name,
    xdm.network.source.ipv4 = "8.8.8.8";
"""
UNIFIED_RULE_FIELDS = {
    "_time",
    "xdm.event.description",
    "xdm.event.outcome",
    "xdm.target.resource.id",
    "xdm.target.resource.name",
    "xdm.target.resource.type",
    "xdm.event.id",
    "xdm.event.operation",
    "xdm.target.resource_before.name",
    "xdm.source.user.username",
    "xdm.network.source.ipv4",
}


def get_modeling_rule(pack, name):
    return pack.create_modeling_rule(name)


class TestModelingRule:
    def test_objects_factory(self, pack):
        modeling_rule = get_modeling_rule(pack, "modeling_rule_name")
        obj = path_to_pack_object(modeling_rule.yml._tmp_path)
        assert isinstance(obj, ModelingRule)

    def test_prefix(self, pack):
        modeling_rule = get_modeling_rule(
            pack, "external-modelingrule-modeling_rule_name"
        )
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        assert obj.normalize_file_name() == modeling_rule.yml._tmp_path.name

        modeling_rule = get_modeling_rule(pack, "modeling_rule_name")
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        assert (
            obj.normalize_file_name()
            == f"external-modelingrule-{modeling_rule.yml._tmp_path.name}"
        )

    def test_files_detection(self, pack):
        modeling_rule = get_modeling_rule(pack, "modeling_rule_name")
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        # assert obj.yml._tmp_path == Path(datadir["README.md"])
        assert obj.rules_path == modeling_rule.rules._tmp_path

    def test_is_unify(self, pack):
        modeling_rule = get_modeling_rule(pack, "modeling_rule_name")
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        assert not obj.is_unify()

    def test_unify_schema(self, pack):
        """
        Given:
        modeling rule:
        - yml file
        - the rule xif file
        - the schema json file
        When:
         - we want to unify all files to one unified yml file.

         Then:
         - Ensure the schema was unified successfully.
        """
        modeling_rule = get_modeling_rule(pack, "modeling_rule_name")
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        unify_obj = get_yaml(obj._unify(modeling_rule._tmpdir_rule_path)[0])
        assert (
            unify_obj["schema"]
            == '{\n    "test_audit_raw": {\n        "name": {\n            "type": "string",\n'
            '            "is_array": false\n        }\n    }\n}'
        )


class TestModelingRules_XSIAM_1_3_Migration:
    @staticmethod
    def test_dump_XSIAM_1_2_rule(pack):
        modeling_rule = pack.create_modeling_rule(
            yml={
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": "6.8.0",
                "toversion": "6.99.99",
                "tags": "tag",
                "rules": "",
                "schema": "",
            }
        )
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        created_files = obj.dump(modeling_rule._tmpdir_rule_path)

        assert len(created_files) == 1
        assert not created_files[0].name.startswith("external-")

    @staticmethod
    def test_dump_XSIAM_1_3_rule(pack):
        modeling_rule = pack.create_modeling_rule(
            yml={
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": "6.10.0",
                "tags": "tag",
                "rules": "",
                "schema": "",
            }
        )
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        created_files = obj.dump(modeling_rule._tmpdir_rule_path)

        assert len(created_files) == 1
        assert created_files[0].name.startswith("external-")


class TestModelingRuleParsing:
    def test_parse_modeling_rule_old_format(self, pack):
        """
        Given:
        - A modeling rule with old format (Prior to unified xql model syntax of XSIAM 1.3)

        When:
        - Parsing the rule

        Then:
        - Ensure the rule is parsed correctly into a ModelingRule object
        - The ModelingRule object's rules attribute should contain 3 SingleModelingRule objects
        """
        modeling_rule = pack.create_modeling_rule(
            yml={
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": "6.8.0",
                "toversion": "6.99.99",
                "tags": "tag",
                "rules": "",
                "schema": "",
            },
            rules=PRE_UNIFIED_MODELING_RULE_XIF_TEXT,
        )
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        assert len(obj.rules) == 3
        assert obj.rules[0].dataset == "fake_fake_raw"
        assert obj.rules[0].datamodel == "Network"
        rule1_fields = {field.casefold() for field in obj.rules[0].fields}
        assert rule1_fields == PRE_UNIFIED_RULE1_FIELDS
        assert obj.rules[1].dataset == "fake_fake_raw"
        assert obj.rules[1].datamodel == "Audit"
        rule2_fields = {field.casefold() for field in obj.rules[1].fields}
        assert rule2_fields == PRE_UNIFIED_RULE2_FIELDS
        assert obj.rules[2].dataset == "fake_fake_raw"
        assert obj.rules[2].datamodel == "Auth"
        rule3_fields = {field.casefold() for field in obj.rules[2].fields}
        assert rule3_fields == PRE_UNIFIED_RULE3_FIELDS

    def test_parse_modeling_rule_new_format(self, pack):
        """
        Given:
        - A modeling rule with new format (Unified xql model syntax of XSIAM 1.3)

        When:
        - Parsing the rule

        Then:
        - Ensure the rule is parsed correctly into a ModelingRule object
        - The ModelingRule object's rules attribute should contain 1 SingleModelingRule object
        """
        modeling_rule = pack.create_modeling_rule(
            yml={
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": "6.10.0",
                "tags": "tag",
                "rules": "",
                "schema": "",
            },
            rules=UNIFIED_RULE_XIF,
        )
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        assert len(obj.rules) == 1
        assert obj.rules[0].dataset == "fake_faker_raw"
        assert obj.rules[0].vendor == "fake"
        assert obj.rules[0].product == "faker"
        rule_fields = {field.casefold() for field in obj.rules[0].fields}
        assert rule_fields == UNIFIED_RULE_FIELDS

    def test_parse_modeling_rule_new_format_with_arbitrary_whitespace(self, pack):
        """
        Given:
        - A modeling rule with new format (Unified xql model syntax of XSIAM 1.3) and arbitrary whitespace

        When:
        - Parsing the rule

        Then:
        - Ensure the rule is parsed correctly into a ModelingRule object
        - The ModelingRule object's rules attribute should contain 1 SingleModelingRule object
        """
        modeling_rule = pack.create_modeling_rule(
            yml={
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": "6.10.0",
                "tags": "tag",
                "rules": "",
                "schema": "",
            },
            rules=UNIFIED_RULE_XIF_WITH_ARBITRARY_WHITESPACE,
        )
        obj = ModelingRule(modeling_rule._tmpdir_rule_path)
        assert len(obj.rules) == 1
        assert obj.rules[0].dataset == "fake_faker_raw"
        assert obj.rules[0].vendor == "fake"
        assert obj.rules[0].product == "faker"
        rule_fields = {field.casefold() for field in obj.rules[0].fields}
        assert rule_fields == UNIFIED_RULE_FIELDS
