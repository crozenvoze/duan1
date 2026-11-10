# Deploy form giao dịch riêng tư

Google Sheet `Trades` phải để riêng tư. Bản triển khai khuyến nghị phục vụ chính giao diện form từ Apps Script và giới hạn người truy cập là tài khoản của bạn. Cách này không cần nhúng token vào trình duyệt và không phụ thuộc CORS từ một trang bên ngoài.

## 1. Cập nhật mã Apps Script

1. Mở dự án Apps Script đang liên kết với Google Sheet.
2. Mở tệp `Code.gs`, thay nội dung bằng `apps_script/Code.gs` trong repo rồi bấm **Save**.
3. Nhấn dấu **+ → HTML**, đặt tên tệp là `Index`, rồi dán toàn bộ `apps_script/Index.html` trong repo và bấm **Save**.
4. Mở **Project Settings → Script Properties**, tạo thuộc tính `SPREADSHEET_ID` bằng phần ID của Sheet nằm giữa `/d/` và `/edit` trong URL.

Nếu bạn còn dùng `web_form/index.html` độc lập trên máy, nó cần thêm `FORM_TOKEN` dài ít nhất 32 ký tự. Token đó nằm trong trình duyệt nên chỉ dùng cho trang cục bộ, không dùng để bảo vệ một form công khai. Có thể tạo bằng PowerShell:

   ```powershell
   $bytes = New-Object byte[] 32
   $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
   $rng.GetBytes($bytes)
   $token = [BitConverter]::ToString($bytes).Replace('-', '').ToLower()
   $token
   ```

   Lưu token trong Script Properties với tên `FORM_TOKEN` và cấu hình vào trang cục bộ bằng `src.configure_form`. Không dán token vào GitHub hoặc chat. Nếu chỉ dùng giao diện `Index` do Apps Script phục vụ, có thể bỏ qua bước token này.

## 2. Tạo bản triển khai Web app

1. Chọn **Deploy → New deployment** (hoặc **Manage deployments → Edit** nếu đã có Web app).
2. Chọn loại **Web app**.
3. Chọn **Execute as: Me** để script ghi bằng quyền của chủ sở hữu.
4. Đặt **Who has access: Only myself**. Điều này giới hạn giao diện vào tài khoản của bạn.
5. Chọn **Deploy**. Khi cập nhật `Code.gs` hoặc `Index.html`, phải chọn **New version**; lưu mã nguồn thôi chưa cập nhật deployment.
6. Sao chép URL kết thúc bằng `/exec`.

Không chọn quyền truy cập công khai cho Sheet. Mở URL `/exec` khi đã đăng nhập bằng chính tài khoản triển khai; trang form được Apps Script phục vụ tại đó.

## 3. Kiểm tra kết nối không ghi dữ liệu

1. Mở URL Web app kết thúc bằng `/exec` và đăng nhập bằng tài khoản triển khai.
2. Bấm **Kiểm tra kết nối (không ghi dữ liệu)**. Nút gọi hàm đọc quyền truy cập Sheet; nó không tạo tab, không đọc dòng giao dịch và không ghi dữ liệu.
3. Thông báo kết nối thành công xác nhận script mở được đúng Sheet. Nếu lỗi, kiểm tra `SPREADSHEET_ID` và quyền của tài khoản triển khai.
4. Để xác nhận ghi thật theo tiêu chí Phase 1, chỉ gửi một giao dịch thật của bạn khi đã sẵn sàng, rồi kiểm tra dòng mới trong tab `Trades`. Nếu chưa muốn ghi giao dịch, dừng ở bước 3.

Nếu bạn cần tiếp tục dùng `web_form/index.html` cục bộ, chạy `python -m src.configure_form` trong môi trường `.venv`, nhập URL `/exec` và token. Trang cục bộ gửi qua POST `no-cors` rồi hỏi trạng thái qua JSONP; nếu trình duyệt hoặc quyền Google chặn luồng này, hãy mở trực tiếp giao diện Apps Script ở URL `/exec` thay vì bật truy cập công khai.

## 4. Xử lý thông báo thiếu URL hoặc token

Thông báo này xuất hiện khi mở `web_form/index.html` như một tệp cục bộ (`file:///...`). Tệp HTML cục bộ cần `web_form/config.local.js` có hai trường `appsScriptUrl` và `formToken`; tệp cấu hình này bị Git bỏ qua nên không được tải từ GitHub.

- **Cách khuyến nghị:** mở URL Web app kết thúc bằng `/exec` khi đã đăng nhập bằng tài khoản triển khai. Trang Apps Script phục vụ `Index.html` và không yêu cầu token trong trình duyệt.
- **Nếu cần dùng HTML cục bộ:** từ thư mục dự án chạy `python -m src.configure_form` trong môi trường `.venv`, nhập URL `/exec` và token đã lưu trong Script Properties. Token phải dài ít nhất 32 ký tự. Không dán token vào chat hoặc commit `config.local.js`.
- Sau khi tạo hoặc sửa cấu hình, tải lại trang cục bộ. Nếu vẫn thấy thông báo cũ, đóng tab đang mở và mở lại `web_form/index.html` từ thư mục dự án hiện tại.
