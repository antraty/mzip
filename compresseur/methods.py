"""Assemblage des algorithmes en "méthodes" de compression.

    deflate : LZ77 (fenêtre 32 Ko)  + Huffman
    bzip2   : BWT + MTF + RLE       + Huffman
    lzma    : LZ77 (fenêtre 64 Ko)  + codage arithmétique
    + chaque algorithme seul (rle, huffman, arithmetic, lz77, lz78, lzw)

Toutes les méthodes ont la même forme : octets -> octets.
"""
import math
import struct
from collections import Counter

from . import arithmetic, bwt, huffman, lz77, lz78, lzw, mtf, rle


class _Identity:
    encode = staticmethod(lambda d: d)
    decode = staticmethod(lambda d: d)


# ---------- briques communes ----------

def _pack_parts(parts):
    return b"".join(struct.pack(">I", len(p)) + p for p in parts)


def _unpack_parts(blob):
    parts, pos = [], 0
    while pos < len(blob):
        (n,) = struct.unpack_from(">I", blob, pos)
        parts.append(blob[pos + 4:pos + 4 + n])
        pos += 4 + n
    return parts


def _lz_compress(data, window, coder):
    """LZ77 puis chaque flux (longueurs, caractères, distances) passe dans `coder`."""
    streams = lz77.to_streams(lz77.tokens(data, window))
    return _pack_parts([coder.encode(s) for s in streams])


def _lz_decompress(blob, coder):
    streams = [coder.decode(p) for p in _unpack_parts(blob)]
    return lz77.expand(lz77.from_streams(*streams))


def _bzip2_compress(data):
    return huffman.encode(rle.encode(mtf.encode(bwt.encode(data))))


def _bzip2_decompress(blob):
    return bwt.decode(mtf.decode(rle.decode(huffman.decode(blob))))


# ---------- registre : nom -> (identifiant dans l'archive, compresser, décompresser) ----------

METHODS = {
    "store": (0, lambda d: d, lambda d: d),
    "rle": (1, rle.encode, rle.decode),
    "huffman": (2, huffman.encode, huffman.decode),
    "arithmetic": (3, arithmetic.encode, arithmetic.decode),
    "lz77": (4, lambda d: _lz_compress(d, 32767, _Identity), lambda b: _lz_decompress(b, _Identity)),
    "lz78": (5, lz78.encode, lz78.decode),
    "lzw": (6, lzw.encode, lzw.decode),
    "deflate": (7, lambda d: _lz_compress(d, 32767, huffman), lambda b: _lz_decompress(b, huffman)),
    "bzip2": (8, _bzip2_compress, _bzip2_decompress),
    "lzma": (9, lambda d: _lz_compress(d, 65535, arithmetic), lambda b: _lz_decompress(b, arithmetic)),
}
BY_ID = {v[0]: (name, v[1], v[2]) for name, v in METHODS.items()}
AUTO_CANDIDATES = ["deflate", "bzip2", "lzma"]


def entropy(data: bytes) -> float:
    """Entropie de Shannon (bits par octet) sur le début des données : 8 = aléatoire."""
    sample = data[:65536]
    if not sample:
        return 0.0
    n = len(sample)
    return -sum(c / n * math.log2(c / n) for c in Counter(sample).values())


def compress_block(data: bytes, method: str = "auto"):
    """Compresse un bloc. Renvoie (identifiant de méthode, données compressées).

    "auto" essaie plusieurs méthodes et garde la meilleure ; si rien ne réduit
    la taille (données déjà compressées : jpg, mp3, mp4, zip...), le bloc est stocké tel quel.
    """
    if not data:
        return 0, b""
    if method == "auto":
        if entropy(data) > 7.9:  # quasi aléatoire : inutile d'essayer
            return 0, data
        candidates = AUTO_CANDIDATES
    elif method in METHODS:
        candidates = [method]
    else:
        raise ValueError("méthode inconnue : %s (choix : auto, %s)" % (method, ", ".join(METHODS)))
    best_id, best = 0, data
    for name in candidates:
        mid, enc, _ = METHODS[name]
        comp = enc(data)
        if len(comp) < len(best):
            best_id, best = mid, comp
    return best_id, best


def decompress_block(method_id: int, comp: bytes, raw_len: int) -> bytes:
    if method_id not in BY_ID:
        raise ValueError("méthode inconnue dans l'archive : %d" % method_id)
    data = BY_ID[method_id][2](comp)
    if len(data) != raw_len:
        raise ValueError("taille décompressée incorrecte")
    return data
