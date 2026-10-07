import re
from datetime import datetime

from flask import jsonify, request


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def fail(status, code, message):
    raise ApiError(status, code, message)


def json_body(allowed=None, required=()):
    if not request.is_json:
        fail(400, "INVALID_JSON", "Gửi Content-Type: application/json.")
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        fail(400, "INVALID_JSON", "Nội dung JSON phải là một object.")
    if allowed is not None:
        extra = set(body) - set(allowed)
        if extra:
            fail(400, "UNKNOWN_FIELD", "Trường không được phép: " + ", ".join(sorted(extra)))
    missing = [name for name in required if name not in body]
    if missing:
        fail(400, "MISSING_FIELD", "Thiếu trường: " + ", ".join(missing))
    return body


def string(value, name, min_length=1, max_length=255):
    if not isinstance(value, str):
        fail(400, "INVALID_" + name.upper(), f"{name} phải là chuỗi.")
    result = value.strip()
    if not min_length <= len(result) <= max_length:
        fail(400, "INVALID_" + name.upper(), f"{name} phải dài {min_length}–{max_length} ký tự.")
    return result


def integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        fail(400, "INVALID_" + name.upper(), f"{name} phải là số nguyên từ {minimum} đến {maximum}.")
    return value


def boolean(value, name):
    if type(value) is not bool:
        fail(400, "INVALID_" + name.upper(), f"{name} phải là true hoặc false.")
    return value


def email(value):
    address = string(value, "email", 3, 255).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", address):
        fail(400, "INVALID_EMAIL", "Email không đúng định dạng.")
    return address


def password(value):
    if not isinstance(value, str) or not 8 <= len(value) <= 64:
        fail(400, "INVALID_PASSWORD", "Mật khẩu phải dài 8–64 ký tự.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
        fail(400, "INVALID_PASSWORD", "Mật khẩu cần có chữ và số.")
    return value


def phone(value):
    if value is None or value == "":
        return None
    value = string(value, "phone", 10, 10)
    if not re.fullmatch(r"0[0-9]{9}", value):
        fail(400, "INVALID_PHONE", "Số điện thoại phải có 10 chữ số và bắt đầu bằng 0.")
    return value


def positive_id(value, name="id"):
    return integer(value, name, 1, 9223372036854775807)


def stamp(row):
    if row is None:
        return None
    for key, value in list(row.items()):
        if isinstance(value, datetime):
            row[key] = value.isoformat(timespec="seconds")
    return row


def output(value, status=200):
    return jsonify(value), status
