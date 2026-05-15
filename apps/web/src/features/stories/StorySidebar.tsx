import type { StoryProject } from "./storyTypes";

interface StorySidebarProps {
  stories: StoryProject[];
  selectedStoryId: string | null;
  onSelectStory: (id: string) => void;
  onNewStory: () => void;
}

export function StorySidebar({
  stories,
  selectedStoryId,
  onSelectStory,
  onNewStory,
}: StorySidebarProps) {
  return (
    <aside className="story-sidebar" aria-label="故事列表">
      <div className="story-sidebar-header">
        <h1 className="text-title">WordFlow</h1>
        <button type="button" className="story-new-btn" onClick={onNewStory}>
          新建故事
        </button>
      </div>

      {stories.length === 0 ? (
        <div className="story-sidebar-empty">
          <p className="text-supporting">还没有故事，点击上方按钮开始创建</p>
        </div>
      ) : (
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
                  {story.targetChapterCount} 章
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
