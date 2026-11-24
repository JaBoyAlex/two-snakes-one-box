import hashlib
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from discs import DiscError
import twin_snakes


class PrepareTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.build = self.root / 'build'
        self.disc = SimpleNamespace(number=0, game_id='GGSEA4',
                                    dol_sha256=hashlib.sha256(b'test DOL').hexdigest())
        tool_patch = patch.object(twin_snakes, 'tool', side_effect=lambda _, name: self.root / name)
        tool_patch.start()
        self.addCleanup(tool_patch.stop)

    @staticmethod
    def write_extraction(folder):
        (folder / 'sys').mkdir(parents=True)
        (folder / 'sys/main.dol').write_bytes(b'test DOL')

    def test_extract_retry_does_not_reuse_an_incomplete_folder(self):
        def interrupted(command, *_args, **_kwargs):
            self.write_extraction(command[-1])
            raise twin_snakes.SetupError('Interrupted extraction', 20)

        with patch.object(twin_snakes, 'run', side_effect=interrupted):
            with self.assertRaises(twin_snakes.SetupError):
                twin_snakes.extract_disc(None, self.disc, self.build, self.root, None, None)
        self.assertEqual(list(self.build.iterdir()), [])

        def complete(command, *_args, **_kwargs):
            self.write_extraction(command[-1])
            (command[-1] / 'asset.dat').touch()

        with patch.object(twin_snakes, 'run', side_effect=complete) as run:
            extracted = twin_snakes.extract_disc(None, self.disc, self.build, self.root, None, None)
            self.assertEqual(extracted, self.build / 'disc1')
            self.assertTrue((extracted / 'asset.dat').is_file())
            self.assertEqual(twin_snakes.extract_disc(None, self.disc, self.build, self.root, None, None),
                             extracted)
            run.assert_called_once()

    def test_rejects_wrong_rel_before_publishing_extraction(self):
        rel_layout = {'path': 'game.rel', 'sha256': hashlib.sha256(b'expected bytes').hexdigest()}

        def extract_wrong_rel(command, *_args, **_kwargs):
            self.write_extraction(command[-1])
            (command[-1] / rel_layout['path']).write_bytes(b'wrong bytes')

        with patch.object(twin_snakes, 'run', side_effect=extract_wrong_rel):
            with self.assertRaisesRegex(DiscError, 'does not match the verified revision'):
                twin_snakes.extract_disc(None, self.disc, self.build, self.root, None, rel_layout)
        self.assertFalse((self.build / 'disc1').exists())

    def test_repair_replaces_corrupt_extraction_after_verifying_new_copy(self):
        extracted = self.build / 'disc1'
        self.write_extraction(extracted)
        dol = extracted / 'sys/main.dol'
        dol.write_bytes(b'damaged DOL')

        def extract_again(command, *_args, **_kwargs):
            self.assertEqual(dol.read_bytes(), b'damaged DOL')
            self.write_extraction(command[-1])

        def failed_repair(command, *_args, **_kwargs):
            (command[-1] / 'sys').mkdir()

        with patch.object(twin_snakes, 'run', side_effect=failed_repair):
            with self.assertRaisesRegex(DiscError, 'Extracted executable does not match'):
                twin_snakes.extract_disc(None, self.disc, self.build, self.root, None, None)
        self.assertEqual(dol.read_bytes(), b'damaged DOL')

        with patch.object(twin_snakes, 'run', side_effect=extract_again) as run:
            self.assertEqual(twin_snakes.extract_disc(None, self.disc, self.build, self.root, None, None),
                             extracted)
            run.assert_called_once()
        self.assertEqual(dol.read_bytes(), b'test DOL')
        self.assertEqual(list(self.build.iterdir()), [extracted])

    def test_link_retry_does_not_reuse_partial_native_output(self):
        self.write_extraction(self.build / 'disc1')
        attempts = 0

        def compile_module(command, *_args, **_kwargs):
            nonlocal attempts
            if command[1] == '--gamecube':
                (command[-1] / 'generated').mkdir(parents=True, exist_ok=True)
            elif command[1] == '--build':
                attempts += 1
                directory = command[2]
                suffix = '.dll' if sys.platform == 'win32' else ('.dylib' if sys.platform == 'darwin' else '.so')
                module = directory / ('gGGSEA4_recomp' + suffix)
                self.assertFalse(module.is_file())
                self.assertFalse((directory / 'link.complete').exists())
                directory.mkdir(parents=True, exist_ok=True)
                module.write_bytes(b'partial output' if attempts == 1 else b'linked output')
                if attempts == 1:
                    raise twin_snakes.SetupError('Interrupted link', 22)

        args = (None, self.disc, self.build, self.root, {}, 'cmake', 'cc', None)
        with patch.object(twin_snakes, 'run', side_effect=compile_module):
            with self.assertRaises(twin_snakes.SetupError):
                twin_snakes.build_disc(*args)
            _, module = twin_snakes.build_disc(*args)
            self.assertEqual(module.read_bytes(), b'linked output')
            self.assertEqual(twin_snakes.build_disc(*args)[1], module)
        self.assertEqual(attempts, 2)

    def test_rebuild_replaces_empty_module_with_stale_completion_record(self):
        self.write_extraction(self.build / 'disc1')
        directory = self.build / 'modules' / self.disc.dol_sha256[:16]
        directory.mkdir(parents=True)
        suffix = '.dll' if sys.platform == 'win32' else ('.dylib' if sys.platform == 'darwin' else '.so')
        module = directory / ('gGGSEA4_recomp' + suffix)
        marker = directory / 'link.complete'
        module.touch()
        marker.touch()

        def compile_module(command, *_args, **_kwargs):
            if command[1] == '--gamecube':
                (command[-1] / 'generated').mkdir(parents=True)
            elif command[1] == '--build':
                self.assertFalse(marker.exists())
                module.write_bytes(b'linked output')

        with patch.object(twin_snakes, 'run', side_effect=compile_module):
            _, result = twin_snakes.build_disc(None, self.disc, self.build, self.root, {}, 'cmake', 'cc', None)
        self.assertEqual(result.read_bytes(), b'linked output')
        self.assertTrue(marker.is_file())

    def test_repair_rebuilds_a_corrupted_nonempty_module(self):
        self.write_extraction(self.build / 'disc1')

        def compile_module(command, *_args, **_kwargs):
            if command[1] == '--gamecube':
                (command[-1] / 'generated').mkdir(parents=True, exist_ok=True)
            elif command[1] == '--build':
                suffix = '.dll' if sys.platform == 'win32' else ('.dylib' if sys.platform == 'darwin' else '.so')
                command[2].mkdir(parents=True, exist_ok=True)
                (command[2] / ('gGGSEA4_recomp' + suffix)).write_bytes(b'linked output')

        args = (None, self.disc, self.build, self.root, {}, 'cmake', 'cc', None)
        with patch.object(twin_snakes, 'run', side_effect=compile_module):
            _, module = twin_snakes.build_disc(*args)
            module.write_bytes(b'broken bytes!')
            self.assertEqual(len(module.read_bytes()), len(b'linked output'))
            twin_snakes.build_disc(*args)
        self.assertEqual(module.read_bytes(), b'linked output')

    def test_recomplauncher_setup_writes_utf8_on_both_pipes(self):
        filename = 'Disc \u00e9 \u6e2c\u8a66.rvz'

        def prepare(*_args):
            twin_snakes.progress(0.04, f'Checking {filename}')
            raise twin_snakes.SetupError(f'Cannot read {filename}', 22)

        with (
            io.TextIOWrapper(io.BytesIO(), encoding='cp1252') as stdout,
            io.TextIOWrapper(io.BytesIO(), encoding='cp1252') as stderr,
            patch('sys.stdout', stdout),
            patch('sys.stderr', stderr),
            patch.dict('os.environ', {'RECOMPLAUNCHER': '1'}),
            patch('sys.argv', ['TwinSnakes.exe', '--prepare', '--data', str(self.root)]),
            patch.object(twin_snakes, 'prepare', side_effect=prepare),
        ):
            self.assertEqual(twin_snakes.main(), 22)
            stdout.flush()
            stderr.flush()
            self.assertIn(f'progress 0.040 Checking {filename}', stdout.buffer.getvalue().decode('utf-8'))
            self.assertIn(f'Error: Cannot read {filename}', stderr.buffer.getvalue().decode('utf-8'))

    def test_visible_play_rejects_a_second_install_and_releases_the_lock(self):
        first = self.root / 'first'
        second = self.root / 'second'
        entry = {'root': 'disc1', 'module': 'disc1.dll'}
        for data in (first, second):
            twin_snakes.atomic_json(data / 'prepared.json', {'discs': [entry]})
        args = SimpleNamespace(boot_disc=1, allow_interpreter=False, headless=False,
                               automation_dir=None)

        def try_second_launch(*_args, **_kwargs):
            with self.assertRaisesRegex(twin_snakes.SetupError, 'already running') as busy:
                twin_snakes.play(args, self.root, second, None)
            self.assertEqual(busy.exception.code, 24)

        with patch.object(twin_snakes, 'user_data_directory', return_value=self.root / 'profile'):
            with patch.object(twin_snakes, 'run', side_effect=try_second_launch) as run:
                twin_snakes.play(args, self.root, first, None)
                run.assert_called_once()
            with patch.object(twin_snakes, 'run') as run:
                twin_snakes.play(args, self.root, second, None)
                run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
