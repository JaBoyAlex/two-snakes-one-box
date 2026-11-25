"""Prepare pinned upstream source checkouts or portable Windows tools."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def fetch_verified(spec, path):
    with urlopen(spec['url'], timeout=60) as response, path.open('wb') as destination:
        shutil.copyfileobj(response, destination)
    with path.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != spec['sha256']:
            raise SystemExit(f'Download hash mismatch: {spec["url"]}')


def prepare_windows_tools(tools, lock):
    if tools.exists():
        raise SystemExit('Choose a new directory for the pinned Windows tools.')
    tools.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='windows-tools-', dir=tools.parent) as directory:
        temporary = Path(directory)
        staged = temporary / 'tools'
        staged.mkdir()
        for name, spec in lock.items():
            print(f'Preparing {name}', flush=True)
            archive = temporary / f'{name}.zip'
            fetch_verified(spec, archive)
            extracted = temporary / name
            with ZipFile(archive) as package:
                package.extractall(extracted)
            source = extracted / spec['root'] if 'root' in spec else extracted
            source.rename(staged / name)
            if 'copying' in spec:
                fetch_verified(spec['copying'], staged / name / 'COPYING')
        staged.rename(tools)
    print(f'Pinned Windows tools are ready at {tools}')


def prepare_source(source, lock):
    source.parent.mkdir(parents=True, exist_ok=True)
    fresh = not source.exists()
    if fresh:
        subprocess.run(['git', 'clone', '--config', 'core.longpaths=true', '--no-checkout',
                        lock['url'], str(source)], check=True)
    git = ['git', '-c', 'core.longpaths=true', '-C', str(source)]
    if not fresh and subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip() == lock['commit']:
        ready = subprocess.check_output([*git, 'submodule', 'status', '--recursive'], text=True)
        if ready and all(line.startswith(' ') for line in ready.splitlines()):
            print('Pinned source dependencies are already checked out.')
            return
    if not fresh and subprocess.check_output([*git, 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise SystemExit('Upstream checkout has local changes; refusing to replace them.')
    subprocess.run([*git, 'fetch', 'origin', lock['commit']], check=True)
    subprocess.run([*git, 'checkout', '--detach', lock['commit']], check=True)
    subprocess.run([*git, 'submodule', 'update', '--init', '--recursive', '--jobs', '8'], check=True)
    for relative, expected in [('vendor/dolphin', lock['recompcore_commit']), ('vendor/dolphin/DolRecomp', lock['dolrecomp_commit'])]:
        actual = subprocess.check_output(['git', '-C', str(source / relative), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != expected:
            raise SystemExit(f'Unexpected dependency revision: {relative}')
    print('Pinned source dependencies are ready.')


def main():
    parser = argparse.ArgumentParser()
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument('--source', type=Path, default=ROOT / '.local/sources/ModernGekko')
    targets.add_argument('--windows-tools', type=Path, help='Prepare a new pinned tool directory for packaging')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
    if args.windows_tools is not None:
        prepare_windows_tools(args.windows_tools.resolve(), lock['windows_tools'])
    else:
        prepare_source(args.source.resolve(), lock['ModernGekko'])


if __name__ == '__main__':
    main()
