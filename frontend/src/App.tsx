import { useEffect, useState } from "react";
import { APP_NAME } from "./brand";
import Batch from "./pages/Batch";
import Editor, { type Tool } from "./pages/Editor";
import Home from "./pages/Home";
import Settings from "./pages/Settings";
import { api, type ImageInfo, type SystemInfo } from "./services/api";

type View = { name: "home" } | { name: "editor"; info: ImageInfo; prev: ImageInfo[]; tool: Tool } | { name: "batch"; files: File[] } | { name: "settings" };

export default function App() {
  const [view, setView] = useState<View>({ name: "home" });
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.system().then(setSystem).catch((e: Error) => setError(e.message)); }, []);

  const home = () => { setError(null); setView({ name: "home" }); };
  const onFiles = async (files: File[]) => {
    setError(null);
    if (files.length > 1) return setView({ name: "batch", files });
    setBusy(true);
    try { setView({ name: "editor", info: await api.upload(files[0]), prev: [], tool: "mejorar" }); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const onOpen = async (id: string) => {
    setBusy(true);
    try { setView({ name: "editor", info: await api.info(id), prev: [], tool: "mejorar" }); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-ink-800 bg-ink-950/85 px-4 py-3 backdrop-blur sm:px-6">
        <button onClick={home} className="flex items-center gap-2.5 font-display text-lg font-semibold" aria-label={`${APP_NAME}: ir al inicio`}>
          <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden><circle cx="16" cy="16" r="13" fill="none" stroke="#f2b45a" strokeWidth="2.4" /><circle cx="16" cy="16" r="5.2" fill="#f2b45a" /><path d="M16 3v8M27.3 9.5 20.4 13.5M27.3 22.5l-6.9-4M16 29v-8M4.7 22.5l6.9-4M4.7 9.5l6.9 4" stroke="#f2b45a" strokeWidth="1.6" opacity=".55" /></svg>
          {APP_NAME}
        </button>
        <nav className="flex items-center gap-2 text-sm text-ink-300"><span className="chip max-sm:hidden" title="Las fotos solo se procesan en el motor de esta app">🔒 Privado</span><button className="btn-ghost" onClick={() => setView({ name: "settings" })}>Ajustes</button></nav>
      </header>
      <main className="min-h-0 flex-1 overflow-y-auto">
        {view.name === "home" && <Home onFiles={onFiles} onOpen={onOpen} busy={busy} error={error} />}
        {view.name === "editor" && (
          <Editor key={view.info.id} info={view.info} system={system} initialTool={view.tool} onBack={home}
            onReplace={(n, tool) => setView({ name: "editor", info: n, prev: [...view.prev, view.info], tool })}
            onPrevImage={view.prev.length ? (tool) => setView({ name: "editor", info: view.prev[view.prev.length - 1], prev: view.prev.slice(0, -1), tool }) : undefined} />
        )}
        {view.name === "batch" && <Batch files={view.files} system={system} onBack={home} />}
        {view.name === "settings" && <Settings system={system} onBack={home} />}
      </main>
    </div>
  );
}
