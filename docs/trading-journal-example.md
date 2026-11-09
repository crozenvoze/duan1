# Trading Journal: ví dụ tính tay với 10 lệnh

> Tất cả mã, giá và giao dịch trong tài liệu này đều là dữ liệu giả lập để học và kiểm tra phần mềm. Giá được ghi bằng đơn vị mô phỏng, không phải giá thị trường hay khuyến nghị đầu tư.

## 1. Bộ lệnh mẫu

| ID | Ngày | Mã | Lệnh | Giá | Khối lượng | Stop loss | Phí |
|---|---|---|---|---:|---:|---:|---:|
| S01 | 2026-01-05 | FPT | BUY | 100 | 100 | — | 0 |
| S02 | 2026-01-05 | FPT | BUY | 110 | 100 | — | 0 |
| S03 | 2026-01-06 | FPT | SELL | 120 | 100 | 95 | 0 |
| S04 | 2026-01-07 | FPT | BUY | 90 | 100 | — | 0 |
| S05 | 2026-01-08 | FPT | SELL | 90 | 100 | 105 | 0 |
| S06 | 2026-01-09 | FPT | BUY | 100 | 100 | — | 0 |
| S07 | 2026-01-12 | FPT | SELL | 110 | 100 | 90 | 0 |
| S08 | 2026-01-13 | FPT | SELL | 95 | 100 | 90 | 0 |
| S09 | 2026-01-14 | MWG | BUY | 50 | 100 | — | 0 |
| S10 | 2026-01-15 | MWG | BUY | 60 | 100 | — | 0 |

Đây là cùng bộ dữ liệu `SAMPLE_TRADES` mà `tests/test_journal.py` dùng. Phí bằng 0 để phép tính dễ kiểm tra; trong dữ liệu thật, phí mua được cộng vào giá vốn và phí bán được trừ khỏi lãi/lỗ.

## 2. Giá vốn bình quân và lãi/lỗ từng lệnh bán

Giá vốn bình quân gia quyền được tính trên lượng cổ phiếu đang giữ ngay trước khi bán:

`Giá vốn bình quân = Tổng giá trị vốn còn lại / Số cổ phiếu đang giữ`

`Lãi/lỗ đã thực hiện = Giá bán × Khối lượng bán − Giá vốn bình quân × Khối lượng bán − Phí bán`

| Lệnh bán | Tính giá vốn trước khi bán | Giá vốn bình quân | Lãi/lỗ | Khối lượng FPT còn lại |
|---|---|---:|---:|---:|
| S03 | (100×100 + 110×100) / 200 | 105.00 | 120×100 − 105×100 = **+1,500** | 100 |
| S05 | (105×100 + 90×100) / 200 | 97.50 | 90×100 − 97.5×100 = **−750** | 100 |
| S07 | (97.5×100 + 100×100) / 200 | 98.75 | 110×100 − 98.75×100 = **+1,125** | 100 |
| S08 | Không có lệnh mua mới sau S07 | 98.75 | 95×100 − 98.75×100 = **−375** | 0 |

Ở S05, sau khi bán 100 cổ phiếu, phần vốn còn lại là `97.5 × 100 = 9,750`. S06 mua thêm 100 cổ phiếu ở giá 100, nên trước S07 giá vốn bình quân mới là `(9,750 + 10,000) / 200 = 98.75`.

## 3. Đối chiếu các chỉ số theo lệnh bán

Có 2 lệnh bán lãi và 2 lệnh bán lỗ:

- **Tổng lãi:** `1,500 + 1,125 = 2,625`.
- **Tổng lỗ:** `−750 − 375 = −1,125`.
- **Lãi/lỗ đã thực hiện:** `2,625 − 1,125 = 1,500`.
- **Win rate:** `2 / 4 = 50%` lệnh bán có lãi.
- **Average win:** `2,625 / 2 = 1,312.50`.
- **Average loss:** `1,125 / 2 = 562.50` (hiển thị độ lớn khoản lỗ).
- **Profit factor:** `Tổng lãi / |Tổng lỗ| = 2,625 / 1,125 ≈ 2.3333`.
- **Expectancy mỗi lệnh bán:** `1,500 / 4 = 375`. Tương đương `50%×1,312.5 − 50%×562.5 = 375`.

Đường lãi/lỗ đã thực hiện cộng dồn lần lượt là `1,500 → 750 → 1,875 → 1,500`. Đỉnh cao nhất trước đoạn giảm lớn nhất là `1,500`, đáy sau đó là `750`, nên **max drawdown = 1,500 − 750 = 750**, tương đương **50%** của đỉnh 1,500.

## 4. R-multiple và chu kỳ vị thế đã đóng

`R-multiple = Lãi/lỗ đã thực hiện / Rủi ro tiền ban đầu của phần cổ phiếu được bán`.

Trong fixture, stop loss được ghi trên dòng bán để kiểm tra tương thích dữ liệu cũ. Do đó rủi ro tiền cho mỗi sự kiện là `|giá vốn bình quân − stop loss| × khối lượng bán`:

| Lệnh bán | Rủi ro tiền | R-multiple |
|---|---:|---:|
| S03 | `|105 − 95| × 100 = 1,000` | `1,500 / 1,000 = 1.5R` |
| S05 | `|97.5 − 105| × 100 = 750` | `−750 / 750 = −1R` |
| S07 | `|98.75 − 90| × 100 = 875` | `1,125 / 875 ≈ 1.2857R` |
| S08 | `|98.75 − 90| × 100 = 875` | `−375 / 875 ≈ −0.4286R` |

Chu kỳ FPT đóng hoàn toàn sau S08. Chu kỳ có 4 lệnh mua, 4 lệnh bán, lãi thực hiện 1,500 và tổng rủi ro ghi nhận 3,500, nên R-multiple của cả chu kỳ là `1,500 / 3,500 ≈ 0.4286R`. MWG còn mở 200 cổ phiếu với giá vốn `((50×100)+(60×100))/200 = 55`; chưa có lệnh bán nên chưa được tính là chu kỳ đã đóng hoặc lãi/lỗ thực hiện.

## 5. Phạm vi của ví dụ

Các con số trên là lãi/lỗ đã thực hiện theo sự kiện bán và chu kỳ vị thế đóng hoàn toàn. Ví dụ không mô phỏng tiền mặt, nạp/rút vốn, lãi/lỗ chưa thực hiện, thuế/phí thực tế hoặc cổ tức. Khi đưa dữ liệu thật vào Sheet, hãy dùng ngày khớp lệnh đúng và nhập phí thực tế; không dùng bộ lệnh giả lập này trong tab `Trades` cá nhân.
