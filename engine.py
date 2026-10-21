"""
engine.py : moteur d'imposition.

Deux types de reliure, une seule logique :

- Piqure a cheval : tout le livret est UNE signature (toutes les feuilles
  imbriquees, pliees une fois, piquees dans le pli).
- Reliure cousue : le livre est decoupe en plusieurs signatures de 4, 8,
  12, 16... 32 pages. Chaque signature est un petit livret (feuilles
  imbriquees, pliees une fois) ; les signatures sont ensuite cousues
  ensemble.

Pour une signature de P pages (P multiple de 4), feuille k (k = 1 pour la
feuille la plus exterieure) :
    recto : gauche = P - 2k + 2 | droite = 2k - 1
    verso : gauche = 2k         | droite = P - 2k + 1

La derniere signature est reduite au strict necessaire (multiple de 4),
pour eviter des pages blanches inutiles.

Traits de coupe et reperes (optionnels) : une marge de 12 mm est ajoutee autour
des pages, qui sont reduites pour y tenir (environ 89 % en A4, 88 % en A3).

Espacement (optionnel) : un vide de la valeur choisie (en mm) entre les deux pages
d'une feuille. Les pages sont reduites si besoin pour que le tout tienne sur la feuille.

Le format d'impression est la feuille sortie de l'imprimante, posee en
paysage. Une feuille A4 donne des pages A5, une feuille A3 des pages A4.
"""

import math
from collections import Counter

import pymupdf

FORMATS_IMPRESSION = {
    "A4": {"mm": (210, 297), "page_finale": "A5"},
    "A3": {"mm": (297, 420), "page_finale": "A4"},
}

TAILLES_SIGNATURE = [4, 8, 12, 16, 20, 24, 28, 32]

MM_TO_PT = 72 / 25.4

# Marge autour du bloc de pages quand on ajoute des traits de coupe ou des reperes.
# Les marques sont dessinees dans cette marge ; les pages sont reduites pour y tenir.
MARGE_REPERES_MM = 12


def _mm_to_pt(mm: float) -> float:
    return mm * MM_TO_PT


def decouper_en_signatures(n_pages_src: int, taille_signature=None) -> list:
    """
    Retourne la liste des tailles de signature (en pages).
    taille_signature=None : une seule signature (piqure a cheval).
    """
    if n_pages_src < 1:
        raise ValueError("Le PDF ne contient aucune page")
    n_total = math.ceil(n_pages_src / 4) * 4
    if taille_signature is None:
        return [n_total]
    if taille_signature not in TAILLES_SIGNATURE:
        raise ValueError(f"Taille de signature inconnue : {taille_signature}")

    tailles = []
    restant = n_total
    while restant > 0:
        s = min(taille_signature, restant)
        tailles.append(s)
        restant -= s
    return tailles


def plan(n_pages_src: int, format_impression: str, taille_signature=None) -> dict:
    """Calcule le livre sans toucher au PDF."""
    if format_impression not in FORMATS_IMPRESSION:
        raise ValueError(f"Format d'impression inconnu : {format_impression}")
    tailles = decouper_en_signatures(n_pages_src, taille_signature)
    n_total = sum(tailles)
    return {
        "tailles": tailles,
        "repartition": dict(Counter(tailles)),
        "n_signatures": len(tailles),
        "n_feuilles": n_total // 4,
        "n_pages_total": n_total,
        "n_blanches": n_total - n_pages_src,
        "page_finale": FORMATS_IMPRESSION[format_impression]["page_finale"],
    }


def sequence_signature(taille: int) -> list:
    """
    Ordre des pages sur chaque feuille d'une signature de `taille` pages.
    Une entree par feuille (de l'exterieure vers l'interieure) :
    ((recto_gauche, recto_droite), (verso_gauche, verso_droite)),
    numeros de page 1..taille.
    """
    if taille % 4 != 0 or taille < 4:
        raise ValueError("Une signature a un nombre de pages multiple de 4")
    feuilles = []
    for k in range(1, taille // 4 + 1):
        recto = (taille - 2 * k + 2, 2 * k - 1)
        verso = (2 * k, taille - 2 * k + 1)
        feuilles.append((recto, verso))
    return feuilles


def echelle(format_impression: str, avec_marges: bool, espacement_mm: float = 0) -> float:
    """
    Facteur de reduction des pages (1.0 = taille reelle) quand on ajoute la marge des
    reperes et/ou un espacement entre les deux pages d'une feuille.
    """
    w_mm, h_mm = FORMATS_IMPRESSION[format_impression]["mm"]
    larg, haut = h_mm, w_mm  # paysage
    m = MARGE_REPERES_MM if avec_marges else 0
    return min((larg - 2 * m) / (larg + espacement_mm), (haut - 2 * m) / haut)


def _dessiner_reperes(page, sheet_w, sheet_h, bloc, traits_coupe, reperes):
    """
    Dessine les marques dans la marge de la feuille.
    - traits_coupe : un trait a chaque coin du bloc de pages, plus deux traits de pli
      (haut et bas, au milieu).
    - reperes : une cible de repérage au milieu de chacun des quatre cotes.
    """
    x0, y0, x1, y1 = bloc  # bloc de pages (zone de coupe)
    xm, ym = sheet_w / 2, sheet_h / 2
    P = pymupdf.Point
    forme = page.new_shape()

    if traits_coupe:
        decal, long_coin, long_pli = _mm_to_pt(2), _mm_to_pt(4), _mm_to_pt(3)
        for cx, sx in ((x0, -1), (x1, 1)):
            for cy, sy in ((y0, -1), (y1, 1)):
                forme.draw_line(P(cx + sx * decal, cy), P(cx + sx * (decal + long_coin), cy))
                forme.draw_line(P(cx, cy + sy * decal), P(cx, cy + sy * (decal + long_coin)))
        for cy, sy in ((y0, -1), (y1, 1)):
            forme.draw_line(P(xm, cy + sy * decal), P(xm, cy + sy * (decal + long_pli)))

    if reperes:
        d = _mm_to_pt(4)  # centre des cibles : 4 mm du bord de la feuille
        rayon, bras = _mm_to_pt(1.6), _mm_to_pt(2.8)
        for cx, cy in ((d, ym), (sheet_w - d, ym), (xm, d), (xm, sheet_h - d)):
            forme.draw_circle(P(cx, cy), rayon)
            forme.draw_line(P(cx - bras, cy), P(cx + bras, cy))
            forme.draw_line(P(cx, cy - bras), P(cx, cy + bras))

    forme.finish(width=0.3, color=(0, 0, 0), fill=None)
    forme.commit()


def impose(input_path: str, output_path: str, format_impression: str,
           taille_signature=None, progress_callback=None,
           traits_coupe=False, reperes=False, espacement_mm=0) -> dict:
    """
    Impose le PDF.
    taille_signature=None : piqure a cheval. Sinon : reliure cousue avec
    des signatures de cette taille.
    Sortie : une page par face de feuille (recto, verso, recto, verso...),
    signature apres signature.
    """
    src = pymupdf.open(input_path)
    try:
        n_src = src.page_count
        p = plan(n_src, format_impression, taille_signature)

        w_mm, h_mm = FORMATS_IMPRESSION[format_impression]["mm"]
        sheet_w, sheet_h = _mm_to_pt(h_mm), _mm_to_pt(w_mm)  # paysage
        avec_marges = traits_coupe or reperes
        if espacement_mm < 0:
            raise ValueError("L'espacement ne peut pas etre negatif")
        k = echelle(format_impression, avec_marges, espacement_mm)
        gouttiere = _mm_to_pt(espacement_mm) * k          # espace entre les deux pages
        bloc_w, bloc_h = (sheet_w + _mm_to_pt(espacement_mm)) * k, sheet_h * k
        bx0, by0 = (sheet_w - bloc_w) / 2, (sheet_h - bloc_h) / 2   # bloc de pages centre
        bloc = (bx0, by0, bx0 + bloc_w, by0 + bloc_h)
        panel_w = (bloc_w - gouttiere) / 2

        out = pymupdf.open()
        decalage = 0  # nombre de pages deja utilisees par les signatures precedentes
        for taille in p["tailles"]:
            for recto, verso in sequence_signature(taille):
                for face in (recto, verso):
                    page = out.new_page(width=sheet_w, height=sheet_h)
                    for col, numero in enumerate(face):
                        absolu = decalage + numero  # 1-indexe
                        if absolu > n_src:
                            continue  # page blanche de complement
                        gauche = bx0 + col * (panel_w + gouttiere)
                        rect = pymupdf.Rect(gauche, by0, gauche + panel_w, by0 + bloc_h)
                        page.show_pdf_page(rect, src, absolu - 1)
                    if avec_marges:
                        _dessiner_reperes(page, sheet_w, sheet_h, bloc, traits_coupe, reperes)
            decalage += taille

        n_faces = out.page_count
        out.save(output_path)
        out.close()
    finally:
        src.close()

    if progress_callback:
        progress_callback(f"{p['n_signatures']} signature(s), {p['n_feuilles']} feuille(s), {n_faces} faces")
    return {**p, "n_faces": n_faces, "echelle": k}
