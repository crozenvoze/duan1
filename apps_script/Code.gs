/**
 * Nhận giao dịch từ form web, kiểm tra dữ liệu và ghi an toàn vào Google Sheets.
 * Cấu hình Script Properties bắt buộc: SPREADSHEET_ID; FORM_TOKEN chỉ dành cho POST form tĩnh.
 */

const TRADES_HEADERS = [
  'trade_id', 'timestamp', 'trade_date', 'ticker', 'side', 'price',
  'quantity', 'fee', 'reason', 'stop_loss', 'target', 'strategy_tag'
];

const MAX_REQUESTS_PER_MINUTE = 30;
const REQUEST_STATUS_TTL_SECONDS = 300;

/**
 * Trả trạng thái POST theo JSONP để form tĩnh đọc được kết quả mà không cần CORS.
 * Đầu vào: request_id ngẫu nhiên và callback JavaScript đã được kiểm tra.
 * Đầu ra: lời gọi callback chỉ chứa trạng thái của request đó, không trả dữ liệu Sheet.
 */
function doGet(e) {
  const params = e && e.parameter ? e.parameter : {};
  const requestId = String(params.request_id || '');
  const callback = String(params.callback || '');
  if (!requestId && !callback) {
    return HtmlService.createHtmlOutputFromFile('Index')
      .setTitle('Nhật ký giao dịch | Vietnam Equity Toolkit');
  }
  if (!/^[0-9a-f-]{36}$/i.test(requestId) || !/^[A-Za-z_$][0-9A-Za-z_$]*$/.test(callback)) {
    return ContentService.createTextOutput('/* invalid request */')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }

  const cached = CacheService.getScriptCache().get('trade_status_' + requestId);
  const result = cached ? JSON.parse(cached) : { pending: true };
  return ContentService.createTextOutput(callback + '(' + JSON.stringify(result) + ');')
    .setMimeType(ContentService.MimeType.JAVASCRIPT);
}

/** Kiểm tra quyền mở Sheet mà không đọc dòng giao dịch hoặc ghi dữ liệu. */
function checkConnection() {
  try {
    const spreadsheetId = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
    if (!spreadsheetId) {
      return { success: false, message: 'Chưa cấu hình SPREADSHEET_ID trong Script Properties.' };
    }
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    return {
      success: true,
      message: 'Đã kết nối Google Sheet “' + spreadsheet.getName() + '”. Bước này không ghi giao dịch.'
    };
  } catch (error) {
    console.error(error && error.stack ? error.stack : error);
    return { success: false, message: 'Không mở được Google Sheet. Kiểm tra SPREADSHEET_ID và quyền của tài khoản triển khai.' };
  }
}

/** Nhận lệnh từ form HTMLService đã giới hạn người truy cập ở tài khoản chủ sở hữu. */
function submitTradeFromApp(payload) {
  try {
    const spreadsheetId = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
    if (!spreadsheetId) {
      return { success: false, message: 'Chưa cấu hình SPREADSHEET_ID trong Script Properties.' };
    }
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return { success: false, message: 'Dữ liệu gửi lên phải là một đối tượng JSON.' };
    }
    const requestId = String(payload.request_id || '');
    if (!/^[0-9a-f-]{36}$/i.test(requestId)) {
      return { success: false, message: 'Mã yêu cầu không hợp lệ. Hãy tải lại trang và thử lại.' };
    }
    return processTrade_(payload, requestId, spreadsheetId);
  } catch (error) {
    console.error(error && error.stack ? error.stack : error);
    const detail = error && typeof error.message === 'string' ? error.message : '';
    const message = detail.indexOf('Cấu trúc tab Trades không đúng.') === 0 ? detail : 'Có lỗi máy chủ khi lưu giao dịch. Vui lòng kiểm tra tab Trades trước khi gửi lại.';
    return { success: false, message: message };
  }
}

/**
 * Nhận POST JSON từ web form.
 * Đầu vào: e.postData.contents chứa JSON giao dịch và token.
 * Đầu ra: JSON {success, message}, đồng thời append một dòng vào tab Trades.
 */
function doPost(e) {
  let requestId = '';
  try {
    const properties = PropertiesService.getScriptProperties();
    const expectedToken = properties.getProperty('FORM_TOKEN');
    const spreadsheetId = properties.getProperty('SPREADSHEET_ID');
    if (!expectedToken || !spreadsheetId) {
      return jsonResponse_(false, 'Backend chưa được cấu hình FORM_TOKEN hoặc SPREADSHEET_ID.');
    }

    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse_(false, 'Không nhận được dữ liệu JSON.');
    }

    let payload;
    try {
      payload = JSON.parse(e.postData.contents);
    } catch (error) {
      return jsonResponse_(false, 'JSON không hợp lệ.');
    }

    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return jsonResponse_(false, 'Dữ liệu gửi lên phải là một đối tượng JSON.');
    }
    requestId = String(payload.request_id || '');
    if (!/^[0-9a-f-]{36}$/i.test(requestId)) {
      return jsonResponse_(false, 'Mã yêu cầu không hợp lệ.');
    }
    if (typeof payload.token !== 'string' || !constantTimeEquals_(payload.token, expectedToken)) {
      rememberRequestStatus_(requestId, false, 'Token không hợp lệ.');
      return jsonResponse_(false, 'Token không hợp lệ.');
    }

    const result = processTrade_(payload, requestId, spreadsheetId);
    return jsonResponse_(Boolean(result.success), String(result.message || ''));
  } catch (error) {
    console.error(error && error.stack ? error.stack : error);
    const genericMessage = 'Có lỗi máy chủ khi lưu giao dịch. Vui lòng thử lại sau.';
    const detail = error && typeof error.message === 'string' ? error.message : '';
    const message = detail.indexOf('Cấu trúc tab Trades không đúng.') === 0 ? detail : genericMessage;
    rememberRequestStatus_(requestId, false, message);
    return jsonResponse_(false, message);
  }
}

/** Kiểm tra, chống gửi trùng và ghi một giao dịch sau khi kênh gọi đã được xác thực. */
function processTrade_(payload, requestId, spreadsheetId) {
  // Cùng request_id chỉ được xử lý một lần trong thời gian trạng thái còn lưu.
  const priorStatus = CacheService.getScriptCache().get('trade_status_' + requestId);
  if (priorStatus) {
    const previous = JSON.parse(priorStatus);
    return { success: Boolean(previous.success), message: String(previous.message || 'Yêu cầu đã được xử lý.') };
  }

  const validation = validateTrade_(payload);
  if (!validation.ok) {
    rememberRequestStatus_(requestId, false, validation.message);
    return { success: false, message: validation.message };
  }

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    rememberRequestStatus_(requestId, false, 'Hệ thống đang bận, vui lòng thử lại sau.');
    return { success: false, message: 'Hệ thống đang bận, vui lòng thử lại sau.' };
  }

  try {
    // Kiểm tra lại khi đã giữ khóa để chặn hai lần gửi đồng thời cùng request_id.
    const lockedPriorStatus = CacheService.getScriptCache().get('trade_status_' + requestId);
    if (lockedPriorStatus) {
      const previous = JSON.parse(lockedPriorStatus);
      return { success: Boolean(previous.success), message: String(previous.message || 'Yêu cầu đã được xử lý.') };
    }
    if (!consumeRateLimit_()) {
      rememberRequestStatus_(requestId, false, 'Đã vượt giới hạn gửi tạm thời. Vui lòng chờ một phút.');
      return { success: false, message: 'Đã vượt giới hạn gửi tạm thời. Vui lòng chờ một phút.' };
    }

    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    let sheet = spreadsheet.getSheetByName('Trades');
    if (!sheet) sheet = spreadsheet.insertSheet('Trades');
    ensureHeaders_(sheet);

    const trade = validation.trade;
    sheet.appendRow([
      Utilities.getUuid(), new Date(), trade.trade_date, trade.ticker, trade.side,
      trade.price, trade.quantity, trade.fee, trade.reason, trade.stop_loss,
      trade.target, trade.strategy_tag
    ]);
    rememberRequestStatus_(requestId, true, 'Đã ghi giao dịch vào nhật ký.');
    return { success: true, message: 'Đã ghi giao dịch vào nhật ký.' };
  } finally {
    lock.releaseLock();
  }
}

/** Kiểm tra dữ liệu giao dịch và chuẩn hóa giá trị trước khi ghi Sheet. */
function validateTrade_(payload) {
  const ticker = typeof payload.ticker === 'string' ? payload.ticker.trim().toUpperCase() : '';
  if (!/^[A-Z]{3}$/.test(ticker)) {
    return { ok: false, message: 'Mã cổ phiếu phải gồm đúng 3 chữ cái, ví dụ: FPT.' };
  }

  const side = typeof payload.side === 'string' ? payload.side.trim().toUpperCase() : '';
  if (side !== 'BUY' && side !== 'SELL') {
    return { ok: false, message: 'Loại lệnh chỉ được là BUY hoặc SELL.' };
  }

  const price = Number(payload.price);
  if (!Number.isFinite(price) || price <= 0) {
    return { ok: false, message: 'Giá khớp phải là số lớn hơn 0.' };
  }

  const quantity = Number(payload.quantity);
  if (!Number.isInteger(quantity) || quantity <= 0) {
    return { ok: false, message: 'Khối lượng phải là số nguyên dương.' };
  }

  const tradeDate = parseDate_(payload.trade_date);
  if (!tradeDate) {
    return { ok: false, message: 'Ngày giao dịch không hợp lệ; dùng định dạng YYYY-MM-DD.' };
  }

  const fee = payload.fee === '' || payload.fee === undefined || payload.fee === null
    ? 0
    : Number(payload.fee);
  if (!Number.isFinite(fee) || fee < 0) {
    return { ok: false, message: 'Phí phải là số không âm.' };
  }

  const stopLoss = optionalPositiveNumber_(payload.stop_loss);
  if (stopLoss.invalid) {
    return { ok: false, message: 'Stop loss phải để trống hoặc là số lớn hơn 0.' };
  }
  const target = optionalPositiveNumber_(payload.target);
  if (target.invalid) {
    return { ok: false, message: 'Giá mục tiêu phải để trống hoặc là số lớn hơn 0.' };
  }

  return {
    ok: true,
    trade: {
      ticker: ticker,
      side: side,
      price: price,
      quantity: quantity,
      fee: fee,
      trade_date: tradeDate,
      reason: safeText_(payload.reason, 1000),
      stop_loss: stopLoss.value,
      target: target.value,
      strategy_tag: safeText_(payload.strategy_tag, 100)
    }
  };
}

/** Chuyển ngày YYYY-MM-DD thành Date và loại bỏ ngày không tồn tại trên lịch. */
function parseDate_(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const parts = value.split('-').map(Number);
  const date = new Date(parts[0], parts[1] - 1, parts[2]);
  if (date.getFullYear() !== parts[0] || date.getMonth() !== parts[1] - 1 || date.getDate() !== parts[2]) {
    return null;
  }
  return date;
}

/** Đọc số dương tùy chọn; giá trị trống được lưu thành ô trống. */
function optionalPositiveNumber_(value) {
  if (value === '' || value === undefined || value === null) return { value: '', invalid: false };
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return { value: '', invalid: true };
  return { value: number, invalid: false };
}

/** Giới hạn độ dài văn bản để tránh ghi dữ liệu quá lớn vào Sheet. */
function safeText_(value, maxLength) {
  if (typeof value !== 'string') return '';
  return value.trim().slice(0, maxLength);
}

/** Tạo header theo đặc tả nếu tab Trades đang trống. */
function ensureHeaders_(sheet) {
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, TRADES_HEADERS.length).setValues([TRADES_HEADERS]);
    return;
  }

  const existing = sheet.getRange(1, 1, 1, TRADES_HEADERS.length).getValues()[0]
    .map(value => String(value || '').trim());
  const matches = TRADES_HEADERS.every((header, index) => existing[index] === header);
  if (!matches) {
    throw new Error(
      'Cấu trúc tab Trades không đúng. Cần đúng thứ tự cột: ' + TRADES_HEADERS.join(', ')
    );
  }
}

/** Giới hạn tổng số yêu cầu hợp lệ tối đa 30 lần trong mỗi phút. */
function consumeRateLimit_() {
  const cache = CacheService.getScriptCache();
  const minuteKey = 'requests_' + Math.floor(Date.now() / 60000);
  const count = Number(cache.get(minuteKey) || 0);
  if (count >= MAX_REQUESTS_PER_MINUTE) return false;
  cache.put(minuteKey, String(count + 1), 90);
  return true;
}

/** So sánh token với thời gian chạy gần như cố định, tránh so sánh dừng sớm. */
function constantTimeEquals_(provided, expected) {
  if (provided.length !== expected.length) return false;
  let difference = 0;
  for (let i = 0; i < provided.length; i++) {
    difference |= provided.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  return difference === 0;
}

/** Trả về JSON cho web form. */
function jsonResponse_(success, message) {
  return ContentService
    .createTextOutput(JSON.stringify({ success: success, message: message }))
    .setMimeType(ContentService.MimeType.JSON);
}

/** Lưu trạng thái ngắn hạn để form tĩnh có thể nhận kết quả qua JSONP. */
function rememberRequestStatus_(requestId, success, message) {
  if (!/^[0-9a-f-]{36}$/i.test(String(requestId || ''))) return;
  const result = { success: success, message: message };
  CacheService.getScriptCache().put(
    'trade_status_' + requestId,
    JSON.stringify(result),
    REQUEST_STATUS_TTL_SECONDS
  );
}
