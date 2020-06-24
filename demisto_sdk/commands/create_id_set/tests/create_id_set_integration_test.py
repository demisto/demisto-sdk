from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from TestSuite.test_tools import ChangeCWD


def setup_one_pack(repo, name):
    pack = repo.create_pack(name)

    script = pack.create_script(f'{name}_script')
    script.create_default_script()

    integration = pack.create_integration(f'{name}_integration')
    integration.create_default_integration()

    pack.create_layout(f'{name}_layout')
    pack.create_mapper(f'{name}_mapper')
    pack.create_classifier(f'{name}_classifier')
    pack.create_incident_type(f'{name}_incident-type')
    pack.create_incident_field(f'{name}_incident-field')
    pack.create_indicator_type(f'{name}_indicator-type')
    pack.create_indicator_field(f'{name}_indicator-field')


def setup_whole_repo(repo, number_of_packs):
    for i in range(number_of_packs):
        setup_one_pack(repo, f'pack_{i}')


def test_create_id_set_flow(mocker, repo):
    setup_whole_repo(repo, 10)

    with ChangeCWD(repo.path):
        id_set_creator = IDSetCreator(repo.id_set.path)
        id_set_creator.create_id_set()

    print(repo.id_set.read_json())
