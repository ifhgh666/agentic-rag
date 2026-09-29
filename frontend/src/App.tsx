import { useEffect, useState } from "react";
import { logout } from "./api/client";
import { clearToken, isAuthenticated } from "./auth/session";
import { AppLayout } from "./components/AppLayout";
import { Login } from "./pages/Login";
import { Chat } from "./pages/Chat";
import { Knowledge } from "./pages/Knowledge";
import { Logs } from "./pages/Logs";

function currentPath() { return window.location.hash.replace("#", "") || "/chat"; }

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());
  const [path, setPath] = useState(currentPath());
  useEffect(() => { const onHash = () => setPath(currentPath()); window.addEventListener("hashchange", onHash); return () => window.removeEventListener("hashchange", onHash); }, []);
  function navigate(next: string) { window.location.hash = next; setPath(next); }
  async function onLogout() { try { await logout(); } catch { /* 令牌仍会在客户端清除 */ } finally { clearToken(); setAuthenticated(false); navigate("/chat"); } }
  if (!authenticated) return <Login onSuccess={() => { setAuthenticated(true); navigate("/chat"); }} />;
  return <AppLayout path={path} onNavigate={navigate} onLogout={() => void onLogout()}>{path === "/knowledge" ? <Knowledge /> : path === "/logs" ? <Logs /> : <Chat />}</AppLayout>;
}
