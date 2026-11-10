import { useCallback, useRef, useState } from "react";

interface Props { before: string; after: string; beforeLabel?: string; afterLabel?: string; minimal?: boolean }

/** Comparador antes/después con divisor deslizante, zoom (rueda / botones) y desplazamiento (arrastrar con zoom). */
export default function Compare({ before, after, beforeLabel = "Original", afterLabel = "Mejorada", minimal = false }: Props) {
  const [split, setSplit] = useState(50);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const box = useRef<HTMLDivElement>(null);
  const drag = useRef<{ kind: "split" | "pan"; x: number; y: number; px: number; py: number } | null>(null);

  const setSplitFrom = useCallback((clientX: number) => {
    const r = box.current!.getBoundingClientRect();
    setSplit(Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100)));
  }, []);

  const clampZoom = (z: number) => Math.min(8, Math.max(1, z));
  const changeZoom = (z: number) => { const nz = clampZoom(z); setZoom(nz); if (nz === 1) setPan({ x: 0, y: 0 }); };

  const tf = { transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: "center" } as const;

  return (
    <div className="relative flex h-full w-full flex-col">
      <div
        ref={box}
        className={`${minimal ? "bg-ink-900" : "checker"} relative flex-1 select-none overflow-hidden rounded-2xl border border-ink-700 touch-none`}
        onWheel={(e) => changeZoom(zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15))}
        onPointerDown={(e) => {
          (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
          drag.current = zoom > 1 ? { kind: "pan", x: e.clientX, y: e.clientY, px: pan.x, py: pan.y } : { kind: "split", x: 0, y: 0, px: 0, py: 0 };
          if (zoom <= 1) setSplitFrom(e.clientX);
        }}
        onPointerMove={(e) => {
          const d = drag.current; if (!d) return;
          if (d.kind === "split") setSplitFrom(e.clientX);
          else setPan({ x: d.px + e.clientX - d.x, y: d.py + e.clientY - d.y });
        }}
        onPointerUp={() => (drag.current = null)}
      >
        <img src={after} alt={afterLabel} draggable={false} className="absolute inset-0 h-full w-full object-contain" style={tf} />
        <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}>
          <img src={before} alt={beforeLabel} draggable={false} className="absolute inset-0 h-full w-full object-contain" style={tf} />
        </div>
        <span className="pointer-events-none absolute left-3 top-3 rounded-full bg-black/60 px-3 py-1 text-xs">{beforeLabel}</span>
        <span className="pointer-events-none absolute right-3 top-3 rounded-full bg-black/60 px-3 py-1 text-xs">{afterLabel}</span>
        <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white/90 shadow" style={{ left: `${split}%` }}>
          <div className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white p-2 text-xs text-black shadow-lg">⟷</div>
        </div>
      </div>
      {!minimal && <div className="mt-2 flex items-center gap-3 text-sm text-ink-300">
        <label className="flex flex-1 items-center gap-2">
          <span className="whitespace-nowrap">Divisor</span>
          <input type="range" min={0} max={100} value={Math.round(split)} onChange={(e) => setSplit(+e.target.value)} aria-label="Posición del divisor antes/después" />
        </label>
        <div className="flex items-center gap-1" role="group" aria-label="Zoom">
          <button className="btn-ghost" onClick={() => changeZoom(zoom / 1.5)} aria-label="Alejar">−</button>
          <button className="btn-ghost w-16" onClick={() => changeZoom(1)} aria-label="Restablecer zoom">{Math.round(zoom * 100)}%</button>
          <button className="btn-ghost" onClick={() => changeZoom(zoom * 1.5)} aria-label="Acercar">+</button>
        </div>
      </div>}
    </div>
  );
}
