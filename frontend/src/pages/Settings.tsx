import { useState } from "react";
import { api, type SystemInfo } from "../services/api";

export default function Settings({ system, onBack }: { system: SystemInfo | null; onBack: () => void }) {
  const [msg, setMsg] = useState<string | null>(null);
  const clear = async () => {
    if (!window.confirm("Se borrarán todas las fotos temporales y resultados de esta sesión. Tus archivos originales fuera de la app no se tocan. ¿Continuar?")) return;
    await api.clearAll(); setMsg("Datos temporales eliminados.");
  };
  const hw = system?.hardware;
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center gap-3"><button className="btn-ghost" onClick={onBack}>← Inicio</button><h1 className="text-lg font-semibold">Ajustes e información</h1></div>
      <section className="card space-y-2 p-4"><h2 className="font-semibold">Equipo detectado</h2>
        {hw ? <p className="text-sm text-ink-300">Procesador de IA: <strong className="text-ink-100">{hw.device === "cuda" ? `GPU ${hw.gpu_name} (${hw.vram_gb} GB)` : "CPU"}</strong> · {hw.threads} hilos · PyTorch {hw.torch}. La aplicación funciona en CPU y usa GPU NVIDIA automáticamente si existe. Para forzar CPU: variable <code>LUMA_DEVICE=cpu</code>.</p> : <p className="label">Sin conexión con el motor.</p>}
        {system && <p className="label">Límites: subida {system.limits.max_upload_mb} MB · entrada {system.limits.max_input_mp} MP · salida {system.limits.max_output_mp} MP · mosaico {system.limits.tile}px (variables <code>LUMA_MAX_OUTPUT_PIXELS</code>, <code>LUMA_TILE</code>).</p>}</section>
      <section className="card space-y-2 p-4"><h2 className="font-semibold">Privacidad</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink-300"><li>Las fotos se procesan solo en este equipo; el servidor escucha únicamente en {system?.privacy.host ?? "127.0.0.1"}.</li><li>Sin telemetría, anuncios, cuentas ni reconocimiento de personas. Los rostros solo se detectan como cajas para el diagnóstico y no se guardan.</li><li>Los temporales viven en una carpeta privada y se eliminan al cerrar la aplicación.</li><li>Al exportar se elimina por defecto el EXIF y la ubicación GPS.</li></ul>
        <button className="btn-ghost" onClick={clear}>Borrar historial y temporales ahora</button>{msg && <p className="label" role="status">{msg}</p>}</section>
      <section className="card space-y-3 p-4"><h2 className="font-semibold">Modelos y licencias</h2>
        {system?.models.map((m) => <div key={m.key} className="text-sm"><p><strong>{m.title}</strong> · {m.present ? "instalado" : "NO instalado"}</p><p className="label">{m.purpose}. Código: {m.code_license}. Pesos: {m.weights_license}. Fuente: {m.source}</p></div>)}
        <p className="label">Funciones aún no disponibles: restauración facial con IA, retoque de piel, eliminación de objetos (inpainting). No se muestran como activas.</p></section>
    </div>
  );
}
