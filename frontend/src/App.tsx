import { useEffect, useState } from "react";
import { useStore } from "zustand";
import { logout } from "./api/client";
import { AUTH_CLEARED_EVENT, clearToken, isAuthenticated } from "./auth/session";
import { AppLayout } from "./components/AppLayout";
import { Login } from "./pages/Login";
import { Chat } from "./pages/Chat";
import { Knowledge } from "./pages/Knowledge";
import { chatStore } from "./stores/chat-store";
import { chatController } from "./features/chat/controller";

function currentPath() {
  const path=window.location.hash.replace(/^#/, "") || "/chat";
  if(path==="/logs") window.history.replaceState(null,"",`${window.location.pathname}${window.location.search}#/chat`);
  return path==="/knowledge" ? path : "/chat";
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [path, setPath] = useState(currentPath);
  const running = useStore(chatStore, state=>Boolean(state.runningTurnId));
  useEffect(() => { const onHash = () => setPath(currentPath()); window.addEventListener("hashchange", onHash); return () => window.removeEventListener("hashchange", onHash); }, []);
  function navigate(next: string) { window.location.hash = next; setPath(next); }
  useEffect(()=>{
    const clear=()=>{chatController.reset();setAuthenticated(false);};
    const storage=(event:StorageEvent)=>{if((event.key==="pdf-rag-access-token" || event.key===null) && !isAuthenticated()) clear();};
    window.addEventListener(AUTH_CLEARED_EVENT,clear);window.addEventListener("storage",storage);
    return()=>{window.removeEventListener(AUTH_CLEARED_EVENT,clear);window.removeEventListener("storage",storage);chatController.reset();};
  },[]);
  async function onLogout() {
    const request=logout();
    chatController.reset();clearToken();setAuthenticated(false);navigate("/chat");
    try { await request; } catch { /* 本地退出已经完成。 */ }
  }
  if (!authenticated) return <Login onSuccess={() => { setAuthenticated(true); navigate("/chat"); }} />;
  return <AppLayout path={path} onNavigate={navigate} onLogout={() => void onLogout()} running={running} onNewSession={()=>{if(chatController.newSession()) navigate("/chat");}}>{path==="/knowledge"?<Knowledge/>:<Chat/>}</AppLayout>;
}
