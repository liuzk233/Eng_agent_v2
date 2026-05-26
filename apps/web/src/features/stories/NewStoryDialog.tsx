import { useState, type FormEvent } from "react";
import type { StoryStyle } from "../../lib/api/types";
import {
  STORY_STYLE_OPTIONS,
  EXAM_READING_CHAPTER_COUNT,
  type NewStoryInput,
} from "./storyTypes";

interface NewStoryDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (input: NewStoryInput) => void;
}

export function NewStoryDialog({ open, onClose, onSubmit }: NewStoryDialogProps) {
  const [style, setStyle] = useState<StoryStyle>("web_novel");
  const [chapterCount, setChapterCount] = useState(5);

  const isExamReading = style === "exam_reading";
  const effectiveChapterCount = isExamReading ? EXAM_READING_CHAPTER_COUNT : chapterCount;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onSubmit({ style, targetChapterCount: effectiveChapterCount });
    setStyle("web_novel");
    setChapterCount(5);
  }

  if (!open) return null;

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true" aria-label="新建故事">
      <form className="dialog-content" onSubmit={handleSubmit}>
        <h2 className="text-title">新建故事</h2>

        <fieldset className="auth-field">
          <legend>故事风格</legend>
          {STORY_STYLE_OPTIONS.map((opt) => (
            <label key={opt.value} className="style-radio-label">
              <input
                type="radio"
                name="story-style"
                value={opt.value}
                checked={style === opt.value}
                onChange={() => {
                  setStyle(opt.value);
                  if (opt.value === "exam_reading") {
                    setChapterCount(EXAM_READING_CHAPTER_COUNT);
                  }
                }}
              />
              {opt.label}
            </label>
          ))}
        </fieldset>

        <div className="auth-field">
          <label htmlFor="new-story-chapters">章节数</label>
          <input
            id="new-story-chapters"
            type="number"
            min={1}
            max={50}
            value={effectiveChapterCount}
            onChange={(e) => setChapterCount(Number(e.target.value))}
            disabled={isExamReading}
          />
          {isExamReading && (
            <span className="text-supporting">应试阅读固定为 1 章</span>
          )}
        </div>

        <div className="dialog-actions">
          <button type="button" className="dialog-cancel-btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" className="auth-submit">
            创建故事
          </button>
        </div>
      </form>
    </div>
  );
}
