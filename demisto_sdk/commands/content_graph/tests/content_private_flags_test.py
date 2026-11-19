"""Tests for the CI injected content-private flags: `is_content_private` (items) and `is_content_private_only` (pack).

The flags are written to the files on disk by the CI. The SDK has to parse them (parsers and graph models) and
accept them in the strict (pydantic) structure validation, while still rejecting any other unknown key.
"""

from pathlib import Path
from typing import Dict, List

import pytest

from demisto_sdk.commands.common.constants import (
    CI_INJECTED_KEYS,
    IS_CONTENT_PRIVATE_KEY,
    IS_CONTENT_PRIVATE_ONLY_KEY,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.docker_helper import get_python_version
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import base_content
from demisto_sdk.commands.content_graph.objects.base_content import (
    CONTENT_TYPE_TO_MODEL,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack as PackModel
from demisto_sdk.commands.content_graph.parsers.agentix_action import (
    AgentixActionParser,
)
from demisto_sdk.commands.content_graph.parsers.assets_modeling_rule import (
    AssetsModelingRuleParser,
)
from demisto_sdk.commands.content_graph.parsers.base_content import validate_structure
from demisto_sdk.commands.content_graph.parsers.classifier import ClassifierParser
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser
from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser
from demisto_sdk.commands.content_graph.parsers.layout import LayoutParser
from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.parsers.parsing_rule import ParsingRuleParser
from demisto_sdk.commands.content_graph.parsers.playbook import PlaybookParser
from demisto_sdk.commands.content_graph.parsers.script import ScriptParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_json, load_yaml
from TestSuite.pack import Pack
from TestSuite.repo import Repo


@pytest.fixture(autouse=True)
def clear_python_version_cache():
    """Building an Integration model fills the lru_cached ``get_python_version``; do not leak it to other test modules."""
    get_python_version.cache_clear()
    yield
    get_python_version.cache_clear()


EXTRA_FIELD_ERROR = "value_error.extra"
# Strict models that deliberately ignore unknown keys, so the negative control does not apply to them.
TYPES_IGNORING_EXTRA_FIELDS = {
    ContentType.AGENTIX_ACTION,
    ContentType.AGENTIX_AGENT,
    ContentType.AGENTIX_SKILL,
    ContentType.KNOWLEDGE,
}


def _error_fields(errors) -> List[str]:
    return [str(error.field_name[0]) for error in errors]


def _create_integration(pack: Pack):
    return pack.create_integration(yml=load_yaml("integration.yml"))


def _create_script(pack: Pack):
    script = pack.create_script()
    script.create_default_script()
    return script


def _create_playbook(pack: Pack):
    playbook = pack.create_playbook()
    playbook.create_default_playbook(name="sample")
    return playbook


def _create_classifier(pack: Pack):
    return pack.create_classifier("TestClassifier", load_json("classifier.json"))


def _create_layout(pack: Pack):
    return pack.create_layout("TestLayout")


# (item creator, parser class, whether the item is a json or a yml file)
ITEM_CASES: Dict[str, tuple] = {
    "integration": (_create_integration, IntegrationParser, "yml"),
    "script": (_create_script, ScriptParser, "yml"),
    "playbook": (_create_playbook, PlaybookParser, "yml"),
    "classifier": (_create_classifier, ClassifierParser, "json"),
    "layout": (_create_layout, LayoutParser, "json"),
}


def _parse_item(item_name: str, pack: Pack, with_flag: bool):
    create_item, parser_cls, _ = ITEM_CASES[item_name]
    item = create_item(pack)
    if with_flag:
        file = item.yml if ITEM_CASES[item_name][2] == "yml" else item
        file.update({IS_CONTENT_PRIVATE_KEY: True})
    return parser_cls(
        Path(item.path), list(MarketplaceVersions), pack_supported_modules=[]
    )


class TestItemParsing:
    @pytest.mark.parametrize("item_name", ITEM_CASES)
    def test_flag_present(self, pack: Pack, item_name: str):
        """
        Given:
            - An item file that contains `is_content_private: true`.
        When:
            - Creating the content item's parser.
        Then:
            - The parser exposes is_content_private as True and the strict validation raises no error.
        """
        parser = _parse_item(item_name, pack, with_flag=True)
        assert parser.is_content_private is True
        assert IS_CONTENT_PRIVATE_KEY not in _error_fields(parser.structure_errors)

    @pytest.mark.parametrize("value", ["true", "false", "yes", 1, None])
    @pytest.mark.parametrize("item_name", ["integration", "classifier"])
    def test_non_bool_value_is_false(self, pack: Pack, item_name: str, value):
        """
        Given:
            - An item file whose `is_content_private` is not a real boolean (string, int, null).
        When:
            - Creating the content item's parser.
        Then:
            - The parser exposes is_content_private as False (strict parsing, no bool coercion).
        """
        create_item, parser_cls, file_type = ITEM_CASES[item_name]
        item = create_item(pack)
        file = item.yml if file_type == "yml" else item
        file.update({IS_CONTENT_PRIVATE_KEY: value})
        parser = parser_cls(
            Path(item.path), list(MarketplaceVersions), pack_supported_modules=[]
        )
        assert parser.is_content_private is False

    @pytest.mark.parametrize("item_name", ITEM_CASES)
    @pytest.mark.parametrize("with_flag", [True, False])
    def test_model_is_populated_from_parser(
        self, mocker, pack: Pack, item_name: str, with_flag: bool
    ):
        """
        Given:
            - An item file with or without the `is_content_private` key.
        When:
            - Creating the content item model from the parser.
        Then:
            - The model's is_content_private matches the file.
            - The graph node (to_dict) exposes the flag under the same name (A5, no neo4j needed).
        """
        mocker.patch.object(base_content, "CONTENT_PATH", Path(pack.repo_path))
        parser = _parse_item(item_name, pack, with_flag=with_flag)
        model = CONTENT_TYPE_TO_MODEL[parser.content_type].from_orm(parser)
        assert model.is_content_private is with_flag  # type: ignore[attr-defined]
        assert model.to_dict()[IS_CONTENT_PRIVATE_KEY] is with_flag


def _create_agentix_action(pack: Pack):
    item = pack.create_agentix_action(
        "TestAgentixAction", load_yaml("agentix_action.yml")
    )
    item.yml.update({IS_CONTENT_PRIVATE_KEY: True})
    return AgentixActionParser, Path(item.path)


def _create_parsing_rule(pack: Pack):
    item = pack.create_parsing_rule("TestParsingRule", load_yaml("parsing_rule.yml"))
    item.yml.update({IS_CONTENT_PRIVATE_KEY: True})
    return ParsingRuleParser, Path(item.path)


def _create_modeling_rule(pack: Pack):
    item = pack.create_modeling_rule("TestModelingRule", load_yaml("modeling_rule.yml"))
    item.yml.update({IS_CONTENT_PRIVATE_KEY: True})
    return ModelingRuleParser, Path(item.path)


# Item types that are built differently from ITEM_CASES: (builder returning the parser class and the item path)
OTHER_ITEM_CASES = {
    "agentix_action": _create_agentix_action,
    "parsing_rule": _create_parsing_rule,
    "modeling_rule": _create_modeling_rule,
}


class TestOtherItemTypesParsing:
    @pytest.mark.parametrize("item_name", OTHER_ITEM_CASES)
    def test_model_is_populated_from_parser(self, mocker, pack: Pack, item_name: str):
        """
        Given:
            - An agentix action, parsing rule or modeling rule with `is_content_private: true`.
        When:
            - Creating the parser and the model.
        Then:
            - The parser and the model expose the flag, and the strict validation raises no error for the key.
        """
        mocker.patch.object(base_content, "CONTENT_PATH", Path(pack.repo_path))
        parser_cls, path = OTHER_ITEM_CASES[item_name](pack)
        parser = parser_cls(path, list(MarketplaceVersions), pack_supported_modules=[])
        assert parser.is_content_private is True
        assert IS_CONTENT_PRIVATE_KEY not in _error_fields(parser.structure_errors)
        model = CONTENT_TYPE_TO_MODEL[parser.content_type].from_orm(parser)
        assert model.is_content_private is True  # type: ignore[attr-defined]


class TestPackParsing:
    @staticmethod
    def _create_pack_with_metadata(repo: Repo, **extra_metadata) -> Path:
        pack = repo.create_pack("HelloWorld")
        pack.pack_metadata.write_json(
            {**load_json("pack_metadata.json"), **extra_metadata}
        )
        return Path(pack.path)

    @pytest.mark.parametrize("value", [True, False])
    def test_flag_present(self, mocker, repo: Repo, value: bool):
        """
        Given:
            - A pack_metadata.json with `is_content_private_only` set to true / false.
        When:
            - Creating the pack parser and model.
        Then:
            - The parser and the model have the matching value.
            - The graph node (to_dict) exposes the flag under the same name (A5, no neo4j needed).
            - The strict validation raises no error for the key.
        """
        mocker.patch.object(base_content, "CONTENT_PATH", Path(repo.path))
        pack_path = self._create_pack_with_metadata(
            repo, **{IS_CONTENT_PRIVATE_ONLY_KEY: value}
        )
        parser = PackParser(pack_path)
        assert parser.is_content_private_only is value
        assert IS_CONTENT_PRIVATE_ONLY_KEY not in _error_fields(parser.structure_errors)

        model = PackModel.from_orm(parser)
        assert model.is_content_private_only is value
        assert model.to_dict()[IS_CONTENT_PRIVATE_ONLY_KEY] is value

    @pytest.mark.parametrize("value", ["true", "false", "yes", 1, None])
    def test_non_bool_value_is_false(self, mocker, repo: Repo, value):
        """
        Given:
            - A pack_metadata.json whose `is_content_private_only` is not a real boolean (string, int, null).
        When:
            - Creating the pack parser.
        Then:
            - The flag is False (strict parsing, no bool coercion).
        """
        mocker.patch.object(base_content, "CONTENT_PATH", Path(repo.path))
        pack_path = self._create_pack_with_metadata(
            repo, **{IS_CONTENT_PRIVATE_ONLY_KEY: value}
        )
        assert PackParser(pack_path).is_content_private_only is False

    def test_flag_absent(self, mocker, repo: Repo):
        """
        Given:
            - A pack_metadata.json without the `is_content_private_only` key.
        When:
            - Creating the pack parser and model.
        Then:
            - The flag defaults to False, and the key is still exposed by to_dict.
        """
        mocker.patch.object(base_content, "CONTENT_PATH", Path(repo.path))
        parser = PackParser(self._create_pack_with_metadata(repo))
        assert parser.is_content_private_only is False
        model = PackModel.from_orm(parser)
        assert model.is_content_private_only is False
        assert model.to_dict()[IS_CONTENT_PRIVATE_ONLY_KEY] is False


def _strict_object_of(content_type: ContentType):
    """The strict model of the parser (None when the parser validates differently, e.g. modeling rules)."""
    parser_cls = ContentItemParser.content_type_to_parser[content_type]
    try:
        return parser_cls.strict_object.fget(None)  # type: ignore[attr-defined]
    except NotImplementedError:
        return None


STRICT_OBJECT_BY_TYPE = {
    content_type: strict_object
    for content_type in ContentItemParser.content_type_to_parser
    if (strict_object := _strict_object_of(content_type)) is not None
}


class TestStrictValidation:
    @pytest.mark.parametrize("content_type", STRICT_OBJECT_BY_TYPE)
    def test_ci_injected_keys_are_accepted(self, content_type: ContentType):
        """
        Given:
            - The strict model of each content type, and raw data holding both CI injected keys.
        When:
            - Running validate_structure.
        Then:
            - No structure error is reported for the CI injected keys, and the result is identical to
              the result without them (an empty dict reports only the missing mandatory fields).
        """
        strict_object = STRICT_OBJECT_BY_TYPE[content_type]
        injected = {key: True for key in CI_INJECTED_KEYS}

        errors = validate_structure(strict_object, injected, Path("item.yml"))
        errors_without_keys = validate_structure(strict_object, {}, Path("item.yml"))

        assert not set(_error_fields(errors)) & CI_INJECTED_KEYS
        assert [str(e) for e in errors] == [str(e) for e in errors_without_keys]

    @pytest.mark.parametrize(
        "content_type",
        [c for c in STRICT_OBJECT_BY_TYPE if c not in TYPES_IGNORING_EXTRA_FIELDS],
    )
    def test_unrelated_extra_key_is_still_rejected(self, content_type: ContentType):
        """
        Given:
            - The strict model of each content type, and raw data holding an unrelated extra key.
        When:
            - Running validate_structure.
        Then:
            - A value_error.extra is reported for that key (negative control for the CI keys filter).
        """
        errors = validate_structure(
            STRICT_OBJECT_BY_TYPE[content_type], {"unrelated": 1}, Path("item.yml")
        )
        assert [
            e
            for e in errors
            if e.field_name == ("unrelated",) and e.error_type == EXTRA_FIELD_ERROR
        ]

    def test_nested_key_is_not_filtered(self, pack: Pack):
        """
        Given:
            - An integration where the CI key is nested inside a sub model (not at the root).
        When:
            - Creating the parser.
        Then:
            - The key is still rejected, the filter applies to the root level only.
        """
        integration = _create_integration(pack)
        integration.yml.update({IS_CONTENT_PRIVATE_KEY: True}, "script")
        parser = IntegrationParser(
            Path(integration.path), list(MarketplaceVersions), pack_supported_modules=[]
        )
        assert any(
            e.error_type == EXTRA_FIELD_ERROR
            and e.field_name[-1] == IS_CONTENT_PRIVATE_KEY
            for e in parser.structure_errors
        )

    def test_pack_metadata(self, mocker, repo: Repo):
        """
        Given:
            - A pack whose pack_metadata.json holds the CI keys.
        When:
            - Creating the pack parser (the pack overrides validate_structure).
        Then:
            - No structure error is reported.
            - An unrelated key in pack_metadata.json (of another pack) is still rejected.
        """
        mocker.patch.object(base_content, "CONTENT_PATH", Path(repo.path))
        injected = {key: True for key in CI_INJECTED_KEYS}
        pack = repo.create_pack("HelloWorld")
        pack.pack_metadata.write_json({**load_json("pack_metadata.json"), **injected})
        assert PackParser(Path(pack.path)).structure_errors == []

        # a second pack: the files are cached by path
        other_pack = repo.create_pack("OtherPack")
        other_pack.pack_metadata.write_json(
            {**load_json("pack_metadata.json"), **injected, "unrelated": 1}
        )
        errors = PackParser(Path(other_pack.path)).structure_errors
        assert [(e.field_name, e.error_type) for e in errors] == [
            (("unrelated",), EXTRA_FIELD_ERROR)
        ]

    @pytest.mark.parametrize(
        "create_rule, parser_cls, yml_file_name",
        [
            ("create_modeling_rule", ModelingRuleParser, "modeling_rule.yml"),
            (
                "create_assets_modeling_rule",
                AssetsModelingRuleParser,
                "assets_modeling_rule.yml",
            ),
        ],
    )
    def test_modeling_rules(
        self, pack: Pack, create_rule: str, parser_cls, yml_file_name: str
    ):
        """
        Given:
            - A (assets) modeling rule whose yml holds the CI keys.
        When:
            - Creating the parser (the (assets) modeling rule parsers override validate_structure).
        Then:
            - No structure error is reported, and an unrelated key in the yml is still rejected.
        """
        injected = {key: True for key in CI_INJECTED_KEYS}

        def parse(rule_name: str, extra: dict) -> ModelingRuleParser:
            # a new rule per call: the files are cached by path
            rule = getattr(pack, create_rule)(rule_name, load_yaml(yml_file_name))
            rule.yml.update({**injected, **extra})
            return parser_cls(
                Path(rule.path), list(MarketplaceVersions), pack_supported_modules=[]
            )

        assert parse("RuleWithCIKeys", {}).structure_errors == []

        errors = parse("RuleWithExtraKey", {"unrelated": 1}).structure_errors
        assert [(e.field_name, e.error_type) for e in errors] == [
            (("unrelated",), EXTRA_FIELD_ERROR)
        ]
