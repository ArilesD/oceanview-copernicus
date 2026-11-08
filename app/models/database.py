import mysql.connector
from flask import current_app


def connect_database():
    config = current_app.config
    return mysql.connector.connect(
        host=config['DB_HOST'],
        port=int(config['DB_PORT']),
        database=config['DB_NAME'],
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        connection_timeout=5,
    )


def get_db_connection():
    try:
        return connect_database()
    except mysql.connector.Error:
        current_app.logger.warning('Connexion à la base MySQL indisponible.')
        return None
