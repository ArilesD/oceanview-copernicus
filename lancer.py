"""Prépare et ouvre le projet téléchargé depuis GitHub."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser
import json
import hashlib
import venv

NAME = 'OcéanView'
PORT = 5114
PAGE = '/map'
SIGNATURE = 'OcéanView'
ENTRY = 'run:app'
ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / ".local"
WINDOWS = os.name == "nt"
PORT = int(os.environ.get("LANCEMENT_PORT", PORT))
FLAGS = subprocess.CREATE_NO_WINDOW if WINDOWS else 0


def run(arguments, **options):
    subprocess.run(arguments, cwd=ROOT, check=True, **options)


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
    dates = json.loads(read_page("/api/available-dates", 180))
    assert dates, "Aucune date dans la base originale."
    values = json.loads(read_page("/api/data?start=" + dates[0] + "&indicator=SST&zone=europe", 180))
    assert isinstance(values, list) and values, "Aucune mesure réelle sur la carte."
    print(f"{NAME} : vérification réussie.")


def serve():
    python = Path(sys.executable)
    from mysql_local import base_locale
    context = base_locale(LOCAL)
    address = f"http://127.0.0.1:{PORT}"
    with context as variables:
        environment = {**os.environ, **variables, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
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
