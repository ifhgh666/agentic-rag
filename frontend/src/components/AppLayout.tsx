import type { ReactNode } from "react";

const links = [
  { href: "#/chat", label: "问答台", icon: "↗" },
  { href: "#/knowledge", label: "知识库", icon: "▦" },
  { href: "#/logs", label: "运行日志", icon: "≋" },
];

export function AppLayout({ path, onNavigate, onLogout, children }: { path: string; onNavigate: (path: string) => void; onLogout: () => void; children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-symbol">R</div>
          <div><strong>文脉</strong><span>PDF RAG 工作台</span></div>
        </div>
        <div className="side-kicker">知识流 · 01</div>
        <nav>
          {links.map((link) => {
            const active = path === link.href.replace("#", "") || (path === "/" && link.href === "#/chat");
            return <button key={link.href} className={`nav-item ${active ? "active" : ""}`} onClick={() => onNavigate(link.href.replace("#", ""))}><span>{link.icon}</span>{link.label}</button>;
          })}
        </nav>
        <div className="sidebar-foot">
          <div className="status-dot"><i />本地服务在线</div>
          <button className="logout-link" onClick={onLogout}>退出当前会话</button>
        </div>
      </aside>
      <main className="main-canvas">{children}</main>
    </div>
  );
}
