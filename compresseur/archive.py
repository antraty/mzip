"""Format d'archive .mz : plusieurs fichiers / dossiers dans un seul fichier.

    MAGIC "MZP1"
    pour chaque fichier :
        [longueur du nom : 2][nom UTF-8][taille : 8][date de modif : 8 (double)]
        des blocs : [méthode : 1][taille brute : 4][taille compressée : 4][données]
        [CRC32 du fichier : 4]
    [0 : 2]   <- fin de l'archive

Chaque fichier est découpé en blocs de 256 Ko compressés indépendamment :
la mémoire reste bornée, et chaque bloc peut utiliser la méthode qui lui
convient le mieux (texte, image, audio, déjà compressé...).
"""
import os
import struct
import zlib

from .methods import BY_ID, compress_block, decompress_block

MAGIC = b"MZP1"
BLOCK = 256 * 1024


class ArchiveError(Exception):
    pass


def _iter_inputs(paths, skip):
    """Liste (chemin réel, nom dans l'archive) pour les fichiers et dossiers donnés."""
    for p in paths:
        p = os.path.abspath(p)
        base = os.path.dirname(p)
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs.sort()
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    if os.path.abspath(full) != skip:
                        yield full, os.path.relpath(full, base).replace(os.sep, "/")
        elif os.path.isfile(p):
            yield p, os.path.basename(p)
        else:
            raise FileNotFoundError(p)


def create(archive_path, inputs, method="auto", callback=None):
    """Crée l'archive. Renvoie [(nom, taille, taille compressée)]."""
    skip = os.path.abspath(archive_path)
    stats = []
    with open(archive_path, "wb") as out:
        out.write(MAGIC)
        for full, name in _iter_inputs(inputs, skip):
            size, mtime = os.path.getsize(full), os.path.getmtime(full)
            raw_name = name.encode("utf-8")
            out.write(struct.pack(">H", len(raw_name)) + raw_name + struct.pack(">Qd", size, mtime))
            crc = csize = done = 0
            with open(full, "rb") as f:
                while done < size:
                    chunk = f.read(min(BLOCK, size - done))
                    if not chunk:
                        raise ArchiveError("le fichier a changé pendant la lecture : " + name)
                    mid, comp = compress_block(chunk, method)
                    out.write(struct.pack(">BII", mid, len(chunk), len(comp)) + comp)
                    crc = zlib.crc32(chunk, crc)
                    csize += 9 + len(comp)
                    done += len(chunk)
            out.write(struct.pack(">I", crc & 0xFFFFFFFF))
            stats.append((name, size, csize))
            if callback:
                callback(name, size, csize)
        out.write(struct.pack(">H", 0))
    return stats


def _entries(f):
    if f.read(4) != MAGIC:
        raise ArchiveError("ce n'est pas une archive .mz")
    while True:
        raw = f.read(2)
        if len(raw) < 2:
            raise ArchiveError("archive tronquée")
        (nlen,) = struct.unpack(">H", raw)
        if nlen == 0:
            return
        name = f.read(nlen).decode("utf-8")
        head = f.read(16)
        if len(head) < 16:
            raise ArchiveError("archive tronquée")
        size, mtime = struct.unpack(">Qd", head)
        yield name, size, mtime


def _blocks(f, size, read=True):
    """Blocs d'une entrée : (méthode, taille brute, taille compressée, données ou None)."""
    done = 0
    while done < size:
        head = f.read(9)
        if len(head) < 9:
            raise ArchiveError("archive tronquée")
        mid, raw, clen = struct.unpack(">BII", head)
        if read:
            comp = f.read(clen)
            if len(comp) < clen:
                raise ArchiveError("archive tronquée")
        else:
            f.seek(clen, os.SEEK_CUR)
            comp = None
        yield mid, raw, clen, comp
        done += raw


def _read_crc(f):
    raw = f.read(4)
    if len(raw) < 4:
        raise ArchiveError("archive tronquée")
    return struct.unpack(">I", raw)[0]


def _safe_path(outdir, name):
    target = os.path.abspath(os.path.join(outdir, *name.split("/")))
    root = os.path.abspath(outdir)
    if os.path.commonpath([root, target]) != root or target == root:
        raise ArchiveError("nom dangereux dans l'archive : " + name)
    return target


def _decode_entry(f, name, size, sink):
    crc = 0
    try:
        for mid, raw, _, comp in _blocks(f, size):
            chunk = decompress_block(mid, comp, raw)
            crc = zlib.crc32(chunk, crc)
            if sink:
                sink(chunk)
    except (ValueError, struct.error, IndexError) as e:
        raise ArchiveError("données corrompues dans %s (%s)" % (name, e))
    if _read_crc(f) != crc & 0xFFFFFFFF:
        raise ArchiveError("CRC invalide pour " + name)


def extract(archive_path, outdir=".", callback=None):
    """Extrait tous les fichiers dans `outdir`. Renvoie la liste des chemins créés."""
    created = []
    with open(archive_path, "rb") as f:
        for name, size, mtime in _entries(f):
            target = _safe_path(outdir, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as g:
                _decode_entry(f, name, size, g.write)
            os.utime(target, (mtime, mtime))
            created.append(target)
            if callback:
                callback(name, size)
    return created


def test(archive_path):
    """Vérifie l'archive (décompresse tout et contrôle les CRC). Renvoie le nombre de fichiers."""
    count = 0
    with open(archive_path, "rb") as f:
        for name, size, _ in _entries(f):
            _decode_entry(f, name, size, None)
            count += 1
    return count


def list_entries(archive_path):
    """[(nom, taille, taille compressée, méthodes utilisées)] sans rien décompresser."""
    result = []
    with open(archive_path, "rb") as f:
        for name, size, _ in _entries(f):
            csize, used = 0, set()
            for mid, _, clen, _ in _blocks(f, size, read=False):
                csize += 9 + clen
                used.add(BY_ID[mid][0] if mid in BY_ID else "?")
            _read_crc(f)
            result.append((name, size, csize, sorted(used)))
    return result
