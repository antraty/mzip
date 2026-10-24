"""Lecture / écriture de bits (utilisé par Huffman, arithmétique, LZW)."""


def bits_to_bytes(bits: str) -> bytes:
    """'0101...' -> octets (complété par des 0 à droite)."""
    if not bits:
        return b""
    pad = (-len(bits)) % 8
    bits += "0" * pad
    return int(bits, 2).to_bytes(len(bits) // 8, "big")


def bytes_to_bits(data: bytes) -> str:
    """octets -> '0101...'"""
    if not data:
        return ""
    return bin(int.from_bytes(data, "big"))[2:].zfill(len(data) * 8)


class BitWriter:
    def __init__(self):
        self.parts = []

    def write_bit(self, bit: int):
        self.parts.append("1" if bit else "0")

    def write_bits(self, value: int, count: int):
        """Écrit `value` sur `count` bits (poids fort d'abord)."""
        self.parts.append(format(value, "0%db" % count))

    def getvalue(self) -> bytes:
        return bits_to_bytes("".join(self.parts))


class BitReader:
    def __init__(self, data: bytes):
        self.bits = bytes_to_bits(data)
        self.pos = 0

    def read_bit(self) -> int:
        p = self.pos
        self.pos = p + 1
        return 1 if p < len(self.bits) and self.bits[p] == "1" else 0  # au-delà de la fin : 0

    def read_bits(self, count: int) -> int:
        chunk = self.bits[self.pos:self.pos + count].ljust(count, "0")
        self.pos += count
        return int(chunk, 2)
