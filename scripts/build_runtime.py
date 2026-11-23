"""Compile and stage only open-source runtime files, never game-derived output."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def apply_patch(source, name, *, after=()):
    patch = ROOT / 'patches' / name
    command = ['git', '-C', str(source), 'apply']
    if not subprocess.run([*command, '--reverse', '--check', str(patch)], capture_output=True).returncode:
        return
    for prerequisite in after:
        apply_patch(source, prerequisite)
    subprocess.run([*command, '--check', str(patch)], check=True)
    subprocess.run([*command, str(patch)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / '.local/sources/ModernGekko')
    parser.add_argument('--build', type=Path, default=ROOT / '.local/build/runtime')
    parser.add_argument('--output', type=Path, default=ROOT / '.local/runtime')
    parser.add_argument('--jobs', type=int, default=min(8, os.cpu_count() or 2))
    args = parser.parse_args()
    source, build, output = (p.resolve() for p in (args.source, args.build, args.output))
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())['ModernGekko']
    for directory, expected in [(source, lock['commit']), (source / 'vendor/dolphin', lock['recompcore_commit']), (source / 'vendor/dolphin/DolRecomp', lock['dolrecomp_commit'])]:
        revision = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != expected:
            raise SystemExit(f'Source revision does not match dependencies.lock.json: {directory.name}')
    apply_patch(source, 'moderngekko-auto-gamepad.patch')
    apply_patch(source, 'moderngekko-no-empty-mod-hooks.patch')
    apply_patch(source / 'vendor/dolphin', 'recompcore-gamepad-bindings.patch',
                after=('recompcore-auto-gamepad.patch',))
    apply_patch(source / 'vendor/dolphin', 'recompcore-twin-snakes-idle.patch')
    subprocess.run(['cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
                    '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_TESTING=OFF',
                    f'-DPython3_EXECUTABLE={os.sys.executable}',
                    '-DDOLRECOMP_ENABLE_LLVM=OFF', '-DMODERNGEKKO_ENABLE_DISC_TOOL=ON',
                    '-DMODERNGEKKO_GAMECUBE_CONTROLLERS=ON',
                    '-DMODERNGEKKO_DEFAULT_WINDOW_TITLE=Twin Snakes Recomp',
                    '-DMODERNGEKKO_LOG_FILENAME=TwinSnakes.log'], check=True)
    targets = ['moderngekko-run', 'dolrecomp', 'dolphin-tool']
    subprocess.run(['cmake', '--build', str(build), '--target', *targets, '-j', str(args.jobs)], check=True)
    output.mkdir(parents=True, exist_ok=True)
    extension = '.exe' if os.name == 'nt' else ''
    for target in targets:
        binary_name = 'DolphinTool' if os.name == 'nt' and target == 'dolphin-tool' else target
        matches = list(build.rglob(binary_name + extension))
        if not matches and os.name == 'nt' and target == 'dolphin-tool':
            matches = list((source / 'Binary').rglob(binary_name + extension))
        if len(matches) != 1:
            raise SystemExit(f'Expected exactly one built {target}, found {len(matches)}')
        shutil.copy2(matches[0], output / (target + extension))
        for dependency in matches[0].parent.glob('*.dll'):
            shutil.copy2(dependency, output / dependency.name)
    dolphin = source / 'vendor/dolphin'
    shutil.copytree(dolphin / 'Data/Sys', output / 'Sys', dirs_exist_ok=True)
    # Only these source directories participate in per-game module compilation.
    # In particular, module-template/generated contains upstream example game data
    # and is deliberately excluded from staging.
    for relative in ['module-template', 'GXRuntime/include', 'GXRuntime/src/core', 'Source/Core/Core/PowerPC/StaticRecomp']:
        shutil.copytree(dolphin / relative, output / 'sdk' / relative,
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns('generated', 'build', '.git', '__pycache__'))
    licenses = output / 'licenses'
    licenses.mkdir(exist_ok=True)
    for directory, name in [(source, 'ModernGekko'), (dolphin, 'RecompCore'), (dolphin / 'DolRecomp', 'DolRecomp')]:
        if (directory / 'LICENSES').is_dir():
            shutil.copytree(directory / 'LICENSES', licenses / name, dirs_exist_ok=True)
        for license_path in directory.glob('COPYING*'):
            shutil.copy2(license_path, licenses / f'{name}-{license_path.name}')
        for license_path in directory.glob('LICENSE*'):
            if license_path.is_file():
                shutil.copy2(license_path, licenses / f'{name}-{license_path.name}')
    shutil.copy2(ROOT / 'dependencies.lock.json', output / 'dependencies.lock.json')
    print(f'Runtime staged at {output}')


if __name__ == '__main__':
    main()
