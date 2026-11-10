import type { JobOptions, Plan } from "../services/api";

export interface Settings {
  intensity: JobOptions["intensity"]; target: JobOptions["target"]; scale: number; upscale: boolean;
  denoise: number | null; color: number | null; sharpen: number | null;
}
export const defaultSettings: Settings = { intensity: "equilibrada", target: "original", scale: 2, upscale: true, denoise: null, color: null, sharpen: null };
const PRESET: Record<Settings["intensity"], [number, number, number]> = { suave: [0.25, 0.35, 0.25], equilibrada: [0.5, 0.6, 0.5], intensa: [0.8, 0.85, 0.8] };

export const toOptions = (id: string, s: Settings): JobOptions => ({
  image_id: id, intensity: s.intensity, target: s.target, scale: s.scale, upscale: s.upscale,
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

interface Props { s: Settings; set: (s: Settings) => void; plan: Plan | null; planError: string | null; srAvailable: boolean }

export default function Controls({ s, set, plan, planError, srAvailable }: Props) {
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

      <section className="rounded-lg border border-dashed border-ink-600 p-3">
        <h3 className="text-sm font-semibold">Rostros y piel · no disponible aún</h3>
        <p className="label mt-1">La restauración facial con IA (GFPGAN/CodeFormer) y el retoque de piel están planificados para las fases 2–3 y todavía no existen en esta versión. La superresolución general sí actúa sobre los rostros sin alterar su forma.</p>
      </section>
    </div>
  );
}
