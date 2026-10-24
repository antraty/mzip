# mzip — un mini WinRAR / WinZip pédagogique

Compresseur / archiveur **sans perte** écrit en Python pur (aucune dépendance),
construit à partir des algorithmes du cours : Huffman, RLE, BWT, codage
arithmétique, LZ77, LZ78, LZW. Il fonctionne sur **n'importe quel fichier**
(texte, image, audio, vidéo, exécutable...) car il travaille sur des octets.

## Utilisation

```bash
python mzip.py create  archive.mz  photo.bmp  musique.wav  dossier/   # créer
python mzip.py create  -m bzip2  texte.mz  livre.txt                  # forcer une méthode
python mzip.py list    archive.mz                                     # contenu + ratios
python mzip.py extract archive.mz -o sortie/                          # extraire
python mzip.py test    archive.mz                                     # vérifier les CRC
python mzip.py bench   fichier                                        # comparer toutes les méthodes
python tests.py                                                       # tests automatiques
python demo.py                                                        # démonstration complète
```

Méthodes (`-m`) : `auto` (défaut), `store`, `rle`, `huffman`, `arithmetic`,
`lz77`, `lz78`, `lzw`, `deflate`, `bzip2`, `lzma`.

## Organisation du code (un fichier = un algorithme du cours)

| Fichier | Contenu |
|---|---|
| `compresseur/rle.py` | Run-Length Encoding |
| `compresseur/huffman.py` | Huffman (code canonique) |
| `compresseur/bwt.py` + `mtf.py` | Burrows-Wheeler + Move-To-Front |
| `compresseur/arithmetic.py` | Codage arithmétique (entiers 32 bits) |
| `compresseur/lz77.py` | LZ77, triplets (distance, longueur, caractère) |
| `compresseur/lz78.py` | LZ78, dictionnaire (indice, caractère) |
| `compresseur/lzw.py` | LZW, codes de 9 à 16 bits |
| `compresseur/methods.py` | Assemblages : **deflate**, **bzip2**, **lzma** |
| `compresseur/archive.py` | Format d'archive `.mz` (dossiers, CRC32, blocs) |
| `mzip.py` | Ligne de commande |

## Les "clones"

| Méthode | Chaîne de traitement | Remarque |
|---|---|---|
| `deflate` | LZ77 → Huffman | même principe que zip / gzip |
| `bzip2` | BWT → MTF → RLE → Huffman | même principe que bzip2 |
| `lzma` | LZ77 (fenêtre 64 Ko) → codage arithmétique | version très simplifiée de LZMA |

Ce sont des clones **fonctionnels** dans l'esprit des originaux, pas des
clones **compatibles** : un `.mz` ne s'ouvre pas dans 7-Zip, et inversement.

## Fonctionnement de l'archive

Chaque fichier est découpé en blocs de 256 Ko. Pour chaque bloc, le mode `auto`
essaie deflate, bzip2 et lzma et garde le plus petit résultat. Si aucun ne
réduit la taille (données déjà compressées), le bloc est **stocké** tel quel.
Un CRC32 par fichier détecte toute corruption.

## Différences avec le cours

- **Arithmétique** : le cours utilise des fractions exactes ; ici des entiers
  32 bits avec renormalisation (même idée, utilisable sur de gros fichiers).
- **BWT** : l'indice commence à 0 (`BANANA` → `NNBAAA`, 3 ; le cours compte 4).
- **LZ77** : longueur minimale d'une correspondance = 3 (une correspondance de 1
  octet coûte plus cher qu'un simple caractère) ; fenêtre 32 Ko / 64 Ko.
- **LZ78** : fin de données gérée par la taille stockée en en-tête (pas de EOT).
- **RLE** : les séries de 4 octets ou plus sont codées `x x x x <reste>`
  pour que les données sans répétition ne grossissent jamais.

## Limites

- Python pur : environ 1 à 2 Mo/s. Pour de très gros fichiers, utilisez `-m deflate`
  ou `-m lzw` (plus rapides que `auto`).
- Audio WAV avec bruit, images JPEG/PNG, vidéos MP4/MKV, MP3 : déjà compressés
  ou trop irréguliers, le gain est faible voire nul. C'est normal (WinRAR
  non plus ne les réduit pas). Les formats non compressés (BMP, WAV, TXT, CSV)
  donnent de très bons ratios.
- Les dossiers vides ne sont pas archivés ; les permissions ne sont pas conservées.
