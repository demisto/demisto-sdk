from pathlib import Path

from demisto_sdk.commands.common.constants import JOB_CENTERS_DIR
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.job_center import JobCenter
from demisto_sdk.commands.validate.validators.ST_validators.ST110_is_valid_scheme import (
    SchemaValidator,
)
from TestSuite.job_center import DEFAULT_JOB_CENTER_PATH
from TestSuite.pack import Pack


def _load_default_job_center() -> dict:
    with open(DEFAULT_JOB_CENTER_PATH) as f:
        return dict(yaml.load(f))


def test_create_job_center_location(pack: Pack):
    """
    Given:
        - A TestSuite pack.
    When:
        - Calling pack.create_job_center with a name.
    Then:
        - The file is written directly under Packs/<pack>/JobCenters/ as <name>.yml.
    """
    job_center = pack.create_job_center("jobcenter-followup")
    path = Path(job_center.path)
    assert path.exists()
    assert path.name == "jobcenter-followup.yml"
    assert path.parent == Path(pack.path) / JOB_CENTERS_DIR


def test_create_job_center_default_name(pack: Pack):
    """
    Given:
        - A TestSuite pack.
    When:
        - Calling pack.create_job_center twice without a name.
    Then:
        - The files are named jobcenter-<index>.yml.
    """
    first = pack.create_job_center()
    second = pack.create_job_center()
    assert Path(first.path).name == "jobcenter-0.yml"
    assert Path(second.path).name == "jobcenter-1.yml"


def test_create_job_center_default_content(pack: Pack):
    """
    Given:
        - A TestSuite pack.
    When:
        - Calling pack.create_job_center without yml.
    Then:
        - The written content matches the default sample, with a top-level id and
          version and no commonfields section.
    """
    job_center = pack.create_job_center()
    data = get_file(job_center.path)
    assert data == _load_default_job_center()
    assert data["id"] == "job-case-followup"
    assert data["version"] == -1
    assert "commonfields" not in data


def test_create_default_job_center_overrides(pack: Pack):
    """
    Given:
        - A TestSuite JobCenter.
    When:
        - Calling create_default_job_center with a custom name and job_id.
    Then:
        - The custom name and top-level id are written; the rest matches the sample.
    """
    job_center = pack.create_job_center("custom")
    job_center.create_default_job_center(name="My Job", job_id="my-job-id")
    data = get_file(job_center.path)
    assert data["name"] == "My Job"
    assert data["id"] == "my-job-id"
    assert "commonfields" not in data
    expected = _load_default_job_center()
    expected.update({"name": "My Job", "id": "my-job-id"})
    assert data == expected


def test_create_job_center_with_yml(pack: Pack):
    """
    Given:
        - A TestSuite pack and custom yml content.
    When:
        - Calling pack.create_job_center with yml.
    Then:
        - The given yml is written as-is.
    """
    yml = _load_default_job_center()
    yml["jobName"] = "Other Job"
    job_center = pack.create_job_center("other", yml)
    assert get_file(job_center.path) == yml


def test_created_job_center_parses_and_passes_st110(pack: Pack):
    """
    Given:
        - A default Job Center job created via the TestSuite builder.
    When:
        - Loading it with BaseContent.from_path and running the SchemaValidator (ST110).
    Then:
        - A JobCenter object is returned with the expected id, and there are no
          structure errors.
    """
    job_center = pack.create_job_center()
    model = BaseContent.from_path(Path(job_center.path))
    assert isinstance(model, JobCenter)
    assert model.object_id == "job-case-followup"
    assert not model.structure_errors
    assert not SchemaValidator().obtain_invalid_content_items([model])
