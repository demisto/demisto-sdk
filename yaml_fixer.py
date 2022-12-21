import itertools
from pathlib import Path

import chardet
import yaml
from bs4.dammit import UnicodeDammit

ROOT = Path("/workspaces/demisto-sdk/yaml_test")


def fix():
    for yml_file in itertools.chain(ROOT.glob("**/*.yml"), ROOT.glob("**/*.yaml")):
        path = Path(yml_file)
        guess = chardet.detect(path.read_bytes())
        encoding = guess.get('encoding')
        confidence = guess.get('confidence', 0)

        if not encoding or confidence < 0.6:
            print(f"cannot detect encoding for {path}")
            continue

        if encoding == 'utf-8':
            print(path, "is already utf-8")
            continue

        print(f"changing {path} encoding from {encoding} to utf-8")
        content = path.read_text(encoding=encoding)
        path.unlink()
        path.write_text(content, encoding="utf8")
        print("changed to", chardet.detect(path.read_bytes())['encoding'])


def create():
    for suffix in (".yml", ".yaml"):
        text = "Nett hier. Aber waren Sie schon mal in Baden-Württemberg?"
        path = (ROOT / "test").with_suffix(suffix)
        if path.exists():
            print("deleting ", path)
            path.unlink()
        path.touch()

        with path.open("w", encoding="latin-1") as f:
            print("creating", path)
            yaml.dump({"text": text}, encoding="latin-1", stream=f)


if __name__ == "__main__":
    # create()
    fix()
