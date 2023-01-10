import argparse
from typing import Optional, Sequence
import subprocess

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        integration_script = BaseContent.from_path(filename)
        if not isinstance(integration_script, IntegrationScript):
            print(f"Skipping {filename} as it is not a content item.")
            continue
        # run runner.sh
        subprocess.Popen(
            f"runner.sh {integration_script.object_id} {integration_script.docker_image} {integration_script.path}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
