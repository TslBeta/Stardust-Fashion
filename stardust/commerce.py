from flask import Blueprint, request

from .auth import current_user, require
from .catalog import available
from .common import fail, integer, json_body, output, phone, positive_id, stamp, string
from .db import all_rows, db, execute, one


bp = Blueprint("commerce", __name__, url_prefix="/api/v1")
SHIPPING_FEE = 30000


def cart_rows(user_id):
    rows = all_rows(
        "SELECT ci.id,ci.variant_id,ci.quantity,v.size,v.color,v.stock,v.active AS variant_active,"
        "p.id AS product_id,p.name AS product_name,p.price,p.image_url,p.active AS product_active,"
        "c.active AS category_active FROM cart_items ci "
        "JOIN variants v ON v.id=ci.variant_id JOIN products p ON p.id=v.product_id "
        "JOIN categories c ON c.id=p.category_id WHERE ci.user_id=%s ORDER BY ci.id", (user_id,))
    for row in rows:
        row["available"] = bool(row["variant_active"] and row["product_active"] and
                                row["category_active"] and row["stock"] >= row["quantity"])
        row["unavailable_reason"] = (
            "Danh mục ngừng hoạt động" if not row["category_active"] else
            "Sản phẩm ngừng bán" if not row["product_active"] else
            "Biến thể ngừng bán" if not row["variant_active"] else
            "Không đủ tồn kho" if row["stock"] < row["quantity"] else None
        )
        row["line_total"] = row["price"] * row["quantity"]
        for key in ("variant_active", "product_active", "category_active"):
            row[key] = bool(row[key])
    return rows


@bp.get("/cart")
@require("CUSTOMER")
def cart():
    rows = cart_rows(current_user()["id"])
    return output({"items": rows, "subtotal": sum(row["line_total"] for row in rows), "shipping_fee": SHIPPING_FEE})


@bp.post("/cart/items")
@require("CUSTOMER")
def add_cart_item():
    data = json_body({"variant_id", "quantity"}, ("variant_id", "quantity"))
    variant_id = positive_id(data["variant_id"], "variant_id")
    quantity = integer(data["quantity"], "quantity", 1, 99)
    user_id = current_user()["id"]
    db().begin()
    try:
        one("SELECT id FROM users WHERE id=%s FOR UPDATE", (user_id,))
        variant = one("SELECT v.id,v.stock,v.active,p.active AS product_active,c.active AS category_active "
                      "FROM variants v JOIN products p ON p.id=v.product_id "
                      "JOIN categories c ON c.id=p.category_id WHERE v.id=%s FOR UPDATE", (variant_id,))
        if not variant:
            fail(404, "VARIANT_NOT_FOUND", "Không tìm thấy biến thể.")
        existing = one("SELECT id,quantity FROM cart_items WHERE user_id=%s AND variant_id=%s FOR UPDATE",
                       (user_id, variant_id))
        new_quantity = quantity + (existing["quantity"] if existing else 0)
        integer(new_quantity, "quantity", 1, 99)
        available(variant, new_quantity)
        if existing:
            execute("UPDATE cart_items SET quantity=%s WHERE id=%s", (new_quantity, existing["id"]))
            item_id, status = existing["id"], 200
        else:
            item_id, _ = execute("INSERT INTO cart_items(user_id,variant_id,quantity) VALUES(%s,%s,%s)",
                                 (user_id, variant_id, new_quantity))
            status = 201
        db().commit()
    except Exception:
        db().rollback()
        raise
    return output({"id": item_id, "variant_id": variant_id, "quantity": new_quantity}, status)


@bp.patch("/cart/items/<int:item_id>")
@require("CUSTOMER")
def update_cart_item(item_id):
    data = json_body({"quantity"}, ("quantity",))
    quantity = integer(data["quantity"], "quantity", 1, 99)
    user_id = current_user()["id"]
    db().begin()
    try:
        one("SELECT id FROM users WHERE id=%s FOR UPDATE", (user_id,))
        item = one("SELECT id,variant_id FROM cart_items WHERE id=%s AND user_id=%s FOR UPDATE", (item_id, user_id))
        if not item:
            fail(404, "CART_ITEM_NOT_FOUND", "Không tìm thấy dòng giỏ hàng của bạn.")
        variant = one("SELECT v.id,v.stock,v.active,p.active AS product_active,c.active AS category_active "
                      "FROM variants v JOIN products p ON p.id=v.product_id JOIN categories c ON c.id=p.category_id "
                      "WHERE v.id=%s FOR UPDATE", (item["variant_id"],))
        available(variant, quantity)
        execute("UPDATE cart_items SET quantity=%s WHERE id=%s", (quantity, item_id))
        db().commit()
    except Exception:
        db().rollback()
        raise
    return output({"id": item_id, "variant_id": item["variant_id"], "quantity": quantity})


@bp.delete("/cart/items/<int:item_id>")
@require("CUSTOMER")
def delete_cart_item(item_id):
    user_id = current_user()["id"]
    db().begin()
    try:
        one("SELECT id FROM users WHERE id=%s FOR UPDATE", (user_id,))
        _, count = execute("DELETE FROM cart_items WHERE id=%s AND user_id=%s", (item_id, user_id))
        if not count:
            fail(404, "CART_ITEM_NOT_FOUND", "Không tìm thấy dòng giỏ hàng của bạn.")
        db().commit()
    except Exception:
        db().rollback()
        raise
    return "", 204


def order_detail(order_id, owner_id=None):
    sql = "SELECT id,user_id,status,payment_method,payment_status,recipient_name,recipient_phone,address,subtotal,shipping_fee,total,created_at,updated_at FROM orders WHERE id=%s"
    args = [order_id]
    if owner_id is not None:
        sql += " AND user_id=%s"
        args.append(owner_id)
    row = one(sql, args)
    if not row:
        fail(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
    row["items"] = all_rows("SELECT id,variant_id,product_name,size,color,unit_price,quantity,line_total "
                            "FROM order_items WHERE order_id=%s ORDER BY id", (order_id,))
    return stamp(row)


@bp.post("/orders")
@require("CUSTOMER")
def create_order():
    data = json_body({"recipient_name", "recipient_phone", "address", "payment_method"},
                     ("recipient_name", "recipient_phone", "address", "payment_method"))
    name = string(data["recipient_name"], "recipient_name", 2, 100)
    number = phone(data["recipient_phone"])
    if not number:
        fail(400, "INVALID_PHONE", "Cần số điện thoại người nhận.")
    address = string(data["address"], "address", 10, 255)
    method = data["payment_method"]
    if method not in ("COD", "ONLINE"):
        fail(400, "INVALID_PAYMENT_METHOD", "payment_method phải là COD hoặc ONLINE.")
    user_id = current_user()["id"]
    db().begin()
    try:
        one("SELECT id FROM users WHERE id=%s FOR UPDATE", (user_id,))
        items = all_rows("SELECT id,variant_id,quantity FROM cart_items WHERE user_id=%s ORDER BY variant_id FOR UPDATE", (user_id,))
        if not items:
            fail(409, "EMPTY_CART", "Giỏ hàng đang rỗng.")
        snapshots = []
        subtotal = 0
        for item in items:
            variant = one("SELECT v.id,v.size,v.color,v.stock,v.active,p.name,p.price,p.active AS product_active,"
                          "c.active AS category_active FROM variants v JOIN products p ON p.id=v.product_id "
                          "JOIN categories c ON c.id=p.category_id WHERE v.id=%s FOR UPDATE", (item["variant_id"],))
            available(variant, item["quantity"])
            line_total = variant["price"] * item["quantity"]
            subtotal += line_total
            snapshots.append((variant, item["quantity"], line_total))
        if method == "ONLINE" and subtotal + SHIPPING_FEE > 50000000:
            fail(409, "MOMO_AMOUNT_LIMIT", "MoMo sandbox hỗ trợ tổng đơn tối đa 50.000.000 đồng.")
        order_id, _ = execute(
            "INSERT INTO orders(user_id,status,payment_method,payment_status,recipient_name,recipient_phone,address,subtotal,shipping_fee,total) "
            "VALUES(%s,'PENDING',%s,%s,%s,%s,%s,%s,%s,%s)",
            (user_id, method, "UNPAID" if method == "COD" else "PENDING", name, number,
             address, subtotal, SHIPPING_FEE, subtotal + SHIPPING_FEE),
        )
        for variant, quantity, line_total in snapshots:
            execute("INSERT INTO order_items(order_id,variant_id,product_name,size,color,unit_price,quantity,line_total) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                    (order_id, variant["id"], variant["name"], variant["size"], variant["color"],
                     variant["price"], quantity, line_total))
            _, updated = execute("UPDATE variants SET stock=stock-%s WHERE id=%s AND stock>=%s",
                                 (quantity, variant["id"], quantity))
            if updated != 1:
                fail(409, "OUT_OF_STOCK", "Tồn kho vừa thay đổi, vui lòng thử lại.")
        execute("DELETE FROM cart_items WHERE user_id=%s", (user_id,))
        db().commit()
    except Exception:
        db().rollback()
        raise
    result = order_detail(order_id, user_id)
    if method == "ONLINE":
        result["payment_start_endpoint"] = f"/api/v1/orders/{order_id}/payments/momo"
    return output(result, 201)


@bp.get("/orders")
@require("CUSTOMER")
def my_orders():
    rows = all_rows("SELECT id,status,payment_method,payment_status,subtotal,shipping_fee,total,created_at "
                    "FROM orders WHERE user_id=%s ORDER BY id DESC", (current_user()["id"],))
    return output([stamp(row) for row in rows])


@bp.get("/orders/<int:order_id>")
@require("CUSTOMER")
def my_order_detail(order_id):
    return output(order_detail(order_id, current_user()["id"]))


def cancel_order_locked(order):
    if order["status"] not in ("PENDING", "CONFIRMED"):
        fail(409, "INVALID_ORDER_TRANSITION", "Đơn hàng không thể hủy ở trạng thái hiện tại.")
    items = all_rows("SELECT variant_id,quantity FROM order_items WHERE order_id=%s ORDER BY variant_id", (order["id"],))
    for item in items:
        stock = one("SELECT stock FROM variants WHERE id=%s FOR UPDATE", (item["variant_id"],))
        if stock["stock"] + item["quantity"] > 100000:
            fail(409, "STOCK_LIMIT", "Hoàn kho sẽ vượt giới hạn 100.000; cần giảm tồn kho trước.")
        execute("UPDATE variants SET stock=stock+%s WHERE id=%s", (item["quantity"], item["variant_id"]))
    execute("UPDATE orders SET status='CANCELLED' WHERE id=%s", (order["id"],))


@bp.patch("/orders/<int:order_id>/cancel")
@require("CUSTOMER")
def cancel_my_order(order_id):
    data = json_body({"status"})
    if data and data.get("status") != "CANCELLED":
        fail(400, "INVALID_STATUS", "Khách hàng chỉ có thể gửi CANCELLED.")
    db().begin()
    try:
        order = one("SELECT id,status FROM orders WHERE id=%s AND user_id=%s FOR UPDATE",
                    (order_id, current_user()["id"]))
        if not order:
            fail(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng của bạn.")
        if order["status"] != "PENDING":
            fail(409, "INVALID_ORDER_TRANSITION", "Khách chỉ được hủy đơn PENDING.")
        cancel_order_locked(order)
        db().commit()
    except Exception:
        db().rollback()
        raise
    return output(order_detail(order_id, current_user()["id"]))


@bp.get("/admin/orders")
@require("ADMIN")
def admin_orders():
    status = request.args.get("status")
    if status and status not in ("PENDING", "CONFIRMED", "SHIPPING", "COMPLETED", "CANCELLED"):
        fail(400, "INVALID_STATUS", "Trạng thái đơn không hợp lệ.")
    sql = "SELECT o.id,o.user_id,u.email,o.status,o.payment_method,o.payment_status,o.total,o.created_at FROM orders o JOIN users u ON u.id=o.user_id"
    args = []
    if status:
        sql += " WHERE o.status=%s"
        args.append(status)
    return output([stamp(row) for row in all_rows(sql + " ORDER BY o.id DESC", args)])


@bp.get("/admin/orders/<int:order_id>")
@require("ADMIN")
def admin_order_detail(order_id):
    return output(order_detail(order_id))


@bp.patch("/admin/orders/<int:order_id>/status")
@require("ADMIN")
def admin_order_status(order_id):
    data = json_body({"status"}, ("status",))
    target = data["status"]
    allowed = {"PENDING": ("CONFIRMED", "CANCELLED"), "CONFIRMED": ("SHIPPING", "CANCELLED"),
               "SHIPPING": ("COMPLETED",)}
    db().begin()
    try:
        order = one("SELECT id,status,payment_method,payment_status FROM orders WHERE id=%s FOR UPDATE", (order_id,))
        if not order:
            fail(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng.")
        if target not in allowed.get(order["status"], ()):
            fail(409, "INVALID_ORDER_TRANSITION", "Chuyển trạng thái không hợp lệ.")
        if target in ("SHIPPING", "COMPLETED") and order["payment_method"] == "ONLINE" and order["payment_status"] != "SUCCESS":
            fail(409, "PAYMENT_NOT_SUCCESSFUL", "Cần thanh toán online thành công trước khi giao hàng.")
        if target == "CANCELLED":
            cancel_order_locked(order)
        else:
            execute("UPDATE orders SET status=%s,payment_status=CASE WHEN %s='COMPLETED' AND payment_method='COD' "
                    "THEN 'SUCCESS' ELSE payment_status END WHERE id=%s", (target, target, order_id))
        db().commit()
    except Exception:
        db().rollback()
        raise
    return output(order_detail(order_id))


