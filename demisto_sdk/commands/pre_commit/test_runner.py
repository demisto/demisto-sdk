import argparse
import logging
from pathlib import Path
from typing import Optional, Sequence
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logging_setup
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
import demisto_sdk.commands.common.docker_helper as docker_helper
from demisto_sdk.commands.lint.helpers import stream_docker_container_output

logging_setup(1)

logger = logging.getLogger("demisto-sdk")
docker_client = docker_helper.init_global_docker_client()

PYTHONPATH = [
    Path(CONTENT_PATH / "Packs" / "Base" / "Scripts" / "CommonServerPython"),
    Path(CONTENT_PATH / "Tests" / "demistomock"),
]

PYTHONPATH.extend(dir for dir in Path(CONTENT_PATH / "Packs" / "ApiModules" / "Scripts").iterdir())

PYTHONPATH = [f"/content/{path.relative_to(CONTENT_PATH)}" for path in PYTHONPATH]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)

    for filename in args.filenames:
        integration_script = BaseContent.from_path(Path(filename))
        if not isinstance(integration_script, IntegrationScript):
            print(f"Skipping {filename} as it is not a content item.")
            continue
        working_dir = f"/content/{integration_script.path.parent.relative_to(CONTENT_PATH)}"

        try:
            container = docker_client.containers.run(
                image=integration_script.docker_image,
                remove=True,
                environment={"PYTHONPATH": ":".join(PYTHONPATH)},
                volumes=[f"{CONTENT_PATH}:/content", f"{(Path(__file__).parent / 'runner.sh')}:/runner.sh"],
                command="sh /runner.sh",
                working_dir=working_dir,
                detach=True,
            )
            stream_docker_container_output(container.logs(stream=True), logging_level=logger.info)
        except Exception as e:
            logger.error(f"Failed to run test for {filename}: {e}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
