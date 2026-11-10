import { useCallback, useEffect, useRef, useState } from "react";
import { api, type ImageInfo } from "../services/api";

type Stroke = { r: number; pts: [number, number][] };

/** Pincel para marcar lo que se quiere borrar. LaMa rellena SOLO la zona marcada; el resto de la foto no cambia. */
export default function EraseTool({ info, enabled, onReplace }: { info: ImageInfo; enabled: boolean; onReplace: (i: ImageInfo) => void }) {
  const img = useRef<HTMLImageElement>(null);
  const cv = useRef<HTMLCanvasElement>(null);
  const strokes = useRef<Stroke[]>([]);
  const cur = useRef<Stroke | null>(null);
  const [count, setCount] = useState(0);
  const [brush, setBrush] = useState(3); // % del ancho de la imagen
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const redraw = useCallback(() => {
    const c = cv.current; if (!c) return;
    const g = c.getContext("2d")!; g.clearRect(0, 0, c.width, c.height);
    g.lineCap = "round"; g.lineJoin = "round"; g.strokeStyle = "rgba(255,59,48,0.75)"; g.fillStyle = "rgba(255,59,48,0.75)";
    for (const s of strokes.current) {
      g.lineWidth = s.r * 2;
      g.beginPath(); g.moveTo(s.pts[0][0], s.pts[0][1]);
      if (s.pts.length === 1) { g.arc(s.pts[0][0], s.pts[0][1], s.r, 0, Math.PI * 2); g.fill(); } else { for (const p of s.pts) g.lineTo(p[0], p[1]); g.stroke(); }
    }
  }, []);

  useEffect(() => { strokes.current = []; setCount(0); redraw(); }, [info.id, redraw]);

  const pos = (e: React.PointerEvent): [number, number] => {
    const c = cv.current!, r = c.getBoundingClientRect();
    return [((e.clientX - r.left) / r.width) * c.width, ((e.clientY - r.top) / r.height) * c.height];
  };
  const down = (e: React.PointerEvent) => {
    if (!enabled || busy) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    cur.current = { r: (brush / 100) * cv.current!.width / 2, pts: [pos(e)] };
    strokes.current.push(cur.current); redraw();
  };
  const move = (e: React.PointerEvent) => { if (cur.current) { cur.current.pts.push(pos(e)); redraw(); } };
  const up = () => { cur.current = null; setCount(strokes.current.length); };

  const apply = async () => {
    const c = cv.current!; setBusy(true); setErr(null);
    try {
      const out = document.createElement("canvas"); out.width = c.width; out.height = c.height;
      const src = c.getContext("2d")!.getImageData(0, 0, c.width, c.height), dst = out.getContext("2d")!.createImageData(c.width, c.height);
      for (let i = 0; i < src.data.length; i += 4) { const v = src.data[i + 3] > 20 ? 255 : 0; dst.data[i] = dst.data[i + 1] = dst.data[i + 2] = v; dst.data[i + 3] = 255; }
      out.getContext("2d")!.putImageData(dst, 0, 0);
      const blob: Blob = await new Promise((res, rej) => out.toBlob((b) => (b ? res(b) : rej(new Error("No se pudo crear la máscara"))), "image/png"));
      onReplace(await api.inpaint(info.id, blob));
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="flex h-full flex-col gap-3 lg:flex-row">
      <div className="checker flex min-h-[40vh] flex-1 items-center justify-center overflow-hidden rounded-xl border border-ink-700 p-2 lg:min-h-0">
        <div className="relative inline-block touch-none select-none" style={{ cursor: enabled ? "crosshair" : "not-allowed" }}>
          <img ref={img} src={api.imageUrl(info.id)} alt="Imagen donde marcar el objeto a borrar" draggable={false} className="block max-h-[58vh] max-w-full lg:max-h-[72vh]"
            onLoad={(e) => { const i = e.currentTarget; if (cv.current) { cv.current.width = i.naturalWidth; cv.current.height = i.naturalHeight; redraw(); } }} />
          <canvas ref={cv} className="absolute inset-0 h-full w-full" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} aria-label="Lienzo para marcar con el pincel" />
          {busy && <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-sm" role="status">Borrando… puede tardar unos segundos</div>}
        </div>
      </div>
      <div className="card w-full space-y-4 p-4 lg:w-72">
        <h3 className="text-sm font-semibold">Borrar objetos</h3>
        {!enabled ? <p className="label">Modelo no instalado: ejecuta <code>scripts/descargar_modelos.sh</code>.</p> : <p className="label">Pinta de rojo sobre lo que quieres quitar (un poco más allá de sus bordes). El área marcada se reconstruye con contenido plausible; el resto no cambia.</p>}
        <label className="block"><span className="flex justify-between label"><span>Tamaño del pincel</span><span>{brush}%</span></span><input type="range" min={1} max={12} value={brush} onChange={(e) => setBrush(+e.target.value)} aria-label="Tamaño del pincel" /></label>
        <div className="grid grid-cols-2 gap-2">
          <button className="btn-ghost" disabled={!count || busy} onClick={() => { strokes.current.pop(); setCount(strokes.current.length); redraw(); }}>↶ Deshacer trazo</button>
          <button className="btn-ghost" disabled={!count || busy} onClick={() => { strokes.current = []; setCount(0); redraw(); }}>Limpiar</button>
        </div>
        <button className="btn w-full" disabled={!enabled || !count || busy} onClick={apply}>{busy ? "Borrando…" : "Borrar lo marcado"}</button>
        <p className="label">El resultado es una imagen nueva. Con «Imagen anterior» vuelves a la de antes. La reconstrucción es una suposición: en zonas grandes o con patrones puede notarse.</p>
        {err && <p role="alert" className="rounded-lg border border-red-500/40 bg-red-500/10 p-2 text-sm text-red-200">{err}</p>}
      </div>
    </div>
  );
}
