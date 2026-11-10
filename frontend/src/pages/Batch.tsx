import { useRef, useState } from "react";
import Controls, { defaultSettings, toOptions, type Settings } from "../components/Controls";
import { api, fmtBytes, type ExportOptions, type SystemInfo } from "../services/api";

type Row = { file: File; state: "pendiente" | "analizando" | "procesando" | "listo" | "error" | "cancelado"; progress: number; msg?: string };

export default function Batch({ files, system, onBack }: { files: File[]; system: SystemInfo | null; onBack: () => void }) {
  const [rows, setRows] = useState<Row[]>(files.map((file) => ({ file, state: "pendiente", progress: 0 })));
  const [settings, setSettings] = useState<Settings>({ ...defaultSettings, scale: 2 });
  const [exp, setExp] = useState<ExportOptions>({ format: "jpeg", quality: 92, keep_metadata: false, keep_gps: false });
  const [running, setRunning] = useState(false);
  const stop = useRef(false);
  const currentJob = useRef<string | null>(null);
  const srAvailable = system?.features.upscale ?? false;
  const faceAvailable = system?.features.face_restoration ?? false;

  const patch = (i: number, p: Partial<Row>) => setRows((r) => r.map((x, k) => (k === i ? { ...x, ...p } : x)));

  const start = async () => {
    stop.current = false; setRunning(true);
    for (let i = 0; i < rows.length; i++) {
      if (rows[i].state === "listo") continue;
      if (stop.current) { patch(i, { state: "cancelado" }); continue; }
      try {
        patch(i, { state: "analizando", progress: 0 });
        const info = await api.upload(rows[i].file);
        const job = await api.createJob(toOptions(info.id, { ...settings, upscale: settings.upscale && srAvailable, faces: settings.faces && faceAvailable, excluded: [] }));
        currentJob.current = job.id; patch(i, { state: "procesando" });
        const done = await api.wait(job.id, (j) => patch(i, { progress: j.progress }));
        currentJob.current = null;
        if (done.status === "cancelled") { patch(i, { state: "cancelado" }); continue; }
        if (done.status === "error") { patch(i, { state: "error", msg: done.error ?? "Error" }); continue; }
        const r = await api.exportJob(job.id, exp);
        const a = document.createElement("a"); a.href = URL.createObjectURL(r.blob); a.download = r.name; a.click(); URL.revokeObjectURL(a.href);
        patch(i, { state: "listo", progress: 1, msg: `${r.width}×${r.height} · ${fmtBytes(r.bytes)}` });
        await api.deleteImage(info.id).catch(() => undefined); // libera temporales al terminar cada foto
      } catch (e) { patch(i, { state: "error", msg: (e as Error).message }); }
    }
    setRunning(false);
  };
  const cancel = async () => { stop.current = true; if (currentJob.current) await api.cancel(currentJob.current).catch(() => undefined); };

  const total = rows.length ? rows.reduce((a, r) => a + (r.state === "listo" ? 1 : r.state === "procesando" ? r.progress : 0), 0) / rows.length : 0;
  return (
    <div className="mx-auto grid max-w-5xl gap-4 p-4 lg:grid-cols-[1fr_340px]">
      <div className="space-y-3">
        <div className="flex items-center gap-3"><button className="btn-ghost" onClick={onBack} disabled={running}>← Inicio</button><h1 className="text-lg font-semibold">Procesamiento por lotes · {rows.length} fotos</h1></div>
        <progress className="h-2 w-full" value={total} max={1} aria-label="Progreso global" />
        <ul className="space-y-2">
          {rows.map((r, i) => (
            <li key={i} className="card p-3 text-sm">
              <div className="flex justify-between gap-3"><span className="truncate">{r.file.name}</span><span className="text-ink-300">{r.state}</span></div>
              {r.state === "procesando" && <progress className="mt-2 h-1.5 w-full" value={r.progress} max={1} />}
              {r.msg && <p className={`label mt-1 ${r.state === "error" ? "text-red-300" : ""}`}>{r.msg}</p>}
            </li>
          ))}
        </ul>
        <p className="label">Cada resultado se descarga al terminar (usa la carpeta de descargas del navegador). Los originales no se modifican y los temporales de cada foto se borran al exportarla.</p>
      </div>
      <aside className="card space-y-4 p-4">
        <Controls s={settings} set={setSettings} plan={null} planError={null} srAvailable={srAvailable} faceAvailable={faceAvailable} />
        <div className="grid grid-cols-3 gap-1 rounded-xl bg-ink-800 p-1" role="radiogroup" aria-label="Formato de salida">
          {(["jpeg", "png", "webp"] as const).map((f) => <button key={f} role="radio" aria-checked={exp.format === f} onClick={() => setExp({ ...exp, format: f })} className={`rounded-lg px-2 py-1.5 text-sm uppercase ${exp.format === f ? "bg-amber-glow font-semibold text-black" : "text-ink-300"}`}>{f}</button>)}
        </div>
        {running ? <button className="btn-ghost w-full py-3" onClick={cancel}>Cancelar de forma segura</button> : <button className="btn w-full" onClick={start}>Procesar lote</button>}
      </aside>
    </div>
  );
}
