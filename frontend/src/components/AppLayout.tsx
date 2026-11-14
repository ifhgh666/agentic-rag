import { useEffect, useState, type ReactNode } from "react";
import { cn } from "cn";
import { ChevronRight, Database, Library, LogOut, Menu, MessageSquare, PanelLeftClose, PanelLeftOpen, Plus, Wifi, WifiOff } from "lucide-react";
import { useServiceHealth } from "../hooks/use-service-health";
import { BrandMark } from "./BrandMark";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "./ui/sheet";

const links = [
  { path: "/chat", label: "问答台", icon: MessageSquare },
  { path: "/knowledge", label: "知识库", icon: Library },
];
const layoutKey = "wenmai.sidebar.collapsed.v1";
function initialCollapsed() {
  try { return window.localStorage.getItem(layoutKey) === "true"; } catch { return false; }
}

export function AppLayout({ path, onNavigate, onLogout, children, onNewSession, running=false }: { path: string; onNavigate: (path: string) => void; onLogout: () => void; children: ReactNode; onNewSession?:()=>void; running?:boolean }) {
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);
  const health = useServiceHealth();
  const current = links.find(link => link.path === path) ?? links[0];
  const connectionText = health.state === "checking" ? "正在检查" : health.state === "online" ? "服务已连接" : "服务不可连接";
  const indexText = health.state === "online" ? health.indexReady ? "索引已就绪" : "索引未就绪" : "索引状态未知";
  const statusText = health.state === "online" ? indexText : connectionText;
  const ConnectionIcon = health.state === "offline" ? WifiOff : Wifi;

  useEffect(() => { setMobileOpen(false); }, [path]);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 768px)");
    const onChange = () => { if (media.matches) setMobileOpen(false); };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  function toggleCollapsed() {
    const next = !collapsed;
    setCollapsed(next);
    try { window.localStorage.setItem(layoutKey, String(next)); } catch { /* Layout remains usable without browser storage. */ }
  }
  function navigation(compact: boolean, mobile = false) {
    return <nav aria-label={mobile ? "移动导航" : "主导航"} className="space-y-1">
      {links.map(({ path: next, label, icon: Icon }) => <Button key={next} variant="ghost" type="button" aria-label={label} aria-current={current.path === next ? "page" : undefined} title={compact ? label : undefined}
        className={cn("h-11 w-full gap-3 px-3 text-muted-foreground", compact ? "justify-center px-0" : "justify-start", current.path === next && "bg-secondary font-medium text-foreground")}
        onClick={() => { onNavigate(next); if (mobile) setMobileOpen(false); }}>
        <Icon aria-hidden="true" className="size-4.5" strokeWidth={1.6} /><span className={compact ? "sr-only" : undefined}>{label}</span>
      </Button>)}
    </nav>;
  }
  function sidebarContent(compact: boolean, mobile = false) {
    return <>
      <div className={cn("flex min-h-16 items-center gap-3 px-2", compact && "justify-center px-0")}>
        <BrandMark className="size-9 rounded-lg [&_svg]:size-5.5" />
        {!compact && <div><strong className="block text-lg font-semibold tracking-tight">文脉</strong><span className="block text-[11px] text-muted-foreground">PDF 知识工作台</span></div>}
      </div>
      <div className="mt-8">
        {onNewSession && <Button variant="outline" type="button" className={cn("mb-5 h-10 w-full",compact?"px-0":"justify-start gap-3")} disabled={running} aria-label="新会话" title="新会话" onClick={()=>{onNewSession();if(mobile)setMobileOpen(false);}}><Plus aria-hidden="true"/><span className={compact?"sr-only":undefined}>新会话</span></Button>}
        <p className={cn("mb-3 px-3 text-[11px] font-medium text-muted-foreground", compact && "sr-only")}>工作空间</p>
        {navigation(compact, mobile)}
      </div>
      <div className={cn("mt-7 space-y-3 border-t border-border px-3 pt-5 text-xs text-muted-foreground", compact && "px-0 text-center")}>
        <div className={cn("flex items-center gap-2", compact && "justify-center")} title={connectionText}>
          <ConnectionIcon aria-hidden="true" className="size-3.5 shrink-0" /><span className={compact ? "sr-only" : undefined}>{connectionText}</span>
        </div>
        <div className={cn("flex items-center gap-2", compact && "justify-center")} title={indexText}>
          <Database aria-hidden="true" className={cn("size-3.5 shrink-0", health.state === "online" && health.indexReady && "text-emerald-700")} /><span className={compact ? "sr-only" : undefined}>{indexText}</span>
        </div>
      </div>
      <div className="mt-auto border-t border-border pt-4">
        <div className={cn("mb-3 flex items-center gap-2.5 px-2", compact && "justify-center px-0")}>
          <span aria-hidden="true" className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary text-xs font-medium text-muted-foreground">管</span>
          {!compact && <div><span className="block text-xs font-medium">管理员</span><span className="block text-[11px] text-muted-foreground">当前会话</span></div>}
        </div>
        <Button variant="ghost" type="button" className={cn("h-10 w-full gap-3 text-muted-foreground", compact ? "justify-center px-0" : "justify-start px-3")} aria-label="退出当前会话" title={compact ? "退出当前会话" : undefined} onClick={onLogout}>
          <LogOut aria-hidden="true" className="size-4" strokeWidth={1.6} /><span className={compact ? "sr-only" : "text-xs"}>退出当前会话</span>
        </Button>
      </div>
    </>;
  }

  return <div className="min-h-svh bg-background text-foreground">
    <a href="#workspace-content" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:rounded-lg focus:bg-primary focus:p-3 focus:text-primary-foreground" onClick={event => { event.preventDefault(); document.getElementById("workspace-content")?.focus(); }}>跳至主要内容</a>
    <aside aria-label="工作空间侧栏" className={cn("fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-border bg-sidebar px-3 py-4 md:flex", collapsed ? "w-18" : "w-60")}>
      {sidebarContent(collapsed)}
    </aside>
    <div className={cn("min-w-0", collapsed ? "md:pl-18" : "md:pl-60")}>
      <header className="sticky top-0 z-20 flex h-16 min-w-0 items-center gap-3 border-b border-border bg-background px-4 md:px-8" aria-label="当前工作区上下文">
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger render={<Button variant="ghost" size="icon" type="button" className="md:hidden" aria-label="打开导航" />}><Menu aria-hidden="true" /></SheetTrigger>
          <SheetContent side="left" className="w-[min(18rem,calc(100vw-2rem))] gap-0 p-4">
            <SheetHeader className="sr-only"><SheetTitle>工作空间导航</SheetTitle><SheetDescription>切换页面或退出当前会话</SheetDescription></SheetHeader>
            {sidebarContent(false, true)}
          </SheetContent>
        </Sheet>
        <Button variant="ghost" size="icon" type="button" className="hidden text-muted-foreground md:inline-flex" aria-label={collapsed ? "展开导航" : "折叠导航"} title={collapsed ? "展开导航" : "折叠导航"} onClick={toggleCollapsed}>
          {collapsed ? <PanelLeftOpen aria-hidden="true" /> : <PanelLeftClose aria-hidden="true" />}
        </Button>
        <div className="flex min-w-0 items-center gap-2 text-sm">
          <span className="hidden text-muted-foreground sm:inline">工作空间</span><ChevronRight aria-hidden="true" className="hidden size-3.5 text-muted-foreground sm:block" /><strong className="truncate font-medium">{current.label}</strong>
        </div>
        <div role="status" aria-live="polite" className="ml-auto flex shrink-0 items-center gap-2 rounded-md border border-border px-2.5 py-1.5 text-[11px] text-muted-foreground">
          <span aria-hidden="true" className={cn("size-1.5 rounded-full", health.state === "online" && health.indexReady ? "bg-emerald-600" : health.state === "offline" ? "bg-red-500" : "bg-amber-500")} />{statusText}
        </div>
      </header>
      <main id="workspace-content" tabIndex={-1} className="min-w-0 focus:outline-none">{children}</main>
    </div>
  </div>;
}
