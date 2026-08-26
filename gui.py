"""
gui.py 

Lancer avec :
    python3 gui.py

Dépendances :
    pip install pymupdf tkinterdnd2
"""

import os
import threading
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

from impose import impose, PAPER_SIZES_MM
from schemes import SCHEMES

import pymupdf


class ImpositionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Imposition cahiers cousus")
        self.root.geometry("560x520")
        self.root.minsize(520, 480)

        self.input_path = tk.StringVar(value="")
        self.sheet_format = tk.StringVar(value="A4")
        self.scheme_name = tk.StringVar(value="fold_1")
        self.n_signatures = tk.StringVar(value="1")
        self.status_text = tk.StringVar(value="Dépose un PDF ci-dessous pour commencer.")
        self.page_count_text = tk.StringVar(value="")

        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        title = ttk.Label(self.root, text="Imposition PDF — cahiers cousus", font=("TkDefaultFont", 14, "bold"))
        title.pack(anchor="w", **pad)

        # Zone de dépôt du PDF
        self.drop_frame = tk.Frame(self.root, bg="#e8e8e8", height=110, highlightbackground="#999",
                                    highlightthickness=1)
        self.drop_frame.pack(fill="x", padx=12, pady=6)
        self.drop_frame.pack_propagate(False)

        self.drop_label = tk.Label(
            self.drop_frame,
            text="Glisse ton PDF ici\n(ou clique pour parcourir)",
            bg="#e8e8e8", fg="#444", font=("TkDefaultFont", 11), justify="center",
        )
        self.drop_label.pack(expand=True)
        self.drop_label.bind("<Button-1>", lambda e: self._browse_file())
        self.drop_frame.bind("<Button-1>", lambda e: self._browse_file())

        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self.drop_label.config(text="Clique pour choisir un PDF\n(glisser-déposer indisponible sur ce poste)")

        ttk.Label(self.root, textvariable=self.page_count_text, foreground="#555").pack(anchor="w", padx=12)

        # Format papier
        form = ttk.Frame(self.root)
        form.pack(fill="x", **pad)

        ttk.Label(form, text="Format de la feuille d'impression :").grid(row=0, column=0, sticky="w", pady=4)
        sheet_combo = ttk.Combobox(form, textvariable=self.sheet_format, values=list(PAPER_SIZES_MM.keys()),
                                    state="readonly", width=12)
        sheet_combo.grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(form, text="Type de pli :").grid(row=1, column=0, sticky="w", pady=4)
        scheme_combo = ttk.Combobox(form, textvariable=self.scheme_name, values=list(SCHEMES.keys()),
                                     state="readonly", width=12)
        scheme_combo.grid(row=1, column=1, sticky="w", padx=8)
        ttk.Label(form, text="(seul le pli simple est dispo pour l'instant)",
                  foreground="#888", font=("TkDefaultFont", 8)).grid(row=1, column=2, sticky="w")

        ttk.Label(form, text="Nombre de cahiers (signatures) souhaité :").grid(row=2, column=0, sticky="w", pady=4)
        n_sig_spin = ttk.Spinbox(form, from_=1, to=200, textvariable=self.n_signatures, width=10)
        n_sig_spin.grid(row=2, column=1, sticky="w", padx=8)

        form.columnconfigure(2, weight=1)

        # Estimation en direct
        self.estimate_text = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.estimate_text, foreground="#333").pack(anchor="w", padx=12, pady=(4, 0))

        for var in (self.n_signatures, self.scheme_name):
            var.trace_add("write", lambda *a: self._update_estimate())

        # Bouton générer
        self.generate_btn = ttk.Button(self.root, text="Générer le PDF imposé", command=self._on_generate)
        self.generate_btn.pack(pady=16)
        self.generate_btn.state(["disabled"])

        # Statut
        ttk.Separator(self.root).pack(fill="x", padx=12, pady=(4, 8))
        status_label = ttk.Label(self.root, textvariable=self.status_text, wraplength=520, foreground="#333")
        status_label.pack(anchor="w", padx=12, pady=4)

        if not HAS_DND:
            note = ttk.Label(
                self.root,
                text="Note : glisser-déposer indisponible (tkinterdnd2 non installé) — utilise le bouton parcourir.",
                foreground="#a55", wraplength=520,
            )
            note.pack(anchor="w", padx=12, pady=(0, 8))

    # -------------------------------------------------------------- events

    def _on_drop(self, event):
        path = event.data.strip("{}")  # tkdnd entoure parfois le chemin d'accolades
        self._set_input_file(path)

    def _browse_file(self):
        path = filedialog.askopenfilename(title="Choisir un PDF", filetypes=[("PDF", "*.pdf")])
        if path:
            self._set_input_file(path)

    def _set_input_file(self, path):
        if not path.lower().endswith(".pdf"):
            messagebox.showerror("Fichier invalide", "Merci de choisir un fichier .pdf")
            return
        if not os.path.isfile(path):
            messagebox.showerror("Fichier introuvable", f"Introuvable : {path}")
            return
        try:
            doc = pymupdf.open(path)
            n_pages = doc.page_count
            doc.close()
        except Exception as e:
            messagebox.showerror("Erreur de lecture", f"Impossible d'ouvrir ce PDF :\n{e}")
            return

        self.input_path.set(path)
        self.page_count_text.set(f"Fichier : {os.path.basename(path)}  —  {n_pages} pages")
        self.drop_label.config(text=os.path.basename(path))
        self.generate_btn.state(["!disabled"])
        self._n_pages_src = n_pages
        self._update_estimate()

    def _update_estimate(self):
        if not getattr(self, "_n_pages_src", None):
            return
        try:
            n_sig = int(self.n_signatures.get())
            if n_sig < 1:
                raise ValueError
        except ValueError:
            self.estimate_text.set("Nombre de cahiers invalide.")
            return

        from impose import pages_per_cahier_from_n_signatures
        pages_per_sheet = 4  # pli simple, seul schéma dispo
        pages_par_cahier = pages_per_cahier_from_n_signatures(self._n_pages_src, n_sig, pages_per_sheet)
        n_feuilles = pages_par_cahier // pages_per_sheet
        total_avec_blancs = pages_par_cahier * n_sig
        blancs = total_avec_blancs - self._n_pages_src
        self.estimate_text.set(
            f"→ {n_sig} cahier(s) de {pages_par_cahier} pages ({n_feuilles} feuille(s) {self.sheet_format.get()} "
            f"imbriquée(s) par cahier), {blancs} page(s) blanche(s) ajoutée(s)."
        )

    def _on_generate(self):
        input_path = self.input_path.get()
        if not input_path:
            return
        try:
            n_sig = int(self.n_signatures.get())
        except ValueError:
            messagebox.showerror("Erreur", "Nombre de cahiers invalide.")
            return

        default_name = os.path.splitext(os.path.basename(input_path))[0] + "_impose.pdf"
        output_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF imposé sous...",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not output_path:
            return

        self.generate_btn.state(["disabled"])
        self.status_text.set("Génération en cours...")

        def worker():
            try:
                result = impose(
                    input_path,
                    output_path,
                    self.sheet_format.get(),
                    pages_per_sheet=4,
                    n_signatures=n_sig,
                    scheme_name=self.scheme_name.get(),
                    progress_callback=lambda m: self.root.after(0, self.status_text.set, m),
                )
                self.root.after(0, self._on_success, output_path, result)
            except Exception as e:
                traceback.print_exc()
                self.root.after(0, self._on_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, output_path, result):
        self.generate_btn.state(["!disabled"])
        self.status_text.set(f"Terminé : {output_path}")
        messagebox.showinfo(
            "Terminé",
            f"PDF imposé généré :\n{output_path}\n\n"
            f"{result['n_cahiers']} cahier(s) de {result['pages_per_cahier']} pages "
            f"({result['n_faces']} faces de feuille au total).",
        )

    def _on_error(self, error_msg):
        self.generate_btn.state(["!disabled"])
        self.status_text.set("Erreur pendant la génération.")
        messagebox.showerror("Erreur", error_msg)


def main():
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    app = ImpositionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
