"use strict";

// Check inline JavaScript syntax and the minimum local token length without
// loading the user's ignored config.local.js or calling Google services.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "..", "web_form", "index.html"), "utf8");
const blocks = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)];
const inlineScripts = blocks
  .filter(([, attributes, body]) => !/\bsrc\s*=/.test(attributes) && body.trim())
  .map(([, , body]) => body);

assert.ok(inlineScripts.length > 0, "Expected at least one inline form script.");
for (const source of inlineScripts) new vm.Script(source);
assert.match(html, /FORM_TOKEN\.length\s*>=\s*32/);

console.log(`Web form smoke test passed (${inlineScripts.length} inline script compiled).`);
