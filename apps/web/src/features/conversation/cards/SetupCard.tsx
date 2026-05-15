import type { StoryStyle } from "../../../lib/api/types";

const STYLE_LABELS: Record<StoryStyle, string> = {
  web_novel: "网络爽文",
  science_fiction: "科幻小说",
  exam_reading: "应试阅读文章",
};

interface SetupCardProps {
  title: string;
  style: StoryStyle;
  targetChapterCount: number;
}

export function SetupCard({ title, style, targetChapterCount }: SetupCardProps) {
  return (
    <div className="conversation-card setup-card">
      <h3 className="text-title">{title}</h3>
      <p className="text-supporting">
        风格：{STYLE_LABELS[style]} · {targetChapterCount} 章
      </p>
    </div>
  );
}
