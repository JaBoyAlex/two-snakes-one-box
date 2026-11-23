"""Compare hybrid AOT and JIT on one prepared disc with isolated runtime settings."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time


def benchmark(mode, runner, game, module, work, windowed, backend, seconds, load_state, dispatch_samples):
    control = work / 'control'
    command_dir = control / 'commands'
    command_dir.mkdir(parents=True)
    user = work / 'user'
    user.mkdir()
    (user / 'config.ini').write_text('resolution=640x528\nbackend=Vulkan\nfullscreen=false\n')
    env = dict(os.environ, MODERNGEKKO_STATICRECOMP='1' if mode == 'aot' else '0')
    env.pop('STATICRECOMP_DISPATCH_SAMPLES', None)
    env.pop('STATICRECOMP_TRACE_FILE', None)
    env.pop('STATICRECOMP_FALLBACK_RANGES', None)
    if dispatch_samples and mode == 'aot':
        env['STATICRECOMP_DISPATCH_SAMPLES'] = '1'
    command = [str(runner), '--game', str(game), '--module', str(module),
               '--user-dir', str(user), '--automation-dir', str(control),
               '--graphics', backend, '--no-mods']
    if not windowed:
        command.append('--headless')
    if load_state:
        command += ['--load-state', str(load_state)]

    with (work / 'runtime.log').open('wb') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        start = time.monotonic()
        began_sampling = None
        previous_sample = None
        samples = []
        forced_stop = False
        try:
            while process.poll() is None and time.monotonic() - start < seconds + 90:
                time.sleep(0.25)
                try:
                    state = dict(line.split('=', 1) for line in (control / 'status.txt').read_text().splitlines() if '=' in line)
                    speed = float(state['speed'])
                    frame = int(state['frame_count'])
                    if windowed:
                        vps = float(state['vps'])
                        fps = float(state['fps'])
                except (OSError, ValueError, KeyError):
                    continue
                now = time.monotonic()
                if state.get('booted') != '1' or state.get('state') != 'running' or not frame:
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
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    forced_stop = True
                    process.terminate()
                    process.wait(timeout=5)

    summary = {'cpu': mode, 'graphics': backend, 'headless': not windowed, 'exit_code': process.returncode,
               'forced_stop': forced_stop,
               'sample_count': len(samples), 'samples': samples}
    if samples:
        metrics = ['speed', 'drawn_fps', 'vps', 'fps'] if windowed else ['speed', 'drawn_fps']
        summary.update({f'median_{key}': round(statistics.median(sample[key] for sample in samples), 3)
                        for key in metrics})
        summary['minimum_speed'] = round(min(sample['speed'] for sample in samples), 3)
        summary['maximum_speed'] = round(max(sample['speed'] for sample in samples), 3)
    (work / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'samples'}), flush=True)
    return process.returncode == 0 and bool(samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--runner', required=True, type=Path)
    parser.add_argument('--module', type=Path, help='Test a candidate module instead of the prepared module')
    parser.add_argument('--load-state', type=Path, help='Replay a local Disc 1 save state for a scene comparison')
    parser.add_argument('--dispatch-samples', action='store_true', help='Log the busiest native dispatch sites on shutdown')
    parser.add_argument('--output', type=Path,
                        help='Directory for isolated profiles and logs (default: system temporary directory)')
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--mode', choices=['aot', 'jit', 'both'], default='both')
    display = parser.add_mutually_exclusive_group()
    display.add_argument('--windowed', action='store_true', help='Use Vulkan with a visible window and normal audio')
    display.add_argument('--offscreen-vulkan', action='store_true', help='Render with Vulkan without a window or audio output')
    args = parser.parse_args()
    if not 5 <= args.seconds <= 300:
        parser.error('--seconds must be between 5 and 300')
    data = args.data.resolve()
    prepared = json.loads((data / 'prepared.json').read_text())
    disc = prepared['discs'][0]
    module = args.module.resolve(strict=True) if args.module else data / disc['module']
    load_state = args.load_state.resolve(strict=True) if args.load_state else None
    work = (args.output.resolve() / str(time.time_ns()) if args.output else
            Path(tempfile.mkdtemp(prefix='TwinSnakesRecompBenchmark-')))
    modes = ['jit', 'aot'] if args.mode == 'both' else [args.mode]
    backend = 'Vulkan' if args.windowed or args.offscreen_vulkan else 'Null'
    outcomes = [benchmark(mode, args.runner.resolve(strict=True), data / disc['root'],
                          module, work / mode, args.windowed, backend, args.seconds, load_state,
                          args.dispatch_samples)
                for mode in modes]
    print(f'Private logs and samples: {work}')
    return 0 if all(outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
