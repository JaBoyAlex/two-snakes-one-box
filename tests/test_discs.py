import dataclasses
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from discs import DiscError, inspect_iso, validate_pair


def fixture(number=0, game_id=b'GGSEA4', revision=0):
    data = bytearray(0x1000)
    data[:6] = game_id
    data[6:8] = bytes([number, revision])
    data[0x1C:0x20] = bytes.fromhex('c2339f3d')
    struct.pack_into('>III', data, 0x420, 0x500, 0x800, 12)
    struct.pack_into('>I', data, 0x500, 0x100)
    struct.pack_into('>I', data, 0x590, 16)
    data[0x600:0x610] = b'FAKE TEST DATA!!\0'
    return data


class DiscTests(unittest.TestCase):
    def inspect(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test disc.iso'
            path.write_bytes(data)
            return inspect_iso(path)

    def test_pair_and_executable_fingerprint(self):
        first = self.inspect(fixture())
        second = self.inspect(fixture(number=1))
        validate_pair(first, second)
        self.assertEqual(first.dol_size, 0x110)
        self.assertEqual(first.dol_sha256, second.dol_sha256)
        changed = fixture()
        changed[0x600] ^= 1
        self.assertNotEqual(first.dol_sha256, self.inspect(changed).dol_sha256)

    def test_wrong_game_and_truncated_header(self):
        for data in [fixture(game_id=b'GMS E4'), b'not a disc']:
            with self.subTest(data=data[:8]), self.assertRaises(DiscError):
                self.inspect(data)

    def test_out_of_bounds_executable_and_filesystem(self):
        for position in [0x420, 0x424, 0x590]:
            data = fixture()
            struct.pack_into('>I', data, position, 0xFFFFFFFF)
            with self.subTest(position=position), self.assertRaises(DiscError):
                self.inspect(data)

    def test_rejects_wrong_order_region_and_revision(self):
        first = self.inspect(fixture())
        second = self.inspect(fixture(number=1))
        for pair in [(second, first), (first, first),
                     (first, dataclasses.replace(second, game_id='GGSPA4')),
                     (first, dataclasses.replace(second, revision=1))]:
            with self.subTest(pair=pair), self.assertRaises(DiscError):
                validate_pair(*pair)


if __name__ == '__main__':
    unittest.main()
