import hashlib
import os
import secrets
from functools import wraps

from flask import Blueprint, g, request
from pymysql.err import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .common import email, fail, json_body, output, password, phone, string
from .db import db, execute, one


bp = Blueprint("auth", __name__, url_prefix="/api/v1")


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_user(required=True):
    if hasattr(g, "current_user"):
        return g.current_user
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else ""
    if not token:
        if required:
            fail(401, "UNAUTHENTICATED", "Cần đăng nhập.")
        return None
    user = one(
        "SELECT u.id,u.email,u.full_name,u.phone,u.role,t.id AS token_id "
        "FROM auth_tokens t JOIN users u ON u.id=t.user_id "
        "WHERE t.token_hash=%s AND t.revoked_at IS NULL AND t.expires_at>UTC_TIMESTAMP()",
        (hash_token(token),),
    )
    if not user:
        fail(401, "INVALID_TOKEN", "Token không hợp lệ, đã hết hạn hoặc đã đăng xuất.")
    g.current_user = user
    return user


def require(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if role and user["role"] != role:
                fail(403, "FORBIDDEN", "Tài khoản không có quyền thực hiện.")
            return func(*args, **kwargs)
        return wrapper
    return decorator


@bp.post("/auth/register")
def register():
    data = json_body({"email", "password", "full_name", "phone"}, ("email", "password", "full_name"))
    address = email(data["email"])
    secret = password(data["password"])
    name = string(data["full_name"], "full_name", 2, 100)
    number = phone(data.get("phone"))
    if one("SELECT id FROM users WHERE email=%s", (address,)):
        fail(409, "EMAIL_EXISTS", "Email đã được sử dụng.")
    try:
        user_id, _ = execute(
            "INSERT INTO users(email,password_hash,full_name,phone,role) VALUES(%s,%s,%s,%s,'CUSTOMER')",
            (address, generate_password_hash(secret), name, number),
        )
        db().commit()
    except IntegrityError:
        db().rollback()
        fail(409, "EMAIL_EXISTS", "Email đã được sử dụng.")
    except Exception:
        db().rollback()
        raise
    return output({"id": user_id, "email": address, "full_name": name, "phone": number, "role": "CUSTOMER"}, 201)


@bp.post("/auth/login")
def login():
    data = json_body({"email", "password"}, ("email", "password"))
    address = email(data["email"])
    if not isinstance(data["password"], str):
        fail(400, "INVALID_PASSWORD", "Mật khẩu phải là chuỗi.")
    user = one("SELECT * FROM users WHERE email=%s", (address,))
    if not user or not check_password_hash(user["password_hash"], data["password"]):
        fail(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng.")
    token = secrets.token_urlsafe(48)
    execute(
        "INSERT INTO auth_tokens(user_id,token_hash,expires_at) VALUES(%s,%s,UTC_TIMESTAMP()+INTERVAL 1 DAY)",
        (user["id"], hash_token(token)),
    )
    db().commit()
    return output({"token": token, "token_type": "Bearer", "expires_in": 86400,
                   "user": {key: user[key] for key in ("id", "email", "full_name", "phone", "role")}})


@bp.post("/auth/logout")
@require()
def logout():
    execute("UPDATE auth_tokens SET revoked_at=UTC_TIMESTAMP() WHERE id=%s", (current_user()["token_id"],))
    db().commit()
    return "", 204


@bp.post("/auth/change-password")
@require()
def change_password():
    data = json_body({"current_password", "new_password"}, ("current_password", "new_password"))
    secret = password(data["new_password"])
    record = one("SELECT password_hash FROM users WHERE id=%s", (current_user()["id"],))
    if not isinstance(data["current_password"], str) or not check_password_hash(record["password_hash"], data["current_password"]):
        fail(401, "INVALID_CREDENTIALS", "Mật khẩu hiện tại không đúng.")
    execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(secret), current_user()["id"]))
    execute("UPDATE auth_tokens SET revoked_at=UTC_TIMESTAMP() WHERE user_id=%s AND id<>%s",
            (current_user()["id"], current_user()["token_id"]))
    db().commit()
    return output({"message": "Đã đổi mật khẩu."})


@bp.post("/auth/forgot-password")
def forgot_password():
    data = json_body({"email"}, ("email",))
    address = email(data["email"])
    user = one("SELECT id FROM users WHERE email=%s", (address,))
    response = {"message": "Nếu email tồn tại, mã đặt lại đã được tạo."}
    if user:
        token = secrets.token_urlsafe(32)
        execute("INSERT INTO reset_tokens(user_id,token_hash,expires_at) VALUES(%s,%s,UTC_TIMESTAMP()+INTERVAL 15 MINUTE)",
                (user["id"], hash_token(token)))
        db().commit()
        if os.getenv("APP_ENV", "development") == "development" and request.host.split(":")[0] in ("127.0.0.1", "localhost"):
            response["reset_token"] = token
            response["message"] = "Mã đặt lại (chỉ hiện trong môi trường development)."
    return output(response)


@bp.post("/auth/reset-password")
def reset_password():
    data = json_body({"reset_token", "new_password"}, ("reset_token", "new_password"))
    token = string(data["reset_token"], "reset_token", 10, 255)
    secret = password(data["new_password"])
    db().begin()
    try:
        record = one("SELECT id,user_id FROM reset_tokens WHERE token_hash=%s AND used_at IS NULL "
                     "AND expires_at>UTC_TIMESTAMP() FOR UPDATE", (hash_token(token),))
        if not record:
            fail(401, "INVALID_RESET_TOKEN", "Mã đặt lại không hợp lệ hoặc đã hết hạn.")
        execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(secret), record["user_id"]))
        execute("UPDATE reset_tokens SET used_at=UTC_TIMESTAMP() WHERE id=%s", (record["id"],))
        execute("UPDATE auth_tokens SET revoked_at=UTC_TIMESTAMP() WHERE user_id=%s", (record["user_id"],))
        db().commit()
    except Exception:
        db().rollback()
        raise
    return output({"message": "Đã đặt lại mật khẩu. Hãy đăng nhập lại."})


@bp.get("/me")
@require()
def me():
    return output({key: current_user()[key] for key in ("id", "email", "full_name", "phone", "role")})


@bp.patch("/me")
@require()
def update_me():
    data = json_body({"full_name", "phone"})
    if not data:
        fail(400, "MISSING_FIELD", "Cần full_name hoặc phone.")
    user = current_user()
    name = string(data["full_name"], "full_name", 2, 100) if "full_name" in data else user["full_name"]
    number = phone(data["phone"]) if "phone" in data else user["phone"]
    execute("UPDATE users SET full_name=%s,phone=%s WHERE id=%s", (name, number, user["id"]))
    db().commit()
    return output({"id": user["id"], "email": user["email"], "full_name": name, "phone": number, "role": user["role"]})
