"""Refuse staging files outside the reviewed public-source list."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    allowed = set(json.loads((ROOT / 'publication-files.json').read_text()))
    staged = set(subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z'], text=True).split('\0')) - {''}
    unexpected = staged - allowed
    missing = allowed - staged
    if unexpected or missing:
        raise SystemExit(f'Publication list mismatch: unexpected={sorted(unexpected)}, missing={sorted(missing)}')
    for name in staged:
        path = ROOT / name
        if path.stat().st_size > 1024 * 1024:
            raise SystemExit(f'Unexpected large public-source file: {name}')
    print(f'Public source allowlist verified: {len(staged)} files; no build or game storage staged.')


if __name__ == '__main__':
    main()
