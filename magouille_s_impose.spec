# -*- mode: python ; coding: utf-8 -*-
# Construire : pyinstaller magouille_s_impose.spec --noconfirm
# Marche sur Windows, Mac et Linux (chacun construit sa version).
# Le glisser-déposer (tkinterdnd2) est pris en charge par le hook de pyinstaller-hooks-contrib.
import sys

a = Analysis(
    ["gui.py"],
    hiddenimports=["tkinterdnd2", "icone_data"],
    excludes=["numpy", "matplotlib"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Magouille", console=False, icon="oiseau.png")
    coll = COLLECT(exe, a.binaries, a.datas, name="Magouille")
    app = BUNDLE(coll, name="Magouille.app", icon="oiseau.png", bundle_identifier="fr.magouille.simpose",
                 info_plist={"NSHighResolutionCapable": True, "CFBundleDisplayName": "Magouille s'impose"})
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Magouille", console=False, upx=False,
              icon="icone.ico" if sys.platform == "win32" else None)
