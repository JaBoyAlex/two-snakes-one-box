from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_windows import check_package_tree


class PackageWindowsTests(unittest.TestCase):
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
