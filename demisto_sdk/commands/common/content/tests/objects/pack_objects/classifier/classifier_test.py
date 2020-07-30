from demisto_sdk.commands.common.content.content.objects.pack_objects import Classifier
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.constants import CLASSIFIERS_DIR, PACKS_DIR
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
CLASSIFIER = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CLASSIFIERS_DIR / 'classifier-sample_new.yml'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(CLASSIFIER)
    assert isinstance(obj, Classifier)


def test_prefix():
    obj = Classifier(CLASSIFIER)
    assert obj._normalized_file_name() == CLASSIFIER.name
