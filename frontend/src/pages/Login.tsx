import { type FormEvent, useRef, useState } from "react";
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";
import { m, useReducedMotion } from "motion/react";
import { login, messageFromError } from "../api/client";
import { setToken } from "../auth/session";
import { BrandMark } from "../components/BrandMark";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const submitting = useRef(false);
  const reduceMotion = useReducedMotion();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current || !username.trim() || !password) return;
    submitting.current = true;
    setLoading(true); setError("");
    try {
      const result = await login(username.trim(), password);
      setToken(result.access_token);
      onSuccess();
    } catch (caught) {
      setError(messageFromError(caught));
    } finally { submitting.current = false; setLoading(false); }
  }

  return <main className="relative grid min-h-svh grid-rows-[minmax(0,1fr)_auto_minmax(0,3fr)] items-center bg-background px-6 py-20 text-foreground">
    <div className="row-start-2 w-full">
      <m.section aria-labelledby="login-title" className="mx-auto w-full max-w-96" initial={reduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : 0.18 }}>
        <header className="mb-10 text-center">
          <BrandMark className="mb-6 size-12 rounded-xl [&_svg]:size-7" />
          <h1 id="login-title" className="text-[28px] font-semibold tracking-tight">登录工作台</h1>
          <p className="mt-2.5 text-sm leading-6 text-muted-foreground">使用管理员账号访问你的知识空间。</p>
        </header>
        <form onSubmit={submit} className="space-y-6" aria-busy={loading}>
          <div className="space-y-2">
            <label htmlFor="login-username" className="block text-sm font-medium">管理员账号</label>
            <div className="relative">
              <UserRound aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3.5 size-4.5 -translate-y-1/2 text-muted-foreground" strokeWidth={1.6} />
              <Input id="login-username" name="username" value={username} onChange={event => setUsername(event.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} required disabled={loading} className="h-11 pl-10" />
            </div>
          </div>
          <div className="space-y-2">
            <label htmlFor="login-password" className="block text-sm font-medium">访问密码</label>
            <div className="relative">
              <LockKeyhole aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3.5 size-4.5 -translate-y-1/2 text-muted-foreground" strokeWidth={1.6} />
              <Input id="login-password" name="password" value={password} onChange={event => setPassword(event.target.value)} type={showPassword ? "text" : "password"} autoComplete="current-password" required disabled={loading} className="h-11 pr-11 pl-10" aria-describedby={error ? "login-error" : undefined} aria-invalid={Boolean(error)} />
              <Button variant="ghost" size="icon" type="button" onClick={() => setShowPassword(value => !value)} disabled={loading} aria-label={showPassword ? "隐藏密码" : "显示密码"} aria-pressed={showPassword} className="absolute top-1/2 right-1.5 -translate-y-1/2 text-muted-foreground">
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </Button>
            </div>
          </div>
          {error && <p id="login-error" role="alert" className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2.5 text-sm leading-6 text-destructive">{error}</p>}
          <Button className="relative h-11 w-full text-sm" type="submit" disabled={loading || !username.trim() || !password}>
            {loading ? "正在验证…" : "进入工作台"}<ArrowRight aria-hidden="true" className="absolute right-4" />
          </Button>
        </form>
        <p className="mt-5 flex items-center justify-center gap-2 text-center text-xs leading-5 text-muted-foreground"><ShieldCheck aria-hidden="true" className="size-4 shrink-0" strokeWidth={1.6} />单管理员模式 · 使用已配置的账号登录</p>
      </m.section>
    </div>
    <footer className="absolute inset-x-6 bottom-7 text-center text-xs leading-5 text-muted-foreground">从文档出发，让答案有据可查。</footer>
  </main>;
}
