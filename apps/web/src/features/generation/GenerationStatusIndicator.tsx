import type { GenerationStatus } from "../../lib/api/types";

interface GenerationStatusIndicatorProps {
  status: GenerationStatus;
  retryCount?: number;
  isStale?: boolean;
  failureReason?: string | null;
  onRetry?: () => void;
}

const STATUS_CONFIG: Record<GenerationStatus, { label: string; className: string }> = {
  queued: { label: "排队中", className: "gen-status--queued" },
  running: { label: "生成中", className: "gen-status--running" },
  reviewing: { label: "质检中", className: "gen-status--reviewing" },
  retrying: { label: "重新生成中", className: "gen-status--retrying" },
  completed: { label: "生成通过", className: "gen-status--completed" },
  fallback_completed: { label: "已标注少量超纲词", className: "gen-status--fallback" },
  failed_internal: { label: "生成异常", className: "gen-status--failed" },
};

const POLLING_STATUSES: GenerationStatus[] = ["queued", "running", "reviewing", "retrying"];

export function GenerationStatusIndicator({
  status,
  retryCount = 0,
  isStale = false,
  failureReason = null,
  onRetry,
}: GenerationStatusIndicatorProps) {
  const isStalePolling = isStale && POLLING_STATUSES.includes(status);
  const isFailed = status === "failed_internal";

  if (isStalePolling) {
    return (
      <div className="gen-status-indicator" role="status" aria-live="polite">
        <span className="gen-status-dot gen-status--failed" />
        <span className="gen-status-label text-label">生成超时，请重试</span>
        {onRetry && (
          <button className="gen-status-retry-btn" onClick={onRetry} type="button">
            重试
          </button>
        )}
      </div>
    );
  }

  const config = STATUS_CONFIG[status];
  const showRetryCount = status === "retrying" && retryCount > 0;

  return (
    <div className="gen-status-indicator" role="status" aria-live="polite">
      <span className={`gen-status-dot ${config.className}`} />
      <span className="gen-status-label text-label">{config.label}</span>
      {isFailed && (
        <span className="gen-status-retry text-supporting">
          {failureReason?.trim() || "生成失败，请重试。"}
        </span>
      )}
      {showRetryCount && (
        <span className="gen-status-retry text-micro-label">
          （第 {retryCount} 次重试）
        </span>
      )}
      {isFailed && onRetry && (
        <button className="gen-status-retry-btn" onClick={onRetry} type="button">
          重试
        </button>
      )}
    </div>
  );
}
