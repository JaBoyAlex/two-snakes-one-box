"""Compare hybrid AOT and JIT on one prepared disc with isolated runtime settings."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]


def benchmark(mode, runner, game, module, work, windowed, seconds):
    control = work / 'control'
    command_dir = control / 'commands'
    command_dir.mkdir(parents=True)
    user = work / 'user'
    user.mkdir()
    backend = 'Vulkan' if windowed else 'Null'
    (user / 'config.ini').write_text('resolution=640x528\nbackend=Vulkan\nfullscreen=false\n')
    env = dict(os.environ, MODERNGEKKO_STATICRECOMP='1' if mode == 'aot' else '0')
    env.pop('STATICRECOMP_DISPATCH_SAMPLES', None)
    env.pop('STATICRECOMP_TRACE_FILE', None)
    env.pop('STATICRECOMP_FALLBACK_RANGES', None)
    command = [str(runner), '--game', str(game), '--module', str(module),
               '--user-dir', str(user), '--automation-dir', str(control),
               '--graphics', backend, '--no-mods']
    if not windowed:
        command.append('--headless')

    with (work / 'runtime.log').open('wb') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        start = time.monotonic()
        began_sampling = None
        previous_sample = None
        samples = []
        try:
            while process.poll() is None and time.monotonic() - start < seconds + 55:
                time.sleep(1)
                try:
                    state = dict(line.split('=', 1) for line in (control / 'status.txt').read_text().splitlines() if '=' in line)
                    speed = float(state.get('speed', '0'))
                    vps = float(state.get('vps', '0'))
                    fps = float(state.get('fps', '0'))
                    frame = int(state.get('frame_count', '0'))
                except (OSError, ValueError):
                    continue
                now = time.monotonic()
                if state.get('booted') != '1' or not frame:
                    continue
                if began_sampling is None:
                    began_sampling = now
                if previous_sample is not None and now - began_sampling >= 3:
                    previous_time, previous_frame = previous_sample
                    samples.append({'seconds_since_boot': round(now - began_sampling, 2),
                                    'speed': speed,
                                    'drawn_fps': (frame - previous_frame) / (now - previous_time)})
                    if windowed:
                        samples[-1].update({'vps': vps, 'fps': fps})
                previous_sample = now, frame
                if now - began_sampling >= seconds + 3:
                    break
        finally:
            if process.poll() is None:
                command_file = control / 'stop.tmp'
                command_file.write_text('command=stop\n', encoding='ascii')
                command_file.rename(command_dir / 'stop.txt')
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=5)

    summary = {'cpu': mode, 'graphics': backend, 'exit_code': process.returncode,
               'sample_count': len(samples), 'samples': samples}
    if samples:
        metrics = ['speed', 'drawn_fps', 'vps', 'fps'] if windowed else ['speed', 'drawn_fps']
        summary.update({f'median_{key}': round(statistics.median(sample[key] for sample in samples), 3)
                        for key in metrics})
    (work / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'samples'}), flush=True)
    return process.returncode == 0 and bool(samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--runner', required=True, type=Path)
    parser.add_argument('--module', type=Path, help='Test a candidate module instead of the prepared module')
    parser.add_argument('--output', type=Path, default=ROOT / '.local/benchmarks')
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--mode', choices=['aot', 'jit', 'both'], default='both')
    parser.add_argument('--windowed', action='store_true', help='Use Vulkan and normal audio instead of headless Null output')
    args = parser.parse_args()
    if not 5 <= args.seconds <= 300:
        parser.error('--seconds must be between 5 and 300')
    data = args.data.resolve()
    prepared = json.loads((data / 'prepared.json').read_text())
    disc = prepared['discs'][0]
    module = args.module.resolve(strict=True) if args.module else data / disc['module']
    work = args.output.resolve() / str(time.time_ns())
    modes = ['jit', 'aot'] if args.mode == 'both' else [args.mode]
    outcomes = [benchmark(mode, args.runner.resolve(strict=True), data / disc['root'],
                          module, work / mode, args.windowed, args.seconds)
                for mode in modes]
    print(f'Private logs and samples: {work}')
    return 0 if all(outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
