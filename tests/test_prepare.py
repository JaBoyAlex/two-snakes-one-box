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

    def test_setup_reuses_matching_disc_data_across_runner_builds(self):
        previous = self.root / 'cache' / 'builds' / 'old'
        first = previous / 'disc1'
        self.write_extraction(first)
        current = self.root / 'cache' / 'builds' / 'new'
        record = {
            'identity': {'format': twin_snakes.BUILD_FORMAT, 'recompiler': 'same',
                         'discs': ['first iso', 'second iso'], 'runner': 'old'},
            'discs': [
                {'iso_sha256': 'first iso', 'root': 'cache/builds/old/disc1'},
                {'iso_sha256': 'second iso', 'root': '../outside/disc2'},
            ],
        }
        identity = {**record['identity'], 'runner': 'new'}
        roots = twin_snakes.reusable_disc_roots(self.root.resolve(), record, identity)
        self.assertEqual(roots, {0: first.resolve()})
        self.assertEqual(twin_snakes.reusable_disc_roots(
            self.root, record, {**identity, 'recompiler': 'new'}), {})
        self.assertEqual(twin_snakes.reusable_disc_roots(
            self.root, record, {**identity, 'discs': ['different iso', 'second iso']}), {})

        with patch.object(twin_snakes, 'run') as run:
            reused = twin_snakes.extract_disc(None, self.disc, current, self.root, None, None,
                                              cached_extraction=roots[0])
            self.assertEqual(reused, first.resolve())
            run.assert_not_called()
        self.assertFalse(current.exists())

        (first / 'sys/main.dol').write_bytes(b'damaged previous extraction')
        with patch.object(twin_snakes, 'run', side_effect=lambda command, *_args, **_kw:
                          self.write_extraction(command[-1])) as run:
            repaired = twin_snakes.extract_disc(None, self.disc, current, self.root, None, None,
                                                cached_extraction=roots[0])
            run.assert_called_once()
        self.assertEqual(repaired, current / 'disc1')
        self.assertEqual((repaired / 'sys/main.dol').read_bytes(), b'test DOL')

    def test_link_retry_does_not_reuse_partial_native_output(self):
        extracted = self.build / 'disc1'
        self.write_extraction(extracted)
        rel_bytes = b'test REL'
        rel_layout = {'path': 'game.rel', 'sha256': hashlib.sha256(rel_bytes).hexdigest()}
        (extracted / rel_layout['path']).write_bytes(rel_bytes)
        attempts = 0

        def compile_module(command, *_args, **_kwargs):
            nonlocal attempts
            if command[1] == '--gamecube':
                self.assertEqual(command[2], extracted / 'sys/main.dol')
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
                twin_snakes.build_disc(*args, rel_layout=rel_layout)
            _, module = twin_snakes.build_disc(*args, rel_layout=rel_layout)
            self.assertEqual(module.read_bytes(), b'linked output')
            self.assertEqual(twin_snakes.build_disc(*args, rel_layout=rel_layout)[1], module)
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

    def test_play_uses_opted_in_ranges_only_for_the_verified_boot_module(self):
        self.write_extraction(self.root / 'disc1')
        (self.root / 'disc1.dll').write_bytes(b'linked output')
        (self.root / 'link.complete').touch()
        entry = {'root': 'disc1', 'dol': 'disc1/sys/main.dol', 'module': 'disc1.dll',
                 'metadata': {'game_id': 'GGSEA4', 'revision': 0, 'dol_sha256': self.disc.dol_sha256}}
        key = 'STATICRECOMP_PROFILE_FALLBACK_RANGES'
        for identity, verified_hash, interpreter, vector, cache, expected in (
            ({}, self.disc.dol_sha256, False, False, False, None),
            ({}, self.disc.dol_sha256, False, True, False, '80000010-80000018'),
            ({}, self.disc.dol_sha256, False, False, True, '80000000-80000008'),
            ({}, self.disc.dol_sha256, False, True, True, '80000010-80000018,80000000-80000008'),
            ({'rel': {}}, self.disc.dol_sha256, False, True, True, None),
            ({}, 'different', False, True, True, None),
            ({}, self.disc.dol_sha256, True, True, True, None),
        ):
            with self.subTest(identity=identity, checksum=verified_hash, interpreter=interpreter,
                              vector=vector, cache=cache):
                twin_snakes.atomic_json(self.root / 'prepared.json',
                                        {'identity': identity, 'discs': [entry]})
                profile = {'dol_sha256': verified_hash, 'rel': None,
                           'jit_vector_math_ranges': ['80000010-80000018'],
                           'jit_cache_loop_ranges': ['80000000-80000008']}
                args = SimpleNamespace(boot_disc=1, allow_interpreter=interpreter,
                                       experimental_cache_loops=cache, experimental_vector_routing=vector,
                                       headless=True, automation_dir=None)
                with (patch.dict('os.environ', {key: 'stale'}),
                      patch.object(twin_snakes, 'supported_profile', return_value=profile),
                      patch.object(twin_snakes, 'run') as run):
                    twin_snakes.play(args, self.root, self.root, None)
                self.assertEqual(run.call_args.kwargs['env'].get(key), expected)

    def test_visible_play_rejects_a_second_install_and_releases_the_lock(self):
        first = self.root / 'first'
        second = self.root / 'second'
        entry = {'root': 'disc1', 'dol': 'disc1/sys/main.dol', 'module': 'disc1.dll',
                 'metadata': {'dol_sha256': self.disc.dol_sha256}}
        for data in (first, second):
            self.write_extraction(data / 'disc1')
            (data / entry['module']).write_bytes(b'linked output')
            (data / 'link.complete').touch()
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

    def test_play_offers_setup_again_after_cache_damage(self):
        rel_bytes = b'test REL'
        rel_layout = {'path': 'game.rel', 'sha256': hashlib.sha256(rel_bytes).hexdigest()}
        metadata = {'dol_sha256': self.disc.dol_sha256, 'game_id': 'GGSEA4', 'revision': 0}
        entries = []
        for number in (1, 2):
            extracted = self.root / f'disc{number}'
            self.write_extraction(extracted)
            (extracted / rel_layout['path']).write_bytes(rel_bytes)
            entries.append({'root': f'disc{number}', 'dol': f'disc{number}/sys/main.dol',
                            'module': 'shared.dll', 'metadata': metadata})
        module = self.root / 'shared.dll'
        good_module = b'linked output'
        module.write_bytes(good_module)
        twin_snakes.atomic_json(self.root / 'link.complete', twin_snakes.digest(module))
        active = self.root / 'prepared.json'
        args = SimpleNamespace(boot_disc=1, allow_interpreter=False, headless=True, automation_dir=None)
        for damaged, original, modified in [(self.root / entries[1]['dol'], b'test DOL', b'bad! DOL'),
                                            (self.root / 'disc1/game.rel', rel_bytes, b'bad! REL'),
                                            (self.root / 'disc2/game.rel', rel_bytes, b'bad! REL'),
                                            (module, good_module, b'broken bytes!')]:
            with self.subTest(file=damaged.relative_to(self.root)):
                twin_snakes.atomic_json(active, {'discs': entries})
                original_record = active.read_bytes()
                damaged.write_bytes(modified)
                with (patch.object(twin_snakes, 'run') as run,
                      patch.object(twin_snakes, 'supported_profile', return_value={'rel': rel_layout})):
                    with self.assertRaisesRegex(twin_snakes.SetupError, 'Run setup again') as error:
                        twin_snakes.play(args, self.root, self.root, None)
                    self.assertEqual(error.exception.code, 27)
                    run.assert_not_called()
                self.assertFalse(active.exists())
                self.assertEqual((self.root / 'prepared.needs-repair.json').read_bytes(), original_record)
                damaged.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
