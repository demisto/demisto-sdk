import os
import subprocess
from pathlib import Path

import typer

from demisto_sdk.commands.common.content_constant_paths import PYTHONPATH

app = typer.Typer()


@app.command("run")
def run(path: Path = Path.cwd()):
    path = Path("/Users/rshunim/dev/demisto/content/Packs/Arkime/Integrations/Arkime")
    os.chdir(path)
    # python_files =
    modules = subprocess.run(
        ["monkeytype", "list-modules"], text=True, check=True, capture_output=True
    ).stdout.splitlines()
    runner_path = path / "runner.py"
    python_path = ':'.join(str(path) for path in PYTHONPATH)
    env = os.environ.copy() | {'PYTHONPATH': os.environ['PYTHONPATH'] + ":" + python_path}
    subprocess.run(
        [
            # "/src/Tests/scripts/script_runner.py",
            "pytest",
            str(path),
            "--monkeytype-output=./monkeytype.sqlite3",
        ],
        check=True,
        env=env,
    )
    runner_path.write_text("\n".join(f"import {module}" for module in modules))
    filtered_modules = set(modules).difference(("demistomock", "CommonServerPython"))
    for module in filtered_modules:
        subprocess.run(["monkeytype", "-v", "stub", module], check=True)
        subprocess.run(["monkeytype", "-v", "apply", module], check=True)
    runner_path.unlink()


def main():
    app()


if __name__ == "__main__":
    main()
"""pip install pytest-monkeytype

# Generate annotations by running your pytest tests as usual:
py.test --monkeytype-output=./monkeytype.sqlite3

# Get a listing of modules annotated by monkeytype
monkeytype list-modules

# Generate a stub file for those annotations using monkeytype:
monkeytype stub some.module

# Apply these annotations directly
monkeytype apply some.module"""


# TODO - running pytest-monkeytypeon Arkime_test.py, now the next step is to solve our problem.
# we want to run it on a single script, not