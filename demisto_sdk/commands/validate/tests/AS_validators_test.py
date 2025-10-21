import pytest
from demisto_sdk.commands.validate.tests.test_tools import create_script_object, create_test_playbook_object
from demisto_sdk.commands.validate.validators.AS_validators.AS_100_aggregated_script_has_tpb import \
    AggregatedScriptHasTPBValidator


def test_sanity_AggregatedScriptHasTPBValidator():
    content_items = [create_script_object()] # example script has a testing tpb

    res = AggregatedScriptHasTPBValidator().obtain_invalid_content_items(content_items)
    assert len(res) == 0

def test_failure_sanity_AggregatedScriptHasTPBValidator():
    content_items = [create_script_object(paths=["tests"], values=[[]])]

    res = AggregatedScriptHasTPBValidator().obtain_invalid_content_items(content_items)
    assert len(res) == 1
    assert res[0].message == "Script script_name is missing a TPB"
