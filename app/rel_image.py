"""Link a revision-verified GameCube REL at its known guest addresses."""
from dataclasses import dataclass
import struct

from discs import DiscError


R_PPC_NONE = 0
R_PPC_ADDR32 = 1
R_PPC_ADDR16_LO = 4
R_PPC_ADDR16_HA = 6
R_PPC_REL24 = 10
R_DOLPHIN_NOP = 201
R_DOLPHIN_SECTION = 202
R_DOLPHIN_END = 203


@dataclass
class RelSection:
    address: int
    size: int
    executable: bool
    data: bytearray | None


def read_sections(rel, load_address, bss_address):
    if len(rel) < 0x4c or struct.unpack_from('>I', rel, 0x1c)[0] != 3:
        raise DiscError('The game module does not have a supported REL header.')
    count, table = struct.unpack_from('>II', rel, 0x0c)
    alignment = struct.unpack_from('>I', rel, 0x44)[0]
    if (count == 0 or table < 0x4c or table + count * 8 > len(rel) or
            not alignment or alignment & (alignment - 1) or bss_address % alignment):
        raise DiscError('Invalid game module section table or BSS alignment.')

    sections = []
    for offset_field, size in struct.iter_unpack('>II', rel[table:table + count * 8]):
        offset = offset_field & ~1
        executable = bool(offset_field & 1)
        if size == 0:
            sections.append(RelSection(0, 0, False, None))
        elif offset == 0 and not executable:
            sections.append(RelSection(bss_address, size, False, None))
            bss_address = (bss_address + size + alignment - 1) & -alignment
        else:
            if (offset < table + count * 8 or offset + size > len(rel) or
                    (executable and (offset % 4 or size % 4))):
                raise DiscError('Invalid file-backed game module section.')
            sections.append(RelSection(load_address + offset, size, executable,
                                       bytearray(rel[offset:offset + size])))
    if any(section.address + section.size > 0x100000000 for section in sections):
        raise DiscError('A game module section exceeds guest address space.')
    return sections


def relocate_word(section, offset, form, target):
    data = section.data
    if form not in (R_PPC_ADDR32, R_PPC_ADDR16_LO, R_PPC_ADDR16_HA, R_PPC_REL24):
        raise DiscError(f'Unsupported game module relocation type {form}.')
    size = 2 if form in (R_PPC_ADDR16_LO, R_PPC_ADDR16_HA) else 4
    if data is None or offset + size > len(data) or offset % size:
        raise DiscError('Game module relocation lies outside an aligned file-backed section.')

    if form == R_PPC_ADDR32:
        struct.pack_into('>I', data, offset, target)
    elif form == R_PPC_ADDR16_LO:
        struct.pack_into('>H', data, offset, target & 0xffff)
    elif form == R_PPC_ADDR16_HA:
        struct.pack_into('>H', data, offset, ((target + 0x8000) >> 16) & 0xffff)
    else:
        displacement = target - (section.address + offset)
        if displacement % 4 or not -0x02000000 <= displacement <= 0x01fffffc:
            raise DiscError('A game module branch target is out of range.')
        opcode = struct.unpack_from('>I', data, offset)[0]
        struct.pack_into('>I', data, offset, (opcode & 0xfc000003) | (displacement & 0x03fffffc))


def apply_relocations(rel, sections):
    module_id = struct.unpack_from('>I', rel)[0]
    reloc_start, imports, import_size = struct.unpack_from('>III', rel, 0x24)
    if (reloc_start < 0x4c or imports < 0x4c or import_size % 8 or
            imports + import_size > len(rel)):
        raise DiscError('Invalid game module import or relocation table.')

    for imported, cursor in struct.iter_unpack('>II', rel[imports:imports + import_size]):
        if imported not in (0, module_id) or not reloc_start <= cursor <= len(rel) - 8:
            raise DiscError('The game module has an unsupported or invalid import.')
        section = None
        offset = 0
        while cursor <= len(rel) - 8:
            delta, form, index, addend = struct.unpack_from('>HBBI', rel, cursor)
            cursor += 8
            if form == R_DOLPHIN_END:
                break
            if form == R_DOLPHIN_SECTION:
                if index >= len(sections):
                    raise DiscError('Invalid section in the game module relocation stream.')
                section, offset = sections[index], 0
                continue
            offset += delta
            if form in (R_PPC_NONE, R_DOLPHIN_NOP):
                continue
            if section is None:
                raise DiscError('Game module relocation has no section.')
            target = addend
            if imported:
                if (index >= len(sections) or sections[index].size == 0 or
                        addend > sections[index].size):
                    raise DiscError('Invalid game module relocation target.')
                target += sections[index].address
                if target > 0xffffffff:
                    raise DiscError('A game module relocation exceeds guest address space.')
            relocate_word(section, offset, form, target)
        else:
            raise DiscError('Unterminated game module relocation stream.')


def append_rel_sections(dol, sections):
    if len(dol) < 0x100:
        raise DiscError('The original DOL header is truncated.')
    result = bytearray(dol)
    starts = struct.unpack_from('>18I', dol, 0x48)
    sizes = list(struct.unpack_from('>18I', dol, 0x90))
    occupied = [(address, address + size) for address, size in zip(starts, sizes) if size]
    bss_start, bss_size = struct.unpack_from('>II', dol, 0xd8)
    if bss_size:
        occupied.append((bss_start, bss_start + bss_size))

    for section in sections:
        if not section.size:
            continue
        end = section.address + section.size
        if any(section.address < right and left < end for left, right in occupied):
            raise DiscError('Game module sections overlap another guest address range.')
        occupied.append((section.address, end))
        if section.data is None:
            continue
        slots = range(7) if section.executable else range(7, 18)
        slot = next((index for index in slots if sizes[index] == 0), None)
        if slot is None:
            raise DiscError('There are insufficient DOL section slots for the game module.')
        result.extend(bytes(-len(result) % 32))
        struct.pack_into('>I', result, 4 * slot, len(result))
        struct.pack_into('>I', result, 0x48 + 4 * slot, section.address)
        struct.pack_into('>I', result, 0x90 + 4 * slot, section.size)
        sizes[slot] = section.size
        result.extend(section.data)
    return result


def link_rel_image(dol, rel, *, load_address, bss_address):
    sections = read_sections(rel, load_address, bss_address)
    apply_relocations(rel, sections)
    return append_rel_sections(dol, sections)
