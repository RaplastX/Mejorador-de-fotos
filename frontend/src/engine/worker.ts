/// <reference lib="webworker" />
/** Web Worker: ejecuta el pipeline de mejora (operaciones clásicas + superresolución ONNX por mosaicos). */
import * as ort from "onnxruntime-web/webgpu";
import { autoColor, denoise, fromRGBA, shadowsHighlights, sharpenRGBA, toRGBA } from "./imageops";

export interface RunMsg {
  type: "run"; id: string; rgba: ArrayBuffer; w: number; h: number;
  o: { denoise: number; color: number; sharpen: number; shadows: number; highlights: number; factor: number; tw: number; th: number };
}
export type Out =
  | { type: "progress"; id: string; p: number; stage: string }
  | { type: "provider"; provider: string; threads: number }
  | { type: "done"; id: string; rgba: ArrayBuffer; w: number; h: number }
  | { type: "error"; id: string; message: string }
  | { type: "cancelled"; id: string };

const ctx = self as unknown as DedicatedWorkerGlobalScope;
const post = (m: Out, tr: Transferable[] = []) => ctx.postMessage(m, tr);
const cancelled = new Set<string>();
const TILE = 128, PAD = 12;
let session: ort.InferenceSession | null = null;

async function getSession(): Promise<ort.InferenceSession> {
  if (session) return session;
  const threads = ctx.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 2) : 1;
  ort.env.wasm.wasmPaths = "/ort/";
  ort.env.wasm.numThreads = threads;
  const url = "/models/realesr-general-x4v3.onnx";
  let provider = "wasm";
  try {
    if ("gpu" in navigator && (await (navigator as unknown as { gpu: { requestAdapter(): Promise<unknown> } }).gpu.requestAdapter())) {
      session = await ort.InferenceSession.create(url, { executionProviders: ["webgpu"], graphOptimizationLevel: "all" });
      provider = "webgpu";
    }
  } catch { session = null; }
  if (!session) session = await ort.InferenceSession.create(url, { executionProviders: ["wasm"], graphOptimizationLevel: "all" });
  post({ type: "provider", provider, threads });
  return session;
}

async function upscale4(img: { w: number; h: number; d: Float32Array }, id: string, report: (p: number) => void): Promise<Uint8ClampedArray> {
  const s = await getSession(), { w, h, d } = img, S = 4;
  const out = new Uint8ClampedArray(w * S * h * S * 4);
  for (let i = 3; i < out.length; i += 4) out[i] = 255;
  const tilesX = Math.ceil(w / TILE), tilesY = Math.ceil(h / TILE);
  let done = 0;
  for (let ty = 0; ty < h; ty += TILE) {
    for (let tx = 0; tx < w; tx += TILE) {
      if (cancelled.has(id)) throw new Error("__cancelled__");
      const y1 = Math.min(ty + TILE, h), x1 = Math.min(tx + TILE, w);
      const py0 = Math.max(ty - PAD, 0), px0 = Math.max(tx - PAD, 0), py1 = Math.min(y1 + PAD, h), px1 = Math.min(x1 + PAD, w);
      const pw = px1 - px0, ph = py1 - py0, plane = pw * ph, input = new Float32Array(3 * plane);
      for (let y = 0; y < ph; y++) for (let x = 0; x < pw; x++) {
        const src = ((py0 + y) * w + px0 + x) * 3, dst = y * pw + x;
        input[dst] = d[src]; input[plane + dst] = d[src + 1]; input[2 * plane + dst] = d[src + 2];
      }
      const res = await s.run({ input: new ort.Tensor("float32", input, [1, 3, ph, pw]) });
      const t = res[s.outputNames[0]], data = t.data as Float32Array, OW = pw * S, OH = ph * S, oplane = OW * OH;
      const cy0 = (ty - py0) * S, cx0 = (tx - px0) * S, rows = (y1 - ty) * S, cols = (x1 - tx) * S;
      for (let y = 0; y < rows; y++) {
        let o = (((ty * S) + y) * (w * S) + tx * S) * 4;
        const rowBase = (cy0 + y) * OW + cx0;
        for (let x = 0; x < cols; x++, o += 4) {
          const k = rowBase + x;
          out[o] = data[k] * 255 + 0.5; out[o + 1] = data[oplane + k] * 255 + 0.5; out[o + 2] = data[2 * oplane + k] * 255 + 0.5;
        }
      }
      t.dispose?.();
      done++; report(done / (tilesX * tilesY));
    }
  }
  return out;
}

async function resizeRGBA(rgba: Uint8ClampedArray, w: number, h: number, tw: number, th: number): Promise<Uint8ClampedArray> {
  const bmp = await createImageBitmap(new ImageData(rgba as unknown as Uint8ClampedArray<ArrayBuffer>, w, h));
  const c = new OffscreenCanvas(tw, th), g = c.getContext("2d")!;
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(bmp, 0, 0, tw, th); bmp.close();
  return g.getImageData(0, 0, tw, th).data;
}

async function run(m: RunMsg): Promise<void> {
  const { id, w, h, o } = m, report = (p: number, stage: string) => post({ type: "progress", id, p, stage });
  const check = () => { if (cancelled.has(id)) throw new Error("__cancelled__"); };
  try {
    let img = fromRGBA(new Uint8ClampedArray(m.rgba), w, h);
    report(0.02, "Reduciendo ruido");
    img = denoise(img, o.denoise * (o.factor > 1 ? 0.6 : 1), (p) => report(0.02 + 0.06 * p, "Reduciendo ruido")); check();
    report(0.1, "Corrigiendo exposición y color");
    img = autoColor(img, o.color); img = shadowsHighlights(img, o.shadows, o.highlights); check();
    let out: Uint8ClampedArray, ow = w, oh = h, shp = o.sharpen;
    if (o.factor > 1) {
      report(0.15, "Superresolución con IA (la primera vez descarga el modelo)");
      out = await upscale4(img, id, (p) => report(0.15 + 0.75 * p, "Superresolución con IA")); ow = w * 4; oh = h * 4; check();
      if (ow !== o.tw || oh !== o.th) { report(0.92, "Ajustando tamaño final"); out = await resizeRGBA(out, ow, oh, o.tw, o.th); ow = o.tw; oh = o.th; }
      shp *= 0.5;
    } else out = toRGBA(img);
    report(0.97, "Afinando nitidez");
    sharpenRGBA(out, ow, oh, shp);
    const buf = out.buffer as ArrayBuffer;
    post({ type: "done", id, rgba: buf, w: ow, h: oh }, [buf]);
  } catch (e) {
    const msg = (e as Error).message;
    if (msg === "__cancelled__") post({ type: "cancelled", id });
    else post({ type: "error", id, message: /memory|alloc/i.test(msg) ? "Memoria insuficiente en el dispositivo. Prueba una foto más pequeña o un objetivo menor." : `No se pudo procesar la imagen (${msg.slice(0, 120)}).` });
  } finally { cancelled.delete(id); }
}

ctx.onmessage = (ev: MessageEvent<RunMsg | { type: "cancel"; id: string }>) => {
  const m = ev.data;
  if (m.type === "cancel") cancelled.add(m.id);
  else void run(m);
};
