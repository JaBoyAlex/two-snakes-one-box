"""Validate GameCube disc structure before passing a dump to the recompiler."""
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import struct


class DiscError(ValueError):
    pass


@dataclass(frozen=True)
class Disc:
    game_id: str
    number: int
    revision: int
    size: int
    dol_offset: int
    dol_size: int
    dol_sha256: str

    def record(self):
        return asdict(self)


def inspect_iso(path):
    path = Path(path)
    size = path.stat().st_size
    with path.open('rb') as stream:
        header = stream.read(0x440)
        if len(header) < 0x440 or header[0x1C:0x20] != bytes.fromhex('c2339f3d'):
            raise DiscError('Not a raw GameCube disc image. RVZ/GCZ must be converted first.')
        try:
            game_id = header[:6].decode('ascii')
        except UnicodeDecodeError as exc:
            raise DiscError('Invalid GameCube disc identity.') from exc
        if game_id not in {'GGSEA4', 'GGSPA4', 'GGSJA4'}:
            raise DiscError(f'This is {game_id!r}, not a recognized Twin Snakes disc.')
        number, revision = header[6:8]
        if number not in (0, 1):
            raise DiscError('Twin Snakes requires Disc 1 and Disc 2.')
        dol_offset, fst_offset, fst_size = struct.unpack_from('>III', header, 0x420)
        if not (0x440 <= dol_offset <= size - 0x100):
            raise DiscError('Executable offset lies outside the disc image.')
        if not (0x440 <= fst_offset <= size - fst_size) or fst_size < 12:
            raise DiscError('Filesystem table is truncated or invalid.')
        stream.seek(dol_offset)
        dol_header = stream.read(0x100)
        offsets = struct.unpack_from('>18I', dol_header, 0)
        sizes = struct.unpack_from('>18I', dol_header, 0x90)
        ends = []
        for offset, section_size in zip(offsets, sizes):
            if section_size:
                if offset < 0x100 or offset + section_size > size - dol_offset:
                    raise DiscError('Executable section lies outside the disc image.')
                ends.append(offset + section_size)
        if not ends:
            raise DiscError('Disc executable has no sections.')
        dol_size = max(ends)
        stream.seek(dol_offset)
        digest = hashlib.sha256()
        remaining = dol_size
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise DiscError('Disc executable is truncated.')
            digest.update(chunk)
            remaining -= len(chunk)
    return Disc(game_id, number, revision, size, dol_offset, dol_size, digest.hexdigest())


def validate_pair(first, second):
    if first.number != 0 or second.number != 1:
        raise DiscError('Select Disc 1 in the first slot and Disc 2 in the second slot.')
    if (first.game_id, first.revision) != (second.game_id, second.revision):
        raise DiscError('Both discs must have the same region and revision.')
