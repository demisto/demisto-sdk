from pathlib import Path
from typing import Optional

from TestSuite.yml import YAML, yaml

DEFAULT_JOB_CENTER_PATH = (
    Path(__file__).parent / "assets" / "default_job_center" / "jobcenter-sample.yml"
)


class JobCenter(YAML):
    """A TestSuite representation of an AgentiX Job Center job.

    Job Center jobs are flat files: ``Packs/<Pack>/JobCenters/<name>.yml``.
    """

    def __init__(self, tmpdir: Path, name: str, repo):
        self.name = name
        self._repo = repo
        self.repo_path = repo.path
        super().__init__(
            tmp_path=tmpdir / f"{self.name}.yml",
            repo_path=str(repo.path),
        )

    def build(self, yml: Optional[dict] = None) -> None:
        """Writes the given yml content to the file, if provided."""
        if yml is not None:
            self.write_dict(yml)

    def create_default_job_center(
        self,
        name: str = "Case Followup",
        job_id: str = "job-case-followup",
    ) -> None:
        """Writes a valid default Job Center job.

        Args:
            name: The ``name`` of the job.
            job_id: The top-level ``id`` of the job.
        """
        with open(DEFAULT_JOB_CENTER_PATH) as yml_file:
            yml = yaml.load(yml_file)
        yml["id"] = job_id
        yml["name"] = name
        self.build(yml=yml)
