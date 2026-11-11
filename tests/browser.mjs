#!/usr/bin/env node
/**
 * The page in a real browser: headless Firefox over raw WebDriver (geckodriver), serving tests/.fixture/ (docs/ with
 * two days of digests recorded by tests/fixture.py), at a desktop width and at a phone's.
 *
 *   python3 tests/fixture.py && node tests/browser.mjs [--shots DIR] [--base URL]
 *
 * --base runs the same cases against the published site.
 */
import { spawn, execFileSync } from "node:child_process";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const FIX = path.join(ROOT, "tests", ".fixture");
const arg = k => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : null);
const SHOTS = arg("--shots"), WEB = 8767, WD = 4458, BASE = arg("--base") || `http://127.0.0.1:${WEB}/`;
let failures = 0;
const check = (name, ok, detail = "") => { console.log(`  ${ok ? "ok  " : "FAIL"}  ${name}${detail ? `  — ${detail}` : ""}`); if (!ok) failures++; };
const sleep = ms => new Promise(r => setTimeout(r, ms));

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const u = new URL(req.url, "http://x/");
  if (u.pathname === "/usage.js" || req.url.includes("usage.js")) { res.writeHead(200, { "content-type": "text/javascript" }); return res.end(""); }
  const p = path.join(FIX, decodeURIComponent(u.pathname === "/" ? "/index.html" : u.pathname));
  if (!p.startsWith(FIX) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": TYPES[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(res);
}).listen(WEB);

const gd = spawn("geckodriver", ["--port", String(WD)], { stdio: "ignore" });
for (let i = 0; i < 50; i++) { try { await fetch(`http://127.0.0.1:${WD}/status`); break; } catch { await sleep(200); } }
async function call(method, p, body) {
  const res = await fetch(`http://127.0.0.1:${WD}${p}`, { method, headers: { "content-type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`${method} ${p} -> ${res.status} ${JSON.stringify(json).slice(0, 300)}`);
  return json.value;
}
const { sessionId: sid } = await call("POST", "/session", { capabilities: { alwaysMatch: { browserName: "firefox", "moz:firefoxOptions": { args: ["-headless"] } } } });
const S = p => `/session/${sid}${p}`;
const js = (script, ...args) => call("POST", S("/execute/sync"), { script, args });
const until = async (script, ms = 20000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = await js(script).catch(() => null); if (v) return v; await sleep(150); } return null; };
const shot = async name => { if (!SHOTS) return; fs.mkdirSync(SHOTS, { recursive: true }); fs.writeFileSync(path.join(SHOTS, name + ".png"), Buffer.from(await call("GET", S("/screenshot")), "base64")); };

// the day's triggers by the Python reference, to compare with the page's own LOOK UP
const today = new Date(Date.now() + 3600000).toISOString().slice(0, 10);
const C = (await import(path.join(ROOT, "docs/nsukka-yg-clock.js"))).default;
const d0 = Date.parse(today + "T00:00:00+01:00");
const den = 23 * 86400000, frac = ms => { const n = C.zOf(ms).num; return `${n}/${den}`; };
const ref = JSON.parse(execFileSync("python3", [path.join(ROOT, "tests/fidelity_ref.py")], { input: JSON.stringify({ spectra: [], ranges: [[frac(d0), frac(d0 + 86400000 - 1)]] }) }).toString());
const expectDay = ref.ranges[0].filter(r => true).length;

try {
  for (const [label, w, h] of [["desktop", 1280, 900], ["phone", 390, 844]]) {
    console.log(label);
    await call("POST", S("/window/rect"), { width: w, height: h });
    await call("POST", S("/url"), { url: BASE });
    check("the page loads", await until(`return document.title === "SOLID STAMP" && /TNLDY \\d+\\.\\d{6}/.test(document.querySelector("#clock").textContent)`));
    const rows = await until(`const n = document.querySelectorAll("#next tr.pick").length; return n || null`);
    check("NEXT lists the coming triggers", rows > 0, `${rows} rows`);
    const clock = await js(`return document.querySelector("#clock").textContent`);
    check("the clock line counts down to the next match", /next match in/.test(clock), clock);
    await shot(`${label}-next`);
    await js(`document.querySelector("#next tr.pick").click()`);
    const sp = await until(`const t = document.querySelectorAll("#spt tr[data-s]").length; return t || null`);
    check("a coming trigger opens: its matches and the full spectrum", sp === 666, `${sp} spectrum rows`);
    const on = await js(`return document.querySelectorAll("#spt tr[data-s] .on").length`);
    const fn = await js(`return document.querySelectorAll("#view h3").length`);
    check("its matched functions are 'on' in the spectrum", on >= 1 && fn >= 1, `${on} on`);
    await shot(`${label}-trigger`);
    await js(`document.querySelector('[data-tab="digests"]').click()`);
    const dg = await until(`const t = document.querySelector("#digests").textContent; return /No digest/.test(t) ? -1 : document.querySelectorAll("#digests tr.pick").length || null`);
    if (dg === -1) console.log("  --    DIGESTS: no digest sent yet; the digest checks wait for the first one");
    else {
      check("DIGESTS lists the digests as sent", dg > 0, `${dg} rows`);
      await js(`[...document.querySelectorAll("#digests tr.pick")].find(r => r.lastElementChild.textContent !== "—").click()`);
      const ver = await until(`const v = document.querySelector("#view .ok"); return v ? v.textContent : null`);
      check("a sent digest: the spectrum read in the page is the one sent", !!ver, ver || "no verification line");
      const items = await js(`return document.querySelectorAll("#view a[rel=noopener]").length`);
      check("its feed items are listed with their links", items > 0, `${items} items`);
      await shot(`${label}-digest`);
    }
    if (arg("--open")) {                                   // a notification's tap: the page opened on its trigger
      await call("POST", S("/url"), { url: BASE + arg("--open") });
      const t = await until(`const v = document.querySelector("#view"); return v && !v.hidden && document.querySelectorAll("#spt tr[data-s]").length ? document.querySelector("#view h2").textContent : null`);
      check("a notification's link opens its trigger, with the full spectrum", !!t, t || "nothing shown");
      await shot(`${label}-tap`);
    }
    await js(`document.querySelector('[data-tab="lookup"]').click(); document.querySelector("#zIn").value = "20824"; document.querySelector("#zGo").click()`);
    const z = await until(`const h = document.querySelector("#lookupOut h3"); return h ? h.textContent : null`);
    check("LOOK UP a TNLDY: 20824 is a match, with 4 REVOTT pairs", /a match/.test(z) && (await js(`return document.querySelectorAll("#lookupOut table")[0].querySelectorAll("tr").length - 1`)) === 4, z);
    await js(`document.querySelector("#day").value = "${today}"; document.querySelector("#dayGo").click()`);
    const dayText = await until(`const h = document.querySelector("#lookupOut h3"); return h && /triggers/.test(h.textContent) ? h.textContent : null`);
    const n = dayText ? +dayText.match(/: (\d+) triggers/)[1] : -1;
    check("LOOK UP a day: as many triggers as the database holds", n === expectDay, `${n} in the page, ${expectDay} in the database`);
    await shot(`${label}-lookup`);
    const over = await js(`return document.documentElement.scrollWidth - window.innerWidth`);
    check("no sideways scroll of the page", over <= 0, `${over}px`);
  }
} finally {
  await call("DELETE", S("")).catch(() => {});
  gd.kill(); server.close();
}
console.log(failures ? `${failures} FAILED` : "all ok");
process.exit(failures ? 1 : 0);
