"""LZ78 : dictionnaire construit au fil de l'eau, paires (indice, caractère).

Format : [n : 4 octets] puis des paires de 3 octets (indice : 2, caractère : 1).
Quand le dictionnaire est plein (65535 entrées) on le vide et on repart.
"""
import struct

MAX_ENTRIES = 65535


def encode(data: bytes) -> bytes:
    out = bytearray(struct.pack(">I", len(data)))
    dico = {}  # (indice du préfixe, octet) -> indice de la nouvelle entrée
    nxt = 1  # l'indice 0 = chaîne vide
    cur = 0
    for b in data:
        if (cur, b) in dico:
            cur = dico[(cur, b)]  # la séquence existe : on continue de l'étendre
        else:
            out += struct.pack(">HB", cur, b)  # (préfixe connu, nouveau caractère)
            if nxt < MAX_ENTRIES:
                dico[(cur, b)] = nxt
                nxt += 1
            else:
                dico.clear()
                nxt = 1
            cur = 0
    if cur:  # les données se terminent au milieu d'une séquence connue
        out += struct.pack(">HB", cur, 0)  # caractère bidon, coupé au décodage grâce à n
    return bytes(out)


def decode(blob: bytes) -> bytes:
    (n,) = struct.unpack_from(">I", blob)
    entries = [b""]
    out = bytearray()
    for pos in range(4, len(blob), 3):
        idx, char = struct.unpack_from(">HB", blob, pos)
        s = entries[idx] + bytes([char])
        out += s
        if len(entries) < MAX_ENTRIES:
            entries.append(s)
        else:
            entries = [b""]
    return bytes(out[:n])
