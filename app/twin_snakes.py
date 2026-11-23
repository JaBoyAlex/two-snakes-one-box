"""Local-disc setup and stable entry point for Twin Snakes Recomp."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discs import DiscError, inspect_iso, validate_pair
from rel_image import link_rel_image

ROOT = Path(__file__).resolve().parents[1]
BUILD_FORMAT = 3


class SetupError(Exception):
    def __init__(self, message, code=21):
        super().__init__(message)
        self.code = code


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def default_data():
    if os.environ.get('RECOMPLAUNCHER_DATA'):
        return Path(os.environ['RECOMPLAUNCHER_DATA'])
    if (ROOT / 'portable.txt').exists():
        return ROOT / 'recompdata'
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'TwinSnakesRecomp'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/TwinSnakesRecomp'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'TwinSnakesRecomp'


def progress(fraction, message):
    print(f'progress {fraction:.3f} {message}', flush=True)


def pick_disc(number):
    import ctypes
    from ctypes import wintypes

    class OpenFileName(ctypes.Structure):
        _fields_ = [('lStructSize', wintypes.DWORD), ('hwndOwner', wintypes.HWND),
                    ('hInstance', wintypes.HINSTANCE), ('lpstrFilter', wintypes.LPCWSTR),
                    ('lpstrCustomFilter', wintypes.LPWSTR), ('nMaxCustFilter', wintypes.DWORD),
                    ('nFilterIndex', wintypes.DWORD), ('lpstrFile', wintypes.LPWSTR),
                    ('nMaxFile', wintypes.DWORD), ('lpstrFileTitle', wintypes.LPWSTR),
                    ('nMaxFileTitle', wintypes.DWORD), ('lpstrInitialDir', wintypes.LPCWSTR),
                    ('lpstrTitle', wintypes.LPCWSTR), ('Flags', wintypes.DWORD),
                    ('nFileOffset', wintypes.WORD), ('nFileExtension', wintypes.WORD),
                    ('lpstrDefExt', wintypes.LPCWSTR), ('lCustData', ctypes.c_ssize_t),
                    ('lpfnHook', ctypes.c_void_p), ('lpTemplateName', wintypes.LPCWSTR),
                    ('pvReserved', ctypes.c_void_p), ('dwReserved', wintypes.DWORD),
                    ('FlagsEx', wintypes.DWORD)]

    filename = ctypes.create_unicode_buffer(32768)
    dialog = OpenFileName()
    dialog.lStructSize = ctypes.sizeof(dialog)
    dialog.lpstrFilter = 'GameCube disc images\0*.iso;*.gcm;*.rvz;*.gcz\0\0'
    dialog.lpstrFile = ctypes.cast(filename, wintypes.LPWSTR)
    dialog.nMaxFile = len(filename)
    dialog.lpstrTitle = f'Select Twin Snakes — Disc {number}'
    dialog.Flags = 0x1000 | 0x800 | 0x8  # File/path must exist; preserve cwd.
    if not ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(dialog)):
        raise SetupError('Disc selection cancelled.', 26)
    return Path(filename.value)


@contextmanager
def installation_lock(data):
    data.mkdir(parents=True, exist_ok=True)
    with (data / 'session.lock').open('a+b') as stream:
        stream.seek(0)
        stream.write(b'0')
        stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise SetupError('This installation is already building or running.', 24) from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def run(command, log, *, env=None, code=22, on_line=None):
    # Always an argument vector. Disc paths never become shell expressions.
    log.write('\n' + json.dumps([str(p) for p in command]) + '\n')
    log.flush()
    process = subprocess.Popen([str(p) for p in command], stdout=subprocess.PIPE if on_line else log,
                               stderr=subprocess.STDOUT, env=env,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        if on_line:
            with process.stdout:
                for raw_line in process.stdout:
                    line = raw_line.decode('utf-8', errors='replace').rstrip('\r\n')
                    log.write(line + '\n')
                    log.flush()
                    on_line(line)
        result = process.wait()
    except BaseException:
        process.terminate()
        process.wait()
        raise
    if result:
        raise SetupError(f'{Path(command[0]).name} stopped with code {result}. See the local log.', code)


def tool(runtime, name):
    result = runtime / (name + ('.exe' if os.name == 'nt' else ''))
    if not result.is_file():
        raise SetupError(f'Missing {name}. Build/stage the runtime first; see docs/BUILDING.md.')
    return result


def normalize_disc(path, cache, runtime, log):
    path = path.resolve(strict=True)
    extension = path.suffix.lower()
    if path.name.lower().endswith(('.nkit.iso', '.nkit.gcz')):
        raise DiscError('Choose a full ISO, GCM, RVZ or GCZ dump. NKit is not supported.')
    if extension in ('.iso', '.gcm'):
        return path
    if extension not in ('.rvz', '.gcz'):
        raise DiscError('Choose ISO, GCM, RVZ or GCZ. NKit and CISO are not supported yet.')
    progress(0.04, f'Checking {path.name}')
    key = digest(path)
    output = cache / 'normalized' / (key + '.iso')
    if not output.is_file():
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix('.partial.iso')
        if temporary.exists():
            temporary.unlink()
        run([tool(runtime, 'dolphin-tool'), 'convert', '-i', path, '-o', temporary, '-f', 'iso'], log, code=20)
        inspect_iso(temporary)
        temporary.replace(output)
    return output


def compiler_environment(runtime):
    env = os.environ.copy()
    tools = runtime.parent / 'tools'
    paths = [p for p in [tools / 'llvm-mingw/bin', tools / 'cmake/bin', tools / 'ninja'] if p.is_dir()]
    env['PATH'] = os.pathsep.join([*(str(p) for p in paths), env.get('PATH', '')])
    env['CMAKE_NINJA_FORCE_RESPONSE_FILE'] = '1'
    env['NINJA_STATUS'] = '[%f/%t] '
    cmake = shutil.which('cmake', path=env['PATH'])
    if not cmake or not shutil.which('ninja', path=env['PATH']):
        raise SetupError('CMake and Ninja are required for local recompilation.')
    compiler = next((shutil.which(name, path=env['PATH']) for name in ['clang', 'gcc', 'cl'] if shutil.which(name, path=env['PATH'])), None)
    if not compiler:
        raise SetupError('A C compiler is required for local recompilation.')
    return env, cmake, compiler


def verify_extraction(extracted, disc, rel_layout):
    dol = extracted / 'sys/main.dol'
    if digest(dol) != disc.dol_sha256:
        raise DiscError('Extracted executable does not match the selected disc.')
    if rel_layout:
        rel = extracted / rel_layout['path']
        if digest(rel) != rel_layout['sha256']:
            raise DiscError('Extracted game module does not match the verified revision.')


def extract_disc(iso, disc, build, runtime, log, rel_layout):
    extracted = build / f'disc{disc.number + 1}'
    if extracted.is_dir():
        verify_extraction(extracted, disc, rel_layout)
        return extracted
    build.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'{extracted.name}-', dir=build) as temp_dir:
        staging = Path(temp_dir)
        run([tool(runtime, 'dolrecomp'), 'extract', iso, staging], log, code=20)
        verify_extraction(staging, disc, rel_layout)
        staging.rename(extracted)
    return extracted


def build_disc(iso, disc, build, runtime, env, cmake, compiler, log, *, rel_layout=None):
    extracted = extract_disc(iso, disc, build, runtime, log, rel_layout)
    dol = extracted / 'sys/main.dol'
    module_build = build / 'modules' / disc.dol_sha256[:16]
    suffix = '.dll' if os.name == 'nt' else ('.dylib' if sys.platform == 'darwin' else '.so')
    module = module_build / f'g{disc.game_id}_recomp{suffix}'
    module_ready = module_build / 'link.complete'
    if module.is_file() and module_ready.is_file():
        return extracted, module
    generated_parent = build / 'generated' / disc.dol_sha256[:16]
    compiler_input = dol
    recompiler_options = ['--gamecube']
    if rel_layout:
        compiler_input = generated_parent / 'linked.dol'
        compiler_input.parent.mkdir(parents=True, exist_ok=True)
        compiler_input.write_bytes(link_rel_image(
            dol.read_bytes(), (extracted / rel_layout['path']).read_bytes(),
            load_address=int(rel_layout['load_address'], 16),
            bss_address=int(rel_layout['bss_address'], 16)))
        recompiler_options += ['--cpu', 'gekko']
    # An interrupted link can leave an output without its completion record.
    module.unlink(missing_ok=True)
    run([tool(runtime, 'dolrecomp'), *recompiler_options, compiler_input, generated_parent], log, env=env)
    generated = generated_parent / 'generated'
    shutil.copy2(compiler_input, generated / 'main.dol')
    smc = generated / 'generated_smc.txt'
    if not smc.exists():
        smc.touch()
    sdk = runtime / 'sdk'
    run([cmake, '-S', sdk / 'module-template', '-B', module_build, '-G', 'Ninja',
         '-DCMAKE_BUILD_TYPE=Release', f'-DCMAKE_C_COMPILER={compiler}',
         f'-DPython3_EXECUTABLE={sys.executable}', f'-DGAME_ID={disc.game_id}',
         f'-DGENERATED_DIR={generated}', f'-DGXRUNTIME_DIR={sdk / "GXRuntime"}',
         f'-DCHASSIS_ABI_DIR={sdk / "Source/Core/Core/PowerPC/StaticRecomp"}'], log, env=env)

    def report_compilation(line):
        match = re.match(r'^\[(\d+)/([1-9]\d*)\] (?:Building C object|Linking C shared)', line)
        if match:
            finished, total = (int(value) for value in match.groups())
            progress(0.22 + disc.number * 0.36 + 0.28 * finished / total,
                     f'Compiling native module ({finished}/{total} steps)')

    run([cmake, '--build', module_build, '-j', str(min(8, os.cpu_count() or 2))], log, env=env,
        on_line=report_compilation)
    if not module.is_file() or module.stat().st_size == 0:
        raise SetupError('The compiler did not produce the expected native module.', 22)
    module_ready.touch()
    return extracted, module


def prepare(args, runtime, data, log):
    if not args.disc1 or not args.disc2:
        raise DiscError('Both --disc1 and --disc2 are required for setup.')
    cache = data / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    iso1 = normalize_disc(args.disc1, cache, runtime, log)
    iso2 = normalize_disc(args.disc2, cache, runtime, log)
    first, second = inspect_iso(iso1), inspect_iso(iso2)
    validate_pair(first, second)
    progress(0.12, 'Validated matching Disc 1 and Disc 2 headers')
    if args.inspect:
        print(json.dumps({'disc1': first.record(), 'disc2': second.record()}, indent=2))
        return
    env, cmake, compiler = compiler_environment(runtime)
    # Hash full content, not only main.dol: two images with different assets
    # must never share a prepared extraction or a completed-build marker.
    disc_hashes = [digest(iso1), digest(iso2)]
    supported = json.loads((ROOT / 'supported-builds.json').read_text(encoding='utf-8'))['builds']
    profile = next((p for p in supported if p['game_id'] == first.game_id and p['revision'] == first.revision), None)
    if not profile:
        raise DiscError('This development build currently supports only the reference USA revision 0 pair.')
    if any(disc.dol_sha256 != profile['dol_sha256'] for disc in [first, second]):
        raise DiscError('The executable differs from the supported USA revision 0 build.')
    if disc_hashes != [entry['sha256'] for entry in profile['discs']]:
        raise DiscError('A disc differs from the supported reference dump. See supported-builds.json.')
    rel_layout = profile['rel'] if args.experimental_rel else None
    identity = {'format': BUILD_FORMAT, 'discs': disc_hashes,
                'runtime': digest(runtime / 'dependencies.lock.json'),
                'recompiler': digest(tool(runtime, 'dolrecomp')),
                'runner': digest(tool(runtime, 'moderngekko-run')),
                'host': platform.machine(), 'compiler': compiler}
    if rel_layout:
        identity['rel'] = rel_layout
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:32]
    build = cache / 'builds' / key
    completed = build / 'prepared.json'
    if completed.is_file():
        record = json.loads(completed.read_text(encoding='utf-8'))
        if record['identity'] == identity and all((data / entry[field]).is_file() for entry in record['discs'] for field in ['dol', 'module']):
            atomic_json(data / 'prepared.json', record)
            progress(1, 'Already built')
            return
    results = []
    for index, (iso, disc) in enumerate([(iso1, first), (iso2, second)]):
        progress(0.18 + index * 0.36, f'Extracting and compiling Disc {index + 1}')
        extracted, module = build_disc(iso, disc, build, runtime, env, cmake, compiler, log,
                                       rel_layout=rel_layout)
        results.append({'root': extracted.relative_to(data).as_posix(),
                        'dol': (extracted / 'sys/main.dol').relative_to(data).as_posix(),
                        'module': module.relative_to(data).as_posix(),
                        'metadata': disc.record(), 'iso_sha256': disc_hashes[index]})
    record = {'identity': identity, 'discs': results}
    atomic_json(completed, record)
    # The previously working build remains selected until both discs succeed.
    atomic_json(data / 'prepared.json', record)
    progress(1, 'Native modules built; gameplay compatibility still needs testing')


def play(args, runtime, data, log):
    prepared = data / 'prepared.json'
    if not prepared.is_file():
        raise DiscError('Setup is required. Select both discs with --prepare first.')
    record = json.loads(prepared.read_text(encoding='utf-8'))
    entry = record['discs'][args.boot_disc - 1]
    user = data / 'user'
    user.mkdir(exist_ok=True)
    config = user / 'config.ini'
    if not config.exists():
        fullscreen = os.environ.get('RECOMPLAUNCHER_MODE') == 'bigpicture'
        config.write_text('resolution=640x528\nbackend=Vulkan\nshow_fps_in_title=true\n'
                          f'fullscreen={str(fullscreen).lower()}\n', encoding='utf-8')
    command = [tool(runtime, 'moderngekko-run'), '--game', data / entry['root'],
               '--module', data / entry['module'], '--user-dir', user,
               '--title', 'Twin Snakes Recomp']
    if args.allow_interpreter:
        command.append('--allow-interpreter')
    if args.headless:
        command.append('--headless')
    if args.automation_dir:
        command += ['--automation-dir', args.automation_dir.resolve()]
    run(command, log, code=25)


def main():
    parser = argparse.ArgumentParser(description='Twin Snakes Recomp development setup and player')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--experimental-rel', action='store_true',
                        help='Compile the gameplay module along with the boot executable')
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--disc1', type=Path)
    parser.add_argument('--disc2', type=Path)
    parser.add_argument('--data', type=Path)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--boot-disc', type=int, choices=[1, 2], default=1)
    parser.add_argument('--allow-interpreter', action='store_true', help='Diagnostic fallback; not proof of native execution')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--automation-dir', type=Path)
    parser.add_argument('--gui', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.experimental_rel and not args.prepare:
        parser.error('--experimental-rel requires --prepare')
    data = (args.data or default_data()).resolve()
    runtime = (args.runtime or (ROOT / 'runtime' if (ROOT / 'runtime').is_dir() else ROOT / '.local/runtime')).resolve()
    try:
        with installation_lock(data):
            logs = data / 'logs'
            logs.mkdir(exist_ok=True)
            for old in sorted(logs.glob('session-*.log'))[:-4]:
                old.unlink()
            with (logs / f'session-{time.time_ns()}.log').open('w', encoding='utf-8') as log:
                if args.prepare or args.inspect:
                    prepare(args, runtime, data, log)
                elif args.gui and not (data / 'prepared.json').is_file():
                    if os.name != 'nt':
                        raise SetupError('Use --prepare with both disc paths on this platform.')
                    args.disc1, args.disc2 = pick_disc(1), pick_disc(2)
                    prepare(args, runtime, data, log)
                if not args.prepare and not args.inspect:
                    play(args, runtime, data, log)
        return 0
    except (DiscError, FileNotFoundError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        if args.gui and os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), 'Twin Snakes Recomp', 0x10)
        return 20
    except SetupError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        if args.gui and os.name == 'nt' and exc.code != 26:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), 'Twin Snakes Recomp', 0x10)
        return exc.code
    except (OSError, ValueError, KeyError) as exc:
        print(f'Setup error: {exc}', file=sys.stderr)
        return 21


if __name__ == '__main__':
    raise SystemExit(main())
