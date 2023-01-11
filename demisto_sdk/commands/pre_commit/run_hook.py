import argparse
import subprocess
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)
    subprocess.run(["demisto-sdk", args.command, "-i", ",".join(args.filename)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
