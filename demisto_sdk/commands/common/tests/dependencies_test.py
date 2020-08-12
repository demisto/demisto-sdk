import inspect
import random
from typing import List

import pytest
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from TestSuite.integration import Integration
from TestSuite.json_based import JSONBased
from TestSuite.playbook import Playbook
from TestSuite.script import Script
from TestSuite.test_tools import ChangeCWD
from TestSuite.utils import IsEqualFunctions


def update_id_set(repo):
    with ChangeCWD(repo.path):
        id_set_creator = IDSetCreator(repo.id_set.path, print_logs=False)
        id_set_creator.create_id_set()


class IntegrationDependencies:
    @staticmethod
    def make_integration_depend_on_classifier(integration: Integration, classifier: JSONBased):
        classifier_id = classifier.read_json_as_dict().get('id')
        integration.yml.update({'defaultclassifier': classifier_id})

    @staticmethod
    def make_integration_depend_on_mapper_in(integration: Integration, mapper: JSONBased):
        mapper_id = mapper.read_json_as_dict().get('id')
        integration.yml.update({'defaultmapperin': mapper_id})

    @staticmethod
    def make_integration_depend_on_mapper_out(integration: Integration, mapper: JSONBased):
        mapper_id = mapper.read_json_as_dict().get('id')
        integration.yml.update({'defaultmapperout': mapper_id})

    @staticmethod
    def make_integration_depend_on_incident_type(integration: Integration, incident_type: JSONBased):
        incident_type_id = incident_type.read_json_as_dict().get('id')
        integration.yml.update({'defaultIncidentType': incident_type_id})

    @staticmethod
    def make_integration_feed(integration: Integration):
        integration.yml.update({'feed': True})


class ClassifierDependencies:
    @staticmethod
    def make_classifier_depend_on_incident_type_default(classifier: JSONBased, incident_type: JSONBased):
        incident_type_id = incident_type.read_json_as_dict().get('id')
        classifier.update({'defaultIncidentType': incident_type_id})

    @staticmethod
    def make_classifier_depend_on_incident_type_key_type_map(classifier: JSONBased, incident_type: JSONBased):
        incident_type_id = incident_type.read_json_as_dict().get('id')
        key_type_map = classifier.read_json_as_dict().get('keyTypeMap', {})
        key_type_map.update({'key': incident_type_id})
        classifier.update({'keyTypeMap': key_type_map})


class MapperDependencies:
    @staticmethod
    def make_mapper_depend_on_incident_type_default(mapper: JSONBased, incident_type: JSONBased):
        incident_type_id = incident_type.read_json_as_dict().get('id')
        mapper.update({'defaultIncidentType': incident_type_id})

    @staticmethod
    def make_classifier_depend_on_incident_type_and_fields(mapper: JSONBased, incident_type: JSONBased,
                                                           incidents_fields: List[JSONBased]):
        incident_type_id = incident_type.read_json_as_dict().get('id')
        incidents_fields_ids = [incident_field.read_json_as_dict().get('id') for incident_field in incidents_fields]
        mapping = mapper.read_json_as_dict().get('mapping', {})

        updates_to_map = {
            incident_type_id: {
                'internalMapping':
                    {
                        incident_field_id: {
                            "simple": "simple"
                        } for incident_field_id in incidents_fields_ids
                    }
            }
        }

        mapping.update(updates_to_map)
        mapper.update({'mapping': mapping})


class IncidentTypeDependencies:
    @staticmethod
    def make_incident_type_depend_on_playbook(incident_type: JSONBased, playbook: Playbook):
        playbook_id = playbook.yml.read_dict().get('id')
        incident_type.update({'playbookId': playbook_id})

    @staticmethod
    def make_incident_type_depend_on_script_pre_processing(incident_type: JSONBased, script: Script):
        script_id = script.yml.read_dict().get('commonfields').get('id')
        incident_type.update({'preProcessingScript': script_id})


class IndicatorTypeDependencies:
    @staticmethod
    def make_indicator_type_depend_on_script_reputation(indicator_type: JSONBased, script: Script):
        script_id = script.yml.read_dict().get('commonfields').get('id')
        indicator_type.update({'reputationScriptName': script_id})

    @staticmethod
    def make_indicator_type_depend_on_script_enhancement(indicator_type: JSONBased, script: Script):
        script_id = script.yml.read_dict().get('commonfields').get('id')
        indicator_type.update({'enhancementScriptNames': [script_id]})

    # Optional dependency
    @staticmethod
    def make_indicator_type_depend_on_integration(indicator_type: JSONBased, integration: Integration):
        indicator_type.update({'reputationCommand': 'ip'})
        integration.yml.update(
            {
                'script': {
                    'commands': [{
                        'name': 'ip'
                    }]
                }
            }
        )


class LayoutDependencies:
    @staticmethod
    def make_layout_depend_on_incident_indicator_type(layout: JSONBased, incident_type: JSONBased):
        incident_type_id = incident_type.read_json_as_dict().get('id')
        layout.update({'TypeName': incident_type_id})

    @staticmethod
    def make_layout_depend_on_incident_indicator_field(layout: JSONBased, indicators_fields: List[JSONBased],
                                                       incidents_fields: List[JSONBased]):
        indicators_fields_ids = [indicator_field.read_json_as_dict().get('id') for indicator_field in indicators_fields]
        incidents_fields_ids = [incident_field.read_json_as_dict().get('id') for incident_field in incidents_fields]

        layout_data = layout.read_json_as_dict().get('layout', {})
        updates_to_layout = {
            'tabs': {
                'sections': [
                    {
                        'displayType': 'ROW',
                        'h': 2,
                        'i': 'uuid',
                        'isVisible': True,
                        'items': [
                            {
                                'endCol': 2,
                                'fieldId': indicator_field_id,
                                'height': 24,
                                'id': 'id',
                                'index': 0,
                                'startCol': 0
                            } for indicator_field_id in indicators_fields_ids
                        ]
                    },
                    {
                        'displayType': 'ROW',
                        'h': 2,
                        'i': 'uuid',
                        'isVisible': True,
                        'items': [
                            {
                                'endCol': 2,
                                'fieldId': incident_field_id,
                                'height': 24,
                                'id': 'id',
                                'index': 0,
                                'startCol': 0
                            } for incident_field_id in incidents_fields_ids
                        ]
                    }
                ]
            }
        }

        layout_data.update(updates_to_layout)
        layout.update({'layout': layout_data})


class IncidentFieldDependencies:
    # Ignored by yaakovi
    # @staticmethod
    # def make_incident_field_depend_on_incident_type_associated(incident_field: JSONBased, incident_type: JSONBased):
    #     incident_type_id = incident_type.read_json_as_dict().get('id')
    #     incident_field.update({'associatedTypes': [incident_type_id]})
    #
    # @staticmethod
    # def make_incident_field_depend_on_incident_type_system_associated(incident_field: JSONBased,
    #                                                                   incident_type: JSONBased):
    #     incident_type_id = incident_type.read_json_as_dict().get('id')
    #     incident_field.update({'systemAssociatedTypes': [incident_type_id]})

    @staticmethod
    def make_incident_field_depend_on_script(incident_field: JSONBased, script: Script):
        script_id = script.yml.read_dict().get('commonfields').get('id')
        incident_field.update({'script': script_id})

    @staticmethod
    def make_incident_field_depend_on_script_field_calc(incident_field: JSONBased, script: Script):
        script_id = script.yml.read_dict().get('commonfields').get('id')
        incident_field.update({'fieldCalcScript': script_id})


CLASSES = [IntegrationDependencies, ClassifierDependencies, MapperDependencies, IncidentTypeDependencies,
           IndicatorTypeDependencies, LayoutDependencies, IncidentFieldDependencies]
METHODS_POOL: list = \
    [(method_name, entity_class) for entity_class in CLASSES for method_name in list(entity_class.__dict__.keys())
     if '_' != method_name[0]]


def get_entity_by_pack_number_and_entity_type(repo, pack_number, entity_type):
    if entity_type == 'integration':
        return repo.packs[pack_number].integrations[0]

    if entity_type == 'script':
        return repo.packs[pack_number].scripts[0]

    if entity_type == 'playbook':
        return repo.packs[pack_number].playbooks[0]

    if entity_type == 'classifier':
        return repo.packs[pack_number].classifiers[0]

    if entity_type == 'mapper':
        return repo.packs[pack_number].mappers[0]

    if entity_type == 'layout':
        return repo.packs[pack_number].layouts[0]

    if entity_type == 'incident_type':
        return repo.packs[pack_number].incident_types[0]

    if entity_type == 'incident_field':
        return repo.packs[pack_number].incident_fields[0]

    if entity_type == 'indicator_type':
        return repo.packs[pack_number].indicator_types[0]

    if entity_type == 'indicator_field':
        return repo.packs[pack_number].indicator_fields[0]


LIST_ARGUMENTS_TO_METHODS = {
    'indicators_fields': 'indicator_field',
    'incidents_fields': 'incident_field'
}


def create_inputs_for_method(repo, current_pack, inputs_arguments):
    """Creates an `argument: object` dict of inputs for a method according to inputs_arguments.

    Args:
        repo (Repo): Content repo object.
        current_pack (int): ID of the pack that its objects will depend on other packs.
        inputs_arguments (list): List of entity types that  are needed as arguments to the method.

    Returns:
        Tuple(Dict, set):
            inputs_values (Dict): An `argument: object` dict of inputs for a method.
            dependencies (Set): All the packs' names that `current_pack` should depend on.
    """
    dependencies = set()

    inputs_values = {inputs_arguments[0]:
                     get_entity_by_pack_number_and_entity_type(repo, current_pack, inputs_arguments[0])}

    inputs_arguments = inputs_arguments[1:]
    # Ignores the `CommonTypes` pack in the flow, so only numeric packs will be chosen
    number_of_packs = len(repo.packs) - 1

    for arg in inputs_arguments:
        if arg in LIST_ARGUMENTS_TO_METHODS.keys():
            number_of_items_in_list = random.randint(1, 5)

            input_argument = []
            for i in range(number_of_items_in_list):
                pack_to_take_entity_from = random.choice(range(1, number_of_packs))
                input_argument.append(get_entity_by_pack_number_and_entity_type(repo, pack_to_take_entity_from,
                                                                                LIST_ARGUMENTS_TO_METHODS[arg]))
                dependencies.add(f'pack_{pack_to_take_entity_from}')

        else:
            pack_to_take_entity_from = random.choice(range(1, number_of_packs))
            input_argument = get_entity_by_pack_number_and_entity_type(repo, pack_to_take_entity_from, arg)
            dependencies.add(f'pack_{pack_to_take_entity_from}')

        inputs_values[arg] = input_argument

    return inputs_values, dependencies


def run_random_methods(repo, current_pack, current_methods_pool, number_of_methods_to_choose):
    """ Runs random set of methods with size number_of_methods_to_choose
        out of the current_methods_pool.

    Args:
        repo (Repo): Content repo object.
        current_pack (int): ID of the pack that its objects will depend on other packs.
        current_methods_pool (list): The pool of methods to choose from.
        number_of_methods_to_choose (int): Amount of methods to choose.

    Returns:
        Set. All the packs' names that `current_pack` should depend on.
    """
    all_dependencies = set()

    for i in range(number_of_methods_to_choose):
        chosen_method = random.choice(current_methods_pool)
        current_methods_pool.remove(chosen_method)

        method = getattr(chosen_method[1], chosen_method[0])
        inputs_arguments = inspect.getfullargspec(method)[0]

        args, dependencies = create_inputs_for_method(repo, current_pack, inputs_arguments)

        if chosen_method[0] == 'make_integration_feed':
            all_dependencies.add('CommonTypes')

        all_dependencies = all_dependencies.union(dependencies)
        method(**args)

    return all_dependencies


@pytest.mark.parametrize('test_number', range(10))
def test_dependencies(mocker, repo, test_number):
    """ This test will run 10 times, when each time it will randomly generate dependencies in the repo and verify that
        the expected dependencies has been updated in the pack metadata correctly.

        Given
        - Content repository
        When
        - Running find_dependencies
        Then
        - Update packs dependencies in pack metadata
    """
    number_of_packs = 10
    repo.setup_content_repo(number_of_packs)
    repo.setup_one_pack('CommonTypes')

    pack_to_verify = random.choice(range(number_of_packs))

    number_of_methods_to_choose = random.choice(range(1, len(METHODS_POOL)))
    dependencies = run_random_methods(repo, pack_to_verify, METHODS_POOL.copy(), number_of_methods_to_choose)

    with ChangeCWD(repo.path):
        # Circle froze on 3.7 dut to high usage of processing power.
        # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
        # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
        # and not the maximum amount.
        import demisto_sdk.commands.common.update_id_set as uis
        mocker.patch.object(uis, 'cpu_count', return_value=1)
        PackDependencies.find_dependencies(f'pack_{pack_to_verify}', silent_mode=True)

    dependencies_from_pack_metadata = repo.packs[pack_to_verify].pack_metadata.read_json_as_dict().get(
        'dependencies').keys()

    if f'pack_{pack_to_verify}' in dependencies:
        dependencies.remove(f'pack_{pack_to_verify}')

    assert IsEqualFunctions.is_lists_equal(list(dependencies), list(dependencies_from_pack_metadata))


@pytest.mark.parametrize('entity_class', CLASSES)
def test_specific_entity(mocker, repo, entity_class):
    """ This test will run for each entity in the repo, when each time it will randomly generate dependencies
        in the repo and verify that the expected dependencies has been updated in the pack metadata correctly.

        Given
        - Content repository and content entity
        When
        - Running find_dependencies
        Then
        - Update packs dependencies in pack metadata
    """
    number_of_packs = 20
    repo.setup_content_repo(number_of_packs)
    repo.setup_one_pack('CommonTypes')

    methods_pool: list = \
        [(method_name, entity_class) for method_name in list(entity_class.__dict__.keys())
         if '_' != method_name[0]]

    dependencies = run_random_methods(repo, 0, methods_pool, len(methods_pool))

    with ChangeCWD(repo.path):
        # Circle froze on 3.7 dut to high usage of processing power.
        # pool = Pool(processes=cpu_count() * 2) is the line that in charge of the multiprocessing initiation,
        # so changing `cpu_count` return value to 1 still gives you multiprocessing but with only 2 processors,
        # and not the maximum amount.
        import demisto_sdk.commands.common.update_id_set as uis
        mocker.patch.object(uis, 'cpu_count', return_value=1)
        PackDependencies.find_dependencies('pack_0', silent_mode=True)

    dependencies_from_pack_metadata = repo.packs[0].pack_metadata.read_json_as_dict().get('dependencies').keys()

    if 'pack_0' in dependencies:
        dependencies.remove('pack_0')

    assert IsEqualFunctions.is_lists_equal(list(dependencies), list(dependencies_from_pack_metadata))
