"""Démonstration : génère des fichiers de test (texte, image, audio, "vidéo"),
les archive, les extrait et vérifie qu'ils sont identiques.

    python demo.py
"""
import filecmp
import math
import os
import random
import shutil
import struct
import tempfile

from compresseur import archive

random.seed(42)
WORDS = "le la de compression données fichier algorithme arbre symbole fréquence dictionnaire fenêtre buffer code binaire".split()


def make_text(path):
    with open(path, "w", encoding="utf-8") as f:
        for _ in range(3000):
            f.write(" ".join(random.choice(WORDS) for _ in range(random.randint(5, 14))).capitalize() + ".\n")


def make_bmp(path, w=256, h=192):
    """Image BMP 24 bits non compressée : dégradé + cercle."""
    rows = bytearray()
    for y in range(h):
        row = bytearray()
        for x in range(w):
            inside = (x - 128) ** 2 + (y - 96) ** 2 < 60 ** 2
            row += bytes((255, 200, 0) if inside else (x, y, 128))
        rows += row + b"\0" * ((-len(row)) % 4)
    header = b"BM" + struct.pack("<IHHI", 54 + len(rows), 0, 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(rows), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + rows)


def make_wav(path, seconds=3, rate=22050):
    """Audio WAV 16 bits : trois sinus + un peu de bruit."""
    frames = bytearray()
    for i in range(seconds * rate):
        t = i / rate
        v = 9000 * math.sin(2 * math.pi * 440 * t) + 4000 * math.sin(2 * math.pi * 660 * t) + random.randint(-200, 200)
        frames += struct.pack("<h", int(v))
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        f.write(b"data" + struct.pack("<I", len(frames)) + frames)


def make_video(path, size=400_000):
    """Une vraie vidéo (mp4, mkv...) est déjà compressée : ses octets ressemblent à du hasard."""
    with open(path, "wb") as f:
        f.write(bytes(random.randrange(256) for _ in range(size)))


def main():
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "echantillons")
    os.makedirs(src)
    make_text(os.path.join(src, "texte.txt"))
    make_bmp(os.path.join(src, "image.bmp"))
    make_wav(os.path.join(src, "audio.wav"))
    make_video(os.path.join(src, "video.mp4"))
    arc = os.path.join(tmp, "demo.mz")

    print("== Création de l'archive ==")
    stats = archive.create(arc, [src], "auto")
    print("%-28s %10s %10s %7s  %s" % ("fichier", "taille", "archive", "ratio", "méthodes"))
    used = {name: m for name, _, _, m in archive.list_entries(arc)}
    for name, size, csize in stats:
        print("%-28s %10d %10d %6.1f%%  %s" % (name, size, csize, 100 * csize / size, ",".join(used[name])))
    total, ctotal = sum(s[1] for s in stats), os.path.getsize(arc)
    print("%-28s %10d %10d %6.1f%%" % ("TOTAL", total, ctotal, 100 * ctotal / total))

    print("\n== Vérification et extraction ==")
    print("CRC OK pour %d fichiers" % archive.test(arc))
    out = os.path.join(tmp, "sortie")
    archive.extract(arc, out)
    ok = all(filecmp.cmp(os.path.join(src, n), os.path.join(out, "echantillons", n), shallow=False)
             for n in os.listdir(src))
    print("Fichiers extraits identiques aux originaux :", "OUI" if ok else "NON")
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
