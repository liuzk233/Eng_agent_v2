import type { StoryProject } from "./storyTypes";

const STYLE_LABELS: Record<StoryProject["style"], string> = {
  web_novel: "网络爽文",
  science_fiction: "科幻小说",
  exam_reading: "应试阅读",
};

interface StorySidebarProps {
  stories: StoryProject[];
  selectedStoryId: string | null;
  onSelectStory: (id: string) => void;
  onNewStory: () => void;
  onHome?: () => void;
}

export function StorySidebar({
  stories,
  selectedStoryId,
  onSelectStory,
  onNewStory,
  onHome = () => {},
}: StorySidebarProps) {
  return (
    <aside className="story-sidebar" aria-label="故事列表">
      <div className="story-sidebar-header">
        <button
          type="button"
          className="story-brand"
          onClick={onHome}
          aria-label="回到 WordFlow 主界面"
        >
          <span className="story-brand-mark" aria-hidden="true">W</span>
          <div>
            <p className="auth-kicker">Closed beta</p>
            <h1 className="text-title">WordFlow</h1>
          </div>
        </button>
        <button type="button" className="story-new-btn" onClick={onNewStory}>
          新建故事
        </button>
      </div>

      {stories.length === 0 ? (
        <div className="story-sidebar-empty">
          <p className="text-supporting">还没有故事，点击上方按钮开始创建</p>
        </div>
      ) : (
        <section className="story-history" aria-labelledby="story-history-heading">
          <h2 id="story-history-heading" className="story-history-heading text-micro-label">历史故事</h2>
          <ul className="story-sidebar-list">
            {stories.map((story) => (
              <li key={story.id}>
                <button
                  type="button"
                  className={`story-sidebar-item ${story.id === selectedStoryId ? "story-sidebar-item--selected" : ""}`}
                  onClick={() => onSelectStory(story.id)}
                  aria-current={story.id === selectedStoryId ? "true" : undefined}
                >
                  <span className="story-sidebar-item-title">{story.title}</span>
                  <span className="story-sidebar-item-meta text-micro-label">
                    {STYLE_LABELS[story.style]} · {story.targetChapterCount} 章
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  );
}
