from flask import Blueprint, request
from pymysql.err import IntegrityError

from .auth import require
from .common import boolean, fail, integer, json_body, output, positive_id, string
from .db import all_rows, db, execute, one


bp = Blueprint("catalog", __name__, url_prefix="/api/v1")


def category_row(category_id, public=False):
    row = one("SELECT id,name,active FROM categories WHERE id=%s", (category_id,))
    if not row or (public and not row["active"]):
        fail(404, "CATEGORY_NOT_FOUND", "Không tìm thấy danh mục.")
    row["active"] = bool(row["active"])
    return row


def product_row(product_id, public=False):
    row = one("SELECT p.id,p.category_id,p.name,p.description,p.price,p.image_url,p.active,"
              "c.name AS category_name,c.active AS category_active FROM products p "
              "JOIN categories c ON c.id=p.category_id WHERE p.id=%s", (product_id,))
    if not row or (public and not (row["active"] and row["category_active"])):
        fail(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm đang bán.")
    row["active"] = bool(row["active"])
    row["category_active"] = bool(row["category_active"])
    return row


def variant_row(variant_id):
    row = one("SELECT v.id,v.product_id,v.size,v.color,v.stock,v.active,p.price,p.name AS product_name,"
              "p.active AS product_active,c.active AS category_active,p.image_url "
              "FROM variants v JOIN products p ON p.id=v.product_id "
              "JOIN categories c ON c.id=p.category_id WHERE v.id=%s", (variant_id,))
    if not row:
        fail(404, "VARIANT_NOT_FOUND", "Không tìm thấy biến thể.")
    for key in ("active", "product_active", "category_active"):
        row[key] = bool(row[key])
    return row


def available(variant, quantity):
    prefix = f"Biến thể #{variant['id']}: "
    if not variant["category_active"]:
        fail(409, "ITEM_INACTIVE", prefix + "danh mục đã ngừng hoạt động.")
    if not variant["product_active"]:
        fail(409, "ITEM_INACTIVE", prefix + "sản phẩm đã ngừng bán.")
    if not variant["active"]:
        fail(409, "ITEM_INACTIVE", prefix + "biến thể đã ngừng bán.")
    if variant["stock"] < quantity:
        fail(409, "OUT_OF_STOCK", prefix + "không đủ tồn kho.")


@bp.get("/categories")
def categories():
    rows = all_rows("SELECT id,name,active FROM categories WHERE active=1 ORDER BY id")
    for row in rows:
        row["active"] = True
    return output(rows)


@bp.get("/products")
def products():
    def query_int(name, default, low, high):
        raw = request.args.get(name)
        if raw is None:
            return default
        if not raw.isdecimal():
            fail(400, "INVALID_" + name.upper(), f"{name} phải là số nguyên.")
        return integer(int(raw), name, low, high)

    page = query_int("page", 1, 1, 1000000)
    limit = query_int("limit", 12, 1, 100)
    min_price = query_int("minPrice", 0, 0, 100000000)
    max_price = query_int("maxPrice", 100000000, 0, 100000000)
    if min_price > max_price:
        fail(400, "INVALID_PRICE_RANGE", "minPrice không được lớn hơn maxPrice.")
    where = ["p.active=1", "c.active=1", "p.price BETWEEN %s AND %s"]
    args = [min_price, max_price]
    if "categoryId" in request.args:
        category_id = query_int("categoryId", None, 1, 9223372036854775807)
        where.append("p.category_id=%s")
        args.append(category_id)
    if "search" in request.args:
        search = string(request.args["search"], "search", 1, 100)
        where.append("p.name LIKE %s")
        args.append("%" + search + "%")
    clause = " AND ".join(where)
    total = one("SELECT COUNT(*) AS n FROM products p JOIN categories c ON c.id=p.category_id WHERE " + clause, args)["n"]
    rows = all_rows("SELECT p.id,p.category_id,p.name,p.description,p.price,p.image_url,p.active,"
                    "c.name AS category_name FROM products p JOIN categories c ON c.id=p.category_id "
                    "WHERE " + clause + " ORDER BY p.id DESC LIMIT %s OFFSET %s", args + [limit, (page - 1) * limit])
    for row in rows:
        row["active"] = True
    return output({"items": rows, "page": page, "limit": limit, "total": total})


@bp.get("/products/<int:product_id>")
def product_detail(product_id):
    row = product_row(product_id, True)
    row["variants"] = all_rows("SELECT id,product_id,size,color,stock,active FROM variants "
                               "WHERE product_id=%s AND active=1 ORDER BY id", (product_id,))
    for variant in row["variants"]:
        variant["active"] = True
    return output(row)


@bp.get("/products/<int:product_id>/variants")
def product_variants(product_id):
    product_row(product_id, True)
    rows = all_rows("SELECT id,product_id,size,color,stock,active FROM variants WHERE product_id=%s AND active=1 ORDER BY id", (product_id,))
    for row in rows:
        row["active"] = True
    return output(rows)


@bp.get("/admin/categories")
@require("ADMIN")
def admin_categories():
    rows = all_rows("SELECT id,name,active FROM categories ORDER BY id")
    for row in rows:
        row["active"] = bool(row["active"])
    return output(rows)


@bp.post("/admin/categories")
@require("ADMIN")
def create_category():
    data = json_body({"name", "active"}, ("name",))
    name = string(data["name"], "name", 1, 100)
    active = boolean(data["active"], "active") if "active" in data else True
    try:
        category_id, _ = execute("INSERT INTO categories(name,name_key,active) VALUES(%s,%s,%s)",
                                 (name, name.casefold(), active))
        db().commit()
    except IntegrityError:
        db().rollback()
        fail(409, "CATEGORY_EXISTS", "Tên danh mục đã tồn tại.")
    return output(category_row(category_id), 201)


@bp.patch("/admin/categories/<int:category_id>")
@require("ADMIN")
def update_category(category_id):
    current = category_row(category_id)
    data = json_body({"name", "active"})
    if not data:
        fail(400, "MISSING_FIELD", "Cần name hoặc active.")
    name = string(data["name"], "name", 1, 100) if "name" in data else current["name"]
    active = boolean(data["active"], "active") if "active" in data else current["active"]
    try:
        execute("UPDATE categories SET name=%s,name_key=%s,active=%s WHERE id=%s",
                (name, name.casefold(), active, category_id))
        db().commit()
    except IntegrityError:
        db().rollback()
        fail(409, "CATEGORY_EXISTS", "Tên danh mục đã tồn tại.")
    return output(category_row(category_id))


@bp.delete("/admin/categories/<int:category_id>")
@require("ADMIN")
def delete_category(category_id):
    category_row(category_id)
    if one("SELECT id FROM products WHERE category_id=%s LIMIT 1", (category_id,)):
        fail(409, "CATEGORY_HAS_PRODUCTS", "Danh mục còn sản phẩm, kể cả sản phẩm ngừng bán.")
    try:
        execute("DELETE FROM categories WHERE id=%s", (category_id,))
        db().commit()
    except IntegrityError:
        db().rollback()
        fail(409, "CATEGORY_HAS_PRODUCTS", "Danh mục còn sản phẩm.")
    return "", 204


@bp.get("/admin/products")
@require("ADMIN")
def admin_products():
    rows = all_rows("SELECT p.id,p.category_id,p.name,p.description,p.price,p.image_url,p.active,c.name AS category_name "
                    "FROM products p JOIN categories c ON c.id=p.category_id ORDER BY p.id DESC")
    for row in rows:
        row["active"] = bool(row["active"])
    return output(rows)


@bp.get("/admin/products/<int:product_id>")
@require("ADMIN")
def admin_product_detail(product_id):
    row = product_row(product_id)
    row["variants"] = all_rows("SELECT id,product_id,size,color,stock,active FROM variants WHERE product_id=%s ORDER BY id", (product_id,))
    for variant in row["variants"]:
        variant["active"] = bool(variant["active"])
    return output(row)


def product_values(data, current=None):
    category_id = positive_id(data["category_id"], "category_id") if "category_id" in data else current["category_id"]
    category_row(category_id)
    name = string(data["name"], "name", 1, 150) if "name" in data else current["name"]
    description = string(data["description"], "description", 0, 5000) if "description" in data else (current["description"] if current else None)
    price = integer(data["price"], "price", 1, 100000000) if "price" in data else current["price"]
    image = string(data["image_url"], "image_url", 1, 500) if data.get("image_url") else (current["image_url"] if current and "image_url" not in data else None)
    active = boolean(data["active"], "active") if "active" in data else (current["active"] if current else False)
    return category_id, name, description, price, image, active


def ensure_publishable(product_id, image, active):
    if active and not image:
        fail(409, "PRODUCT_NEEDS_IMAGE", "Sản phẩm cần đường dẫn ảnh trước khi mở bán.")
    if active and not one("SELECT id FROM variants WHERE product_id=%s AND active=1 LIMIT 1", (product_id,)):
        fail(409, "PRODUCT_NEEDS_VARIANT", "Sản phẩm cần ít nhất một biến thể hoạt động trước khi mở bán.")


@bp.post("/admin/products")
@require("ADMIN")
def create_product():
    data = json_body({"category_id", "name", "description", "price", "image_url", "active"},
                     ("category_id", "name", "price"))
    category_id, name, description, price, image, active = product_values(data)
    if active:
        fail(409, "PRODUCT_NEEDS_VARIANT", "Sản phẩm mới ngừng bán; hãy tạo biến thể rồi mở bán.")
    product_id, _ = execute("INSERT INTO products(category_id,name,description,price,image_url,active) "
                            "VALUES(%s,%s,%s,%s,%s,0)", (category_id, name, description, price, image))
    db().commit()
    return output(product_row(product_id), 201)


@bp.patch("/admin/products/<int:product_id>")
@require("ADMIN")
def update_product(product_id):
    current = product_row(product_id)
    data = json_body({"category_id", "name", "description", "price", "image_url", "active"})
    if not data:
        fail(400, "MISSING_FIELD", "Cần ít nhất một trường sản phẩm.")
    category_id, name, description, price, image, active = product_values(data, current)
    ensure_publishable(product_id, image, active)
    execute("UPDATE products SET category_id=%s,name=%s,description=%s,price=%s,image_url=%s,active=%s WHERE id=%s",
            (category_id, name, description, price, image, active, product_id))
    db().commit()
    return output(product_row(product_id))


@bp.post("/admin/products/<int:product_id>/variants")
@require("ADMIN")
def create_variant(product_id):
    product_row(product_id)
    data = json_body({"size", "color", "stock", "active"}, ("size", "color", "stock"))
    size = string(data["size"], "size", 1, 30)
    color = string(data["color"], "color", 1, 50)
    stock = integer(data["stock"], "stock", 0, 100000)
    active = boolean(data["active"], "active") if "active" in data else True
    try:
        variant_id, _ = execute("INSERT INTO variants(product_id,size,color,size_key,color_key,stock,active) "
                                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                                (product_id, size, color, size.casefold(), color.casefold(), stock, active))
        db().commit()
    except IntegrityError:
        db().rollback()
        fail(409, "VARIANT_EXISTS", "Tổ hợp size và màu đã tồn tại trong sản phẩm.")
    return output(variant_row(variant_id), 201)


@bp.patch("/admin/variants/<int:variant_id>")
@require("ADMIN")
def update_variant(variant_id):
    variant = variant_row(variant_id)
    data = json_body({"stock", "active"})
    if not data:
        fail(400, "MISSING_FIELD", "Cần stock hoặc active.")
    stock = integer(data["stock"], "stock", 0, 100000) if "stock" in data else variant["stock"]
    active = boolean(data["active"], "active") if "active" in data else variant["active"]
    db().begin()
    try:
        one("SELECT stock FROM variants WHERE id=%s FOR UPDATE", (variant_id,))
        execute("UPDATE variants SET stock=%s,active=%s WHERE id=%s", (stock, active, variant_id))
        db().commit()
    except Exception:
        db().rollback()
        raise
    return output(variant_row(variant_id))
