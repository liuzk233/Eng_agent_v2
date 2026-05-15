import { useState, type FormEvent } from "react";
import { useAuth } from "./AuthProvider";
import "./auth.css";

export function RegisterPage() {
  const { register, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    register(email, password, inviteCode);
  }

  return (
    <div className="auth-page">
      <section className="auth-hero" aria-label="WordFlow 内测入口">
        <div className="auth-brand-mark" aria-hidden="true">W</div>
        <p className="auth-kicker">Invite only</p>
        <h1 className="auth-hero-title">先用一个故事项目，试试目标词怎么自然出现。</h1>
        <p className="auth-hero-copy">
          注册后选择网络爽文、科幻小说或应试阅读文章，每章输入目标词，再让系统生成可读的英文内容。
        </p>
        <div className="auth-proof-grid" aria-hidden="true">
          <span>邀请码门禁</span>
          <span>目标词高亮</span>
          <span>中文释义</span>
        </div>
      </section>

      <section className="auth-panel" aria-label="注册表单">
        <div className="auth-panel-header">
          <p className="auth-kicker">Start learning</p>
          <h2 className="text-headline">注册 WordFlow</h2>
          <p className="auth-panel-copy">内测阶段需要邀请码。</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <div className="auth-field">
            <label htmlFor="register-email">邮箱</label>
            <input id="register-email" type="email" value={email}
              onChange={(e) => { setEmail(e.target.value); clearError(); }}
              required autoComplete="email" placeholder="you@example.com" />
          </div>
          <div className="auth-field">
            <label htmlFor="register-password">密码</label>
            <input id="register-password" type="password" value={password}
              onChange={(e) => { setPassword(e.target.value); clearError(); }}
              required autoComplete="new-password" minLength={8} placeholder="至少 8 位" />
          </div>
          <div className="auth-field">
            <label htmlFor="register-invite-code">邀请码</label>
            <input id="register-invite-code" type="text" value={inviteCode}
              onChange={(e) => { setInviteCode(e.target.value); clearError(); }}
              required placeholder="输入内测邀请码" />
          </div>
          <button type="submit" disabled={isLoading} className="auth-submit">
            {isLoading ? "注册中..." : "注册"}
          </button>
          <p className="auth-switch">已有账号？<a href="/login">登录</a></p>
        </form>
      </section>
    </div>
  );
}
