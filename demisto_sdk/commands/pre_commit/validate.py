import argparse
import subprocess
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)
    subprocess.run(["demisto-sdk", "validate", "-i", ",".join(args.filename)], check=True)



if __name__ == "__main__":
    raise SystemExit(main())
