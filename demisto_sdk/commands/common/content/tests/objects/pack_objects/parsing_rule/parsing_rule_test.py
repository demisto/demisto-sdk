from demisto_sdk.commands.common.content.objects.pack_objects import ParsingRule
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object


def get_parsing_rule(pack, name):
    return pack.create_parsing_rule(name)


class TestParsingRule:
    def test_objects_factory(self, pack):
        parsing_rule = get_parsing_rule(pack, "parsing_rule_name")
        obj = path_to_pack_object(parsing_rule.yml._tmp_path)
        assert isinstance(obj, ParsingRule)

    def test_prefix(self, pack):
        parsing_rule = get_parsing_rule(pack, "external-parsingrule-parsing_rule_name")
        obj = ParsingRule(parsing_rule._tmpdir_rule_path)
        assert obj.normalize_file_name() == parsing_rule.yml._tmp_path.name

        parsing_rule = get_parsing_rule(pack, "parsing_rule_name")
        obj = ParsingRule(parsing_rule._tmpdir_rule_path)
        assert (
            obj.normalize_file_name()
            == f"external-parsingrule-{parsing_rule.yml._tmp_path.name}"
        )

    def test_files_detection(self, pack):
        parsing_rule = get_parsing_rule(pack, "parsing_rule_name")
        obj = ParsingRule(parsing_rule._tmpdir_rule_path)
        # assert obj.yml._tmp_path == Path(datadir["README.md"])
        assert obj.rules_path == parsing_rule.rules._tmp_path

    def test_is_unify(self, pack):
        parsing_rule = get_parsing_rule(pack, "parsing_rule_name")
        obj = ParsingRule(parsing_rule._tmpdir_rule_path)
        assert not obj.is_unify()


class TestParsingRules_XSIAM_1_3_Migration:
    @staticmethod
    def test_dump_XSIAM_1_2_rule(pack):
        parsing_rule = pack.create_parsing_rule(
            yml={
                "id": "parsing-rule",
                "name": "Parsing Rule",
                "fromversion": "6.8.0",
                "toversion": "6.99.99",
                "tags": "tag",
                "rules": "",
                "schema": "",
            }
        )
        obj = ParsingRule(parsing_rule._tmpdir_rule_path)
        created_files = obj.dump(parsing_rule._tmpdir_rule_path)

        assert len(created_files) == 1
        assert not created_files[0].name.startswith("external-")

    @staticmethod
    def test_dump_XSIAM_1_3_rule(pack):
        parsing_rule = pack.create_parsing_rule(
            yml={
                "id": "modeling-rule",
                "name": "Modeling Rule",
                "fromversion": "6.10.0",
                "tags": "tag",
                "rules": "",
                "schema": "",
            }
        )
        obj = ParsingRule(parsing_rule._tmpdir_rule_path)
        created_files = obj.dump(parsing_rule._tmpdir_rule_path)

        assert len(created_files) == 1
        assert created_files[0].name.startswith("external-")
