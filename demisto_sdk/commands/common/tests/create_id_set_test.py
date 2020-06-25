from demisto_sdk.commands.common.update_id_set import ID_SET_ENTITIES
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions


def test_create_id_set_flow(repo):
    number_of_packs_to_create = 10
    repo.setup_content_repo(number_of_packs_to_create)

    with ChangeCWD(repo.path):
        id_set_creator = IDSetCreator(repo.id_set.path, print_logs=False)
        id_set_creator.create_id_set()

    id_set_content = repo.id_set.read_json_as_dict()
    assert not IsEqualFunctions.is_dicts_equal(id_set_content, {})
    assert IsEqualFunctions.is_lists_equal(list(id_set_content.keys()), ID_SET_ENTITIES)
    for id_set_entity in ID_SET_ENTITIES:
        entity_content_in_id_set = id_set_content.get(id_set_entity)
        assert entity_content_in_id_set
        assert len(entity_content_in_id_set) == number_of_packs_to_create
