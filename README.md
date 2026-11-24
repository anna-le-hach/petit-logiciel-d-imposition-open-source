# Magouille s'impose (piqûre à cheval, reliure cousue, traits de coupe et repères)

Glisse un PDF, choisis le type de reliure, le format d'impression (et la signature pour la reliure cousue), génère.

## Ce que ça fait

- Type de reliure :
  - Piqûre à cheval : tout le livret en un seul cahier, feuilles imbriquées, pliées une fois
  - Reliure cousue : le livre est découpé en signatures de 4, 8, 12, 16, 20, 24, 28 ou 32 pages
- Format d'impression : A4 (pages A5) ou A3 (pages A4), feuille posée en paysage
- Le format de signature n'est actif que pour la reliure cousue
- La dernière signature est réduite au strict nécessaire (par exemple 16 + 16 + 8), pas de pages blanches inutiles
- Pages blanches à la fin seulement pour arriver à un multiple de 4
- Traits de coupe (un trait à chaque coin des pages + deux traits de pli en haut et en bas) et repères d'impression (quatre cibles au milieu des côtés), en cases à cocher
- Avec l'une de ces cases, une marge de 12 mm est ajoutée autour des pages, qui sont réduites pour y tenir (environ 89 %). Pour garder la taille réelle, imprime sur une feuille plus grande
- Espacement entre les pages : case à cocher + valeur en mm de ton choix (0 à 30), un vide au milieu de la feuille entre les deux pages. Les pages sont réduites si besoin pour que tout tienne
- Sortie : un PDF avec une page par face de feuille (recto, verso, recto, verso...), signature après signature

L'ordre des pages de chaque signature suit le tableau de référence (vérifié pour 4, 8, 12, 16, 20, 24 et 32 pages).

## L'interface

- Grand panneau blanc : dépose le PDF dessus (ou clique), il affiche le nom, le nombre de pages et le calcul des feuilles
- L'oiseau est posé sur les boutons roses, sans cadre. Carré du bas à gauche : aperçu de la première page
- Les quatre boutons roses : le cœur ouvre le dossier du dernier PDF généré, la montagne choisit un PDF, le sourire donne les conseils d'impression, la croix réinitialise
- La grande barre du bas génère le PDF imposé. Quand tu survoles un petit bouton, elle affiche son nom

## Lancer

    pip install pymupdf tkinterdnd2
    python gui.py

## Fabriquer l'appli à double-cliquer

À la main, sur ton ordi :

    python -m pip install -r requirements.txt pyinstaller pillow
    python -m PyInstaller magouille_s_impose.spec --noconfirm

Le résultat est dans `dist/` (`Magouille.exe` sur Windows, `Magouille.app` sur Mac, `Magouille` sur Linux).

Sur GitHub, pour tous les systèmes d'un coup : onglet Actions, « Construire l'appli », Run workflow. Pour publier une version, crée une Release avec un tag `v1.2` (par exemple) : GitHub construit tout et accroche les fichiers à la Release.

## Installer

- Windows : lance le `.exe`. Si « Windows a protégé votre ordinateur » s'affiche, clique sur « Informations complémentaires » puis « Exécuter quand même ».
- Mac : dézippe, glisse l'appli dans Applications, puis clic droit sur l'appli, Ouvrir, et encore Ouvrir (l'appli n'est pas signée par Apple).
- Linux : décompresse le `.tar.gz` et lance `Magouille`.

## Imprimer

Recto verso, à 100 %, retournement sur le bord court (la feuille sort en paysage). Si le verso est à l'envers, essaie le bord long.
En reliure cousue, plie les feuilles d'une signature et glisse-les les unes dans les autres, la première feuille imprimée à l'extérieur.

## Étapes suivantes

Le plan de départ est terminé. Idées : feuille plus grande que le format d'impression pour garder la taille réelle avec les marques, fond perdu, repères de signature pour la couture.

## Fichiers

- `engine.py` : le moteur (signatures, séquence des pages, assemblage du PDF)
- `gui.py` : l'interface
- `icone_data.py` : l'oiseau, rangé dans le code
- `magouille_s_impose.spec` : la recette pour fabriquer l'appli sur chaque système
