/* SOLID STAMP in the browser: the same exact computations as stage/solid.py (tests/fidelity.mjs).

   Rationals are [n, d] pairs of BigInts, d > 0, in lowest terms; a value is written as a decimal when it ends,
   else as n/d -- the same text as stage/exact.py's fstr, so rows match Python's by string equality.

   SOLID.spectrum(z, keys, maps)        every MDQNM map at TNLDY z: [index, c to 6 decimals, where, lo, hi],
                                        where = on | between | before | after; JSON.stringify of it hashes
                                        (SHA-256) to the digest record's spectrum.sha256
   SOLID.between(z0, z1, keys, maps)    every trigger with z0 <= Z <= z1: {z, pairs [[yi, xi]], hits [[k, xi]]},
                                        in order of Z: the precomputed table, recomputed exactly for that stretch
   keys = [[x, reading, layers]] (x exact text), maps = functions.json's maps ({ztp, unit, ...}).          */
(function (root) {
  "use strict";
  const abs = v => (v < 0n ? -v : v);
  const gcd = (a, b) => { a = abs(a); b = abs(b); while (b) [a, b] = [b, a % b]; return a; };
  function Q(n, d = 1n) {
    if (d === 0n) throw new Error("division by zero");
    if (d < 0n) { n = -n; d = -d; }
    const g = gcd(n, d) || 1n;
    return [n / g, d / g];
  }
  function parse(s) {
    s = String(s).trim();
    if (s.includes("/")) { const [a, b] = s.split("/"); return Q(BigInt(a), BigInt(b)); }
    const m = /^([+-]?)(\d*)(?:\.(\d*))?$/.exec(s);
    if (!m) throw new Error("not exact text: " + s);
    const frac = m[3] || "", n = BigInt((m[2] || "0") + frac) * (m[1] === "-" ? -1n : 1n);
    return Q(n, 10n ** BigInt(frac.length));
  }
  const add = (a, b) => Q(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
  const sub = (a, b) => Q(a[0] * b[1] - b[0] * a[1], a[1] * b[1]);
  const mul = (a, b) => Q(a[0] * b[0], a[1] * b[1]);
  const div = (a, b) => Q(a[0] * b[1], a[1] * b[0]);
  const cmp = (a, b) => { const l = a[0] * b[1], r = b[0] * a[1]; return l < r ? -1 : l > r ? 1 : 0; };

  /* fstr: a decimal when the denominator has no prime but 2 and 5, else n/d; no trailing zeros. */
  function text(q) {
    let [n, d] = q, k2 = 0, k5 = 0, r = d;
    while (r % 2n === 0n) { r /= 2n; k2++; }
    while (r % 5n === 0n) { r /= 5n; k5++; }
    if (r !== 1n) return `${n}/${d}`;
    const places = Math.max(k2, k5), scaled = abs(n) * 10n ** BigInt(places) / d;
    let s = scaled.toString().padStart(places + 1, "0");
    if (places) s = s.slice(0, -places) + "." + s.slice(-places);
    if (s.includes(".")) s = s.replace(/0+$/, "").replace(/\.$/, "");
    return (n < 0n ? "-" : "") + s;
  }
  /* fmt: to `places` decimals, half away from zero. */
  function fmt(q, places = 6) {
    const [n, d] = q, p = 10n ** BigInt(places), t = abs(n) * p;
    let w = t / d; if (2n * (t - w * d) >= d) w += 1n;
    const neg = n < 0n && w !== 0n;
    let s = w.toString().padStart(places + 1, "0");
    if (places) s = s.slice(0, -places) + "." + s.slice(-places);
    return (neg ? "-" : "") + s;
  }

  function prepare(keys, maps) {
    return { ks: keys.map(k => parse(k[0])), ms: maps.map(m => [parse(m.ztp), parse(m.unit)]) };
  }
  /* the first index i with ks[i] >= c (cmp), as bisect_left */
  function lower(ks, c) {
    let lo = 0, hi = ks.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (cmp(ks[mid], c) < 0) lo = mid + 1; else hi = mid; }
    return lo;
  }
  function upper(ks, c) {
    let lo = 0, hi = ks.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (cmp(ks[mid], c) <= 0) lo = mid + 1; else hi = mid; }
    return lo;
  }

  function spectrum(z, keys, maps, prep) {
    const { ks, ms } = prep || prepare(keys, maps), Z = typeof z === "string" ? parse(z) : z, out = [];
    ms.forEach(([ztp, u], k) => {
      const c = div(sub(Z, ztp), u), i = lower(ks, c);
      if (i < ks.length && cmp(ks[i], c) === 0) out.push([k, fmt(c), "on", i, i]);
      else if (i === 0) out.push([k, fmt(c), "before", null, 0]);
      else if (i === ks.length) out.push([k, fmt(c), "after", ks.length - 1, null]);
      else out.push([k, fmt(c), "between", i - 1, i]);
    });
    return out;
  }

  const ZTP = Q(14160n), U = Q(100n);
  function between(z0, z1, keys, maps, prep) {
    const { ks, ms } = prep || prepare(keys, maps);
    const lo = typeof z0 === "string" ? parse(z0) : z0, hi = typeof z1 === "string" ? parse(z1) : z1;
    const rows = new Map();
    const at = z => { const t = text(z); if (!rows.has(t)) rows.set(t, { z: t, q: z, pairs: [], hits: [] }); return rows.get(t); };
    // REVOTT: Y + X in [(lo - 14160)/100, (hi - 14160)/100]
    const s0 = div(sub(lo, ZTP), U), s1 = div(sub(hi, ZTP), U);
    ks.forEach((y, i) => {
      for (let j = lower(ks, sub(s0, y)); j < upper(ks, sub(s1, y)); j++) at(add(ZTP, mul(U, add(y, ks[j])))).pairs.push([i, j]);
    });
    // MDQNM: x in [(lo - Ztp)/U, (hi - Ztp)/U]
    ms.forEach(([ztp, u], k) => {
      let a = div(sub(lo, ztp), u), b = div(sub(hi, ztp), u);
      if (u[0] < 0n) [a, b] = [b, a];                                  // a unit counting in reverse
      for (let j = lower(ks, a); j < upper(ks, b); j++) at(add(ztp, mul(u, ks[j]))).hits.push([k, j]);
    });
    const out = [...rows.values()].sort((a, b) => cmp(a.q, b.q));
    out.forEach(r => { r.pairs.sort((a, b) => a[0] - b[0] || a[1] - b[1]); r.hits.sort((a, b) => a[0] - b[0] || a[1] - b[1]); delete r.q; });
    return out;
  }

  const kind = r => (r.pairs.length && r.hits.length ? "revott+mdqnm" : r.pairs.length ? "revott" : "mdqnm");
  const api = { Q, parse, add, sub, mul, div, cmp, text, fmt, prepare, spectrum, between, kind };
  root.SOLID = api;
  if (typeof module === "object" && module && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
