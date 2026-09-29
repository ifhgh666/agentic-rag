import { FormEvent, useState } from "react";
import { login, messageFromError } from "../api/client";
import { setToken } from "../auth/session";

export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true); setError("");
    try {
      const result = await login(username, password);
      setToken(result.access_token);
      onSuccess();
    } catch (caught) {
      setError(messageFromError(caught));
    } finally { setLoading(false); }
  }

  return <div className="login-screen"><div className="login-art"><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-core">R</div><span className="art-caption">RETRIEVAL<br />/ OBSERVATORY</span></div><div className="login-card"><span className="eyebrow">LOCAL KNOWLEDGE SYSTEM · 001</span><h1>让每一页<br /><i>被找到。</i></h1><p className="login-lede">一个安静、可追溯的 PDF 知识工作台。上传文档，让答案从证据里长出来。</p><form onSubmit={submit}><label>管理员账号<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label><label>访问密码<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" /></label>{error && <div className="form-error">{error}</div>}<button className="primary-button" disabled={loading}>{loading ? "正在验证…" : "进入工作台"}<span>→</span></button></form><small>凭据由本地环境配置 · V1 单管理员模式</small></div></div>;
}
