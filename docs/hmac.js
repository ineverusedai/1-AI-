/* HMAC-SHA256 (순수 자바스크립트).
 * crypto.subtle 은 https/localhost 에서만 동작해서, 파일을 더블클릭해서 열었을 때(file://)도
 * 채점되도록 직접 구현했다. Python 쪽 common/answer_hash.py 와 같은 값을 낸다. */
(function () {
  function primes(n) {
    const out = [];
    for (let c = 2; out.length < n; c++) if (out.every(p => c % p)) out.push(c);
    return out;
  }
  const P = primes(64);
  const frac = x => Math.floor((x - Math.floor(x)) * 4294967296) >>> 0;
  const K = new Uint32Array(P.map(p => frac(Math.cbrt(p))));
  const H0 = P.slice(0, 8).map(p => frac(Math.sqrt(p)));
  const rotr = (x, n) => (x >>> n) | (x << (32 - n));

  function sha256(bytes) {
    const len = bytes.length;
    const n = ((len + 9 + 63) >> 6) << 6;
    const m = new Uint8Array(n);
    m.set(bytes);
    m[len] = 0x80;
    const dv = new DataView(m.buffer);
    dv.setUint32(n - 8, Math.floor((len * 8) / 4294967296));
    dv.setUint32(n - 4, (len * 8) >>> 0);
    const H = Uint32Array.from(H0);
    const W = new Uint32Array(64);
    for (let i = 0; i < n; i += 64) {
      for (let t = 0; t < 16; t++) W[t] = dv.getUint32(i + t * 4);
      for (let t = 16; t < 64; t++) {
        const x = W[t - 15], y = W[t - 2];
        const s0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3);
        const s1 = rotr(y, 17) ^ rotr(y, 19) ^ (y >>> 10);
        W[t] = (W[t - 16] + s0 + W[t - 7] + s1) >>> 0;
      }
      let a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
      for (let t = 0; t < 64; t++) {
        const t1 = (h + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + K[t] + W[t]) >>> 0;
        const t2 = ((rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
      H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
    }
    const out = new Uint8Array(32);
    const odv = new DataView(out.buffer);
    for (let i = 0; i < 8; i++) odv.setUint32(i * 4, H[i]);
    return out;
  }

  function hexToBytes(hex) {
    const out = new Uint8Array(hex.length / 2);
    for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
    return out;
  }
  const toHex = b => Array.from(b, x => x.toString(16).padStart(2, "0")).join("");
  const utf8 = s => new TextEncoder().encode(s);

  function hmacSha256Hex(keyHex, message) {
    let key = hexToBytes(keyHex);
    if (key.length > 64) key = sha256(key);
    const k = new Uint8Array(64);
    k.set(key);
    const msg = utf8(message);
    const inner = new Uint8Array(64 + msg.length);
    const outer = new Uint8Array(64 + 32);
    for (let i = 0; i < 64; i++) { inner[i] = k[i] ^ 0x36; outer[i] = k[i] ^ 0x5c; }
    inner.set(msg, 64);
    outer.set(sha256(inner), 64);
    return toHex(sha256(outer));
  }

  window.HV = window.HV || {};
  window.HV.sha256Hex = s => toHex(sha256(utf8(s)));
  window.HV.answerHash = (keyHex, mission, qNo, answer) => hmacSha256Hex(keyHex, `${mission}|${qNo}|${answer}`);
})();
