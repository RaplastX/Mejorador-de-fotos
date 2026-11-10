import { api, type JobOptions, type Plan } from "../services/api";

export interface FaceBox { x: number; y: number; w: number; h: number }
export interface ImageRef { id: string; width: number; height: number; faces: FaceBox[] }

export interface Settings {
  intensity: JobOptions["intensity"]; target: JobOptions["target"]; scale: number; upscale: boolean;
  denoise: number | null; color: number | null; sharpen: number | null;
  skin: boolean; skinSmooth: number; skinWrinkles: number; keepTexture: boolean;
  faces: boolean; faceStrength: number; excluded: number[]; // índices de rostros que NO se mejoran
}
export const defaultSettings: Settings = { intensity: "equilibrada", target: "original", scale: 2, upscale: true, denoise: null, color: null, sharpen: null, faces: false, faceStrength: 0.7, excluded: [], skin: false, skinSmooth: 0.35, skinWrinkles: 0.35, keepTexture: true };
const PRESET: Record<Settings["intensity"], [number, number, number]> = { suave: [0.25, 0.25, 0.25], equilibrada: [0.5, 0.4, 0.5], intensa: [0.8, 0.75, 0.8] };

export const toOptions = (id: string, s: Settings, faces: FaceBox[] = []): JobOptions => ({
  image_id: id, faces: s.faces, face_strength: s.faceStrength, skin: s.skin, skin_smooth: s.skinSmooth, skin_wrinkles: s.skinWrinkles, keep_texture: s.keepTexture, exclude_faces: s.excluded.map((i) => faces[i]).filter(Boolean), intensity: s.intensity, target: s.target, scale: s.scale, upscale: s.upscale,
  ...(s.denoise !== null && { denoise: s.denoise }), ...(s.color !== null && { color: s.color }), ...(s.sharpen !== null && { sharpen: s.sharpen }),
});

function Slider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="flex justify-between label"><span>{label}</span><span>{Math.round(value * 100)}%</span></span>
      <input type="range" min={0} max={100} value={Math.round(value * 100)} onChange={(e) => onChange(+e.target.value / 100)} aria-label={label} />
    </label>
  );
}

interface Props { s: Settings; set: (s: Settings) => void; plan: Plan | null; planError: string | null; srAvailable: boolean; faceAvailable: boolean; image?: ImageRef }

export default function Controls({ s, set, plan, planError, srAvailable, faceAvailable, image }: Props) {
  const p = PRESET[s.intensity];
  const v = (k: "denoise" | "color" | "sharpen", i: number) => s[k] ?? p[i];
  return (
    <div className="space-y-5">
      <section aria-labelledby="int">
        <h3 id="int" className="mb-2 text-sm font-semibold">Intensidad</h3>
        <div className="grid grid-cols-3 gap-1 rounded-xl bg-ink-800 p-1" role="radiogroup" aria-label="Intensidad de la mejora">
          {(["suave", "equilibrada", "intensa"] as const).map((k) => (
            <button key={k} role="radio" aria-checked={s.intensity === k} onClick={() => set({ ...s, intensity: k, denoise: null, color: null, sharpen: null })}
              className={`rounded-lg px-2 py-1.5 text-sm capitalize ${s.intensity === k ? "bg-amber-glow font-semibold text-black" : "text-ink-300 hover:bg-ink-700"}`}>{k}</button>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">Ajustes finos</h3>
        <Slider label="Reducción de ruido" value={v("denoise", 0)} onChange={(x) => set({ ...s, denoise: x })} />
        <Slider label="Exposición y color" value={v("color", 1)} onChange={(x) => set({ ...s, color: x })} />
        <Slider label="Nitidez" value={v("sharpen", 2)} onChange={(x) => set({ ...s, sharpen: x })} />
      </section>

      <section className="space-y-3">
        <label className="flex items-center justify-between text-sm font-semibold">
          Superresolución con IA
          <input type="checkbox" className="h-5 w-5 accent-amber-400" checked={s.upscale && srAvailable} disabled={!srAvailable} onChange={(e) => set({ ...s, upscale: e.target.checked })} />
        </label>
        {!srAvailable && <p className="label">Modelo no instalado: ejecuta <code>scripts/descargar_modelos.sh</code>.</p>}
        {s.upscale && srAvailable && (
          <>
            <label className="block">
              <span className="label">Tamaño de salida</span>
              <select className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-800 p-2 text-sm" value={s.target} onChange={(e) => set({ ...s, target: e.target.value as Settings["target"] })}>
                <option value="original">Factor sobre el original</option>
                <option value="1080p">1080p (lado largo 1920 px)</option>
                <option value="2k">2K (lado largo 2560 px)</option>
                <option value="4k">4K (lado largo 3840 px)</option>
              </select>
            </label>
            {s.target === "original" && (
              <div className="grid grid-cols-3 gap-1 rounded-xl bg-ink-800 p-1" role="radiogroup" aria-label="Factor de escala">
                {[1, 2, 4].map((f) => (
                  <button key={f} role="radio" aria-checked={s.scale === f} onClick={() => set({ ...s, scale: f })}
                    className={`rounded-lg px-2 py-1.5 text-sm ${s.scale === f ? "bg-amber-glow font-semibold text-black" : "text-ink-300 hover:bg-ink-700"}`}>{f}×</button>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {planError ? <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">{planError}</p> : plan && (
        <div className="rounded-lg bg-ink-800 p-3 text-sm" aria-live="polite">
          <p>Resultado: <strong>{plan.width} × {plan.height}</strong> px{plan.factor > 1 && ` (${plan.factor.toFixed(2)}×)`}</p>
          {plan.warnings.map((w) => <p key={w} className="mt-1.5 text-xs text-amber-200/90">⚠ {w}</p>)}
        </div>
      )}

      <section className="space-y-3" aria-labelledby="faces">
        <label id="faces" className="flex items-center justify-between text-sm font-semibold">
          Restauración de rostros con IA
          <input type="checkbox" className="h-5 w-5 accent-amber-400" checked={s.faces && faceAvailable} disabled={!faceAvailable} onChange={(e) => set({ ...s, faces: e.target.checked })} />
        </label>
        {!faceAvailable && <p className="label">Modelos de rostros no instalados: ejecuta <code>scripts/descargar_modelos.sh</code> (~540 MB).</p>}
        {s.faces && faceAvailable && (
          <>
            <Slider label="Intensidad (bajo = conserva más tu rostro original)" value={s.faceStrength} onChange={(x) => set({ ...s, faceStrength: x })} />
            <p className="label">GFPGAN reconstruye ojos, boca y piel; con intensidad alta puede cambiar ligeramente la expresión. Recomendado 50–70 %.</p>
            {image && image.faces.length > 0 && (
              <div>
                <p className="label mb-1">Rostros detectados (desmarca para dejar uno sin tocar)</p>
                <div className="flex flex-wrap gap-2">
                  {image.faces.map((b, i) => {
                    const on = !s.excluded.includes(i); const k = 56 / b.w;
                    return (
                      <button key={i} role="checkbox" aria-checked={on} aria-label={`Rostro ${i + 1}`} onClick={() => set({ ...s, excluded: on ? [...s.excluded, i] : s.excluded.filter((x) => x !== i) })}
                        className={`relative h-14 w-14 overflow-hidden rounded-lg border-2 ${on ? "border-amber-glow" : "border-ink-600 opacity-40"}`}
                        style={{ backgroundImage: `url(${api.imageUrl(image.id)})`, backgroundSize: `${image.width * k}px ${image.height * k}px`, backgroundPosition: `${-b.x * k}px ${-b.y * k}px` }}>
                        <span className="absolute bottom-0 right-0 rounded-tl bg-black/70 px-1 text-[10px]">{on ? "✓" : "✕"}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <section className="space-y-3" aria-labelledby="skin">
        <label id="skin" className="flex items-center justify-between text-sm font-semibold">
          Retoque natural de piel
          <input type="checkbox" className="h-5 w-5 accent-amber-400" checked={s.skin} onChange={(e) => set({ ...s, skin: e.target.checked })} />
        </label>
        {s.skin && (
          <>
            <Slider label="Suavizar imperfecciones" value={s.skinSmooth} onChange={(x) => set({ ...s, skinSmooth: x })} />
            <Slider label="Reducir arrugas finas" value={s.skinWrinkles} onChange={(x) => set({ ...s, skinWrinkles: x })} />
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="accent-amber-400" checked={s.keepTexture} onChange={(e) => set({ ...s, keepTexture: e.target.checked })} /> Conservar textura natural</label>
            <p className="label">Edición clásica (no generativa): no cambia el tono ni los rasgos. Solo actúa sobre rostros frontales detectados.</p>
          </>
        )}
      </section>
    </div>
  );
}
