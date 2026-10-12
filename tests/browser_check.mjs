// SPDX-License-Identifier: GPL-2.0-or-later
// Open clients/web/index.html in headless Chromium against a live sidecar and
// report what the page shows.  Test tooling only (global playwright in the
// container).  usage: node tests/browser_check.mjs PAGE_URL SIDECAR_URL SECONDS
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright"); } catch { pw = require(process.env.PLAYWRIGHT_PATH || "playwright"); }
const [, , page_url, ws_url, secs] = process.argv;
const browser = await pw.chromium.launch();
const page = await browser.newPage();
const logs = [];
page.on("console", (m) => logs.push(m.text()));
page.on("pageerror", (e) => logs.push("PAGEERROR " + e.message));
await page.goto(page_url);
await page.fill("#url", ws_url);
await page.dispatchEvent("#url", "change");
const t0 = Date.now();
const samples = [];
while (Date.now() - t0 < Number(secs || 10) * 1000) {
  await page.waitForTimeout(2000);
  samples.push({
    t: ((Date.now() - t0) / 1000).toFixed(1),
    link: await page.textContent("#link"),
    pos: await page.textContent("#pos"),
    state: (await page.textContent("#state")).replace(/\s+/g, " "),
    prog: (await page.textContent("#prog")).replace(/\s+/g, " "),
    pend: (await page.textContent("#pend")).replace(/\s+/g, " "),
    stats: await page.textContent("#stats"),
  });
  console.log(JSON.stringify(samples.at(-1)));
}
await page.screenshot({ path: process.env.SHOT || "logs/browser_check.png" });
console.log("console:", JSON.stringify(logs.slice(-10)));
await browser.close();
