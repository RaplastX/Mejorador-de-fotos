import { useEffect, useRef, useState } from "react";
import Compare from "../components/Compare";
import { api } from "../services/api";

interface Props { onFiles: (files: File[]) => void; onOpen: (id: string) => void; busy: boolean; error: string | null }
type Recent = Awaited<ReturnType<typeof api.list>>;

const DEMOS = [
  { id: "retrato", title: "Retrato de baja resolución", note: "256 px muy comprimida → 1024 px, con restauración facial al 60 %", before: "/samples/retrato_antes.jpg", after: "/samples/retrato_despues.jpg", la: "Ampliación estándar", lb: "Luma" },
  { id: "antigua", title: "Foto antigua", note: "Sin rayones, con color generado por IA y rostro restaurado", before: "/samples/antigua_antes.jpg", after: "/samples/antigua_despues.jpg", la: "Antes", lb: "Después" },
];

const FEATURES: { t: string; d: string; icon: string }[] = [
  { t: "Más resolución", d: "Amplía 2×, 4× o hasta 4K con IA y mosaicos sin costuras.", icon: "M4 14v6h6M20 10V4h-6M4 20 20 4" },
  { t: "Rostros", d: "Reconstruye ojos y piel con control de intensidad, rostro a rostro.", icon: "M12 3a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm-8 18c.6-4 4-6 8-6s7.4 2 8 6" },
  { t: "Foto antigua", d: "Quita rayones y polvo, y colorea fotos en blanco y negro.", icon: "M5 4h14v16H5zM9 9h6M9 13h6" },
  { t: "Borrar objetos", d: "Pinta lo que sobra y se rellena; lo demás no cambia.", icon: "m4 20 6-2L20 8l-4-4L6 14l-2 6Zm10-14 4 4" },
  { t: "Recortar y girar", d: "Proporciones, 90° y enderezado automático de bordes.", icon: "M7 3v14h14M3 7h14v14" },
  { t: "Luz y color", d: "Ruido, sombras, luces, nitidez y ojos rojos.", icon: "M12 3v2m0 14v2M3 12h2m14 0h2m-3.5-6.5-1.4 1.4M7 17l-1.5 1.5m0-13L7 7m10 10 1.5 1.5M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" },
];

export default function Home({ onFiles, onOpen, busy, error }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [recent, setRecent] = useState<Recent>([]);
  const [demo, setDemo] = useState(0);
  useEffect(() => { api.list().then(setRecent).catch(() => setRecent([])); }, []);
  const d = DEMOS[demo];

  return (
    <div className="glow relative">
      <div className="mx-auto flex max-w-5xl flex-col gap-14 px-4 pb-20 pt-8 sm:px-6 sm:pt-14">
        <section className="grid items-center gap-8 lg:grid-cols-[1fr_1.05fr]">
          <div className="fade-up space-y-5 text-center lg:text-left">
            <span className="chip mx-auto lg:mx-0"><span className="h-2 w-2 rounded-full bg-emerald-400" /> Sin cuentas · sin anuncios · sin suscripción</span>
            <h1 className="font-display text-[2.4rem] font-semibold leading-[1.05] sm:text-6xl">Devuelve la luz<br className="hidden sm:block" /> a tus fotos.</h1>
            <p className="mx-auto max-w-md text-base text-ink-300 sm:text-lg lg:mx-0">Nitidez, rostros, fotos antiguas y color con IA. Elige una foto y compara el antes y el después.</p>
            <div
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); const f = [...e.dataTransfer.files]; if (f.length) onFiles(f); }}
              className={`flex flex-col items-center gap-3 rounded-3xl border border-dashed p-4 transition lg:items-start ${over ? "border-amber-glow bg-ink-800" : "border-ink-600"}`}
            >
              <button className="btn btn-lg" disabled={busy} onClick={() => input.current?.click()}>{busy ? "Analizando…" : "Mejorar una foto"}</button>
              <p className="label text-center lg:text-left">Toca para elegir de tu galería o cámara. También puedes arrastrar fotos aquí. Varias a la vez abren el modo por lotes.</p>
              <input ref={input} type="file" multiple accept="image/jpeg,image/png,image/webp,image/tiff,image/heic,image/heif" className="hidden" aria-label="Elegir fotografías"
                onChange={(e) => { const f = [...(e.target.files ?? [])]; if (f.length) onFiles(f); e.target.value = ""; }} />
            </div>
            {api.mode === "navegador" && <p className="label rounded-xl border border-ink-700 bg-ink-900 px-3 py-2 text-left">Versión en el navegador: tus fotos no salen de este dispositivo y funciona sin conexión tras la primera carga. Incluye superresolución, ruido, color, luz, recorte y giro. Rostros, colorización y borrar objetos requieren la versión con servidor.</p>}
            {error && <p role="alert" className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-2 text-left text-sm text-red-200">{error}</p>}
          </div>

          <div className="fade-up space-y-3" style={{ animationDelay: ".1s" }}>
            <div className="grain relative h-[48vh] max-h-[470px] min-h-[300px] overflow-hidden rounded-[1.6rem] border border-ink-700 bg-ink-900 p-2 shadow-[0_30px_80px_-30px_rgba(0,0,0,.9)]">
              <Compare key={d.id} before={d.before} after={d.after} beforeLabel={d.la} afterLabel={d.lb} minimal />
            </div>
            <div className="flex items-center justify-between gap-3">
              <div className="scroll-x" role="tablist" aria-label="Ejemplos">
                {DEMOS.map((x, i) => <button key={x.id} role="tab" aria-selected={demo === i} className="chip-btn" onClick={() => setDemo(i)}>{x.title}</button>)}
              </div>
            </div>
            <p className="label">{d.note}. Ejemplo real procesado con esta app (imagen de dominio público degradada a propósito). Desliza para comparar.</p>
          </div>
        </section>

        <section aria-labelledby="feat" className="space-y-5">
          <h2 id="feat" className="font-display text-2xl font-semibold sm:text-3xl">Todo lo que necesitas, en un sitio</h2>
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <li key={f.t} className="card flex gap-3.5 p-4">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-amber-glow/10 text-amber-glow">
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d={f.icon} /></svg>
                </span>
                <div><h3 className="font-semibold">{f.t}</h3><p className="mt-0.5 text-sm text-ink-300">{f.d}</p></div>
              </li>
            ))}
          </ul>
          <p className="label">La IA reconstruye detalle plausible: no recupera lo que la foto original no contiene. Cada resultado indica cuándo es generativo.</p>
        </section>

        <section aria-labelledby="rec" className="space-y-3">
          <h2 id="rec" className="text-sm font-semibold text-ink-300">Trabajos recientes (esta sesión)</h2>
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
    </div>
  );
}
