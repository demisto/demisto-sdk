from demisto_sdk.commands.common.content.objects.pack_objects.job.job import Job
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object

sample_job_name = "sample-job"
sample_file_path = f"Jobs/{sample_job_name}.json"


class TestJob:
    def test_objects_factory(self, datadir):
        obj = path_to_pack_object(datadir[sample_file_path])
        assert isinstance(obj, Job)

    def test_prefix(self, datadir):
        """
        Test that Jobs created from files whose name does not start with `job-` are normalized correctly.
        """
        obj = Job(datadir[sample_file_path])
        assert obj.normalize_file_name() == f"job-{sample_job_name}.json"
