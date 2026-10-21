"""
gui.py : interface pixel art du logiciel d'imposition.

Lancer avec :  python gui.py
Dependances :  pip install pymupdf tkinterdnd2
"""

import base64
import os
import subprocess
import sys
import threading
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

import pymupdf

import engine

try:
    from icone_data import ICONE_PNG_BASE64
except ImportError:
    ICONE_PNG_BASE64 = None

PIQURE = "Piqûre à cheval"
COUSUE = "Reliure cousue"
TYPES_RELIURE = [PIQURE, COUSUE]

LABELS_SIGNATURE = [f"{n} pages" for n in engine.TAILLES_SIGNATURE]
SIGNATURE_PAR_DEFAUT = "16 pages"

CONSEIL_IMPRESSION = (
    "Imprime en recto verso, à 100 % (pas « ajuster à la page »), avec retournement "
    "sur le bord court. Si le verso est à l'envers, essaie le bord long."
)
CONSEIL_COUSUE = (
    "Pour chaque signature : plie les feuilles une par une et glisse-les les unes dans les autres, "
    "la première feuille imprimée à l'extérieur."
)

# Palette relevée sur la maquette
BLANC = "#ffffff"
CREME = "#fffde7"
CREME_FONCE = "#f7eadb"
CREME_SURVOL = "#f0dcc8"
BRUN = "#70524f"
BRUN_FONCE = "#603d43"
BRUN_CLAIR = "#d1b8ae"
NOIR_CARRE = "#0b0c06"
ROSE = "#ffd2d4"
ROSE_SURVOL = "#ffbfc4"
ROSE_BORD = "#d9707a"
ROUGE = "#ff4c4a"
TEXTE = "#603d43"
TEXTE_PALE = "#a98c84"
INACTIF_FOND = "#f6ebe8"
INACTIF_BORD = "#d8c4c0"
INACTIF_ICONE = "#e6b8b8"

# Petites icônes pixel (cases pleines = '#')
ICONES = {
    "coeur": [
        ".##.##.",
        "#######",
        "#######",
        ".#####.",
        "..###..",
        "...#...",
    ],
    "image": [
        ".#.......",
        "###..#...",
        ".#..###..",
        "...#####.",
        "..#######",
        "#########",
    ],
    "sourire": [
        "..#####..",
        ".#.....#.",
        "#.......#",
        "#..#.#..#",
        "#.......#",
        "#.#...#.#",
        "#..###..#",
        ".#.....#.",
        "..#####..",
    ],
    "croix": [
        "##...##",
        "###.###",
        ".#####.",
        "..###..",
        ".#####.",
        "###.###",
        "##...##",
    ],
}

# Boutons : nom -> (icône, boîte)
BOUTONS = {
    "coeur": ("coeur", (490, 164, 538, 212)),
    "image": ("image", (546, 164, 594, 212)),
    "sourire": ("sourire", (490, 220, 538, 268)),
    "croix": ("croix", (546, 220, 594, 268)),
}
COCHE = [
    "......#",
    ".....##",
    "#...##.",
    "##.##..",
    ".###...",
    "..#....",
]
# Cases à cocher : nom -> (x, y du centre, libellé, largeur de la zone cliquable)
CASES = {
    "coupe": (66, 454, "Traits de coupe", 200),
    "reperes": (300, 454, "Repères d'impression", 270),
    "espace": (66, 494, "Espacement entre les pages", 270),
}
INDICES = {
    "coeur": "Ouvrir le dossier du dernier PDF",
    "image": "Choisir un PDF",
    "sourire": "Conseils d'impression",
    "croix": "Supprimer le PDF ajouté",
}
BARRE = (150, 554, 594, 646)
ZONE = (46, 46, 478, 276)


def _dans(boite, x, y):
    return boite[0] <= x <= boite[2] and boite[1] <= y <= boite[3]


def _police():
    dispo = set(tkfont.families())
    for nom in ("Courier New", "Courier", "Liberation Mono", "DejaVu Sans Mono", "Consolas"):
        if nom in dispo:
            return nom
    return tkfont.nametofont("TkFixedFont").actual("family")


def _rect_arrondi(c, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Magouille s'impose")
        root.resizable(False, False)

        if ICONE_PNG_BASE64:
            try:
                self._icone = tk.PhotoImage(data=ICONE_PNG_BASE64)  # garder une référence
                root.iconphoto(True, self._icone)
            except tk.TclError:
                pass

        self.police = _police()
        self.n_pages = None
        self.fichier = None
        self.dernier_pdf = None
        self.en_cours = False
        self.survol = None
        self.statut = "Dépose un PDF pour commencer."

        self.type_reliure = tk.StringVar(value=PIQURE)
        self.format_impression = tk.StringVar(value="A4")
        self.signature = tk.StringVar(value=SIGNATURE_PAR_DEFAUT)
        self.coches = {"coupe": False, "reperes": False, "espace": False}
        self.espacement = tk.StringVar(value="5")

        self._construire()
        self._maj_signature()
        self._maj_info()
        self._peindre()

        self.espacement.trace_add("write", lambda *a: self._peindre())
        for var in (self.format_impression, self.type_reliure, self.signature):
            var.trace_add("write", lambda *a: self._maj_signature_et_info())

    # ------------------------------------------------------------ construction

    def _f(self, taille, gras=False):
        return (self.police, taille, "bold") if gras else (self.police, taille)

    def _construire(self):
        c = tk.Canvas(self.root, width=640, height=702, bg=BLANC, highlightthickness=0)
        c.pack()
        self.c = c

        # Fenêtre crème avec petite ombre
        _rect_arrondi(c, 14, 18, 626, 692, 10, fill=BRUN_CLAIR, outline="")
        _rect_arrondi(c, 14, 14, 626, 688, 10, fill=CREME, outline=BRUN_FONCE, width=2)

        # Grand panneau blanc (dépôt du PDF + infos)
        c.create_rectangle(*ZONE, fill=BLANC, outline=BRUN, width=2)
        self.t_vide = c.create_text(262, 161, text="Glisse ton PDF ici\n(ou clique pour parcourir)",
                                    font=self._f(12), fill=TEXTE_PALE, justify="center")
        self.t_nom = c.create_text(66, 64, anchor="nw", text="", font=self._f(13, True), fill=TEXTE)
        self.t_pages = c.create_text(66, 90, anchor="nw", text="", font=self._f(11), fill=TEXTE_PALE)
        self.t_info = c.create_text(66, 126, anchor="nw", text="", font=self._f(11), fill=TEXTE, width=396)

        # Petits boutons roses
        self.b_rect, self.b_pix = {}, {}
        for nom, (icone, (x0, y0, x1, y1)) in BOUTONS.items():
            self.b_rect[nom] = c.create_rectangle(x0, y0, x1, y1, fill=ROSE, outline=ROSE_BORD, width=2)
            bitmap = ICONES[icone]
            cell = 3
            w, h = len(bitmap[0]) * cell, len(bitmap) * cell
            ox, oy = (x0 + x1) // 2 - w // 2, (y0 + y1) // 2 - h // 2
            ids = []
            for j, ligne in enumerate(bitmap):
                for i, ch in enumerate(ligne):
                    if ch == "#":
                        ids.append(c.create_rectangle(ox + i * cell, oy + j * cell,
                                                      ox + (i + 1) * cell, oy + (j + 1) * cell,
                                                      fill=ROUGE, outline=""))
            self.b_pix[nom] = ids

        # Panneau des réglages
        c.create_rectangle(46, 292, 594, 540, fill=BLANC, outline=BRUN, width=2)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Pixel.TCombobox", fieldbackground="#fffdf9", background=ROSE, foreground=TEXTE,
                        bordercolor=BRUN, lightcolor="#fffdf9", darkcolor="#fffdf9", arrowcolor=ROUGE,
                        padding=5)
        style.map("Pixel.TCombobox",
                  fieldbackground=[("readonly", "#fffdf9"), ("disabled", INACTIF_FOND)],
                  foreground=[("disabled", TEXTE_PALE)],
                  background=[("disabled", INACTIF_FOND)],
                  selectbackground=[("readonly", "#fffdf9")],
                  selectforeground=[("readonly", TEXTE)])
        self.root.option_add("*TCombobox*Listbox.font", self._f(11))
        self.root.option_add("*TCombobox*Listbox.background", "#fffdf9")
        self.root.option_add("*TCombobox*Listbox.foreground", TEXTE)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ROSE)
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXTE)

        lignes = [
            ("Type de reliure :", self.type_reliure, TYPES_RELIURE, 320),
            ("Format d'impression :", self.format_impression, list(engine.FORMATS_IMPRESSION), 362),
            ("Format de signature :", self.signature, LABELS_SIGNATURE, 404),
        ]
        self.labels_reglages = []
        self.combos = []
        for texte, var, valeurs, y in lignes:
            self.labels_reglages.append(c.create_text(66, y, anchor="w", text=texte,
                                                      font=self._f(11, True), fill=TEXTE))
            combo = ttk.Combobox(self.root, textvariable=var, values=valeurs, state="readonly",
                                 style="Pixel.TCombobox", font=self._f(11))
            c.create_window(290, y, window=combo, width=284, anchor="w")
            self.combos.append(combo)
        self.combo_signature = self.combos[2]

        # Cases à cocher (traits de coupe, repères d'impression)
        self.case_rect, self.case_pix = {}, {}
        for nom, (x, y, texte, _) in CASES.items():
            self.case_rect[nom] = c.create_rectangle(x, y - 12, x + 24, y + 12, fill="#fffdf9",
                                                     outline=BRUN, width=2)
            ids = []
            ox, oy = x + 12 - 10, y - 9
            for j, ligne in enumerate(COCHE):
                for i, ch in enumerate(ligne):
                    if ch == "#":
                        ids.append(c.create_rectangle(ox + i * 3, oy + j * 3, ox + i * 3 + 3, oy + j * 3 + 3,
                                                      fill=ROUGE, outline="", state="hidden"))
            self.case_pix[nom] = ids
            c.create_text(x + 36, y, anchor="w", text=texte, font=self._f(11, True), fill=TEXTE)
        self.champ_espace = tk.Entry(self.root, textvariable=self.espacement, width=5, justify="center",
                                     font=self._f(11), bg="#fffdf9", fg=TEXTE, relief="flat",
                                     highlightthickness=2, highlightbackground=BRUN, highlightcolor=ROSE_BORD,
                                     disabledbackground=INACTIF_FOND, disabledforeground=TEXTE_PALE,
                                     insertbackground=TEXTE)
        c.create_window(352, 494, window=self.champ_espace, width=64, height=28, anchor="w")
        self.t_mm = c.create_text(426, 494, anchor="w", text="mm", font=self._f(11, True), fill=TEXTE_PALE)
        self.t_marques = c.create_text(66, 522, anchor="w", text="", font=self._f(9), fill=TEXTE_PALE)

        # Carré de l'aperçu (première page)
        c.create_rectangle(46, 554, 138, 646, fill=BLANC, outline=NOIR_CARRE, width=2)
        self.i_apercu = c.create_image(92, 600, state="hidden")
        self._apercu = None

        # Barre du bas : bouton Générer + statut
        self.r_barre = c.create_rectangle(*BARRE, fill=CREME_FONCE, outline="#996f63", width=2)
        self.t_barre1 = c.create_text(372, 586, text="Générer le PDF imposé", font=self._f(15, True), fill=TEXTE)
        self.t_barre2 = c.create_text(372, 618, text="", font=self._f(11), fill=TEXTE_PALE)

        # L'oiseau, sans cadre, debout sur les boutons roses : son bec dépasse un peu
        # sur le cadre du grand panneau. Créé en dernier pour passer au premier plan.
        # (l image fait 100 x 100, l oiseau occupe x 16..96 et y 15..78 ; zoom x2 = pixels nets)
        if ICONE_PNG_BASE64:
            self._oiseau = tk.PhotoImage(data=ICONE_PNG_BASE64).zoom(2)
            c.create_image(438, 14, image=self._oiseau, anchor="nw")

        # Souris et glisser-déposer
        c.bind("<Motion>", self._bouger)
        c.bind("<Leave>", lambda e: self._survoler(None))
        c.bind("<Button-1>", self._cliquer)
        if HAS_DND:
            c.drop_target_register(DND_FILES)
            c.dnd_bind("<<Drop>>", self._deposer)
        else:
            c.itemconfig(self.t_vide, text="Clique pour choisir un PDF\n(glisser-déposer indisponible)")

    # ------------------------------------------------------------------ etats

    def _espacement(self):
        """Espacement choisi en mm, ou None si la valeur est invalide."""
        try:
            v = float(self.espacement.get().replace(",", ".").strip())
        except ValueError:
            return None
        return v if 0 <= v <= 30 else None

    def _taille_signature(self):
        if self.type_reliure.get() == COUSUE:
            return int(self.signature.get().split()[0])
        return None

    def _actif(self, nom):
        if nom == "coeur":
            return self.dernier_pdf is not None
        if nom in ("croix", "generer"):
            return self.fichier is not None and not self.en_cours
        if nom in ("image", "zone") or nom.startswith("case_"):
            return not self.en_cours
        return True  # sourire

    def _zone_sous(self, x, y):
        for nom, (_, boite) in BOUTONS.items():
            if _dans(boite, x, y):
                return nom
        for nom, (cx, cy, _, larg) in CASES.items():
            if _dans((cx, cy - 14, cx + larg, cy + 14), x, y):
                return "case_" + nom
        if _dans(BARRE, x, y):
            return "generer"
        if _dans(ZONE, x, y):
            return "zone"
        return None

    def _bouger(self, e):
        self._survoler(self._zone_sous(e.x, e.y))

    def _survoler(self, nom):
        if nom != self.survol:
            self.survol = nom
            self._peindre()
        self.c.config(cursor="hand2" if nom and self._actif(nom) else "")

    def _peindre(self):
        c = self.c
        for nom in BOUTONS:
            actif = self._actif(nom)
            survol = actif and self.survol == nom
            if not actif:
                fond, bord, icone = INACTIF_FOND, INACTIF_BORD, INACTIF_ICONE
            else:
                fond, bord, icone = (ROSE_SURVOL if survol else ROSE), ROSE_BORD, ROUGE
            c.itemconfig(self.b_rect[nom], fill=fond, outline=bord)
            for i in self.b_pix[nom]:
                c.itemconfig(i, fill=icone)

        for nom in CASES:
            coche = self.coches[nom]
            survol = self.survol == "case_" + nom
            c.itemconfig(self.case_rect[nom], fill=ROSE if coche else (ROSE_SURVOL if survol else "#fffdf9"),
                         outline=ROSE_BORD if coche or survol else BRUN)
            for i in self.case_pix[nom]:
                c.itemconfig(i, state="normal" if coche else "hidden")
        esp_on = self.coches["espace"]
        self.champ_espace.config(state="normal" if esp_on else "disabled")
        c.itemconfig(self.t_mm, fill=TEXTE if esp_on else TEXTE_PALE)
        marges = self.coches["coupe"] or self.coches["reperes"]
        esp = self._espacement() if esp_on else 0
        if esp is None:
            texte = "Espacement invalide : entre un nombre en mm (de 0 à 30)."
        elif marges or esp:
            k = engine.echelle(self.format_impression.get(), marges, esp)
            texte = f"Pages réduites à {round(k * 100)} % pour que tout tienne sur la feuille." if k < 0.9995 else ""
        else:
            texte = ""
        c.itemconfig(self.t_marques, text=texte, fill=ROUGE if esp is None else TEXTE_PALE)

        actif = self._actif("generer")
        c.itemconfig(self.r_barre, fill=(CREME_SURVOL if actif and self.survol == "generer"
                                         else CREME_FONCE if actif else "#fbf5ec"))
        c.itemconfig(self.t_barre1, fill=TEXTE if actif else TEXTE_PALE)
        indice = INDICES.get(self.survol) if self.survol in BOUTONS else None
        c.itemconfig(self.t_barre2, text=indice or self.statut)

    def _definir_statut(self, texte):
        self.statut = texte
        self._peindre()

    def _maj_signature(self):
        cousue = self.type_reliure.get() == COUSUE
        self.combo_signature.state(["!disabled"] if cousue else ["disabled"])
        self.c.itemconfig(self.labels_reglages[2], fill=TEXTE if cousue else TEXTE_PALE)

    def _maj_info(self):
        c = self.c
        if not self.n_pages:
            c.itemconfig(self.t_vide, state="normal")
            for t in (self.t_nom, self.t_pages, self.t_info):
                c.itemconfig(t, text="")
            return
        c.itemconfig(self.t_vide, state="hidden")
        nom = os.path.basename(self.fichier)
        c.itemconfig(self.t_nom, text=nom if len(nom) <= 34 else nom[:31] + "...")
        c.itemconfig(self.t_pages, text=f"{self.n_pages} pages")

        p = engine.plan(self.n_pages, self.format_impression.get(), self._taille_signature())
        fmt = self.format_impression.get()
        if self.type_reliure.get() == PIQURE:
            texte = f"{p['n_feuilles']} feuille(s) {fmt} imbriquées, livret en pages {p['page_finale']}."
        else:
            detail = ", ".join(f"{n} de {t} pages" for t, n in sorted(p["repartition"].items(), reverse=True))
            texte = (f"{p['n_signatures']} signature(s) ({detail}), {p['n_feuilles']} feuille(s) {fmt} "
                     f"au total, pages {p['page_finale']}.")
        if p["n_blanches"]:
            texte += (f"\n\n{p['n_blanches']} page(s) blanche(s) ajoutée(s) à la fin "
                      f"pour arriver à {p['n_pages_total']} pages (multiple de 4).")
        c.itemconfig(self.t_info, text=texte)

    def _maj_signature_et_info(self):
        self._maj_signature()
        self._maj_info()
        self._peindre()

    # ---------------------------------------------------------------- actions

    def _cliquer(self, e):
        nom = self._zone_sous(e.x, e.y)
        if not nom or not self._actif(nom):
            return
        if nom.startswith("case_"):
            cle = nom[5:]
            self.coches[cle] = not self.coches[cle]
            self._peindre()
            return
        {"coeur": self._ouvrir_dossier, "image": self._choisir, "zone": self._choisir,
         "sourire": self._conseils, "croix": self._reinitialiser, "generer": self._generer}[nom]()

    def _deposer(self, event):
        chemins = self.root.tk.splitlist(event.data)
        if chemins and not self.en_cours:
            self._charger(chemins[0])

    def _choisir(self):
        chemin = filedialog.askopenfilename(title="Choisir un PDF", filetypes=[("PDF", "*.pdf")])
        if chemin:
            self._charger(chemin)

    def _charger(self, chemin):
        if not chemin.lower().endswith(".pdf") or not os.path.isfile(chemin):
            messagebox.showerror("Fichier invalide", "Merci de choisir un fichier PDF.")
            return
        try:
            doc = pymupdf.open(chemin)
            n = doc.page_count
            if n == 0:
                doc.close()
                messagebox.showerror("PDF vide", "Ce PDF ne contient aucune page.")
                return
            r = doc[0].rect
            zoom = min(84 / r.width, 84 / r.height)
            png = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).tobytes("png")
            doc.close()
        except Exception as e:
            messagebox.showerror("Erreur de lecture", f"Impossible d'ouvrir ce PDF :\n{e}")
            return

        self.fichier, self.n_pages = chemin, n
        nouveau = tk.PhotoImage(data=base64.b64encode(png))
        self.c.itemconfig(self.i_apercu, image=nouveau, state="normal")
        self._apercu = nouveau  # garder une référence (sinon l'image disparaît)
        self._maj_info()
        self._definir_statut("Prêt.")

    def _reinitialiser(self):
        self.fichier, self.n_pages = None, None
        self.c.itemconfig(self.i_apercu, image="", state="hidden")
        self._apercu = None
        self._maj_info()
        self._definir_statut("Dépose un PDF pour commencer.")

    def _conseils(self):
        messagebox.showinfo("Conseils d'impression", f"{CONSEIL_IMPRESSION}\n\n{CONSEIL_COUSUE}")

    def _ouvrir_dossier(self):
        if not self.dernier_pdf:
            return
        dossier = os.path.dirname(self.dernier_pdf)
        try:
            if sys.platform.startswith("win"):
                os.startfile(dossier)
            elif sys.platform == "darwin":
                subprocess.run(["open", dossier], check=False)
            else:
                subprocess.run(["xdg-open", dossier], check=False)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier :\n{e}")

    def _generer(self):
        if not self.fichier:
            return
        if self.coches["espace"] and self._espacement() is None:
            messagebox.showerror("Espacement invalide", "Entre un nombre en mm, de 0 à 30 (par exemple 5).")
            return
        cousue = self.type_reliure.get() == COUSUE
        nom = os.path.splitext(os.path.basename(self.fichier))[0] + ("_cousue" if cousue else "_piqure") + ".pdf"
        sortie = filedialog.asksaveasfilename(title="Enregistrer le PDF imposé sous...",
                                              initialfile=nom, defaultextension=".pdf",
                                              filetypes=[("PDF", "*.pdf")])
        if not sortie:
            return

        entree, fmt, taille = self.fichier, self.format_impression.get(), self._taille_signature()
        coupe, reperes = self.coches["coupe"], self.coches["reperes"]
        espace = self._espacement() if self.coches["espace"] else 0
        self.en_cours = True
        self._definir_statut("Génération en cours...")

        def travail():
            try:
                res = engine.impose(entree, sortie, fmt, taille, traits_coupe=coupe, reperes=reperes, espacement_mm=espace)
                self.root.after(0, self._succes, sortie, res, fmt, cousue)
            except Exception as e:
                traceback.print_exc()
                self.root.after(0, self._echec, str(e))

        threading.Thread(target=travail, daemon=True).start()

    def _succes(self, sortie, res, fmt, cousue):
        self.en_cours = False
        self.dernier_pdf = sortie
        self._definir_statut("Terminé. Le cœur ouvre le dossier.")
        message = (f"{res['n_signatures']} signature(s), {res['n_feuilles']} feuille(s) {fmt}, "
                   f"{res['n_faces']} faces.\n\n{sortie}\n\n{CONSEIL_IMPRESSION}")
        if cousue:
            message += f"\n\n{CONSEIL_COUSUE}"
        if res["echelle"] < 0.9995:
            message += (f"\n\nAttention : pour que tout tienne sur la feuille, les pages sont réduites à "
                        f"{round(res['echelle'] * 100)} %. Pour garder la taille réelle, "
                        "imprime sur une feuille plus grande.")
        messagebox.showinfo("Terminé", message)

    def _echec(self, message):
        self.en_cours = False
        self._definir_statut("Erreur pendant la génération.")
        messagebox.showerror("Erreur", message)


def main():
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
