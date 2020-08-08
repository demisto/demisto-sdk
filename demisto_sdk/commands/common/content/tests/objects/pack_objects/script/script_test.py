from pathlib import Path

from demisto_sdk.commands.common.content.content.objects.pack_objects import Script
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry


class TestNotUnifiedScript:
    def test_objects_factory(self, datadir):
        obj = ContentObjectFacotry.from_path(datadir["FindSimilarIncidentsByText.yml"])
        assert isinstance(obj, Script)

    def test_prefix(self, datadir):
        obj = Script(datadir["FindSimilarIncidentsByText.yml"])
        assert obj.normalized_file_name() == "script-FindSimilarIncidentsByText.yml"

    def test_files_detection(self, datadir):
        obj = Script(datadir["FindSimilarIncidentsByText.yml"])
        assert obj.readme is None
        assert obj.code_path == Path(datadir["FindSimilarIncidentsByText.py"])
        assert obj.changelog.path == Path(datadir["CHANGELOG.md"])
        assert obj.description_path is None
        assert obj.png_path is None
        assert obj.unittest_path is None

    def test_is_unify(self, datadir):
        obj = Script(datadir["FindSimilarIncidentsByText.yml"])
        assert not obj.is_unify()


class TestUnifiedScript:
    def test_objects_factory(self, datadir):
        obj = ContentObjectFacotry.from_path(datadir["script-FindSimilarIncidentsByText.yml"])
        assert isinstance(obj, Script)

    def test_prefix(self, datadir):
        obj = Script(datadir["script-FindSimilarIncidentsByText.yml"])
        assert obj.normalized_file_name() == "script-FindSimilarIncidentsByText.yml"

    def test_files_detection(self, datadir):
        obj = Script(datadir["script-FindSimilarIncidentsByText.yml"])
        assert obj.readme is None
        assert obj.code_path is None
        assert obj.changelog.path == Path(datadir["script-FindSimilarIncidentsByText_CHANGELOG.md"])
        assert obj.description_path is None
        assert obj.png_path is None

    def test_is_unify(self, datadir):
        obj = Script(datadir["script-FindSimilarIncidentsByText.yml"])
        assert obj.is_unify()
