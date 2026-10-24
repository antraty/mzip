"""Run-Length Encoding (RLE) sur des octets.

Principe : une série de 4 octets identiques ou plus est écrite sous la forme
    <octet> <octet> <octet> <octet> <nombre de répétitions supplémentaires>
Les séries plus courtes restent telles quelles : les données sans répétition
ne grossissent donc jamais (contrairement au RLE naïf "4A3B2C...").
"""


def encode(data: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        b = data[i]
        j = i + 1
        while j < n and data[j] == b and j - i < 259:  # 4 + 255 maximum
            j += 1
        run = j - i
        if run >= 4:
            out += bytes([b]) * 4
            out.append(run - 4)
        else:
            out += bytes([b]) * run
        i = j
    return bytes(out)


def decode(data: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(data)
    prev, run = -1, 0
    while i < n:
        b = data[i]
        i += 1
        out.append(b)
        if b == prev:
            run += 1
        else:
            prev, run = b, 1
        if run == 4:  # le prochain octet est le nombre de répétitions en plus
            if i < n:
                out += bytes([b]) * data[i]
                i += 1
            prev, run = -1, 0
    return bytes(out)
