import { useState } from "react";
import { api, type JobOptions, type Plan } from "../services/api";

export interface FaceBox { x: number; y: number; w: number; h: number }
export interface ImageRef { id: string; width: number; height: number; faces: FaceBox[] }

export interface Settings {
  intensity: JobOptions["intensity"]; target: JobOptions["target"]; scale: number; upscale: boolean; quality: "rapida" | "alta";
  denoise: number | null; color: number | null; sharpen: number | null; shadows: number; highlights: number; redeye: boolean;
  scratches: boolean; scratchStrength: number; colorize: boolean; colorizeStrength: number;
  skin: boolean; skinSmooth: number; skinWrinkles: number; keepTexture: boolean;
  faces: boolean; faceStrength: number; excluded: number[]; // índices de rostros que NO se mejoran
}
export const defaultSettings: Settings = {
  intensity: "equilibrada", target: "original", scale: 2, upscale: true, quality: "rapida", denoise: null, color: null, sharpen: null,
  shadows: 0, highlights: 0, redeye: false, scratches: false, scratchStrength: 0.5, colorize: false, colorizeStrength: 1,
  faces: false, faceStrength: 0.7, excluded: [], skin: false, skinSmooth: 0.35, skinWrinkles: 0.35, keepTexture: true,
};
const PRESET: Record<Settings["intensity"], [number, number, number]> = { suave: [0.25, 0.25, 0.25], equilibrada: [0.5, 0.4, 0.5], intensa: [0.8, 0.75, 0.8] };

export const toOptions = (id: string, s: Settings, faces: FaceBox[] = []): JobOptions => ({
  image_id: id, intensity: s.intensity, target: s.target, scale: s.scale, upscale: s.upscale, quality: s.quality,
  shadows: s.shadows, highlights: s.highlights, redeye: s.redeye, scratches: s.scratches ? s.scratchStrength : 0,
  colorize: s.colorize, colorize_strength: s.colorizeStrength,
  faces: s.faces, face_strength: s.faceStrength, skin: s.skin, skin_smooth: s.skinSmooth, skin_wrinkles: s.skinWrinkles, keep_texture: s.keepTexture,
  exclude_faces: s.excluded.map((i) => faces[i]).filter(Boolean),
  ...(s.denoise !== null && { denoise: s.denoise }), ...(s.color !== null && { color: s.color }), ...(s.sharpen !== null && { sharpen: s.sharpen }),
});

/** Aplica las funciones que existen en este equipo: lo que no está instalado se apaga en vez de fallar. */
export const effective = (s: Settings, f: Record<string, boolean>): Settings => ({
  ...s, upscale: s.upscale && !!f.upscale, faces: s.faces && !!f.face_restoration, colorize: s.colorize && !!f.colorize,
  quality: s.quality === "alta" && f.quality_high ? "alta" : "rapida",
});

const BUILTIN: { name: string; hint: string; s: Partial<Settings> }[] = [
  { name: "Retrato natural", hint: "2×, rostro 50 %, piel suave", s: { upscale: true, target: "original", scale: 2, faces: true, faceStrength: 0.5, skin: true, skinSmooth: 0.3, skinWrinkles: 0.3, intensity: "suave" } },
  { name: "Foto antigua", hint: "rayones + 2× + rostro 50 %", s: { scratches: true, scratchStrength: 0.5, upscale: true, scale: 2, faces: true, faceStrength: 0.5, intensity: "equilibrada" } },
  { name: "Antigua en color", hint: "como la anterior + colorización", s: { scratches: true, scratchStrength: 0.5, colorize: true, upscale: true, scale: 2, faces: true, faceStrength: 0.5 } },
  { name: "Nocturna", hint: "ruido, sombras y color", s: { intensity: "intensa", shadows: 0.5, highlights: 0.2, upscale: false } },
  { name: "Máxima resolución 4K", hint: "superresolución a 4K", s: { upscale: true, target: "4k" } },
];
const KEY = "luma.presets";
type UserPreset = { name: string; s: Settings };
const loadPresets = (): UserPreset[] => { try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; } };
const savePresets = (p: UserPreset[]) => { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* sin almacenamiento: no se guarda */ } };

function Slider({ label, value, onChange, min = 0, max = 100, show }: { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; show?: (v: number) => string }) {
  return (
    <label className="block">
      <span className="flex justify-between label"><span>{label}</span><span>{show ? show(value) : `${Math.round(value * 100)}%`}</span></span>
      <input type="range" min={min} max={max} value={Math.round(value * 100)} onChange={(e) => onChange(+e.target.value / 100)} aria-label={label} />
    </label>
  );
}
function Seg<T extends string | number>({ value, options, onChange, label }: { value: T; options: { v: T; t: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="grid gap-1 rounded-xl bg-ink-800 p-1" style={{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }} role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button key={String(o.v)} role="radio" aria-checked={value === o.v} onClick={() => onChange(o.v)}
          className={`rounded-lg px-2 py-1.5 text-sm ${value === o.v ? "bg-amber-glow font-semibold text-black" : "text-ink-300 hover:bg-ink-700"}`}>{o.t}</button>
      ))}
    </div>
  );
}
function Toggle({ id, label, checked, disabled, onChange }: { id: string; label: string; checked: boolean; disabled?: boolean; onChange: (v: boolean) => void }) {
  return (
    <label id={id} className={`flex items-center justify-between text-sm font-semibold ${disabled ? "opacity-60" : ""}`}>
      {label}
      <input type="checkbox" className="h-5 w-5 accent-amber-400" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}
const Missing = () => <p className="label">Modelo no instalado: ejecuta <code>scripts/descargar_modelos.sh</code>.</p>;

interface Props { s: Settings; set: (s: Settings) => void; plan: Plan | null; planError: string | null; features: Record<string, boolean>; image?: ImageRef }

export default function Controls({ s, set, plan, planError, features: f, image }: Props) {
  const p = PRESET[s.intensity];
  const v = (k: "denoise" | "color" | "sharpen", i: number) => s[k] ?? p[i];
  const [presets, setPresets] = useState<UserPreset[]>(loadPresets);
  const [name, setName] = useState("");
  const apply = (patch: Partial<Settings>) => set({ ...defaultSettings, ...patch, excluded: [] });
  const persist = (next: UserPreset[]) => { setPresets(next); savePresets(next); };

  return (
    <div className="space-y-5">
      <section aria-labelledby="pre" className="space-y-2">
        <h3 id="pre" className="text-sm font-semibold">Presets</h3>
        <div className="flex flex-wrap gap-1.5">
          {BUILTIN.map((b) => <button key={b.name} className="btn-ghost text-xs" title={b.hint} onClick={() => apply(b.s)}>{b.name}</button>)}
          {presets.map((u) => (
            <span key={u.name} className="inline-flex overflow-hidden rounded-[.6rem] border border-amber-glow/50">
              <button className="bg-ink-800 px-2.5 py-1 text-xs hover:bg-ink-700" onClick={() => set({ ...u.s, excluded: [] })}>{u.name}</button>
              <button className="bg-ink-800 px-2 text-xs text-ink-300 hover:bg-ink-700" aria-label={`Borrar preset ${u.name}`} onClick={() => persist(presets.filter((x) => x.name !== u.name))}>✕</button>
            </span>
          ))}
        </div>
        <form className="flex gap-1.5" onSubmit={(e) => { e.preventDefault(); const n = name.trim().slice(0, 30); if (!n) return; persist([...presets.filter((x) => x.name !== n), { name: n, s: { ...s, excluded: [] } }]); setName(""); }}>
          <input className="min-w-0 flex-1 rounded-lg border border-ink-700 bg-ink-800 px-2 py-1 text-sm" placeholder="Guardar ajustes como…" value={name} maxLength={30} onChange={(e) => setName(e.target.value)} aria-label="Nombre del preset" />
          <button className="btn-ghost text-xs" type="submit" disabled={!name.trim()}>Guardar</button>
        </form>
        <p className="label">Los presets se guardan solo en este navegador.</p>
      </section>

      <section aria-labelledby="int">
        <h3 id="int" className="mb-2 text-sm font-semibold">Intensidad</h3>
        <Seg label="Intensidad de la mejora" value={s.intensity} options={[{ v: "suave", t: "Suave" }, { v: "equilibrada", t: "Equilibrada" }, { v: "intensa", t: "Intensa" }]}
          onChange={(k) => set({ ...s, intensity: k, denoise: null, color: null, sharpen: null })} />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">Ajustes finos</h3>
        <Slider label="Reducción de ruido" value={v("denoise", 0)} onChange={(x) => set({ ...s, denoise: x })} />
        <Slider label="Exposición y color" value={v("color", 1)} onChange={(x) => set({ ...s, color: x })} />
        <Slider label="Nitidez" value={v("sharpen", 2)} onChange={(x) => set({ ...s, sharpen: x })} />
        <Slider label="Sombras (levantar)" value={s.shadows} min={-100} max={100} onChange={(x) => set({ ...s, shadows: x })} show={(x) => `${x > 0 ? "+" : ""}${Math.round(x * 100)}`} />
        <Slider label="Luces (recuperar)" value={s.highlights} min={-100} max={100} onChange={(x) => set({ ...s, highlights: x })} show={(x) => `${x > 0 ? "+" : ""}${Math.round(x * 100)}`} />
      </section>

      <section className="space-y-3">
        <Toggle id="sr" label="Superresolución con IA" checked={s.upscale && !!f.upscale} disabled={!f.upscale} onChange={(x) => set({ ...s, upscale: x })} />
        {!f.upscale && <Missing />}
        {s.upscale && f.upscale && (
          <>
            <label className="block"><span className="label">Tamaño de salida</span>
              <select className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-800 p-2 text-sm" value={s.target} onChange={(e) => set({ ...s, target: e.target.value as Settings["target"] })}>
                <option value="original">Factor sobre el original</option><option value="1080p">1080p (lado largo 1920 px)</option><option value="2k">2K (lado largo 2560 px)</option><option value="4k">4K (lado largo 3840 px)</option>
              </select></label>
            {s.target === "original" && <Seg label="Factor de escala" value={s.scale} options={[{ v: 1, t: "1×" }, { v: 2, t: "2×" }, { v: 4, t: "4×" }]} onChange={(x) => set({ ...s, scale: x })} />}
            {f.quality_high && <Seg label="Modelo de superresolución" value={s.quality} options={[{ v: "rapida", t: "Rápida" }, { v: "alta", t: "Alta (lenta)" }]} onChange={(x) => set({ ...s, quality: x })} />}
          </>
        )}
      </section>

      {planError ? <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">{planError}</p> : plan && (
        <div className="rounded-lg bg-ink-800 p-3 text-sm" aria-live="polite">
          <p>Resultado: <strong>{plan.width} × {plan.height}</strong> px{plan.factor > 1 && ` (${plan.factor.toFixed(2)}×)`}</p>
          {plan.warnings.map((w) => <p key={w} className="mt-1.5 text-xs text-amber-200/90">⚠ {w}</p>)}
        </div>
      )}

      <section className="space-y-3 border-t border-ink-700 pt-4" aria-labelledby="old">
        <h3 id="old" className="text-sm font-semibold">Foto antigua</h3>
        <Toggle id="scr" label="Quitar rayones y polvo" checked={s.scratches} onChange={(x) => set({ ...s, scratches: x })} />
        {s.scratches && <><Slider label="Intensidad de limpieza" value={s.scratchStrength} onChange={(x) => set({ ...s, scratchStrength: x })} /><p className="label">Solo trazos finos y largos (verticales/horizontales) y puntos aislados. Los rayones diagonales o daños grandes no se detectan; revisa el resultado.</p></>}
        <Toggle id="col" label="Colorizar con IA" checked={s.colorize && !!f.colorize} disabled={!f.colorize} onChange={(x) => set({ ...s, colorize: x })} />
        {!f.colorize && <Missing />}
        {s.colorize && f.colorize && <><Slider label="Intensidad del color" value={s.colorizeStrength} onChange={(x) => set({ ...s, colorizeStrength: x })} /><p className="label">Generativo: los colores son una suposición plausible, no los reales. Pensado para fotos en blanco y negro.</p></>}
      </section>

      <section className="space-y-3" aria-labelledby="faces">
        <Toggle id="faces" label="Restauración de rostros con IA" checked={s.faces && !!f.face_restoration} disabled={!f.face_restoration} onChange={(x) => set({ ...s, faces: x })} />
        {!f.face_restoration && <Missing />}
        {s.faces && f.face_restoration && (
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
        <Toggle id="red" label="Corregir ojos rojos" checked={s.redeye} onChange={(x) => set({ ...s, redeye: x })} />
      </section>

      <section className="space-y-3" aria-labelledby="skin">
        <Toggle id="skin" label="Retoque natural de piel" checked={s.skin} onChange={(x) => set({ ...s, skin: x })} />
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
