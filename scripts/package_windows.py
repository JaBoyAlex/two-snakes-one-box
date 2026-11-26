"""Stage a development package from explicit, local toolchain inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VC_FILES = ['msvcp140.dll', 'msvcp140_atomic_wait.dll', 'vcruntime140.dll', 'vcruntime140_1.dll']
PRIVATE_DIRECTORIES = {'.local', 'recompdata', 'statesaves'}
PRIVATE_RUNTIME_DIRECTORIES = PRIVATE_DIRECTORIES | {'cache', 'dump', 'generated', 'logs', 'saves', 'user'}
PRIVATE_SUFFIXES = {
    '.iso', '.gcm', '.rvz', '.gcz', '.dol', '.rel', '.gci', '.raw', '.sav',
    '.log', '.dmp', '.trace', '.profraw', '.profdata',
}


def check_package_tree(root, *, runtime=False):
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        in_runtime = runtime or relative.parts[0].casefold() == 'runtime'
        private_directories = PRIVATE_RUNTIME_DIRECTORIES if in_runtime else PRIVATE_DIRECTORIES
        if any(part.casefold() in private_directories for part in relative.parts):
            raise SystemExit(f'Private path in package input: {relative.as_posix()}')
        if path.is_file() and (path.suffix.casefold() in PRIVATE_SUFFIXES
                               or path.name.casefold().endswith('_recomp.dll')):
            raise SystemExit(f'Private file in package input: {relative.as_posix()}')


def copy_game_runtime(runtime, destination, builds):
    game_settings = set()
    for build in builds:
        game_id = build['game_id'].casefold()
        revision = build['revision']
        # The runtime loads system, region-independent, game and revision settings.
        game_settings.update((f'{game_id[0]}.ini', f'{game_id[:3]}.ini',
                              f'{game_id}.ini', f'{game_id}r{revision}.ini'))

    def omit_unused_resources(folder, entries):
        relative = Path(folder).relative_to(runtime).as_posix().casefold()
        if relative == 'sys':
            return [name for name in entries if name.casefold() in {'themes', 'totaldb.dsy'}]
        if relative == 'sys/gamesettings':
            return [name for name in entries if name.casefold() not in game_settings]
        return ()

    shutil.copytree(runtime, destination, ignore=omit_unused_resources)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=Path, default=ROOT / '.local/runtime')
    parser.add_argument('--launcher', type=Path, default=ROOT / '.local/build/launcher/TwinSnakes.exe')
    parser.add_argument('--tools', type=Path, required=True, help='Directory holding python, cmake, ninja and llvm-mingw')
    parser.add_argument('--vc-runtime-dir', type=Path, help='Visual Studio x64 Microsoft.VC143.CRT directory')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--staging-root', type=Path, default=ROOT / '.local/packages',
                        help='Directory where the versioned build folder is staged')
    parser.add_argument('--version', default='0.1.0-dev')
    parser.add_argument('--stage-only', action='store_true',
                        help='Prepare a local RecompLauncher build folder without creating an archive')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', args.version):
        parser.error('--version must be a version such as 0.1.0-dev')
    vc_runtime = args.vc_runtime_dir
    if vc_runtime is None and os.environ.get('VCToolsRedistDir'):
        vc_runtime = Path(os.environ['VCToolsRedistDir']) / 'x64/Microsoft.VC143.CRT'
    if vc_runtime is None or any(not (vc_runtime / name).is_file() for name in VC_FILES):
        parser.error('Supply the x64 Microsoft.VC143.CRT redistributable directory with --vc-runtime-dir')
    for required in [args.launcher, args.runtime / 'moderngekko-run.exe', args.runtime / 'dolrecomp.exe',
                     args.runtime / 'dolphin-tool.exe', args.tools / 'python/python.exe',
                     args.tools / 'cmake/bin/cmake.exe', args.tools / 'ninja/ninja.exe',
                     args.tools / 'llvm-mingw/bin/clang.exe', args.tools / 'python/LICENSE.txt',
                     args.tools / 'cmake/doc/cmake/LICENSE.rst', args.tools / 'ninja/COPYING',
                     args.tools / 'llvm-mingw/LICENSE.TXT']:
        if not required.is_file():
            raise SystemExit(f'Missing package input: {required}')
    check_package_tree(args.runtime, runtime=True)
    stage = args.staging_root.resolve() / args.version
    if stage.exists():
        raise SystemExit('Use a new package version or remove the old staging directory after reviewing it.')
    stage.mkdir(parents=True)
    for name in ['README.md', 'LICENSE', 'THIRD_PARTY.md', 'recomplauncher.json',
                 'dependencies.lock.json', 'supported-builds.json', 'app/discs.py',
                 'app/rel_image.py', 'app/twin_snakes.py']:
        destination = stage / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    shutil.copytree(ROOT / 'docs', stage / 'docs')
    shutil.copy2(args.launcher, stage / 'TwinSnakes.exe')
    builds = json.loads((ROOT / 'supported-builds.json').read_text(encoding='utf-8'))['builds']
    copy_game_runtime(args.runtime, stage / 'runtime', builds)
    for name in VC_FILES:
        shutil.copy2(vc_runtime / name, stage / 'runtime' / name)
    shutil.copytree(args.tools / 'python', stage / 'python')
    omitted_directories = {
        # CMake's CLI help lives under share. Keep the notices in doc/cmake.
        'cmake/doc/cmake': ('html',),
        # The package builds and loads x64 game modules on Windows.
        'llvm-mingw': ('aarch64-w64-mingw32', 'armv7-w64-mingw32', 'i686-w64-mingw32'),
    }

    def omit_unused_directories(folder, _entries):
        return omitted_directories.get(Path(folder).relative_to(args.tools).as_posix(), ())

    for name in ['cmake', 'ninja', 'llvm-mingw']:
        shutil.copytree(args.tools / name, stage / 'tools' / name, ignore=omit_unused_directories)
    (stage / 'portable.txt').touch()
    # Run the entry points before recording the files in the assembled package.
    subprocess.run([str(stage / 'TwinSnakes.exe'), '--help'], check=True)
    subprocess.run([str(stage / 'runtime/moderngekko-run.exe'), '--help'], check=True)
    check_package_tree(stage)
    manifest = {}
    for path in sorted(stage.rglob('*')):
        if path.is_file():
            with path.open('rb') as stream:
                manifest[path.relative_to(stage).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (stage / 'package-files.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    if args.stage_only:
        print(f'Local RecompLauncher build folder: {stage}')
        return
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f'Two-Snakes-One-Box-v{args.version}-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(stage.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(stage).as_posix())
    with archive.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n', encoding='ascii')
    print(f'Packaged development tooling: {archive}')
    print('Do not publish until runtime notices/source availability and the clean-install/gameplay checks have been reviewed.')


if __name__ == '__main__':
    main()
