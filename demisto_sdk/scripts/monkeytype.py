import os
import subprocess
import sys
from pathlib import Path

from demisto_sdk.commands.common.content_constant_paths import PYTHONPATH


def monkeytype(path: Path):
    if path.is_file():
        path = path.parent
    runner_path = path / "runner.py"
    python_path = ":".join(str(path_) for path_ in PYTHONPATH + [path])
    env = os.environ.copy() | {"PYTHONPATH": os.environ["PYTHONPATH"] + ":" + python_path}
    subprocess.run(
        [
            "pytest",
            str(path),
            "--monkeytype-output=./monkeytype.sqlite3",
        ],
        check=True,
        env=env,
        cwd=path,
    )
    modules = subprocess.run(
        ["monkeytype", "list-modules"],
        text=True,
        check=True,
        capture_output=True,
        cwd=path,
        env=env,
    ).stdout.splitlines()
    filtered_modules = set(modules).difference(("demistomock", "CommonServerPython")) # we don't want to run monkeytype on these
    runner_path.write_text(
        "\n".join(f"import {module}\n{module}.main()" for module in filtered_modules)
    )
    for module in filtered_modules: # actually run monkeytype on each module
        subprocess.run(
            ["monkeytype", "-v", "stub", module], check=True, cwd=path, env=env
        )
        subprocess.run(
            ["monkeytype", "-v", "apply", module], check=True, cwd=path, env=env
        )
    runner_path.unlink()


def main():
    monkeytype(Path(sys.argv[0]))


if __name__ == "__main__":
    main()
