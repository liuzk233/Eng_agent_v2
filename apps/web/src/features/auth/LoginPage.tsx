import { useState, type FormEvent } from "react";
import { useAuth } from "./AuthProvider";
import "./auth.css";

export function LoginPage() {
  const { login, isLoading, error, clearError } = useAuth();
  const [account, setAccount] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    login(account, password);
  }

  return (
    <div className="auth-page">
      <section className="auth-hero" aria-label="WordFlow 学习入口">
        <div className="auth-brand-mark" aria-hidden="true">W</div>
        <p className="auth-kicker">Closed beta</p>
        <h1 className="auth-hero-title">把单词放进一段会继续生长的故事里。</h1>
        <p className="auth-hero-copy">
          WordFlow 用章节、目标词和中文释义，把背词变成每天能接着读下去的英语故事训练。
        </p>
        <div className="auth-proof-grid" aria-hidden="true">
          <span>7 词/章</span>
          <span>300-500 words</span>
          <span>连载记忆</span>
        </div>
      </section>

      <section className="auth-panel" aria-label="登录表单">
        <div className="auth-panel-header">
          <p className="auth-kicker">Welcome back</p>
          <h2 className="text-headline">登录 WordFlow</h2>
          <p className="auth-panel-copy">继续你的故事词汇训练。</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <div className="auth-field">
            <label htmlFor="login-account">账号/邮箱</label>
            <input id="login-account" type="text" value={account}
              onChange={(e) => { setAccount(e.target.value); clearError(); }}
              required autoComplete="username" placeholder="you@example.com" />
          </div>
          <div className="auth-field">
            <label htmlFor="login-password">密码</label>
            <input id="login-password" type="password" value={password}
              onChange={(e) => { setPassword(e.target.value); clearError(); }}
              required autoComplete="current-password" placeholder="输入密码" />
          </div>
          <button type="submit" disabled={isLoading} className="auth-submit">
            {isLoading ? "登录中..." : "登录"}
          </button>
          <p className="auth-switch">没有账号？<a href="/register">注册</a></p>
        </form>
      </section>
    </div>
  );
}
