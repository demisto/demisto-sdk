from pathlib import Path

from demisto_sdk.commands.common.content.objects.pack_objects.job.job import Job
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object

sample_file_name = "job-sample.json"


class TestJob:
    def test_objects_factory(self, datadir):
        obj = path_to_pack_object(datadir[sample_file_name])  # todo can't read file
        assert isinstance(obj, Job)

    def test_prefix(self, datadir):
        obj = Job(datadir[sample_file_name])  # todo can't read file
        assert obj.normalize_file_name() == sample_file_name

    def test_files_detection(self, datadir):
        obj = Job(datadir[sample_file_name])
        # assert obj.readme.path == Path(datadir["integration-sample_README.md"]) # todo
        # assert obj.changelog.path == Path(datadir["integration-sample_CHANGELOG.md"]) # todo
