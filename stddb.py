import pymysql
import os

timeout = 10
connection = pymysql.connect(
  charset="utf8mb4",
  connect_timeout=timeout,
  cursorclass=pymysql.cursors.DictCursor,
  db=os.environ['login'],
  host=os.environ['host'],
  password=os.environ['password'],
  read_timeout=timeout,
  port=24350,
  user=os.environ['user'],
  write_timeout=timeout,
)