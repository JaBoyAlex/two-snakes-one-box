from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from discs import DiscError
from rel_image import link_rel_image


LOAD = 0x7f008000
BSS = 0x8054a180
DOL_ENTRY = 0x80003100


def fixture():
    dol = bytearray(0x104)
    struct.pack_into('>I', dol, 0, 0x100)
    struct.pack_into('>I', dol, 0x48, DOL_ENTRY)
    struct.pack_into('>I', dol, 0x90, 4)
    struct.pack_into('>III', dol, 0xd8, 0x80004000, 0x100, DOL_ENTRY)
    dol[0x100:] = b'dol!'

    rel = bytearray(0xf8)
    struct.pack_into('>I', rel, 0, 1)
    struct.pack_into('>II', rel, 0x0c, 4, 0x4c)
    struct.pack_into('>IIIII', rel, 0x1c, 3, 16, 0xb0, 0xa0, 16)
    struct.pack_into('>I', rel, 0x44, 32)
    struct.pack_into('>8I', rel, 0x4c, 0, 0, 0x81, 16, 0, 16, 0x90, 8)
    struct.pack_into('>4I', rel, 0x80, 0x3c600000, 0x38630000, 0x48000001, 0x4e800020)
    struct.pack_into('>4I', rel, 0xa0, 1, 0xb0, 0, 0xe0)
    relocations = [
        (0, 202, 1, 0), (2, 6, 2, 4), (4, 4, 2, 4),
        (0, 202, 3, 0), (0, 1, 1, 12), (0, 203, 0, 0),
        (0, 202, 1, 0), (8, 10, 0, DOL_ENTRY), (0, 203, 0, 0),
    ]
    for index, record in enumerate(relocations):
        struct.pack_into('>HBBI', rel, 0xb0 + 8 * index, *record)
    return dol, rel


class RelImageTests(unittest.TestCase):
    def test_links_calls_and_addresses_without_loading_bss_as_file_data(self):
        dol, rel = fixture()
        linked = link_rel_image(dol, rel, load_address=LOAD, bss_address=BSS)
        self.assertEqual(linked[0x100:0x104], b'dol!')
        self.assertEqual(struct.unpack_from('>I', linked, 0xe0)[0], DOL_ENTRY)

        text_offset = struct.unpack_from('>I', linked, 4)[0]
        text_address = struct.unpack_from('>I', linked, 0x4c)[0]
        self.assertEqual(text_address, LOAD + 0x80)
        branch = 0x48000001 | ((DOL_ENTRY - text_address - 8) & 0x03fffffc)
        self.assertEqual(struct.unpack_from('>4I', linked, text_offset),
                         (0x3c608055, 0x3863a184, branch, 0x4e800020))
        data_offset = struct.unpack_from('>I', linked, 7 * 4)[0]
        self.assertEqual(struct.unpack_from('>I', linked, data_offset)[0], text_address + 12)
        self.assertEqual(len(linked), data_offset + 8)

    def test_refuses_truncated_relocations_and_unsupported_imports(self):
        dol, rel = fixture()
        with self.assertRaisesRegex(DiscError, 'Unterminated'):
            link_rel_image(dol, rel[:-1], load_address=LOAD, bss_address=BSS)
        struct.pack_into('>I', rel, 0xa0, 99)
        with self.assertRaisesRegex(DiscError, 'unsupported or invalid import'):
            link_rel_image(dol, rel, load_address=LOAD, bss_address=BSS)

    def test_refuses_a_branch_out_of_range_or_sections_in_use(self):
        dol, rel = fixture()
        with self.assertRaisesRegex(DiscError, 'branch target is out of range'):
            link_rel_image(dol, rel, load_address=0x70000000, bss_address=BSS)
        with self.assertRaisesRegex(DiscError, 'overlap'):
            link_rel_image(dol, rel, load_address=LOAD, bss_address=0x80004000)


if __name__ == '__main__':
    unittest.main()
