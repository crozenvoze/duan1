# Dữ liệu đầu vào Screener

Trang Screener đọc dữ liệu từ tab `Screener_Data` hoặc một file CSV. File CSV chỉ được giữ trong phiên Streamlit hiện tại; ứng dụng không ghi file đó vào Google Sheets. Các bộ lọc yêu thích vẫn được lưu riêng trong `Saved_Filters`.

Mẫu rỗng nằm tại [`data/screener_template.csv`](../data/screener_template.csv). Mỗi snapshot chỉ có một dòng cho mỗi mã. Có thể thêm cột metadata như `as_of`, `data_source` hoặc `period`; ứng dụng giữ lại các cột bổ sung khi hiển thị kết quả.

| Cột | Đơn vị / định nghĩa |
|---|---|
| `ticker` | Mã chứng khoán Việt Nam gồm đúng 3 chữ cái, ví dụ `FPT`. |
| `pe`, `pb` | Hệ số P/E và P/B; phải thống nhất nguồn và kỳ đo lường trong cùng snapshot. |
| `roe` | ROE dạng thập phân; `0.15` tương đương 15%. Ghi rõ ở metadata nếu là ROE năm hay TTM. |
| `revenue_growth`, `eps_growth` | Tăng trưởng dạng thập phân; `0.10` tương đương 10%. So sánh cùng kỳ hoặc cùng năm cho toàn bộ snapshot. |
| `debt_to_equity` | Nợ vay / vốn chủ sở hữu; không dùng tổng nợ phải trả thay nợ vay nếu muốn giữ đúng định nghĩa dự án. |
| `avg_value_traded` | Giá trị giao dịch bình quân mỗi phiên, VND. Ghi rõ số phiên trong metadata. |
| `market_cap` | Vốn hóa, VND. |
| `industry` | Tên ngành theo một hệ phân loại nhất quán. |
| `momentum` | Chỉ số động lượng do người dùng chọn; cần ghi công thức và khoảng thời gian ở metadata. Cột này được phép để trống. |

Các cột bắt buộc khác không có dữ liệu có thể để trống; giá trị chữ không phải số, mã sai định dạng, hoặc mã trùng sẽ bị từ chối. Không dùng dấu phân tách hàng nghìn trong trường số. P/E và P/B không dương vẫn được giữ trong bảng gốc nhưng bị loại khỏi điểm value vì P/E âm thường đi với lợi nhuận âm, còn P/B âm có thể phản ánh vốn chủ âm. Hãy kiểm tra ngày chốt, nguồn và cách tính từ BCTC gốc trước khi diễn giải xếp hạng; điểm percentile chỉ so sánh các mã trong snapshot đang nạp, không phải khuyến nghị mua/bán.
