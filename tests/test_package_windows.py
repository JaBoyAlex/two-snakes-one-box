import hashlib
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from bootstrap import prepare_windows_tools
import build_runtime
from package_windows import check_package_tree


class PackageWindowsTests(unittest.TestCase):
    def test_runtime_patch_stack_can_be_reapplied(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            patch_dir = root / 'patches'
            patch_dir.mkdir()
            target = root / 'source.txt'
            target.write_bytes(b'original\n')
            for name, before, after in [('base', 'original', 'base'),
                                        ('middle', 'base', 'middle'),
                                        ('top', 'middle', 'top')]:
                (patch_dir / name).write_bytes(
                    f'diff --git a/source.txt b/source.txt\n--- a/source.txt\n+++ b/source.txt\n'
                    f'@@ -1 +1 @@\n-{before}\n+{after}\n'.encode())

            prerequisites = {'middle': ('base',), 'top': ('middle',)}
            with (patch.dict(os.environ, {'GIT_CONFIG_COUNT': '0'}),
                  patch.object(build_runtime, 'ROOT', root),
                  patch.object(build_runtime, 'PATCH_PREREQUISITES', prerequisites)):
                build_runtime.apply_patch(root, 'middle')
                self.assertEqual(target.read_text(encoding='ascii'), 'middle\n')
                build_runtime.apply_patch(root, 'top')
                build_runtime.apply_patch(root, 'top')
                self.assertEqual(target.read_text(encoding='ascii'), 'top\n')

    def test_prepares_pinned_archive_and_license_together(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'tool.zip'
            with ZipFile(archive, 'w') as bundle:
                bundle.writestr('ninja-test/ninja.exe', 'tool content')
            license_file = root / 'license.txt'
            license_file.write_bytes(b'upstream license')
            copy = {'url': license_file.as_uri(), 'sha256': '0' * 64}
            lock = {'ninja': {'url': archive.as_uri(),
                              'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                              'root': 'ninja-test', 'copying': copy}}
            target = root / 'tools'
            with self.assertRaisesRegex(SystemExit, 'Download hash mismatch'):
                prepare_windows_tools(target, lock)
            self.assertFalse(target.exists())

            copy['sha256'] = hashlib.sha256(license_file.read_bytes()).hexdigest()
            prepare_windows_tools(target, lock)
            self.assertEqual((target / 'ninja/ninja.exe').read_bytes(), b'tool content')
            self.assertEqual((target / 'ninja/COPYING').read_bytes(), b'upstream license')

    def test_rejects_private_runtime_inputs(self):
        for relative in ('sdk/module-template/generated/translated.c', 'recompdata/prepared.json',
                         'game.GGSEA4_Recomp.DLL', 'latest.LOG', 'run.profraw'):
            with self.subTest(path=relative), TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
                with self.assertRaisesRegex(SystemExit, 'Private'):
                    check_package_tree(root, runtime=True)

    def test_checks_runtime_paths_again_in_the_package(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runtime/sdk/core').mkdir(parents=True)
            (root / 'runtime/sdk/core/cpu.c').touch()
            (root / 'tools/cmake/share/cache').mkdir(parents=True)
            check_package_tree(root)
            (root / 'runtime/USER').mkdir()
            with self.assertRaisesRegex(SystemExit, 'runtime/USER'):
                check_package_tree(root)
