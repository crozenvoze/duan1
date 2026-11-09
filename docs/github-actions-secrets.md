# Bật cập nhật giá tự động

> Hướng dẫn này dùng cho repository GitHub `crozenvoze/duan1`. **Không gửi API key, API secret hoặc nội dung JSON credentials vào chat.**

Workflow chỉ đọc danh sách mã từ tab `Watchlist` và ghi dữ liệu giá vào `Prices_Cache`. Nó không đọc tab `Trades`. Bản Streamlit công khai vẫn dùng dữ liệu giả lập và không cần các secrets này.

## 1. Chọn nguồn giá

Vnstock v6 yêu cầu khóa API của nguồn bạn chọn. Các nguồn được workflow hỗ trợ:

| Nguồn | Secrets cần tạo |
|---|---|
| SSI | `SSI_API_KEY`, `SSI_API_SECRET` |
| DNSE | `DNSE_API_KEY`, `DNSE_API_SECRET` |
| FHSC | `FHSC_API_KEY` |

Tạo khóa tại cổng chính thức của nhà cung cấp đã chọn và xem điều khoản/quota của họ. Đừng dùng mã OTP đăng nhập TCBS làm secret dài hạn; OTP không được lưu trong workflow.

## 2. Thêm secrets vào GitHub

1. Mở repository `crozenvoze/duan1` trên GitHub.
2. Chọn **Settings → Secrets and variables → Actions**.
3. Chọn **New repository secret** cho từng mục cần thiết:
   - `GOOGLE_SHEETS_SPREADSHEET_ID`: ID của Sheet `Equity_Toolkit`.
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: toàn bộ nội dung file service-account JSON. Chỉ GitHub Actions mới dùng giá trị này; không tạo file JSON trong repository.
   - `VNSTOCK_SOURCE`: viết thường, một trong `ssi`, `dnse`, `fhsc`.
   - Thêm đúng API key/secret tương ứng với nguồn ở bảng trên.
4. Đảm bảo service account đã được chia sẻ quyền **Editor** trên đúng Google Sheet. Không bật chia sẻ công khai cho Sheet.

## 3. Chạy thử workflow

1. Trong repository, mở tab **Actions**.
2. Chọn **Update watchlist prices**.
3. Chọn **Run workflow → Run workflow**.
4. Mở lần chạy mới nhất. Nếu thiếu secrets, bước kiểm tra sẽ báo bỏ qua; nếu chạy thành công, phần Summary cho biết số mã và số dòng thêm/cập nhật, không in dữ liệu giao dịch.

Sau khi chạy thành công, kiểm tra tab `Prices_Cache` trong Google Sheet. Lịch chạy tự động là 17:30 giờ Việt Nam, thứ Hai đến thứ Sáu; ngày nghỉ và lịch giao dịch đặc biệt không được tự nhận biết.
