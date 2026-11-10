/** Operaciones de imagen puras para la versión que corre en el navegador (sin DOM: sirven en el Web Worker).
 *  Son equivalentes simplificados de backend/app/pipelines/basic.py (sin CLAHE ni NLM). */

export interface Img { w: number; h: number; d: Float32Array } // RGB entrelazado, 0..1

export const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);

export function fromRGBA(u8: Uint8ClampedArray, w: number, h: number): Img {
  const d = new Float32Array(w * h * 3);
  for (let i = 0, j = 0; i < w * h * 4; i += 4, j += 3) { d[j] = u8[i] / 255; d[j + 1] = u8[i + 1] / 255; d[j + 2] = u8[i + 2] / 255; }
  return { w, h, d };
}

export function toRGBA(img: Img): Uint8ClampedArray {
  const out = new Uint8ClampedArray(img.w * img.h * 4);
  for (let i = 0, j = 0; j < img.d.length; i += 4, j += 3) { out[i] = img.d[j] * 255 + 0.5; out[i + 1] = img.d[j + 1] * 255 + 0.5; out[i + 2] = img.d[j + 2] * 255 + 0.5; out[i + 3] = 255; }
  return out;
}

export function lumaOf(img: Img): Float32Array {
  const n = img.w * img.h, y = new Float32Array(n);
  for (let i = 0, j = 0; i < n; i++, j += 3) y[i] = 0.299 * img.d[j] + 0.587 * img.d[j + 1] + 0.114 * img.d[j + 2];
  return y;
}

/** Desenfoque de caja separable con sumas acumuladas (borde replicado). */
export function boxBlur(src: Float32Array, w: number, h: number, r: number): Float32Array {
  if (r < 1) return src.slice();
  const tmp = new Float32Array(src.length), out = new Float32Array(src.length), k = 2 * r + 1;
  for (let y = 0; y < h; y++) {
    const row = y * w; let s = 0;
    for (let x = -r; x <= r; x++) s += src[row + Math.min(w - 1, Math.max(0, x))];
    for (let x = 0; x < w; x++) {
      tmp[row + x] = s / k;
      s += src[row + Math.min(w - 1, x + r + 1)] - src[row + Math.max(0, x - r)];
    }
  }
  for (let x = 0; x < w; x++) {
    let s = 0;
    for (let y = -r; y <= r; y++) s += tmp[Math.min(h - 1, Math.max(0, y)) * w + x];
    for (let y = 0; y < h; y++) {
      out[y * w + x] = s / k;
      s += tmp[Math.min(h - 1, y + r + 1) * w + x] - tmp[Math.max(0, y - r) * w + x];
    }
  }
  return out;
}

/** Aproximación gaussiana: 3 pasadas de caja. */
export function gaussApprox(src: Float32Array, w: number, h: number, sigma: number): Float32Array {
  const r = Math.max(1, Math.round(Math.sqrt((12 * sigma * sigma) / 3 + 1) / 2));
  return boxBlur(boxBlur(boxBlur(src, w, h, r), w, h, r), w, h, r);
}

export function denoise(img: Img, strength: number, report?: (p: number) => void): Img {
  if (strength <= 0.01) return img;
  const { w, h } = img, n = w * h;
  const y = new Float32Array(n), cb = new Float32Array(n), cr = new Float32Array(n);
  for (let i = 0, j = 0; i < n; i++, j += 3) {
    const r = img.d[j], g = img.d[j + 1], b = img.d[j + 2];
    y[i] = 0.299 * r + 0.587 * g + 0.114 * b; cb[i] = -0.1687 * r - 0.3313 * g + 0.5 * b; cr[i] = 0.5 * r - 0.4187 * g - 0.0813 * b;
  }
  // luminancia: bilateral 5x5 (preserva bordes); crominancia: desenfoque más fuerte (el ruido de color es más molesto y menos visible)
  const sr = 0.03 + 0.12 * strength, inv2sr = 1 / (2 * sr * sr), sp = 1.1, inv2sp = 1 / (2 * sp * sp);
  const wsp = new Float32Array(25);
  for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) wsp[(dy + 2) * 5 + dx + 2] = Math.exp(-(dx * dx + dy * dy) * inv2sp);
  const yo = new Float32Array(n);
  for (let py = 0; py < h; py++) {
    for (let px = 0; px < w; px++) {
      const c = y[py * w + px]; let acc = 0, ws = 0;
      for (let dy = -2; dy <= 2; dy++) {
        const yy = Math.min(h - 1, Math.max(0, py + dy)) * w;
        for (let dx = -2; dx <= 2; dx++) {
          const v = y[yy + Math.min(w - 1, Math.max(0, px + dx))], dv = v - c;
          const wt = wsp[(dy + 2) * 5 + dx + 2] * Math.exp(-dv * dv * inv2sr);
          acc += wt * v; ws += wt;
        }
      }
      yo[py * w + px] = acc / ws;
    }
    if (report && py % 64 === 0) report(py / h);
  }
  const rc = Math.max(1, Math.round(1 + 3 * strength));
  const cbo = boxBlur(cb, w, h, rc), cro = boxBlur(cr, w, h, rc);
  const out = new Float32Array(img.d.length);
  for (let i = 0, j = 0; i < n; i++, j += 3) {
    const Y = yo[i], B = cbo[i], R = cro[i];
    out[j] = clamp01(Y + 1.402 * R); out[j + 1] = clamp01(Y - 0.34414 * B - 0.71414 * R); out[j + 2] = clamp01(Y + 1.772 * B);
  }
  return { w, h, d: out };
}

/** Balance de blancos gris-mundo limitado, gamma hacia luminancia objetivo, estiramiento de niveles y saturación suave. */
export function autoColor(img: Img, strength: number): Img {
  if (strength <= 0.01) return img;
  const { w, h } = img, n = w * h, d = new Float32Array(img.d);
  const m = [0, 0, 0];
  for (let j = 0; j < d.length; j += 3) { m[0] += d[j]; m[1] += d[j + 1]; m[2] += d[j + 2]; }
  const avg = (m[0] + m[1] + m[2]) / 3 + 1e-6, lim = 1 + 0.1 * strength;
  const gain = m.map((v) => Math.min(lim, Math.max(1 / lim, avg / (v + 1e-6))));
  const mix = gain.map((g) => 1 - 0.7 * strength + 0.7 * strength * g);
  let sum = 0;
  for (let j = 0; j < d.length; j += 3) { d[j] = clamp01(d[j] * mix[0]); d[j + 1] = clamp01(d[j + 1] * mix[1]); d[j + 2] = clamp01(d[j + 2] * mix[2]); sum += (d[j] + d[j + 1] + d[j + 2]) / 3; }
  const mean = sum / n;
  let gamma = Math.log(0.45) / Math.log(Math.min(0.95, Math.max(0.05, mean)));
  gamma = Math.min(1.5, Math.max(0.65, gamma)); gamma = 1 + (gamma - 1) * strength * 0.8;
  // histograma de luminancia para el estiramiento (percentiles 0,5 % y 99,5 %)
  const hist = new Uint32Array(256);
  for (let j = 0; j < d.length; j += 3) hist[Math.min(255, ((0.299 * d[j] + 0.587 * d[j + 1] + 0.114 * d[j + 2]) * 255) | 0)]++;
  let acc = 0, lo = 0, hi = 255;
  for (let i = 0; i < 256; i++) { acc += hist[i]; if (acc >= n * 0.005) { lo = i; break; } }
  acc = 0;
  for (let i = 255; i >= 0; i--) { acc += hist[i]; if (acc >= n * 0.005) { hi = i; break; } }
  const loV = (lo / 255) * 0.5 * strength, hiV = 1 - (1 - hi / 255) * 0.5 * strength, span = Math.max(0.2, hiV - loV);
  const sat = 1 + 0.1 * strength;
  for (let j = 0; j < d.length; j += 3) {
    let r = Math.pow(Math.max(1e-6, d[j]), gamma), g = Math.pow(Math.max(1e-6, d[j + 1]), gamma), b = Math.pow(Math.max(1e-6, d[j + 2]), gamma);
    r = clamp01((r - loV) / span); g = clamp01((g - loV) / span); b = clamp01((b - loV) / span);
    const y = 0.299 * r + 0.587 * g + 0.114 * b;
    d[j] = clamp01(y + (r - y) * sat); d[j + 1] = clamp01(y + (g - y) * sat); d[j + 2] = clamp01(y + (b - y) * sat);
  }
  return { w, h, d };
}

export function shadowsHighlights(img: Img, shadows: number, highlights: number): Img {
  if (Math.abs(shadows) < 0.01 && Math.abs(highlights) < 0.01) return img;
  const { w, h } = img, y = lumaOf(img), base = gaussApprox(y, w, h, Math.max(3, Math.min(w, h) / 60)), d = new Float32Array(img.d);
  for (let i = 0, j = 0; i < w * h; i++, j += 3) {
    const l = y[i], b = base[i];
    const sw = Math.pow(clamp01(1 - b * 2), 1.5), hw = Math.pow(clamp01(b * 2 - 1), 1.5);
    const l2 = clamp01(l + shadows * 0.45 * sw * (1 - l) - highlights * 0.35 * hw * l);
    const g = l > 1e-4 ? Math.min(4, l2 / l) : 1;
    if (l > 1e-4) { d[j] = clamp01(d[j] * g); d[j + 1] = clamp01(d[j + 1] * g); d[j + 2] = clamp01(d[j + 2] * g); }
    else { const add = l2 - l; d[j] = clamp01(d[j] + add); d[j + 1] = clamp01(d[j + 1] + add); d[j + 2] = clamp01(d[j + 2] + add); }
  }
  return { w, h, d };
}

/** Nitidez en luminancia sobre RGBA de 8 bits (en sitio): umbral anti-ruido y recorte local anti-halo. */
export function sharpenRGBA(u8: Uint8ClampedArray, w: number, h: number, strength: number, radius = 1.2): void {
  if (strength <= 0.01) return;
  const n = w * h, y = new Float32Array(n);
  for (let i = 0, j = 0; i < n; i++, j += 4) y[i] = (0.299 * u8[j] + 0.587 * u8[j + 1] + 0.114 * u8[j + 2]) / 255;
  const blur = gaussApprox(y, w, h, radius), amount = 0.2 + 0.9 * strength, margin = 0.04;
  for (let py = 0; py < h; py++) {
    for (let px = 0; px < w; px++) {
      const i = py * w + px; const detail = y[i] - blur[i];
      if (Math.abs(detail) < 0.008) continue;
      let mn = 1, mx = 0;
      for (let dy = -1; dy <= 1; dy++) { const yy = Math.min(h - 1, Math.max(0, py + dy)) * w; for (let dx = -1; dx <= 1; dx++) { const v = y[yy + Math.min(w - 1, Math.max(0, px + dx))]; if (v < mn) mn = v; if (v > mx) mx = v; } }
      const target = Math.min(mx + margin, Math.max(mn - margin, y[i] + amount * detail));
      const delta = (target - y[i]) * 255, j = i * 4;
      u8[j] = u8[j] + delta; u8[j + 1] = u8[j + 1] + delta; u8[j + 2] = u8[j + 2] + delta; // el array acotado satura solo
    }
  }
}

export interface Analysis {
  width: number; height: number; megapixels: number; resolution: string; blur: string; noise: string; compression: string; exposure: string; faces: number; recommendations: string[];
}

/** Diagnóstico sobre una versión reducida (≤768 px) en escala de grises. */
export function analyzeGray(gray: Uint8ClampedArray | Float32Array, gw: number, gh: number, fullW: number, fullH: number): Analysis {
  const g = (i: number) => gray[i] as number, n = gw * gh;
  let lapSum = 0, lapSq = 0, noiseSum = 0, cnt = 0, mean = 0, sq = 0;
  for (let i = 0; i < n; i++) { mean += g(i); sq += g(i) * g(i); }
  mean /= n; const sd = Math.sqrt(Math.max(0, sq / n - mean * mean));
  for (let y = 1; y < gh - 1; y++) for (let x = 1; x < gw - 1; x++) {
    const i = y * gw + x, c = g(i);
    const lap = g(i - 1) + g(i + 1) + g(i - gw) + g(i + gw) - 4 * c;
    lapSum += lap; lapSq += lap * lap;
    const im = g(i - gw - 1) - 2 * g(i - gw) + g(i - gw + 1) - 2 * g(i - 1) + 4 * c - 2 * g(i + 1) + g(i + gw - 1) - 2 * g(i + gw) + g(i + gw + 1);
    noiseSum += Math.abs(im); cnt++;
  }
  const lapVar = lapSq / cnt - (lapSum / cnt) ** 2, sigma = (noiseSum * Math.sqrt(0.5 * Math.PI)) / (6 * cnt);
  let on = 0, off = 0, non = 0, noff = 0;
  for (let y = 0; y < gh; y++) for (let x = 0; x < gw - 1; x++) { const dv = Math.abs(g(y * gw + x + 1) - g(y * gw + x)); if (x % 8 === 7) { on += dv; non++; } else { off += dv; noff++; } }
  const block = non && noff ? on / non / (off / noff + 1e-6) : 1;
  const luma = mean / 255, contrast = sd / 255, longSide = Math.max(fullW, fullH);
  const resolution = longSide < 900 ? "baja" : longSide < 2000 ? "media" : "alta";
  const blur = lapVar < 40 ? "alto" : lapVar < 150 ? "moderado" : "bajo";
  const noise = sigma > 6 ? "alto" : sigma > 2.5 ? "moderado" : "bajo";
  const compression = block > 1.25 ? "fuerte" : block > 1.08 ? "moderada" : "baja";
  const exposure = luma < 0.3 ? "oscura" : luma > 0.7 ? "clara" : "normal";
  const rec: string[] = [];
  if (resolution === "baja") rec.push("Resolución baja: escalar ayudará, pero los detalles nuevos serán una reconstrucción aproximada.");
  if (blur !== "bajo") rec.push("Hay desenfoque: se recomienda nitidez moderada. Si es muy fuerte, el detalle que no está en la foto no se puede recuperar.");
  if (noise !== "bajo") rec.push("Se detecta ruido digital: activa la reducción de ruido.");
  if (compression !== "baja") rec.push("Parece muy comprimida (bloques JPEG): el modelo de superresolución también suaviza estos artefactos.");
  if (exposure === "oscura") rec.push("La imagen está subexpuesta: levanta las sombras.");
  if (contrast < 0.12) rec.push("Contraste bajo: la corrección de color puede darle más vida.");
  if (!rec.length) rec.push("La imagen está en buen estado; una mejora suave es suficiente.");
  return { width: fullW, height: fullH, megapixels: Math.round((fullW * fullH) / 1e4) / 100, resolution, blur, noise, compression, exposure, faces: 0, recommendations: rec };
}
