import pymysql
import os

def getdb():
    timeout = 10
    connection = pymysql.connect(
        charset="utf8mb4",
        connect_timeout=timeout,
        cursorclass=pymysql.cursors.DictCursor,
        db=os.environ.get("DB_NAME", "defaultdb"),  # Environment variable or default
        host=os.environ.get("DB_HOST", "mysql-smartsys-smartsys-db.k.aivencloud.com"),
        password=os.environ.get("DB_PASS", "fdgfdgfd2FglFvdfsgrmhbP0"),  # Replace with env variable
        read_timeout=timeout,
        port=int(os.environ.get("DB_PORT", 24350)),  # Ensure port is an int
        user=os.environ.get("DB_USER", "avnadmin"),
        write_timeout=timeout,
    )
    return connection

