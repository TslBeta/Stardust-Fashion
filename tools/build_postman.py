"""Create importable Postman Collection v2.1 and Environment without secrets."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "postman"
OUT.mkdir(exist_ok=True)


def req(name, method, path, body=None, token=None, status=200, tests="", prerequest=""):
    headers = [{"key": "Content-Type", "value": "application/json"}]
    if token:
        headers.append({"key": "Authorization", "value": "Bearer {{" + token + "}}"})
    item = {"name": name, "request": {"method": method, "header": headers,
            "url": "{{base_url}}" + path}}
    if body is not None:
        raw = json.dumps(body, ensure_ascii=False)
        raw = raw.replace('"{{category_id}}"', '{{category_id}}')
        item["request"]["body"] = {"mode": "raw", "raw": raw,
                                   "options": {"raw": {"language": "json"}}}
    scripts = []
    if prerequest:
        scripts.append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": prerequest.splitlines()}})
    check = f"pm.test('HTTP {status}', function () {{ pm.response.to.have.status({status}); }});"
    if status != 204:
        check += "\npm.test('JSON response', function () { pm.response.to.be.json; });"
    if tests:
        check += "\n" + tests
    scripts.append({"listen": "test", "script": {"type": "text/javascript", "exec": check.splitlines()}})
    item["event"] = scripts
    return item


def folder(code, name, items):
    return {"name": f"{code} — {name}", "item": items}


items = [
    folder("SETUP", "Smoke và đăng nhập", [
        req("GET health", "GET", "/health", tests="pm.test('MySQL connected', () => pm.expect(pm.response.json().database).to.eql('mysql'));"),
        req("Login customer A", "POST", "/auth/login", {"email": "an@stardust.test", "password": "Customer123"},
            tests="pm.environment.set('token_customer_a', pm.response.json().token); pm.test('customer role', () => pm.expect(pm.response.json().user.role).to.eql('CUSTOMER'));"),
        req("Login customer B", "POST", "/auth/login", {"email": "binh@stardust.test", "password": "Customer123"},
            tests="pm.environment.set('token_customer_b', pm.response.json().token);"),
        req("Login admin", "POST", "/auth/login", {"email": "admin@stardust.test", "password": "Admin12345"},
            tests="pm.environment.set('token_admin', pm.response.json().token); pm.test('admin role', () => pm.expect(pm.response.json().user.role).to.eql('ADMIN'));"),
    ]),
    folder("CN01", "Tài khoản", [
        req("Register duplicate email → 409", "POST", "/auth/register", {"email": "  AN@stardust.test  ", "password": "Customer123", "full_name": "Nguyễn An"}, status=409),
        req("Bad login → 401", "POST", "/auth/login", {"email": "an@stardust.test", "password": "wrongpass"}, status=401),
        req("Forgot password development", "POST", "/auth/forgot-password", {"email": "nobody@stardust.test"}),
        req("Missing token → 401", "GET", "/me", status=401),
    ]),
    folder("CN02", "Hồ sơ", [
        req("Customer A profile", "GET", "/me", token="token_customer_a", tests="pm.test('Own email', () => pm.expect(pm.response.json().email).to.eql('an@stardust.test'));"),
        req("Cannot change role", "PATCH", "/me", {"role": "ADMIN"}, "token_customer_a", 400),
    ]),
    folder("CN03", "Tra cứu sản phẩm", [
        req("Categories", "GET", "/categories", tests="pm.test('Categories are array', () => pm.expect(pm.response.json()).to.be.an('array'));"),
        req("Products, filter and page", "GET", "/products?categoryId=1&minPrice=100000&maxPrice=300000&page=1&limit=12",
            tests="const x=pm.response.json(); pm.test('Pagination shape', () => {pm.expect(x.items).to.be.an('array');pm.expect(x.page).to.eql(1);}); pm.environment.set('product_id', x.items[0]?.id || 1);"),
        req("Invalid page → 400", "GET", "/products?page=0", status=400),
        req("Missing product → 404", "GET", "/products/999999", status=404),
    ]),
    folder("CN04", "Biến thể và tồn kho", [
        req("Product detail", "GET", "/products/{{product_id}}", tests="pm.test('Variants exist', () => pm.expect(pm.response.json().variants.length).to.be.above(0)); pm.environment.set('variant_id', 1);"),
        req("Variant list", "GET", "/products/{{product_id}}/variants", tests="pm.test('Stock exposed', () => pm.expect(pm.response.json()[0]).to.have.property('stock'));"),
    ]),
    folder("CN05", "Giỏ hàng", [
        req("Cart A", "GET", "/cart", token="token_customer_a"),
        req("Add 2 tee", "POST", "/cart/items", {"variant_id": 1, "quantity": 2}, "token_customer_a", 201,
            "pm.environment.set('cart_item_id', pm.response.json().id);"),
        req("Add pants", "POST", "/cart/items", {"variant_id": 8, "quantity": 1}, "token_customer_a", 201),
        req("Cart sum", "GET", "/cart", token="token_customer_a",
            tests="pm.test('550000 subtotal', () => pm.expect(pm.response.json().subtotal).to.eql(550000));"),
        req("Quantity zero → 400", "PATCH", "/cart/items/{{cart_item_id}}", {"quantity": 0}, "token_customer_a", 400),
        req("B cannot edit A cart → 404", "PATCH", "/cart/items/{{cart_item_id}}", {"quantity": 1}, "token_customer_b", 404),
    ]),
    folder("CN06", "Đặt hàng và thanh toán", [
        req("Create COD order", "POST", "/orders", {"recipient_name": "Nguyễn An", "recipient_phone": "0900000002",
            "address": "12 Nguyễn Huệ, Quận 1, TP.HCM", "payment_method": "COD"}, "token_customer_a", 201,
            "const x=pm.response.json(); pm.environment.set('order_id',x.id); pm.test('total 580000 and pending',()=>{pm.expect(x.subtotal).to.eql(550000);pm.expect(x.shipping_fee).to.eql(30000);pm.expect(x.total).to.eql(580000);pm.expect(x.status).to.eql('PENDING');});"),
        req("Cart empty after order", "GET", "/cart", token="token_customer_a",
            tests="pm.test('cart cleared',()=>pm.expect(pm.response.json().items).to.have.length(0));"),
        req("Empty cart order → 409", "POST", "/orders", {"recipient_name": "Nguyễn An", "recipient_phone": "0900000002",
            "address": "12 Nguyễn Huệ, Quận 1, TP.HCM", "payment_method": "COD"}, "token_customer_a", 409),
        req("MoMo start (manual with keys and ONLINE order)", "POST", "/orders/{{momo_order_id}}/payments/momo", {}, "token_customer_a", 200,
            prerequest="if (pm.environment.get('momo_enabled') !== 'true') pm.execution.skipRequest();"),
    ]),
    folder("CN07", "Đơn khách", [
        req("Own orders", "GET", "/orders", token="token_customer_a"),
        req("Own order detail", "GET", "/orders/{{order_id}}", token="token_customer_a"),
        req("B cannot view A order → 404", "GET", "/orders/{{order_id}}", token="token_customer_b", status=404),
        req("B cannot cancel A order → 404", "PATCH", "/orders/{{order_id}}/cancel", {"status": "CANCELLED"}, "token_customer_b", 404),
        req("A cancels pending", "PATCH", "/orders/{{order_id}}/cancel", {"status": "CANCELLED"}, "token_customer_a",
            tests="pm.test('Cancelled',()=>pm.expect(pm.response.json().status).to.eql('CANCELLED'));"),
        req("Repeat cancel → 409", "PATCH", "/orders/{{order_id}}/cancel", {"status": "CANCELLED"}, "token_customer_a", 409),
    ]),
    folder("CN08", "Quản trị danh mục", [
        req("Customer cannot list admin categories → 403", "GET", "/admin/categories", token="token_customer_a", status=403),
        req("Admin categories", "GET", "/admin/categories", token="token_admin"),
        req("Create unique category", "POST", "/admin/categories", {"name": "Test {{run_id}}", "active": True}, "token_admin", 201,
            "pm.environment.set('category_id',pm.response.json().id);", "pm.environment.set('run_id', Date.now().toString());"),
        req("Duplicate category → 409", "POST", "/admin/categories", {"name": " test {{run_id}} ", "active": True}, "token_admin", 409),
    ]),
    folder("CN09", "Quản trị sản phẩm và kho", [
        req("Create inactive product", "POST", "/admin/products", {"category_id": "{{category_id}}", "name": "TEST TEE {{run_id}}", "price": 150000,
            "image_url": "/static/images/tee.png", "description": "Test product"}, "token_admin", 201,
            "pm.environment.set('admin_product_id',pm.response.json().id);"),
        req("Add variant", "POST", "/admin/products/{{admin_product_id}}/variants", {"size": "M", "color": "Black", "stock": 5}, "token_admin", 201,
            "pm.environment.set('admin_variant_id',pm.response.json().id);"),
        req("Duplicate variant → 409", "POST", "/admin/products/{{admin_product_id}}/variants", {"size": " m ", "color": "black", "stock": 5}, "token_admin", 409),
        req("Activate product", "PATCH", "/admin/products/{{admin_product_id}}", {"active": True}, "token_admin"),
        req("Stock 100001 → 400", "PATCH", "/admin/variants/{{admin_variant_id}}", {"stock": 100001}, "token_admin", 400),
    ]),
    folder("CN10", "Quản trị đơn", [
        req("Add tee for second order", "POST", "/cart/items", {"variant_id": 1, "quantity": 1}, "token_customer_a", 201),
        req("Create second COD order", "POST", "/orders", {"recipient_name": "Nguyễn An", "recipient_phone": "0900000002",
            "address": "12 Nguyễn Huệ, Quận 1, TP.HCM", "payment_method": "COD"}, "token_customer_a", 201,
            "pm.environment.set('admin_order_id',pm.response.json().id);"),
        req("Admin list orders", "GET", "/admin/orders?status=PENDING", token="token_admin"),
        req("Admin confirm", "PATCH", "/admin/orders/{{admin_order_id}}/status", {"status": "CONFIRMED"}, "token_admin"),
        req("Repeat confirm → 409", "PATCH", "/admin/orders/{{admin_order_id}}/status", {"status": "CONFIRMED"}, "token_admin", 409),
        req("Admin shipping", "PATCH", "/admin/orders/{{admin_order_id}}/status", {"status": "SHIPPING"}, "token_admin"),
        req("Admin complete", "PATCH", "/admin/orders/{{admin_order_id}}/status", {"status": "COMPLETED"}, "token_admin",
            tests="pm.test('COD paid at completion',()=>pm.expect(pm.response.json().payment_status).to.eql('SUCCESS'));"),
    ]),
    folder("CN11", "Hiệu năng", [
        req("Products under 3 seconds", "GET", "/products", tests="pm.test('Response < 3000 ms',()=>pm.expect(pm.response.responseTime).to.be.below(3000));"),
    ]),
]

collection = {"info": {"name": "Stardust Fashion API Test", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                       "description": "CN01–CN11. Run on a reset seed database. MoMo request is manual and requires sandbox keys."},
              "item": items}
environment = {"name": "Stardust Fashion Local", "values": [
    {"key": key, "value": value, "enabled": True} for key, value in {
        "base_url": "http://127.0.0.1:5000/api/v1", "token_customer_a": "", "token_customer_b": "", "token_admin": "",
        "category_id": "", "product_id": "", "variant_id": "", "cart_item_id": "", "order_id": "", "admin_product_id": "",
        "admin_variant_id": "", "admin_order_id": "", "momo_order_id": "", "momo_enabled": "false", "run_id": ""
    }.items()]}

(OUT / "Stardust-Fashion.postman_collection.json").write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "Stardust-Fashion.postman_environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
print("Wrote Postman Collection and Environment to", OUT)
