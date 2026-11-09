# Deploy form giao dịch cá nhân

Hướng dẫn này dành cho bản form cá nhân. Google Sheet \`Trades\` phải để riêng tư. Không đưa API token hoặc URL deployment có token vào chat.

## 1. Cập nhật mã Apps Script

1. Mở dự án Apps Script đang liên kết với Google Sheet.
2. Mở tệp \`Code.gs\`, thay nội dung bằng \`apps_script/Code.gs\` trong repo rồi bấm **Save**.
3. Mở **Project Settings → Script Properties** và tạo hai thuộc tính:
   - \`SPREADSHEET_ID\`: phần ID trong URL Google Sheet nằm giữa \`/d/\` và \`/edit\`.
   - \`FORM_TOKEN\`: token ngẫu nhiên dài ít nhất 32 ký tự.
4. Nếu cần tạo token trong PowerShell, chạy:

   \`\`\`powershell
   $bytes = New-Object byte[] 32
   $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
   $rng.GetBytes($bytes)
   $token = [BitConverter]::ToString($bytes).Replace('-', '').ToLower()
   $token
   \`\`\`

   Giữ token trong trình quản lý mật khẩu khi chuyển giữa Script Properties và máy tính. Đừng dán token vào GitHub hoặc chat.

## 2. Tạo bản triển khai Web app

1. Chọn **Deploy → New deployment** (hoặc **Manage deployments → Edit** nếu đã có Web app).
2. Chọn loại **Web app**.
3. Chọn **Execute as: Me** để script ghi bằng quyền của chủ sở hữu.
4. Với form chỉ dùng cá nhân, đặt **Who has access: Only myself** và đăng nhập đúng tài khoản Google sở hữu Sheet khi mở form.
5. Chọn **Deploy**. Khi cập nhật \`Code.gs\`, phải chọn **New version**; lưu mã nguồn thôi chưa cập nhật deployment.
6. Sao chép URL kết thúc bằng \`/exec\`.

Không chọn quyền truy cập công khai cho Sheet. Token nằm trong trình duyệt của form nên không phải cơ chế xác thực cho một form công khai.

## 3. Cấu hình form cục bộ

Trong PowerShell, tại thư mục \`E:\DU_AN\`, tạo tệp cá nhân:

\`\`\`powershell
@'
window.APP_CONFIG = {
  appsScriptUrl: "DAN_URL_WEB_APP_KET_THUC_BANG_EXEC_VAO_DAY",
  formToken: "DAN_CUNG_FORM_TOKEN_VAO_DAY"
};
'@ | Set-Content -Encoding utf8 web_form/config.local.js
\`\`\`

Tệp \`web_form/config.local.js\` đã bị \`.gitignore\` loại khỏi Git. Không dùng giá trị ví dụ trong dấu ngoặc kép; thay bằng URL deployment và token của bạn.

## 4. Kiểm tra an toàn

1. Mở \`web_form/index.html\` bằng trình duyệt, đăng nhập Google bằng tài khoản đã chọn ở bước triển khai.
2. Bấm **Kiểm tra kết nối (không ghi dữ liệu)**. Nút chỉ gọi GET trạng thái; nó không gửi lệnh và không ghi vào Sheet.
3. Thông báo **Web app đang phản hồi** xác nhận URL và tuyến trạng thái GET hoạt động. Nó chưa xác nhận quyền ghi vào \`Trades\`.
4. Để xác nhận ghi thật theo tiêu chí Phase 1, chỉ gửi một giao dịch thật của bạn khi đã sẵn sàng, rồi kiểm tra dòng đó trong tab \`Trades\`. Nếu chưa muốn ghi giao dịch, dừng ở bước 3.

Nếu nút kiểm tra không nhận phản hồi, kiểm tra URL \`/exec\`, quyền truy cập của Web app và xác nhận deployment đang dùng **New version**. Nếu cấu hình hợp lệ nhưng form vẫn không phản hồi, kiểm tra tài khoản Google đang đăng nhập và quyền của script đối với Sheet.
