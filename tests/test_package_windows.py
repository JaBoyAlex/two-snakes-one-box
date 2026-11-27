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
from package_windows import check_package_tree, copy_game_runtime


class PackageWindowsTests(unittest.TestCase):
    def test_packages_settings_for_supported_builds_and_keeps_shared_assets(self):
        keep = {'Sys/GameSettings/G.ini', 'Sys/GameSettings/GGS.ini',
                'Sys/GameSettings/GGSEA4.ini', 'Sys/GameSettings/GGSEA4r0.ini',
                'Sys/Resources/OSD_Font.ttf', 'Sys/GC/font-licenses.txt', 'Sys/wiitdb-en.txt',
                'Sys/Load/GraphicMods/Common/config.json', 'sdk/totaldb.dsy'}
        omit = {'Sys/GameSettings/GGSPA4.ini', 'Sys/GameSettings/GGSEA4r1.ini',
                'Sys/Themes/example/icon.png', 'Sys/totaldb.dsy'}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            for name in keep | omit:
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name, encoding='ascii')

            destination = root / 'package'
            copy_game_runtime(source, destination, [{'game_id': 'GGSEA4', 'revision': 0}])
            self.assertEqual({path.relative_to(destination).as_posix()
                              for path in destination.rglob('*') if path.is_file()}, keep)
            for name in keep:
                self.assertEqual((destination / name).read_text(encoding='ascii'), name)

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
                         'game.GGSEA4_Recomp.DLL', 'latest.LOG', 'run.profraw', 'dock.dtm', 'door.sav.DTM'):
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
