from pathlib import Path

import typer

app = typer.Typer()


@app.command("run")
def run(path: Path = Path.cwd()):
    print(list(path.iterdir()))


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
