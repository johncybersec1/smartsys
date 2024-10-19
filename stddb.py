import pymysql
import os

timeout = 10
connection = pymysql.connect(
  charset="utf8mb4",
  connect_timeout=timeout,
  cursorclass=pymysql.cursors.DictCursor,
  db="defaultdb",
  host="mysql-smartsys-smartsys-db.k.aivencloud.com",
  password=os.environ['DB_PASS'],
  read_timeout=timeout,
  port=24350,
  user="avnadmin",
  write_timeout=timeout,
)