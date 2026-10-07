# Stardust Fashion — chạy từ đầu trên máy Windows

Đây là website bán quần áo dùng **Python + Flask/Waitress + MySQL**. Một chương trình phục vụ cả giao diện và API tại cổng `5000`; MySQL dùng cổng `3306`. `Postman` gửi request đến `http://127.0.0.1:5000/api/v1`. Python được chọn để dự án chỉ cần một terminal cho web và không cần Node.js/npm. `requirements.txt` là danh sách thư viện; không có `package.json` vì dự án không dùng Node.js.

Phạm vi theo test plan ở [docs/SCOPE.md](docs/SCOPE.md), hợp đồng API ở [docs/API.md](docs/API.md), kết quả đã kiểm chứng ở [docs/VERIFICATION.md](docs/VERIFICATION.md). Website chạy với **MySQL**, không dùng SQLite/MongoDB. Ảnh tham chiếu chỉ định hướng giao diện; không thay đổi quy tắc nghiệp vụ của plan.

## 1. Cây thư mục

```text
StardustFashion/
├─ .env.example                 mẫu cấu hình; sao chép thành .env
├─ .gitignore                   loại bí mật và file sinh ra khỏi Git
├─ requirements.txt             thư viện Python cần cài
├─ app.py                       gắn API và trang chủ Flask
├─ serve.py                     chạy Waitress tại cổng 5000
├─ manage.py                    tạo/seed/kiểm tra/reset MySQL
├─ database/schema.sql          bảng, khóa chính/ngoại và ràng buộc MySQL
├─ stardust/
│  ├─ __init__.py               đánh dấu gói Python
│  ├─ db.py                     kết nối MySQL, đọc .env
│  ├─ common.py                 validation và phản hồi lỗi
│  ├─ auth.py                   tài khoản, hồ sơ, token
│  ├─ catalog.py                danh mục, sản phẩm, biến thể
│  ├─ commerce.py               giỏ, đơn, kho
│  └─ momo.py                   MoMo sandbox, chữ ký, IPN
├─ static/
│  ├─ index.html                khung giao diện
│  ├─ style.css                 bố cục responsive
│  ├─ app.js                    giao diện gọi API
│  └─ images/*.png              ảnh chiến dịch/sản phẩm đã tạo
├─ postman/
│  ├─ Stardust-Fashion.postman_collection.json    request/assertion CN01–CN11
│  └─ Stardust-Fashion.postman_environment.json   biến mẫu, không có token
├─ docs/SCOPE.md                đối chiếu test plan
├─ docs/API.md                  endpoint, body, status
├─ docs/VERIFICATION.md         kết quả kiểm chứng và mục chưa chạy
└─ tools/
   ├─ build_postman.py          tái tạo 2 file Postman
   ├─ load_test.py              100 request đồng thời cho CN11
   ├─ concurrency_test.py       2 khách tranh 1 sản phẩm
   └─ read_docx.py             công cụ đọc test plan DOCX
```

Các file trên đã có sẵn trong thư mục này, **không cần tự tạo hay dán code**. `.venv/` được Python tự tạo ở bước 3. `.env` phải tự sao chép từ mẫu và điền mật khẩu MySQL trên máy của bạn. Không tạo file `.js.txt`, `.env.txt` hoặc `package-lock.json`.

## 2. Kiểm tra phần mềm

1. Mở **File Explorer** tới `C:\StardustFashion`. Trong thanh địa chỉ gõ `powershell` rồi Enter. Mọi lệnh PowerShell dưới đây chạy tại thư mục này, trừ khi nói khác.
2. Gõ `python --version` và `python -m pip --version`. Cần Python 3.10 trở lên. Nếu thiếu, cài từ [python.org](https://www.python.org/downloads/windows/) và chọn **Add Python to PATH**, rồi mở PowerShell mới.
3. Kiểm tra MySQL: `Get-Service -Name '*mysql*'`. Máy hiện tại đã thấy dịch vụ `MySQL94` đang chạy. Nếu máy khác chưa có, cài **MySQL Server** và **MySQL Workbench** từ trang [MySQL Downloads](https://dev.mysql.com/downloads/); ghi nhớ mật khẩu tài khoản MySQL do bạn tự đặt. Nếu dịch vụ ở trạng thái Stopped, mở Windows Services và chọn Start cho dịch vụ MySQL.
4. Mở **VS Code** → **File** → **Open Folder** → chọn `C:\StardustFashion`. Bật hiển thị đuôi file trong File Explorer (**View → Show → File name extensions**) để tránh nhầm `.env.txt`.

## 3. Tạo môi trường Python và cài thư viện

Trong PowerShell tại `C:\StardustFashion`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Dấu hiệu đúng: dòng cuối có `Successfully installed ... Flask ... PyMySQL ... waitress`, hoặc `Requirement already satisfied`. Có thể chạy `Get-ChildItem .venv\Scripts\python.exe` để xác nhận. Không cần mở `requirements.txt` để xem website.

## 4. Cấu hình MySQL

Trong VS Code, tìm `.env.example` ở thư mục gốc. Nhấp phải → **Copy**, rồi **Paste** cùng thư mục và đổi tên bản sao thành đúng `.env`. Mở `.env`, sửa các dòng:

```dotenv
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=stardust_fashion
MYSQL_USER=root
MYSQL_PASSWORD=mat-khau-mysql-cua-ban
APP_HOST=127.0.0.1
APP_PORT=5000
APP_ENV=development
```

Chỉ thay mật khẩu trong `.env` trên máy; không gửi vào chat hoặc GitHub. `MYSQL_DATABASE` phải giữ `stardust_fashion`. Lưu bằng **Ctrl+S**. Nếu dùng tài khoản MySQL khác root, thay `MYSQL_USER` và đảm bảo tài khoản đó có quyền tạo database/tables. `MOMO_*` có thể để trống lúc đầu; COD và toàn bộ API còn lại vẫn dùng được.

**Cách dễ nhất để tạo database, bảng và dữ liệu mẫu:**

```powershell
.\.venv\Scripts\python.exe manage.py init-db
.\.venv\Scripts\python.exe manage.py check-db
```

Dấu hiệu đúng: `Initialized Stardust Fashion...`, sau đó `{'name': 'stardust_fashion', 'users': 3}`. `init-db` tạo database nếu chưa có, dùng `database/schema.sql` và seed 3 tài khoản, 4 danh mục, 5 sản phẩm, 10 biến thể. Chạy lại khi đã có user sẽ **không** ghi đè dữ liệu.

**Nếu muốn xem/chạy SQL trong MySQL Workbench:** mở Workbench → kết nối MySQL bằng tài khoản của bạn → **File → Open SQL Script** → chọn `C:\StardustFashion\database\schema.sql` → nhấn biểu tượng tia sét để chạy. Sau đó quay lại PowerShell chạy ` .\.venv\Scripts\python.exe manage.py init-db ` để thêm dữ liệu mẫu (lệnh này chỉ tạo bảng còn thiếu). Nếu Workbench hỏi mật khẩu, nhập trong Workbench, không lưu vào mã nguồn.

**Reset dữ liệu chỉ trong database của dự án:** lệnh dưới đây xóa **toàn bộ** đơn, tài khoản và dữ liệu đang có trong `stardust_fashion`, tạo lại schema rồi seed. Không chạy khi nhóm khác đang kiểm thử hoặc cần giữ bằng chứng. Lệnh có cờ xác nhận riêng và từ chối chạy nếu `.env` chỉ sang database khác.

```powershell
.\.venv\Scripts\python.exe manage.py reset-db --yes-reset-project-database
```

## 5. Chạy website

Chỉ cần **một cửa sổ PowerShell** tại `C:\StardustFashion`:

```powershell
.\.venv\Scripts\python.exe serve.py
```

Dấu hiệu đúng: `Stardust Fashion: http://127.0.0.1:5000`. Mở trình duyệt tại **http://127.0.0.1:5000/**. Thử API sức khỏe tại **http://127.0.0.1:5000/api/v1/health**; kết quả đúng là `{"status":"ok","database":"mysql"}`. Giao diện và backend dùng cùng địa chỉ nên không cần terminal thứ hai hay cấu hình CORS. Dừng bằng **Ctrl+C** trong PowerShell; chạy lại cùng lệnh.

### Tài khoản kiểm thử sau khi seed

| Vai trò | Email | Mật khẩu mẫu |
|---|---|---|
| Quản trị | `admin@stardust.test` | `Admin12345` |
| Khách A | `an@stardust.test` | `Customer123` |
| Khách B | `binh@stardust.test` | `Customer123` |

Trong trình duyệt: bấm **TÀI KHOẢN** → đăng nhập bằng khách A → **SHOP** → chọn sản phẩm và biến thể → thêm giỏ → đặt COD → xem/hủy đơn tại **ĐƠN HÀNG**. Đăng xuất, đăng nhập admin để xem danh mục, sản phẩm, kho và đổi trạng thái đơn. Khách B dùng để thử chặn truy cập đơn/giỏ của A. Mật khẩu này chỉ dành cho database seed cục bộ, không phải tài khoản thật.

## 6. Postman

1. Mở Postman → **Import** → chọn cả hai file trong `C:\StardustFashion\postman\`.
2. Ở góc phải Postman, chọn Environment **Stardust Fashion Local**. `base_url` đã là `http://127.0.0.1:5000/api/v1`; token/ID ban đầu rỗng.
3. Trước khi chạy Collection Runner toàn bộ, reset database thử nghiệm như bước 4. Chạy folder **SETUP** trước; các login lưu token A/B/admin tự động. Tiếp tục CN01 → CN11 theo thứ tự. Request MoMo trong CN06 tự bỏ qua nếu `momo_enabled=false`.
4. Muốn xem từng nghiệp vụ, mở request và nhấn **Send**. Tab **Test Results** cho assertion; body và HTTP status hiển thị ở dưới. Các ID được lưu vào Environment sau request tạo mới. Các case test không được coi là PASS chỉ vì file Collection đã được tạo.
5. Với 100 người đồng thời, trong PowerShell khác tại dự án chạy `python tools/load_test.py` khi web đang hoạt động. Script in số HTTP 200, median, p95, max và mục tiêu <3 giây. Để thử tranh mua 1 sản phẩm, reset DB trước rồi chạy `python tools/concurrency_test.py`; sau đó đọc lại đơn/kho trong Postman hoặc Workbench. Hai script có thể làm thay đổi dữ liệu hoặc đặt tải, chỉ chạy trên database thử nghiệm riêng.

## 7. MoMo sandbox (chỉ khi cần thử thanh toán online)

Theo [hướng dẫn MoMo](https://developers.momo.vn/v3/docs/payment/onboarding/merchant-profile/), nhóm cần tài khoản MoMo for Business để lấy **Partner Code, Access Key và Secret Key** của môi trường Test. Điền ba giá trị đó trong `.env`, không gửi khóa vào chat. MoMo gửi kết quả qua IPN server-to-server; `localhost` không nhận được IPN từ Internet. Dùng một HTTPS tunnel tạm thời cho bài thử:

1. Tải `cloudflared` bản Windows từ [trang Cloudflare Downloads](https://developers.cloudflare.com/tunnel/downloads/) và cài MSI, hoặc tải `.exe` rồi đặt đường dẫn tới nó trong PowerShell.
2. Giữ terminal chạy `serve.py`. Mở terminal thứ hai và chạy `cloudflared tunnel --url http://127.0.0.1:5000` (nếu dùng `.exe` tải rời, chạy bằng đường dẫn đầy đủ tới file đó). Nó in URL dạng `https://...trycloudflare.com`.
3. Trong `.env` đặt `MOMO_IPN_URL=https://...trycloudflare.com/api/v1/payments/momo/ipn` và `MOMO_REDIRECT_URL=http://127.0.0.1:5000/checkout/momo-return`. Đặt `APP_ENV=production` trong thời gian mở tunnel để không trả mã đặt lại mật khẩu trong response. Giữ nguyên tên biến, lưu file, **Ctrl+C** dừng web rồi chạy lại `serve.py` để đọc cấu hình mới. Giữ tunnel đang chạy.
4. Đặt đơn với `payment_method=ONLINE`; giao diện mở `payment_url` từ MoMo sandbox. Dùng ứng dụng/thiết bị test theo [hướng dẫn MoMo](https://developers.momo.vn/v3/docs/payment/onboarding/test-instructions/) để thanh toán. Quay lại **ĐƠN HÀNG** và kiểm `payment_status=SUCCESS` hoặc `FAILED`.

[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) dùng cho thử nghiệm, URL thay đổi mỗi lần mở và công khai với người có đường dẫn. Dùng database seed riêng, đóng tunnel sau khi thử. MoMo có thể không gọi được IPN nếu tunnel bị đóng; trong trường hợp đó redirect có chữ ký vẫn được xử lý khi trình duyệt quay về, nhưng nhóm phải ghi rõ giới hạn khi báo cáo. Không dùng thẻ/tài khoản thật. Hoàn tiền MoMo không nằm trong phạm vi dự án; xem `docs/SCOPE.md`.

## 8. Lỗi thường gặp

| Hiện tượng | Kiểm tra và sửa |
|---|---|
| `python` không nhận diện | Cài Python, chọn Add to PATH, mở PowerShell mới. |
| `No module named flask/pymysql/waitress` | Đứng tại `C:\StardustFashion`, chạy lại `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, rồi dùng đúng `.venv\Scripts\python.exe` để chạy web. |
| `Access denied for user` / MySQL 1045 | Sửa `MYSQL_USER` và `MYSQL_PASSWORD` trong `.env` bằng thông tin trên máy; không gửi mật khẩu. Sau khi lưu, mở terminal mới hoặc chạy lại Python. |
| `Unknown database` / MySQL 1049 | Giữ `MYSQL_DATABASE=stardust_fashion`, chạy `manage.py init-db`. |
| `Can't connect to MySQL server` / 2003 | Kiểm tra dịch vụ MySQL trong Windows Services, host `127.0.0.1`, cổng `3306`. |
| Trình duyệt không mở cổng 5000 | Kiểm tra terminal web còn chạy; nếu cổng bị chiếm, sửa `APP_PORT` trong `.env`, chạy lại và đổi URL Postman cho khớp. |
| 401 sau đăng xuất | Đúng hành vi: token bị thu hồi; đăng nhập lại để lấy token mới. |
| MoMo trả `MOMO_NOT_CONFIGURED` | Điền khóa sandbox và hai URL trong `.env`, chạy lại web. |
| MoMo có URL nhưng trạng thái không đổi | Kiểm tra tunnel/IPN URL còn hoạt động, và trình duyệt đã quay về redirect. Xem log terminal; đối chiếu request/response MoMo sandbox. |

## 9. Git và GitHub

**Git** lưu lịch sử mã nguồn trên máy. **GitHub** là dịch vụ lưu repository trực tuyến; website chạy local không cần GitHub. Máy hiện tại chưa thấy lệnh `git`, nên nếu cần, cài [Git for Windows](https://git-scm.com/download/win), mở PowerShell mới và kiểm `git --version`.

Trong PowerShell ở `C:\StardustFashion`, khi đã kiểm `.env` không bị theo dõi:

```powershell
git init
git status
git add .
git status
git commit -m "Build Stardust Fashion MySQL test site"
```

`git init` tự tạo **thư mục `.git`**, không cần tự tạo “file git”. `.gitignore` đã chặn `.env`, `.venv`, cache; trước commit kiểm `git status` không có `.env` hoặc mật khẩu. Nếu Git yêu cầu tên/email, chạy `git config --global user.name "Tên của bạn"` và `git config --global user.email "email-cua-ban@example.com"`, sau đó commit lại.

Khi muốn đưa lên GitHub: trên **website GitHub**, đăng nhập → **New repository** → đặt tên, chọn repository rỗng, copy URL HTTPS do GitHub cấp. Trở lại **PowerShell trên máy**:

```powershell
git branch -M main
git remote add origin https://github.com/TEN-CUA-BAN/TEN-REPOSITORY.git
git push -u origin main
```

Thay URL ví dụ bằng URL repository thật của bạn. GitHub có thể yêu cầu đăng nhập qua trình duyệt hoặc credential manager. Đừng đưa `.env`, token hay khóa MoMo lên GitHub.

## 10. Trạng thái bàn giao

Mã nguồn, MySQL schema/seed, giao diện, API, Postman Collection/Environment và tài liệu đã được tạo. Đã kiểm tra cú pháp Python và cấu trúc file. **Chưa xác nhận PASS test plan** vì môi trường này không có mật khẩu MySQL của người dùng, khóa MoMo sandbox hoặc IPN URL công khai; cần nhóm chạy các bước trên và ghi build, máy, thời điểm, kết quả từng ca. Mục CN11 phải đo thực tế; script 100 người không phải bằng chứng nếu chưa chạy.
