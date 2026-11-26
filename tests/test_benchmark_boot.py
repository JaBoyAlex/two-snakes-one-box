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
    def test_distinguishes_new_frames_from_duplicate_presents(self):
        for advancing in (False, True):
            with self.subTest(advancing=advancing), TemporaryDirectory() as directory:
                work = Path(directory)
                elapsed = 0.0

                def poll_status(interval):
                    nonlocal elapsed
                    elapsed += interval
                    frame = int(elapsed * 30) if advancing else 1
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
                    succeeded = benchmark_boot.benchmark('jit', 'runner', 'disc', 'module',
                                                         work, True, 'D3D', 1, None, False)

                summary = json.loads((work / 'summary.json').read_text())
                self.assertTrue(summary['presentation_advanced'])
                self.assertEqual(summary['drawn_frames_advanced'], advancing)
                self.assertEqual(summary['completed'], advancing)
                self.assertEqual(succeeded, advancing)
                self.assertEqual('median_speed' in summary, advancing)

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
