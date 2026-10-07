# API Stardust Fashion v1

Base URL: `http://127.0.0.1:5000/api/v1`. JSON UTF-8. API bảo vệ dùng `Authorization: Bearer <token>`. Các request có body dùng `Content-Type: application/json`. Không gửi `userId` để chọn người dùng; server lấy từ token. Tất cả lỗi có dạng:

```json
{"error":{"code":"OUT_OF_STOCK","message":"Không đủ tồn kho cho biến thể này."}}
```

## Endpoint

| Method | Đường dẫn sau base URL | Quyền | Mục đích / body chính |
|---|---|---|---|
| GET | `/health` | Công khai | Kiểm tra kết nối MySQL |
| POST | `/auth/register` | Công khai | `{email,password,full_name,phone?}`; 201, role luôn CUSTOMER |
| POST | `/auth/login` | Công khai | `{email,password}`; 200, nhận token 24 giờ |
| POST | `/auth/logout` | Đã đăng nhập | Body `{}`; 204, thu hồi token hiện tại |
| POST | `/auth/change-password` | Đã đăng nhập | `{current_password,new_password}`; 200 |
| POST | `/auth/forgot-password` | Công khai | `{email}`; 200; dev trả `reset_token` nếu email tồn tại |
| POST | `/auth/reset-password` | Công khai | `{reset_token,new_password}`; 200; thu hồi token đăng nhập |
| GET/PATCH | `/me` | Đã đăng nhập | Xem hồ sơ / sửa `{full_name?,phone?}` |
| GET | `/categories` | Công khai | Danh mục đang hoạt động |
| GET | `/products` | Công khai | `search`, `categoryId`, `minPrice`, `maxPrice`, `page=1`, `limit=12` |
| GET | `/products/{id}` | Công khai | Chi tiết kèm biến thể hoạt động |
| GET | `/products/{id}/variants` | Công khai | Size–màu, tồn kho |
| GET | `/cart` | CUSTOMER | Giỏ riêng, tiền hàng tạm tính |
| POST | `/cart/items` | CUSTOMER | `{variant_id,quantity}`; 201 dòng mới, 200 cộng dòng cũ |
| PATCH | `/cart/items/{id}` | CUSTOMER | `{quantity}`; 200, đặt số lượng mới |
| DELETE | `/cart/items/{id}` | CUSTOMER | 204 |
| POST | `/orders` | CUSTOMER | `{recipient_name,recipient_phone,address,payment_method}`; COD hoặc ONLINE; 201 |
| GET | `/orders` | CUSTOMER | Danh sách đơn của mình |
| GET | `/orders/{id}` | CUSTOMER | Chi tiết đơn của mình |
| PATCH | `/orders/{id}/cancel` | CUSTOMER | `{status:"CANCELLED"}`; chỉ PENDING; 200 |
| POST | `/orders/{id}/payments/momo` | CUSTOMER | Body `{}`; tạo/trả URL MoMo sandbox |
| POST | `/payments/momo/ipn` | MoMo | Callback đã ký; 204; không dùng token khách |
| GET | `/admin/categories` | ADMIN | Tất cả danh mục |
| POST | `/admin/categories` | ADMIN | `{name,active?}`; 201 |
| PATCH | `/admin/categories/{id}` | ADMIN | `{name?,active?}`; 200 |
| DELETE | `/admin/categories/{id}` | ADMIN | 204 nếu không có sản phẩm |
| GET | `/admin/products` | ADMIN | Tất cả sản phẩm |
| GET | `/admin/products/{id}` | ADMIN | Chi tiết và mọi biến thể |
| POST | `/admin/products` | ADMIN | `{category_id,name,price,description?,image_url?}`; 201, mặc định ngừng bán |
| PATCH | `/admin/products/{id}` | ADMIN | `{category_id?,name?,price?,description?,image_url?,active?}`; 200 |
| POST | `/admin/products/{id}/variants` | ADMIN | `{size,color,stock,active?}`; 201 |
| PATCH | `/admin/variants/{id}` | ADMIN | `{stock?,active?}`; 200, không sửa size/màu |
| GET | `/admin/orders?status=PENDING` | ADMIN | Tất cả hoặc lọc trạng thái |
| GET | `/admin/orders/{id}` | ADMIN | Chi tiết đơn bất kỳ |
| PATCH | `/admin/orders/{id}/status` | ADMIN | `{status}`; 200 |

`GET /checkout/momo-return` là URL trở về của trình duyệt, nằm ngoài tiền tố `/api/v1`.

## Body và response mẫu

Đăng nhập:

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email":"an@stardust.test","password":"Customer123"}
```

```json
{"token":"<random-token>","token_type":"Bearer","expires_in":86400,"user":{"id":2,"email":"an@stardust.test","full_name":"Nguyễn An","phone":"0900000002","role":"CUSTOMER"}}
```

Lọc sản phẩm:

```http
GET /api/v1/products?search=tee&categoryId=1&minPrice=100000&maxPrice=300000&page=1&limit=12
```

Trả `{ "items": [ ... ], "page": 1, "limit": 12, "total": 2 }`. Khi không có kết quả, `items` rỗng và `total=0`.

Tạo đơn:

```http
POST /api/v1/orders
Authorization: Bearer <token_customer_a>
Content-Type: application/json

{"recipient_name":"Nguyễn An","recipient_phone":"0900000002","address":"12 Nguyễn Huệ, Quận 1, TP.HCM","payment_method":"COD"}
```

Response 201 gồm `id`, `status:"PENDING"`, `payment_status:"UNPAID"`, `subtotal`, `shipping_fee:30000`, `total` và `items` snapshot. Nếu là ONLINE, response thêm `payment_start_endpoint`; gọi endpoint đó để lấy `payment_url` từ MoMo. Trường giá hoặc tổng tiền do client thêm bị từ chối 400 `UNKNOWN_FIELD`.

Ví dụ 2 áo × 150.000 + 1 quần × 250.000: `subtotal=550000`, `shipping_fee=30000`, `total=580000`.

Chuyển trạng thái: `PENDING→CONFIRMED/CANCELLED`; `CONFIRMED→SHIPPING/CANCELLED`; `SHIPPING→COMPLETED`. Khách chỉ hủy `PENDING`; admin hủy `PENDING` hoặc `CONFIRMED`. Online phải thanh toán SUCCESS trước khi giao hàng. COD chuyển `payment_status` sang SUCCESS khi COMPLETED.

## Chuẩn bị luồng Postman

1. Gọi `/health`, `/auth/login` cho customer A/B và admin; lưu token từng vai trò.
2. Lấy danh mục, sản phẩm, biến thể. Dữ liệu seed có biến thể #1 tồn 5 và #8 thuộc quần tồn 9.
3. Khách A `POST /cart/items` với `{ "variant_id":1,"quantity":2 }`, sau đó thêm biến thể #8 số lượng 1.
4. `GET /cart`, rồi `POST /orders` theo body trên. Kiểm `subtotal=550000`, `total=580000`, giỏ rỗng và kho giảm. ID đơn lưu từ response.
5. Dùng token B gọi `GET /orders/{id}` và hủy đơn A, phải nhận 404. Dùng token A hủy đơn PENDING, kho hoàn một lần; hủy lại 409.
6. Dùng admin tạo đơn mới và chuyển trạng thái theo từng bước. Thử bước sai phải 409. Khi sửa kho hoặc hủy, đọc lại biến thể/đơn để xác nhận dữ liệu cuối.
7. Với ONLINE, cấu hình khóa MoMo sandbox trong `.env`, gọi `POST /orders/{id}/payments/momo`, mở `payment_url` trên trình duyệt. IPN phải có URL HTTPS công khai. Không tự gửi `result=SUCCESS` bằng token khách; chỉ callback có chữ ký MoMo được chấp nhận.

## Mã lỗi thường gặp

`INVALID_JSON`, `MISSING_FIELD`, `UNKNOWN_FIELD`, `INVALID_EMAIL`, `INVALID_PASSWORD`, `EMAIL_EXISTS`, `INVALID_TOKEN`, `FORBIDDEN`, `PRODUCT_NOT_FOUND`, `VARIANT_NOT_FOUND`, `OUT_OF_STOCK`, `ITEM_INACTIVE`, `EMPTY_CART`, `INVALID_ORDER_TRANSITION`, `CATEGORY_HAS_PRODUCTS`, `MOMO_NOT_CONFIGURED`, `MOMO_UNAVAILABLE`. HTTP status cụ thể theo bảng quy ước trong `docs/SCOPE.md`.

## MoMo sandbox

Tích hợp dùng MoMo Wallet one-time `captureWallet` trên `/v2/gateway/api/create`, HMAC-SHA256 và xác minh chữ ký response/IPN. `requestId` được lưu để thử lại cùng mã khi kết nối timeout. IPN phải có HTTPS công khai và phản hồi 204; redirect được xác minh cùng chữ ký khi trình duyệt trở về. Theo [tài liệu MoMo Wallet one-time](https://developers.momo.vn/v3/docs/payment/api/wallet/onetime/) và [tài liệu IPN](https://developers.momo.vn/v3/docs/payment/api/result-handling/notification/). Nhóm lấy khóa test từ [MoMo for Business](https://developers.momo.vn/v3/docs/payment/onboarding/merchant-profile/); không đặt khóa vào Postman Collection hoặc Git.
