import { useCallback, useEffect, useRef, useState } from "react";
import Compare from "../components/Compare";
import Controls, { defaultSettings, effective, toOptions, type Settings } from "../components/Controls";
import CropTool from "../components/CropTool";
import EraseTool from "../components/EraseTool";
import { api, fmtBytes, type ExportOptions, type ImageInfo, type Job, type Plan, type SystemInfo } from "../services/api";

interface Version { job: Job; settings: Settings }

const CHIP: Record<string, string> = { baja: "Resolución baja", media: "Resolución media", alta: "Resolución alta" };

const NO_FEATURES: Record<string, boolean> = {};
export type Tool = "mejorar" | "recortar" | "borrar";

interface EditorProps { info: ImageInfo; system: SystemInfo | null; initialTool: Tool; onBack: () => void; onReplace: (i: ImageInfo, tool: Tool) => void; onPrevImage?: (tool: Tool) => void }

export default function Editor({ info, system, initialTool, onBack, onReplace, onPrevImage }: EditorProps) {
  const [tool, setTool] = useState<Tool>(initialTool);
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [versions, setVersions] = useState<Version[]>([]);
  const [idx, setIdx] = useState(-1); // -1 = solo original
  const [plan, setPlan] = useState<Plan | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [running, setRunning] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exp, setExp] = useState<ExportOptions>({ format: "jpeg", quality: 92, keep_metadata: false, keep_gps: false });
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const features = system?.features ?? NO_FEATURES;
  const cur = idx >= 0 ? versions[idx] : null;

  useEffect(() => {
    const t = setTimeout(() => {
      api.plan(toOptions(info.id, effective(settings, features), info.faces))
        .then((p) => { setPlan(p); setPlanError(null); }).catch((e: Error) => { setPlan(null); setPlanError(e.message); });
    }, 150);
    return () => clearTimeout(t);
  }, [settings, info, features]);

  const run = useCallback(async () => {
    setError(null); setExportMsg(null);
    abort.current = new AbortController();
    try {
      const job = await api.createJob(toOptions(info.id, effective(settings, features), info.faces));
      setRunning(job);
      const done = await api.wait(job.id, setRunning, abort.current.signal);
      if (done.status === "done") {
        setVersions((v) => { const next = [...v.slice(0, idx + 1), { job: done, settings }]; setIdx(next.length - 1); return next; });
      } else if (done.status === "error") setError(done.error);
    } catch (e) { setError((e as Error).message); }
    finally { setRunning(null); }
  }, [info, settings, features, idx]);

  const cancel = async () => { if (running) { abort.current?.abort(); await api.cancel(running.id).catch(() => undefined); } };

  const save = async () => {
    if (!cur) return;
    setExportMsg("Exportando…");
    try {
      const r = await api.exportJob(cur.job.id, exp);
      const a = document.createElement("a"); a.href = URL.createObjectURL(r.blob); a.download = r.name; a.click(); URL.revokeObjectURL(a.href);
      setExportMsg(`Guardado ${r.name}: ${r.width}×${r.height} · ${exp.format.toUpperCase()} · ${fmtBytes(r.bytes)}`);
    } catch (e) { setExportMsg((e as Error).message); }
  };

  const saveAll = async () => {
    setExportMsg("Exportando versiones…");
    try {
      for (let i = 0; i < versions.length; i++) {
        const r = await api.exportJob(versions[i].job.id, exp);
        const a = document.createElement("a"); a.href = URL.createObjectURL(r.blob); a.download = r.name.replace(/(\.[a-z]+)$/i, `_v${i + 1}$1`); a.click(); URL.revokeObjectURL(a.href);
        await new Promise((ok) => setTimeout(ok, 350)); // el navegador puede pedir permiso para varias descargas
      }
      setExportMsg(`Se exportaron ${versions.length} versiones.`);
    } catch (e) { setExportMsg((e as Error).message); }
  };

  const an = info.analysis;
  return (
    <div className={`grid grid-cols-1 gap-4 p-3 pb-28 lg:h-full lg:p-4 lg:pb-4 ${tool === "mejorar" ? "lg:grid-cols-[1fr_360px]" : ""}`}>
      <div className="flex flex-col gap-3 lg:min-h-[55vh]">
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn-ghost" onClick={onBack} aria-label="Volver al inicio">← <span className="max-sm:hidden">Inicio</span></button>
          <span className="min-w-0 flex-1 truncate text-sm text-ink-300 sm:flex-none">{info.name} · {info.width}×{info.height} · {info.format} · {fmtBytes(info.size)}</span>
          <span className="hidden flex-1 sm:block" />
          {onPrevImage && <button className="btn-ghost" disabled={!!running} onClick={() => onPrevImage(tool)} title="Vuelve a la imagen anterior a un recorte, giro o borrado" aria-label="Imagen anterior">⟲ <span className="max-sm:hidden">Imagen anterior</span></button>}
          {tool === "mejorar" && (
            <>
              <button className="btn-ghost" disabled={idx < 0 || !!running} onClick={() => setIdx(idx - 1)} aria-label="Deshacer">↶ <span className="max-sm:hidden">Deshacer</span></button>
              <button className="btn-ghost" disabled={idx >= versions.length - 1 || !!running} onClick={() => setIdx(idx + 1)} aria-label="Rehacer">↷ <span className="max-sm:hidden">Rehacer</span></button>
            </>
          )}
        </div>
        <div className="scroll-x" role="tablist" aria-label="Herramientas">
          {([["mejorar", "Mejorar"], ["recortar", "Recortar y girar"], ["borrar", "Borrar objetos"]] as const).map(([k, t]) => (
            <button key={k} role="tab" aria-selected={tool === k} disabled={!!running} onClick={() => setTool(k)} className="chip-btn">{t}</button>
          ))}
        </div>
        {tool === "recortar" && <div className="min-h-0 flex-1"><CropTool info={info} onReplace={(n) => onReplace(n, tool)} /></div>}
        {tool === "borrar" && <div className="min-h-0 flex-1"><EraseTool info={info} enabled={!!features.inpainting} onReplace={(n) => onReplace(n, tool)} /></div>}
        {tool === "mejorar" && <div className="relative h-[56vh] min-h-[320px] lg:h-auto lg:flex-1">
          {cur ? <Compare before={api.imageUrl(info.id)} after={api.jobUrl(cur.job.id)} />
            : <div className="checker flex h-full items-center justify-center rounded-xl border border-ink-700"><img src={api.imageUrl(info.id)} alt="Fotografía original" className="max-h-full max-w-full object-contain" /></div>}
          {running && (
            <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-black/55 backdrop-blur-sm" role="status" aria-live="polite">
              <div className="card w-72 p-5 text-center">
                <p className="text-sm">{running.stage}</p>
                <progress className="mt-3 h-2 w-full" value={running.progress} max={1} aria-label="Progreso" />
                <p className="label mt-1">{Math.round(running.progress * 100)} %</p>
                <button className="btn-ghost mt-3" onClick={cancel}>Cancelar</button>
              </div>
            </div>
          )}
        </div>}
        {tool === "mejorar" && versions.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs" aria-label="Versiones">
            <span className="label">Versiones:</span>
            <button className={`rounded-full border px-2.5 py-1 ${idx < 0 ? "border-amber-glow bg-amber-glow font-semibold text-black" : "border-ink-700 bg-ink-800"}`} disabled={!!running} onClick={() => setIdx(-1)}>Original</button>
            {versions.map((v, i) => (
              <button key={v.job.id} className={`rounded-full border px-2.5 py-1 ${idx === i ? "border-amber-glow bg-amber-glow font-semibold text-black" : "border-ink-700 bg-ink-800"}`} disabled={!!running} onClick={() => setIdx(i)}>v{i + 1} · {v.job.result?.width}×{v.job.result?.height}</button>
            ))}
            <button className="btn-ghost text-xs" disabled={!!running} onClick={saveAll}>Guardar todas</button>
          </div>
        )}
        {tool === "mejorar" && cur && <p className="label">Resultado {cur.job.result?.width}×{cur.job.result?.height} px · procesado en {cur.job.seconds} s · vista en pantalla reducida a 2048 px; la exportación usa la resolución completa.{cur.job.plan.generative && " Escalado generativo: el detalle añadido es una reconstrucción aproximada."}</p>}
        {error && <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">{error}</p>}
      </div>

      {tool === "mejorar" && (
        <div className="action-bar fixed inset-x-0 bottom-0 lg:hidden">
          <button className="btn btn-lg" disabled={!!running || !!planError} onClick={run}>{running ? `Procesando… ${Math.round((running.progress || 0) * 100)} %` : cur ? "Aplicar de nuevo" : "Mejorar imagen"}</button>
        </div>
      )}
      {tool === "mejorar" && <aside className="card flex flex-col gap-4 p-4 lg:max-h-full lg:overflow-y-auto" aria-label="Panel de herramientas">
        <section aria-labelledby="diag" className="space-y-2">
          <h2 id="diag" className="text-sm font-semibold">Diagnóstico</h2>
          <div className="flex flex-wrap gap-1.5 text-xs">
            {[CHIP[an.resolution], `Desenfoque ${an.blur}`, `Ruido ${an.noise}`, `Compresión ${an.compression}`, `Exposición ${an.exposure}`, `${an.faces} rostro(s)`].map((c) => <span key={c} className="rounded-full bg-ink-800 px-2.5 py-1">{c}</span>)}
          </div>
          <details className="text-sm">
            <summary className="cursor-pointer py-1 text-amber-glow">Ver recomendaciones</summary>
            <ul className="label mt-1 list-disc space-y-1 pl-4">{an.recommendations.map((r) => <li key={r}>{r}</li>)}</ul>
          </details>
        </section>

        <Controls s={settings} set={setSettings} plan={plan} planError={planError} features={features} image={info} />
        <button className="btn btn-lg hidden lg:inline-flex" disabled={!!running || !!planError} onClick={run}>{running ? "Procesando…" : cur ? "Aplicar de nuevo" : "Mejorar imagen"}</button>

        <section className="space-y-3 border-t border-ink-700 pt-4" aria-labelledby="exp">
          <h2 id="exp" className="text-sm font-semibold">Exportar</h2>
          <div className="grid grid-cols-3 gap-1 rounded-xl bg-ink-800 p-1" role="radiogroup" aria-label="Formato de salida">
            {(["jpeg", "png", "webp"] as const).map((f) => (
              <button key={f} role="radio" aria-checked={exp.format === f} onClick={() => setExp({ ...exp, format: f })} className={`rounded-lg px-2 py-1.5 text-sm uppercase ${exp.format === f ? "bg-amber-glow font-semibold text-black" : "text-ink-300 hover:bg-ink-700"}`}>{f}</button>
            ))}
          </div>
          {exp.format !== "png" && (
            <label className="block"><span className="flex justify-between label"><span>Calidad</span><span>{exp.quality}</span></span>
              <input type="range" min={60} max={100} value={exp.quality} onChange={(e) => setExp({ ...exp, quality: +e.target.value })} aria-label="Calidad de exportación" /></label>
          )}
          {!features.local && (
            <>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="accent-amber-400" checked={exp.keep_metadata} onChange={(e) => setExp({ ...exp, keep_metadata: e.target.checked, keep_gps: e.target.checked && exp.keep_gps })} /> Conservar metadatos EXIF</label>
          <label className={`flex items-center gap-2 text-sm ${exp.keep_metadata ? "" : "opacity-50"}`}><input type="checkbox" className="accent-amber-400" disabled={!exp.keep_metadata} checked={exp.keep_gps} onChange={(e) => setExp({ ...exp, keep_gps: e.target.checked })} /> Conservar ubicación GPS</label>
            </>
          )}
          {features.local && <p className="label">Se exporta sin metadatos (EXIF/GPS) por privacidad.</p>}
          <button className="btn" disabled={!cur || !!running} onClick={save}>Guardar copia</button>
          {!cur && <p className="label">Mejora la imagen para poder exportarla. El original nunca se modifica.</p>}
          {exportMsg && <p className="label" aria-live="polite">{exportMsg}</p>}
        </section>
      </aside>}
    </div>
  );
}
