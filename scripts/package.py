#!/usr/bin/env python3
"""Create a source bundle, excluding Git metadata, local records, caches, and fonts."""
import argparse
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def package(output):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).decode().split('\0')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(filter(None, files))):
            path = ROOT / name
            if path.is_file() and path != output:
                archive.write(path, 'xsolla-orchestrate/' + name)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    print(package(parser.parse_args().output))
