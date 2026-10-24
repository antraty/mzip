"""Codage arithmétique (version entière à 32 bits).

Le cours utilise des fractions exactes (0,1447 pour "CALCUL"), ce qui est
impossible sur de grosses données. Ici on applique la MÊME idée sur des entiers :
on garde un intervalle [low, high] de 32 bits, on le réduit à la sous-partie du
symbole, et dès que ses bits de poids fort sont connus on les envoie (on "zoome").

Format : [n : 4][nb symboles : 2][(symbole, fréquence) ...][bits]
"""
import struct
from bisect import bisect_right
from collections import Counter

from .bitio import BitReader, BitWriter

FULL = (1 << 32) - 1
HALF = 1 << 31
QUARTER = 1 << 30
MAX_TOTAL = 65535  # somme maximale des fréquences


def _scale(freq: dict) -> dict:
    total = sum(freq.values())
    if total <= MAX_TOTAL:
        return dict(freq)
    target = MAX_TOTAL - 256
    return {s: max(1, f * target // total) for s, f in freq.items()}


def encode(data: bytes) -> bytes:
    n = len(data)
    header = struct.pack(">I", n)
    if n == 0:
        return header
    freq = _scale(Counter(data))
    syms = sorted(freq)
    header += struct.pack(">H", len(syms)) + b"".join(struct.pack(">BH", s, freq[s]) for s in syms)

    cum_low, total = {}, 0  # C(s_{i-1}) du cours, en entiers
    for s in syms:
        cum_low[s] = total
        total += freq[s]

    w = BitWriter()
    low, high, pending = 0, FULL, 0

    def emit(bit):
        nonlocal pending
        w.write_bit(bit)
        for _ in range(pending):
            w.write_bit(1 - bit)
        pending = 0

    for b in data:
        rng = high - low + 1
        high = low + rng * (cum_low[b] + freq[b]) // total - 1
        low = low + rng * cum_low[b] // total
        while True:  # on envoie les bits devenus certains
            if high < HALF:
                emit(0)
            elif low >= HALF:
                emit(1)
                low -= HALF
                high -= HALF
            elif low >= QUARTER and high < 3 * QUARTER:
                pending += 1  # bit encore incertain
                low -= QUARTER
                high -= QUARTER
            else:
                break
            low = low * 2
            high = high * 2 + 1
    pending += 1
    emit(0 if low < QUARTER else 1)
    return header + w.getvalue()


def decode(blob: bytes) -> bytes:
    (n,) = struct.unpack_from(">I", blob)
    if n == 0:
        return b""
    (k,) = struct.unpack_from(">H", blob, 4)
    syms, freqs, starts, total = [], [], [], 0
    for i in range(k):
        s, f = struct.unpack_from(">BH", blob, 6 + 3 * i)
        syms.append(s)
        freqs.append(f)
        starts.append(total)
        total += f
    r = BitReader(blob[6 + 3 * k:])
    value = r.read_bits(32)
    low, high = 0, FULL
    out = bytearray()
    for _ in range(n):
        rng = high - low + 1
        scaled = ((value - low + 1) * total - 1) // rng
        i = bisect_right(starts, scaled) - 1  # sous-intervalle qui contient la valeur
        out.append(syms[i])
        high = low + rng * (starts[i] + freqs[i]) // total - 1
        low = low + rng * starts[i] // total
        while True:
            if high < HALF:
                pass
            elif low >= HALF:
                value -= HALF
                low -= HALF
                high -= HALF
            elif low >= QUARTER and high < 3 * QUARTER:
                value -= QUARTER
                low -= QUARTER
                high -= QUARTER
            else:
                break
            low = low * 2
            high = high * 2 + 1
            value = value * 2 + r.read_bit()
    return bytes(out)
