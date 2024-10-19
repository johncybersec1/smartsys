from flask import current_app, g
import mysql.connector
import os


def getdb():
    if 'db' not in g or not g.db.is_connected():
        g.db = mysql.connector.connect(
            host=os.environ['host'],  # Accessing the environment variable
            user=os.environ['user'],  # Accessing the environment variable
            password=os.
            environ['password'],  # Accessing the environment variable
            database=os.environ['login'],  # Accessing the environment variable
            ssl_verify_identity=
            True,  # This may depend on your database settings
        )
    return g.db
def closedb(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
    