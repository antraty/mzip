#!/usr/bin/env python3
"""mzip : mini WinRAR / WinZip pédagogique (compression sans perte de tout type de fichier).

Exemples :
    python mzip.py create  mon_archive.mz  photo.bmp  musique.wav  dossier/
    python mzip.py create  -m bzip2  texte.mz  livre.txt
    python mzip.py list    mon_archive.mz
    python mzip.py extract mon_archive.mz  -o sortie/
    python mzip.py test    mon_archive.mz
    python mzip.py bench   photo.bmp          (compare toutes les méthodes)
"""
import argparse
import os
import sys
import time

from compresseur import archive
from compresseur.methods import METHODS, compress_block, decompress_block


def pct(csize, size):
    return "%5.1f%%" % (100.0 * csize / size) if size else "   -  "


def human(n):
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return "%d %s" % (n, unit) if unit == "o" else "%.1f %s" % (n, unit)
        n /= 1024.0


def cmd_create(a):
    t = time.time()
    stats = archive.create(a.archive, a.inputs, a.method,
                           callback=lambda n, s, c: print("  + %-40s %10s -> %10s  %s" % (n, human(s), human(c), pct(c, s))))
    total, ctotal = sum(s[1] for s in stats), os.path.getsize(a.archive)
    print("%d fichier(s) : %s -> %s (%s) en %.1f s" % (len(stats), human(total), human(ctotal), pct(ctotal, total), time.time() - t))


def cmd_extract(a):
    files = archive.extract(a.archive, a.output, callback=lambda n, s: print("  - %s (%s)" % (n, human(s))))
    print("%d fichier(s) extrait(s) dans %s" % (len(files), a.output))


def cmd_list(a):
    rows = archive.list_entries(a.archive)
    for name, size, csize, used in rows:
        print("%-40s %10s %10s %s  %s" % (name, human(size), human(csize), pct(csize, size), ",".join(used)))
    ts, tc = sum(r[1] for r in rows), sum(r[2] for r in rows)
    print("-" * 80 + "\nTotal : %d fichier(s), %s -> %s (%s)" % (len(rows), human(ts), human(tc), pct(tc, ts)))


def cmd_test(a):
    print("Archive OK : %d fichier(s) vérifié(s) (CRC valides)" % archive.test(a.archive))


def cmd_bench(a):
    with open(a.file, "rb") as f:
        data = f.read(a.limit)
    print("%s : %s analysés\n%-12s %10s %8s %8s  %s" % (a.file, human(len(data)), "méthode", "taille", "ratio", "temps", "aller-retour"))
    for name in METHODS:
        t = time.time()
        mid, comp = compress_block(data, name)
        dt = time.time() - t
        ok = decompress_block(mid, comp, len(data)) == data
        print("%-12s %10s %8s %7.2fs  %s" % (name, human(len(comp)), pct(len(comp), len(data)), dt, "OK" if ok else "ERREUR"))


def main():
    p = argparse.ArgumentParser(description="mini WinRAR pédagogique")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", aliases=["c"], help="créer une archive")
    c.add_argument("archive")
    c.add_argument("inputs", nargs="+", help="fichiers et/ou dossiers")
    c.add_argument("-m", "--method", default="auto", help="auto (défaut), %s" % ", ".join(METHODS))
    c.set_defaults(func=cmd_create)
    x = sub.add_parser("extract", aliases=["x"], help="extraire une archive")
    x.add_argument("archive")
    x.add_argument("-o", "--output", default=".")
    x.set_defaults(func=cmd_extract)
    l = sub.add_parser("list", aliases=["l"], help="lister le contenu")
    l.add_argument("archive")
    l.set_defaults(func=cmd_list)
    t = sub.add_parser("test", aliases=["t"], help="vérifier l'intégrité")
    t.add_argument("archive")
    t.set_defaults(func=cmd_test)
    b = sub.add_parser("bench", help="comparer toutes les méthodes sur un fichier")
    b.add_argument("file")
    b.add_argument("--limit", type=int, default=65536, help="octets lus au début du fichier (défaut 64 Ko)")
    b.set_defaults(func=cmd_bench)
    a = p.parse_args()
    try:
        a.func(a)
    except (archive.ArchiveError, FileNotFoundError, ValueError) as e:
        sys.exit("Erreur : %s" % e)


if __name__ == "__main__":
    main()
