"""Prépare et ouvre le projet téléchargé depuis GitHub."""
PROJECT = 'oceanview'
NAME = 'OcéanView'
PORT = 5114
ENTRY = 'run:app'
PAGE = '/map'
SIGNATURE = 'OcéanView'

from contextlib import nullcontext
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / ".local"
PORT = int(os.environ.get("LANCEMENT_PORT", PORT))
WINDOWS = os.name == "nt"
FLAGS = subprocess.CREATE_NO_WINDOW if WINDOWS else 0


def run(arguments, **options):
    subprocess.run(arguments, cwd=ROOT, check=True, **options)


def stop(process):
    if process.poll() is None:
        if WINDOWS:
            subprocess.run(
                [str(Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"),
                 "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=FLAGS, timeout=10,
            )
        else:
            process.terminate()
        process.wait(timeout=15)


def read_page(path, timeout=4):
    with urlopen(f"http://127.0.0.1:{PORT}" + path, timeout=timeout) as response:
        return response.read()


def running():
    with socket.socket() as connection:
        connection.settimeout(.3)
        return connection.connect_ex(("127.0.0.1", PORT)) == 0


def reuse():
    if not running():
        return False
    html = read_page(PAGE)
    if SIGNATURE.encode("utf-8") not in html:
        raise RuntimeError(f"Le port {PORT} est utilisé par une autre application.")
    if "--verifier" in sys.argv:
        verify()
    else:
        webbrowser.open(f"http://127.0.0.1:{PORT}" + PAGE)
    print(f"{NAME} est déjà ouvert.")
    return True


def verify():
    if PROJECT == "ameli":
        assert b"data:image/" in read_page(PAGE, 45)
        assert b"Extrait de d" not in read_page(PAGE, 45)
    elif PROJECT == "diplomaatique":
        assert b"/arrete/" in read_page("/?q=jardin", 15)
    elif PROJECT == "hubeau":
        assert json.loads(read_page("/api/communes/94", 15))
    elif PROJECT == "oceanview":
        assert len(json.loads(read_page("/api/available-dates", 45))) == 12
        assert len(json.loads(read_page("/api/data?start=2025-01-01&indicator=SST&zone=europe", 45))) == 16
    else:
        for path in ("/velib_stations_map.html", "/velib_stations_voronoi.html"):
            assert b"assets/leaflet/leaflet.js" in read_page(path)
    print(f"{NAME} : vérification réussie.")


def install():
    requirements = ROOT / "requirements.txt"
    fingerprint = hashlib.sha256(
        requirements.read_bytes() + str(ROOT).encode() + str(sys.version_info[:2]).encode()
    ).hexdigest()
    environment = LOCAL / "python"
    python = environment / ("Scripts/python.exe" if WINDOWS else "bin/python")
    marker = LOCAL / "bibliotheques"
    installed = marker.read_text() if marker.is_file() else ""
    if not python.is_file() or installed != fingerprint:
        print("Préparation de Python et des bibliothèques. Internet est nécessaire à la première ouverture.", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
        run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
             "-r", str(requirements)])
        marker.write_text(fingerprint)
    return python


def prepare(python):
    if PROJECT in ("ameli", "hubeau"):
        run([str(python), "prepare_data.py"])
    elif PROJECT == "diplomaatique" and not (ROOT / "Base_donnees/arretes.db").is_file():
        run([str(python), "diplomaatique.py", "exemple/raa-fictif.txt",
             "exemple/raa-fictif.json", "--output", "output"])


def serve():
    python = Path(sys.executable)
    if PROJECT != "velib":
        prepare(python)
    context = nullcontext({})
    if PROJECT == "oceanview":
        from mysql_local import base_locale
        context = base_locale(ROOT, LOCAL)
    address = f"http://127.0.0.1:{PORT}"
    with context as variables:
        environment = {**os.environ, **variables, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        environment["MPLCONFIGDIR"] = str(LOCAL / "matplotlib")
        if PROJECT == "oceanview":
            run([str(python), "-m", "flask", "--app", "run", "init-demo"], env=environment)
        arguments = ["-m", "http.server", str(PORT), "--bind", "127.0.0.1"]
        if PROJECT != "velib":
            arguments = ["-m", "flask", "--app", ENTRY, "run",
                         "--host", "127.0.0.1", "--port", str(PORT)]
        with (LOCAL / "application.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(python), *arguments], cwd=ROOT, env=environment,
                                       stdout=log, stderr=log, creationflags=FLAGS)
        try:
            deadline = time.monotonic() + 90
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"Le site s’est arrêté. Consulte {LOCAL / 'application.log'}.")
                try:
                    read_page(PAGE, 3)
                    break
                except (OSError, URLError):
                    if time.monotonic() > deadline:
                        raise RuntimeError("Le projet met trop de temps à démarrer. Consulte .local/application.log.")
                    time.sleep(.3)
            print(f"{NAME} est prêt : {address + PAGE}", flush=True)
            if "--verifier" in sys.argv:
                verify()
                return
            webbrowser.open(address + PAGE)
            input("Garde cette fenêtre ouverte. Appuie sur Entrée ici pour arrêter le projet.\n")
        finally:
            stop(process)


def main():
    os.chdir(ROOT)
    if not (3, 12) <= sys.version_info[:2] < (3, 15):
        raise RuntimeError("Installe Python 3.12, 3.13 ou 3.14 depuis https://www.python.org/downloads/.")
    if reuse():
        return
    LOCAL.mkdir(exist_ok=True)
    with (LOCAL / "lancement.lock").open("a+b") as lock:
        lock.seek(0)
        if WINDOWS:
            import msvcrt
            if lock.read(1) == b"":
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError("Une préparation est déjà en cours dans ce dossier. Attends sa fin.") from error
        else:
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise RuntimeError("Une préparation est déjà en cours dans ce dossier.") from error
        if PROJECT == "velib":
            serve()
        else:
            python = install()
            process = subprocess.Popen([str(python), "-B", str(Path(__file__)), "--serve",
                                        *sys.argv[1:]], cwd=ROOT)
            try:
                code = process.wait()
            finally:
                stop(process)
            if code:
                raise RuntimeError("Le lancement a échoué. Les explications figurent dans les lignes ci-dessus.")


if __name__ == "__main__":
    try:
        if "--serve" in sys.argv:
            serve()
        else:
            main()
    except (KeyboardInterrupt, EOFError):
        print("\nProjet arrêté.")
    except Exception as error:
        print(f"Ouverture impossible. {error}", file=sys.stderr)
        sys.exit(1)
