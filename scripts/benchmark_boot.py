"""Benchmark CPU modes and native modules with isolated runtime settings."""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time


def log_size(path):
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def summarize_intervals(path, start, end):
    if end <= start:
        return None
    with path.open('rb') as stream:
        stream.seek(start)
        lines = stream.read(end - start).splitlines()
    intervals = []
    for line in lines:
        try:
            interval = float(line)
        except ValueError:
            continue
        if math.isfinite(interval) and interval > 0:
            intervals.append(interval)
    if not intervals:
        return None
    intervals.sort()
    return {'count': len(intervals), 'median': round(statistics.median(intervals), 3),
            'p95': round(intervals[math.ceil(len(intervals) * 0.95) - 1], 3),
            'maximum': round(intervals[-1], 3)}


def benchmark(mode, runner, game, module, work, windowed, backend, seconds, load_state, dispatch_samples,
              *, dual_core=False, frame_times=False, internal_scale=1, fullscreen=False):
    control = work / 'control'
    command_dir = control / 'commands'
    command_dir.mkdir(parents=True)
    user = work / 'user'
    user.mkdir()
    (user / 'config.ini').write_text(f'resolution={640 * internal_scale}x{528 * internal_scale}\n'
                                   f'backend=Vulkan\nfullscreen={str(fullscreen).lower()}\n',
                                   encoding='ascii')
    config = user / 'Config'
    if dual_core or frame_times:
        config.mkdir()
    if dual_core:
        (config / 'Dolphin.ini').write_text('[Core]\nCPUThread = True\n', encoding='ascii')
    interval_logs = {}
    if frame_times:
        logs = user / 'Logs'
        logs.mkdir()
        (config / 'GFX.ini').write_text('[Settings]\nLogRenderTimeToFile = True\n', encoding='ascii')
        interval_logs = {'render': logs / 'render_times.txt', 'vblank': logs / 'vblank_times.txt'}
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
        interval_start = {}
        interval_end = {}
        completed = False
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
                    if not samples:
                        interval_start = {name: log_size(path) for name, path in interval_logs.items()}
                    previous_time, previous_frame = previous_sample
                    samples.append({'seconds_since_boot': round(now - began_sampling, 2),
                                    'speed': speed,
                                    'drawn_fps': (frame - previous_frame) / (now - previous_time)})
                    if windowed:
                        samples[-1].update({'vps': vps, 'fps': fps})
                previous_sample = now, frame
                if now - began_sampling >= seconds + 3:
                    interval_end = {name: log_size(path) for name, path in interval_logs.items()}
                    completed = True
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
               'completed': completed, 'forced_stop': forced_stop,
               'sample_count': len(samples), 'samples': samples,
               'internal_scale_requested': internal_scale, 'fullscreen_requested': fullscreen}
    if dual_core:
        summary['dual_core_requested'] = True
    if frame_times and completed:
        summary['frame_intervals_ms'] = {
            name: summarize_intervals(path, interval_start[name], interval_end[name])
            for name, path in interval_logs.items()
        }
    if samples:
        metrics = ['speed', 'drawn_fps', 'vps', 'fps'] if windowed else ['speed', 'drawn_fps']
        summary.update({f'median_{key}': round(statistics.median(sample[key] for sample in samples), 3)
                        for key in metrics})
        summary['minimum_speed'] = round(min(sample['speed'] for sample in samples), 3)
        summary['maximum_speed'] = round(max(sample['speed'] for sample in samples), 3)
    (work / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'samples'}), flush=True)
    return process.returncode == 0 and completed and not forced_stop and bool(samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--runner', required=True, type=Path)
    parser.add_argument('--module', type=Path, help='Test a candidate module instead of the prepared module')
    parser.add_argument('--compare-module', type=Path,
                        help='Compare a candidate against --module or the prepared module in both run orders')
    parser.add_argument('--load-state', type=Path, help='Replay a local Disc 1 save state for a scene comparison')
    parser.add_argument('--dispatch-samples', action='store_true', help='Log the busiest native dispatch sites on shutdown')
    parser.add_argument('--output', type=Path,
                        help='Directory for isolated profiles and logs (default: system temporary directory)')
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--dual-core', action='store_true', help='Test separate CPU and video threads in the isolated profile')
    parser.add_argument('--frame-times', action='store_true', help='Record render and video update intervals in windowed mode')
    parser.add_argument('--internal-scale', type=int, default=1, metavar='N',
                        help='Integer EFB render scale in the isolated profile, from 1 to 12 (default: 1)')
    parser.add_argument('--fullscreen', action='store_true', help='Start the windowed benchmark in borderless fullscreen')
    parser.add_argument('--mode', choices=['aot', 'jit', 'both'],
                        help='Default: both, or aot for --compare-module')
    display = parser.add_mutually_exclusive_group()
    backends = ['Vulkan', 'D3D', 'D3D12']
    display.add_argument('--windowed', nargs='?', const='Vulkan', choices=backends,
                         help='Use a visible window and normal audio (default backend: Vulkan)')
    display.add_argument('--offscreen', choices=backends,
                         help='Render with the selected backend without a window or audio output')
    display.add_argument('--offscreen-vulkan', dest='offscreen', action='store_const', const='Vulkan',
                         help='Alias for --offscreen Vulkan')
    args = parser.parse_args()
    if not 5 <= args.seconds <= 300:
        parser.error('--seconds must be between 5 and 300')
    if not 1 <= args.internal_scale <= 12:
        parser.error('--internal-scale must be between 1 and 12')
    if args.compare_module and args.mode not in (None, 'aot'):
        parser.error('--compare-module requires AOT mode')
    windowed = args.windowed is not None
    if args.frame_times and not windowed:
        parser.error('--frame-times requires --windowed')
    if args.fullscreen and not windowed:
        parser.error('--fullscreen requires --windowed')
    data = args.data.resolve()
    prepared = json.loads((data / 'prepared.json').read_text())
    disc = prepared['discs'][0]
    module = args.module.resolve(strict=True) if args.module else data / disc['module']
    runner = args.runner.resolve(strict=True)
    load_state = args.load_state.resolve(strict=True) if args.load_state else None
    work = (args.output.resolve() / str(time.time_ns()) if args.output else
            Path(tempfile.mkdtemp(prefix='TwinSnakesRecompBenchmark-')))
    backend = args.windowed or args.offscreen or 'Null'
    if args.compare_module:
        candidate = args.compare_module.resolve(strict=True)
        cases = [('reference-first', 'aot', module), ('candidate-second', 'aot', candidate),
                 ('candidate-first', 'aot', candidate), ('reference-second', 'aot', module)]
    else:
        modes = ['jit', 'aot'] if args.mode in (None, 'both') else [args.mode]
        cases = [(mode, mode, module) for mode in modes]
    outcomes = []
    for label, mode, selected_module in cases:
        print(f'Running {label}', flush=True)
        outcomes.append(benchmark(mode, runner, data / disc['root'], selected_module,
                                  work / label, windowed, backend, args.seconds,
                                  load_state, args.dispatch_samples, dual_core=args.dual_core,
                                  frame_times=args.frame_times, internal_scale=args.internal_scale,
                                  fullscreen=args.fullscreen))
    print(f'Private logs and samples: {work}')
    return 0 if all(outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
