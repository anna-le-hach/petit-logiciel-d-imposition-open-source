"""
schemes.py — Définitions des schémas d'imposition.

Un "schéma" décrit comment les pages d'un cahier (signature) se placent
sur une feuille d'impression, une fois celle-ci pliée N fois.

Chaque schéma est une liste de "slots". Un slot dit :
    - sur quelle face de la feuille il se trouve ("recto" ou "verso")
    - à quelle position (col, row) dans la grille de panneaux de cette face
    - quel numéro de page du cahier (1..N, en ordre de lecture) il porte
    - de combien de degrés il faut faire pivoter la page source (0, 90, 180, 270)

IMPORTANT — pourquoi seul le schéma "fold_1" (pli simple, in-2) est fourni
pour l'instant :

Le schéma à un seul pli (A4 -> A5 imbriqué, comme dans ton script InDesign)
se calcule avec une formule fiable et vérifiable :

    Pour un cahier de P pages (P divisible par 4), feuille k (k=1 = la plus
    extérieure), sur S = P/4 feuilles imbriquées :
        recto : gauche = P - 2k + 2   |   droite = 2k - 1
        verso : gauche = 2k           |   droite = P - 2k + 1

Les schémas à plis multiples (in-4, in-8, in-16, in-32) dépendent de
l'ORDRE et du SENS des plis (pli à angle droit, sens du grain du papier,
quel côté est "à cheval"...) — il existe plusieurs variantes standard
selon les fabricants de plieuses (voir les codes CIP4/JDF type "F16-6").
Se planter sur une rotation ou un miroir donne un cahier illisible une
fois plié. La méthode fiable : plier une vraie feuille numérotée
1..N dans l'ordre de lecture, la déplier, relever position + rotation
de chaque case, et transcrire ça ici une fois pour toutes.

C'est pour ça que la structure ci-dessous est pensée pour qu'on ajoute
un schéma à la fois, vérifié physiquement, plutôt que de générer les
plis multiples "à l'aveugle".
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    side: str       # "recto" ou "verso"
    col: int        # colonne dans la grille de panneaux (0-indexé)
    row: int         # ligne dans la grille de panneaux (0-indexé)
    page_number: int  # numéro de page dans le cahier, 1..N (ordre de lecture)
    rotation: int     # rotation en degrés à appliquer à la page source (0/90/180/270)


def fold_1_scheme(pages_per_sheet: int) -> dict:
    """
    Schéma à un seul pli (in-2), imbrication classique du dos carré cousu.

    pages_per_sheet doit être un multiple de 4 (c'est le nombre de pages
    du cahier obtenu en imbriquant plusieurs feuilles pliées une fois).

    Retourne un dict avec :
        - "grid": (cols, rows) de la grille de panneaux par face -> (2, 1)
        - "slots": liste de Slot
    """
    if pages_per_sheet % 4 != 0:
        raise ValueError("pages_per_sheet doit être un multiple de 4 pour un pli simple")

    n_feuilles = pages_per_sheet // 4
    slots = []
    P = pages_per_sheet
    for k in range(1, n_feuilles + 1):
        front_left = P - 2 * k + 2
        front_right = 2 * k - 1
        back_left = 2 * k
        back_right = P - 2 * k + 1

        # Chaque feuille imbriquée est une "sous-feuille" distincte, on les
        # indexe par sheet_index pour que le moteur sache combien de
        # feuilles physiques imprimer par cahier.
        # Pli simple = aucune rotation nécessaire, toutes les pages
        # restent à l'endroit une fois la feuille pliée.
        slots.append((k, Slot("recto", 0, 0, front_left, 0)))
        slots.append((k, Slot("recto", 1, 0, front_right, 0)))
        slots.append((k, Slot("verso", 0, 0, back_left, 0)))
        slots.append((k, Slot("verso", 1, 0, back_right, 0)))

    return {
        "name": "fold_1",
        "n_folds": 1,
        "grid": (2, 1),
        "pages_per_sheet": pages_per_sheet,
        "n_feuilles_par_cahier": n_feuilles,
        "slots": slots,  # liste de (sheet_index, Slot)
    }


# Registre des schémas disponibles. On en ajoutera d'autres ici
# (fold_2, fold_3, fold_4, fold_5 = in-4/in-8/in-16/in-32) une fois
# vérifiés physiquement.
SCHEMES = {
    "fold_1": fold_1_scheme,
}
