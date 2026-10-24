"""LZW : dictionnaire initialisé avec les 256 octets, codes de 9 à 16 bits.

Format : [nombre de codes : 4 octets][codes sur bits].
La largeur des codes grandit avec le dictionnaire ; encodeur et décodeur
la calculent de la même façon à partir du numéro du code (sans la transmettre).
"""
import struct

from .bitio import BitReader, BitWriter

MAX_CODES = 65536


def _width(k: int) -> int:
    """Largeur du k-ième code émis (k >= 1) : le plus grand code possible est 254 + k."""
    return min(16, max(9, (254 + k).bit_length()))


def encode(data: bytes) -> bytes:
    w = BitWriter()
    dico = {}  # (code du préfixe, octet) -> code
    nxt, k, cur = 256, 0, -1
    for b in data:
        if cur < 0:
            cur = b
        elif (cur, b) in dico:
            cur = dico[(cur, b)]  # le motif est connu : on l'allonge
        else:
            k += 1
            w.write_bits(cur, _width(k))  # on émet le plus long motif connu
            if nxt < MAX_CODES:
                dico[(cur, b)] = nxt  # et on enregistre motif + nouveau caractère
                nxt += 1
            cur = b
    if cur >= 0:
        k += 1
        w.write_bits(cur, _width(k))
    return struct.pack(">I", k) + w.getvalue()


def decode(blob: bytes) -> bytes:
    (count,) = struct.unpack_from(">I", blob)
    r = BitReader(blob[4:])
    table = [bytes([i]) for i in range(256)]
    out = bytearray()
    prev = None
    for k in range(1, count + 1):
        code = r.read_bits(_width(k))
        if code < len(table):
            entry = table[code]
        else:  # cas particulier : le code vient d'être créé par l'encodeur (motif "KwKwK")
            entry = prev + prev[:1]
        out += entry
        if prev is not None and len(table) < MAX_CODES:
            table.append(prev + entry[:1])
        prev = entry
    return bytes(out)
