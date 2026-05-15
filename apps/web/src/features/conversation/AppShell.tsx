import type { ReactNode } from "react";

interface AppShellProps {
  sidebar: ReactNode;
  main: ReactNode;
}

export function AppShell({ sidebar, main }: AppShellProps) {
  return (
    <div className="app-shell">
      <div className="app-shell-sidebar">{sidebar}</div>
      <main className="app-shell-main">{main}</main>
    </div>
  );
}
