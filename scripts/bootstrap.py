"""Fetch exact source revisions; all upstream files stay in ignored build storage."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())['ModernGekko']
    source = ROOT / '.local/sources/ModernGekko'
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        subprocess.run(['git', 'clone', '--no-checkout', lock['url'], str(source)], check=True)
    if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == lock['commit']:
        ready = subprocess.check_output(['git', '-C', str(source), 'submodule', 'status', '--recursive'], text=True)
        if ready and all(line.startswith(' ') for line in ready.splitlines()):
            print('Pinned source dependencies are already checked out.')
            return
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise SystemExit('Upstream checkout has local changes; refusing to replace them.')
    subprocess.run(['git', '-C', str(source), 'fetch', 'origin', lock['commit']], check=True)
    subprocess.run(['git', '-C', str(source), 'checkout', '--detach', lock['commit']], check=True)
    subprocess.run(['git', '-c', 'core.longpaths=true', '-C', str(source), 'submodule', 'update', '--init', '--recursive', '--jobs', '8'], check=True)
    for relative, expected in [('vendor/dolphin', lock['recompcore_commit']), ('vendor/dolphin/DolRecomp', lock['dolrecomp_commit'])]:
        actual = subprocess.check_output(['git', '-C', str(source / relative), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != expected:
            raise SystemExit(f'Unexpected dependency revision: {relative}')
    print('Pinned source dependencies are ready.')


if __name__ == '__main__':
    main()
