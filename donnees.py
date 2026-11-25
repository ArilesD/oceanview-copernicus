"""Récupère les données originales du projet depuis ses téléchargements GitHub."""
from pathlib import Path
import hashlib
import json
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent

def empreinte(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def telecharger():
    source = json.loads((ROOT / "donnees.json").read_text(encoding="utf-8"))
    folder = ROOT / ".local" / "donnees"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / source["fichier"]
    if target.is_file() and empreinte(target) == source["sha256"]:
        return target
    temporary = target.with_suffix(target.suffix + ".part")
    print("Téléchargement des données originales du projet. Cette étape est nécessaire une seule fois.", flush=True)
    request = Request(source["url"], headers={"User-Agent": "ArilesD-project"})
    try:
        digest = hashlib.sha256()
        size = 0
        last = 0
        with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
                digest.update(block)
                size += len(block)
                if size - last >= 20 * 1024 * 1024:
                    print(f"Données : {100 * size // source['octets']} %", flush=True)
                    last = size
        if size != source["octets"] or digest.hexdigest() != source["sha256"]:
            raise RuntimeError("Le téléchargement des données est incomplet. Relance LANCER.cmd.")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target
