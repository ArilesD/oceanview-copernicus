from datetime import date
from math import cos, pi
from pathlib import Path

import click
import mysql.connector
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app.models.database import connect_database


POSITIONS = [
    (49.4, -4.2), (49.6, -2.1), (50.0, -0.5), (50.3, 0.9),
    (43.7, -6.0), (44.7, -4.9), (45.2, -3.7), (46.2, -5.0),
    (41.5, 4.2), (42.2, 5.5), (41.2, 8.1), (39.7, 10.3),
    (53.0, -12.4), (54.0, -11.0), (55.2, -13.2), (55.6, -8.2),
]
VARIABLES = [(1, 'SST'), (2, 'SSS'), (3, 'Chl-a')]


def demo_measurements():
    rows = []
    for month in range(1, 13):
        season = cos((month - 8) * pi / 6)
        for location, (latitude, _) in enumerate(POSITIONS, 1):
            values = (
                17 + 5 * season - (latitude - 42) * 0.47,
                34.4 + (location % 5) * 0.3 + 0.2 * season,
                0.6 + (location % 4) * 0.2 - 0.25 * season,
            )
            for variable, value in enumerate(values, 1):
                # Les requêtes historiques échantillonnent par ID de mesure.
                rows.append((100 * (len(rows) + 1), variable, location, date(2025, month, 1), round(value, 2)))
    return rows


@click.command('init-demo')
@click.option('--admin-email', help='Créer un compte administrateur de démonstration.')
@with_appcontext
def init_demo(admin_email):
    """Initialise une base MySQL dédiée à la démonstration."""
    if not current_app.config['DB_NAME'].endswith('_demo'):
        raise click.ClickException('Utilisez une base dédiée dont le nom se termine par _demo.')

    admin_password = None
    if admin_email:
        admin_password = click.prompt('Mot de passe administrateur', hide_input=True, confirmation_prompt=True)
        if len(admin_password) < 8:
            raise click.ClickException('Utilisez au moins 8 caractères.')

    schema = Path(__file__).with_name('schema_demo.sql').read_text(encoding='utf-8')
    try:
        with connect_database() as connection, connection.cursor() as cursor:
            cursor.execute(schema)
            while cursor.nextset():
                pass
            cursor.executemany('INSERT IGNORE INTO variable VALUES (%s, %s)', VARIABLES)
            cursor.executemany('INSERT IGNORE INTO localisation VALUES (%s, %s, %s)', [
                (index, lat, lon) for index, (lat, lon) in enumerate(POSITIONS, 1)
            ])
            cursor.executemany('INSERT IGNORE INTO mesure VALUES (%s, %s, %s, %s, %s)', demo_measurements())
            if admin_email:
                cursor.execute(
                    "INSERT INTO utilisateur (Nom_Utilisateur, Email, Role, Mot_de_Passe) VALUES (%s, %s, 'Admin', %s)",
                    ('Administration démo', admin_email, generate_password_hash(admin_password)),
                )
            connection.commit()
    except mysql.connector.Error as error:
        raise click.ClickException(f'Initialisation MySQL impossible ({error.errno}). Vérifiez la base et la configuration locale.') from error

    click.echo('La base OcéanView est prête avec les données fictives.')
