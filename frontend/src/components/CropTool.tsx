import { useState } from "react";
import { api, type ImageInfo } from "../services/api";

const RATIOS: { t: string; r: number | null }[] = [
  { t: "Original", r: null }, { t: "1:1", r: 1 }, { t: "4:5", r: 4 / 5 }, { t: "3:4", r: 3 / 4 }, { t: "4:3", r: 4 / 3 }, { t: "16:9", r: 16 / 9 }, { t: "9:16", r: 9 / 16 },
];

let lastMode: "rotar" | "recortar" = "recortar"; // sobrevive al remontaje del editor al cambiar de imagen

/** Rotar 90°, enderezar y recortar. Cada acción aplicada crea una imagen nueva; la anterior se conserva (botón «Imagen anterior»). */
export default function CropTool({ info, onReplace }: { info: ImageInfo; onReplace: (i: ImageInfo) => void }) {
  const [mode, setModeState] = useState<"rotar" | "recortar">(lastMode);
  const setMode = (m: "rotar" | "recortar") => { lastMode = m; setModeState(m); };
  const [angle, setAngle] = useState(0);
  const [ratio, setRatio] = useState<number | null>(1);
  const [zoom, setZoom] = useState(1);
  const [px, setPx] = useState(0.5);
  const [py, setPy] = useState(0.5);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const A = info.width / info.height;
  const R = ratio ?? A;
  let cw = R > A ? 1 : R / A, ch = R > A ? A / R : 1;
  cw /= zoom; ch /= zoom;
  const cx = (1 - cw) * px, cy = (1 - ch) * py;
  const outW = Math.round(cw * info.width), outH = Math.round(ch * info.height);

  const run = async (body: Parameters<typeof api.transform>[1]) => {
    setBusy(true); setErr(null);
    try { onReplace(await api.transform(info.id, body)); setAngle(0); setZoom(1); setPx(0.5); setPy(0.5); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="flex h-full flex-col gap-3 lg:flex-row">
      <div className="checker flex min-h-[40vh] flex-1 items-center justify-center overflow-hidden rounded-xl border border-ink-700 p-2 lg:min-h-0">
        <div className="relative inline-block overflow-hidden">
          <img src={api.imageUrl(info.id)} alt="Imagen a recortar" draggable={false} className="block max-h-[58vh] max-w-full select-none lg:max-h-[72vh]"
            style={mode === "rotar" ? { transform: `rotate(${angle}deg) scale(${1 + Math.abs(angle) / 45})` } : undefined} />
          {mode === "recortar" && (
            <div className="pointer-events-none absolute border-2 border-white" style={{ left: `${cx * 100}%`, top: `${cy * 100}%`, width: `${cw * 100}%`, height: `${ch * 100}%`, boxShadow: "0 0 0 9999px rgba(0,0,0,.6)" }} />
          )}
          {mode === "rotar" && angle !== 0 && <div className="pointer-events-none absolute inset-0 opacity-40" style={{ backgroundImage: "linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px)", backgroundSize: "12.5% 12.5%" }} />}
        </div>
      </div>

      <div className="card w-full space-y-4 p-4 lg:w-72">
        <div className="grid grid-cols-2 gap-1 rounded-xl bg-ink-800 p-1" role="tablist" aria-label="Modo">
          {(["recortar", "rotar"] as const).map((m) => <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)} className={`rounded-lg px-2 py-1.5 text-sm capitalize ${mode === m ? "bg-amber-glow font-semibold text-black" : "text-ink-300"}`}>{m === "rotar" ? "Rotar / enderezar" : "Recortar"}</button>)}
        </div>
        {mode === "rotar" ? (
          <>
            <div className="grid grid-cols-2 gap-2">
              <button className="btn-ghost" disabled={busy} onClick={() => run({ rotate: 270 })}>↺ 90° izq.</button>
              <button className="btn-ghost" disabled={busy} onClick={() => run({ rotate: 90 })}>↻ 90° der.</button>
            </div>
            <label className="block"><span className="flex justify-between label"><span>Enderezar</span><span>{angle.toFixed(1)}°</span></span>
              <input type="range" min={-150} max={150} value={Math.round(angle * 10)} onChange={(e) => setAngle(+e.target.value / 10)} aria-label="Ángulo de enderezado" /></label>
            <p className="label">La vista previa es aproximada. Al aplicar se recortan automáticamente los bordes vacíos, así que la imagen queda algo más pequeña.</p>
            <button className="btn w-full" disabled={busy || angle === 0} onClick={() => run({ angle })}>{busy ? "Aplicando…" : "Aplicar enderezado"}</button>
          </>
        ) : (
          <>
            <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Proporción">
              {RATIOS.map((o) => <button key={o.t} role="radio" aria-checked={ratio === o.r} onClick={() => { setRatio(o.r); setPx(0.5); setPy(0.5); }} className={`rounded-lg border px-2.5 py-1 text-xs ${ratio === o.r ? "border-amber-glow bg-amber-glow font-semibold text-black" : "border-ink-700 bg-ink-800"}`}>{o.t}</button>)}
            </div>
            <label className="block"><span className="flex justify-between label"><span>Zoom</span><span>{zoom.toFixed(1)}×</span></span><input type="range" min={10} max={40} value={Math.round(zoom * 10)} onChange={(e) => setZoom(+e.target.value / 10)} aria-label="Zoom del recorte" /></label>
            <label className="block"><span className="label">Posición horizontal</span><input type="range" min={0} max={100} value={Math.round(px * 100)} onChange={(e) => setPx(+e.target.value / 100)} aria-label="Posición horizontal" /></label>
            <label className="block"><span className="label">Posición vertical</span><input type="range" min={0} max={100} value={Math.round(py * 100)} onChange={(e) => setPy(+e.target.value / 100)} aria-label="Posición vertical" /></label>
            <p className="label">Tamaño resultante: <strong className="text-ink-100">{outW} × {outH}</strong> px</p>
            <button className="btn w-full" disabled={busy} onClick={() => run({ crop: { x: cx, y: cy, w: cw, h: ch } })}>{busy ? "Aplicando…" : "Aplicar recorte"}</button>
          </>
        )}
        {err && <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-2 text-sm text-red-200">{err}</p>}
      </div>
    </div>
  );
}
