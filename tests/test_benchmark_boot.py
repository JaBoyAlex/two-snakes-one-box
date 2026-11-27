import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import benchmark_boot


class BenchmarkTests(unittest.TestCase):
    def test_compare_scale_runs_in_both_orders_with_the_same_backend(self):
        with TemporaryDirectory() as directory:
            work = Path(directory)
            runner = work / 'runner'
            runner.touch()
            (work / 'prepared.json').write_text(json.dumps({'discs': [{'root': 'disc', 'module': 'module'}]}))
            argv = ['benchmark_boot', '--data', directory, '--runner', str(runner), '--output', directory,
                    '--windowed', 'Vulkan', '--internal-scale', '1', '--compare-scale', '4']
            with (patch.object(sys, 'argv', argv), patch.object(benchmark_boot, 'benchmark', return_value=True) as run,
                  patch('builtins.print')):
                self.assertEqual(benchmark_boot.main(), 0)
            self.assertEqual([call.args[4].name for call in run.call_args_list],
                             ['1x-first', '4x-second', '4x-first', '1x-second'])
            self.assertEqual([call.kwargs['internal_scale'] for call in run.call_args_list], [1, 4, 4, 1])
            self.assertTrue(all(call.args[6] == 'Vulkan' and call.args[0] == 'aot' for call in run.call_args_list))

    def test_xfb_override_keeps_frame_interval_logging(self):
        for mode, texture_only in (('guest-memory', 'False'), ('texture-only', 'True')):
            with (self.subTest(mode=mode), TemporaryDirectory() as directory,
                  patch.object(benchmark_boot.subprocess, 'Popen') as launch, patch('builtins.print')):
                work = Path(directory)
                process = launch.return_value
                process.poll.return_value = 0
                process.returncode = 0
                benchmark_boot.benchmark('aot', 'runner', 'disc', 'module', work,
                                         True, 'D3D', 1, None, False,
                                         frame_times=True, xfb_copies=mode, window_position=(-1500, 660))
                graphics = (work / 'user/Config/GFX.ini').read_text()
                self.assertIn('[Settings]\nLogRenderTimeToFile = True', graphics)
                self.assertIn(f'[Hacks]\nXFBToTextureEnable = {texture_only}', graphics)
                dolphin = (work / 'user/Config/Dolphin.ini').read_text()
                self.assertIn('[DSP]\nVolume = 5\n', dolphin)
                self.assertIn('[Display]\nRenderWindowXPos = -1500\nRenderWindowYPos = 660\n', dolphin)
                summary = json.loads((work / 'summary.json').read_text())
                self.assertEqual(summary['xfb_copies_requested'], mode)

    def test_reports_ending_draw_pause_while_duplicate_presents_continue(self):
        with TemporaryDirectory() as directory:
            work = Path(directory)
            elapsed = 0.0

            def poll_status(interval):
                nonlocal elapsed
                elapsed += interval
                # Draw once after sampling begins, pause and recover, then freeze.
                frame = 3 if elapsed >= 4.25 else 2 if elapsed >= 3.5 else 1
                (work / 'control/status.txt').write_text(
                    f'booted=1\nstate=running\nspeed=1\nvps=60\nfps=30\n'
                    f'frame_count={frame}\npresent_count={int(elapsed * 60)}\n')

            with (patch.object(benchmark_boot.subprocess, 'Popen') as launch,
                  patch.object(benchmark_boot.time, 'monotonic', side_effect=lambda: elapsed),
                  patch.object(benchmark_boot.time, 'sleep', side_effect=poll_status),
                  patch('builtins.print')):
                process = launch.return_value
                process.poll.return_value = None
                process.returncode = 0
                benchmark_boot.benchmark('jit', 'runner', 'disc', 'module',
                                         work, True, 'D3D', 2, None, False)

            summary = json.loads((work / 'summary.json').read_text())
            self.assertTrue(summary['drawn_frames_advanced'])
            self.assertEqual(summary['counter_pauses'], {
                'drawn_frames': {'longest_seconds': 1.0, 'ending_seconds': 1.0},
                'presents': {'longest_seconds': 0.0, 'ending_seconds': 0.0},
            })

    def test_distinguishes_new_frames_from_duplicate_presents(self):
        for advancing, reset_clock in ((False, False), (True, False), (True, True)):
            with self.subTest(advancing=advancing, reset_clock=reset_clock), TemporaryDirectory() as directory:
                work = Path(directory)
                elapsed = 0.0

                def poll_status(interval):
                    nonlocal elapsed
                    elapsed += interval
                    frame = int(elapsed * 30) if advancing else 1
                    ticks = 5_000_000_000 + int(elapsed * 486_000_000)
                    if reset_clock and elapsed >= 4.0:
                        ticks -= 1_000_000_000
                    clock = (f'guest_ticks={ticks}\n'
                             f'throttle_clock_hz={486_000_000 if elapsed < 4.0 else 0}\n') if advancing else ''
                    (work / 'control/status.txt').write_text(
                        f'booted=1\nstate=running\nspeed=1\nvps=60\nfps=30\n'
                        f'frame_count={frame}\npresent_count={int(elapsed * 60)}\n{clock}')

                with (patch.object(benchmark_boot.subprocess, 'Popen') as launch,
                      patch.object(benchmark_boot.time, 'monotonic', side_effect=lambda: elapsed),
                      patch.object(benchmark_boot.time, 'sleep', side_effect=poll_status),
                      patch('builtins.print')):
                    process = launch.return_value
                    process.poll.return_value = None
                    process.returncode = 0
                    succeeded = benchmark_boot.benchmark('jit', 'runner', 'disc', 'module',
                                                         work, True, 'D3D', 1, None, False)

                summary = json.loads((work / 'summary.json').read_text())
                self.assertTrue(summary['presentation_advanced'])
                self.assertEqual(summary['drawn_frames_advanced'], advancing)
                self.assertEqual(summary['completed'], advancing)
                self.assertEqual(succeeded, advancing)
                self.assertEqual('median_speed' in summary, advancing)
                self.assertEqual('guest_ticks' in summary['samples'][0], advancing)
                self.assertEqual('guest_ticks_per_host_second' in summary, advancing and not reset_clock)
                if advancing:
                    expected_end = 6_065_500_000 if reset_clock else 7_065_500_000
                    self.assertEqual(summary['guest_tick_range'], {'start': 6_579_500_000, 'end': expected_end})
                    if not reset_clock:
                        self.assertEqual(summary['guest_ticks_per_host_second'], 486_000_000)
                    self.assertEqual(summary['throttle_clocks_hz'], [0, 486_000_000])
                    self.assertEqual(summary['samples'][0]['throttle_clock_hz'], 486_000_000)
                else:
                    self.assertNotIn('guest_tick_range', summary)
                    self.assertNotIn('throttle_clocks_hz', summary)

    def test_ignores_fallback_ranges_in_inherited_environment(self):
        ranges = dict.fromkeys(('STATICRECOMP_FALLBACK_RANGES',
                               'STATICRECOMP_PROFILE_FALLBACK_RANGES'), '100-200')
        with (TemporaryDirectory() as directory, patch.dict(os.environ, ranges),
              patch.object(benchmark_boot.subprocess, 'Popen') as launch, patch('builtins.print')):
            process = launch.return_value
            process.poll.return_value = 0
            process.returncode = 0
            benchmark_boot.benchmark('aot', 'runner', 'disc', 'module', Path(directory),
                                     False, 'Null', 1, None, False)
            self.assertTrue(ranges.keys().isdisjoint(launch.call_args.kwargs['env']))
            self.assertFalse((Path(directory) / 'user/Config/Dolphin.ini').exists())
