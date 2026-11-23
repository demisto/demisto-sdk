from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import (
    CI_INJECTED_KEYS,
    IS_CONTENT_PRIVATE_KEY,
    IS_CONTENT_PRIVATE_ONLY_KEY,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.objects import base_content
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.pack import Pack as PackModel
from demisto_sdk.commands.content_graph.parsers.classifier import ClassifierParser
from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser
from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_json, load_yaml
from TestSuite.pack import Pack
from TestSuite.repo import Repo

INJECTED = {key: True for key in CI_INJECTED_KEYS}
UNRELATED_KEY_ERRORS = [(("unrelated",), "value_error.extra")]


def _errors(parser):
    return [(e.field_name, e.error_type) for e in parser.structure_errors]


def _parser(parser_cls, path):
    return parser_cls(Path(path), list(MarketplaceVersions), pack_supported_modules=[])


@pytest.mark.parametrize(
    "value, expected", [(True, True), ("true", False), (None, False)]
)
def test_item_flag_is_parsed(mocker, pack: Pack, value, expected: bool):
    mocker.patch.object(base_content, "CONTENT_PATH", Path(pack.repo_path))
    content = {**load_json("classifier.json"), IS_CONTENT_PRIVATE_KEY: value}
    parser = _parser(ClassifierParser, pack.create_classifier("Test", content).path)

    assert parser.is_content_private is expected
    model = Classifier.from_orm(parser)
    assert model.is_content_private is expected
    assert model.to_dict()[IS_CONTENT_PRIVATE_KEY] is expected


@pytest.mark.parametrize(
    "value, expected", [(True, True), ("true", False), (None, False)]
)
def test_pack_flag_is_parsed(mocker, repo: Repo, value, expected: bool):
    mocker.patch.object(base_content, "CONTENT_PATH", Path(repo.path))
    pack = repo.create_pack("HelloWorld")
    pack.pack_metadata.write_json(
        {**load_json("pack_metadata.json"), IS_CONTENT_PRIVATE_ONLY_KEY: value}
    )
    parser = PackParser(Path(pack.path))

    assert parser.is_content_private_only is expected
    model = PackModel.from_orm(parser)
    assert model.is_content_private_only is expected
    assert model.to_dict()[IS_CONTENT_PRIVATE_ONLY_KEY] is expected


@pytest.mark.parametrize("item_type", ["integration", "classifier"])
def test_strict_validation_accepts_item_flag_but_not_other_keys(
    pack: Pack, item_type: str
):
    def parse(name: str, extra: dict):
        if item_type == "integration":
            item = pack.create_integration(
                name, yml={**load_yaml("integration.yml"), **extra}
            )
            return _parser(IntegrationParser, item.yml.path)
        content = {**load_json("classifier.json"), **extra}
        return _parser(ClassifierParser, pack.create_classifier(name, content).path)

    assert _errors(parse("WithFlag", {IS_CONTENT_PRIVATE_KEY: True})) == []
    assert _errors(parse("WithUnrelated", {"unrelated": 1})) == UNRELATED_KEY_ERRORS


def test_strict_validation_accepts_pack_flags_but_not_other_keys(mocker, repo: Repo):
    mocker.patch.object(base_content, "CONTENT_PATH", Path(repo.path))

    def parse(name: str, extra: dict):
        pack = repo.create_pack(name)
        pack.pack_metadata.write_json({**load_json("pack_metadata.json"), **extra})
        return PackParser(Path(pack.path))

    assert _errors(parse("WithFlags", INJECTED)) == []
    assert (
        _errors(parse("WithUnrelated", {**INJECTED, "unrelated": 1}))
        == UNRELATED_KEY_ERRORS
    )


def test_strict_validation_accepts_modeling_rule_flag_but_not_other_keys(pack: Pack):
    def parse(name: str, extra: dict):
        rule = pack.create_modeling_rule(name, load_yaml("modeling_rule.yml"))
        rule.yml.update(extra)
        return _parser(ModelingRuleParser, rule.path)

    assert _errors(parse("WithFlag", INJECTED)) == []
    assert (
        _errors(parse("WithUnrelated", {**INJECTED, "unrelated": 1}))
        == UNRELATED_KEY_ERRORS
    )
