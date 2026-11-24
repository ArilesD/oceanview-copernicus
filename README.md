# OcéanView - Exploration de données marines

Projet universitaire réalisé à cinq en BUT Informatique à l’IUT de Créteil-Vitry (UPEC). Nous avons partagé les tâches entre le traitement des données et le développement de l’application.

OcéanView permet de :
- Filtrer des mesures de température de surface, de salinité et de chlorophylle-a sur une carte.
- Comparer les mesures dans des graphiques.
- Créer un compte local et enregistrer des sélections en favoris.

**Outils :** Python, Flask, MySQL, Leaflet et Plotly.

## Aperçu du projet

![Carte des mesures historiques Copernicus dans la version universitaire d’OcéanView.](docs/presentation.gif)

La vidéo montre les mesures [Copernicus Marine](https://marine.copernicus.eu/) de 2024-2025 utilisées dans le projet d’origine. Ce dépôt fournit **576 mesures fictives**, sur 16 positions et 12 dates, pour tester l’application.

[Image en grand format](docs/apercu.png) · [Voir la vidéo](docs/presentation.mp4)

## Télécharger et lancer

1. Installe [Python 3.14](https://www.python.org/downloads/) si besoin, en cochant **Add python.exe to PATH**.
2. [Télécharge le projet en ZIP](https://github.com/ArilesD/oceanview-copernicus/archive/refs/heads/main.zip), fais **Extraire tout**, puis ouvre le dossier extrait.
3. Double-clique sur **LANCER.cmd**.

Le premier lancement nécessite Internet pour installer les bibliothèques. Garde la fenêtre de lancement ouverte pendant l’utilisation et appuie sur **Entrée** dans cette fenêtre pour arrêter le projet.

Le lancement prépare MySQL et les données de test, puis ouvre le site. Crée un compte via **Inscription** avec un mot de passe d’au moins huit caractères, puis connecte-toi.

La première préparation peut télécharger MySQL (environ 268 Mo). Prévois environ **1 Go d’espace libre**. La carte et les graphiques nécessitent Internet.

## Comprendre les fichiers

| Fichier ou dossier | Rôle |
| --- | --- |
| `LANCER.cmd` et `lancer.py` | Préparent et démarrent le projet. |
| `mysql_local.py` | Prépare la base MySQL locale. |
| `app/controllers/` | Pages et données demandées par la carte et les graphiques. |
| `app/models/` | Requêtes et accès à MySQL. |
| `app/templates/` et `app/static/` | Interface, carte et graphiques. |
| `app/schema_demo.sql` et `app/demo.py` | Structure de la base et génération des mesures fictives. |

Les crédits de l’équipe figurent dans la page **À propos**. [Carte avec les mesures fictives](docs/carte-demo.jpg) · [Graphique des mesures fictives](docs/graphique-demo.jpg)

<details>
<summary>Installation manuelle et détails techniques</summary>

### Première préparation de MySQL

Le lanceur utilise MySQL 8.4 si son dossier est indiqué dans **MYSQL_HOME** ou s’il est installé dans son emplacement habituel. Sinon, il télécharge automatiquement l’archive officielle de MySQL 8.4.13 (environ 268 Mio), la vérifie et l’extrait dans **.local/outils/**. Prévois environ 1 Go d’espace libre. Une base dédiée et des identifiants locaux sont créés dans **.local/mysql/**.

Si MySQL signale une bibliothèque Windows manquante, installe le [Microsoft Visual C++ Redistributable x64](https://aka.ms/vs/17/release/vc_redist.x64.exe), puis relance le projet. [Téléchargements officiels MySQL](https://dev.mysql.com/downloads/mysql/8.4.html) · [Installation MySQL sur Windows](https://dev.mysql.com/doc/refman/8.4/en/windows-install-archive.html)

### Lancement manuel

Prépare Python 3.12 ou 3.14 et démarre MySQL 8.4. La carte et les graphiques chargent leurs bibliothèques et le fond de carte depuis Internet.

Crée une base MySQL dédiée avec ton compte d’administration. Dans les commandes ci-dessous, remplace `mot-de-passe-local-a-choisir` par le mot de passe du nouveau compte MySQL local.

```sql
CREATE DATABASE oceanview_demo CHARACTER SET utf8mb4;
CREATE USER 'oceanview'@'127.0.0.1' IDENTIFIED BY 'mot-de-passe-local-a-choisir';
GRANT ALL PRIVILEGES ON oceanview_demo.* TO 'oceanview'@'127.0.0.1';
```

Depuis la racine du dépôt, crée un environnement virtuel et le fichier de configuration local.

**PowerShell**

```powershell
python -m venv .venv
New-Item -ItemType Directory -Force instance
Copy-Item config.example.py instance/config.py
```

Renseigne ton mot de passe MySQL dans `instance/config.py`, puis installe les dépendances, initialise les données et démarre l’application.

**PowerShell**

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run init-demo
.\.venv\Scripts\python.exe run.py
```

Ouvre [OcéanView sur ton ordinateur](http://127.0.0.1:5001) et crée un compte via **Inscription**. Connecte-toi pour accéder à la carte et aux graphiques.

### Reproduire les aperçus

- Dans **Carte**, choisis **Température (SST)**, **Europe (Global)** et **Carte de points**. Garde la période du 1er janvier au 1er décembre 2025 et clique sur **Mettre à jour la carte**. Les 192 mesures de température sont regroupées sur la carte selon le zoom.
- Dans **Graphiques**, choisis **Évolution** et **Température (SST)** sur la même période. Clique sur **Voir l’évolution** pour afficher les 12 valeurs de la démo.

Pour tester l’administration, ajoute `--admin-email admin@example.test` à la commande `init-demo`. L’application te demande de choisir le mot de passe de ce compte.

</details>

Fond de carte © OpenStreetMap France et [contributeurs OpenStreetMap](https://www.openstreetmap.org/copyright).
