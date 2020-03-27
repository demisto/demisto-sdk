import pytest
import json
import os
# import networkx
# from demisto_sdk.commands.find_dependencies.find_dependencies import PackDependencies


@pytest.fixture(scope="module")
def id_set():
    id_set_path = os.path.join('test_data', 'id_set.json')

    with open(id_set_path, 'r') as id_set_file:
        id_set = json.load(id_set_file)
        yield id_set


class TestIdSetFilters:
    pass
