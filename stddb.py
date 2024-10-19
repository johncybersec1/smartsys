import pymysql
import os

timeout = 10
my_secret = os.environ['password']
connection = pymysql.connect(
  charset="utf8mb4",
  connect_timeout=timeout,
  cursorclass=pymysql.cursors.DictCursor,
  db="defaultdb",
  host="mysql-smartsys-smartsys-db.k.aivencloud.com",
  password=my_secret,
  read_timeout=timeout,
  port=24350,
  user="avnadmin",
  write_timeout=timeout,
)