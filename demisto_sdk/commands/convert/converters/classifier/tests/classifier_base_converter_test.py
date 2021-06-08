import os
from typing import Optional

import pytest
from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import \
    Classifier
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.classifier.classifier_base_converter import \
    ClassifierBaseConverter


class TestLayoutBaseConverter:
    TEST_PACK_PATH = os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/tests/test_data/Packs/ExtraHop')
    OLD_CLASSIFIER_SCHEMA_PATH = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/classifier/tests/test_data',
                     'classifier_5_9_9.yml'))
    NEW_CLASSIFIER_SCHEMA_PATH = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/classifier/tests/test_data',
                     'classifier.yml'))

    def setup(self):
        self.classifier_converter = ClassifierBaseConverter(Pack(self.TEST_PACK_PATH))

    def test_get_classifiers_schema_intersection_fields(self):
        """
        Given:
        - Two schemas of classifiers (classifier 5_9_9 and below, classifier 6_0_0 and above schemas

        When:
        - Wanting to retrieve all intersecting fields between schemas that are not excluded.

        Then:
        - Ensure expected intersecting fields are returned.

        """
        result = self.classifier_converter.get_classifiers_schema_intersection_fields(self.OLD_CLASSIFIER_SCHEMA_PATH,
                                                                                      self.NEW_CLASSIFIER_SCHEMA_PATH)
        assert result == {'custom', 'defaultIncidentType', 'feed', 'incidentSamples', 'indicatorSamples',
                          'isDefault', 'keyTypeMap', 'modified', 'propagationLabels', 'sortValues', 'transformer',
                          'unclassifiedCases', 'version'}

    EXTRACT_CLASSIFIER_NAME_INPUTS = [('classifier-Cymulate_5_9_9', 'Cymulate'),
                                      ('classifier-Cymulate-unexpected', None)]

    @pytest.mark.parametrize('name_suffix, expected', EXTRACT_CLASSIFIER_NAME_INPUTS)
    def test_extract_classifier_name(self, name_suffix: str, expected: Optional[str]):
        """
        Given:
        - Old classifier object.

        When:
        - Wanting to retrieve its name from the path.

        Then:
        - Ensure expected name is extracted, if name corresponds to the expected naming format. None if not.

        """
        old_classifier_path = os.path.normpath(os.path.join(__file__,
                                                            f'{git_path()}/demisto_sdk/commands/convert/converters/'
                                                            f'classifier/tests/test_data/{name_suffix}.json'))
        assert self.classifier_converter.extract_classifier_name(
            Classifier(old_classifier_path)) == expected
