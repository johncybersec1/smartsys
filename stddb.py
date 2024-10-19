from flask import current_app, g
import mysql.connector
import os

def getdb():
  if 'db' not in g or not g.db.is_connected():
      g.db = mysql.connector.connect(
          host=current_app.config[os.environ['host']],
          user=current_app.config[os.environ['user']],
          password=current_app.config[os.environ['password']],
          database=current_app.config[os.environ['login']],
          ssl_verify_identity=True,
          ssl_ca=os.environ['cert']
      )
  return g.db
def close_db(e=None):
  db = g.pop('db', None)

  if db is not None and db.is_connected():
      db.close()

current_app.teardown_appcontext(close_db)