"""Move-To-Front : après la BWT, les octets identiques sont groupés ;
le MTF les transforme en petits nombres (surtout des 0) très faciles à
compresser ensuite par RLE + Huffman."""


def encode(data: bytes) -> bytes:
    table = list(range(256))
    out = bytearray()
    for b in data:
        i = table.index(b)
        out.append(i)
        del table[i]
        table.insert(0, b)
    return bytes(out)


def decode(data: bytes) -> bytes:
    table = list(range(256))
    out = bytearray()
    for i in data:
        b = table.pop(i)
        out.append(b)
        table.insert(0, b)
    return bytes(out)
