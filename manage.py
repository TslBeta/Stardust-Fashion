"""Initialize or explicitly reset only the Stardust Fashion MySQL database."""

import argparse
import os
from pathlib import Path

from werkzeug.security import generate_password_hash

from stardust.db import connect


ROOT = Path(__file__).resolve().parent
DATABASE = "stardust_fashion"


def initialize(reset=False):
    configured = os.getenv("MYSQL_DATABASE", DATABASE)
    if configured != DATABASE:
        raise SystemExit("Refusing to initialize a database other than stardust_fashion.")
    connection = connect(with_database=False)
    try:
        with connection.cursor() as cursor:
            if reset:
                cursor.execute("DROP DATABASE IF EXISTS stardust_fashion")
            statements = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8").split(";")
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()
    seed()


def seed():
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS n FROM users")
            if cursor.fetchone()["n"]:
                print("Database already has users; seed skipped. Use reset only for disposable test data.")
                return
            users = [
                ("admin@stardust.test", "Admin12345", "Quản trị Stardust", "0900000001", "ADMIN"),
                ("an@stardust.test", "Customer123", "Nguyễn An", "0900000002", "CUSTOMER"),
                ("binh@stardust.test", "Customer123", "Trần Bình", "0900000003", "CUSTOMER"),
            ]
            cursor.executemany("INSERT INTO users(email,password_hash,full_name,phone,role) VALUES(%s,%s,%s,%s,%s)",
                               [(email, generate_password_hash(secret), name, phone, role)
                                for email, secret, name, phone, role in users])
            categories = [("Áo", "áo", 1), ("Quần", "quần", 1), ("Phụ kiện", "phụ kiện", 1),
                          ("Archive", "archive", 0)]
            cursor.executemany("INSERT INTO categories(name,name_key,active) VALUES(%s,%s,%s)", categories)
            products = [
                (1, "NEBULA OVERSIZED TEE", "Áo thun cotton form rộng, tinh thần streetwear.", 150000, "/static/images/tee.png", 1),
                (1, "ORBIT HOODIE", "Hoodie đen phom rộng cho những ngày thành phố lên đèn.", 390000, "/static/images/hero.png", 1),
                (1, "SOLAR RELAXED TEE", "Áo thun sáng màu, chất cotton mềm và thoáng.", 190000, "/static/images/cream-tee.png", 1),
                (2, "DRIFT CARGO PANTS", "Quần cargo xanh rêu, nhiều túi và dễ phối.", 250000, "/static/images/pants.png", 1),
                (3, "VOID CAP", "Mũ lưỡi trai đen thêu logo tối giản.", 120000, "/static/images/cap.png", 1),
            ]
            cursor.executemany("INSERT INTO products(category_id,name,description,price,image_url,active) "
                               "VALUES(%s,%s,%s,%s,%s,%s)", products)
            variants = [
                (1, "M", "Đen", "m", "đen", 5, 1), (1, "L", "Đen", "l", "đen", 10, 1),
                (1, "M", "Trắng", "m", "trắng", 0, 1),
                (2, "M", "Đen", "m", "đen", 4, 1), (2, "L", "Đen", "l", "đen", 8, 1),
                (3, "M", "Kem", "m", "kem", 7, 1), (3, "L", "Kem", "l", "kem", 2, 1),
                (4, "M", "Rêu", "m", "rêu", 9, 1), (4, "L", "Rêu", "l", "rêu", 5, 1),
                (5, "ONE SIZE", "Đen", "one size", "đen", 12, 1),
            ]
            cursor.executemany("INSERT INTO variants(product_id,size,color,size_key,color_key,stock,active) "
                               "VALUES(%s,%s,%s,%s,%s,%s,%s)", variants)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    print("Initialized Stardust Fashion with admin, customer A/B, categories, products and variants.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("init-db", "reset-db", "check-db"))
    parser.add_argument("--yes-reset-project-database", action="store_true")
    args = parser.parse_args()
    if args.command == "reset-db" and not args.yes_reset_project_database:
        raise SystemExit("Reset deletes only stardust_fashion data. Add --yes-reset-project-database to confirm.")
    if args.command == "check-db":
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE() AS name, COUNT(*) AS users FROM users")
                print(cursor.fetchone())
        finally:
            connection.close()
    else:
        initialize(args.command == "reset-db")
