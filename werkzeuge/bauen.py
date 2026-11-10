"""Baut die Seite «3D-Ansichten» (GitHub Pages) aus den verschluesselten Quellen in quelle/.
Aufruf (auf GitHub im Ablauf .github/workflows/seite.yml):  python werkzeuge/bauen.py _site
- quelle/*.bin sind mit dem Uebertragungsschluessel verschluesselt (Geheimnis DREID_SCHLUESSEL, 64 Hex-Zeichen).
  Hier werden sie entschluesselt und mit dem Passwort neu verschluesselt (Geheimnis DREID_PASSWORT, mindestens 12 Zeichen).
- Oeffentlich liegen nur verschluesselte Dateien: ohne Passwort ist weder ein Modell noch ein Objektname lesbar.
- Format beider Stufen: 4 Zeichen Kennung + 12 Byte IV + AES-GCM(gzip(Inhalt)); Passwort-Schluessel per PBKDF2-SHA256.
"""
import hashlib, json, os, shutil, sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

hier = os.path.dirname(os.path.abspath(__file__)); oben = os.path.dirname(hier)
SALZ = hashlib.sha256(b"3d-ansichten salzgeber").digest()[:16]   # fest, damit der gespeicherte Schluessel nach Updates gilt
RUNDEN = 600_000

def main(ziel):
    pw = os.environ.get("DREID_PASSWORT", "")
    k = os.environ.get("DREID_SCHLUESSEL", "").strip()
    if len(pw) < 12: sys.exit("Kein Passwort (mindestens 12 Zeichen) - nichts gebaut.")
    if len(k) != 64: sys.exit("Kein Uebertragungsschluessel - nichts gebaut.")
    transport = AESGCM(bytes.fromhex(k))
    pwschluessel = AESGCM(PBKDF2HMAC(hashes.SHA256(), 32, SALZ, RUNDEN).derive(pw.encode("utf-8")))

    def umschluesseln(name):
        d = open(os.path.join(oben, "quelle", name), "rb").read()
        assert d[:4] == b"DRK1", name + ": unbekanntes Format"
        roh = transport.decrypt(d[4:16], d[16:], None)            # gzip-Daten
        iv = os.urandom(12)
        return b"DRA1" + iv + pwschluessel.encrypt(iv, roh, None)

    if os.path.isdir(ziel): shutil.rmtree(ziel)
    shutil.copytree(os.path.join(oben, "web"), ziel)
    import gzip
    liste_bin = open(os.path.join(oben, "quelle", "liste.bin"), "rb").read()
    liste = json.loads(gzip.decompress(transport.decrypt(liste_bin[4:16], liste_bin[16:], None)))
    dateien = ["./", "liste.dat", "manifest.webmanifest", "symbol-180.png", "symbol-192.png", "symbol-512.png"]
    pruef = hashlib.sha256()
    open(os.path.join(ziel, "liste.dat"), "wb").write(umschluesseln("liste.bin"))
    for e in liste:
        quelle = e["datei"].replace(".dat", ".bin")
        daten = umschluesseln(quelle)
        pruef.update(open(os.path.join(oben, "quelle", quelle), "rb").read())
        open(os.path.join(ziel, e["datei"]), "wb").write(daten)
        dateien.append(e["datei"])
        for p in e.get("plaene", []):                                # Plaene (PDF): nicht vorab gespeichert, erst beim Oeffnen
            q = p["datei"].replace(".dat", ".bin")
            pruef.update(open(os.path.join(oben, "quelle", q), "rb").read())
            open(os.path.join(ziel, p["datei"]), "wb").write(umschluesseln(q))
    pruef.update(liste_bin)
    stand = pruef.hexdigest()[:10]
    for name, ersatz in (("index.html", {"__SALZ__": SALZ.hex(), "__RUNDEN__": str(RUNDEN)}),
                         ("sw.js", {"__STAND__": stand, "__DATEIEN__": json.dumps(dateien)})):
        p = os.path.join(ziel, name); t = open(p, encoding="utf-8").read()
        for alt, neu in ersatz.items():
            assert alt in t, f"{alt} fehlt in {name}"
            t = t.replace(alt, neu)
        open(p, "w", encoding="utf-8", newline="\n").write(t)
    open(os.path.join(ziel, ".nojekyll"), "w").close()
    print(f"Seite gebaut: {len(liste)} Ansichten, {sum(len(e.get('plaene', [])) for e in liste)} Plaene, Stand {stand}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(oben, "_site"))
