import argparse
from pathlib import Path
from typing import Optional, Sequence
import subprocess
from uuid import uuid4
from demisto_sdk.commands.common.tools import get_content_path
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        integration_script = BaseContent.from_path(Path(filename))
        print(integration_script)
        if not isinstance(integration_script, IntegrationScript):
            print(f"Skipping {filename} as it is not a content item.")
            continue
        # run runner.sh
        subprocess.Popen(
            f"sh -x runner.sh '{integration_script.object_id.replace(' ', '').lower()}' '{get_content_path()}' '{integration_script.docker_image}' '{integration_script.path.parent.relative_to(get_content_path())}'",
            shell=True,
            cwd=Path(__file__).parent,
        ).communicate()
    return retval


if __name__ == "__main__":
    raise SystemExit(main())
