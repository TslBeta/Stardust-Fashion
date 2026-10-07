# Kết quả kiểm chứng hiện có — 07/10/2026

Đây là kết quả thực chạy trong workspace, **không phải** báo cáo PASS của toàn bộ test plan. Mỗi đợt kiểm thử của nhóm cần ghi build/commit, máy, MySQL, thời gian, người chạy, request/response và dữ liệu sau thao tác.

| Kiểm tra | Kết quả | Bằng chứng / giới hạn |
|---|---|---|
| Cài thư viện Python trong `.venv` | Đạt | Flask 3.1.3, PyMySQL 1.2.3 với RSA, Waitress 3.0.2 đã cài |
| Cú pháp Python | Đạt | `python -m compileall -q app.py serve.py manage.py stardust tools` exit 0 |
| Đăng ký URL Flask | Đạt | `app.url_map` có các endpoint CN01–CN10 và MoMo |
| Giao diện tĩnh | Đạt | Flask test client: `/`, `/static/style.css`, `/static/app.js` đều HTTP 200 |
| API không token | Đạt | `GET /api/v1/me` trả 401 |
| Validation không cần DB | Đạt | `POST /api/v1/auth/register` với email/mật khẩu sai trả 400 |
| Trang chủ desktop | Đã xem | Edge headless chụp `preview-home.png`; bố cục và ảnh hiển thị |
| Giao diện kích thước nhỏ | Đã xem và sửa | Ảnh `preview-mobile-fixed.png`; chữ tiêu đề đã thu gọn. Edge headless có giới hạn chiều rộng cửa sổ tối thiểu, nên cần kiểm tra thêm trên điện thoại thật hoặc DevTools. |
| Postman Collection | Đã tạo, chưa chạy | 12 folder, 49 request, Environment 15 biến; file JSON parse được. Chưa gán PASS cho assertion. |
| Kết nối MySQL với database dự án | Chưa chạy | Dịch vụ MySQL94 của người dùng đang chạy, nhưng `.env` và mật khẩu của người dùng chưa được điền. `GET /health` trả 503 `DATABASE_UNAVAILABLE`/MySQL 1045 trong môi trường hiện tại. |
| Đặt/hủy đơn, quyền, kho và đồng thời | NOT RUN | Cần `.env`, `manage.py init-db`, rồi chạy Postman/`tools/concurrency_test.py`. |
| CN11 tải 100 người và <3 giây | NOT RUN | Cần server + MySQL thực tế; chạy `tools/load_test.py`, lưu số liệu. |
| MoMo sandbox end-to-end | NOT RUN | Cần khóa sandbox và HTTPS IPN URL công khai. |

Không dùng bảng này để kết luận Exit Criteria mục 6 của test plan đã đạt.
