import type { ReactNode } from "react";
import { useRef, useEffect } from "react";

interface ConversationViewProps {
  children: ReactNode;
}

export function ConversationView({ children }: ConversationViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [children]);

  return (
    <div className="conversation-view" ref={containerRef}>
      {children}
    </div>
  );
}
