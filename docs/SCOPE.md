# Đối chiếu test plan Stardust Fashion

Nguồn: `TestPlan.docx` do nhóm cung cấp, phiên bản tài liệu ghi **1.0 — Dự thảo kế hoạch** ngày 22/09/2026. Người dùng nói giảng viên đã duyệt; nhóm cần xác nhận đây chính là bản đã duyệt trước khi chốt kết quả kiểm thử. Mã CN01–CN11 dưới đây là mã gốc trong tài liệu. Test plan không có mã test case cụ thể; mã trong Postman dạng `CNxx-yy` là **tham chiếu tạm**.

Ảnh tham chiếu dùng chữ THORIQ, trong khi yêu cầu thương hiệu là Stardust Fashion. Giao diện theo bố cục editorial trắng → vàng chanh → xanh đậm → đen → cam, nhưng đổi toàn bộ thương hiệu thành Stardust Fashion. Ảnh không có trang tài khoản/giỏ/quản trị; các trang đó được thiết kế mới cùng hệ màu.

| Mục test plan | Chức năng xây dựng | Trang giao diện | API chính | Dữ liệu / điều kiện kiểm thử |
|---|---|---|---|---|
| CN01 Tài khoản | Đăng ký, đăng nhập, đăng xuất, quên/đặt lại/đổi mật khẩu, token hết hạn và thu hồi | `#login`, `#register`, `#forgot`, `#reset`, `#account` | `/auth/*` | Email chuẩn hóa, duy nhất; mật khẩu 8–64 có chữ và số; vai trò đăng ký luôn CUSTOMER; token A/B/admin |
| CN02 Hồ sơ | Xem/sửa tên, điện thoại bản thân | `#account` | `GET/PATCH /me` | Tên 2–100; điện thoại 10 số bắt đầu 0; từ chối email/role trong PATCH |
| CN03 Tra cứu | Danh mục, tìm kiếm, lọc giá/danh mục, phân trang, chi tiết | `#shop`, `#product/{id}` | `GET /categories`, `/products`, `/products/{id}` | Chỉ danh mục/sản phẩm hoạt động; page≥1, limit 1–100, min≤max |
| CN04 Biến thể | Xem size/màu/tồn kho; hàng hết vẫn hiển thị | `#product/{id}` | `GET /products/{id}/variants` | Ít nhất 2 biến thể; tồn 0 không mua được; 404 với ID sai |
| CN05 Giỏ | Xem/thêm/cộng/sửa/xóa dòng, tách theo khách | `#cart` | `GET /cart`, `POST/PATCH/DELETE /cart/items` | Số lượng 1–99, không quá kho; không giữ chỗ/trừ kho |
| CN06 Đơn & thanh toán | Đặt toàn bộ giỏ, giá backend, phí 30.000, COD/MoMo sandbox, kết quả MoMo có chữ ký | `#checkout`, `#orders`, MoMo redirect | `POST /orders`, `POST /orders/{id}/payments/momo`, IPN | Giỏ không rỗng, mọi dòng hợp lệ; snapshot; transaction MySQL; MoMo 1.000–50.000.000 VND |
| CN07 Đơn khách | Lịch sử, chi tiết, hủy PENDING, hoàn kho một lần | `#orders` | `GET /orders`, `GET /orders/{id}`, `PATCH /orders/{id}/cancel` | Khách A không đọc/hủy đơn B; hủy lặp 409 |
| CN08 Danh mục admin | Xem/thêm/sửa/ngừng/xóa khi rỗng | `#admin` → Danh mục | `/admin/categories` | Tên chuẩn hóa duy nhất, không xóa khi còn sản phẩm kể cả ngừng bán |
| CN09 Sản phẩm & kho admin | Thêm/sửa/ngừng sản phẩm; biến thể; tồn kho | `#admin` → Sản phẩm & kho | `/admin/products`, `/admin/variants/{id}` | Giá 1–100 triệu; kho 0–100.000; không trùng size–màu; sản phẩm mới ngừng bán |
| CN10 Đơn admin | Xem/lọc/chi tiết/chuyển trạng thái, hủy hoàn kho | `#admin` → Đơn hàng | `/admin/orders`, `/admin/orders/{id}/status` | PENDING→CONFIRMED/CANCELLED; CONFIRMED→SHIPPING/CANCELLED; SHIPPING→COMPLETED |
| CN11 Hiệu năng | Đo thời gian phản hồi và tải 100 người dùng | Không có trang chức năng | `GET /products` và các API qua Postman/`tools/load_test.py` | Mục tiêu <3 giây; phải chạy với MySQL và ghi kết quả, chưa được mặc định PASS |

## Vai trò và quyền

- Khách chưa đăng nhập: xem danh mục, sản phẩm, biến thể; đăng ký/đăng nhập/quên mật khẩu.
- Khách hàng: hồ sơ, giỏ, tạo và xem đơn của chính mình, hủy đơn PENDING, bắt đầu thanh toán MoMo cho đơn của mình.
- Quản trị viên: hồ sơ, danh mục, sản phẩm, biến thể/kho và tất cả đơn. API giỏ/đơn của khách chỉ dành CUSTOMER.

API lấy danh tính từ Bearer token, không nhận `userId` từ client cho `/me`, `/cart`, `/orders`. Tài khoản khách A/B là cùng vai trò để thử quyền sở hữu.

## Quy tắc dữ liệu và kết quả

- Khi đặt hàng: khóa hàng giỏ và từng biến thể trong giao dịch InnoDB; tính giá hiện tại × số lượng, cộng **30.000 ₫** một lần; lưu snapshot; trừ kho và xóa giỏ cùng giao dịch. Bất kỳ lỗi nào rollback toàn bộ.
- Hủy: khóa đơn, hoàn từng biến thể đúng một lần; trạng thái CANCELLED làm lần hủy sau trả 409. Đơn cũ giữ tên, size, màu, giá, địa chỉ đã chụp.
- Sản phẩm mới mặc định ngừng bán; cần ảnh và ít nhất một biến thể hoạt động trước khi mở bán. Trạng thái danh mục cũng quyết định khả năng mua.
- HTTP: 200 đọc/cập nhật/đăng nhập; 201 tạo; 204 xóa/đăng xuất; 400 dữ liệu sai; 401 thiếu/sai token; 403 sai vai trò; 404 không tồn tại/khác chủ; 409 trùng, thiếu kho, trạng thái không hợp lệ.

## Điểm cần nhóm xác nhận hoặc đo thực tế

1. Test plan ghi “dự thảo” và không có hợp đồng endpoint/JSON cuối cùng. Bộ API trong `docs/API.md` là **đề xuất triển khai của dự án**, cần nhóm dùng bản này làm đặc tả thực thi hoặc cập nhật test plan sau khi giảng viên đồng ý.
2. Người dùng chọn **MoMo sandbox** sau khi đọc plan. Tài khoản MoMo for Business, khóa test và IPN URL HTTPS công khai chưa có. COD chạy độc lập; MoMo không thể xác minh end-to-end trên máy này cho tới khi nhóm cấu hình.
3. MoMo giới hạn số tiền ví 1.000–50.000.000 VND theo tài liệu hiện tại. Đơn ONLINE ngoài giới hạn trả 409 ngay khi đặt, trước khi trừ kho, dù test plan cho giá sản phẩm tới 100 triệu. Đây là giới hạn dịch vụ, không thay đổi giá sản phẩm của plan.
4. Plan vừa giới hạn kho tối đa 100.000 vừa yêu cầu mọi đơn hủy hợp lệ hoàn kho. Nếu admin đặt tồn kho lên 100.000 sau khi bán, hoàn đơn sẽ vượt giới hạn. Hệ thống trả 409 và không hủy cho tới khi kho được giảm; nhóm cần chốt quy tắc cho tình huống này.
5. Hủy đơn đã thanh toán MoMo có thể cần hoàn tiền, trong khi hoàn tiền nằm ngoài scope. Bản sandbox ghi CANCELLED và hoàn kho nhưng **không gửi giao dịch hoàn tiền MoMo**. Nhóm không nên dùng luồng này với tiền thật.
6. Quên mật khẩu không tích hợp email (ngoài scope dịch vụ email trong plan); mã đặt lại chỉ được trả trong `APP_ENV=development`, có hạn 15 phút. Cần SMTP nếu muốn dùng ngoài localhost.
7. CN11 và các ca đồng thời, đặc biệt đặt/hủy/đổi kho cạnh tranh, chỉ được ghi PASS sau khi nhóm chạy Postman và script tải trên máy có MySQL. Kiểm tra giao diện phải thực hiện trực tiếp trên trình duyệt; Postman không đánh giá bố cục hay responsive.

## Những gì Postman kiểm được và không kiểm được

Postman kiểm status, schema JSON, quyền, validation, trạng thái đơn, giá/kho trước–sau, callback MoMo giả có chữ ký (nếu nhóm có khóa test), thời gian request. Tải 100 người cần script chạy đồng thời; Collection Runner tuần tự không đủ. Bố cục, màu, cỡ màn hình và thao tác trên UI phải xem bằng trình duyệt và không thuộc tiêu chí PASS API của plan.
