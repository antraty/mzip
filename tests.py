"""Tests : python tests.py"""
import os
import random
import tempfile
import unittest

from compresseur import archive, arithmetic, bwt, huffman, lz77, lz78, lzw, rle
from compresseur.methods import METHODS, compress_block, decompress_block

random.seed(1)
SAMPLES = {
    "vide": b"",
    "un octet": b"A",
    "ABRACADABRA": b"ABRACADABRA",
    "RLE": b"AAAABBBCCDAA",
    "CALCUL": b"CALCUL",
    "LZ77": b"CABRACADABRARRARRAD",
    "LZ78": b"WABBATWABBATWABBATWABBATWOOTWOOTWO",
    "LZW": b"ABABBABCABABBA",
    "BANANA": b"BANANA",
    "longue série": b"x" * 1000 + b"y" * 3 + b"z" * 300,
    "octets 0 et 255": bytes([0, 255] * 50 + [0] * 10),
    "texte": (b"Le codage de Huffman attribue des codes courts aux symboles frequents. " * 40),
    "aleatoire": bytes(random.randrange(256) for _ in range(3000)),
    "peu de symboles": bytes(random.choice(b"ab") for _ in range(2000)),
}


class TestCours(unittest.TestCase):
    def test_huffman_abracadabra_23_bits(self):
        from collections import Counter
        lengths = huffman.code_lengths(Counter(b"ABRACADABRA"))
        self.assertEqual(sum(lengths[c] * n for c, n in Counter(b"ABRACADABRA").items()), 23)

    def test_bwt_banana(self):
        self.assertEqual(bwt.transform(b"BANANA"), (b"NNBAAA", 3))

    def test_rle(self):
        self.assertEqual(rle.encode(b"AAAABBBCCDAA"), b"AAAA\x00BBBCCDAA")


class TestRoundTrip(unittest.TestCase):
    def test_all_methods(self):
        for method, (mid, enc, dec) in METHODS.items():
            for label, data in SAMPLES.items():
                with self.subTest(method=method, data=label):
                    self.assertEqual(dec(enc(data)), data)

    def test_blocks_auto(self):
        for label, data in SAMPLES.items():
            with self.subTest(data=label):
                mid, comp = compress_block(data)
                self.assertEqual(decompress_block(mid, comp, len(data)), data)

    def test_lz77_chevauchement(self):
        data = b"ab" * 500
        self.assertEqual(lz77.expand(lz77.tokens(data)), data)

    def test_dictionnaires_pleins(self):
        data = bytes(random.randrange(4) for _ in range(150000))  # remplit LZ78 / LZW
        self.assertEqual(lz78.decode(lz78.encode(data)), data)
        self.assertEqual(lzw.decode(lzw.encode(data)), data)

    def test_arithmetique_gros(self):
        data = bytes(random.choice(b"aaaabbc") for _ in range(100000))
        self.assertEqual(arithmetic.decode(arithmetic.encode(data)), data)

    def test_bwt_periodique(self):
        for data in (b"abab" * 50, b"aaaa", b"abcabcabc"):
            self.assertEqual(bwt.decode(bwt.encode(data)), data)


class TestArchive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        src = os.path.join(self.tmp, "src")
        os.makedirs(os.path.join(src, "sous dossier"))
        self.files = {
            "a.txt": SAMPLES["texte"],
            "vide.bin": b"",
            "sous dossier/é à ü.dat": SAMPLES["aleatoire"],
            "sous dossier/gros.txt": SAMPLES["texte"] * 200,  # > 1 bloc de 256 Ko
        }
        for name, data in self.files.items():
            with open(os.path.join(src, name), "wb") as f:
                f.write(data)
        self.src = src
        self.arc = os.path.join(self.tmp, "test.mz")

    def test_roundtrip(self):
        archive.create(self.arc, [self.src])
        self.assertEqual(archive.test(self.arc), len(self.files))
        out = os.path.join(self.tmp, "out")
        archive.extract(self.arc, out)
        for name, data in self.files.items():
            with open(os.path.join(out, "src", *name.split("/")), "rb") as f:
                self.assertEqual(f.read(), data, name)
        self.assertEqual(len(archive.list_entries(self.arc)), len(self.files))

    def test_chaque_methode(self):
        for method in METHODS:
            with self.subTest(method=method):
                archive.create(self.arc, [os.path.join(self.src, "a.txt")], method)
                self.assertEqual(archive.test(self.arc), 1)

    def test_corruption_detectee(self):
        archive.create(self.arc, [self.src])
        with open(self.arc, "rb") as f:
            raw = bytearray(f.read())
        raw[len(raw) // 2] ^= 0xFF
        with open(self.arc, "wb") as f:
            f.write(raw)
        with self.assertRaises(archive.ArchiveError):
            archive.test(self.arc)

    def test_nom_dangereux_refuse(self):
        with self.assertRaises(archive.ArchiveError):
            archive._safe_path(self.tmp, "../evil.txt")


if __name__ == "__main__":
    unittest.main(verbosity=1)
