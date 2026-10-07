import os
from pathlib import Path

import pymysql
from flask import g


ROOT = Path(__file__).resolve().parent.parent


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


load_env()


def connect(with_database=True):
    opts = dict(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    if with_database:
        opts["database"] = os.getenv("MYSQL_DATABASE", "stardust_fashion")
    return pymysql.connect(**opts)


def db():
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def one(sql, args=(), connection=None):
    with (connection or db()).cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchone()


def all_rows(sql, args=(), connection=None):
    with (connection or db()).cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def execute(sql, args=(), connection=None):
    with (connection or db()).cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.lastrowid, cursor.rowcount
