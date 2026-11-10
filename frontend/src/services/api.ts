export interface Analysis {
  width: number; height: number; megapixels: number; resolution: string; blur: string; noise: string;
  compression: string; exposure: string; faces: number; recommendations: string[];
}
export interface ImageInfo {
  id: string; name: string; format: string; width: number; height: number; size: number; has_alpha: boolean;
  analysis: Analysis; faces: { x: number; y: number; w: number; h: number }[];
}
export interface Plan { factor: number; width: number; height: number; generative: boolean; warnings: string[] }
export interface JobOptions {
  image_id: string; intensity: "suave" | "equilibrada" | "intensa"; denoise?: number; color?: number; sharpen?: number;
  upscale: boolean; target: "original" | "1080p" | "2k" | "4k"; scale: number;
  quality?: "rapida" | "alta"; shadows?: number; highlights?: number; redeye?: boolean; scratches?: number; colorize?: boolean; colorize_strength?: number;
  faces?: boolean; face_strength?: number; skin?: boolean; skin_smooth?: number; skin_wrinkles?: number; keep_texture?: boolean; exclude_faces?: { x: number; y: number; w: number; h: number }[];
}
export interface Job {
  id: string; image_id: string; status: "queued" | "running" | "done" | "cancelled" | "error"; progress: number;
  stage: string; error: string | null; plan: Plan; seconds: number; result: { width: number; height: number } | null;
}
export interface ExportOptions { format: "jpeg" | "png" | "webp"; quality: number; keep_metadata: boolean; keep_gps: boolean }
export interface SystemInfo {
  app: string; version: string;
  hardware: { device: string; torch: string; threads: number; gpu_name: string | null; vram_gb: number | null };
  limits: { max_upload_mb: number; max_input_mp: number; max_output_mp: number; tile: number };
  models: { key: string; title: string; present: boolean; code_license: string; weights_license: string; source: string; purpose: string }[];
  privacy: { local_only: boolean; telemetry: boolean; host: string };
  features: Record<string, boolean>;
}

export class ApiError extends Error {}

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try { res = await fetch(url, init); } catch { throw new ApiError("No se pudo conectar con el motor local. ¿Está iniciado?"); }
  if (!res.ok) {
    let msg = "Error inesperado";
    try { msg = (await res.json()).message ?? msg; } catch { /* sin cuerpo JSON */ }
    throw new ApiError(msg);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}
const json = (method: string, body: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const remote = {
  mode: "servidor" as "servidor" | "navegador",
  system: () => call<SystemInfo>("/api/system"),
  list: () => call<{ id: string; name: string; width: number; height: number; size: number }[]>("/api/images"),
  upload(file: File) { const f = new FormData(); f.append("file", file); return call<ImageInfo>("/api/images", { method: "POST", body: f }); },
  plan: (o: JobOptions) => call<Plan>("/api/plan", json("POST", o)),
  createJob: (o: JobOptions) => call<Job>("/api/jobs", json("POST", o)),
  job: (id: string) => call<Job>(`/api/jobs/${id}`),
  cancel: (id: string) => call<Job>(`/api/jobs/${id}`, { method: "DELETE" }),
  transform: (id: string, body: { rotate?: number; angle?: number; crop?: { x: number; y: number; w: number; h: number } | null }) => call<ImageInfo>(`/api/images/${id}/transform`, json("POST", body)),
  inpaint(id: string, mask: Blob) { const f = new FormData(); f.append("mask", mask, "mask.png"); return call<ImageInfo>(`/api/images/${id}/inpaint`, { method: "POST", body: f }); },
  info: (id: string) => call<ImageInfo>(`/api/images/${id}`),
  deleteImage: (id: string) => call<void>(`/api/images/${id}`, { method: "DELETE" }),
  clearAll: () => call<void>("/api/data", { method: "DELETE" }),
  imageUrl: (id: string) => `/api/images/${id}/display`,
  jobUrl: (id: string) => `/api/jobs/${id}/display`,
  async exportJob(id: string, o: ExportOptions) {
    const res = await fetch(`/api/jobs/${id}/export`, json("POST", o));
    if (!res.ok) throw new ApiError((await res.json().catch(() => ({}))).message ?? "No se pudo exportar");
    const blob = await res.blob();
    const name = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? "foto_mejorada";
    return { blob, name, width: Number(res.headers.get("X-Output-Width")), height: Number(res.headers.get("X-Output-Height")), bytes: blob.size };
  },
  async wait(id: string, onTick: (j: Job) => void, signal?: AbortSignal): Promise<Job> {
    for (;;) {
      const j = await api.job(id); onTick(j);
      if (["done", "error", "cancelled"].includes(j.status)) return j;
      if (signal?.aborted) return j;
      await new Promise((r) => setTimeout(r, 350));
    }
  },
};

export type Api = typeof remote;
/** Objeto que usa toda la interfaz. Por defecto habla con el servidor; si no hay servidor, pasa al motor del navegador. */
export const api: Api = { ...remote };

/** Detecta si hay un servidor de mejora (API JSON). Si no, usa el motor que corre en el navegador. */
export async function detectBackend(): Promise<"servidor" | "navegador"> {
  try {
    const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 4000);
    const r = await fetch("/api/system", { signal: ctl.signal }); clearTimeout(t);
    if ((r.headers.get("content-type") ?? "").includes("application/json")) {
      const j = await r.json().catch(() => null) as { app?: string; error?: string; message?: string } | null;
      if (r.ok && j?.app) return "servidor"; // firma de mi API
      if (r.status === 401 && j?.error === "unauthorized" && /emparejad/.test(j.message ?? "")) return "servidor"; // servidor protegido
    }
  } catch { /* sin servidor */ }
  const { local } = await import("../engine/local");
  Object.assign(api, local);
  return "navegador";
}

export const fmtBytes = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
