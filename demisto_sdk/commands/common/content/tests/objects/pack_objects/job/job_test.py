from pathlib import Path

from demisto_sdk.commands.common.content.objects.pack_objects.job.job import \
    Job
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object

sample_file_path = Path('Jobs/sample-job.json')
sample_file_folder = Path("Jobs")


class TestJob:
    def test_objects_factory(self, datadir):
        obj = path_to_pack_object(datadir / sample_file_path)
        assert isinstance(obj, Job)

    def test_prefix(self, datadir):
        obj = Job(datadir / sample_file_path)
        assert obj.normalize_file_name() == 'job-' + sample_file_path.name

    def test_files_detection(self, datadir):
        obj = Job(datadir / sample_file_path)
        assert obj.readme.path == Path(datadir / sample_file_folder / f"{sample_file_path.stem}_README.md")
        assert obj.changelog.path == Path(datadir / sample_file_folder / f"{sample_file_path.stem}_CHANGELOG.md")
