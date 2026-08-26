Imposition PDF pour cahiers coususv0.2 (interface graphique, pli simple)

Ce qui marche déjà

- **Interface graphique** (`gui.py`) : glisser-déposer du PDF, choix du format
  de feuille, choix du nombre de cahiers souhaité (le logiciel calcule la
  taille de chaque cahier tout seul), bouton "Générer".
- Découpe un PDF en cahiers, complète avec des pages blanches si besoin
- Impose en pli simple (A4→A5 imbriqué, plusieurs feuilles nichées par cahier)
- Sort un PDF prêt à imprimer en recto-verso
- Testé : rendu de l'UI vérifié par capture d'écran, génération testée sur
  un PDF de 16 pages (résultat conforme à la formule saddle-stitch classique)

Je tourne sur un serveur Linux, je ne peux pas fabriquer un exécutable
Windows (.exe) ni Mac (.app) depuis ici . Il faut lancer une seule commande sur Windows
ou Mac pour transformer le script en vrai logiciel double-cliquable.
Une fois fait, tu n'as plus jamais besoin de retoucher à Python : tu
gardes juste le fichier généré.

installer Python 

- Windows : télécharge sur https://www.python.org/downloads/ et coche
  bien "Add Python to PATH" à l'installation.
- Mac : Python est souvent déjà présent (`python3` dans le Terminal),
  sinon même lien que ci-dessus.

 installer les dépendances

Ouvre un terminal (Invite de commandes sur Windows, Terminal sur Mac)
dans le dossier du projet, puis :

```bash
pip install pymupdf tkinterdnd2 pyinstaller
ou py -m pip install pymupdf tkinterdnd2 pyinstaller

```

(sur Mac, utilise parfois `pip3` au lieu de `pip`)

fabriquer l'exécutable

Toujours dans le dossier du projet :

```bash
pyinstaller --onefile --windowed --name ImpositionCahiers gui.py
ou python.exe -m pip install --upgrade pip 
```

Ça va créer un dossier `dist/` avec dedans :
- Windows : `ImpositionCahiers.exe`
- Mac : `ImpositionCahiers` (app empaquetée — si macOS bloque au lancement,
  clic droit → "Ouvrir" la première fois, le temps de passer Gatekeeper)

**C'est ce fichier dans `dist/` qu'il faut désormais garder et partager**
— plus besoin de Python ni de terminal ensuite, double-clic et c'est parti.

Il faut refaire cette étape séparément sur Windows ET sur Mac (un exécutable
Windows ne tourne pas sur Mac et inversement) — mais une fois fait sur
chaque machine, c'est fait pour de bon.

Usage (dans l'appli)

1. Glisser-déposer le PDF (ou cliquer pour choisir un fichier)
2. Choisir le format de la feuille d'impression (A4, A3...)
3. Choisir le nombre de cahiers (signatures) souhaité
4. Cliquer "Générer le PDF imposé", choisir où l'enregistrer

Ce qu'il reste à faire

1. **Plis multiples (in-4, in-8, in-16, in-32)** — le menu "Type de pli"
   n'a qu'une seule option pour l'instant (`fold_1`). On les ajoute un
   par un, chacun vérifié par pliage papier réel avant d'être codé
   (voir `schemes.py` pour le détail).
2. **Marges/fond perdu/traits de coupe** — pas encore gérés.
3. **Repères de cahier** (numérotation dans le dos, utile à la couture)
   — pas encore ajoutés.

## Structure du projet

- `schemes.py` — définit les schémas d'imposition (positions + rotations)
- `impose.py` — moteur : découpage en cahiers + assemblage du PDF de sortie
- `gui.py` — interface graphique (glisser-déposer, formulaire, génération)
