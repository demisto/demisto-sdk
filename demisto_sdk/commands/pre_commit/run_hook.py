import argparse
import subprocess
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)
    print(args.filenames)
    print(args.command)
    res = subprocess.run(["demisto-sdk", args.command, "-i", ",".join(args.filenames)])
    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
