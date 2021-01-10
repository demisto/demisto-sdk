from demisto_sdk.commands.common.content.objects.pack_objects import (
    Classifier, ClassifierMapper, OldClassifier)
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    MAPPER, NEW_CLASSIFIER, OLD_CLASSIFIER)

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'


def mock_new_classifier(repo, classifier_data=None):
    pack = repo.create_pack('Temp')
    return pack.create_classifier(name='MyClassifier', content=classifier_data if classifier_data else NEW_CLASSIFIER)


def mock_old_classifier(repo, classifier_data=None):
    pack = repo.create_pack('Temp')
    return pack.create_classifier(name='MyClassifier', content=classifier_data if classifier_data else OLD_CLASSIFIER)


def mock_mapper(repo, mapper_data=None):
    pack = repo.create_pack('Temp')
    return pack.create_mapper(name='MyMapper', content=mapper_data if mapper_data else MAPPER)


class TestClassifierType:
    def test_objects_factory(self, repo):
        classifier = mock_new_classifier(repo)
        obj = path_to_pack_object(classifier.path)
        assert isinstance(obj, Classifier)

    def test_prefix(self, repo):
        classifier = mock_new_classifier(repo)
        obj = Classifier(classifier.path)
        assert obj.normalize_file_name() == 'classifier-MyClassifier.json'


class TestOldClassifierType:
    def test_objects_factory(self, repo):
        classifier = mock_old_classifier(repo)
        obj = path_to_pack_object(classifier.path)
        assert isinstance(obj, OldClassifier)

    def test_prefix(self, repo):
        classifier = mock_old_classifier(repo)
        obj = OldClassifier(classifier.path)
        assert obj.normalize_file_name() == 'classifier-MyClassifier.json'


class TestClassifierMapperType:
    def test_objects_factory(self, repo):
        mapper = mock_mapper(repo)
        obj = path_to_pack_object(mapper.path)
        assert isinstance(obj, ClassifierMapper)

    def test_prefix(self, repo):
        mapper = mock_mapper(repo)
        obj = ClassifierMapper(mapper.path)
        assert obj.normalize_file_name() == 'classifier-mapper-MyMapper.json'
