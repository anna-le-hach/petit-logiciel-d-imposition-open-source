"""
impose.py — Moteur d'imposition PDF pour cahiers cousus.

Usage (ligne de commande, pour l'instant — l'UI viendra ensuite) :

    python3 impose.py mon_livre.pdf sortie.pdf \
        --sheet-format A4 \
        --pages-per-sheet 16 \
        --sheets-per-cahier 1

- mon_livre.pdf : le PDF en ordre de lecture normal (page 1, 2, 3...)
- --sheet-format : format de la feuille d'impression (A4, A3, Letter...)
- --pages-per-sheet : nb de pages du cahier obtenu par UNE feuille pliée
  (4 pour un pli simple, 8/16/32 pour les plis multiples — pas encore
  implémentés, voir schemes.py)
- --sheets-per-cahier : nb de feuilles imbriquées par cahier (pli simple
  uniquement — pour empiler plusieurs feuilles A4 pliées en un seul
  cahier avant couture, comme dans le script InDesign)

Le PDF de sortie contient une page par face de feuille imprimée
(recto, verso, recto, verso...), prête à envoyer en impression recto-verso.
"""

import argparse
import sys

import pymupdf

from schemes import SCHEMES, fold_1_scheme

PAPER_SIZES_MM = {
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "A6": (105, 148),
    "LETTER": (215.9, 279.4),
}

MM_TO_PT = 72 / 25.4


def mm_to_pt(mm: float) -> float:
    return mm * MM_TO_PT


def build_cahiers(n_pages_total: int, pages_per_cahier: int):
    """
    Découpe n_pages_total en cahiers de pages_per_cahier pages, en
    complétant le dernier cahier avec des pages blanches si besoin.

    Retourne (n_cahiers, n_pages_avec_blancs).
    """
    import math

    n_cahiers = math.ceil(n_pages_total / pages_per_cahier)
    n_pages_avec_blancs = n_cahiers * pages_per_cahier
    return n_cahiers, n_pages_avec_blancs


def pages_per_cahier_from_n_signatures(n_pages_src: int, n_signatures: int, pages_per_sheet: int) -> int:
    """
    Étant donné un nombre de pages source et un nombre de cahiers
    (signatures) souhaité, calcule combien de pages doit faire chaque
    cahier (arrondi au multiple de pages_per_sheet supérieur, pour que
    chaque cahier corresponde à un nombre entier de feuilles pliées).
    """
    import math

    if n_signatures < 1:
        raise ValueError("Le nombre de cahiers doit être >= 1")
    brut = math.ceil(n_pages_src / n_signatures)
    # arrondi au multiple de pages_per_sheet supérieur
    pages_par_cahier = math.ceil(brut / pages_per_sheet) * pages_per_sheet
    return max(pages_par_cahier, pages_per_sheet)


def impose(
    input_path: str,
    output_path: str,
    sheet_format: str,
    pages_per_sheet: int,
    sheets_per_cahier: int = None,
    n_signatures: int = None,
    scheme_name: str = "fold_1",
    progress_callback=None,
):
    """
    Impose un PDF en cahiers.

    Fournir SOIT sheets_per_cahier (taille de cahier fixe, comme avant),
    SOIT n_signatures (nombre de cahiers souhaité — la taille de chaque
    cahier est calculée automatiquement).
    """
    if scheme_name not in SCHEMES:
        raise ValueError(
            f"Schéma '{scheme_name}' pas encore implémenté. "
            f"Disponibles : {list(SCHEMES.keys())}"
        )
    if (sheets_per_cahier is None) == (n_signatures is None):
        raise ValueError("Fournir soit sheets_per_cahier, soit n_signatures (l'un des deux, pas les deux).")

    src = pymupdf.open(input_path)
    n_pages_src = src.page_count

    if n_signatures is not None:
        pages_per_cahier = pages_per_cahier_from_n_signatures(n_pages_src, n_signatures, pages_per_sheet)
    else:
        pages_per_cahier = pages_per_sheet * sheets_per_cahier

    n_cahiers, n_pages_total = build_cahiers(n_pages_src, pages_per_cahier)

    msg = (f"{n_pages_src} pages sources -> {n_cahiers} cahier(s) "
           f"de {pages_per_cahier} pages ({n_pages_total - n_pages_src} page(s) "
           f"blanche(s) ajoutée(s) à la fin)")
    print(f"[info] {msg}")
    if progress_callback:
        progress_callback(msg)

    # Le schéma décrit tout le cahier (P pages, imbrication de plusieurs
    # feuilles pour un pli simple), pas une seule feuille.
    scheme = SCHEMES[scheme_name](pages_per_cahier)
    cols, rows = scheme["grid"]

    sheet_w_mm, sheet_h_mm = PAPER_SIZES_MM[sheet_format.upper()]
    sheet_w_pt, sheet_h_pt = mm_to_pt(sheet_w_mm), mm_to_pt(sheet_h_mm)
    panel_w_pt = sheet_w_pt / cols
    panel_h_pt = sheet_h_pt / rows

    out = pymupdf.open()

    def get_source_page_number(cahier_index: int, page_number_in_cahier: int):
        """Convertit un numéro de page 'dans le cahier' (1..N) en numéro
        de page absolu dans le document source (0-indexé), ou None si
        c'est une page blanche de complément."""
        absolute = cahier_index * pages_per_cahier + (page_number_in_cahier - 1)
        if absolute >= n_pages_src:
            return None
        return absolute

    for cahier_index in range(n_cahiers):
        # On regroupe les slots par (sheet_index, side) pour générer une
        # page de sortie par face de feuille imprimée.
        by_sheet = {}
        for sheet_index, slot in scheme["slots"]:
            by_sheet.setdefault(sheet_index, {}).setdefault(slot.side, []).append(slot)

        for sheet_index in sorted(by_sheet.keys()):
            for side in ("recto", "verso"):
                slots = by_sheet[sheet_index].get(side, [])
                out_page = out.new_page(width=sheet_w_pt, height=sheet_h_pt)
                for slot in slots:
                    src_page_no = get_source_page_number(cahier_index, slot.page_number)
                    x0 = slot.col * panel_w_pt
                    y0 = slot.row * panel_h_pt
                    rect = pymupdf.Rect(x0, y0, x0 + panel_w_pt, y0 + panel_h_pt)
                    if src_page_no is None:
                        continue  # page blanche : on laisse le panneau vide
                    out_page.show_pdf_page(
                        rect, src, src_page_no, rotate=slot.rotation
                    )

    n_faces = out.page_count
    out.save(output_path)
    out.close()
    src.close()
    final_msg = f"écrit : {output_path} ({n_faces} faces de feuille, {n_cahiers} cahier(s))"
    print(f"[ok] {final_msg}")
    if progress_callback:
        progress_callback(final_msg)
    return {"n_cahiers": n_cahiers, "pages_per_cahier": pages_per_cahier, "n_faces": n_faces}


def main():
    parser = argparse.ArgumentParser(description="Impose un PDF en cahiers pour reliure cousue.")
    parser.add_argument("input_pdf")
    parser.add_argument("output_pdf")
    parser.add_argument("--sheet-format", default="A4", choices=list(PAPER_SIZES_MM.keys()))
    parser.add_argument("--pages-per-sheet", type=int, default=4,
                         help="4 = pli simple (in-2). Autres valeurs pas encore supportées.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sheets-per-cahier", type=int,
                        help="Nombre de feuilles imbriquées par cahier (taille de cahier fixe).")
    group.add_argument("--n-signatures", type=int,
                        help="Nombre de cahiers souhaité (la taille de chaque cahier est calculée).")
    parser.add_argument("--scheme", default="fold_1")
    args = parser.parse_args()

    impose(
        args.input_pdf,
        args.output_pdf,
        args.sheet_format,
        args.pages_per_sheet,
        sheets_per_cahier=args.sheets_per_cahier,
        n_signatures=args.n_signatures,
        scheme_name=args.scheme,
    )


if __name__ == "__main__":
    main()
