import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";

interface Props { onFiles: (files: File[]) => void; onOpen: (id: string) => void; busy: boolean; error: string | null }
type Recent = Awaited<ReturnType<typeof api.list>>;

export default function Home({ onFiles, onOpen, busy, error }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [recent, setRecent] = useState<Recent>([]);
  useEffect(() => { api.list().then(setRecent).catch(() => setRecent([])); }, []);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 px-5 py-12">
      <div className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight">Mejora tus fotos, sin salir de tu equipo</h1>
        <p className="mt-3 text-ink-300">Nitidez, menos ruido, mejor color y más resolución con IA. Todo se procesa en este ordenador.</p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); const f = [...e.dataTransfer.files]; if (f.length) onFiles(f); }}
        className={`card flex flex-col items-center gap-4 border-dashed p-12 text-center transition ${over ? "border-amber-glow bg-ink-800" : ""}`}
      >
        <button className="btn px-8 py-4 text-lg" disabled={busy} onClick={() => input.current?.click()}>{busy ? "Analizando…" : "Mejorar fotografía"}</button>
        <p className="label">o arrastra aquí una o varias imágenes · JPEG, PNG, WebP, TIFF o HEIC · varias a la vez usan el modo por lotes</p>
        <input ref={input} type="file" multiple accept="image/jpeg,image/png,image/webp,image/tiff,image/heic,image/heif" className="hidden" aria-label="Elegir fotografías"
          onChange={(e) => { const f = [...(e.target.files ?? [])]; if (f.length) onFiles(f); e.target.value = ""; }} />
        {error && <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-200">{error}</p>}
      </div>

      <div className="flex items-center justify-center gap-2 text-sm text-ink-300"><span className="h-2 w-2 rounded-full bg-emerald-400" /> Procesamiento 100 % local · sin cuentas · sin telemetría</div>

      <section aria-labelledby="rec">
        <h2 id="rec" className="mb-3 text-sm font-semibold text-ink-300">Trabajos recientes (esta sesión)</h2>
        {recent.length === 0 ? <p className="label">Aún no hay fotos. Las que importes aparecerán aquí hasta que cierres la aplicación o borres los datos.</p> : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {recent.map((r) => (
              <li key={r.id}><button className="card block w-full overflow-hidden text-left hover:border-amber-glow" onClick={() => onOpen(r.id)}>
                <img src={api.imageUrl(r.id)} alt="" className="aspect-square w-full object-cover" loading="lazy" />
                <span className="block truncate px-2 py-1.5 text-xs">{r.name} · {r.width}×{r.height}</span>
              </button></li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
