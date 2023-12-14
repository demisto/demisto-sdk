from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.validators.tools import collect_all_inputs_in_use


playbook = create_playbook_object(paths = ["inputs"],values=[{"name": "input1", "description": "input1 description"}])
def test_collect_all_inputs_in_use_empty(mocker):
    """
    Given:
        - A playbook with no input usages
    When:
        - Running collect_all_inputs_in_use
    Then:
        - An empty set should be returned
    """
    # pack1 = mock_pack("TestPack")
    # pack1.content_items.playbook.append(
    #     mock_playbook(
    #         name="playbook_1",
    #     )
    # )
    # repository.packs.extend([pack1])
    # with ContentGraphInterface() as interface:
    #     create_content_graph(interface)
    #     playbooks = interface.search(content_type=ContentType.PLAYBOOK)
    # #mocker.patch.object(Playbook, 'content_item_as_text', return_value='')
    assert collect_all_inputs_in_use(playbook) == set()
    
def test_collect_all_inputs_in_use_with_usage(mocker, playbook):
    """
    Given:
        - A playbook using input1 and input2
    When:
        - Running collect_all_inputs_in_use
    Then:
        - A set with input1 and input2 should be returned
    """
    mocker.patch.object('demisto_sdk.commands.common.tools.content_item_as_text', return_value={'input1'})
    playbook.data={'inputs':[{'key': 'Domain2', 'value': {'abc': 'def'}, 'required': False, 'description': None, 'playbookInputQuery': None},
                             {'key': 'Domain3', 'value': {'abc': 'def'}, 'required': False, 'description': None, 'playbookInputQuery': None}]}
    playbook.content_item_as_text ="abc"
    assert collect_all_inputs_in_use(playbook) == {'input1', 'input2'}


def test_collect_all_inputs_from_inputs_section(playbook):
    """
    Given:
        - A playbook with input1 and input2 defined
    When:
        - Running collect_all_inputs_from_inputs_section
    Then:
        - A set with input1 and input2 should be returned
    """
    playbook.data={'inputs':[{'key': 'Domain2', 'value': {'abc': 'def'}, 'required': False, 'description': None, 'playbookInputQuery': None},
                             {'key': 'Domain3', 'value': {'abc': 'def'}, 'required': False, 'description': None, 'playbookInputQuery': None}]}
    assert collect_all_inputs_from_inputs_section(playbook) == {'Domain2', 'Domain3'}