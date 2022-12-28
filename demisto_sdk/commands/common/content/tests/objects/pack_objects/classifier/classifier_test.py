from demisto_sdk.commands.common.constants import CLASSIFIERS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import (
    Classifier,
    ClassifierMapper,
    OldClassifier,
)
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
CLASSIFIER = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / CLASSIFIERS_DIR
    / "classifier-sample_new.json"
)


class TestClassifierType:
    def test_objects_factory(self):
        obj = path_to_pack_object(CLASSIFIER)
        assert isinstance(obj, Classifier)

    def test_prefix(self):
        obj = Classifier(CLASSIFIER)
        assert obj.normalize_file_name() == "classifier-sample_new.json"


class TestOldClassifierType:
    def test_objects_factory(self, datadir):
        obj = path_to_pack_object(datadir["old_classifier.json"])
        assert isinstance(obj, OldClassifier)

    def test_prefix(self, datadir):
        obj = OldClassifier(datadir["old_classifier.json"])
        assert obj.normalize_file_name() == "classifier-old_classifier.json"


class TestClassifierMapperType:
    def test_objects_factory(self, datadir):
        obj = path_to_pack_object(datadir["classifier_mapper.json"])
        assert isinstance(obj, ClassifierMapper)

    def test_prefix(self, datadir):
        obj = ClassifierMapper(datadir["classifier_mapper.json"])
        assert obj.normalize_file_name() == "classifier-mapper-classifier_mapper.json"
