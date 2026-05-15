interface ReviewCardProps {
  outOfSyllabusRate: number;
  retryCount: number;
  status: "completed" | "fallback_completed" | "reviewing" | "retrying";
}

const STATUS_LABELS: Record<ReviewCardProps["status"], string> = {
  completed: "生成通过",
  fallback_completed: "已标注少量超纲词",
  reviewing: "质检中",
  retrying: "重新生成中",
};

export function ReviewCard({
  outOfSyllabusRate,
  retryCount,
  status,
}: ReviewCardProps) {
  const ratePercent = (outOfSyllabusRate * 100).toFixed(1);

  return (
    <div className="conversation-card review-card">
      <h4 className="text-label">质检结果</h4>
      <p className="text-supporting">
        超纲率：{ratePercent}%
      </p>
      {retryCount > 0 && (
        <p className="text-supporting">
          重试次数：{retryCount}
        </p>
      )}
      <p className={`review-status review-status--${status}`}>
        {STATUS_LABELS[status]}
      </p>
    </div>
  );
}
