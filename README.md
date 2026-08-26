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
