"use strict";

// Lightweight local smoke tests for the deployed Apps Script entry points.
// All Google services below are in-memory fakes; no network or real Sheet is used.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function createHarness(initialRows = []) {
  const cacheValues = new Map();
  const rows = initialRows.map(row => [...row]);
  let beforeLock = null;
  const sheet = {
    getLastRow: () => rows.length,
    getRange: (row, column, rowCount, columnCount) => ({
      getValues: () => rows.slice(row - 1, row - 1 + rowCount)
        .map(value => value.slice(column - 1, column - 1 + columnCount)),
      setValues: values => rows.push(...values),
    }),
    appendRow: row => rows.push(row),
  };
  const cache = {
    get: key => cacheValues.get(key) || null,
    put: (key, value) => cacheValues.set(key, value),
  };
  const response = value => ({
    value,
    setMimeType() { return this; },
    getContent() { return this.value; },
  });
  const context = {
    console: { log: console.log, error: () => {} },
    Date,
    JSON,
    Math,
    Number,
    String,
    Boolean,
    Array,
    Object,
    RegExp,
    PropertiesService: { getScriptProperties: () => ({
      getProperty: key => ({ FORM_TOKEN: "local-test-token", SPREADSHEET_ID: "fake-sheet" })[key] || null,
    }) },
    CacheService: { getScriptCache: () => cache },
    LockService: { getScriptLock: () => ({
      tryLock: () => {
        if (beforeLock) {
          const callback = beforeLock;
          beforeLock = null;
          callback();
        }
        return true;
      },
      releaseLock: () => {},
    }) },
    SpreadsheetApp: { openById: () => ({
      getName: () => "Equity_Toolkit",
      getSheetByName: () => sheet,
      insertSheet: () => sheet,
    }) },
    Utilities: { getUuid: () => "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" },
    ContentService: {
      MimeType: { JSON: "application/json", JAVASCRIPT: "application/javascript" },
      createTextOutput: response,
    },
    HtmlService: {
      createHtmlOutputFromFile: file => ({ file, setTitle(title) { this.title = title; return this; } }),
    },
  };
  vm.createContext(context);
  const source = fs.readFileSync(path.join(__dirname, "..", "apps_script", "Code.gs"), "utf8");
  vm.runInContext(source, context);
  return {
    context,
    rows,
    setBeforeLock: callback => { beforeLock = callback; },
    post(payload) {
      const output = context.doPost({ postData: { contents: JSON.stringify(payload) } });
      return JSON.parse(output.getContent());
    },
  };
}

function payload(requestId, overrides = {}) {
  return {
    request_id: requestId,
    token: "local-test-token",
    trade_date: "2026-01-05",
    ticker: "FPT",
    side: "BUY",
    price: 100000,
    quantity: 100,
    fee: 0,
    reason: "smoke test",
    stop_loss: "",
    target: "",
    strategy_tag: "test",
    ...overrides,
  };
}

const validId = "11111111-1111-4111-8111-111111111111";

{
  const app = createHarness();
  const page = app.context.doGet();
  assert.equal(page.file, "Index");
  assert.match(page.title, /Vietnam Equity Toolkit/);
  const result = app.context.checkConnection();
  assert.equal(result.success, true);
  assert.match(result.message, /Equity_Toolkit/);
  assert.equal(app.rows.length, 0); // mở trang và kiểm tra Sheet không ghi dữ liệu
}

{
  const app = createHarness();
  let output = app.context.doGet({ parameter: { request_id: validId, callback: "checkStatus" } });
  assert.equal(output.getContent(), "checkStatus({\"pending\":true});");
  app.context.rememberRequestStatus_(validId, false, "Expected validation response.");
  output = app.context.doGet({ parameter: { request_id: validId, callback: "checkStatus" } });
  assert.equal(output.getContent(), "checkStatus({\"success\":false,\"message\":\"Expected validation response.\"});");
  assert.equal(app.rows.length, 0); // GET chỉ đọc trạng thái, không ghi Trades
}

{
  const app = createHarness();
  const result = app.post(payload(validId, { ticker: "FP1" }));
  assert.equal(result.success, false);
  assert.match(result.message, /3 chữ cái/);
  assert.equal(app.rows.length, 0);
}

{
  const app = createHarness([[
    "trade_id", "timestamp", "trade_date", "ticker", "side", "price",
    "quantity", "fee", "reason", "stop_loss", "target", "strategy_tag",
  ]]);
  const request = payload("33333333-3333-4333-8333-333333333333", { token: undefined });
  assert.equal(app.context.submitTradeFromApp(request).success, true); // giao diện riêng tư không gửi token ra trình duyệt
  assert.equal(app.context.submitTradeFromApp(request).success, true);
  assert.equal(app.rows.length, 2); // retry cùng request_id không ghi dòng thứ hai
}

{
  const app = createHarness();
  const result = app.post(payload(validId, { trade_date: "2026-02-30" }));
  assert.equal(result.success, false);
  assert.match(result.message, /Ngày giao dịch không hợp lệ/);
  assert.equal(app.rows.length, 0);
}

{
  const app = createHarness([["ticker", "trade_id", "timestamp"]]);
  const result = app.post(payload(validId));
  assert.equal(result.success, false);
  assert.match(result.message, /Cấu trúc tab Trades không đúng/);
  assert.equal(app.rows.length, 1); // không nối dữ liệu vào schema sai
}

{
  const app = createHarness([["trade_id", "timestamp", "trade_date", "ticker", "side", "price", "quantity", "fee", "reason", "stop_loss", "target", "strategy_tag"]]);
  const request = payload(validId);
  assert.equal(app.post(request).success, true);
  assert.equal(app.post(request).success, true);
  assert.equal(app.rows.length, 2); // header plus exactly one trade
  assert.equal(app.rows[0][0], "trade_id");
  assert.equal(app.rows[1][3], "FPT");
}

{
  const app = createHarness([["trade_id", "timestamp", "trade_date", "ticker", "side", "price", "quantity", "fee", "reason", "stop_loss", "target", "strategy_tag"]]);
  const result = app.post(payload("44444444-4444-4444-8444-444444444444", {
    reason: "=IMPORTXML(\"https://example.invalid\",\"//a\")",
    strategy_tag: "+SUM(1,1)",
  }));
  assert.equal(result.success, true);
  assert.equal(app.rows[1][8][0], "'");
  assert.equal(app.rows[1][11][0], "'");
}

{
  const app = createHarness();
  const concurrentId = "22222222-2222-4222-8222-222222222222";
  app.setBeforeLock(() => app.context.rememberRequestStatus_(concurrentId, true, "Already recorded."));
  const result = app.post(payload(concurrentId));
  assert.equal(result.success, true);
  assert.equal(app.rows.length, 0); // competing request already wrote; this request must not append
}

console.log("Apps Script smoke tests passed (invalid inputs, valid write, retry and concurrent duplicate).");
