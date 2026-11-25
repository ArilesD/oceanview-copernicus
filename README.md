# OcéanView - Exploration de données marines

Projet universitaire réalisé en équipe, avec des tâches partagées entre le traitement des données et le développement de l’application.

OcéanView permet de :
- Filtrer des mesures de température de surface, de salinité et de chlorophylle-a sur une carte.
- Comparer les mesures dans des graphiques.
- Créer un compte local et enregistrer des sélections en favoris.

**Outils :** Python, Flask, MySQL, Leaflet et Plotly.

## Aperçu du projet

![Carte des mesures historiques Copernicus dans la version universitaire d’OcéanView.](docs/presentation.gif)

La vidéo montre les mesures [Copernicus Marine](https://marine.copernicus.eu/) de 2024-2025 utilisées dans le projet d’origine. Ce dépôt fournit des **données fictives** pour lancer l’application.

[Image en grand format](docs/apercu.png) · [Voir la vidéo](docs/presentation.mp4)

## Télécharger et lancer

1. Installe [Python 3.14](https://www.python.org/downloads/) si besoin, en cochant **Add python.exe to PATH**.
2. [Télécharge le projet en ZIP](https://github.com/ArilesD/oceanview-copernicus/archive/refs/heads/main.zip), fais **Extraire tout**, puis ouvre le dossier extrait.
3. Double-clique sur **LANCER.cmd**.

Le premier lancement nécessite Internet pour installer les bibliothèques. Garde la fenêtre de lancement ouverte pendant l’utilisation et appuie sur **Entrée** dans cette fenêtre pour arrêter le projet.

Le lancement prépare MySQL et les données de test, puis ouvre le site. Crée un compte via **Inscription** avec un mot de passe d’au moins huit caractères, puis connecte-toi.

La carte et les graphiques nécessitent Internet.

## Comprendre les fichiers

| Fichier ou dossier | Rôle |
| --- | --- |
| `LANCER.cmd` et `lancer.py` | Préparent et démarrent le projet. |
| `mysql_local.py` | Prépare la base MySQL locale. |
| `app/controllers/` | Pages et données demandées par la carte et les graphiques. |
| `app/models/` | Requêtes et accès à MySQL. |
| `app/templates/` et `app/static/` | Interface, carte et graphiques. |
| `app/schema_demo.sql` et `app/demo.py` | Structure de la base et génération des mesures fictives. |

Fond de carte © OpenStreetMap France et [contributeurs OpenStreetMap](https://www.openstreetmap.org/copyright).
