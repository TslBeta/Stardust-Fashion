"""MoMo one-time wallet sandbox integration.

Only signed results from MoMo may change a payment to SUCCESS. Localhost cannot
receive IPN; the operator must supply a public HTTPS callback URL for full tests.
"""

import hashlib
import hmac
import json
import os
import secrets
import urllib.error
import urllib.request

from flask import Blueprint, redirect, request

from .auth import current_user, require
from .common import fail, output
from .db import db, execute, one


bp = Blueprint("momo", __name__)
MOMO_CREATE_URL = "https://test-payment.momo.vn/v2/gateway/api/create"


def config():
    values = {name: os.getenv(name, "").strip() for name in
              ("MOMO_PARTNER_CODE", "MOMO_ACCESS_KEY", "MOMO_SECRET_KEY", "MOMO_IPN_URL", "MOMO_REDIRECT_URL")}
    if not all(values.values()):
        fail(503, "MOMO_NOT_CONFIGURED", "Chưa cấu hình khóa MoMo sandbox, redirect URL và IPN URL trong .env.")
    if not values["MOMO_IPN_URL"].startswith("https://"):
        fail(503, "MOMO_IPN_NOT_PUBLIC", "MOMO_IPN_URL phải là HTTPS công khai để MoMo gửi IPN.")
    return values


def signature(raw, secret):
    return hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def request_signature(data, settings):
    raw = (f"accessKey={settings['MOMO_ACCESS_KEY']}&amount={data['amount']}&extraData={data['extraData']}"
           f"&ipnUrl={data['ipnUrl']}&orderId={data['orderId']}&orderInfo={data['orderInfo']}"
           f"&partnerCode={data['partnerCode']}&redirectUrl={data['redirectUrl']}"
           f"&requestId={data['requestId']}&requestType={data['requestType']}")
    return signature(raw, settings["MOMO_SECRET_KEY"])


def result_signature(data, settings):
    fields = ("amount", "extraData", "message", "orderId", "orderInfo", "orderType", "partnerCode",
              "payType", "requestId", "responseTime", "resultCode", "transId")
    if any(field not in data for field in fields) or "signature" not in data:
        fail(400, "MOMO_RESULT_INCOMPLETE", "Phản hồi MoMo thiếu trường xác minh.")
    raw = "accessKey=" + settings["MOMO_ACCESS_KEY"] + "&" + "&".join(f"{field}={data[field]}" for field in fields)
    return signature(raw, settings["MOMO_SECRET_KEY"])


def verified_create_response(answer, settings):
    fields = ("amount", "message", "orderId", "partnerCode", "payUrl", "requestId", "responseTime", "resultCode")
    if any(field not in answer for field in fields) or "signature" not in answer:
        return False
    raw = "accessKey=" + settings["MOMO_ACCESS_KEY"] + "&" + "&".join(f"{field}={answer[field]}" for field in fields)
    return hmac.compare_digest(signature(raw, settings["MOMO_SECRET_KEY"]), str(answer["signature"]))


def numeric(value):
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def start_payment(order_id, user_id):
    settings = config()
    db().begin()
    try:
        order = one("SELECT id,total,status,payment_method,payment_status FROM orders WHERE id=%s AND user_id=%s FOR UPDATE",
                    (order_id, user_id))
        if not order:
            fail(404, "ORDER_NOT_FOUND", "Không tìm thấy đơn hàng của bạn.")
        if order["payment_method"] != "ONLINE" or order["status"] != "PENDING" or order["payment_status"] == "SUCCESS":
            fail(409, "INVALID_PAYMENT_STATE", "Đơn hàng không chờ thanh toán MoMo.")
        if not 1000 <= order["total"] <= 50000000:
            fail(409, "MOMO_AMOUNT_LIMIT", "MoMo sandbox hỗ trợ đơn từ 1.000 đến 50.000.000 đồng.")
        attempt = one("SELECT * FROM momo_payment_attempts WHERE order_id=%s ORDER BY id DESC LIMIT 1 FOR UPDATE", (order_id,))
        if attempt and attempt["status"] == "PENDING" and attempt["pay_url"]:
            db().commit()
            return {"payment_url": attempt["pay_url"], "order_id": order_id, "payment_status": "PENDING"}
        if not attempt or attempt["status"] in ("FAILED", "SUCCESS"):
            unique = secrets.token_hex(12)
            momo_order_id = f"SF{order_id}_{unique}"
            request_id = f"R{unique}"
            attempt_id, _ = execute("INSERT INTO momo_payment_attempts(order_id,momo_order_id,request_id,amount,status) "
                                    "VALUES(%s,%s,%s,%s,'INITIATING')", (order_id, momo_order_id, request_id, order["total"]))
            attempt = {"id": attempt_id, "momo_order_id": momo_order_id, "request_id": request_id,
                       "amount": order["total"], "status": "INITIATING"}
        db().commit()
    except Exception:
        db().rollback()
        raise
    payload = {
        "partnerCode": settings["MOMO_PARTNER_CODE"], "requestType": "captureWallet",
        "ipnUrl": settings["MOMO_IPN_URL"], "redirectUrl": settings["MOMO_REDIRECT_URL"],
        "orderId": attempt["momo_order_id"], "amount": attempt["amount"],
        "orderInfo": f"Stardust Fashion order {order_id}", "requestId": attempt["request_id"],
        "extraData": "", "lang": "vi",
    }
    payload["signature"] = request_signature(payload, settings)
    http_request = urllib.request.Request(MOMO_CREATE_URL, json.dumps(payload).encode("utf-8"),
                                          {"Content-Type": "application/json; charset=UTF-8"}, method="POST")
    try:
        with urllib.request.urlopen(http_request, timeout=30) as response:
            answer = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        fail(502, "MOMO_UNAVAILABLE", "Không kết nối được MoMo sandbox. Có thể thử lại cùng mã yêu cầu.")
    if answer.get("partnerCode") != settings["MOMO_PARTNER_CODE"] or answer.get("requestId") != attempt["request_id"] or answer.get("orderId") != attempt["momo_order_id"] or numeric(answer.get("amount")) != attempt["amount"]:
        fail(502, "MOMO_RESPONSE_MISMATCH", "MoMo trả về thông tin không khớp yêu cầu.")
    if not verified_create_response(answer, settings):
        fail(502, "MOMO_INVALID_SIGNATURE", "Chữ ký phản hồi tạo thanh toán MoMo không hợp lệ.")
    if answer.get("resultCode") != 0:
        execute("UPDATE momo_payment_attempts SET status='FAILED' WHERE id=%s", (attempt["id"],))
        execute("UPDATE orders SET payment_status='FAILED' WHERE id=%s AND payment_status<>'SUCCESS'", (order_id,))
        db().commit()
        fail(502, "MOMO_REJECTED", "MoMo từ chối tạo thanh toán: " + str(answer.get("message", "không rõ lý do")))
    url = answer.get("payUrl", "")
    if not url.startswith("https://test-payment.momo.vn/"):
        fail(502, "MOMO_INVALID_URL", "MoMo trả về URL thanh toán không hợp lệ.")
    execute("UPDATE momo_payment_attempts SET status='PENDING',pay_url=%s WHERE id=%s AND status='INITIATING'", (url, attempt["id"]))
    execute("UPDATE orders SET payment_status='PENDING' WHERE id=%s AND payment_status<>'SUCCESS'", (order_id,))
    db().commit()
    return {"payment_url": url, "order_id": order_id, "payment_status": "PENDING"}


@bp.post("/api/v1/orders/<int:order_id>/payments/momo")
@require("CUSTOMER")
def start_route(order_id):
    return output(start_payment(order_id, current_user()["id"]))


def process_result(data):
    settings = config()
    actual = result_signature(data, settings)
    if not hmac.compare_digest(actual, str(data["signature"])):
        fail(401, "MOMO_INVALID_SIGNATURE", "Chữ ký phản hồi MoMo không hợp lệ.")
    if data["partnerCode"] != settings["MOMO_PARTNER_CODE"]:
        fail(400, "MOMO_PARTNER_MISMATCH", "Partner Code không khớp.")
    db().begin()
    try:
        attempt = one("SELECT * FROM momo_payment_attempts WHERE momo_order_id=%s FOR UPDATE", (data["orderId"],))
        if not attempt or data["requestId"] != attempt["request_id"] or numeric(data["amount"]) != attempt["amount"]:
            fail(400, "MOMO_ORDER_MISMATCH", "Mã yêu cầu hoặc số tiền không khớp đơn hàng.")
        order = one("SELECT id,status,payment_status FROM orders WHERE id=%s FOR UPDATE", (attempt["order_id"],))
        if attempt["status"] == "SUCCESS":
            db().commit()
            return attempt["order_id"], "SUCCESS"
        result_code = numeric(data["resultCode"])
        if result_code is None:
            fail(400, "MOMO_RESULT_INVALID", "Mã kết quả MoMo không hợp lệ.")
        state = "SUCCESS" if result_code == 0 else ("PENDING" if result_code == 9000 else "FAILED")
        execute("UPDATE momo_payment_attempts SET status=%s,momo_trans_id=%s WHERE id=%s",
                (state, str(data["transId"]), attempt["id"]))
        if order["payment_status"] != "SUCCESS":
            execute("UPDATE orders SET payment_status=%s WHERE id=%s", (state, order["id"]))
        db().commit()
    except Exception:
        db().rollback()
        raise
    return attempt["order_id"], state


@bp.post("/api/v1/payments/momo/ipn")
def ipn():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        fail(400, "INVALID_JSON", "IPN phải là JSON object.")
    process_result(data)
    return "", 204


@bp.get("/checkout/momo-return")
def momo_return():
    order_id, state = process_result(request.args.to_dict())
    return redirect(f"/#orders?payment={state.lower()}&order={order_id}")
