"""MySQL local isolé pour la version publique d’OcéanView."""

from contextlib import contextmanager
import gzip
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
from tempfile import TemporaryDirectory
import time
from urllib.request import urlopen
from zipfile import ZipFile

import mysql.connector

from donnees import telecharger

VERSION = "8.4.13"
ARCHIVE = f"mysql-{VERSION}-winx64"
URL = f"https://cdn.mysql.com/Downloads/MySQL-8.4/{ARCHIVE}.zip"
MD5 = "7b94489d5524dea9b27097068bea25a8"


def trouver_mysql(local):
    configured = os.environ.get("MYSQL_HOME")
    candidates = [Path(configured)] if configured else []
    candidates.extend([
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "MySQL/MySQL Server 8.4",
        local / "outils" / ARCHIVE,
    ])
    for folder in candidates:
        if (folder / "bin/mysqld.exe").is_file():
            return folder.resolve()
    if os.name != "nt":
        raise RuntimeError("Ce lancement nécessite Windows 64 bits.")
    if not os.environ.get("PROCESSOR_ARCHITECTURE", "").upper().endswith("64"):
        raise RuntimeError("Le téléchargement MySQL nécessite Windows 64 bits.")
    tools = local / "outils"
    tools.mkdir(exist_ok=True)
    print("Téléchargement de MySQL 8.4 depuis Oracle (environ 268 Mio). Cette étape est nécessaire une fois.", flush=True)
    with TemporaryDirectory(dir=tools) as temporary:
        temporary = Path(temporary)
        archive = temporary / "mysql.zip"
        digest = hashlib.md5()
        total = 0
        with urlopen(URL, timeout=60) as response, archive.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
                digest.update(block)
                total += len(block)
                if total % (32 * 1024 * 1024) == 0:
                    print(f"MySQL : {total // (1024 * 1024)} Mio reçus.", flush=True)
        if digest.hexdigest() != MD5:
            raise RuntimeError("Le téléchargement MySQL est incomplet. Relance LANCER.cmd.")
        print("Extraction de MySQL.", flush=True)
        with ZipFile(archive) as package:
            for item in package.namelist():
                path = Path(item)
                if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != ARCHIVE:
                    raise RuntimeError("L’archive MySQL contient un chemin inattendu.")
            package.extractall(temporary)
        source = temporary / ARCHIVE
        if not (source / "bin/mysqld.exe").is_file():
            raise RuntimeError("Le programme MySQL est absent de l’archive.")
        source.replace(tools / ARCHIVE)
    return tools / ARCHIVE


def importer_donnees(root, binary_folder, port, password, folder):
    marker = folder / "import-original-termine.json"
    source = json.loads((Path(__file__).parent / "donnees.json").read_text(encoding="utf-8"))
    if marker.is_file() and json.loads(marker.read_text(encoding="utf-8")).get("sha256") == source["sha256"]:
        with root.cursor() as cursor:
            cursor.execute("SELECT ID_Mesure FROM oceanview_original.mesure LIMIT 1")
            if cursor.fetchone() is not None:
                return
        raise RuntimeError("La base originale a été modifiée ou vidée. Consulte .local/mysql/mysql.log.")
    archive = telecharger()
    print("Import des mesures historiques Copernicus. Cette première préparation peut prendre plusieurs minutes.", flush=True)
    with root.cursor() as cursor:
        # Seule la base de cette installation isolée est reconstruite après un import interrompu.
        cursor.execute("DROP DATABASE IF EXISTS oceanview_original")
        cursor.execute("CREATE DATABASE oceanview_original CHARACTER SET utf8mb4")
    options = folder / "import.cnf"
    options.write_text(f"[client]\nuser=root\npassword={password}\n", encoding="ascii")
    try:
        with (folder / "import.log").open("ab") as log, gzip.open(archive, "rb") as source_sql:
            with subprocess.Popen(
                [str(binary_folder / "bin/mysql.exe"), "--defaults-extra-file=import.cnf",
                 "--host=127.0.0.1", f"--port={port}", "--max-allowed-packet=64M",
                 "--default-character-set=utf8mb4", "--database=oceanview_original"],
                stdin=subprocess.PIPE, stdout=log, stderr=log, cwd=folder,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ) as importer:
                try:
                    with importer.stdin as stream:
                        shutil.copyfileobj(source_sql, stream, length=1024 * 1024)
                        stream.write(b"\n")
                        stream.write((Path(__file__).parent / "app/schema.sql").read_bytes())
                except BrokenPipeError:
                    importer.wait()
                    raise RuntimeError("L’import des données a échoué. Consulte .local/mysql/import.log, puis relance LANCER.cmd.") from None
                if importer.wait():
                    raise RuntimeError("L’import des données a échoué. Consulte .local/mysql/import.log, puis relance LANCER.cmd.")
    finally:
        options.unlink(missing_ok=True)
    with root.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT COUNT(*) AS mesures, MIN(Jour_Opti) AS debut, MAX(Jour_Opti) AS fin FROM oceanview_original.mesure")
        result = cursor.fetchone()
        if result["mesures"] != source["mesures"]:
            raise RuntimeError("L’import ne contient pas toutes les mesures originales. Consulte .local/mysql/import.log, puis relance LANCER.cmd.")
    result["sha256"] = source["sha256"]
    marker.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Données originales prêtes : {result['mesures']} mesures.", flush=True)


@contextmanager
def base_locale(local):
    folder = local / "mysql"
    folder.mkdir(exist_ok=True)
    config = folder / "comptes.json"
    if not config.is_file():
        config.write_text(json.dumps({key: secrets.token_hex(32) for key in ("root", "app", "session")}), encoding="utf-8")
    passwords = json.loads(config.read_text(encoding="utf-8"))
    binary_folder = trouver_mysql(local)
    program = binary_folder / "bin/mysqld.exe"
    data = folder / "data"
    log_path = folder / "mysql.log"
    flags = subprocess.CREATE_NO_WINDOW
    arguments = [str(program), "--no-defaults", "--console",
                 f"--basedir={binary_folder}", f"--datadir={data}"]
    with log_path.open("ab") as log:
        if not (data / "mysql.ibd").is_file():
            if data.exists() and any(data.iterdir()):
                # Préserve un éventuel démarrage interrompu pour permettre son diagnostic.
                data.rename(folder / f"data-incomplet-{time.time_ns()}")
            print("Création de la base MySQL locale.", flush=True)
            subprocess.run([*arguments, "--initialize-insecure"], stdout=log, stderr=log,
                           creationflags=flags, check=True, timeout=120)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    initialization = folder / "initialiser.sql"
    initialization.write_text(
        f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{passwords['root']}';\n", encoding="ascii"
    )
    with log_path.open("ab") as log:
        server = subprocess.Popen(
            [*arguments, "--bind-address=127.0.0.1", f"--port={port}",
             "--mysqlx=OFF", "--skip-log-bin", f"--init-file={initialization}"],
            stdout=log, stderr=log, creationflags=flags,
        )
    root = None
    try:
        end = time.monotonic() + 60
        while time.monotonic() < end:
            if server.poll() is not None:
                raise RuntimeError(f"MySQL s’est arrêté. Consulte {log_path}. Si une DLL manque, installe Microsoft Visual C++ Redistributable x64.")
            try:
                root = mysql.connector.connect(host="127.0.0.1", port=port, user="root",
                                               password=passwords["root"], connection_timeout=2)
                break
            except mysql.connector.Error:
                time.sleep(.35)
        if root is None:
            raise RuntimeError(f"MySQL ne répond pas. Consulte {log_path}.")
        initialization.unlink(missing_ok=True)
        with root.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS oceanview_original CHARACTER SET utf8mb4")
            cursor.execute("CREATE USER IF NOT EXISTS 'oceanview'@'127.0.0.1' IDENTIFIED BY %s", (passwords["app"],))
            cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON oceanview_original.* TO 'oceanview'@'127.0.0.1'")
        importer_donnees(root, binary_folder, port, passwords["root"], folder)
        yield {
            "OCEANVIEW_DB_HOST": "127.0.0.1",
            "OCEANVIEW_DB_PORT": str(port),
            "OCEANVIEW_DB_NAME": "oceanview_original",
            "OCEANVIEW_DB_USER": "oceanview",
            "OCEANVIEW_DB_PASSWORD": passwords["app"],
            "OCEANVIEW_SECRET_KEY": passwords["session"],
        }
    finally:
        initialization.unlink(missing_ok=True)
        if root is not None:
            try:
                with root.cursor() as cursor:
                    cursor.execute("SHUTDOWN")
            except mysql.connector.Error:
                pass
            finally:
                root.close()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.terminate()
            server.wait(timeout=10)
