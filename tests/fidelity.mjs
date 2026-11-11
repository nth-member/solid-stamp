// docs/solid.js against the Python reference: every spectrum byte for byte (and its SHA-256), and the triggers of
// each stretch exactly as the precomputed database holds them.    node tests/fidelity.mjs
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const root = new URL("..", import.meta.url).pathname;
const S = require(root + "docs/solid.js"), C = require(root + "docs/nsukka-yg-clock.js");
const keys = JSON.parse(readFileSync(root + "docs/data/keys.json", "utf8"));
const maps = JSON.parse(readFileSync(root + "docs/data/functions.json", "utf8")).maps;
const prep = S.prepare(keys, maps);

// cases: the next 30 days' triggers, instants every 97 minutes, odd rationals, and stretches of a day each
const now = Date.now(), spectra = [], ranges = [];
for (let t = now - 5 * 864e5; t < now + 30 * 864e5; t += 97 * 6e4) spectra.push(S.text(S.Q(BigInt(C.zOf(t).num), BigInt(23 * 86400000))));
for (const z of ["20824", "478949/23", "187411/9", "14160", "22440", "-15360", "56640", "0", "1/3", "-100000.5", "2900000"]) spectra.push(z);
for (let d = -3; d < 30; d += 1) {
  const z0 = C.zOf(now + d * 864e5).num, z1 = C.zOf(now + (d + 1) * 864e5).num, den = BigInt(23 * 86400000);
  ranges.push([S.text(S.Q(BigInt(z0), den)), S.text(S.Q(BigInt(z1), den))]);
}
ranges.push(["20000", "20100"], ["-15360", "-15000"], ["56000", "56640"]);
const ref = JSON.parse(execFileSync("python3", [root + "tests/fidelity_ref.py"], { input: JSON.stringify({ spectra, ranges }), maxBuffer: 1 << 30 }).toString());

let ok = 0, bad = 0;
spectra.forEach((z, i) => {
  const js = JSON.stringify(S.spectrum(z, keys, maps, prep)), sha = createHash("sha256").update(js).digest("hex");
  if (js === ref.spectra[i].json && sha === ref.spectra[i].sha256) ok++; else { bad++; if (bad < 5) console.log("spectrum differs at", z); }
});
const sp = ok;
ranges.forEach(([z0, z1], i) => {
  const js = JSON.stringify(S.between(z0, z1, keys, maps, prep)), py = JSON.stringify(ref.ranges[i]);
  if (js === py) ok++; else { bad++; if (bad < 5) console.log("stretch differs", z0, z1, js.length, py.length); }
});
const rows = ref.ranges.reduce((n, r) => n + r.length, 0);
console.log(`spectra ${sp}/${spectra.length} identical; stretches ${ok - sp}/${ranges.length} identical (${rows} triggers); ${bad ? "FAIL" : "all identical"}`);
process.exit(bad ? 1 : 0);
