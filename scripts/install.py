#!/usr/bin/env python3
"""Link this checkout under an explicit skill name without replacing an existing skill."""
import argparse
from pathlib import Path


def install(destination):
    source = Path(__file__).resolve().parent.parent
    target = Path(destination).expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise ValueError("Destination already exists; choose another path: " + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=True)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    try:
        print(install(args.destination))
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
