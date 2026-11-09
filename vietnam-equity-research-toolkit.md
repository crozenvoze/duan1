# DỰ ÁN: Vietnam Equity Research Toolkit

> File này là bản đặc tả (spec) để giao cho ChatGPT thực hiện theo từng giai đoạn. Hãy đọc toàn bộ, sau đó làm đúng theo mục "Quy tắc làm việc" bên dưới.

---

## 0. Quy tắc làm việc (ChatGPT phải tuân thủ)

1. **Làm từng giai đoạn (Phase), từng bước (Step).** Sau mỗi Step, dừng lại, đưa code + cách chạy + cách kiểm tra đúng/sai, rồi chờ tôi xác nhận "OK, tiếp" trước khi sang Step tiếp theo. Không dồn nhiều Phase vào một câu trả lời.
2. **Trước khi viết code của mỗi Phase**, hãy tóm tắt bằng 5-7 dòng: bạn sẽ làm gì, file nào được tạo/sửa, và những giả định bạn đang đặt ra. Nếu có điểm mơ hồ, hỏi tôi tối đa 3 câu rồi mới code.
3. **Luôn đưa code hoàn chỉnh của file được sửa**, không viết "... phần còn lại giữ nguyên", để tôi có thể copy-paste nguyên file.
4. **Comment bằng tiếng Việt** cho mọi hàm quan trọng: hàm làm gì, đầu vào, đầu ra, công thức tài chính dùng (nếu có).
5. **Tôi là sinh viên Tài chính - Ngân hàng, đang học lập trình qua dự án này.** Giải thích ngắn gọn vì sao chọn thiết kế đó. Không giả định tôi đã biết Git, Google Cloud, hay Streamlit.
6. **Trung thực về độ không chắc chắn.** Nếu bạn không chắc một thư viện/API còn hoạt động hay đúng cú pháp phiên bản hiện tại (đặc biệt `vnstock`, Google API), hãy nói rõ và đề xuất cách tôi tự kiểm tra, không đoán.
7. **Không bao giờ yêu cầu tôi dán API key, mật khẩu, hay dữ liệu cá nhân thật vào chat.** Dùng biến môi trường / secrets và dữ liệu mẫu.
8. **Mọi công thức tài chính phải có tên và định nghĩa rõ** (xem Phụ lục A). Nếu bạn muốn đổi định nghĩa, phải hỏi tôi.
9. **Khi tôi báo lỗi**, hãy chỉ ra nguyên nhân gốc trước, rồi mới sửa.

---

## 1. Mục tiêu dự án

Xây một bộ công cụ nghiên cứu cổ phiếu Việt Nam chạy trên nền **Google Sheets + Python + Streamlit**, gồm:

| Module | Chức năng | Luồng dữ liệu |
|---|---|---|
| M1. Trading Journal | Nhập lệnh mua/bán qua form web, tự tính hiệu suất | Web form → Google Sheet |
| M2. Watchlist | Danh sách mã theo dõi, giá, % thay đổi, cảnh báo ngưỡng | Sheet → Python → Web |
| M3. Fundamental Dashboard | Chỉ số tài chính, phân rã DuPont, so sánh cùng ngành | Python → Sheet → Web |
| M4. Stock Screener | Lọc cổ phiếu theo nhiều tiêu chí | Python → Web |
| M5. Backtest & Risk (giai đoạn mở rộng) | Backtest chiến lược cơ bản, Markowitz, VaR | Python → Web |

**Vì sao chọn dự án này:** bao phủ cả hai luồng tôi cần (web → Sheet và Sheet → web), bám sát chuyên ngành Tài chính - Ngân hàng, dùng dữ liệu của chính tôi (trading journal) nên không vướng riêng tư, và đủ chiều sâu để làm portfolio cho CV và Upwork.

**Người dùng:** chính tôi (nhà đầu tư cá nhân, trainee data analyst). Có thể mở rộng cho người khác sau.

---

## 2. Công nghệ

| Thành phần | Công cụ |
|---|---|
| Lưu trữ dữ liệu | Google Sheets |
| Nhận dữ liệu từ web form | Google Apps Script (web app) |
| Xử lý dữ liệu | Python 3.10+, `pandas`, `numpy` |
| Dữ liệu thị trường VN | `vnstock` (kiểm tra phiên bản và cú pháp hiện hành trước khi dùng) |
| Đọc/ghi Sheet từ Python | `gspread` + Service Account |
| Giao diện web | `streamlit`, `plotly` |
| Phân tích định lượng (Phase 5) | `scipy`, `statsmodels`, `cvxpy` hoặc `scipy.optimize` |
| Quản lý mã nguồn | Git + GitHub |
| Triển khai | Streamlit Community Cloud |
| Lập lịch cập nhật tự động | GitHub Actions (cron) |

Nếu một công cụ ở trên không phù hợp, hãy đề xuất phương án thay thế kèm lý do trước khi làm.

---

## 3. Cấu trúc thư mục mục tiêu

```
vietnam-equity-toolkit/
├── README.md
├── requirements.txt
├── .gitignore                  # phải chặn credentials, .env, secrets.toml
├── .env.example                # mẫu, không chứa giá trị thật
├── app/
│   ├── main.py                 # trang chủ Streamlit
│   ├── pages/
│   │   ├── 1_Trading_Journal.py
│   │   ├── 2_Watchlist.py
│   │   ├── 3_Fundamentals.py
│   │   ├── 4_Screener.py
│   │   └── 5_Backtest_Risk.py
├── src/
│   ├── config.py               # đọc cấu hình, secrets
│   ├── sheets.py               # kết nối và đọc/ghi Google Sheets
│   ├── market_data.py          # lấy dữ liệu giá, BCTC (bọc vnstock)
│   ├── metrics.py              # toàn bộ công thức tài chính
│   ├── journal.py              # tính chỉ số trading journal
│   ├── screener.py
│   └── backtest.py
├── apps_script/
│   └── Code.gs                 # backend nhận form
├── web_form/
│   └── index.html              # form nhập lệnh (GitHub Pages)
├── tests/
│   └── test_metrics.py         # kiểm thử công thức với số liệu tính tay
└── .github/workflows/
    └── update_data.yml
```

---

## 4. Thiết kế dữ liệu Google Sheet

Tạo 1 Google Sheet tên `Equity_Toolkit` gồm các tab:

### Tab `Trades` (nhật ký giao dịch)

| Cột | Kiểu | Mô tả |
|---|---|---|
| trade_id | text | Mã duy nhất (tự sinh) |
| timestamp | datetime | Thời điểm nhập |
| trade_date | date | Ngày khớp lệnh |
| ticker | text | Mã cổ phiếu, viết hoa |
| side | text | `BUY` hoặc `SELL` |
| price | number | Giá khớp (VND) |
| quantity | integer | Khối lượng (bội số của 100 với lô chẵn) |
| fee | number | Phí + thuế (VND) |
| reason | text | Lý do vào/ra lệnh |
| stop_loss | number | Giá cắt lỗ dự kiến (có thể trống) |
| target | number | Giá mục tiêu (có thể trống) |
| strategy_tag | text | Ví dụ: breakout, value, swing |

### Tab `Watchlist`

| Cột | Mô tả |
|---|---|
| ticker | Mã |
| alert_above | Cảnh báo khi giá vượt ngưỡng này |
| alert_below | Cảnh báo khi giá xuống dưới ngưỡng này |
| note | Ghi chú |

### Tab `Fundamentals` (do Python ghi)

`ticker, period, revenue, gross_profit, net_income, total_assets, total_equity, total_debt, operating_cash_flow, roe, roa, net_margin, asset_turnover, equity_multiplier, debt_to_equity, updated_at`

Lưu ý: ngân hàng có cấu trúc BCTC khác doanh nghiệp phi tài chính. Hãy xử lý riêng nhóm ngân hàng (NIM, CIR, NPL, LDR, CASA) ở một bước sau, không trộn chung.

### Tab `Prices_Cache`

`ticker, date, open, high, low, close, volume` (cache để không gọi API lặp lại)

---

## 5. Lộ trình triển khai

### PHASE 0: Chuẩn bị môi trường

**Step 0.1:** Hướng dẫn tôi cài Python, tạo virtual environment, cài thư viện, tạo repo GitHub, và viết `.gitignore` chuẩn.
**Step 0.2:** Hướng dẫn tạo Google Cloud project, bật Google Sheets API, tạo Service Account, tải file JSON credentials, và chia sẻ Sheet cho email của service account. Nhấn mạnh: file JSON không được commit lên GitHub.
**Step 0.3:** Viết `src/config.py` và `src/sheets.py` kết nối Sheet, kèm một script test đọc được tab `Trades`.

**Tiêu chí hoàn thành:** chạy `python -m src.sheets` đọc được dữ liệu mẫu từ Sheet.

---

### PHASE 1: Module M1, Trading Journal (web → Sheet)

**Step 1.1:** Viết `apps_script/Code.gs` với hàm `doPost(e)` nhận JSON, validate (ticker 3 ký tự chữ, side là BUY/SELL, price > 0, quantity nguyên dương, ngày hợp lệ), sinh `trade_id`, ghi vào tab `Trades`, trả JSON `{success, message}`. Thêm cơ chế chống spam cơ bản và một khóa bí mật (token) lưu trong Script Properties, form phải gửi kèm token.
**Step 1.2:** Hướng dẫn deploy Apps Script thành web app. Nhắc rõ: mỗi lần sửa code phải tạo version deployment mới.
**Step 1.3:** Viết `web_form/index.html` (HTML/CSS/JS thuần, responsive, tiếng Việt) với các trường của tab `Trades`. Dùng `fetch` với `Content-Type: text/plain;charset=utf-8` để tránh lỗi CORS với Apps Script. Có trạng thái đang gửi, thông báo thành công/lỗi, chặn gửi trùng.
**Step 1.4:** Viết `src/journal.py` tính từ tab `Trades`:
- Giá vốn bình quân và vị thế hiện tại theo từng mã
- Lãi/lỗ đã thực hiện (theo phương pháp bình quân gia quyền; nêu rõ giả định)
- Với các lệnh đã đóng: win rate, average win, average loss, profit factor, expectancy, R-multiple (nếu có stop_loss), max drawdown của đường vốn
- Phân tích theo `strategy_tag`
**Step 1.5:** Viết `app/pages/1_Trading_Journal.py` hiển thị bảng vị thế, các chỉ số trên, biểu đồ đường vốn và phân bố lãi/lỗ.

**Tiêu chí hoàn thành:**
- Nhập 1 lệnh trên web, thấy dòng mới trong Sheet trong vài giây.
- Nhập lệnh sai định dạng thì bị từ chối kèm thông báo rõ.
- Chỉ số trong dashboard khớp với kết quả tôi tính tay trên 10 lệnh mẫu (ChatGPT phải cung cấp bộ 10 lệnh mẫu kèm đáp án tính tay để đối chiếu).

---

### PHASE 2: Module M2, Watchlist

**Step 2.1:** Viết `src/market_data.py` bọc `vnstock` với các hàm: lấy giá lịch sử, giá hiện tại, danh sách mã theo ngành. Phải có xử lý lỗi, retry, và ghi cache vào tab `Prices_Cache` hoặc file local. Báo rõ cho tôi nếu nguồn dữ liệu có giới hạn hay thay đổi cú pháp.
**Step 2.2:** Viết `app/pages/2_Watchlist.py`: đọc tab `Watchlist`, hiển thị giá, % thay đổi ngày/tuần/tháng, volume so với trung bình 20 phiên, tô xanh/đỏ, đánh dấu mã chạm ngưỡng cảnh báo.
**Step 2.3 (tùy chọn):** Gửi cảnh báo qua Telegram bot khi chạm ngưỡng, chạy bằng GitHub Actions theo lịch. Token lưu trong GitHub Secrets.

**Tiêu chí hoàn thành:** sửa ngưỡng trong Sheet thì dashboard phản ánh sau khi refresh; mã chạm ngưỡng được đánh dấu đúng.

---

### PHASE 3: Module M3, Fundamental Dashboard

**Step 3.1:** Viết `src/metrics.py` cài đặt các công thức ở Phụ lục A. Mỗi hàm có docstring nêu công thức. Viết `tests/test_metrics.py` kiểm thử với số liệu giả định có đáp án tính tay.
**Step 3.2:** Lấy BCTC theo quý/năm cho một rổ mã (bắt đầu với 10 mã phi tài chính thanh khoản cao), tính chỉ số, ghi vào tab `Fundamentals`.
**Step 3.3:** Viết `app/pages/3_Fundamentals.py`:
- Chọn mã và khoảng thời gian
- Biểu đồ xu hướng doanh thu, biên lợi nhuận, ROE
- **DuPont 3 bước:** ROE = Net margin × Asset turnover × Equity multiplier, hiển thị đóng góp của từng thành phần theo thời gian
- So sánh với trung vị cùng ngành
- Cảnh báo chất lượng lợi nhuận: dòng tiền HĐKD/lợi nhuận ròng, khoản phải thu tăng nhanh hơn doanh thu
**Step 3.4 (sau khi 3.3 ổn):** Nhánh riêng cho ngân hàng với NIM, CIR, NPL, LDR, CASA, chi phí dự phòng/dư nợ.

**Tiêu chí hoàn thành:** DuPont của 2 mã (một sản xuất, một bán lẻ) khớp với bảng tính Excel tôi tự làm từ BCTC gốc, sai số dưới 1% (sai khác do làm tròn thì phải giải thích).

---

### PHASE 4: Module M4, Stock Screener

**Step 4.1:** Viết `src/screener.py` lọc theo: P/E, P/B, ROE, tăng trưởng doanh thu/EPS, nợ/vốn chủ, thanh khoản trung bình, vốn hóa, ngành.
**Step 4.2:** Viết `app/pages/4_Screener.py` với slider/bộ lọc, bảng kết quả sắp xếp được, nút tải CSV, và lưu "bộ lọc yêu thích" vào Sheet.
**Step 4.3:** Thêm điểm xếp hạng tổng hợp (ví dụ z-score trung bình của value, quality, momentum). Giải thích rõ cách chuẩn hóa và nêu hạn chế.

**Tiêu chí hoàn thành:** bộ lọc trả kết quả trong vài giây; chọn 3 mã kết quả và đối chiếu thủ công thấy chỉ số đúng.

---

### PHASE 5: Module M5, Backtest và Risk (mở rộng)

**Step 5.1: Backtest** MA cross và RSI trên dữ liệu lịch sử. Bắt buộc: tính phí giao dịch, độ trượt giá, tránh look-ahead bias (tín hiệu ngày t chỉ khớp ngày t+1), tuân thủ ràng buộc thị trường VN (lô giao dịch, biên độ giá, T+2 cho cổ phiếu). Xuất CAGR, Sharpe, max drawdown, win rate, so sánh với buy-and-hold và VN-Index.
**Step 5.2: Markowitz.** Đường biên hiệu quả, danh mục phương sai tối thiểu, Sharpe tối đa, có ràng buộc tỷ trọng (không bán khống, tối đa mỗi mã).
**Step 5.3: VaR và CVaR** theo 3 phương pháp (lịch sử, parametric, Monte Carlo) cho danh mục lấy từ vị thế thật ở M1, so sánh kết quả và giải thích vì sao khác nhau.

**Tiêu chí hoàn thành:** mỗi kết quả đi kèm phần "Giả định và hạn chế". Backtest phải có phân tích độ nhạy với mức phí giao dịch.

---

### PHASE 6: Hoàn thiện và triển khai

**Step 6.1:** Deploy lên Streamlit Community Cloud, cấu hình secrets đúng cách.
**Step 6.2:** GitHub Actions cập nhật dữ liệu theo lịch (ví dụ sau giờ đóng cửa mỗi ngày giao dịch).
**Step 6.3:** Viết `README.md` bằng **tiếng Anh**: mô tả vấn đề, kiến trúc (kèm sơ đồ), ảnh chụp màn hình, hướng dẫn cài đặt, phương pháp luận, giả định, hạn chế, và lộ trình. README phải đủ tốt để nhà tuyển dụng đọc trong 2 phút.
**Step 6.4:** Rà soát bảo mật: quét repo để chắc chắn không lộ credentials; dùng dữ liệu mẫu hóa cho bản demo công khai.

---

## 6. Yêu cầu chất lượng chung

- Mọi hàm tính toán có unit test với số liệu tính tay.
- Xử lý lỗi rõ ràng: nguồn dữ liệu ngừng hoạt động, Sheet trống, mã không tồn tại, mất kết nối. App không được crash trắng màn hình.
- Dùng `st.cache_data` hợp lý để giảm số lần gọi API; ghi rõ TTL.
- Không hard-code đường dẫn, ID Sheet, token trong code. Mọi thứ qua config/secrets.
- Code theo module, mỗi hàm một nhiệm vụ, đặt tên rõ nghĩa.
- Giao diện tiếng Việt, số hiển thị theo định dạng dễ đọc (ví dụ 1,250,000 VND, phần trăm 2 chữ số thập phân).

---

## 7. Bảo mật và dữ liệu

- Dữ liệu trong Sheet `Trades` là riêng tư; không publish Sheet ra công khai.
- Credentials Service Account, token Apps Script, token Telegram: chỉ lưu trong Streamlit secrets, GitHub Secrets, Script Properties hoặc `.env` (đã nằm trong `.gitignore`).
- Bản demo công khai dùng dữ liệu giả lập, không dùng giao dịch thật.
- Nếu sau này mở cho người khác nhập dữ liệu cá nhân, phải bổ sung thông báo mục đích sử dụng dữ liệu và phân quyền; hãy nhắc tôi khi đến giai đoạn đó.

---

## 8. Cách bắt đầu

Hãy trả lời theo đúng thứ tự:

1. Xác nhận bạn đã hiểu dự án bằng 5-7 dòng, nêu 3 rủi ro kỹ thuật lớn nhất bạn thấy (ví dụ độ ổn định của nguồn dữ liệu, giới hạn quota của Apps Script/Google API).
2. Hỏi tôi tối đa 3 câu làm rõ nếu cần.
3. Sau khi tôi trả lời, bắt đầu **Phase 0, Step 0.1**.

---

## Phụ lục A: Định nghĩa công thức (chuẩn của dự án)

| Chỉ số | Công thức | Ghi chú |
|---|---|---|
| Net margin | Lợi nhuận ròng / Doanh thu thuần | |
| Asset turnover | Doanh thu thuần / Tổng tài sản bình quân | Bình quân = (đầu kỳ + cuối kỳ) / 2 |
| Equity multiplier | Tổng tài sản bình quân / Vốn chủ sở hữu bình quân | |
| ROE | Lợi nhuận ròng / Vốn chủ sở hữu bình quân | = Net margin × Asset turnover × Equity multiplier |
| ROA | Lợi nhuận ròng / Tổng tài sản bình quân | |
| Debt/Equity | Tổng nợ vay / Vốn chủ sở hữu | Nêu rõ dùng nợ vay hay tổng nợ phải trả |
| Cash conversion | Dòng tiền HĐKD / Lợi nhuận ròng | Cảnh báo nếu thấp kéo dài |
| Profit factor | Tổng lãi các lệnh thắng / Tổng lỗ các lệnh thua | |
| Expectancy | Win rate × Avg win − Loss rate × Avg loss | |
| R-multiple | Lãi/lỗ của lệnh / Rủi ro ban đầu (entry − stop) × khối lượng | |
| Sharpe | (Lợi suất TB − Lãi suất phi rủi ro) / Độ lệch chuẩn | Nêu rõ năm hóa và lãi suất phi rủi ro dùng |
| Max drawdown | Mức sụt giảm lớn nhất từ đỉnh đến đáy của đường vốn | |
| CAGR | (Giá trị cuối / Giá trị đầu)^(1/số năm) − 1 | |

Nếu chuẩn kế toán Việt Nam (VAS) khiến tên chỉ tiêu khác với mô tả trên, hãy nêu rõ ánh xạ giữa tên chỉ tiêu trong dữ liệu nguồn và công thức trước khi tính.

## Phụ lục B: Bộ dữ liệu mẫu để kiểm thử (ChatGPT phải tạo ở Phase 1)

Tạo 10 lệnh giao dịch giả lập gồm cả lệnh lãi, lỗ, bán một phần, và mua thêm, kèm bảng đáp án tính tay (vị thế cuối, giá vốn bình quân, lãi/lỗ thực hiện, win rate, profit factor) để tôi đối chiếu với kết quả của code.
