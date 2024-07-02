import os
import subprocess
from pathlib import Path

import typer

app = typer.Typer()


@app.command("run")
def run(path: Path = Path.cwd()):
    os.chdir(path)
    # python_files =
    subprocess.run(["pytest", "/src/Tests/scripts/script_runner.py", "--monkeytype-output=./monkeytype.sqlite3"], check=True)
    (path/"runner.py").write_text("\n".join(f"import {module}" for module in modules))
    modules = subprocess.run(["monkeytype", "list-modules"], text=True, check=True, capture_output=True).stdout.splitlines()
    filtered_modules = set(modules).difference(("demistomock", "CommonServerPython"))
    for module in filtered_modules:
        subprocess.run(["monkeytype", "-v", "stub", module], check=True)
        subprocess.run(["monkeytype", "-v", "apply", module], check=True)


def main():
    app()


if __name__ == '__main__':
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
