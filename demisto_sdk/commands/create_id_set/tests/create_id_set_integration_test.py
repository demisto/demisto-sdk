from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from TestSuite.test_tools import ChangeCWD


def test_create_id_set_flow(repo):
    repo.setup_content_repo(10)

    with ChangeCWD(repo.path):
        id_set_creator = IDSetCreator(repo.id_set.path)
        id_set_creator.create_id_set()

    assert repo.id_set.read_json_as_text() != '{}'
