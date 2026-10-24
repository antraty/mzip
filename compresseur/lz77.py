"""LZ77 : fenêtre glissante, triplets (distance, longueur, caractère).

tokens()  : données -> liste de triplets (comme dans le cours)
expand()  : triplets -> données
to_streams()/from_streams() : range les triplets dans 4 flux d'octets
    (longueurs, caractères, distance haute, distance basse) pour que
    Huffman ou le codage arithmétique les compressent bien ensuite.
"""
MAX_LEN = 255
MIN_MATCH = 3


def tokens(data: bytes, window: int = 32767, max_chain: int = 32):
    """Renvoie la liste des triplets (distance, longueur, caractère suivant).

    Le "buffer de recherche" est la fenêtre des `window` derniers octets.
    Pour trouver vite les correspondances, on indexe chaque position par ses
    3 premiers octets (au lieu de comparer avec toute la fenêtre).
    """
    n = len(data)
    index = {}  # 3 octets -> positions où ils apparaissent
    out = []
    i = 0
    while i < n:
        best_len = best_dist = 0
        if i + 2 < n:
            limit = min(MAX_LEN, n - i - 1)  # il doit rester un caractère après la correspondance
            for pos in reversed(index.get(data[i:i + 3], ())[-max_chain:]):
                dist = i - pos
                if dist > window:
                    break
                length = 0
                while length < limit and data[pos + length] == data[i + length]:
                    length += 1
                if length > best_len:
                    best_len, best_dist = length, dist
                    if length == limit:
                        break
        if best_len < MIN_MATCH:
            best_len = best_dist = 0  # pas de correspondance : (0, 0, caractère)
        out.append((best_dist, best_len, data[i + best_len]))
        step = best_len + 1
        for p in range(i, min(i + step, n - 2)):
            index.setdefault(data[p:p + 3], []).append(p)
        i += step
    return out


def expand(toks) -> bytes:
    out = bytearray()
    for dist, length, char in toks:
        start = len(out) - dist
        for k in range(length):  # octet par octet : la copie peut se chevaucher elle-même
            out.append(out[start + k])
        out.append(char)
    return bytes(out)


def to_streams(toks):
    lens, chars, dhi, dlo = bytearray(), bytearray(), bytearray(), bytearray()
    for dist, length, char in toks:
        lens.append(length)
        chars.append(char)
        if length:
            dhi.append(dist >> 8)
            dlo.append(dist & 255)
    return bytes(lens), bytes(chars), bytes(dhi), bytes(dlo)


def from_streams(lens, chars, dhi, dlo):
    toks, j = [], 0
    for length, char in zip(lens, chars):
        if length:
            toks.append(((dhi[j] << 8) | dlo[j], length, char))
            j += 1
        else:
            toks.append((0, 0, char))
    return toks
