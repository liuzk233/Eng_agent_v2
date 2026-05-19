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

function isGeneratingStatus(status: string): boolean {
  return ["queued", "running", "reviewing", "retrying"].includes(status);
}

function isCompletedStatus(status: string): boolean {
  return status === "completed" || status === "fallback_completed";
}

function findUnlockableDraft(chapters: ChapterListItem[]): number | undefined {
  const sorted = [...chapters].sort((a, b) => a.chapterNumber - b.chapterNumber);
  for (const chapter of sorted) {
    if (chapter.status !== "draft") continue;
    if (chapter.chapterNumber === 1) return chapter.chapterNumber;
    const prev = sorted.find((c) => c.chapterNumber === chapter.chapterNumber - 1);
    if (prev && isCompletedStatus(prev.status)) {
      return chapter.chapterNumber;
    }
    return undefined;
  }
  return undefined;
}

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
  const firstDraftChapterNumber = findUnlockableDraft(chapters);

  return (
    <nav className="chapter-navigator" aria-label="章节目录">
      {chapters.map((chapter) => {
        const isActive = chapter.chapterNumber === currentChapterNumber;
        const isCompleted = isCompletedStatus(chapter.status);
        const isGenerating = isGeneratingStatus(chapter.status);
        const isLockedDraft =
          chapter.status === "draft" &&
          chapter.chapterNumber !== firstDraftChapterNumber;
        const statusLabel = isLockedDraft
          ? "待解锁"
          : STATUS_LABELS[chapter.status] ?? chapter.status;

        let itemClass = "chapter-nav-item";
        if (isActive) itemClass += " chapter-nav-item--active";
        if (isCompleted) itemClass += " chapter-nav-item--completed";
        if (isGenerating) itemClass += " chapter-nav-item--generating";
        if (isLockedDraft) itemClass += " chapter-nav-item--locked";

        return (
          <button
            key={chapter.id}
            type="button"
            className={itemClass}
            onClick={() => onSelectChapter(chapter.chapterNumber)}
            aria-current={isActive ? "page" : undefined}
            disabled={isLockedDraft}
          >
            <span className="chapter-nav-number">
              第 {chapter.chapterNumber} 章
            </span>
            <span className="chapter-nav-status">
              {statusLabel}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
