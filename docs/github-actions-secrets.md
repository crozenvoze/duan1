# Bật cập nhật giá tự động

> Hướng dẫn này dùng cho repository GitHub `crozenvoze/duan1`. **Không gửi API key, API secret hoặc nội dung JSON credentials vào chat.**

Workflow chỉ đọc danh sách mã từ tab `Watchlist` và ghi dữ liệu giá vào `Prices_Cache`. Nó không đọc tab `Trades`. Bản Streamlit công khai vẫn dùng dữ liệu giả lập và không cần các secrets này.

## 1. Chọn nguồn giá

Vnstock v6 yêu cầu khóa API của nguồn bạn chọn. Các nguồn được workflow hỗ trợ:

| Nguồn | Secrets cần tạo |
|---|---|
| SSI — [Developer Portal](https://developers.ssi.com.vn/) | `SSI_API_KEY`, `SSI_API_SECRET` |
| DNSE — [Developer Portal](https://developers.dnse.com.vn/) | `DNSE_API_KEY`, `DNSE_API_SECRET` |
| FHSC — [Open API](https://developers.fhsc.com.vn/) | `FHSC_API_KEY` |

Tạo khóa tại cổng chính thức của nhà cung cấp đã chọn và xem điều khoản/quota của họ. Với SSI, workflow chỉ cần dữ liệu thị trường; không cần quyền đặt lệnh hoặc OTP. Nếu cổng cho phép chọn phạm vi, chỉ bật phạm vi dữ liệu thị trường.

Vnstock có thể yêu cầu thêm khóa cấp quyền Vnstock khi chạy trên CI, tùy chính sách hiện hành. `VNSTOCK_API_KEY` (nếu cần) lấy riêng từ Vnstock, không thay thế khóa SSI và không được gửi đến SSI. Nếu workflow báo `VNSTOCK_TIER_CI_KEY_REQUIRED`, tạo secret này theo [hướng dẫn thiết lập Vnstock v6](https://www.vnstocks.com/docs/vnstock/v6/cai-dat) rồi chạy lại. Khi không có thông báo đó, chưa cần thêm khóa Vnstock.

## 2. Thêm secrets vào GitHub

1. Mở repository `crozenvoze/duan1` trên GitHub.
2. Chọn **Settings → Secrets and variables → Actions**.
3. Chọn **New repository secret** cho từng mục cần thiết:
   - `GOOGLE_SHEETS_SPREADSHEET_ID`: ID của Sheet `Equity_Toolkit`.
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: toàn bộ nội dung file service-account JSON. Chỉ GitHub Actions mới dùng giá trị này; không tạo file JSON trong repository.
   - `VNSTOCK_SOURCE`: viết thường, một trong `ssi`, `dnse`, `fhsc`.
   - Thêm đúng API key/secret tương ứng với nguồn ở bảng trên.
   - `VNSTOCK_API_KEY` chỉ khi log báo `VNSTOCK_TIER_CI_KEY_REQUIRED`; khóa này thuộc tài khoản Vnstock, khác với khóa nguồn SSI.
4. Đảm bảo service account đã được chia sẻ quyền **Editor** trên đúng Google Sheet. Không bật chia sẻ công khai cho Sheet.

## 3. Chạy thử workflow

1. Trong repository, mở tab **Actions**.
2. Chọn **Update watchlist prices**.
3. Chọn **Run workflow → Run workflow**.
4. Mở lần chạy mới nhất. Nếu thiếu secrets, bước kiểm tra sẽ báo bỏ qua; nếu chạy thành công, phần Summary cho biết số mã và số dòng thêm/cập nhật, không in dữ liệu giao dịch.

Sau khi chạy thành công, kiểm tra tab `Prices_Cache` trong Google Sheet. Lịch chạy tự động là 17:30 giờ Việt Nam, thứ Hai đến thứ Sáu; ngày nghỉ và lịch giao dịch đặc biệt không được tự nhận biết.

Với SSI, tạo API key riêng chỉ có quyền đọc Market Data nếu cổng cho chọn scope. Không bật quyền Trading cho workflow cập nhật giá.
