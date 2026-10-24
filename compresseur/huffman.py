"""Codage de Huffman (version canonique).

Format : [n : 4 octets][longueur du code de chacun des 256 octets][bits]
On ne stocke que les LONGUEURS des codes : les codes eux-mêmes sont
reconstruits de façon déterministe (code canonique), pas besoin de l'arbre.
"""
import heapq
import struct
from collections import Counter

from .bitio import bits_to_bytes, bytes_to_bits


def code_lengths(freq: dict) -> dict:
    """Construit l'arbre de Huffman et renvoie {symbole: longueur du code}."""
    if len(freq) == 1:
        return {next(iter(freq)): 1}
    # tas de (fréquence, numéro unique, noeud) ; un noeud est un symbole ou (gauche, droite)
    heap = [(f, s, s) for s, f in freq.items()]
    heapq.heapify(heap)
    tie = 256
    while len(heap) > 1:
        f1, _, a = heapq.heappop(heap)  # les deux plus petites fréquences
        f2, _, b = heapq.heappop(heap)
        heapq.heappush(heap, (f1 + f2, tie, (a, b)))  # on les fusionne en un parent
        tie += 1
    lengths = {}
    stack = [(heap[0][2], 0)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, int):
            lengths[node] = depth
        else:
            stack.append((node[0], depth + 1))  # branche gauche = 0
            stack.append((node[1], depth + 1))  # branche droite = 1
    return lengths


def canonical_codes(lengths: dict) -> dict:
    """{symbole: longueur} -> {symbole: chaîne de bits}"""
    items = sorted(lengths.items(), key=lambda kv: (kv[1], kv[0]))
    codes, code, prev = {}, 0, items[0][1]
    for sym, length in items:
        code <<= length - prev
        prev = length
        codes[sym] = format(code, "0%db" % length)
        code += 1
    return codes


def encode(data: bytes) -> bytes:
    header = struct.pack(">I", len(data))
    if not data:
        return header
    lengths = code_lengths(Counter(data))
    table = bytes(lengths.get(s, 0) for s in range(256))
    codes = canonical_codes(lengths)
    bits = "".join([codes[b] for b in data])
    return header + table + bits_to_bytes(bits)


def decode(blob: bytes) -> bytes:
    (n,) = struct.unpack_from(">I", blob)
    if n == 0:
        return b""
    lengths = {s: l for s, l in enumerate(blob[4:260]) if l}
    reverse = {code: s for s, code in canonical_codes(lengths).items()}
    out = bytearray()
    cur = ""
    for bit in bytes_to_bits(blob[260:]):  # on part de la racine, on descend bit par bit
        cur += bit
        sym = reverse.get(cur)
        if sym is not None:  # feuille atteinte -> symbole, retour à la racine
            out.append(sym)
            if len(out) == n:
                break
            cur = ""
    return bytes(out)
