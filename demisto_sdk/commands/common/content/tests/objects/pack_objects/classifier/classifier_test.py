from demisto_sdk.commands.common.constants import CLASSIFIERS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Classifier
from demisto_sdk.commands.common.content.objects_factory import \
    ContentObjectFactory
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
CLASSIFIER = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CLASSIFIERS_DIR / 'classifier-sample_new.json'


def test_objects_factory():
    obj = ContentObjectFactory.from_path(CLASSIFIER)
    assert isinstance(obj, Classifier)


def test_prefix():
    obj = Classifier(CLASSIFIER)
    assert obj.normalize_file_name() == CLASSIFIER.name
