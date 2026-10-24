"""Transformée de Burrows-Wheeler (BWT), par blocs.

transform(b"BANANA") -> (b"NNBAAA", 3)
(le cours donne 4 car il compte à partir de 1 ; ici on compte à partir de 0)
"""
import struct

BLOCK = 65536  # taille des blocs traités (comme bzip2, mais plus petit)


def transform(block: bytes):
    """Trie toutes les rotations du bloc et renvoie (dernière colonne, position de l'original).

    Au lieu de fabriquer les n rotations (trop gros en mémoire), on les trie par
    "doublement de préfixe" : on trie d'abord sur 1 caractère, puis 2, 4, 8...
    """
    n = len(block)
    rank = list(block)
    sa = list(range(n))  # sa = indices de départ des rotations, triés
    k = 1
    while True:
        key = lambda i: (rank[i], rank[(i + k) % n])
        sa.sort(key=key)
        new = [0] * n
        for j in range(1, n):
            new[sa[j]] = new[sa[j - 1]] + (key(sa[j]) != key(sa[j - 1]))
        rank = new
        if n == 0 or rank[sa[-1]] == n - 1 or k >= n:
            break
        k *= 2
    last = bytes(block[i - 1] for i in sa)  # dernier caractère de chaque rotation
    return last, (sa.index(0) if n else 0)


def inverse(last: bytes, index: int) -> bytes:
    """Reconstruit le texte d'origine à partir de la dernière colonne."""
    n = len(last)
    counts = [0] * 256
    for b in last:
        counts[b] += 1
    start, total = [0] * 256, 0
    for c in range(256):
        start[c] = total
        total += counts[c]
    # nxt[i] = ligne de la matrice triée qui commence par le caractère last[i]
    nxt, seen = [0] * n, [0] * 256
    for i, c in enumerate(last):
        nxt[i] = start[c] + seen[c]
        seen[c] += 1
    out = bytearray()
    row = index
    for _ in range(n):
        out.append(last[row])
        row = nxt[row]
    out.reverse()
    return bytes(out)


def encode(data: bytes) -> bytes:
    blocks = [data[i:i + BLOCK] for i in range(0, len(data), BLOCK)]
    header, body = struct.pack(">I", len(blocks)), bytearray()
    for b in blocks:
        last, idx = transform(b)
        header += struct.pack(">II", len(b), idx)
        body += last
    return header + bytes(body)


def decode(blob: bytes) -> bytes:
    (nb,) = struct.unpack_from(">I", blob)
    pos = 4 + 8 * nb
    out = bytearray()
    for k in range(nb):
        size, idx = struct.unpack_from(">II", blob, 4 + 8 * k)
        out += inverse(blob[pos:pos + size], idx)
        pos += size
    return bytes(out)
