/** Motor que corre ENTERO en el navegador: mismas funciones que el cliente del servidor, sin enviar nada a ninguna parte. */
import type { Analysis as AnalysisT, ExportOptions, ImageInfo, Job, JobOptions, SystemInfo } from "../services/api";
import { analyzeGray } from "./imageops";
import { INTENSITY, planOutput } from "./plan";
import type { Out, RunMsg } from "./worker";

interface LImage { info: ImageInfo; rgba: Uint8ClampedArray; w: number; h: number; url: string }
interface LJob { job: Job; rgba?: Uint8ClampedArray; w?: number; h?: number; url?: string }

const images = new Map<string, LImage>();
const jobs = new Map<string, LJob>();
let worker: Worker | null = null;
let provider = "wasm", threads = 1;
const MAX_INPUT_BYTES = 60 * 1024 * 1024, MAX_INPUT_PX = 24_000_000;

const uid = () => crypto.randomUUID().replace(/-/g, "");
const fail = (m: string) => { throw new Error(m); };
const stem = (n: string) => (n.replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^[._-]+|[._-]+$/g, "").slice(0, 60) || "foto");

function canvasOf(w: number, h: number): HTMLCanvasElement { const c = document.createElement("canvas"); c.width = w; c.height = h; return c; }
const toBlob = (c: HTMLCanvasElement, type: string, q?: number) => new Promise<Blob>((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error("No se pudo codificar la imagen"))), type, q));

async function displayUrl(rgba: Uint8ClampedArray, w: number, h: number): Promise<string> {
  const src = canvasOf(w, h); src.getContext("2d")!.putImageData(new ImageData(rgba as Uint8ClampedArray<ArrayBuffer>, w, h), 0, 0);
  const s = Math.min(1, 2048 / Math.max(w, h)), c = canvasOf(Math.max(1, Math.round(w * s)), Math.max(1, Math.round(h * s))), g = c.getContext("2d")!;
  g.imageSmoothingQuality = "high"; g.drawImage(src, 0, 0, c.width, c.height);
  return URL.createObjectURL(await toBlob(c, "image/jpeg", 0.88));
}

function analyze(rgba: Uint8ClampedArray, w: number, h: number): AnalysisT {
  const s = Math.min(1, 768 / Math.max(w, h)), gw = Math.max(8, Math.round(w * s)), gh = Math.max(8, Math.round(h * s));
  const src = canvasOf(w, h); src.getContext("2d")!.putImageData(new ImageData(rgba as Uint8ClampedArray<ArrayBuffer>, w, h), 0, 0);
  const c = canvasOf(gw, gh), g = c.getContext("2d", { willReadFrequently: true })!; g.imageSmoothingQuality = "high"; g.drawImage(src, 0, 0, gw, gh);
  const d = g.getImageData(0, 0, gw, gh).data, gray = new Float32Array(gw * gh);
  for (let i = 0, j = 0; i < gray.length; i++, j += 4) gray[i] = 0.299 * d[j] + 0.587 * d[j + 1] + 0.114 * d[j + 2];
  return analyzeGray(gray, gw, gh, w, h);
}

async function register(rgba: Uint8ClampedArray, w: number, h: number, name: string, format: string, size: number): Promise<ImageInfo> {
  const id = uid(), info: ImageInfo = { id, name, format, width: w, height: h, size, has_alpha: false, analysis: analyze(rgba, w, h), faces: [] };
  images.set(id, { info, rgba, w, h, url: await displayUrl(rgba, w, h) });
  return info;
}

function getImage(id: string): LImage { return images.get(id) ?? fail("La imagen no existe o ya se eliminó."); }

function getWorker(): Worker {
  if (worker) return worker;
  worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
  worker.onmessage = async (ev: MessageEvent<Out>) => {
    const m = ev.data;
    if (m.type === "provider") { provider = m.provider; threads = m.threads; return; }
    const lj = jobs.get(m.id); if (!lj) return;
    const j = lj.job;
    if (m.type === "progress") { j.status = "running"; j.progress = m.p; j.stage = m.stage; }
    else if (m.type === "cancelled") { j.status = "cancelled"; j.stage = "Cancelado"; }
    else if (m.type === "error") { j.status = "error"; j.error = m.message; j.stage = "Error"; }
    else if (m.type === "done") {
      lj.rgba = new Uint8ClampedArray(m.rgba); lj.w = m.w; lj.h = m.h;
      try { lj.url = await displayUrl(lj.rgba, m.w, m.h); j.result = { width: m.w, height: m.h }; j.seconds = Math.round((performance.now() - (j as unknown as { _t0: number })._t0) / 10) / 100; j.status = "done"; j.progress = 1; j.stage = "Listo"; }
      catch { j.status = "error"; j.error = "No se pudo preparar el resultado."; }
    }
  };
  worker.onerror = () => { for (const l of jobs.values()) if (l.job.status === "running" || l.job.status === "queued") { l.job.status = "error"; l.job.error = "El motor del navegador falló. Recarga la página."; } };
  return worker;
}

export const local = {
  mode: "navegador" as "servidor" | "navegador",

  async system(): Promise<SystemInfo> {
    return {
      app: "Luma Enhance", version: "navegador",
      hardware: { device: provider === "webgpu" ? "webgpu" : "cpu", torch: `onnxruntime-web 1.23.2 (${provider})`, threads, gpu_name: null, vram_gb: null },
      limits: { max_upload_mb: MAX_INPUT_BYTES / 1048576, max_input_mp: MAX_INPUT_PX / 1e6, max_output_mp: 12, tile: 128 },
      models: [{ key: "realesr-general-x4v3", title: "Real-ESRGAN general x4 v3 (ONNX, en tu navegador)", present: true, code_license: "BSD-3-Clause", weights_license: "Release oficial del repo (BSD-3-Clause)", source: "https://github.com/xinntao/Real-ESRGAN", purpose: "Superresolución x4 y limpieza de artefactos" }],
      privacy: { local_only: true, telemetry: false, host: "este dispositivo" },
      features: { upscale: true, face_restoration: false, skin_retouch: false, inpainting: false, colorize: false, quality_high: false, red_eye: false, geometry: true, scratches: false, local: true },
    };
  },
  async list() { return [...images.values()].reverse().slice(0, 24).map((i) => ({ id: i.info.id, name: i.info.name, width: i.w, height: i.h, size: i.info.size })); },
  async info(id: string) { return getImage(id).info; },
  async upload(file: File): Promise<ImageInfo> {
    if (file.size > MAX_INPUT_BYTES) fail(`El archivo supera el límite de ${MAX_INPUT_BYTES / 1048576} MB.`);
    let bmp: ImageBitmap;
    try { bmp = await createImageBitmap(file, { imageOrientation: "from-image" }); }
    catch { return fail("Este navegador no puede leer ese archivo. Usa JPEG, PNG o WebP (los HEIC/TIFF solo se aceptan en la versión con servidor)."); }
    if (bmp.width * bmp.height > MAX_INPUT_PX) { bmp.close(); fail(`La imagen es demasiado grande (${bmp.width}×${bmp.height}). Máximo ${MAX_INPUT_PX / 1e6} megapíxeles.`); }
    const c = canvasOf(bmp.width, bmp.height), g = c.getContext("2d", { willReadFrequently: true })!;
    g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height); g.drawImage(bmp, 0, 0); bmp.close(); // las transparencias se aplanan sobre blanco
    const d = g.getImageData(0, 0, c.width, c.height);
    return register(d.data, c.width, c.height, stem(file.name), (file.type.split("/")[1] || "img").toUpperCase(), file.size);
  },
  async plan(o: JobOptions) { const i = getImage(o.image_id); try { return planOutput(i.w, i.h, o); } catch (e) { return fail((e as Error).message); } },
  async createJob(o: JobOptions): Promise<Job> {
    const img = getImage(o.image_id);
    let plan; try { plan = planOutput(img.w, img.h, o); } catch (e) { return fail((e as Error).message); }
    const [dn, col, shp] = INTENSITY[o.intensity] ?? INTENSITY.equilibrada;
    const job: Job = { id: uid(), image_id: o.image_id, status: "queued", progress: 0, stage: "En cola", error: null, plan, seconds: 0, result: null };
    (job as unknown as { _t0: number })._t0 = performance.now();
    jobs.set(job.id, { job });
    const copy = img.rgba.slice(); // el worker recibe su propia copia (se transfiere)
    const msg: RunMsg = { type: "run", id: job.id, rgba: copy.buffer, w: img.w, h: img.h, o: { denoise: o.denoise ?? dn, color: o.color ?? col, sharpen: o.sharpen ?? shp, shadows: o.shadows ?? 0, highlights: o.highlights ?? 0, factor: plan.factor, tw: plan.width, th: plan.height } };
    getWorker().postMessage(msg, [copy.buffer]);
    return { ...job };
  },
  async job(id: string): Promise<Job> { return { ...(jobs.get(id)?.job ?? fail("El trabajo no existe.")) }; },
  async cancel(id: string): Promise<Job> { const l = jobs.get(id) ?? fail("El trabajo no existe."); getWorker().postMessage({ type: "cancel", id }); return { ...l.job }; },
  async deleteImage(id: string) { const i = images.get(id); if (i) { URL.revokeObjectURL(i.url); images.delete(id); } for (const [k, l] of jobs) if (l.job.image_id === id) { if (l.url) URL.revokeObjectURL(l.url); jobs.delete(k); } },
  async clearAll() { for (const id of [...images.keys()]) await local.deleteImage(id); },
  imageUrl: (id: string) => images.get(id)?.url ?? "",
  jobUrl: (id: string) => jobs.get(id)?.url ?? "",

  async exportJob(id: string, o: ExportOptions) {
    const l = jobs.get(id); if (!l?.rgba || !l.w || !l.h) return fail("El resultado aún no está listo.");
    const c = canvasOf(l.w, l.h); c.getContext("2d")!.putImageData(new ImageData(l.rgba as Uint8ClampedArray<ArrayBuffer>, l.w, l.h), 0, 0);
    const blob = await toBlob(c, `image/${o.format}`, o.format === "png" ? undefined : o.quality / 100);
    const ext = o.format === "jpeg" ? "jpg" : o.format, base = stem(getImage(l.job.image_id).info.name);
    return { blob, name: `${base}_mejorada.${ext}`, width: l.w, height: l.h, bytes: blob.size };
  },

  async transform(id: string, body: { rotate?: number; angle?: number; crop?: { x: number; y: number; w: number; h: number } | null }): Promise<ImageInfo> {
    const src = getImage(id), rot = body.rotate ?? 0, ang = body.angle ?? 0;
    if (![0, 90, 180, 270].includes(rot)) fail("La rotación debe ser 0, 90, 180 o 270 grados.");
    if (ang < -45 || ang > 45) fail("El enderezado admite entre -45° y 45°.");
    let cur = canvasOf(src.w, src.h); cur.getContext("2d")!.putImageData(new ImageData(src.rgba as Uint8ClampedArray<ArrayBuffer>, src.w, src.h), 0, 0);
    if (rot) {
      const sw = rot === 180 ? src.w : src.h, sh = rot === 180 ? src.h : src.w, c = canvasOf(sw, sh), g = c.getContext("2d")!;
      g.translate(sw / 2, sh / 2); g.rotate((rot * Math.PI) / 180); g.drawImage(cur, -src.w / 2, -src.h / 2); cur = c;
    }
    if (Math.abs(ang) > 1e-3) {
      const w = cur.width, h = cur.height, a = Math.abs((ang * Math.PI) / 180), k = Math.min(1, Math.min(w / (w * Math.cos(a) + h * Math.sin(a)), h / (w * Math.sin(a) + h * Math.cos(a))));
      const c = canvasOf(Math.max(1, Math.floor(w * k)), Math.max(1, Math.floor(h * k))), g = c.getContext("2d")!;
      g.imageSmoothingQuality = "high"; g.translate(c.width / 2, c.height / 2); g.rotate((ang * Math.PI) / 180); g.drawImage(cur, -w / 2, -h / 2); cur = c;
    }
    const cr = body.crop;
    if (cr) {
      if (!(cr.x >= 0 && cr.y >= 0 && cr.w > 0 && cr.h > 0 && cr.x + cr.w <= 1.0001 && cr.y + cr.h <= 1.0001)) fail("El recorte queda fuera de la imagen.");
      const x0 = Math.round(cr.x * cur.width), y0 = Math.round(cr.y * cur.height), cw = Math.max(1, Math.round(cr.w * cur.width)), ch = Math.max(1, Math.round(cr.h * cur.height));
      const c = canvasOf(Math.min(cw, cur.width - x0), Math.min(ch, cur.height - y0)); c.getContext("2d")!.drawImage(cur, x0, y0, c.width, c.height, 0, 0, c.width, c.height); cur = c;
    }
    const d = cur.getContext("2d", { willReadFrequently: true })!.getImageData(0, 0, cur.width, cur.height);
    return register(d.data, cur.width, cur.height, src.info.name, "PNG", d.data.length);
  },
  async inpaint(): Promise<ImageInfo> { return fail("Borrar objetos solo está en la versión con servidor."); },
};
