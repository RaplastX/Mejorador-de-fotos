import type { JobOptions, Plan } from "../services/api";

export const INTENSITY: Record<string, [number, number, number]> = { suave: [0.25, 0.25, 0.25], equilibrada: [0.5, 0.4, 0.5], intensa: [0.8, 0.75, 0.8] };
const TARGET: Record<string, number> = { "1080p": 1920, "2k": 2560, "4k": 3840 };
export const MAX_OUT_PX = 12_000_000; // límite prudente para móviles (4K = 8,3 MP)

/** Equivalente de plan_output() del servidor: tamaño final y avisos ANTES de procesar. */
export function planOutput(width: number, height: number, o: JobOptions): Plan {
  const long = Math.max(width, height), warnings: string[] = [];
  let factor = 1;
  if (o.upscale) {
    if (o.target !== "original") {
      factor = TARGET[o.target] / long;
      if (factor < 1) { factor = 1; warnings.push("La imagen ya es más grande que el objetivo elegido; se mantiene el tamaño original."); }
    } else factor = o.scale;
  }
  if (factor > 4) warnings.push("El factor supera 4×: se aplica 4× con IA y el resto con interpolación; el detalle extra no es real.");
  const generative = factor > 1;
  if (generative && long < 600 && factor >= 3) warnings.push("La imagen original es muy pequeña: el resultado a gran resolución reconstruye detalles de forma aproximada.");
  if (generative && width * height > 1_000_000) warnings.push("En el navegador, ampliar una foto de más de 1 megapíxel puede tardar varios minutos si tu dispositivo no usa su GPU. Para fotos grandes usa la versión con servidor.");
  if (generative) warnings.push("El escalado con IA reconstruye detalle plausible; no recupera información que no existía en la foto original.");
  const W = Math.max(1, Math.round(width * factor)), H = Math.max(1, Math.round(height * factor));
  if (W * H > MAX_OUT_PX) throw new Error(`El resultado (${W}×${H}) supera el límite de ${MAX_OUT_PX / 1e6} MP de la versión en el navegador. Elige un objetivo menor o reduce la foto.`);
  if (generative && width * height > 4_000_000) throw new Error("Para ampliar con IA en el navegador, la foto original no debe superar 4 megapíxeles. Usa 1× o una foto más pequeña.");
  return { factor: Math.round(factor * 10000) / 10000, width: W, height: H, generative, warnings };
}
