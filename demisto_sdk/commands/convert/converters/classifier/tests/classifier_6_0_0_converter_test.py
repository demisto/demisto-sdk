import io
import json
import os
from pathlib import Path

import pytest

from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import \
    Classifier
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.classifier.classifier_6_0_0_converter import \
    ClassifierSixConverter
from TestSuite.pack import Pack as MockPack
from TestSuite.repo import Repo


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


class TestClassifierSixConverter:
    OLD_CLASSIFIER_PATH = os.path.join(__file__,
                                       f'{git_path()}/demisto_sdk/commands/convert/converters/classifier/tests'
                                       '/test_data/classifier-Cymulate_5_9_9.json')

    def test_convert_dir(self, tmpdir):
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_classifier('Cymulate_5_9_9', util_load_json(self.OLD_CLASSIFIER_PATH))
        fake_pack_path = fake_pack.path
        classifier_converter = ClassifierSixConverter(Pack(fake_pack_path))
        assert classifier_converter.convert_dir() == 0
        expected_new_classifier_path = f'{tmpdir}/Packs/FakeTestPack/Classifiers/classifier-Cymulate.json'
        expected_new_mapper_path = f'{tmpdir}/Packs/FakeTestPack/Classifiers/classifier-mapper-incoming-Cymulate.json'
        self.assert_expected_file_output(expected_new_classifier_path, 'classifier-Cymulate')
        self.assert_expected_file_output(expected_new_mapper_path, 'classifier-mapper-incoming-Cymulate')

    def test_create_classifier_from_old_classifier(self, tmpdir):
        """
        Given:
        - 'old_classifier': Old classifier to convert into 6_0_0 classifier.
        - 'intersection_fields': List of the intersecting fields of classifiers 5_9_9 and below to classifiers 6_0_0.

        When:
        - Creating a 6_0_0 classifier convention from 5_9_9 and below classifier

        Then:
        - Ensure expected classifier is created in the expected path with the expected data.

        """
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_classifier('Cymulate_5_9_9', util_load_json(self.OLD_CLASSIFIER_PATH))
        fake_pack_path = fake_pack.path
        converter = ClassifierSixConverter(Pack(fake_pack_path))
        old_classifier = Classifier(self.OLD_CLASSIFIER_PATH)
        intersecting_fields = converter.get_classifiers_schema_intersection_fields()
        converter.create_classifier_from_old_classifier(old_classifier, intersecting_fields)
        classifier_expected_path = f'{tmpdir}/Packs/FakeTestPack/Classifiers/classifier-Cymulate.json'
        self.assert_expected_file_output(classifier_expected_path, 'classifier-Cymulate')

    def test_create_mapper_from_old_classifier(self, tmpdir):
        """
        Given:
        - 'old_classifier': Old classifier to convert into 6_0_0 classifier.

        When:
        - Creating a 6_0_0 mapper convention from 5_9_9 and below classifier

        Then:
        - Ensure expected mapper is created in the expected path with the expected data.

        """
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_classifier('Cymulate_5_9_9', util_load_json(self.OLD_CLASSIFIER_PATH))
        fake_pack_path = fake_pack.path
        converter = ClassifierSixConverter(Pack(fake_pack_path))
        old_classifier = Classifier(self.OLD_CLASSIFIER_PATH)
        converter.create_mapper_from_old_classifier(old_classifier)
        mapper_path = f'{tmpdir}/Packs/FakeTestPack/Classifiers/classifier-mapper-incoming-Cymulate.json'
        self.assert_expected_file_output(mapper_path, 'classifier-mapper-incoming-Cymulate')

    CALCULATE_NEW_PATH_INPUTS = [('QRadar-v3', False, 'classifier-QRadar_v3.json'),
                                 ('QRadar v2', True, 'classifier-mapper-incoming-QRadar_v2.json')]

    @pytest.mark.parametrize('old_classifier_brand, is_mapper, expected_suffix', CALCULATE_NEW_PATH_INPUTS)
    def test_calculate_new_path(self, tmpdir, old_classifier_brand: str, is_mapper: bool, expected_suffix: str):
        """
        Given:
        - 'old_classifier_brand': Old classifier brand name.
        - 'is_mapper': Whether file created is mapper or classifier of 6_0_0 convention.

        When:
        - Creating the path to the newly classifier/mapper of 6_0_0 convention.

        Then:
        - Ensure the expected path is returned.

        """
        classifier_six_converter = ClassifierSixConverter(Pack(tmpdir))
        assert classifier_six_converter.calculate_new_path(old_classifier_brand,
                                                           is_mapper) == f'{tmpdir}/Classifiers/{expected_suffix}'

    @staticmethod
    def assert_expected_file_output(result_path: str, file_name: str):
        expected_result_path = os.path.join(__file__,
                                            f'{git_path()}/demisto_sdk/commands/convert/converters/classifier/'
                                            f'tests/test_data/{file_name}.json')
        assert os.path.exists(result_path)
        assert util_load_json(result_path) == util_load_json(expected_result_path)
