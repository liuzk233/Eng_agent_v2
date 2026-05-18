import type { ChapterListItem } from "../../lib/api/types";

const STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  fallback_completed: "已完成",
  queued: "生成中",
  running: "生成中",
  reviewing: "生成中",
  retrying: "生成中",
  failed_internal: "失败",
  draft: "待生成",
};

interface ChapterNavigatorProps {
  chapters: ChapterListItem[];
  currentChapterNumber: number;
  onSelectChapter: (chapterNumber: number) => void;
}

export function ChapterNavigator({
  chapters,
  currentChapterNumber,
  onSelectChapter,
}: ChapterNavigatorProps) {
  return (
    <nav className="chapter-navigator" aria-label="章节目录">
      {chapters.map((chapter) => {
        const isActive = chapter.chapterNumber === currentChapterNumber;
        const isCompleted =
          chapter.status === "completed" ||
          chapter.status === "fallback_completed";
        const isGenerating =
          chapter.status === "queued" ||
          chapter.status === "running" ||
          chapter.status === "reviewing" ||
          chapter.status === "retrying";

        let itemClass = "chapter-nav-item";
        if (isActive) itemClass += " chapter-nav-item--active";
        if (isCompleted) itemClass += " chapter-nav-item--completed";
        if (isGenerating) itemClass += " chapter-nav-item--generating";

        return (
          <button
            key={chapter.id}
            type="button"
            className={itemClass}
            onClick={() => onSelectChapter(chapter.chapterNumber)}
            aria-current={isActive ? "page" : undefined}
          >
            <span className="chapter-nav-number">
              第 {chapter.chapterNumber} 章
            </span>
            <span className="chapter-nav-status">
              {STATUS_LABELS[chapter.status] ?? chapter.status}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
